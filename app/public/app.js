// EVSE Monitor · app web (sin dependencias). Rutas con #: #/entrar, #/, #/e/<id>[/historial|/alarmas|/ajustes],
// #/perfil, #/admin. Los datos en vivo llegan por WebSocket desde el Durable Object del equipo.

import { Grafica } from "./grafica.js";

const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const vista = $("#vista");
const app = { usuario: null, ws: null, wsReintento: null, graficas: [], temporizadores: [], equipo: null, estado: null };

// ------------------------------------------------------------------ formato
const nf = {};
const fmt = (v, d = 1) => {
  if (v === null || v === undefined || v === "" || !Number.isFinite(Number(v))) return "—";
  nf[d] ??= new Intl.NumberFormat("es-CO", { minimumFractionDigits: d, maximumFractionDigits: d });
  return nf[d].format(Number(v));
};
const cop = (v) => (Number.isFinite(Number(v)) ? "$ " + fmt(v, 0) : "—");
const fFecha = (ts) =>
  ts ? new Date(ts * 1000).toLocaleString("es-CO", { timeZone: "America/Bogota", dateStyle: "medium", timeStyle: "short" }) : "—";
const fCorta = (ts) =>
  ts
    ? new Date(ts * 1000).toLocaleString("es-CO", { timeZone: "America/Bogota", day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit", hour12: false })
    : "—";
const ahora = () => Math.floor(Date.now() / 1000);
function duracion(s) {
  if (!Number.isFinite(s) || s < 0) return "—";
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60);
  return h ? `${h} h ${m} min` : m ? `${m} min` : `${Math.floor(s)} s`;
}
function hace(ts) {
  if (!ts) return "—";
  const d = ahora() - ts;
  if (d < 60) return "hace un momento";
  if (d < 3600) return `hace ${Math.floor(d / 60)} min`;
  if (d < 86400) return `hace ${Math.floor(d / 3600)} h ${Math.floor((d % 3600) / 60)} min`;
  return `hace ${Math.floor(d / 86400)} días`;
}
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

const ALARMAS = {
  temp_sonda: "Sobretemperatura en la sonda",
  temp_amb: "Sobretemperatura en la placa",
  sonda_falla: "Sonda DS18B20 sin respuesta",
  medidor_falla: "Falla del medidor ATM90E26",
  red_baja: "Tensión de red baja",
  parar: "PARAR pulsado",
  amb_falla: "Sensor de ambiente sin respuesta",
  sin_hora: "Sin hora (sin NTP ni RTC)",
  reinicio: "Reinicio inesperado",
  sin_calibrar: "Medidor sin calibrar",
  temp_aviso: "Sonda cerca del límite de temperatura",
};
const GRAVES = new Set(["temp_sonda", "temp_amb", "sonda_falla", "medidor_falla", "red_baja", "parar", "reinicio"]);
const MOTIVOS = {
  falla: ["mal", "Falla del medidor o de la sonda. Revisa las alarmas."],
  temperatura: ["mal", "Sobretemperatura. Vuelve a cargar sola 5 min después de enfriarse."],
  parar: ["mal", "Se pulsó PARAR. Se libera manteniendo PARAR 3 s en la placa o con el botón de aquí."],
  red: ["mal", "Tensión de red baja. Vuelve sola cuando la red se normaliza durante 1 min."],
  limite: ["aviso", "Se alcanzó el límite de la sesión. «Permitir» empieza otra."],
  horario: ["aviso", "Fuera del horario de carga. Vuelve sola al entrar al horario."],
  app: ["aviso", "Detenida desde la app."],
  arranque: ["aviso", "El equipo acaba de arrancar o espera tu confirmación."],
};
const RESETS = { 1: "encendido", 2: "pin EN", 3: "software", 4: "excepción", 5: "watchdog", 6: "watchdog de tareas", 7: "watchdog", 9: "brownout" };

// ------------------------------------------------------------------ API y avisos
async function api(ruta, { metodo = "GET", datos, crudo } = {}) {
  const op = { method: metodo, headers: {} };
  if (metodo !== "GET") op.headers["x-evse"] = "1";
  if (datos !== undefined) {
    op.headers["content-type"] = "application/json";
    op.body = JSON.stringify(datos);
  }
  if (crudo) {
    op.headers["content-type"] = "application/octet-stream";
    op.body = crudo;
  }
  const r = await fetch(ruta, op);
  let j = {};
  try {
    j = await r.json();
  } catch {}
  if (r.status === 401 && !ruta.startsWith("/api/auth/")) {
    app.usuario = null;
    location.hash = "#/entrar";
    throw new Error(j.error || "Inicia sesión.");
  }
  if (!r.ok) throw new Error(j.error || j.msg || `Error ${r.status}`);
  return j;
}

let avisoT;
function aviso(msg, mal = false) {
  const a = $("#aviso");
  a.textContent = msg;
  a.className = "notif" + (mal ? " mal" : "");
  a.hidden = false;
  clearTimeout(avisoT);
  avisoT = setTimeout(() => (a.hidden = true), mal ? 6000 : 3500);
}

function confirmar(titulo, html, si = "Aceptar", peligro = false) {
  const d = $("#dialogo");
  $("#dialogo-titulo").textContent = titulo;
  $("#dialogo-texto").innerHTML = html;
  $("#dialogo-si").textContent = si;
  $("#dialogo-si").className = "boton" + (peligro ? " peligro" : "");
  $("#dialogo-no").hidden = false;
  d.showModal();
  return new Promise((res) => d.addEventListener("close", () => res(d.returnValue === "si"), { once: true }));
}

function mostrar(titulo, html) {
  const d = $("#dialogo");
  $("#dialogo-titulo").textContent = titulo;
  $("#dialogo-texto").innerHTML = html;
  $("#dialogo-si").textContent = "Listo";
  $("#dialogo-si").className = "boton";
  $("#dialogo-no").hidden = true;
  d.showModal();
}

async function conBoton(boton, f) {
  const texto = boton.textContent;
  boton.disabled = true;
  boton.textContent = "Un momento…";
  try {
    return await f();
  } catch (e) {
    aviso(e.message, true);
  } finally {
    boton.disabled = false;
    boton.textContent = texto;
  }
}

// La clave se deriva aquí (PBKDF2-SHA256, 300 000 iteraciones); al servidor solo llega el resultado.
async function derivar(email, clave) {
  const enc = new TextEncoder();
  const k = await crypto.subtle.importKey("raw", enc.encode(clave), "PBKDF2", false, ["deriveBits"]);
  const bits = await crypto.subtle.deriveBits(
    { name: "PBKDF2", hash: "SHA-256", salt: enc.encode("evse-monitor|" + email.trim().toLowerCase()), iterations: 300000 },
    k,
    256,
  );
  return [...new Uint8Array(bits)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

// ------------------------------------------------------------------ navegación
function limpiar() {
  if (app.ws) {
    app.ws.onclose = null;
    app.ws.close();
    app.ws = null;
  }
  clearTimeout(app.wsReintento);
  app.graficas.forEach((g) => g.destruir());
  app.graficas = [];
  app.temporizadores.forEach(clearInterval);
  app.temporizadores = [];
}

function pestanas(id, activa) {
  const n = $("#pestanas");
  n.hidden = !id;
  if (!id) return;
  for (const a of $$("a", n)) {
    const p = a.dataset.p;
    a.href = p === "panel" ? `#/e/${id}` : `#/e/${id}/${p}`;
    a.classList.toggle("activa", p === activa);
  }
}

async function navegar() {
  limpiar();
  const h = location.hash || "#/";
  if (!app.usuario && h !== "#/entrar") {
    try {
      const r = await api("/api/auth/estado", { metodo: "POST", datos: {} });
      app.usuario = r.usuario;
    } catch {}
    if (!app.usuario) {
      location.hash = "#/entrar";
      return;
    }
  }
  $("#menu-usuario").hidden = !app.usuario;
  if (app.usuario) $("#nombre-usuario").textContent = app.usuario.nombre;
  window.scrollTo(0, 0);
  try {
    let m;
    if (h === "#/entrar") return await vEntrar();
    if (h === "#/perfil") return pestanas(null), await vPerfil();
    if (h === "#/admin") return pestanas(null), await vAdmin();
    if ((m = /^#\/e\/([a-z0-9-]+)(?:\/(historial|alarmas|ajustes))?$/.exec(h))) {
      const p = m[2] || "panel";
      pestanas(m[1], p);
      if (p === "panel") return await vPanel(m[1]);
      if (p === "historial") return await vHistorial(m[1]);
      if (p === "alarmas") return await vAlarmas(m[1]);
      return await vAjustes(m[1]);
    }
    pestanas(null);
    return await vInicio();
  } catch (e) {
    vista.innerHTML = `<div class="tarjeta"><h2>No se pudo cargar</h2><p class="error">${esc(e.message)}</p><a href="#/">Volver al inicio</a></div>`;
  }
}
window.addEventListener("hashchange", navegar);
navegar();

// ------------------------------------------------------------------ entrar
async function vEntrar() {
  pestanas(null);
  $("#menu-usuario").hidden = true;
  const est = await api("/api/auth/estado", { metodo: "POST", datos: {} });
  if (est.usuario) {
    app.usuario = est.usuario;
    location.hash = "#/";
    return;
  }
  const primero = !est.hay_usuarios;
  vista.innerHTML = `
    <div class="centro tarjeta">
      <h1>${primero ? "Crear el administrador" : "Entrar"}</h1>
      <p class="suave">${primero ? "No hay usuarios todavía. El primero es el administrador y necesita el código de instalación (CODIGO_INICIAL)." : "Monitor y control de la carga del vehículo."}</p>
      <form id="f">
        ${primero ? `<label for="nombre">Nombre</label><input id="nombre" required autocomplete="name">` : ""}
        <label for="email">Correo</label><input id="email" type="email" required autocomplete="username">
        <label for="clave">Clave</label><input id="clave" type="password" required minlength="${primero ? 10 : 1}" autocomplete="${primero ? "new-password" : "current-password"}">
        ${primero ? `<p class="ayuda">Mínimo 10 caracteres.</p><label for="codigo">Código de instalación</label><input id="codigo" required>` : ""}
        <p class="error" id="err" hidden></p>
        <button class="boton ancho" style="margin-top:1rem">${primero ? "Crear y entrar" : "Entrar"}</button>
      </form>
    </div>`;
  $("#f").onsubmit = async (e) => {
    e.preventDefault();
    const b = $("button", e.target);
    const err = $("#err");
    err.hidden = true;
    await conBoton(b, async () => {
      const email = $("#email").value.trim();
      const clave = await derivar(email, $("#clave").value);
      try {
        if (primero) await api("/api/auth/registro", { metodo: "POST", datos: { email, clave, nombre: $("#nombre").value, codigo: $("#codigo").value } });
        else await api("/api/auth/entrar", { metodo: "POST", datos: { email, clave } });
      } catch (x) {
        err.textContent = x.message;
        err.hidden = false;
        return;
      }
      app.usuario = (await api("/api/auth/yo")).usuario;
      location.hash = "#/";
    });
  };
}

// ------------------------------------------------------------------ inicio: lista de equipos
function resumenEstado(est) {
  if (!est || !est.tel) return { clase: "", texto: "Sin datos todavía" };
  const t = est.tel;
  if (!est.en_linea) return { clase: "", texto: `Fuera de línea · ${hace(est.hasta)}` };
  if (t.k1 && t.i >= 1) return { clase: "ok", texto: `Cargando · ${fmt(t.p / 1000, 2)} kW` };
  if (t.k1) return { clase: "ok", texto: "Carga permitida · sin consumo" };
  return { clase: (MOTIVOS[t.mot] || ["aviso"])[0], texto: `Detenida · ${est.motivo_texto || t.mot}` };
}

async function vInicio() {
  const { equipos } = await api("/api/equipos");
  if (equipos.length === 1 && !app.usuario.admin) {
    location.hash = `#/e/${equipos[0].id}`;
    return;
  }
  vista.innerHTML = `
    <div class="cabecera"><h1>Equipos</h1>${app.usuario.admin ? `<a class="boton chico" href="#/admin">Administrar</a>` : ""}</div>
    ${equipos.length ? "" : `<div class="tarjeta"><p>No tienes equipos todavía.</p>${app.usuario.admin ? `<a class="boton" href="#/admin">Agregar el primer equipo</a>` : "<p class='suave'>Pídele acceso al administrador.</p>"}</div>`}
    ${equipos
      .map((e) => {
        const r = resumenEstado(e.estado);
        return `<a class="tarjeta equipo" href="#/e/${e.id}">
          <div class="cabecera" style="margin:0"><div><h2 style="margin:0">${esc(e.nombre)}</h2><small>${esc(e.id)} · firmware ${esc(e.estado?.fw || e.fw || "—")}</small></div>
          <span class="chip ${e.estado?.en_linea ? "ok" : ""}">${e.estado?.en_linea ? "En línea" : "Fuera de línea"}</span></div>
          <p style="margin:.6rem 0 0" class="${r.clase === "mal" ? "error" : ""}">${esc(r.texto)}</p></a>`;
      })
      .join("")}`;
}

// ------------------------------------------------------------------ panel en vivo
const MEDIDAS = [
  ["p", "Potencia", "kW", (t) => fmt(t.p / 1000, 2), "destacada"],
  ["v", "Tensión", "V", (t) => fmt(t.v, 1)],
  ["i", "Corriente", "A", (t) => fmt(t.i, 2)],
  ["pf", "Factor de potencia", "", (t) => fmt(t.pf, 2)],
  ["f", "Frecuencia", "Hz", (t) => fmt(t.f, 2)],
  ["es", "Energía de la sesión", "kWh", (t) => fmt(t.es, 2), "", (t, c) => (t.ses ? cop(t.es * (c?.tarifa || 0)) : "sin sesión abierta")],
  ["dur", "Duración de la sesión", "", (t) => (t.ses ? duracion(t.dur) : "—"), "", (t) => (t.ses ? `sesión nº ${t.ses}` : "")],
  ["et", "Energía total", "kWh", (t) => fmt(t.et, 1)],
  ["tsn", "Sonda (conector)", "°C", (t) => fmt(t.tsn, 1), "", (t, c) => `corte a ${fmt(c?.tmax_sonda, 0)} °C`],
  ["tam", "Placa", "°C", (t) => fmt(t.tam, 1), "", (t, c) => `corte a ${fmt(c?.tmax_amb, 0)} °C`],
  ["hum", "Humedad", "%HR", (t) => fmt(t.hum, 0)],
  ["rssi", "WiFi", "dBm", (t) => fmt(t.rssi, 0), "", (t) => (t.pend ? `${t.pend} registros por subir` : "historial al día")],
];

async function vPanel(id) {
  const r = await api(`/api/equipos/${id}`);
  app.equipo = r.equipo;
  app.rol = r.rol;
  app.estado = r.estado;
  vista.innerHTML = `
    <div class="cabecera">
      <div><h1>${esc(r.equipo.nombre)}</h1><small id="sub"></small></div>
      <span class="chip" id="chip-linea"></span>
    </div>
    <section class="estado gris" id="estado"><div class="titulo">…</div></section>
    <div id="alarmas"></div>
    <div class="medidas">
      ${MEDIDAS.map(([k, et, u, , cl]) => `<div class="medida ${cl || ""}" data-k="${k}"><div class="etiqueta">${et}</div><div class="valor"><span class="x">—</span><span class="u">${u}</span></div><div class="sub"></div></div>`).join("")}
    </div>
    <div class="tarjeta"><h2>Potencia · última media hora</h2><div id="g-vivo"></div></div>
    <p class="suave" id="pie" style="font-size:.85rem"></p>`;
  const g = new Grafica($("#g-vivo"), {
    alto: 200,
    cero: true,
    hueco: 120,
    series: [{ nombre: "Potencia", color: "#2f6fec", unidad: "kW", dec: 2, relleno: true }],
    vacio: "Sin datos de la última media hora",
  });
  app.graficas.push(g);
  const t = ahora();
  api(`/api/equipos/${id}/mediciones?desde=${t - 1800}&hasta=${t}&max=200`)
    .then((m) => g.datos([m.puntos.map((p) => [p.ts, p.p / 1000])]))
    .catch(() => {});
  app.grafVivo = g;
  pintarPanel();
  conectarWs(id);
  app.temporizadores.push(setInterval(pintarPanel, 30000)); // «hace X min» al día
}

function pintarPanel() {
  const est = app.estado;
  const t = est?.tel || {};
  const c = app.equipo?.config;
  if (!$("#estado")) return;
  $("#chip-linea").className = "chip " + (est?.en_linea ? "ok" : "");
  $("#chip-linea").textContent = est?.en_linea ? "En línea" : "Fuera de línea";
  $("#sub").textContent = `${app.equipo.id} · firmware ${est?.fw || app.equipo.fw || "—"}`;

  // estado de la carga
  const caja = $("#estado");
  let clase, titulo, detalle;
  if (!est?.tel) {
    [clase, titulo, detalle] = ["gris", "Sin datos todavía", "El equipo no se ha conectado nunca. Revisa la guía de instalación."];
  } else if (t.k1) {
    clase = "ok";
    titulo = t.i >= (c?.i_inicio || 1) ? `Cargando · ${fmt(t.p / 1000, 2)} kW` : "Carga permitida";
    detalle = t.i >= (c?.i_inicio || 1) ? `${fmt(t.i, 1)} A a ${fmt(t.v, 0)} V` : "El vehículo no está tomando corriente.";
  } else {
    const [cl, txt] = MOTIVOS[t.mot] || ["aviso", t.mot];
    clase = cl;
    titulo = "Carga detenida";
    detalle = txt;
  }
  if (est?.tel && !est.en_linea) {
    clase = "gris";
    detalle = `Fuera de línea ${hace(est.hasta)}. Último estado: ${titulo.toLowerCase()}.`;
    titulo = "Equipo fuera de línea";
  }
  const puede = app.rol === "propietario" && est?.en_linea;
  const al = t.al || [];
  const nr = t.nr || [];
  const botones = [];
  if (puede) {
    // «Permitir» también cuando el permiso sigue pero la carga espera (límite alcanzado o arranque).
    const espera = !t.k1 && ["limite", "arranque"].includes(t.mot);
    if (t.perm && !espera) botones.push(`<button class="boton peligro" data-o="detener">Detener carga</button>`);
    else botones.push(`<button class="boton verde" data-o="permitir">${t.mot === "limite" ? "Permitir (nueva sesión)" : "Permitir carga"}</button>`);
    if (al.includes("parar")) botones.push(`<button class="boton secundario" data-o="soltar_parar">Liberar PARAR</button>`);
    if (nr.length) botones.push(`<button class="boton secundario" data-o="reconocer">Reconocer alarmas (${nr.length})</button>`);
  }
  caja.className = "estado " + clase;
  caja.innerHTML = `<div><div class="titulo">${esc(titulo)}</div><div class="detalle">${esc(detalle)}</div></div>${botones.length ? `<div class="acciones">${botones.join("")}</div>` : ""}`;
  for (const b of $$("button[data-o]", caja)) b.onclick = () => ordenPanel(b);

  // alarmas activas
  const activas = al.filter((a) => a !== "sin_calibrar" || app.usuario.admin);
  $("#alarmas").innerHTML = activas.length
    ? `<div class="tarjeta"><h2>Alarmas activas</h2><ul class="lista">${activas
        .map((a) => `<li><span class="punto ${GRAVES.has(a) ? "n2" : "n1"}"></span><div>${esc(ALARMAS[a] || a)}${nr.includes(a) ? ' <span class="chip mal">sin reconocer</span>' : ""}</div></li>`)
        .join("")}</ul></div>`
    : "";

  // medidas
  for (const [k, , , f, , sub] of MEDIDAS) {
    const el = $(`.medida[data-k="${k}"]`);
    if (!el) continue;
    $(".x", el).textContent = est?.tel ? f(t) : "—";
    $(".sub", el).textContent = est?.tel && sub ? sub(t, c) : "";
    el.style.opacity = est?.en_linea ? 1 : 0.6;
  }
  $('.medida[data-k="tsn"]')?.classList.toggle("alerta", al.includes("temp_sonda") || al.includes("temp_aviso"));
  $('.medida[data-k="tam"]')?.classList.toggle("alerta", al.includes("temp_amb"));
  $("#pie").textContent = est?.tel
    ? `Último dato ${hace(est.tel.rx)} (${fFecha(est.tel.rx)}) · equipo encendido hace ${duracion(t.up)}${est.viendo > 1 ? ` · ${est.viendo} personas viendo` : ""}`
    : "";
}

async function ordenPanel(b) {
  const o = b.dataset.o;
  const textos = {
    detener: ["¿Detener la carga?", "K1 abre los bornes de habilitación (J2) y el EVSE deja de cargar.", "Detener", true],
    permitir: ["¿Permitir la carga?", "K1 cierra J2 y el EVSE puede cargar, si nada más lo impide (horario, temperatura, PARAR…).", "Permitir", false],
    soltar_parar: ["¿Liberar PARAR?", "Alguien pulsó PARAR en la placa o en el botón del panel. Libéralo solo si sabes por qué se pulsó.", "Liberar", true],
    reconocer: ["¿Reconocer las alarmas?", "Las alarmas quedan marcadas como vistas. Si la causa sigue, siguen activas.", "Reconocer", false],
  }[o];
  if (!(await confirmar(textos[0], `<p>${textos[1]}</p>`, textos[2], textos[3]))) return;
  await conBoton(b, async () => {
    const r = await api(`/api/equipos/${app.equipo.id}/orden`, { metodo: "POST", datos: { o } });
    aviso(r.msg || "Hecho");
  });
}

function conectarWs(id) {
  const url = `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/api/equipos/${id}/ws`;
  const ws = new WebSocket(url);
  app.ws = ws;
  ws.onmessage = (ev) => {
    let m;
    try {
      m = JSON.parse(ev.data);
    } catch {
      return;
    }
    if (m.t === "estado") {
      delete m.t;
      app.estado = m;
    } else if (m.t === "tel") {
      app.estado = { ...app.estado, tel: m.d, en_linea: true };
      if (app.grafVivo && Number.isFinite(m.d.p)) app.grafVivo.agregar(m.d.rx, [m.d.p / 1000], 1800);
    } else if (m.t === "conexion") {
      app.estado = { ...app.estado, en_linea: m.en_linea, hasta: m.hasta || null, fw: m.fw || app.estado?.fw };
    } else if (m.t === "eventos") {
      for (const e of m.eventos) if (e.codigo === "alarma" && e.nivel >= 2) aviso(`Alarma: ${e.texto || e.alarma}`, true);
    } else if (m.t === "cfg") {
      app.estado = { ...app.estado, cfg_rep: { v: m.v, c: m.c } };
    } else if (m.t === "ota") {
      aviso(`OTA: ${m.fase} ${m.pct ?? ""}% ${m.msg || ""}`, m.fase === "error");
    }
    pintarPanel();
  };
  ws.onclose = () => {
    app.wsReintento = setTimeout(() => {
      if (location.hash.startsWith(`#/e/${id}`) && !/historial|alarmas|ajustes/.test(location.hash)) conectarWs(id);
    }, 4000);
  };
}

// ------------------------------------------------------------------ historial
async function vHistorial(id) {
  const r = await api(`/api/equipos/${id}`);
  app.equipo = r.equipo;
  vista.innerHTML = `
    <div class="cabecera"><div><h1>Historial</h1><small>${esc(r.equipo.nombre)}</small></div>
      <div class="segmentos" id="rango"><button data-d="1" class="activo">24 h</button><button data-d="7">7 días</button><button data-d="30">30 días</button><button data-d="365">1 año</button></div></div>
    <div class="tarjeta"><h2>Potencia</h2><div class="leyenda"><span style="--c:#2f6fec">promedio (kW)</span><span style="--c:#9db6f2">máxima (kW)</span></div><div id="g-p"></div></div>
    <div class="tarjeta"><h2>Tensión y corriente</h2><div class="leyenda"><span style="--c:#d97706">tensión (V)</span></div><div id="g-v"></div>
      <div class="leyenda" style="margin-top:.6rem"><span style="--c:#059669">corriente (A)</span></div><div id="g-i"></div></div>
    <div class="tarjeta"><h2>Temperatura</h2><div class="leyenda"><span style="--c:#dc2626">sonda (°C)</span><span style="--c:#7c3aed">placa (°C)</span></div><div id="g-t"></div></div>
    <div class="tarjeta"><div class="cabecera"><h2 style="margin:0">Sesiones de carga</h2><div><a class="boton chico secundario" id="csv-s">CSV sesiones</a> <a class="boton chico secundario" id="csv-m">CSV mediciones</a></div></div>
      <div id="totales" class="medidas"></div><div class="desliza" id="sesiones"></div></div>`;
  const gp = new Grafica($("#g-p"), { cero: true, series: [{ nombre: "Máxima", color: "#9db6f2", unidad: "kW", dec: 2 }, { nombre: "Promedio", color: "#2f6fec", unidad: "kW", dec: 2, relleno: true }] });
  const gv = new Grafica($("#g-v"), { alto: 170, series: [{ nombre: "Tensión", color: "#d97706", unidad: "V", dec: 1 }] });
  const gi = new Grafica($("#g-i"), { alto: 170, cero: true, series: [{ nombre: "Corriente", color: "#059669", unidad: "A", dec: 2 }] });
  const gt = new Grafica($("#g-t"), { series: [{ nombre: "Sonda", color: "#dc2626", unidad: "°C", dec: 1 }, { nombre: "Placa", color: "#7c3aed", unidad: "°C", dec: 1 }] });
  app.graficas.push(gp, gv, gi, gt);

  async function cargar(dias) {
    const hasta = ahora(), desde = hasta - dias * 86400;
    $("#csv-s").href = `/api/equipos/${id}/sesiones.csv?desde=${desde}&hasta=${hasta}`;
    $("#csv-m").href = `/api/equipos/${id}/mediciones.csv?desde=${desde}&hasta=${hasta}`;
    const [m, s] = await Promise.all([
      api(`/api/equipos/${id}/mediciones?desde=${desde}&hasta=${hasta}&max=500`),
      api(`/api/equipos/${id}/sesiones?desde=${desde}&hasta=${hasta}`),
    ]);
    const P = m.puntos;
    const hueco = Math.max(m.paso * 3, 900);
    for (const g of [gp, gv, gi, gt]) g.op.hueco = hueco;
    gp.datos([P.map((p) => [p.ts, p.pmax / 1000]), P.map((p) => [p.ts, p.p / 1000])]);
    gv.datos([P.map((p) => [p.ts, p.v])]);
    gi.datos([P.map((p) => [p.ts, p.i])]);
    gt.datos([P.map((p) => [p.ts, p.tsn]), P.map((p) => [p.ts, p.tam])]);
    const ses = s.sesiones;
    const kwh = ses.reduce((a, x) => a + (x.kwh || 0), 0);
    const costo = ses.reduce((a, x) => a + (x.costo || 0), 0);
    const seg = ses.reduce((a, x) => a + (x.fin ? x.fin - x.inicio : 0), 0);
    $("#totales").innerHTML = [
      ["Sesiones", fmt(ses.length, 0), ""],
      ["Energía", fmt(kwh, 1), "kWh"],
      ["Costo", cop(costo), ""],
      ["Tiempo", duracion(seg), ""],
    ].map(([e, v, u]) => `<div class="medida"><div class="etiqueta">${e}</div><div class="valor">${v}<span class="u">${u}</span></div></div>`).join("");
    const fin = { sin_corriente: "terminó la carga", limite: "límite", otro: "—" };
    $("#sesiones").innerHTML = ses.length
      ? `<table class="tabla"><thead><tr><th>Inicio</th><th class="n">Duración</th><th class="n">kWh</th><th class="n">Costo</th><th class="n">P máx</th><th>Fin</th></tr></thead><tbody>${ses
          .map((x) => `<tr><td>${fCorta(x.inicio)}</td><td class="n">${duracion(x.fin - x.inicio)}</td><td class="n">${fmt(x.kwh, 2)}</td><td class="n">${cop(x.costo)}</td><td class="n">${fmt((x.p_max || 0) / 1000, 1)} kW</td><td>${esc(fin[x.motivo_fin] || x.motivo_fin || "")}</td></tr>`)
          .join("")}</tbody></table>`
      : `<p class="suave">No hay sesiones en este rango.</p>`;
  }
  for (const b of $$("#rango button"))
    b.onclick = () => {
      $$("#rango button").forEach((x) => x.classList.toggle("activo", x === b));
      cargar(Number(b.dataset.d)).catch((e) => aviso(e.message, true));
    };
  await cargar(1);
}

// ------------------------------------------------------------------ alarmas y eventos
function textoEvento(e) {
  switch (e.codigo) {
    case "alarma": {
      // extra = medida × 10 (°C de la sonda o la placa, o V de la red), como lo guarda el firmware
      const u = { temp_sonda: "°C", temp_aviso: "°C", temp_amb: "°C", red_baja: "V" }[e.alarma];
      return (e.texto || ALARMAS[e.alarma] || e.alarma) + (u && e.extra ? ` · ${fmt(e.extra / 10, 1)} ${u}` : "");
    }
    case "alarma_fin": return `Se despejó: ${e.texto || ALARMAS[e.alarma] || e.alarma}`;
    case "arranque": return `Arranque del equipo (${RESETS[e.valor] || "motivo " + e.valor})${e.extra ? ` · ${e.extra} reinicios seguidos` : ""}`;
    case "k1": return e.valor ? "K1 cerrado: carga permitida" : `K1 abierto: carga detenida (${(MOTIVOS[e.mot] || [, e.mot])[1] || e.mot})`;
    case "sesion_inicio": return `Empezó la sesión nº ${fmt(e.valor, 0)}`;
    case "limite": return `Límite de la sesión alcanzado (${["", "kWh", "tiempo", "costo"][e.valor] || ""})`;
    case "config": return `Configuración v${fmt(e.valor, 0)} aplicada en el equipo`;
    case "calibracion": return "Calibración del medidor cambiada";
    case "orden_local": return ["", "PARAR pulsado", "PARAR liberado en la placa", "PARAR liberado desde la app"][e.valor] || "Orden local";
    case "hora": return "Hora puesta por NTP y copiada al DS3231";
    case "ota": return "Actualización de firmware";
    default: return e.codigo;
  }
}

async function vAlarmas(id) {
  const r = await api(`/api/equipos/${id}`);
  app.equipo = r.equipo;
  vista.innerHTML = `
    <div class="cabecera"><div><h1>Alarmas y eventos</h1><small>${esc(r.equipo.nombre)}</small></div>
      ${r.rol === "propietario" ? `<button class="boton chico secundario" id="reconocer">Reconocer todas</button>` : ""}</div>
    <div class="tarjeta"><div class="segmentos" id="filtro" style="margin-bottom:.6rem"><button data-n="1" class="activo">Alarmas y avisos</button><button data-n="0">Todos los eventos</button></div>
      <ul class="lista" id="eventos"></ul></div>
    <div class="tarjeta"><h2>Órdenes recientes</h2><div class="desliza" id="ordenes"></div></div>`;
  async function cargar(nivel) {
    const { eventos } = await api(`/api/equipos/${id}/eventos?nivel=${nivel}&desde=${ahora() - 90 * 86400}`);
    $("#eventos").innerHTML = eventos.length
      ? eventos
          .map((e) => `<li><span class="punto n${e.nivel}"></span><div><div>${esc(textoEvento(e))}${e.nivel >= 1 && !e.reconocido && e.codigo === "alarma" ? ' <span class="chip mal">sin reconocer</span>' : ""}</div><small>${fFecha(e.ts)}</small></div></li>`)
          .join("")
      : `<li class="suave">Nada en los últimos 90 días.</li>`;
  }
  for (const b of $$("#filtro button"))
    b.onclick = () => {
      $$("#filtro button").forEach((x) => x.classList.toggle("activo", x === b));
      cargar(Number(b.dataset.n));
    };
  if ($("#reconocer"))
    $("#reconocer").onclick = (e) =>
      conBoton(e.target, async () => {
        const x = await api(`/api/equipos/${id}/orden`, { metodo: "POST", datos: { o: "reconocer" } });
        aviso(x.msg);
        cargar(1);
      });
  await cargar(1);
  const { ordenes } = await api(`/api/equipos/${id}/ordenes`);
  $("#ordenes").innerHTML = ordenes.length
    ? `<table class="tabla"><thead><tr><th>Fecha</th><th>Quién</th><th>Orden</th><th>Resultado</th></tr></thead><tbody>${ordenes
        .map((o) => `<tr><td>${fCorta(o.ts)}</td><td>${esc(o.nombre || "—")}</td><td>${esc(o.orden)}</td><td>${o.ok ? "✓" : "✗"} ${esc(o.msg || "")}</td></tr>`)
        .join("")}</tbody></table>`
    : `<p class="suave">Todavía no hay órdenes.</p>`;
}

// ------------------------------------------------------------------ ajustes
const DIAS = ["D", "L", "M", "X", "J", "V", "S"]; // bit 0 = domingo

function htmlVentana(w, k) {
  return `<div class="ventana" data-k="${k}">
    <div class="dias">${DIAS.map((d, b) => `<label><input type="checkbox" data-b="${b}" ${w.d >> b & 1 ? "checked" : ""}>${d}</label>`).join("")}</div>
    <div class="fila"><div><label>Desde</label><input type="time" class="vi" value="${w.i}"></div><div><label>Hasta</label><input type="time" class="vf" value="${w.f}"></div></div>
    <button type="button" class="boton chico secundario quitar" style="margin-top:.5rem">Quitar</button></div>`;
}

async function vAjustes(id) {
  const r = await api(`/api/equipos/${id}`);
  app.equipo = r.equipo;
  const c = r.equipo.config;
  const prop = r.rol === "propietario";
  const admin = app.usuario.admin;
  const rep = r.estado?.cfg_rep;
  const dis = prop ? "" : "disabled";
  vista.innerHTML = `
    <div class="cabecera"><div><h1>Ajustes</h1><small>${esc(r.equipo.nombre)} · configuración v${r.equipo.config_v}${rep ? (rep.v >= r.equipo.config_v ? " · aplicada en el equipo" : ` · el equipo tiene la v${rep.v}`) : ""}</small></div></div>
    <form id="f-cfg">
      <div class="tarjeta"><h2>General</h2>
        <label>Nombre</label><input id="nombre" value="${esc(r.equipo.nombre)}" ${dis}>
        <div class="fila">
          <div><label>Tensión nominal</label><select id="vnom" ${dis}><option value="120">120 V (L–N)</option><option value="240">240 V (L1–L2)</option></select></div>
          <div><label>Tarifa (COP/kWh)</label><input id="tarifa" type="number" min="0" step="1" value="${c.tarifa}" ${dis}></div>
        </div>
        <p class="ayuda">Zona horaria: America/Bogota (UTC−5).</p>
      </div>
      <div class="tarjeta"><h2>Límites por sesión</h2><p class="ayuda">0 = sin límite. Al llegar, el equipo detiene la carga y cierra la sesión.</p>
        <div class="fila3">
          <div><label>Energía (kWh)</label><input id="lim_kwh" type="number" min="0" step="0.1" value="${c.lim_kwh}" ${dis}></div>
          <div><label>Tiempo (min)</label><input id="lim_min" type="number" min="0" step="1" value="${c.lim_min}" ${dis}></div>
          <div><label>Costo (COP)</label><input id="lim_cop" type="number" min="0" step="100" value="${c.lim_cop}" ${dis}></div>
        </div></div>
      <div class="tarjeta"><h2>Horario de carga</h2>
        <label class="opcion"><input type="checkbox" id="h_on" ${c.horario.on ? "checked" : ""} ${dis}>Cargar solo dentro de estas franjas</label>
        <p class="ayuda">Hasta 4 franjas. Si «hasta» es menor que «desde», la franja cruza la medianoche (p. ej. 22:00–05:00). Sin hora válida, el equipo no aplica el horario.</p>
        <div id="ventanas">${c.horario.v.map(htmlVentana).join("")}</div>
        ${prop ? `<button type="button" class="boton chico secundario" id="mas">Agregar franja</button>` : ""}
      </div>
      <div class="tarjeta"><h2>Temperatura</h2><p class="ayuda">Las aplica el equipo aunque no haya internet.</p>
        <div class="fila3">
          <div><label>Corte sonda (°C)</label><input id="tmax_sonda" type="number" min="30" max="90" step="1" value="${c.tmax_sonda}" ${dis}></div>
          <div><label>Corte placa (°C)</label><input id="tmax_amb" type="number" min="30" max="85" step="1" value="${c.tmax_amb}" ${dis}></div>
          <div><label>Histéresis (°C)</label><input id="t_hist" type="number" min="2" max="30" step="1" value="${c.t_hist}" ${dis}></div>
        </div>
        <label class="opcion"><input type="checkbox" id="sonda_req" ${c.sonda_req ? "checked" : ""} ${dis}>Sonda obligatoria: sin sonda, la carga se detiene por falla</label>
      </div>
      <div class="tarjeta"><h2>Al volver la energía</h2>
        <p class="ayuda">Con el AQY214EHAX (normalmente abierto), sin energía el EVSE no carga. Esto decide qué hace el equipo cuando vuelve la luz o después de un reinicio:</p>
        <label class="opcion"><input type="radio" name="arranque" value="restaurar" ${dis}><span><b>Restaurar</b> el último estado después de 10 s de verificaciones (recomendado).</span></label>
        <label class="opcion"><input type="radio" name="arranque" value="detenida" ${dis}><span><b>Quedar detenida</b> hasta que alguien la permita desde la app.</span></label>
        <label class="opcion"><input type="radio" name="arranque" value="permitida" ${dis}><span><b>Permitir siempre</b> después de las verificaciones.</span></label>
        <p class="ayuda">En cualquier caso, tres reinicios anormales seguidos en menos de 10 min dejan la carga detenida hasta reconocer la alarma.</p>
      </div>
      <details class="tarjeta"><summary><b>Avanzado</b></summary>
        <div class="fila"><div><label>Corriente de inicio de sesión (A)</label><input id="i_inicio" type="number" min="0.2" max="10" step="0.1" value="${c.i_inicio}" ${dis}></div>
          <div><label>Fin de sesión sin corriente (min)</label><input id="fin_min" type="number" min="1" max="240" value="${c.fin_min}" ${dis}></div></div>
        <div class="fila3"><div><label>Telemetría (s)</label><input id="tel_s" type="number" min="5" max="300" value="${c.tel_s}" ${dis}></div>
          <div><label>Historial cargando (s)</label><input id="reg_carga_s" type="number" min="10" max="600" value="${c.reg_carga_s}" ${dis}></div>
          <div><label>Historial en reposo (s)</label><input id="reg_reposo_s" type="number" min="60" max="3600" value="${c.reg_reposo_s}" ${dis}></div></div>
        <label class="opcion"><input type="checkbox" id="inv_ct" ${c.inv_ct ? "checked" : ""} ${dis}>El CT quedó al revés (invierte el signo de la potencia)</label>
      </details>
      ${prop ? `<button class="boton ancho">Guardar configuración</button>` : `<p class="suave">Tu usuario es de solo lectura.</p>`}
    </form>
    ${admin ? htmlAdminEquipo(r) : ""}`;
  $("#vnom").value = String(c.vnom);
  for (const x of $$('input[name="arranque"]')) x.checked = x.value === c.arranque;
  const ventanas = $("#ventanas");
  const enlazar = () => $$(".quitar", ventanas).forEach((b) => (b.onclick = () => b.closest(".ventana").remove()));
  enlazar();
  if ($("#mas"))
    $("#mas").onclick = () => {
      if ($$(".ventana", ventanas).length >= 4) return aviso("Máximo 4 franjas.", true);
      ventanas.insertAdjacentHTML("beforeend", htmlVentana({ d: 127, i: "22:00", f: "05:00" }, 0));
      enlazar();
    };
  $("#f-cfg").onsubmit = async (e) => {
    e.preventDefault();
    const n = (k) => Number($("#" + k).value);
    const config = {
      vnom: n("vnom"), tarifa: n("tarifa"), tz: -300, lim_kwh: n("lim_kwh"), lim_min: n("lim_min"), lim_cop: n("lim_cop"),
      horario: {
        on: $("#h_on").checked,
        v: $$(".ventana", ventanas).map((w) => ({
          d: $$("input[data-b]", w).reduce((a, x) => a | (x.checked ? 1 << Number(x.dataset.b) : 0), 0),
          i: $(".vi", w).value || "00:00",
          f: $(".vf", w).value || "00:00",
        })),
      },
      tmax_sonda: n("tmax_sonda"), tmax_amb: n("tmax_amb"), t_hist: n("t_hist"), sonda_req: $("#sonda_req").checked,
      arranque: $('input[name="arranque"]:checked')?.value || "restaurar",
      i_inicio: n("i_inicio"), fin_min: n("fin_min"), inv_ct: $("#inv_ct").checked, tel_s: n("tel_s"), reg_carga_s: n("reg_carga_s"), reg_reposo_s: n("reg_reposo_s"),
    };
    if (config.horario.on && !config.horario.v.length) return aviso("Agrega al menos una franja o apaga el horario.", true);
    await conBoton($("button.ancho", e.target), async () => {
      if ($("#nombre").value.trim() !== r.equipo.nombre) await api(`/api/equipos/${id}`, { metodo: "PUT", datos: { nombre: $("#nombre").value } });
      const x = await api(`/api/equipos/${id}/config`, { metodo: "PUT", datos: { config } });
      aviso(x.enviada ? `Guardada (v${x.v}) y enviada al equipo.` : `Guardada (v${x.v}). Se aplica cuando el equipo se conecte.`);
    });
  };
  if (admin) enlazarAdminEquipo(id, r);
}

function htmlAdminEquipo(r) {
  return `
    <div class="tarjeta"><h2>Calibración del medidor</h2>
      <p class="ayuda">Solo en S7, con el transformador de aislamiento, una carga resistiva conocida y una pinza de referencia (docs/pruebas/PROTOCOLO_PRUEBAS.md). El equipo ajusta Ugain e IgainN en proporción a tu referencia.</p>
      <button class="boton chico secundario" id="cal-leer">Leer del equipo</button>
      <pre class="consola" id="cal-datos" hidden></pre>
      <div class="fila"><div><label>Tensión de referencia (V)</label><input id="cal-v" type="number" step="0.01" placeholder="p. ej. 120.4"></div>
        <div><label>Corriente de referencia (A)</label><input id="cal-i" type="number" step="0.001" placeholder="p. ej. 9.87"></div></div>
      <p class="ayuda">Deja en blanco la que no quieras tocar. La corriente necesita ≥ 0,5 A pasando por el CT.</p>
      <div class="acciones" style="display:flex;gap:.5rem;flex-wrap:wrap;margin-top:.6rem">
        <button class="boton chico" id="cal-auto">Calibrar</button><button class="boton chico secundario" id="cal-fab">Valores de fábrica</button></div>
    </div>
    <div class="tarjeta"><h2>Firmware</h2>
      <p>Versión instalada: <b>${esc(r.estado?.fw || r.equipo.fw || "—")}</b>${r.estado?.ota ? ` · última OTA: ${esc(r.estado.ota.fase)} ${esc(r.estado.ota.msg || "")}` : ""}</p>
      <div id="fw-lista" class="desliza"></div>
      <h3>Subir un .bin nuevo</h3>
      <p class="ayuda">El archivo es <code>firmware/evse_monitor/.pio/build/placa/firmware.bin</code> después de compilar. Sube la versión que dice FW_VERSION en include/config.h.</p>
      <div class="fila"><div><label>Versión</label><input id="fw-ver" placeholder="1.0.1"></div><div><label>Archivo</label><input id="fw-bin" type="file" accept=".bin"></div></div>
      <label>Notas</label><input id="fw-notas" placeholder="qué cambia">
      <button class="boton chico" id="fw-subir" style="margin-top:.6rem">Subir</button>
    </div>
    <div class="tarjeta"><h2>Equipo</h2>
      <div class="acciones" style="display:flex;gap:.5rem;flex-wrap:wrap">
        <button class="boton chico secundario" id="eq-reiniciar">Reiniciar el equipo</button>
        <button class="boton chico secundario" id="eq-token">Generar token nuevo</button>
        <button class="boton chico peligro" id="eq-borrar">Borrar equipo</button></div>
      <h3>Usuarios con acceso</h3><div id="permisos"></div>
      <div class="fila"><div><label>Correo</label><input id="perm-email" type="email"></div>
        <div><label>Rol</label><select id="perm-rol"><option value="propietario">Propietario (control)</option><option value="lectura">Solo lectura</option></select></div></div>
      <button class="boton chico" id="perm-dar" style="margin-top:.6rem">Dar acceso</button>
    </div>`;
}

function instruccionesEquipo(id, token) {
  const host = location.host;
  const local = location.protocol !== "https:";
  const servidor = local ? `ws://IP-DE-TU-PC:${location.port || 80}` : host;
  return `<p>Guárdalo ya: <b>no se vuelve a mostrar</b>.</p>
    <label>Id</label><div class="secreto">${esc(id)}</div><label>Token</label><div class="secreto">${esc(token)}</div>
    <p>En el monitor serie del equipo (115200):</p>
    <pre class="consola">wifi "NOMBRE DE TU RED" CLAVE_DEL_WIFI
servidor ${esc(servidor)}
equipo ${esc(id)} ${esc(token)}
reiniciar</pre>
    <p class="ayuda">O en el portal: mantén PARAR 5 s al encender, conéctate a la red EVSE-XXXX y abre 192.168.4.1.${local ? " Estás en pruebas sin TLS: usa la IP de tu PC en la red local." : ""}</p>`;
}

function enlazarAdminEquipo(id, r) {
  const orden = (o, a) => api(`/api/equipos/${id}/orden`, { metodo: "POST", datos: { o, a } });
  $("#cal-leer").onclick = (e) =>
    conBoton(e.target, async () => {
      const x = await orden("cal_leer");
      const d = x.datos || {};
      $("#cal-datos").hidden = false;
      $("#cal-datos").textContent = `${d.calibrada ? "Calibrado" : "SIN CALIBRAR (valores de fábrica)"}
Ugain ${hex4(d.ugain)}  IgainN ${hex4(d.igain_n)}  Uoffset ${hex4(d.uoffset)}  IoffsetN ${hex4(d.ioffset_n)}
PoffsetN ${hex4(d.poffset_n)}  Ngain ${hex4(d.ngain)}  Nphi ${hex4(d.nphi)}  MMode ${hex4(d.mmode)}
Chip: ${Object.entries(d.chip || {}).map(([k, v]) => `${k} ${v}`).join("  ")}
Ahora: ${fmt(d.v, 2)} V · ${fmt(d.i, 3)} A · ${fmt(d.p, 0)} W · FP ${fmt(d.pf, 3)}`;
    });
  $("#cal-auto").onclick = async (e) => {
    const v = Number($("#cal-v").value) || 0, i = Number($("#cal-i").value) || 0;
    if (!v && !i) return aviso("Escribe la tensión o la corriente de referencia.", true);
    if (!(await confirmar("¿Calibrar el medidor?", `<p>Referencia: ${v ? fmt(v, 2) + " V" : "—"} · ${i ? fmt(i, 3) + " A" : "—"}. Las lecturas deben estar estables.</p>`, "Calibrar"))) return;
    conBoton(e.target, async () => aviso((await orden("cal_auto", { v, i })).msg));
  };
  $("#cal-fab").onclick = async (e) => {
    if (!(await confirmar("¿Volver a los valores de fábrica?", "<p>Se pierde la calibración del equipo.</p>", "Volver", true))) return;
    conBoton(e.target, async () => aviso((await orden("cal_fabrica")).msg));
  };
  $("#eq-reiniciar").onclick = async (e) => {
    if (!(await confirmar("¿Reiniciar el equipo?", "<p>K1 se abre durante el reinicio (unos 15 s) y luego aplica la política de arranque.</p>", "Reiniciar", true))) return;
    conBoton(e.target, async () => aviso((await orden("reiniciar")).msg));
  };
  $("#eq-token").onclick = async (e) => {
    if (!(await confirmar("¿Generar un token nuevo?", "<p>El token actual deja de servir: tendrás que poner el nuevo en el equipo.</p>", "Generar", true))) return;
    conBoton(e.target, async () => {
      const x = await api(`/api/equipos/${id}/token`, { metodo: "POST", datos: {} });
      mostrar("Token nuevo", instruccionesEquipo(x.id, x.token));
    });
  };
  $("#eq-borrar").onclick = async (e) => {
    if (!(await confirmar("¿Borrar el equipo?", "<p>Se borra el equipo y sus permisos. El historial queda en la base, pero no se ve.</p>", "Borrar", true))) return;
    conBoton(e.target, async () => {
      await api(`/api/equipos/${id}`, { metodo: "DELETE" });
      location.hash = "#/";
    });
  };
  async function fw() {
    const { firmware } = await api("/api/firmware");
    $("#fw-lista").innerHTML = firmware.length
      ? `<table class="tabla"><thead><tr><th>Versión</th><th class="n">Tamaño</th><th>Subido</th><th></th></tr></thead><tbody>${firmware
          .map((f) => `<tr><td><b>${esc(f.version)}</b><br><small>${esc(f.notas || "")}</small></td><td class="n">${fmt(f.tam / 1024, 0)} KB</td><td>${fCorta(f.subido)}</td><td><button class="boton chico" data-v="${esc(f.version)}">Instalar</button></td></tr>`)
          .join("")}</tbody></table>`
      : `<p class="suave">No has subido ningún firmware.</p>`;
    for (const b of $$("button[data-v]", $("#fw-lista")))
      b.onclick = async () => {
        if (!(await confirmar(`¿Instalar la versión ${b.dataset.v}?`, "<p>El equipo descarga el firmware, revisa el SHA-256 y se reinicia. Si el nuevo no llega al servidor y se reinicia más de 3 veces, vuelve al anterior.</p>", "Instalar"))) return;
        conBoton(b, async () => aviso((await api(`/api/equipos/${id}/ota`, { metodo: "POST", datos: { ver: b.dataset.v } })).msg));
      };
  }
  fw();
  $("#fw-subir").onclick = (e) =>
    conBoton(e.target, async () => {
      const f = $("#fw-bin").files[0];
      const ver = $("#fw-ver").value.trim();
      if (!f || !ver) throw new Error("Falta la versión o el archivo.");
      const x = await api(`/api/firmware?ver=${encodeURIComponent(ver)}&notas=${encodeURIComponent($("#fw-notas").value)}`, { metodo: "POST", crudo: await f.arrayBuffer() });
      aviso(`Subido ${x.version} (${fmt(x.tam / 1024, 0)} KB)`);
      fw();
    });
  async function permisos() {
    const { permisos } = await api(`/api/equipos/${id}/permisos`);
    $("#permisos").innerHTML = permisos.length
      ? `<ul class="lista">${permisos.map((p) => `<li><div style="flex:1">${esc(p.nombre)} <small>${esc(p.email)} · ${esc(p.rol)}</small></div><button class="boton chico secundario" data-u="${p.id}">Quitar</button></li>`).join("")}</ul>`
      : `<p class="suave">Solo los administradores.</p>`;
    for (const b of $$("button[data-u]", $("#permisos")))
      b.onclick = () => conBoton(b, async () => (await api(`/api/equipos/${id}/permisos`, { metodo: "DELETE", datos: { usuario_id: Number(b.dataset.u) } }), permisos()));
  }
  permisos();
  $("#perm-dar").onclick = (e) =>
    conBoton(e.target, async () => {
      await api(`/api/equipos/${id}/permisos`, { metodo: "POST", datos: { email: $("#perm-email").value, rol: $("#perm-rol").value } });
      aviso("Acceso dado.");
      permisos();
    });
}
const hex4 = (v) => (Number.isFinite(v) ? v.toString(16).toUpperCase().padStart(4, "0") + "H" : "—");

// ------------------------------------------------------------------ perfil
async function vPerfil() {
  const { usuario } = await api("/api/auth/yo");
  app.usuario = usuario;
  vista.innerHTML = `
    <div class="cabecera"><h1>Perfil</h1>${usuario.admin ? `<a class="boton chico secundario" href="#/admin">Administración</a>` : ""}</div>
    <form class="tarjeta" id="f-perfil"><h2>Datos y notificaciones</h2>
      <label>Nombre</label><input id="nombre" value="${esc(usuario.nombre)}">
      <label>Correo</label><input value="${esc(usuario.email)}" disabled>
      <label>Chat id de Telegram</label><input id="chat" value="${esc(usuario.telegram_chat || "")}" placeholder="p. ej. 123456789" inputmode="numeric">
      <p class="ayuda">Para recibir las alarmas: abre el bot de la app en Telegram y escríbele /start; tu chat id te lo da @userinfobot. Deja vacío para no recibir.</p>
      <div style="display:flex;gap:.5rem;margin-top:.8rem"><button class="boton">Guardar</button><button type="button" class="boton secundario" id="probar">Probar notificación</button></div>
    </form>
    <form class="tarjeta" id="f-clave"><h2>Cambiar la clave</h2>
      <label>Clave actual</label><input id="actual" type="password" required autocomplete="current-password">
      <label>Clave nueva</label><input id="nueva" type="password" required minlength="10" autocomplete="new-password">
      <button class="boton" style="margin-top:.8rem">Cambiar</button></form>
    <button class="boton secundario ancho" id="salir">Cerrar sesión</button>`;
  $("#f-perfil").onsubmit = (e) => {
    e.preventDefault();
    conBoton($("button", e.target), async () => {
      await api("/api/perfil", { metodo: "POST", datos: { nombre: $("#nombre").value, telegram_chat: $("#chat").value } });
      aviso("Guardado.");
    });
  };
  $("#probar").onclick = (e) => conBoton(e.target, async () => (await api("/api/perfil/probar", { metodo: "POST", datos: {} }), aviso("Mensaje enviado: revisa Telegram.")));
  $("#f-clave").onsubmit = (e) => {
    e.preventDefault();
    conBoton($("button", e.target), async () => {
      await api("/api/auth/clave", { metodo: "POST", datos: { actual: await derivar(usuario.email, $("#actual").value), nueva: await derivar(usuario.email, $("#nueva").value) } });
      aviso("Clave cambiada. Las demás sesiones se cerraron.");
      e.target.reset();
    });
  };
  $("#salir").onclick = async () => {
    await api("/api/auth/salir", { metodo: "POST", datos: {} });
    app.usuario = null;
    location.hash = "#/entrar";
  };
}

// ------------------------------------------------------------------ administración
async function vAdmin() {
  if (!app.usuario.admin) {
    location.hash = "#/";
    return;
  }
  const [{ usuarios }, { equipos }] = await Promise.all([api("/api/usuarios"), api("/api/equipos")]);
  vista.innerHTML = `
    <h1>Administración</h1>
    <form class="tarjeta" id="f-equipo"><h2>Agregar un equipo</h2>
      <div class="fila"><div><label>Id</label><input id="eq-id" required pattern="[a-z0-9][a-z0-9-]{2,31}" placeholder="evse-01"></div>
        <div><label>Nombre</label><input id="eq-nombre" placeholder="Garaje"></div></div>
      <p class="ayuda">El id va en minúsculas, sin espacios. Al crearlo te muestro el token del equipo una sola vez.</p>
      <button class="boton" style="margin-top:.6rem">Crear equipo</button></form>
    <div class="tarjeta"><h2>Equipos</h2>${equipos.length ? `<ul class="lista">${equipos.map((e) => `<li><div style="flex:1"><a href="#/e/${e.id}">${esc(e.nombre)}</a> <small>${esc(e.id)}</small></div><span class="chip ${e.estado?.en_linea ? "ok" : ""}">${e.estado?.en_linea ? "En línea" : "Fuera de línea"}</span></li>`).join("")}</ul>` : `<p class="suave">Ninguno todavía.</p>`}</div>
    <form class="tarjeta" id="f-usuario"><h2>Crear un usuario</h2>
      <div class="fila"><div><label>Nombre</label><input id="u-nombre" required></div><div><label>Correo</label><input id="u-email" type="email" required></div></div>
      <label>Clave inicial</label><input id="u-clave" type="password" minlength="10" required autocomplete="new-password">
      <div class="fila"><div><label>Equipo</label><select id="u-equipo"><option value="">(ninguno)</option>${equipos.map((e) => `<option value="${e.id}">${esc(e.nombre)}</option>`).join("")}</select></div>
        <div><label>Rol</label><select id="u-rol"><option value="propietario">Propietario</option><option value="lectura">Solo lectura</option></select></div></div>
      <label class="opcion"><input type="checkbox" id="u-admin">Administrador (ve y controla todos los equipos)</label>
      <button class="boton" style="margin-top:.6rem">Crear usuario</button></form>
    <div class="tarjeta"><h2>Usuarios</h2><ul class="lista">${usuarios
      .map((u) => `<li><div style="flex:1">${esc(u.nombre)} ${u.admin ? '<span class="chip">admin</span>' : ""}<br><small>${esc(u.email)} · ${esc(u.equipos || "sin equipos")}${u.telegram ? " · Telegram" : ""}</small></div>${u.id !== app.usuario.id ? `<button class="boton chico secundario" data-u="${u.id}">Borrar</button>` : ""}</li>`)
      .join("")}</ul></div>`;
  $("#f-equipo").onsubmit = (e) => {
    e.preventDefault();
    conBoton($("button", e.target), async () => {
      const x = await api("/api/equipos", { metodo: "POST", datos: { id: $("#eq-id").value.trim(), nombre: $("#eq-nombre").value.trim() } });
      mostrar("Equipo creado", instruccionesEquipo(x.id, x.token));
      $("#dialogo").addEventListener("close", () => vAdmin(), { once: true });
    });
  };
  $("#f-usuario").onsubmit = (e) => {
    e.preventDefault();
    conBoton($("button", e.target), async () => {
      const email = $("#u-email").value.trim();
      await api("/api/usuarios", {
        metodo: "POST",
        datos: { email, nombre: $("#u-nombre").value, clave: await derivar(email, $("#u-clave").value), admin: $("#u-admin").checked, equipo: $("#u-equipo").value, rol: $("#u-rol").value },
      });
      aviso("Usuario creado. Pásale su correo y su clave inicial.");
      vAdmin();
    });
  };
  for (const b of $$("button[data-u]"))
    b.onclick = async () => {
      if (!(await confirmar("¿Borrar el usuario?", "<p>Pierde el acceso de inmediato.</p>", "Borrar", true))) return;
      conBoton(b, async () => (await api(`/api/usuarios/${b.dataset.u}`, { metodo: "DELETE" }), vAdmin()));
    };
}
