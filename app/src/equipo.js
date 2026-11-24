// Durable Object «Equipo»: uno por equipo. Mantiene el WebSocket del ESP32 y los de los navegadores
// (API de hibernación: no se cobra duración mientras nadie habla), guarda el último estado, escribe el
// historial en D1, reenvía órdenes y avisa de alarmas. Protocolo en docs/software/PROTOCOLO_MENSAJES.md.

import { DurableObject } from "cloudflare:workers";
import { avisarEquipo } from "./notificar.js";
import { ahora, CONFIG_DEFECTO } from "./util.js";

const FUERA_DE_LINEA_S = 100; // sin nada del equipo (ni «ping») durante este tiempo = fuera de línea
const AVISO_FUERA_S = 120; // espera antes de avisar «fuera de línea» (reconexiones cortas no avisan)
const ESPERA_ACK_MS = 10000;

const TEXTO_MOTIVO = {
  falla: "falla",
  temperatura: "sobretemperatura",
  parar: "PARAR pulsado",
  red: "tensión de red baja",
  limite: "límite de la sesión",
  horario: "fuera del horario",
  app: "detenida desde la app",
  arranque: "esperando confirmación al arrancar",
};

export class Equipo extends DurableObject {
  constructor(ctx, env) {
    super(ctx, env);
    this.pendientes = new Map();
    // El «ping» del equipo se contesta sin despertar al objeto.
    this.ctx.setWebSocketAutoResponse(new WebSocketRequestResponsePair("ping", "pong"));
  }

  // ------------------------------------------------------------------ conexiones
  async fetch(req) {
    if (req.headers.get("upgrade") !== "websocket") return new Response("Se espera WebSocket", { status: 426 });
    const tipo = req.headers.get("x-tipo");
    const id = req.headers.get("x-equipo");
    const par = new WebSocketPair();
    const [cliente, servidor] = Object.values(par);
    await this.ctx.storage.put("id", id);

    if (tipo === "equipo") {
      for (const viejo of this.ctx.getWebSockets("equipo")) {
        try {
          viejo.close(4000, "reemplazado por una conexión nueva");
        } catch {}
      }
      this.ctx.acceptWebSocket(servidor, ["equipo"]);
      servidor.serializeAttachment({ tipo: "equipo", desde: ahora() });
      await this.ctx.storage.setAlarm(Date.now() + 60000);
    } else {
      const uid = req.headers.get("x-usuario");
      const rol = req.headers.get("x-rol");
      this.ctx.acceptWebSocket(servidor, ["web"]);
      servidor.serializeAttachment({ tipo: "web", uid, rol });
      servidor.send(JSON.stringify({ t: "estado", ...(await this.estado()) }));
      if (this.webAbiertos().length === 1) this.alEquipo({ t: "vivo", on: true });
    }
    return new Response(null, { status: 101, webSocket: cliente });
  }

  equipoWs() {
    return this.ctx.getWebSockets("equipo").find((w) => w.readyState === WebSocket.OPEN) || null;
  }

  webAbiertos(excepto) {
    return this.ctx.getWebSockets("web").filter((w) => w !== excepto && w.readyState === WebSocket.OPEN);
  }

  alEquipo(m) {
    const w = this.equipoWs();
    if (!w) return false;
    try {
      w.send(JSON.stringify(m));
      return true;
    } catch {
      return false;
    }
  }

  aLaWeb(m) {
    const s = JSON.stringify(m);
    for (const w of this.webAbiertos()) {
      try {
        w.send(s);
      } catch {}
    }
  }

  async webSocketMessage(ws, msg) {
    const a = ws.deserializeAttachment() || {};
    if (a.tipo !== "equipo") return; // los navegadores solo escuchan; las órdenes van por la API
    if (typeof msg !== "string") return;
    let m;
    try {
      m = JSON.parse(msg);
    } catch {
      return;
    }
    const id = await this.ctx.storage.get("id");
    switch (m.t) {
      case "hola":
        return this.hola(ws, id, m);
      case "tel":
        return this.telemetria(id, m);
      case "reg":
        return this.registros(ws, id, m);
      case "ack":
        return this.ack(m);
      case "cfg":
        return this.cfgReportada(id, m);
      case "ota":
        await this.ctx.storage.put("ota", { ...m, rx: ahora() });
        return this.aLaWeb({ t: "ota", ...m });
    }
  }

