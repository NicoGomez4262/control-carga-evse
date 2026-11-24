// EVSE Monitor · Worker principal: API REST, WebSockets (equipo y navegador) y limpieza diaria.
// La app web está en public/ y la sirve Cloudflare como archivos estáticos.

import { crearUsuario, rutasAuth, usuarioActual } from "./auth.js";
import { telegram } from "./notificar.js";
import { ahora, CONFIG_DEFECTO, tokenEquipo, cuerpo, error, ID_EQUIPO, iguales, json, limpiarConfig, sha256 } from "./util.js";

export { Equipo } from "./equipo.js";

const ORDENES = new Set(["permitir", "detener", "reconocer", "soltar_parar", "estado", "reiniciar", "cal_leer", "cal_auto", "cal_escribir", "cal_fabrica"]);

const stub = (env, id) => env.EQUIPO.get(env.EQUIPO.idFromName(id));

// ------------------------------------------------------------------ equipo (ESP32)
async function autenticarEquipo(req, env) {
  const m = /^Bearer ([a-z0-9-]+):([A-Za-z0-9_-]{16,})$/.exec(req.headers.get("authorization") || "");
  if (!m) return null;
  const fila = await env.DB.prepare("SELECT id, token_hash FROM equipos WHERE id = ?").bind(m[1]).first();
  if (!fila || !iguales(await sha256(m[2]), fila.token_hash)) return null;
  return fila.id;
}

async function rutasDispositivo(req, env, ruta) {
  const id = await autenticarEquipo(req, env);
  if (!id) return error(401, "credenciales del equipo inválidas");
  if (ruta === "/api/dispositivo/ws") {
    if (req.headers.get("upgrade") !== "websocket") return error(426, "se espera WebSocket");
    const h = new Headers(req.headers);
    h.set("x-tipo", "equipo");
    h.set("x-equipo", id);
    return stub(env, id).fetch(new Request(req.url, { headers: h }));
  }
  const fw = /^\/api\/dispositivo\/firmware\/([\w.-]+)$/.exec(ruta);
  if (fw) {
    const bin = await env.FIRMWARE.get(`fw:${fw[1]}`, "arrayBuffer");
    if (!bin) return error(404, "no existe esa versión");
    return new Response(bin, { headers: { "content-type": "application/octet-stream", "content-length": String(bin.byteLength) } });
  }
  return error(404, "ruta desconocida");
}

// ------------------------------------------------------------------ permisos
async function rolEn(env, usuario, equipoId) {
  if (usuario.admin) return "propietario";
  const f = await env.DB.prepare("SELECT rol FROM permisos WHERE usuario_id = ? AND equipo_id = ?").bind(usuario.id, equipoId).first();
  return f?.rol || null;
}

function rango(url, diasPorDefecto) {
  const t = ahora();
  const hasta = Number(url.searchParams.get("hasta")) || t;
  const desde = Number(url.searchParams.get("desde")) || hasta - diasPorDefecto * 86400;
  return [Math.floor(desde), Math.floor(hasta)];
}

