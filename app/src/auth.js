// Usuarios y sesiones.
//
// La clave nunca viaja ni se guarda en claro: el navegador la deriva con PBKDF2-SHA256 (300 000 iteraciones,
// sal = «evse-monitor|» + email) y manda el resultado en hexadecimal. El servidor guarda sha256(sal:derivada)
// con una sal aleatoria propia. Así el costo del PBKDF2 lo paga el navegador (el plan gratis de Workers da
// 10 ms de CPU por petición) y un volcado de la base no sirve sin repetir el PBKDF2 por cada intento.

import { ahora, aleatorio, cookies, error, iguales, json, sha256, EMAIL } from "./util.js";

const COOKIE = "evse_sesion";
const DURACION = 30 * 86400;
const DERIVADA = /^[0-9a-f]{64}$/;

export async function usuarioActual(req, env) {
  const token = cookies(req)[COOKIE];
  if (!token) return null;
  const h = await sha256(token);
  const fila = await env.DB.prepare(
    `SELECT u.id, u.email, u.nombre, u.admin, u.telegram_chat FROM sesiones_web s
     JOIN usuarios u ON u.id = s.usuario_id WHERE s.token_hash = ? AND s.expira > ?`,
  )
    .bind(h, ahora())
    .first();
  return fila || null;
}

function cookieSesion(token, req, maxAge = DURACION) {
  const seguro = new URL(req.url).protocol === "https:" ? "; Secure" : "";
  return `${COOKIE}=${token}; Path=/; HttpOnly; SameSite=Lax; Max-Age=${maxAge}${seguro}`;
}

async function abrirSesion(env, req, usuarioId) {
  const token = aleatorio(32);
  const t = ahora();
  await env.DB.prepare("INSERT INTO sesiones_web (token_hash, usuario_id, expira, creado) VALUES (?, ?, ?, ?)")
    .bind(await sha256(token), usuarioId, t + DURACION, t)
    .run();
  return cookieSesion(token, req);
}

export async function crearUsuario(env, { email, nombre, clave, admin = 0 }) {
  if (!EMAIL.test(email || "")) return "correo inválido";
  if (!DERIVADA.test(clave || "")) return "clave inválida";
  const sal = aleatorio(16);
  try {
    const r = await env.DB.prepare(
      "INSERT INTO usuarios (email, nombre, sal, hash, admin, creado) VALUES (?, ?, ?, ?, ?, ?)",
    )
      .bind(email.trim().toLowerCase(), (nombre || email).trim().slice(0, 60), sal, await sha256(`${sal}:${clave}`), admin ? 1 : 0, ahora())
      .run();
    return { id: r.meta.last_row_id };
  } catch (e) {
    return String(e).includes("UNIQUE") ? "ya existe un usuario con ese correo" : "no se pudo crear el usuario";
  }
}

export async function rutasAuth(req, env, ruta, usuario, datos) {
  if (ruta === "/api/auth/estado") {
    const n = await env.DB.prepare("SELECT COUNT(*) AS n FROM usuarios").first("n");
    return json({ hay_usuarios: n > 0, usuario });
  }

  if (ruta === "/api/auth/registro") {
    // Solo para crear el primer administrador, con el código de CODIGO_INICIAL (secreto del Worker).
    const n = await env.DB.prepare("SELECT COUNT(*) AS n FROM usuarios").first("n");
    if (n > 0) return error(403, "El registro está cerrado: pídele una cuenta al administrador.");
    if (!env.CODIGO_INICIAL || !iguales(await sha256(datos.codigo || ""), await sha256(env.CODIGO_INICIAL)))
      return error(403, "Código de instalación incorrecto.");
    const r = await crearUsuario(env, { ...datos, admin: 1 });
    if (typeof r === "string") return error(400, r);
    return json({ ok: true }, 200, { "set-cookie": await abrirSesion(env, req, r.id) });
  }

  if (ruta === "/api/auth/entrar") {
    const email = String(datos.email || "").trim().toLowerCase();
    const t = ahora();
    const fallos = await env.DB.prepare("SELECT COUNT(*) AS n FROM intentos WHERE email = ? AND ts > ?")
      .bind(email, t - 900)
      .first("n");
    if (fallos >= 5) return error(429, "Demasiados intentos. Espera 15 minutos.");
    const u = await env.DB.prepare("SELECT id, sal, hash FROM usuarios WHERE email = ?").bind(email).first();
    const ok = u && DERIVADA.test(datos.clave || "") && iguales(await sha256(`${u.sal}:${datos.clave}`), u.hash);
    if (!ok) {
      await env.DB.prepare("INSERT INTO intentos (email, ts) VALUES (?, ?)").bind(email, t).run();
      return error(401, "Correo o clave incorrectos.");
    }
    await env.DB.prepare("DELETE FROM intentos WHERE email = ?").bind(email).run();
    return json({ ok: true }, 200, { "set-cookie": await abrirSesion(env, req, u.id) });
  }

  if (ruta === "/api/auth/salir") {
    const token = cookies(req)[COOKIE];
    if (token) await env.DB.prepare("DELETE FROM sesiones_web WHERE token_hash = ?").bind(await sha256(token)).run();
    return json({ ok: true }, 200, { "set-cookie": cookieSesion("", req, 0) });
  }

  if (!usuario) return error(401, "Inicia sesión.");

  if (ruta === "/api/auth/yo") return json({ usuario });

  if (ruta === "/api/auth/clave") {
    const u = await env.DB.prepare("SELECT sal, hash FROM usuarios WHERE id = ?").bind(usuario.id).first();
    if (!iguales(await sha256(`${u.sal}:${datos.actual}`), u.hash)) return error(401, "La clave actual no coincide.");
    if (!DERIVADA.test(datos.nueva || "")) return error(400, "Clave nueva inválida.");
    const sal = aleatorio(16);
    await env.DB.batch([
      env.DB.prepare("UPDATE usuarios SET sal = ?, hash = ? WHERE id = ?").bind(sal, await sha256(`${sal}:${datos.nueva}`), usuario.id),
      env.DB.prepare("DELETE FROM sesiones_web WHERE usuario_id = ?").bind(usuario.id),
    ]);
    return json({ ok: true }, 200, { "set-cookie": await abrirSesion(env, req, usuario.id) });
  }

  return null;
}