  async webSocketClose(ws, codigo) {
    try {
      ws.close(codigo >= 1000 && codigo < 5000 && codigo !== 1005 && codigo !== 1006 ? codigo : 1000, "cerrado");
    } catch {}
    await this.alCerrar(ws);
  }

  async webSocketError(ws) {
    await this.alCerrar(ws);
  }

  async alCerrar(ws) {
    const a = ws.deserializeAttachment() || {};
    if (a.tipo === "equipo") {
      if (this.equipoWs() && this.equipoWs() !== ws) return; // ya hay otra conexión
      const info = (await this.ctx.storage.get("info")) || {};
      info.en_linea = false;
      info.hasta = ahora();
      await this.ctx.storage.put("info", info);
      this.aLaWeb({ t: "conexion", en_linea: false, hasta: info.hasta });
      await this.ctx.storage.setAlarm(Date.now() + AVISO_FUERA_S * 1000);
      const id = await this.ctx.storage.get("id");
      await this.env.DB.prepare("UPDATE equipos SET ultimo_contacto = ? WHERE id = ?").bind(info.hasta, id).run();
    } else if (this.webAbiertos(ws).length === 0) {
      this.alEquipo({ t: "vivo", on: false });
    }
  }

  // Revisa cada minuto que el equipo siga vivo; avisa si quedó fuera de línea.
  async alarm() {
    const id = await this.ctx.storage.get("id");
    const info = (await this.ctx.storage.get("info")) || {};
    const w = this.equipoWs();
    if (w) {
      const tel = (await this.ctx.storage.get("tel")) || {};
      const pingTs = this.ctx.getWebSocketAutoResponseTimestamp(w);
      const ultimo = Math.max(tel.rx || 0, info.desde || 0, pingTs ? Math.floor(pingTs.getTime() / 1000) : 0);
      if (ahora() - ultimo > FUERA_DE_LINEA_S) {
        try {
          w.close(4001, "sin datos");
        } catch {}
        await this.alCerrar(w);
        return;
      }
      await this.ctx.storage.setAlarm(Date.now() + 60000);
      return;
    }
    if (!info.aviso_fuera && info.hasta && ahora() - info.hasta >= AVISO_FUERA_S - 5) {
      info.aviso_fuera = true;
      await this.ctx.storage.put("info", info);
      await avisarEquipo(this.env, id, `⚠️ ${id}: el equipo está fuera de línea desde hace ${Math.round((ahora() - info.hasta) / 60)} min.`);
    }
  }

  // ------------------------------------------------------------------ mensajes del equipo
  async hola(ws, id, m) {
    const t = ahora();
    const anterior = (await this.ctx.storage.get("info")) || {};
    const info = {
      en_linea: true,
      desde: t,
      fw: m.fw,
      mac: m.mac,
      reset: m.reset,
      up: m.up || 0,
      upT: t,
      cfgv: m.cfgv || 0,
      aviso_fuera: false,
    };
    await this.ctx.storage.put("info", info);
    if (anterior.aviso_fuera) await avisarEquipo(this.env, id, `✅ ${id}: el equipo volvió a estar en línea.`);

    let seq = (await this.ctx.storage.get("seq")) || 0;
    if (m.seq_max !== undefined && m.seq_max < seq) seq = Math.max(0, (m.seq_min || 1) - 1); // se borró la flash
    ws.send(JSON.stringify({ t: "bienvenida", hora: t, vivo: this.webAbiertos().length > 0, seq }));

    const fila = await this.env.DB.prepare("SELECT config, config_v FROM equipos WHERE id = ?").bind(id).first();
    if (fila && fila.config_v > (m.cfgv || 0)) {
      ws.send(JSON.stringify({ t: "cfg", v: fila.config_v, c: { ...CONFIG_DEFECTO, ...JSON.parse(fila.config || "{}") } }));
    }
    await this.env.DB.prepare("UPDATE equipos SET fw = ?, mac = ?, ultimo_contacto = ? WHERE id = ?")
      .bind(m.fw || null, m.mac || null, t, id)
      .run();
    this.aLaWeb({ t: "conexion", en_linea: true, desde: t, fw: m.fw, reset: m.reset });
  }