function csv(filas, columnas, nombre) {
  const esc = (v) => (v === null || v === undefined ? "" : /[",\n;]/.test(String(v)) ? `"${String(v).replace(/"/g, '""')}"` : String(v));
  const texto = [columnas.join(","), ...filas.map((f) => columnas.map((c) => esc(f[c])).join(","))].join("\n");
  return new Response("﻿" + texto, {
    headers: { "content-type": "text/csv; charset=utf-8", "content-disposition": `attachment; filename="${nombre}"` },
  });
}

const fechaBogota = (ts) =>
  ts ? new Date(ts * 1000).toLocaleString("sv-SE", { timeZone: "America/Bogota" }).replace("T", " ") : "";

// ------------------------------------------------------------------ rutas de un equipo
async function rutasEquipo(req, env, url, usuario, id, resto, datos) {
  const rol = await rolEn(env, usuario, id);
  if (!rol) return error(404, "No tienes acceso a ese equipo.");
  const propietario = rol === "propietario";
  const m = req.method;

  if (resto === "" && m === "GET") {
    const fila = await env.DB.prepare("SELECT id, nombre, config, config_v, fw, mac, ultimo_contacto, creado FROM equipos WHERE id = ?")
      .bind(id)
      .first();
    if (!fila) return error(404, "No existe el equipo.");
    const estado = await stub(env, id).estado();
    return json({ equipo: { ...fila, config: { ...CONFIG_DEFECTO, ...JSON.parse(fila.config || "{}") } }, rol, estado });
  }

  if (resto === "" && m === "PUT") {
    if (!propietario) return error(403, "Solo el propietario puede cambiarlo.");
    const nombre = String(datos.nombre || "").trim().slice(0, 60);
    if (!nombre) return error(400, "Falta el nombre.");
    await env.DB.prepare("UPDATE equipos SET nombre = ? WHERE id = ?").bind(nombre, id).run();
    return json({ ok: true });
  }

  if (resto === "/ws") {
    if (req.headers.get("upgrade") !== "websocket") return error(426, "se espera WebSocket");
    const h = new Headers();
    h.set("upgrade", "websocket");
    h.set("x-tipo", "web");
    h.set("x-equipo", id);
    h.set("x-usuario", String(usuario.id));
    h.set("x-rol", rol);
    for (const k of ["sec-websocket-key", "sec-websocket-version", "sec-websocket-extensions"]) {
      const v = req.headers.get(k);
      if (v) h.set(k, v);
    }
    return stub(env, id).fetch(new Request(req.url, { headers: h }));
  }

  if (resto === "/orden" && m === "POST") {
    if (!propietario) return error(403, "Tu usuario es de solo lectura.");
    const o = String(datos.o || "");
    if (!ORDENES.has(o)) return error(400, "Orden desconocida.");
    if (o.startsWith("cal_") && o !== "cal_leer" && !usuario.admin) return error(403, "La calibración la cambia un administrador.");
    const r = await stub(env, id).orden(o, datos.a || {}, usuario.id);
    if (o === "reconocer" && r.ok)
      await env.DB.prepare("UPDATE eventos SET reconocido = 1 WHERE equipo_id = ? AND nivel >= 1 AND reconocido = 0").bind(id).run();
    return json(r, r.ok ? 200 : 409);
  }

  if (resto === "/config" && m === "PUT") {
    if (!propietario) return error(403, "Tu usuario es de solo lectura.");
    const fila = await env.DB.prepare("SELECT config, config_v FROM equipos WHERE id = ?").bind(id).first();
    const c = limpiarConfig(datos.config, JSON.parse(fila.config || "{}"));
    const v = (fila.config_v || 0) + 1;
    await env.DB.prepare("UPDATE equipos SET config = ?, config_v = ? WHERE id = ?").bind(JSON.stringify(c), v, id).run();
    const enviada = await stub(env, id).enviarConfig(v, c);
    return json({ ok: true, v, config: c, enviada });
  }

  if (resto === "/ota" && m === "POST") {
    if (!usuario.admin) return error(403, "La OTA la hace un administrador.");
    const fw = await env.DB.prepare("SELECT version, tam, sha256 FROM firmware WHERE version = ?").bind(String(datos.ver || "")).first();
    if (!fw) return error(404, "No existe esa versión de firmware.");
    const r = await stub(env, id).orden("ota", { ver: fw.version, tam: fw.tam, sha: fw.sha256 }, usuario.id);
    return json(r, r.ok ? 200 : 409);
  }

  if (resto === "/token" && m === "POST") {
    if (!usuario.admin) return error(403, "Solo un administrador.");
    const secreto = tokenEquipo();
    await env.DB.prepare("UPDATE equipos SET token_hash = ? WHERE id = ?").bind(await sha256(secreto), id).run();
    return json({ id, token: secreto });
  }

  if (resto === "" && m === "DELETE") {
    if (!usuario.admin) return error(403, "Solo un administrador.");
    await env.DB.batch([
      env.DB.prepare("DELETE FROM permisos WHERE equipo_id = ?").bind(id),
      env.DB.prepare("DELETE FROM equipos WHERE id = ?").bind(id),
    ]);
    return json({ ok: true });
  }

  if (resto === "/mediciones" || resto === "/mediciones.csv") {
    const [desde, hasta] = rango(url, 1);
    if (resto.endsWith(".csv")) {
      const { results } = await env.DB.prepare(
        "SELECT * FROM mediciones WHERE equipo_id = ? AND ts BETWEEN ? AND ? ORDER BY ts LIMIT 200000",
      )
        .bind(id, desde, hasta)
        .all();
      for (const f of results) f.fecha = fechaBogota(f.ts);
      return csv(results, ["fecha", "ts", "v", "i", "p", "pf", "f", "es", "et", "tsn", "tam", "hum", "k1", "mot"], `mediciones_${id}.csv`);
    }
    // Se agrupa en ≤ 600 puntos para las gráficas.
    const max = Math.min(2000, Math.max(50, Number(url.searchParams.get("max")) || 600));
    const paso = Math.max(1, Math.ceil((hasta - desde) / max));
    const { results } = await env.DB.prepare(
      `SELECT (ts / ?1) * ?1 AS ts, AVG(v) AS v, AVG(i) AS i, AVG(p) AS p, MAX(p) AS pmax, AVG(pf) AS pf,
              AVG(tsn) AS tsn, MAX(tsn) AS tsn_max, AVG(tam) AS tam, AVG(hum) AS hum, MAX(et) AS et, MAX(k1) AS k1
       FROM mediciones WHERE equipo_id = ?2 AND ts BETWEEN ?3 AND ?4 GROUP BY ts / ?1 ORDER BY 1`,
    )
      .bind(paso, id, desde, hasta)
      .all();
    return json({ desde, hasta, paso, puntos: results });
  }

  if (resto === "/sesiones" || resto === "/sesiones.csv") {
    const [desde, hasta] = rango(url, 90);
    const { results } = await env.DB.prepare(
      "SELECT * FROM sesiones_carga WHERE equipo_id = ? AND inicio BETWEEN ? AND ? ORDER BY inicio DESC LIMIT 2000",
    )
      .bind(id, desde, hasta)
      .all();
    if (resto.endsWith(".csv")) {
      for (const f of results) {
        f.inicio_fecha = fechaBogota(f.inicio);
        f.fin_fecha = fechaBogota(f.fin);
        f.duracion_min = f.fin ? Math.round((f.fin - f.inicio) / 60) : "";
      }
      return csv(results, ["num", "inicio_fecha", "fin_fecha", "duracion_min", "kwh", "p_max", "tarifa", "costo", "motivo_fin"], `sesiones_${id}.csv`);
    }
    return json({ desde, hasta, sesiones: results });
  }

  if (resto === "/eventos") {
    const [desde, hasta] = rango(url, 30);
    const nivel = Number(url.searchParams.get("nivel")) || 0;
    const { results } = await env.DB.prepare(
      "SELECT * FROM eventos WHERE equipo_id = ? AND ts BETWEEN ? AND ? AND nivel >= ? ORDER BY ts DESC, seq DESC LIMIT 500",
    )
      .bind(id, desde, hasta, nivel)
      .all();
    return json({ eventos: results });
  }

  if (resto === "/ordenes") {
    const { results } = await env.DB.prepare(
      `SELECT o.ts, o.orden, o.args, o.ok, o.msg, u.nombre FROM ordenes o LEFT JOIN usuarios u ON u.id = o.usuario_id
       WHERE o.equipo_id = ? ORDER BY o.ts DESC LIMIT 100`,
    )
      .bind(id)
      .all();
    return json({ ordenes: results });
  }

  if (resto === "/permisos") {
    if (!usuario.admin) return error(403, "Solo un administrador.");
    if (m === "GET") {
      const { results } = await env.DB.prepare(
        "SELECT u.id, u.email, u.nombre, p.rol FROM permisos p JOIN usuarios u ON u.id = p.usuario_id WHERE p.equipo_id = ?",
      )
        .bind(id)
        .all();
      return json({ permisos: results });
    }
    if (m === "POST") {
      const u = await env.DB.prepare("SELECT id FROM usuarios WHERE email = ?").bind(String(datos.email || "").toLowerCase()).first();
      if (!u) return error(404, "No hay un usuario con ese correo.");
      const r = datos.rol === "lectura" ? "lectura" : "propietario";
      await env.DB.prepare("INSERT OR REPLACE INTO permisos (usuario_id, equipo_id, rol) VALUES (?, ?, ?)").bind(u.id, id, r).run();
      return json({ ok: true });
    }
    if (m === "DELETE") {
      await env.DB.prepare("DELETE FROM permisos WHERE usuario_id = ? AND equipo_id = ?").bind(Number(datos.usuario_id), id).run();
      return json({ ok: true });
    }
  }

  return error(404, "Ruta desconocida.");
}

// ------------------------------------------------------------------ API
async function api(req, env, url) {
  const ruta = url.pathname.replace(/\/+$/, "");
  if (ruta === "/api/salud") return json({ ok: true, hora: ahora() });
  if (ruta.startsWith("/api/dispositivo/")) return rutasDispositivo(req, env, ruta);

  // Contra CSRF: toda petición que cambia algo debe traer esta cabecera (otro sitio no la puede poner sin CORS).
  const cambia = !["GET", "HEAD"].includes(req.method);
  if (cambia && req.headers.get("x-evse") !== "1") return error(403, "Falta la cabecera X-EVSE.");

  const usuario = await usuarioActual(req, env);
  const datos = cambia && req.headers.get("content-type")?.includes("json") ? await cuerpo(req) : {};

  if (ruta.startsWith("/api/auth/")) {
    const r = await rutasAuth(req, env, ruta, usuario, datos);
    if (r) return r;
  }
  if (!usuario) return error(401, "Inicia sesión.");

  if (ruta === "/api/perfil" && req.method === "POST") {
    const nombre = String(datos.nombre ?? usuario.nombre).trim().slice(0, 60) || usuario.nombre;
    const chat = String(datos.telegram_chat ?? "").trim().slice(0, 32) || null;
    await env.DB.prepare("UPDATE usuarios SET nombre = ?, telegram_chat = ? WHERE id = ?").bind(nombre, chat, usuario.id).run();
    return json({ ok: true });
  }
  if (ruta === "/api/perfil/probar" && req.method === "POST") {
    if (!env.TELEGRAM_TOKEN) return error(409, "El servidor no tiene TELEGRAM_TOKEN configurado.");
    const ok = await telegram(env, usuario.telegram_chat, `🔔 Prueba de EVSE Monitor para ${usuario.nombre}.`);
    return ok ? json({ ok }) : error(409, "Telegram rechazó el mensaje: revisa el chat id y que le hayas escrito al bot.");
  }

  if (ruta === "/api/equipos" && req.method === "GET") {
    const q = usuario.admin
      ? env.DB.prepare("SELECT id, nombre, fw, ultimo_contacto, 'propietario' AS rol FROM equipos ORDER BY nombre")
      : env.DB.prepare(
          "SELECT e.id, e.nombre, e.fw, e.ultimo_contacto, p.rol FROM equipos e JOIN permisos p ON p.equipo_id = e.id WHERE p.usuario_id = ? ORDER BY e.nombre",
        ).bind(usuario.id);
    const { results } = await q.all();
    const estados = await Promise.all(results.map((e) => stub(env, e.id).estado().catch(() => null)));
    return json({ equipos: results.map((e, k) => ({ ...e, estado: estados[k] })) });
  }

  if (ruta === "/api/equipos" && req.method === "POST") {
    if (!usuario.admin) return error(403, "Solo un administrador.");
    const id = String(datos.id || "").trim().toLowerCase();
    if (!ID_EQUIPO.test(id)) return error(400, "El id debe tener de 3 a 32 letras minúsculas, números o guiones.");
    const secreto = tokenEquipo();
    try {
      await env.DB.prepare("INSERT INTO equipos (id, nombre, token_hash, config, config_v, creado) VALUES (?, ?, ?, ?, 1, ?)")
        .bind(id, String(datos.nombre || id).slice(0, 60), await sha256(secreto), JSON.stringify(CONFIG_DEFECTO), ahora())
        .run();
    } catch {
      return error(409, "Ya existe un equipo con ese id.");
    }
    return json({ id, token: secreto });
  }

  const e = /^\/api\/equipos\/([a-z0-9-]+)(\/.*)?$/.exec(ruta);
  if (e) return rutasEquipo(req, env, url, usuario, e[1], e[2] || "", datos);

  // ---- administración
  if (!usuario.admin && (ruta.startsWith("/api/usuarios") || ruta.startsWith("/api/firmware"))) return error(403, "Solo un administrador.");

  if (ruta === "/api/usuarios" && req.method === "GET") {
    const { results } = await env.DB.prepare(
      `SELECT u.id, u.email, u.nombre, u.admin, u.creado, (u.telegram_chat IS NOT NULL) AS telegram,
              (SELECT GROUP_CONCAT(equipo_id || ':' || rol) FROM permisos WHERE usuario_id = u.id) AS equipos
       FROM usuarios u ORDER BY u.nombre`,
    ).all();
    return json({ usuarios: results });
  }
  if (ruta === "/api/usuarios" && req.method === "POST") {
    const r = await crearUsuario(env, datos);
    if (typeof r === "string") return error(400, r);
    if (datos.equipo && ID_EQUIPO.test(datos.equipo))
      await env.DB.prepare("INSERT OR REPLACE INTO permisos (usuario_id, equipo_id, rol) VALUES (?, ?, ?)")
        .bind(r.id, datos.equipo, datos.rol === "lectura" ? "lectura" : "propietario")
        .run();
    return json({ ok: true, id: r.id });
  }
  const u = /^\/api\/usuarios\/(\d+)$/.exec(ruta);
  if (u && req.method === "DELETE") {
    if (Number(u[1]) === usuario.id) return error(400, "No te puedes borrar a ti mismo.");
    await env.DB.prepare("DELETE FROM usuarios WHERE id = ?").bind(Number(u[1])).run();
    return json({ ok: true });
  }

  if (ruta === "/api/firmware" && req.method === "GET") {
    const { results } = await env.DB.prepare("SELECT * FROM firmware ORDER BY subido DESC").all();
    return json({ firmware: results });
  }
  if (ruta === "/api/firmware" && req.method === "POST") {
    const ver = url.searchParams.get("ver") || "";
    if (!/^[\w.-]{1,32}$/.test(ver)) return error(400, "Versión inválida (p. ej. 1.0.1).");
    const bin = await req.arrayBuffer();
    if (bin.byteLength < 100000 || bin.byteLength > 4 * 1024 * 1024) return error(400, "El .bin debe medir entre 100 KB y 4 MB.");
    if (new Uint8Array(bin)[0] !== 0xe9) return error(400, "No parece un firmware de ESP32 (debe empezar con E9).");
    const sha = await sha256(bin);
    await env.FIRMWARE.put(`fw:${ver}`, bin);
    await env.DB.prepare("INSERT OR REPLACE INTO firmware (version, tam, sha256, notas, subido) VALUES (?, ?, ?, ?, ?)")
      .bind(ver, bin.byteLength, sha, (url.searchParams.get("notas") || "").slice(0, 200), ahora())
      .run();
    return json({ ok: true, version: ver, tam: bin.byteLength, sha256: sha });
  }
  const f = /^\/api\/firmware\/([\w.-]+)$/.exec(ruta);
  if (f && req.method === "DELETE") {
    await env.FIRMWARE.delete(`fw:${f[1]}`);
    await env.DB.prepare("DELETE FROM firmware WHERE version = ?").bind(f[1]).run();
    return json({ ok: true });
  }

  return error(404, "Ruta desconocida.");
}

export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    if (url.pathname.startsWith("/api/")) {
      try {
        return await api(req, env, url);
      } catch (e) {
        console.error(e);
        return error(500, "Error interno del servidor.");
      }
    }
    return env.ASSETS.fetch(req);
  },

  // Limpieza diaria.
  async scheduled(_evento, env) {
    const t = ahora();
    const dias = Number(env.RETENCION_DIAS) || 730;
    await env.DB.batch([
      env.DB.prepare("DELETE FROM mediciones WHERE ts < ?").bind(t - dias * 86400),
      env.DB.prepare("DELETE FROM sesiones_web WHERE expira < ?").bind(t),
      env.DB.prepare("DELETE FROM intentos WHERE ts < ?").bind(t - 86400),
      env.DB.prepare("DELETE FROM ordenes WHERE ts < ?").bind(t - 365 * 86400),
    ]);
  },
};