  async telemetria(id, m) {
    const t = ahora();
    const tel = { ...m, rx: t };
    delete tel.t;
    await this.ctx.storage.put("tel", tel); // una sola escritura por telemetría (plan gratis: 100 000 filas/día)
    this.aLaWeb({ t: "tel", d: tel });
  }

  async registros(ws, id, m) {
    const filas = [];
    const avisos = [];
    const info = (await this.ctx.storage.get("info")) || {};
    const ultimaTel = (await this.ctx.storage.get("tel")) || {};
    // Referencia de uptime para los registros sin hora: la telemetría más reciente o el «hola».
    const ref = ultimaTel.rx > (info.upT || 0) && ultimaTel.up !== undefined ? { up: ultimaTel.up, upT: ultimaTel.rx } : info;
    const t = ahora();
    const fila = await this.env.DB.prepare("SELECT config FROM equipos WHERE id = ?").bind(id).first();
    const tarifa = Number(JSON.parse(fila?.config || "{}").tarifa ?? CONFIG_DEFECTO.tarifa);
    const db = this.env.DB;
    const eventos = [];
    for (const r of Array.isArray(m.r) ? m.r : []) {
      // Sin hora: ts es el uptime del equipo; se estima con el último uptime conocido.
      let ts = r.ts;
      if (r.sh) ts = ref.upT ? ref.upT - ((ref.up || 0) - r.ts) : t;
      if (!Number.isFinite(ts) || ts < 1600000000 || ts > t + 3600) ts = t;
      if (r.k === "m") {
        filas.push(
          db
            .prepare(
              `INSERT OR REPLACE INTO mediciones (equipo_id, ts, v, i, p, pf, f, es, et, tsn, tam, hum, k1, mot)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
            )
            .bind(id, ts, r.v ?? null, r.i ?? null, r.p ?? null, r.pf ?? null, r.f ?? null, r.es ?? null, r.et ?? null,
              r.tsn ?? null, r.tam ?? null, r.hum ?? null, r.k1 ?? null, r.mot || null),
        );
      } else if (r.k === "e") {
        filas.push(
          db
            .prepare(
              `INSERT OR IGNORE INTO eventos (equipo_id, ts, seq, codigo, nivel, alarma, texto, valor, extra, mot)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
            )
            .bind(id, ts, r.s, r.c || "evento", r.n || 0, r.a || null, r.txt || null, r.val ?? null, r.x ?? null, r.mot || null),
        );
        const ev = { ts, codigo: r.c, nivel: r.n || 0, alarma: r.a, texto: r.txt, valor: r.val, extra: r.x };
        eventos.push(ev);
        // Solo se avisa de lo reciente (no de lo que se acumuló sin internet hace horas).
        if (r.c === "alarma" && r.n >= 2 && t - ts < 900) avisos.push(ev);
      } else if (r.k === "s") {
        const ini = r.ini && r.ini > 1600000000 ? r.ini : ts;
        const fin = r.fin && r.fin > 1600000000 ? r.fin : ts;
        const kwh = Number(r.kwh) || 0;
        filas.push(
          db
            .prepare(
              `INSERT OR REPLACE INTO sesiones_carga (equipo_id, num, inicio, fin, kwh, p_max, tarifa, costo, motivo_fin)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
            )
            .bind(id, r.num, ini, fin, kwh, r.pmax ?? null, tarifa, Math.round(kwh * tarifa), r.mf || null),
        );
      }
    }
    if (filas.length) await db.batch(filas);
    if (Number.isFinite(m.hasta)) await this.ctx.storage.put("seq", m.hasta);
    ws.send(JSON.stringify({ t: "regack", hasta: m.hasta }));
    if (eventos.length) this.aLaWeb({ t: "eventos", eventos });
    for (const ev of avisos) {
      const fecha = new Date(ev.ts * 1000).toLocaleString("es-CO", { timeZone: "America/Bogota" });
      const extra = ev.extra ? ` (${(ev.extra / 10).toFixed(1)})` : "";
      await avisarEquipo(this.env, id, `🚨 ${id}: ${ev.texto || ev.alarma}${extra} · ${fecha}`);
    }
  }

  ack(m) {
    const f = this.pendientes.get(m.id);
    if (f) {
      this.pendientes.delete(m.id);
      f({ ok: !!m.ok, msg: m.msg || "", datos: m.datos });
    }
    this.aLaWeb({ t: "ack", id: m.id, ok: !!m.ok, msg: m.msg });
  }

  async cfgReportada(id, m) {
    await this.ctx.storage.put("cfg_rep", { v: m.v, c: m.c, rx: ahora() });
    // Si el equipo tiene una versión más nueva que la del servidor (por ejemplo, la base se borró), se adopta.
    const fila = await this.env.DB.prepare("SELECT config_v FROM equipos WHERE id = ?").bind(id).first();
    if (fila && m.v > fila.config_v)
      await this.env.DB.prepare("UPDATE equipos SET config = ?, config_v = ? WHERE id = ?").bind(JSON.stringify(m.c), m.v, id).run();
    this.aLaWeb({ t: "cfg", v: m.v, c: m.c });
  }

  // ------------------------------------------------------------------ RPC desde el Worker
  async estado() {
    const [info, tel, cfg_rep, ota] = await Promise.all([
      this.ctx.storage.get("info"),
      this.ctx.storage.get("tel"),
      this.ctx.storage.get("cfg_rep"),
      this.ctx.storage.get("ota"),
    ]);
    const i = info || {};
    const en_linea = !!this.equipoWs() && i.en_linea !== false;
    const t = tel || null;
    return {
      en_linea,
      desde: i.desde || null,
      hasta: en_linea ? null : i.hasta || t?.rx || null,
      fw: i.fw || null,
      reset: i.reset || null,
      tel: t,
      motivo_texto: t?.mot ? TEXTO_MOTIVO[t.mot] || t.mot : "",
      cfg_rep: cfg_rep || null,
      ota: ota || null,
      viendo: this.webAbiertos().length,
    };
  }

  async orden(o, a, usuarioId) {
    const id = await this.ctx.storage.get("id");
    const t = ahora();
    let r;
    if (!this.equipoWs()) {
      r = { ok: false, msg: "El equipo está fuera de línea." };
    } else {
      const oid = crypto.randomUUID().replace(/-/g, "").slice(0, 16);
      r = await new Promise((resolver) => {
        const temporizador = setTimeout(() => {
          this.pendientes.delete(oid);
          resolver({ ok: false, msg: "El equipo no respondió en 10 s." });
        }, ESPERA_ACK_MS);
        this.pendientes.set(oid, (x) => {
          clearTimeout(temporizador);
          resolver(x);
        });
        if (!this.alEquipo({ t: "orden", id: oid, o, a: a || {} })) {
          clearTimeout(temporizador);
          this.pendientes.delete(oid);
          resolver({ ok: false, msg: "No se pudo enviar la orden." });
        }
      });
    }
    if (id)
      await this.env.DB.prepare("INSERT INTO ordenes (equipo_id, usuario_id, ts, orden, args, ok, msg) VALUES (?, ?, ?, ?, ?, ?, ?)")
        .bind(id, usuarioId || null, t, o, a ? JSON.stringify(a) : null, r.ok ? 1 : 0, r.msg || null)
        .run();
    return r;
  }

  async enviarConfig(v, c) {
    return this.alEquipo({ t: "cfg", v, c });
  }
}
