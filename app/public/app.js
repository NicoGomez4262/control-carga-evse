// EVSE Monitor · app web (Firebase, sin framework). Rutas con #: #/entrar, #/, #/e/<id>[/historial|/alarmas|/ajustes],
// #/perfil, #/admin. Los datos en vivo llegan de la Realtime Database (docs/software/PROTOCOLO_MENSAJES.md).

import * as fb from "./fb.js";
import { Grafica } from "./grafica.js";
import { encender, icono, Medidor, mimico, numero, pintarMimico, pintarSelector, rodillos, selector, termometro } from "./instrumentos.js";

const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const vista = $("#vista");
const mando = $("#mando");
const app = { u: null, limpiar: [], estados: {} };

// ------------------------------------------------------------------ formato
const nfs = {};
const fmt = (v, d = 1) => {
  if (v === null || v === undefined || v === "" || !Number.isFinite(Number(v))) return "—";
  nfs[d] ??= new Intl.NumberFormat("es-CO", { minimumFractionDigits: d, maximumFractionDigits: d });
  return nfs[d].format(Number(v));
};
const cop = (v) => (Number.isFinite(Number(v)) ? "$ " + fmt(v, 0) : "—");
const tz = { timeZone: "America/Bogota" };
const fFecha = (s) => (s ? new Date(s * 1000).toLocaleString("es-CO", { ...tz, dateStyle: "medium", timeStyle: "short" }) : "—");
const fCorta = (s) => (s ? new Date(s * 1000).toLocaleString("es-CO", { ...tz, day: "numeric", month: "short", hour: "2-digit", minute: "2-digit", hour12: false }) : "—");
const fDia = (s) => new Date(s * 1000).toLocaleDateString("es-CO", { ...tz, weekday: "short", day: "numeric", month: "short" });
const ahora = () => Math.floor(Date.now() / 1000);
function duracion(s) {
  if (!Number.isFinite(s) || s < 0) return "—";
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60);
  return h ? `${h} h ${String(m).padStart(2, "0")} min` : m ? `${m} min` : `${Math.floor(s)} s`;
}
function hace(seg) {
  if (!Number.isFinite(seg)) return "—";
  if (seg < 10) return "ahora";
  if (seg < 60) return `hace ${Math.floor(seg)} s`;
  if (seg < 3600) return `hace ${Math.floor(seg / 60)} min`;
  if (seg < 86400) return `hace ${Math.floor(seg / 3600)} h`;
  return `hace ${Math.floor(seg / 86400)} días`;
}
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

// ------------------------------------------------------------------ textos del equipo
const ALARMAS = {
  temp_sonda: ["Sobretemp. sonda", "Sobretemperatura en la sonda"],
  temp_amb: ["Sobretemp. placa", "Sobretemperatura en la placa"],
  sonda_falla: ["Sonda sin respuesta", "La sonda DS18B20 no responde"],
  medidor_falla: ["Falla medidor", "Falla del medidor ATM90E26"],
  red_baja: ["Red baja", "Tensión de red baja"],
  parar: ["PARAR", "Se pulsó PARAR"],
  amb_falla: ["Sensor placa", "El sensor de ambiente no responde"],
  sin_hora: ["Sin hora", "Sin hora (sin NTP ni RTC)"],
  reinicio: ["Reinicio", "Reinicio inesperado (brownout o watchdog)"],
  sin_calibrar: ["Sin calibrar", "El medidor aún no está calibrado"],
  temp_aviso: ["Sonda caliente", "La sonda está cerca del límite de temperatura"],
};
const GRAVES = new Set(["temp_sonda", "temp_amb", "sonda_falla", "medidor_falla", "red_baja", "parar", "reinicio"]);
const MOTIVOS = {
  falla: ["rojo", "Detenida por falla", "El medidor o la sonda fallan. Mira el anunciador."],
  temperatura: ["rojo", "Detenida por temperatura", "Vuelve sola 5 min después de enfriarse por debajo de la histéresis."],
  parar: ["rojo", "PARAR pulsado", "Se libera manteniendo PARAR 3 s en la placa o con «Soltar PARAR»."],
  red: ["rojo", "Tensión de red baja", "Vuelve sola cuando la red se normaliza durante 1 min."],
  limite: ["ambar", "Límite de la sesión", "Se alcanzó el límite. «Nueva sesión» empieza otra."],
  horario: ["ambar", "Fuera del horario", "Vuelve sola al entrar en una franja de carga."],
  app: ["ambar", "Detenida desde la app", "Gira el selector a Permitir para cargar."],
  arranque: ["ambar", "Arrancando", "El equipo acaba de encender: verifica 10 s o espera tu permiso."],
};
const RESETS = { encendido: "encendido", pin_en: "botón EN", software: "software", panic: "excepción", wdt_int: "watchdog", wdt_tarea: "watchdog de tareas", wdt: "watchdog", brownout: "brownout" };
const FIN = { sin_corriente: "terminó la carga", limite: "límite", otro: "otro" };
const ORDENES = { permitir: "Permitió la carga", detener: "Detuvo la carga", reconocer: "Reconoció las alarmas", soltar_parar: "Soltó PARAR", reiniciar: "Reinició el equipo", estado: "Pidió el estado", cal_leer: "Leyó la calibración", cal_auto: "Calibró el medidor", cal_escribir: "Escribió la calibración", cal_fabrica: "Volvió a la calibración de fábrica", telegram_probar: "Probó Telegram" };
const DIAS = ["D", "L", "M", "M", "J", "V", "S"];
const NOMBRE_DIAS = ["domingo", "lunes", "martes", "miércoles", "jueves", "viernes", "sábado"];

function textoEvento(e) {
  const al = ALARMAS[e.a]?.[1] || e.txt || e.a;
  switch (e.c) {
    case "alarma": {
      const v = Number(e.x) / 10;
      const extra = e.a?.startsWith("temp") && v > 0 ? ` (${fmt(v, 1)} °C)` : "";
      return [GRAVES.has(e.a) ? "rojo" : "ambar", `${al}${extra}`];
    }
    case "alarma_fin": return ["verde", `Se despejó: ${al}`];
    case "arranque": return ["", `Arranque del equipo${e.x ? ` · ${e.x} reinicios seguidos` : ""}`];
    case "k1": return Number(e.val) ? ["verde", "K1 cerrado: carga permitida"] : ["", `K1 abierto${e.mot ? ` (${MOTIVOS[e.mot]?.[1] || e.mot})` : ""}`];
    case "sesion_inicio": return ["verde", `Empezó la sesión nº ${fmt(e.val, 0)}`];
    case "limite": return ["ambar", `Límite de la sesión: ${["", "energía", "tiempo", "costo"][Number(e.val)] || ""}`];
    case "config": return ["", `Configuración v${fmt(e.val, 0)} aplicada en el equipo`];
    case "calibracion": return ["ambar", "Calibración del medidor cambiada"];
    case "orden_local": return ["", ["", "PARAR pulsado en la placa", "PARAR liberado en la placa", "PARAR liberado desde la app"][Number(e.val)] || "Orden local"];
    case "hora": return ["", "Hora puesta por NTP y copiada al DS3231"];
    case "ota": return [Number(e.val) ? "verde" : "rojo", Number(e.val) ? "Firmware actualizado" : "Volvió al firmware anterior"];
    default: return ["", e.c];
  }
}

// ------------------------------------------------------------------ avisos, diálogos y botones
let tNotif;
function notif(msg, tipo = "verde") {
  const n = $("#notif");
  n.hidden = false;
  n.innerHTML = `<span class="piloto ${tipo}"></span><span>${esc(msg)}</span>`;
  n.style.animation = "none";
  void n.offsetWidth;
  n.style.animation = "";
  clearTimeout(tNotif);
  tNotif = setTimeout(() => (n.hidden = true), tipo === "rojo" ? 6500 : 3800);
}
const fallo = (e) => notif(traducir(e), "rojo");

function traducir(e) {
  const c = e?.code || "";
  const m = {
    "auth/invalid-credential": "Correo o clave incorrectos.",
    "auth/invalid-email": "Ese correo no es válido.",
    "auth/user-disabled": "Esta cuenta está deshabilitada.",
    "auth/email-already-in-use": "Ya hay una cuenta con ese correo. Entra con ella.",
    "auth/weak-password": "La clave es muy corta (mínimo 8 caracteres).",
    "auth/too-many-requests": "Demasiados intentos. Espera unos minutos.",
    "auth/network-request-failed": "Sin conexión a internet.",
    "auth/requires-recent-login": "Vuelve a entrar para hacer esto.",
    "auth/operation-not-allowed": "Activa «Correo y contraseña» en Firebase Authentication.",
    PERMISSION_DENIED: "No tienes permiso para esto.",
  };
  return m[c] || (String(e?.message || e).includes("permission_denied") ? m.PERMISSION_DENIED : e?.message || String(e));
}

function dialogo({ titulo, html = "", si = "Aceptar", no = "Cancelar", peligro = false, formulario = false }) {
  const d = $("#dialogo");
  d.innerHTML = `<form method="dialog" class="formulario"><h2 id="dialogo-titulo">${esc(titulo)}</h2><div>${html}</div>
    <div class="acciones">${no ? `<button class="boton sec" value="no" formnovalidate>${esc(no)}</button>` : ""}<button class="boton ${peligro ? "peligro" : ""}" value="si">${esc(si)}</button></div></form>`;
  d.showModal();
  return new Promise((ok) => {
    d.onclose = () => ok(d.returnValue === "si" ? (formulario ? new FormData($("form", d)) : true) : false);
  });
}
const mostrar = (titulo, html) => dialogo({ titulo, html, si: "Listo", no: "" });

async function conBoton(b, f) {
  if (b.disabled) return;
  b.disabled = true;
  b.classList.add("cargando");
  try {
    return await f();
  } catch (e) {
    fallo(e);
  } finally {
    b.disabled = false;
    b.classList.remove("cargando");
  }
}

async function copiar(txt) {
  try {
    await navigator.clipboard.writeText(txt);
    notif("Copiado.");
  } catch {
    notif("No se pudo copiar: selecciónalo a mano.", "ambar");
  }
}

function descargar(nombre, filas) {
  const csv = "﻿" + filas.map((f) => f.map((x) => (/[;"\n]/.test(String(x ?? "")) ? `"${String(x).replace(/"/g, '""')}"` : x ?? "")).join(";")).join("\n");
  const a = Object.assign(document.createElement("a"), { href: URL.createObjectURL(new Blob([csv], { type: "text/csv" })), download: nombre });
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 2000);
}

// Repinta un bloque solo si cambió (así un botón no se reemplaza bajo el dedo ni pierde su estado «cargando»).
function cambia(el, html) {
  if (el.dataset.h === html) return false;
  el.dataset.h = html;
  el.innerHTML = html;
  return true;
}

// ------------------------------------------------------------------ estado en línea
function edad(est) {
  return est?.ts ? (fb.ahoraServidor() - est.ts) / 1000 : Infinity;
}
function enLinea(est, cfg) {
  const lim = Math.max(25, (Number(cfg?.tel_s) || 15) * 2.5 + 5);
  return edad(est) < lim;
}
const corriendo = (e) => !!e?.k1 && Number(e?.i) >= 0.3;
const rol = (id) => (app.u?.admin ? "propietario" : app.u?.equipos?.[id]);
const puedeMandar = (id) => rol(id) === "propietario";

// ------------------------------------------------------------------ mando (navegación)
function pintarMando(id, seccion) {
  if (!app.u) {
    mando.hidden = true;
    return;
  }
  mando.hidden = false;
  const ids = Object.keys(app.u.equipos);
  const eq = id || ids[0];
  const nr = (app.estados[eq]?.nr || []).length;
  const item = (h, ic, txt, actual, extra = "") => `<a href="${h}" ${actual ? 'aria-current="page"' : ""}>${icono(ic)}<span>${txt}</span>${extra}</a>`;
  mando.innerHTML = `
    <div class="marca"><div class="marca-nombre">${icono("rayo")}EVSE Monitor</div><div class="marca-sub">Tablero de carga · Rev 1.0</div></div>
    ${ids.length > 1 ? `<div class="equipos-lista">${ids.map((k) => `<a href="#/e/${k}" ${k === id ? 'aria-current="page"' : ""}>${icono("equipo")}<span>${esc(app.nombres?.[k] || k)}</span></a>`).join("")}</div>` : ""}
    ${eq
      ? item(`#/e/${eq}`, "panel", "Panel", seccion === "panel") +
        item(`#/e/${eq}/historial`, "historial", "Historial", seccion === "historial") +
        item(`#/e/${eq}/alarmas`, "alarmas", "Alarmas", seccion === "alarmas", nr ? `<span class="alerta">${nr}</span>` : "") +
        item(`#/e/${eq}/ajustes`, "ajustes", "Ajustes", seccion === "ajustes")
      : item("#/", "panel", "Inicio", seccion === "inicio") + (app.u.admin ? item("#/admin", "admin", "Admin", seccion === "admin") : "") + item("#/perfil", "usuario", "Perfil", seccion === "perfil")}
    ${eq ? `<div class="cuenta">
      ${app.u.admin ? item("#/admin", "admin", "Administración", seccion === "admin") : ""}
      ${item("#/perfil", "usuario", esc(app.u.nombre), seccion === "perfil")}
    </div>` : ""}`;
}

// ------------------------------------------------------------------ rutas
function limpiar() {
  for (const f of app.limpiar.splice(0)) {
    try {
      f();
    } catch {}
  }
}
const alSalir = (f) => app.limpiar.push(f);

async function navegar() {
  const h = location.hash.replace(/^#\/?/, "");
  const [a, id, sub] = h.split("/");
  const pintar = async () => {
    limpiar();
    vista.scrollTop = 0;
    window.scrollTo(0, 0);
    try {
      if (!app.u) {
        pintarMando();
        return await vEntrar();
      }
      if (a === "e" && id) {
        if (!rol(id)) return (location.hash = "#/");
        const s = sub || "panel";
        pintarMando(id, s);
        if (s === "historial") return await vHistorial(id);
        if (s === "alarmas") return await vAlarmas(id);
        if (s === "ajustes") return await vAjustes(id);
        return await vPanel(id);
      }
      if (a === "perfil") return pintarMando(null, "perfil"), await vPerfil();
      if (a === "admin" && app.u.admin) return pintarMando(null, "admin"), await vAdmin();
      pintarMando(null, "inicio");
      return await vInicio();
    } catch (e) {
      console.error(e);
      vista.innerHTML = `<div class="riel"><article class="mod"><h2>No se pudo abrir esta vista</h2><p class="suave">${esc(traducir(e))}</p><a class="boton sec" href="#/">Volver al inicio</a></article></div>`;
    }
  };
  if (document.startViewTransition && app.pintada && document.visibilityState === "visible" && !matchMedia("(prefers-reduced-motion: reduce)").matches) {
    const t = document.startViewTransition(pintar);
    t.ready.catch(() => {});
    await t.updateCallbackDone.catch(() => {});
  } else {
    await pintar();
  }
  app.pintada = true;
  vista.focus({ preventScroll: true });
}
window.addEventListener("hashchange", navegar);

// ------------------------------------------------------------------ entrada
async function vEntrar() {
  let modo = "entrar";
  const dibujar = () => {
    vista.innerHTML = `
    <div class="puerta"><div class="riel placa-datos"><article class="mod">
      <div class="marca-nombre">${icono("rayo")}EVSE Monitor</div>
      <div class="marca-sub">Monitor y control de carga de vehículo eléctrico</div>
      <dl class="datos-nominales">
        <dt>Entrada</dt><dd>100–264 VAC · 120 V L–N o 240 V L1–L2</dd>
        <dt>Medición</dt><dd>ATM90E26 · tensión, corriente, potencia, energía</dd>
        <dt>Mando</dt><dd>K1 AQY214EHAX (NA) en J2 del EVSE</dd>
        <dt>Control</dt><dd>ESP32-S3 · protecciones sin internet</dd>
      </dl>
      <div class="pestanas rango" role="tablist">
        <button type="button" data-m="entrar" aria-pressed="${modo === "entrar"}">Entrar</button>
        <button type="button" data-m="crear" aria-pressed="${modo === "crear"}">Crear cuenta</button>
      </div>
      <form class="formulario" id="f-entrar">
        ${modo === "crear" ? `<label class="campo"><span>Tu nombre</span><input name="nombre" autocomplete="name" required maxlength="60"></label>` : ""}
        <label class="campo"><span>Correo</span><input name="correo" type="email" autocomplete="email" required></label>
        <label class="campo"><span>Clave</span><input name="clave" type="password" autocomplete="${modo === "crear" ? "new-password" : "current-password"}" minlength="${modo === "crear" ? 8 : 1}" required></label>
        <button class="boton ancho verde">${modo === "crear" ? "Crear la cuenta" : "Entrar"}</button>
      </form>
      <div class="pie-enlaces">
        ${modo === "entrar" ? `<button class="enlace-boton" id="olvide" type="button">Olvidé mi clave</button>` : `<span class="suave">Después, quien administra te da acceso a un equipo.</span>`}
        ${fb.local ? `<span class="suave">Emulador local</span>` : ""}
      </div>
      <div class="pilotos-fila" aria-hidden="true"><span class="piloto verde"></span><span class="piloto ambar"></span><span class="piloto rojo"></span><small>Rev 1.0 · firmware evse_monitor</small></div>
    </article></div></div>`;
    for (const b of $$(".pestanas button")) b.onclick = () => ((modo = b.dataset.m), dibujar());
    $("#f-entrar").onsubmit = (e) => {
      e.preventDefault();
      const d = new FormData(e.target);
      conBoton($("button.boton", e.target), async () => {
        if (modo === "crear") {
          app.nombreNuevo = d.get("nombre").trim();
          await fb.crearCuenta(d.get("correo").trim(), d.get("clave"));
        } else {
          await fb.entrar(d.get("correo").trim(), d.get("clave"));
        }
      });
    };
    if ($("#olvide"))
      $("#olvide").onclick = async () => {
        const correo = $('[name="correo"]').value.trim();
        if (!correo) return notif("Escribe tu correo primero.", "ambar");
        try {
          await fb.recuperar(correo);
          notif("Te mandé un correo para cambiar la clave.");
        } catch (e) {
          fallo(e);
        }
      };
    encender(vista);
  };
  dibujar();
}

// ------------------------------------------------------------------ inicio
async function vInicio() {
  const ids = Object.keys(app.u.equipos);
  if (ids.length === 1 && !app.u.admin) return (location.hash = `#/e/${ids[0]}`);
  if (!ids.length) {
    vista.innerHTML = `
    <header class="cabecera"><div class="titulo"><h1>Hola, ${esc(app.u.nombre)}</h1><div class="enlace-estado">Todavía no tienes equipos en tu tablero.</div></div></header>
    <div class="riel">
      ${app.u.admin ? htmlAgregar() : `
      <article class="mod" style="--d:7"><div class="mod-cab"><span class="rotulo"><b>?</b> Acceso</span></div>
        <h2>Pídele acceso a quien administra el equipo</h2>
        <p>Dile tu correo, <b>${esc(app.u.email)}</b>. Cuando te dé permiso, el equipo aparece aquí solo.</p>
        <details><summary>¿Eres tú quien administra?</summary>
          <p class="ayuda">La primera vez, en la consola de Firebase: Realtime Database → Datos → <b>+</b> en la raíz → clave <code>admins</code>, y dentro tu identificador con el valor <code>true</code>. Después recarga esta página.</p>
          <div class="secreto"><code>${esc(app.u.uid)}</code><button class="boton-icono" id="c-uid" aria-label="Copiar identificador">${icono("copiar")}</button></div>
        </details>
      </article>`}
    </div>`;
    if ($("#c-uid")) $("#c-uid").onclick = () => copiar(app.u.uid);
    enlazarAgregar();
    return encender(vista);
  }
  vista.innerHTML = `
    <header class="cabecera"><div class="titulo"><h1>Tus equipos</h1><div class="enlace-estado">${ids.length} en el tablero</div></div></header>
    <div class="riel">${ids.map((k) => `
      <a class="mod tarjeta-equipo" href="#/e/${k}" style="--m:4;--d:4;text-decoration:none;color:inherit" data-id="${k}">
        <div class="mod-cab"><span class="rotulo"><b>${esc(k)}</b></span><span class="piloto"></span></div>
        <h2 class="nombre">${esc(app.nombres?.[k] || k)}</h2>
        <p class="lectura l-l pot">—</p><p class="dato-pie txt">Sin datos todavía</p>
      </a>`).join("")}
      ${app.u.admin ? htmlAgregar() : ""}
    </div>`;
  enlazarAgregar();
  for (const k of ids) {
    const t = $(`.tarjeta-equipo[data-id="${k}"]`);
    alSalir(fb.escuchar(`equipos/${k}/nombre`, (n) => n && ($(".nombre", t).textContent = n)));
    alSalir(
      fb.escuchar(`estado/${k}`, (e) => {
        app.estados[k] = e;
        const on = enLinea(e);
        $(".piloto", t).className = `piloto ${on ? (corriendo(e) ? "verde respira" : "verde") : ""}`;
        $(".pot", t).innerHTML = on && Number.isFinite(e?.p) ? `${fmt(e.p / 1000, 2)}<span class="u">kW</span>` : "—";
        $(".txt", t).textContent = !e ? "El equipo aún no se ha conectado" : !on ? `Sin conexión · ${hace(edad(e))}` : corriendo(e) ? `Cargando · ${fmt(e.es, 2)} kWh` : MOTIVOS[e.mot]?.[1] || "En reposo";
      }),
    );
  }
  encender(vista);
}

function htmlAgregar() {
  return `<article class="mod" style="--m:4;--d:5"><div class="mod-cab"><span class="rotulo">${icono("mas")}Nuevo equipo</span></div>
    <form class="formulario" id="f-agregar">
      <div class="campos">
        <label class="campo"><span>Id</span><input name="id" required pattern="[a-z0-9][a-z0-9_\\-]{1,23}" placeholder="evse-01" autocapitalize="off"></label>
        <label class="campo"><span>Nombre</span><input name="nombre" required maxlength="40" placeholder="Garaje"></label>
      </div>
      <label class="campo"><span>Red</span><select name="vnom"><option value="240">240 V (L1–L2)</option><option value="120">120 V (L–N)</option></select></label>
      <button class="boton verde">Agregar equipo</button>
    </form></article>`;
}
function enlazarAgregar() {
  const f = $("#f-agregar");
  if (!f) return;
  f.onsubmit = (e) => {
    e.preventDefault();
    const d = new FormData(f);
    conBoton($("button", f), async () => {
      const id = await fb.crearEquipo(d.get("id").trim(), d.get("nombre").trim(), Number(d.get("vnom")));
      app.u = await fb.perfil(fb.auth.currentUser);
      notif(`Equipo «${id}» creado. Ahora enlázalo con la placa.`);
      location.hash = `#/e/${id}/ajustes`;
    });
  };
}

// ------------------------------------------------------------------ panel
async function vPanel(id) {
  const manda = puedeMandar(id);
  vista.innerHTML = `
    <header class="cabecera">
      <div class="titulo"><h1 id="t-nombre">${esc(app.nombres?.[id] || id)}</h1>
        <div class="enlace-estado"><span class="piloto" id="p-enlace"></span><span id="t-enlace">Conectando…</span></div></div>
      ${Object.keys(app.u.equipos).length > 1 ? `<a class="boton-icono" href="#/" aria-label="Todos los equipos">${icono("equipo")}</a>` : ""}
      <a class="boton-icono solo-movil" href="#/perfil" aria-label="Tu perfil">${icono("usuario")}</a>
    </header>
    <section class="riel"><article class="mod" style="--d:12"><div class="mod-cab"><span class="rotulo"><b>X0</b> Circuito de carga</span><small id="t-red"></small></div><div id="mimico"></div></article></section>
    <section class="riel">
      <article class="mod" style="--d:5"><div class="mod-cab"><span class="rotulo"><b>P1</b> Potencia</span><span class="piloto" id="p-p1"></span></div>
        <div id="medidor"></div>
        <div class="potencia"><div class="lectura l-xl"><span id="l-p">—</span><span class="u">kW</span></div><div class="dato-pie" id="l-pmax"></div></div>
        <div class="fila-lecturas">
          <div><small>Corriente</small><span class="lectura l-m"><span id="l-i">—</span><span class="u">A</span></span></div>
          <div><small>Tensión</small><span class="lectura l-m"><span id="l-v">—</span><span class="u">V</span></span></div>
          <div><small>FP</small><span class="lectura l-m" id="l-pf">—</span></div>
        </div>
      </article>
      <article class="mod" style="--d:4"><div class="mod-cab"><span class="rotulo"><b>K1</b> Permiso de carga</span><span class="piloto" id="p-k1"></span></div>
        <div id="selector"></div>
        <p class="k1-estado" id="t-k1"></p>
        <div class="acciones centro" id="k1-acciones"></div>
      </article>
      <article class="mod" style="--d:3"><div class="mod-cab"><span class="rotulo"><b>E1</b> Sesión</span><small id="t-ses"></small></div>
        <div class="lectura l-l"><span id="l-es">—</span><span class="u">kWh</span></div>
        <div class="resumen" style="grid-template-columns:1fr 1fr;margin-top:12px">
          <div><small>Costo</small><b id="l-cop">—</b></div>
          <div><small>Tiempo</small><b id="l-dur">—</b></div>
          <div><small>Pico</small><b id="l-pico">—</b></div>
          <div><small>Tarifa / kWh</small><b id="l-tar">—</b></div>
        </div>
      </article>
    </section>
    <section class="riel" id="r-anun" hidden><article class="mod" style="--d:12">
      <div class="mod-cab"><span class="rotulo"><b>H1</b> Anunciador</span><a href="#/e/${id}/alarmas" class="suave" style="margin-left:auto">Ver todo</a></div>
      <div class="anunciador" id="anun"></div>
      <div class="acciones" id="anun-acc"></div>
    </article></section>
    <section class="riel">
      <article class="mod" style="--m:2;--d:3"><div class="mod-cab"><span class="rotulo"><b>T1</b> Sonda</span></div>
        <div class="lectura l-m"><span id="l-tsn">—</span><span class="u">°C</span></div><div class="termo" id="b-tsn"></div><div class="dato-pie" id="c-tsn"></div></article>
      <article class="mod" style="--m:2;--d:3"><div class="mod-cab"><span class="rotulo"><b>T2</b> Placa</span></div>
        <div class="lectura l-m"><span id="l-tam">—</span><span class="u">°C</span></div><div class="termo" id="b-tam"></div><div class="dato-pie" id="c-tam"></div></article>
      <article class="mod" style="--d:3"><div class="mod-cab"><span class="rotulo"><b>V1</b> Red</span></div>
        <div class="fila-lecturas" style="margin-top:0">
          <div><small>Frecuencia</small><span class="lectura l-m"><span id="l-f">—</span><span class="u">Hz</span></span></div>
          <div><small>WiFi</small><span class="lectura l-m"><span id="l-rssi">—</span><span class="u">dBm</span></span></div>
          <div><small>Nominal</small><span class="lectura l-m"><span id="l-vnom">—</span><span class="u">V</span></span></div>
        </div></article>
      <article class="mod" style="--d:3"><div class="mod-cab"><span class="rotulo"><b>E0</b> Energía total</span></div>
        <div class="rodillos" id="l-et"></div><div class="dato-pie">kWh medidos desde que se instaló</div></article>
    </section>`;
  const mim = mimico();
  $("#mimico").append(mim);
  const med = new Medidor(8);
  $("#medidor").append(med.el);
  const sel = selector();
  $("#selector").append(sel);
  let est = app.estados[id] || null, cfg = null, esperando = false, ultimaOrden = 0;

  const pintar = () => {
    const e = est || {};
    const on = enLinea(est, cfg);
    const vnom = Number(cfg?.vnom) || 240;
    med.escala(vnom >= 200 ? 8 : 4);
    $("#p-enlace").className = `piloto ${on ? "verde" : est ? "" : "ambar respira"}`;
    $("#t-enlace").textContent = !est ? "El equipo todavía no se ha conectado" : on ? `En línea · ${hace(edad(est))}${e.fw ? ` · firmware ${e.fw}` : ""}` : `Sin conexión · último dato ${hace(edad(est))}`;
    $("#t-red").textContent = vnom >= 200 ? "240 V L1–L2" : "120 V L–N";
    pintarMimico(mim, on ? e : null, vnom);
    const kw = on && Number.isFinite(e.p) ? Math.max(0, e.p / 1000) : NaN;
    med.ir(Number.isFinite(kw) ? kw : 0, on ? (Number(e.pmax) || 0) / 1000 : 0);
    numero($("#l-p"), kw, 2);
    $("#l-pmax").textContent = on && e.ses ? `Pico de la sesión ${fmt((e.pmax || 0) / 1000, 2)} kW` : on ? "Sin sesión abierta" : "";
    numero($("#l-i"), on ? e.i : NaN, 1);
    numero($("#l-v"), on ? e.v : NaN, 1);
    $("#l-pf").textContent = on ? fmt(e.pf, 2) : "—";
    const carga = on && corriendo(e);
    $("#p-p1").className = `piloto ${carga ? "verde respira" : ""}`;
    // K1
    const mot = e.mot || "";
    const espera = !e.k1 && ["limite", "arranque"].includes(mot);
    $("#p-k1").className = `piloto ${!on ? "" : e.k1 ? "verde" : MOTIVOS[mot]?.[0] || "ambar"}`;
    if (!esperando) pintarSelector(sel, { permiso: on ? !!e.perm && !espera : !!e.perm, k1: on && e.k1, esperando: false, bloqueado: !manda || !on });
    let txt;
    if (!est) txt = "Cuando el equipo se conecte, aquí verás el permiso de carga.";
    else if (!on) txt = "<b>Sin conexión con el equipo.</b> Sus protecciones siguen funcionando solas.";
    else if (carga) txt = "<b>Cargando.</b> K1 cerrado: el EVSE tiene permiso y el vehículo toma corriente.";
    else if (e.k1) txt = "<b>Permitida.</b> K1 cerrado; el vehículo no está tomando corriente.";
    else if (MOTIVOS[mot]) txt = `<b>${MOTIVOS[mot][1]}.</b> ${MOTIVOS[mot][2]}`;
    else txt = "<b>Detenida.</b>";
    if (!manda && est) txt += "<br><small>Tu usuario es de solo lectura.</small>";
    $("#t-k1").innerHTML = txt;
    const acc = [];
    if (on && manda && mot === "limite") acc.push(`<button class="boton chico verde" data-o="permitir">Nueva sesión</button>`);
    if (on && manda && (mot === "parar" || (e.al || []).includes("parar"))) acc.push(`<button class="boton chico sec" data-o="soltar_parar">Soltar PARAR</button>`);
    if (cambia($("#k1-acciones"), acc.join(""))) for (const b of $$("#k1-acciones button")) b.onclick = () => conBoton(b, () => mandar(b.dataset.o));
    // sesión
    numero($("#l-es"), on || est ? Number(e.es) : NaN, 2);
    const tarifa = Number(cfg?.tarifa) || 0;
    $("#l-cop").textContent = est ? cop((Number(e.es) || 0) * tarifa) : "—";
    $("#l-dur").textContent = e.ses ? duracion(Number(e.dur)) : "—";
    $("#l-pico").textContent = e.ses ? `${fmt((e.pmax || 0) / 1000, 2)} kW` : "—";
    $("#l-tar").textContent = tarifa ? cop(tarifa) : "—";
    $("#t-ses").textContent = e.ses ? `nº ${e.ses} · desde ${fCorta(e.sini)}` : "sin sesión";
    // anunciador
    const al = new Set(e.al || []), nr = new Set(e.nr || []);
    const visibles = Object.keys(ALARMAS).filter((k) => al.has(k) || nr.has(k));
    $("#r-anun").hidden = !visibles.length;
    cambia($("#anun"), visibles.map((k) => `<div class="ventana ${al.has(k) ? "activa" : ""} ${GRAVES.has(k) ? "grave" : "leve"} ${nr.has(k) ? "sin-rec" : ""}" title="${esc(ALARMAS[k][1])}">${esc(ALARMAS[k][0])}</div>`).join(""));
    if (cambia($("#anun-acc"), nr.size && manda && on ? `<button class="boton chico" id="b-rec">Reconocer alarmas</button>` : "") && $("#b-rec"))
      $("#b-rec").onclick = () => conBoton($("#b-rec"), () => mandar("reconocer"));
    // sensores y red
    const tmaxS = Number(cfg?.tmax_sonda) || 60, tmaxA = Number(cfg?.tmax_amb) || 60;
    numero($("#l-tsn"), on ? e.tsn : NaN, 1);
    termometro($("#b-tsn"), on ? e.tsn : NaN, tmaxS);
    $("#c-tsn").textContent = on && !Number.isFinite(e.tsn) ? "Sin lectura de la sonda" : `Corte a ${fmt(tmaxS, 0)} °C`;
    numero($("#l-tam"), on ? e.tam : NaN, 1);
    termometro($("#b-tam"), on ? e.tam : NaN, tmaxA);
    $("#c-tam").textContent = on && Number.isFinite(e.hum) ? `${fmt(e.hum, 0)} % HR · corte a ${fmt(tmaxA, 0)} °C` : `Corte a ${fmt(tmaxA, 0)} °C`;
    $("#l-f").textContent = on ? fmt(e.f, 2) : "—";
    $("#l-rssi").textContent = on ? fmt(e.rssi, 0) : "—";
    $("#l-vnom").textContent = fmt(vnom, 0);
    rodillos($("#l-et"), Number.isFinite(e.et) ? Number(e.et) : NaN, 1);
  };

  async function mandar(o) {
    if (!enLinea(est, cfg)) throw new Error("El equipo no está en línea: la orden no le llegaría.");
    ultimaOrden = Date.now();
    const r = await fb.orden(id, o);
    notif(r.msg || "Hecho.");
    return r;
  }
  const girar = async (o) => {
    if (esperando) return;
    if (!manda) return notif("Tu usuario es de solo lectura.", "ambar");
    const e = est || {};
    if (!enLinea(est, cfg)) {
      sel.classList.remove("no-cuadra");
      void sel.offsetWidth;
      sel.classList.add("no-cuadra");
      return notif("El equipo no está en línea: la orden no le llegaría.", "ambar");
    }
    const quiere = o === "permitir";
    const espera = !e.k1 && ["limite", "arranque"].includes(e.mot);
    if (quiere === (!!e.perm && !espera) && !(quiere && espera)) return;
    esperando = true;
    pintarSelector(sel, { permiso: quiere, k1: false, esperando: true });
    try {
      await mandar(o);
    } catch (err) {
      fallo(err);
      sel.classList.remove("no-cuadra");
      void sel.offsetWidth;
      sel.classList.add("no-cuadra");
    } finally {
      esperando = false;
      pintar();
    }
  };
  $(".perilla", sel).onclick = () => girar(sel.classList.contains("en-per") ? "detener" : "permitir");
  for (const b of $$(".pos", sel)) b.onclick = () => girar(b.dataset.o);

  alSalir(fb.mirar(id));
  alSalir(fb.escuchar(`equipos/${id}/nombre`, (n) => n && ($("#t-nombre").textContent = (app.nombres ??= {})[id] = n)));
  alSalir(fb.escuchar(`entrada/${id}/config`, (c) => ((cfg = c), pintar())));
  alSalir(
    fb.escuchar(`estado/${id}`, (e) => {
      est = e;
      const antes = (app.estados[id]?.nr || []).length;
      app.estados[id] = e;
      if ((e?.nr || []).length !== antes) pintarMando(id, "panel");
      pintar();
    }),
  );
  const reloj = setInterval(pintar, 5000);
  alSalir(() => clearInterval(reloj));
  pintar();
  encender(vista);
}

// ------------------------------------------------------------------ historial
async function vHistorial(id) {
  let dias = 1;
  vista.innerHTML = `
    <header class="cabecera"><div class="titulo"><h1>Historial</h1><div class="enlace-estado" id="t-rango">—</div></div>
      <div class="rango" role="group" aria-label="Rango">${[[1, "24 h"], [7, "7 días"], [30, "30 días"]].map(([d, t]) => `<button type="button" data-d="${d}" aria-pressed="${d === dias}">${t}</button>`).join("")}</div></header>
    <section class="riel"><article class="mod" style="--d:12"><div class="resumen" id="resumen"></div></article></section>
    <section class="riel">
      <article class="mod" style="--d:12"><div class="mod-cab"><span class="rotulo"><b>P1</b> Potencia</span><small>kW</small></div><div id="g-p"></div></article>
      <article class="mod" style="--d:6"><div class="mod-cab"><span class="rotulo"><b>V1</b> Tensión</span><small>V</small></div><div id="g-v"></div></article>
      <article class="mod" style="--d:6"><div class="mod-cab"><span class="rotulo"><b>T1</b> Temperaturas</span><small><i class="muestra" style="background:var(--rojo)"></i>sonda <i class="muestra" style="background:var(--azul);margin-left:8px"></i>placa</small></div><div id="g-t"></div></article>
      <article class="mod" style="--d:12" id="m-dias"><div class="mod-cab"><span class="rotulo"><b>E1</b> Energía por día</span><small>kWh</small></div><div id="g-e"></div></article>
    </section>
    <section class="riel"><article class="mod" style="--d:12">
      <div class="mod-cab"><span class="rotulo"><b>S</b> Sesiones</span></div>
      <ul class="lista sesiones" id="sesiones"><li class="suave">Cargando…</li></ul>
      <div class="acciones"><button class="boton chico sec" id="csv-s">${icono("bajar")}CSV de sesiones</button><button class="boton chico sec" id="csv-m">${icono("bajar")}CSV de mediciones</button></div>
    </article></section>`;
  const gp = new Grafica($("#g-p"), { series: [{ nombre: "Potencia", color: "--verde", unidad: "kW", dec: 2 }], alto: 220, cero: true });
  const gv = new Grafica($("#g-v"), { series: [{ nombre: "Tensión", color: "--ambar", unidad: "V", dec: 1, relleno: false }], alto: 170 });
  const gt = new Grafica($("#g-t"), { series: [{ nombre: "Sonda", color: "--rojo", unidad: "°C", dec: 1, relleno: false }, { nombre: "Placa", color: "--azul", unidad: "°C", dec: 1, relleno: false }], alto: 170 });
  const ge = new Grafica($("#g-e"), { series: [{ nombre: "Energía", color: "--verde", unidad: "kWh", dec: 2 }], alto: 170, barras: true, vacio: "Sin sesiones en este rango." });
  alSalir(() => [gp, gv, gt, ge].forEach((g) => g.destruir()));
  const cfg = (await fb.leer(`entrada/${id}/config`).catch(() => null)) || {};
  let med = [], ses = [];

  async function cargar() {
    const hasta = ahora(), desde = hasta - dias * 86400;
    $("#t-rango").textContent = `${fDia(desde)} – ${fDia(hasta)}`;
    for (const b of $$(".rango button")) b.setAttribute("aria-pressed", String(Number(b.dataset.d) === dias));
    [med, ses] = await Promise.all([fb.mediciones(id, desde, hasta), fb.sesiones(id, 400)]);
    ses = ses.filter((s) => (s.ini || s.fin) >= desde);
    // ≤ 600 puntos por gráfica: promedio por tramo
    const tramo = Math.max(1, Math.ceil(med.length / 600));
    const prom = (k, f = (x) => x) => {
      const out = [];
      for (let i = 0; i < med.length; i += tramo) {
        const g = med.slice(i, i + tramo).filter((m) => Number.isFinite(m[k]));
        if (g.length) out.push([g[Math.floor(g.length / 2)].ts, f(g.reduce((a, m) => a + m[k], 0) / g.length)]);
      }
      return out;
    };
    const rango = [desde, hasta];
    gp.datos([prom("p", (w) => Math.max(0, w / 1000))], rango);
    gv.datos([prom("v")], rango);
    gt.datos([prom("tsn"), prom("tam")], rango);
    $("#m-dias").hidden = dias === 1;
    const porDia = new Map();
    for (const s of ses) {
      const t = s.ini || s.fin;
      const dia = Math.floor((t - 5 * 3600) / 86400) * 86400 + 5 * 3600;
      porDia.set(dia, (porDia.get(dia) || 0) + (Number(s.kwh) || 0));
    }
    ge.datos([[...porDia.entries()].sort((a, b) => a[0] - b[0])], rango);
    const kwh = ses.reduce((a, s) => a + (Number(s.kwh) || 0), 0);
    const costo = ses.reduce((a, s) => a + (Number(s.cop) || (Number(s.kwh) || 0) * (cfg.tarifa || 0)), 0);
    const pico = Math.max(0, ...med.map((m) => Number(m.p) || 0), ...ses.map((s) => Number(s.pmax) || 0));
    $("#resumen").innerHTML = `
      <div><small>Energía</small><span class="lectura l-m">${fmt(kwh, 2)}<span class="u">kWh</span></span></div>
      <div><small>Costo</small><span class="lectura l-m">${cop(costo)}</span></div>
      <div><small>Sesiones</small><span class="lectura l-m">${ses.length}</span></div>
      <div><small>Pico</small><span class="lectura l-m">${fmt(pico / 1000, 2)}<span class="u">kW</span></span></div>`;
    $("#sesiones").innerHTML = ses.length
      ? ses
          .map((s) => `<li><span class="piloto ${s.mf === "limite" ? "ambar" : "verde"}"></span><div class="crece"><b>${fCorta(s.ini)}</b><small>${duracion((s.fin || 0) - (s.ini || 0))} · pico ${fmt((s.pmax || 0) / 1000, 2)} kW · ${esc(FIN[s.mf] || s.mf || "")}</small></div>
            <div class="cifra"><span class="lectura l-m">${fmt(s.kwh, 2)}<span class="u">kWh</span></span><small>${cop(s.cop ?? (s.kwh || 0) * (cfg.tarifa || 0))}</small></div></li>`)
          .join("")
      : `<li class="suave">No hubo sesiones de carga en este rango.</li>`;
  }
  for (const b of $$(".rango button")) b.onclick = () => ((dias = Number(b.dataset.d)), cargar().catch(fallo));
  $("#csv-s").onclick = () =>
    descargar(`sesiones_${id}.csv`, [["inicio", "fin", "kwh", "costo_cop", "pico_w", "fin_por"], ...ses.map((s) => [fFecha(s.ini), fFecha(s.fin), String(s.kwh ?? "").replace(".", ","), s.cop ?? "", s.pmax ?? "", FIN[s.mf] || s.mf || ""])]);
  $("#csv-m").onclick = () =>
    descargar(`mediciones_${id}.csv`, [["fecha", "v", "i", "p_w", "fp", "hz", "kwh_sesion", "kwh_total", "t_sonda", "t_placa", "hum", "k1"], ...med.map((m) => [fFecha(m.ts), m.v, m.i, m.p, m.pf, m.f, m.es, m.et, m.tsn, m.tam, m.hum, m.k1].map((x) => (typeof x === "number" ? String(x).replace(".", ",") : x ?? "")))]);
  await cargar();
  encender(vista);
}

// ------------------------------------------------------------------ alarmas
async function vAlarmas(id) {
  const manda = puedeMandar(id);
  vista.innerHTML = `
    <header class="cabecera"><div class="titulo"><h1>Alarmas</h1><div class="enlace-estado" id="t-anun">—</div></div></header>
    <section class="riel"><article class="mod" style="--d:12">
      <div class="mod-cab"><span class="rotulo"><b>H1</b> Anunciador</span><small>titila = sin reconocer</small></div>
      <div class="anunciador" id="anun"></div><div class="acciones" id="anun-acc"></div>
    </article></section>
    <section class="riel">
      <article class="mod" style="--d:7"><div class="mod-cab"><span class="rotulo"><b>R</b> Registro del equipo</span></div><div id="eventos"><p class="suave">Cargando…</p></div></article>
      <article class="mod" style="--d:5"><div class="mod-cab"><span class="rotulo"><b>O</b> Órdenes desde la app</span></div><div id="bitacora"><p class="suave">Cargando…</p></div></article>
    </section>`;
  let est = null;
  const pintar = () => {
    const al = new Set(est?.al || []), nr = new Set(est?.nr || []);
    cambia($("#anun"), Object.keys(ALARMAS).map((k) => `<div class="ventana ${al.has(k) ? "activa" : ""} ${GRAVES.has(k) ? "grave" : "leve"} ${nr.has(k) ? "sin-rec" : ""}" title="${esc(ALARMAS[k][1])}">${esc(ALARMAS[k][0])}</div>`).join(""));
    $("#t-anun").textContent = !est ? "El equipo aún no se ha conectado" : al.size ? `${al.size} activa${al.size > 1 ? "s" : ""}${nr.size ? ` · ${nr.size} sin reconocer` : ""}` : nr.size ? `${nr.size} sin reconocer` : "Todo en orden";
    if (cambia($("#anun-acc"), nr.size && manda ? `<button class="boton" id="b-rec">${icono("check")}Reconocer alarmas</button>` : "") && $("#b-rec"))
      $("#b-rec").onclick = () =>
        conBoton($("#b-rec"), async () => {
          if (!enLinea(est)) throw new Error("El equipo no está en línea.");
          notif((await fb.orden(id, "reconocer")).msg || "Reconocidas.");
        });
  };
  alSalir(fb.escuchar(`estado/${id}`, (e) => ((est = e), (app.estados[id] = e), pintar())));
  pintar();
  const [evs, bit] = await Promise.all([fb.eventos(id, 150), fb.bitacora(id, 40).catch(() => [])]);
  $("#eventos").innerHTML = evs.length
    ? evs.map((e) => {
        const [c, t] = textoEvento(e);
        return `<div class="evento"><span class="piloto ${c}"></span><div>${esc(t)}<time>${e.ts ? fFecha(e.ts) : "sin hora"}</time></div></div>`;
      }).join("")
    : `<p class="suave">Todavía no hay eventos.</p>`;
  const nombres = app.u.admin ? (await fb.leer("usuarios").catch(() => null)) || {} : {};
  $("#bitacora").innerHTML = bit.length
    ? bit.map((b) => {
        const quien = b.por === app.u.uid ? "Tú" : nombres[b.por]?.nombre || "Otro usuario";
        const r = b.resp;
        return `<div class="evento"><span class="piloto ${!r ? "" : r.ok ? "verde" : "rojo"}"></span><div><b>${esc(quien)}</b> · ${esc((ORDENES[b.o] || b.o).toLowerCase())}<br><small>${r ? esc(r.msg || (r.ok ? "confirmada" : "rechazada")) : "sin respuesta del equipo"}</small><time>${fFecha(Math.floor((b.ts || 0) / 1000))}</time></div></div>`;
      }).join("")
    : `<p class="suave">Nadie ha dado órdenes todavía.</p>`;
  encender(vista);
}

// ------------------------------------------------------------------ ajustes
const campoNum = (k, txt, v, unidad, extra = "") =>
  `<label class="campo"><span>${txt}</span><span class="entrada"><input id="${k}" type="number" inputmode="decimal" value="${esc(v)}" ${extra}><span class="unidad">${unidad}</span></span></label>`;
const htmlFranja = (w) => `
  <div class="franja"><div class="dias">${DIAS.map((d, b) => `<label><input type="checkbox" data-b="${b}" ${(w.d >> b) & 1 ? "checked" : ""} aria-label="${NOMBRE_DIAS[b]}"><span>${d}</span></label>`).join("")}</div>
    <div class="campos"><label class="campo"><span>Desde</span><input type="time" class="vi" value="${esc(w.i)}"></label><label class="campo"><span>Hasta</span><input type="time" class="vf" value="${esc(w.f)}"></label></div>
    <button type="button" class="boton chico sec quitar">Quitar franja</button></div>`;

async function vAjustes(id) {
  const manda = puedeMandar(id);
  const admin = app.u.admin;
  const [eq, c0, est, tg] = await Promise.all([
    fb.leer(`equipos/${id}`).catch(() => null),
    fb.leer(`entrada/${id}/config`).catch(() => null),
    fb.leer(`estado/${id}`).catch(() => null),
    manda ? fb.leer(`entrada/${id}/telegram`).catch(() => null) : null,
  ]);
  const c = { ...fb.CONFIG_DEFECTO, ...(c0 || {}) };
  c.horario = { on: false, v: [], ...(c.horario || {}) };
  c.horario.v = Array.isArray(c.horario.v) ? c.horario.v : Object.values(c.horario.v || {});
  const dis = manda ? "" : "disabled";
  const aplicada = est?.cfg_v >= (c0?.v || 0);
  vista.innerHTML = `
    <header class="cabecera"><div class="titulo"><h1>Ajustes</h1>
      <div class="enlace-estado"><span class="piloto ${c0 ? (aplicada ? "verde" : "ambar respira") : ""}"></span><span>${esc(eq?.nombre || id)} · configuración v${c0?.v ?? 0}${c0 ? (aplicada ? " · aplicada en el equipo" : " · esperando al equipo") : ""}</span></div></div></header>
    <form id="f-cfg">
    <section class="riel">
      <article class="mod" style="--d:6"><div class="mod-cab"><span class="rotulo"><b>G</b> General</span></div>
        <div class="campos">
          <label class="campo"><span>Red</span><select id="vnom" ${dis}><option value="240">240 V (L1–L2)</option><option value="120">120 V (L–N)</option></select></label>
          ${campoNum("tarifa", "Tarifa", c.tarifa, "$/kWh", `min="0" step="1" ${dis}`)}
        </div><p class="ayuda">Hora de Colombia (UTC−5). La tarifa calcula el costo de cada sesión.</p></article>
      <article class="mod" style="--d:6"><div class="mod-cab"><span class="rotulo"><b>L</b> Límites por sesión</span></div>
        <div class="campos">${campoNum("lim_kwh", "Energía", c.lim_kwh, "kWh", `min="0" step="0.1" ${dis}`)}${campoNum("lim_min", "Tiempo", c.lim_min, "min", `min="0" step="1" ${dis}`)}${campoNum("lim_cop", "Costo", c.lim_cop, "$", `min="0" step="100" ${dis}`)}</div>
        <p class="ayuda">0 = sin límite. Al llegar, el equipo detiene la carga y cierra la sesión.</p></article>
      <article class="mod" style="--d:6"><div class="mod-cab"><span class="rotulo"><b>H</b> Horario de carga</span></div>
        <label class="interruptor"><span>Cargar solo dentro de estas franjas</span><input type="checkbox" id="h_on" ${c.horario.on ? "checked" : ""} ${dis}></label>
        <div id="franjas">${c.horario.v.map(htmlFranja).join("")}</div>
        ${manda ? `<button type="button" class="boton chico sec" id="mas">${icono("mas")}Agregar franja</button>` : ""}
        <p class="ayuda">Hasta 4 franjas. Si «hasta» es menor que «desde», la franja cruza la medianoche (22:00–05:00). Sin hora válida el equipo no aplica el horario.</p></article>
      <article class="mod" style="--d:6"><div class="mod-cab"><span class="rotulo"><b>T</b> Temperatura</span></div>
        <div class="campos">${campoNum("tmax_sonda", "Corte sonda", c.tmax_sonda, "°C", `min="30" max="90" ${dis}`)}${campoNum("tmax_amb", "Corte placa", c.tmax_amb, "°C", `min="30" max="85" ${dis}`)}${campoNum("t_hist", "Histéresis", c.t_hist, "°C", `min="2" max="30" ${dis}`)}</div>
        <label class="interruptor"><span>Sonda obligatoria: sin sonda, la carga se detiene por falla</span><input type="checkbox" id="sonda_req" ${c.sonda_req ? "checked" : ""} ${dis}></label>
        <p class="ayuda">Las aplica el equipo aunque no haya internet.</p></article>
      <article class="mod" style="--d:12"><div class="mod-cab"><span class="rotulo"><b>A</b> Al volver la energía</span></div>
        <p class="ayuda">K1 es normalmente abierto: sin energía, el EVSE no carga. Esto decide qué hace el equipo cuando vuelve la luz o tras un reinicio (decisión D28).</p>
        <div class="posiciones3" style="grid-template-columns:repeat(auto-fit,minmax(220px,1fr))">
          <label class="posicion"><input type="radio" name="arranque" value="restaurar" ${dis}><span><b>Restaurar</b><br><small>Vuelve el último permiso después de 10 s de verificaciones.</small></span></label>
          <label class="posicion"><input type="radio" name="arranque" value="detenida" ${dis}><span><b>Quedar detenida</b><br><small>Espera a que alguien la permita desde la app.</small></span></label>
          <label class="posicion"><input type="radio" name="arranque" value="permitida" ${dis}><span><b>Permitir siempre</b><br><small>Permite después de las verificaciones.</small></span></label>
        </div>
        <p class="ayuda">En los tres casos, tres reinicios anormales en menos de 10 min dejan la carga detenida hasta reconocer la alarma.</p></article>
      <article class="mod" style="--d:12"><details><summary><span class="rotulo"><b>X</b> Avanzado</span></summary>
        <div class="campos" style="margin-top:12px">${campoNum("i_inicio", "Corriente de inicio", c.i_inicio, "A", `min="0.2" max="10" step="0.1" ${dis}`)}${campoNum("fin_min", "Fin sin corriente", c.fin_min, "min", `min="1" max="240" ${dis}`)}${campoNum("tel_s", "Telemetría", c.tel_s, "s", `min="5" max="300" ${dis}`)}${campoNum("reg_carga_s", "Historial cargando", c.reg_carga_s, "s", `min="10" max="600" ${dis}`)}${campoNum("reg_reposo_s", "Historial en reposo", c.reg_reposo_s, "s", `min="60" max="3600" ${dis}`)}</div>
        <label class="interruptor"><span>El CT quedó al revés (invierte el signo de la potencia)</span><input type="checkbox" id="inv_ct" ${c.inv_ct ? "checked" : ""} ${dis}></label></details></article>
    </section>
    ${manda ? `<div class="riel" style="padding-top:0"><div style="grid-column:1/-1"><button class="boton verde ancho" id="b-guardar">Guardar y enviar al equipo</button></div></div>` : `<p class="suave">Tu usuario es de solo lectura.</p>`}
    </form>
    ${manda ? `<section class="riel"><article class="mod" style="--d:6"><div class="mod-cab"><span class="rotulo">${icono("telegram")}Avisos por Telegram</span></div>
      <p class="ayuda">El equipo mismo escribe a Telegram cuando hay una alarma grave o termina una carga. Crea un bot con @BotFather, pega su token y tu chat id (te lo da @userinfobot).</p>
      <form class="formulario" id="f-tg"><div class="campos"><label class="campo"><span>Token del bot</span><input name="token" value="${esc(tg?.token || "")}" autocomplete="off" placeholder="123456:ABC…"></label>
        <label class="campo"><span>Chat id</span><input name="chat" value="${esc(tg?.chat || "")}" inputmode="numeric" placeholder="123456789"></label></div>
        <div class="acciones"><button class="boton chico">Guardar</button><button type="button" class="boton chico sec" id="tg-probar">Probar</button><button type="button" class="boton chico sec" id="tg-quitar">Quitar</button></div></form>
    </article></section>` : ""}
    ${admin ? htmlAdminEquipo(id, eq, est) : ""}`;
  $("#vnom").value = String(c.vnom >= 200 ? 240 : 120);
  for (const x of $$('input[name="arranque"]')) x.checked = x.value === c.arranque;
  const franjas = $("#franjas");
  const enlazarQuitar = () => $$(".quitar", franjas).forEach((b) => (b.onclick = () => b.closest(".franja").remove()));
  enlazarQuitar();
  if ($("#mas"))
    $("#mas").onclick = () => {
      if ($$(".franja", franjas).length >= 4) return notif("Máximo 4 franjas.", "ambar");
      franjas.insertAdjacentHTML("beforeend", htmlFranja({ d: 127, i: "22:00", f: "05:00" }));
      enlazarQuitar();
    };
  $("#f-cfg").onsubmit = (e) => {
    e.preventDefault();
    if (!manda) return;
    const n = (k) => Number($("#" + k).value) || 0;
    const cfg = {
      vnom: n("vnom"), tarifa: n("tarifa"), tz: -300, lim_kwh: n("lim_kwh"), lim_min: n("lim_min"), lim_cop: n("lim_cop"),
      horario: {
        on: $("#h_on").checked,
        v: $$(".franja", franjas).map((w) => ({ d: $$("input[data-b]", w).reduce((a, x) => a | (x.checked ? 1 << Number(x.dataset.b) : 0), 0), i: $(".vi", w).value || "00:00", f: $(".vf", w).value || "00:00" })),
      },
      tmax_sonda: n("tmax_sonda"), tmax_amb: n("tmax_amb"), t_hist: n("t_hist"), sonda_req: $("#sonda_req").checked,
      arranque: $('input[name="arranque"]:checked')?.value || "restaurar",
      i_inicio: n("i_inicio"), fin_min: n("fin_min"), inv_ct: $("#inv_ct").checked, tel_s: n("tel_s"), reg_carga_s: n("reg_carga_s"), reg_reposo_s: n("reg_reposo_s"),
    };
    if (cfg.horario.on && !cfg.horario.v.length) return notif("Agrega al menos una franja o apaga el horario.", "ambar");
    conBoton($("#b-guardar"), async () => {
      const v = await fb.guardarConfig(id, cfg);
      notif(enLinea(est, c) ? `Guardada (v${v}). El equipo la aplica en segundos.` : `Guardada (v${v}). Se aplica cuando el equipo se conecte.`);
      setTimeout(() => location.hash === `#/e/${id}/ajustes` && navegar(), 2500);
    });
  };
  if ($("#f-tg")) {
    $("#f-tg").onsubmit = (e) => {
      e.preventDefault();
      const d = new FormData(e.target);
      conBoton($("button", e.target), async () => {
        await fb.escribir(`entrada/${id}/telegram`, { token: d.get("token").trim(), chat: d.get("chat").trim() });
        notif("Telegram guardado.");
      });
    };
    $("#tg-probar").onclick = (e) => conBoton(e.currentTarget, async () => notif((await fb.orden(id, "telegram_probar")).msg));
    $("#tg-quitar").onclick = (e) => conBoton(e.currentTarget, async () => (await fb.escribir(`entrada/${id}/telegram`, null), notif("Avisos de Telegram quitados."), navegar()));
  }
  if (admin) enlazarAdminEquipo(id, eq, est);
  encender(vista);
}

function htmlAdminEquipo(id, eq, est) {
  const ota = est?.ota;
  return `
    <section class="riel">
      <article class="mod" style="--d:12"><div class="mod-cab"><span class="rotulo">${icono("enlace")}Enlace del equipo</span><small>${esc(eq?.correo || "")}</small></div>
        <p class="ayuda">Este código lleva la base de datos, la API key del proyecto y la cuenta del equipo. Pégalo en la placa una sola vez. No lo publiques.</p>
        <div class="secreto"><code id="enlace">••••••••</code><button class="boton-icono" type="button" id="ver-enlace" aria-label="Mostrar el código">${icono("enlace")}</button><button class="boton-icono" type="button" id="c-enlace" aria-label="Copiar el código">${icono("copiar")}</button></div>
        <p class="ayuda" style="margin-top:12px">Por la consola serie (115200), con la placa encendida:</p>
        <pre class="consola">wifi "NOMBRE DE TU RED" CLAVE_DEL_WIFI
enlazar CÓDIGO_DE_ARRIBA
reiniciar</pre>
        <p class="ayuda">O por el portal: mantén PARAR 5 s al encender, conéctate a la red EVSE-XXXX (clave configurar-evse), abre 192.168.4.1 y pega el código.${fb.local ? " Estás en el emulador: este código sirve para el simulador (tools/simulador), no para la placa." : ""}</p>
      </article>
      <article class="mod" style="--d:6"><div class="mod-cab"><span class="rotulo"><b>C</b> Calibración del medidor</span></div>
        <p class="ayuda">Solo en S7, con el transformador de aislamiento, una carga resistiva y una referencia (docs/pruebas/PROTOCOLO_PRUEBAS.md). Ajusta Ugain e IgainN en proporción a tu referencia.</p>
        <div class="campos">${campoNum("cal-v", "Tensión de referencia", "", "V", 'step="0.01" placeholder="120,4"')}${campoNum("cal-i", "Corriente de referencia", "", "A", 'step="0.001" placeholder="9,87"')}</div>
        <pre class="consola" id="cal-datos" hidden></pre>
        <div class="acciones"><button type="button" class="boton chico sec" id="cal-leer">Leer del equipo</button><button type="button" class="boton chico" id="cal-auto">Calibrar</button><button type="button" class="boton chico sec" id="cal-fab">Valores de fábrica</button></div>
      </article>
      <article class="mod" style="--d:6"><div class="mod-cab"><span class="rotulo"><b>F</b> Firmware</span><small>instalado ${esc(est?.fw || "—")}</small></div>
        ${ota ? `<p><span class="piloto ${ota.fase === "error" ? "rojo" : ota.fase === "ok" ? "verde" : "ambar respira"}"></span> Actualización a ${esc(ota.ver)}: ${esc(ota.fase)} ${ota.pct ? `${ota.pct} %` : ""} <small>${esc(ota.msg || "")}</small></p>` : ""}
        <div id="fw-lista"><p class="suave">Cargando…</p></div>
        <p class="ayuda">Los .bin se suben en Administración → Firmware.</p>
      </article>
      <article class="mod" style="--d:6"><div class="mod-cab"><span class="rotulo">${icono("usuario")}Acceso</span></div>
        <ul class="lista" id="permisos"><li class="suave">Cargando…</li></ul>
        <form class="formulario" id="f-perm" style="margin-top:10px"><div class="campos">
          <label class="campo"><span>Usuario</span><select name="uid" id="perm-uid"></select></label>
          <label class="campo"><span>Rol</span><select name="rol"><option value="propietario">Propietario (manda)</option><option value="lectura">Solo lectura</option></select></label></div>
          <button class="boton chico">Dar acceso</button>
          <p class="ayuda">La persona crea su cuenta en esta app y aparece en la lista.</p></form>
      </article>
      <article class="mod" style="--d:6"><div class="mod-cab"><span class="rotulo">${icono("equipo")}Equipo ${esc(id)}</span></div>
        <form class="formulario" id="f-nombre"><label class="campo"><span>Nombre</span><input name="nombre" value="${esc(eq?.nombre || "")}" maxlength="40" required></label><button class="boton chico sec">Renombrar</button></form>
        <div class="acciones" style="margin-top:14px"><button type="button" class="boton chico sec" id="eq-reiniciar">Reiniciar</button><button type="button" class="boton chico sec" id="eq-clave">Clave nueva</button><button type="button" class="boton chico peligro" id="eq-borrar">Borrar equipo</button></div>
      </article>
    </section>`;
}

const hex4 = (v) => (Number.isFinite(v) ? v.toString(16).toUpperCase().padStart(4, "0") + "H" : "—");

function enlazarAdminEquipo(id, eq, est) {
  let codigo = null;
  const traer = async () => (codigo ??= await fb.codigoEnlace(id));
  $("#ver-enlace").onclick = async () => {
    try {
      $("#enlace").textContent = await traer();
    } catch (e) {
      fallo(e);
    }
  };
  $("#c-enlace").onclick = async () => {
    try {
      copiar(await traer());
    } catch (e) {
      fallo(e);
    }
  };
  const orden = (o, a) => fb.orden(id, o, a);
  $("#cal-leer").onclick = (e) =>
    conBoton(e.currentTarget, async () => {
      const d = (await orden("cal_leer")).datos || {};
      $("#cal-datos").hidden = false;
      $("#cal-datos").textContent = `${d.calibrada ? "Calibrado" : "SIN CALIBRAR (valores de fábrica)"}
Ugain ${hex4(d.ugain)}  IgainN ${hex4(d.igain_n)}  Uoffset ${hex4(d.uoffset)}  IoffsetN ${hex4(d.ioffset_n)}
PoffsetN ${hex4(d.poffset_n)}  Ngain ${hex4(d.ngain)}  Nphi ${hex4(d.nphi)}  MMode ${hex4(d.mmode)}
Chip: ${Object.entries(d.chip || {}).map(([k, v]) => `${k} ${v}`).join("  ")}
Ahora: ${fmt(d.v, 2)} V · ${fmt(d.i, 3)} A · ${fmt(d.p, 0)} W · FP ${fmt(d.pf, 3)}`;
    });
  $("#cal-auto").onclick = async (e) => {
    const b = e.currentTarget;
    const v = Number($("#cal-v").value) || 0, i = Number($("#cal-i").value) || 0;
    if (!v && !i) return notif("Escribe la tensión o la corriente de referencia.", "ambar");
    if (!(await dialogo({ titulo: "¿Calibrar el medidor?", html: `<p>Referencia: ${v ? fmt(v, 2) + " V" : "—"} · ${i ? fmt(i, 3) + " A" : "—"}. Las lecturas deben estar estables.</p>`, si: "Calibrar" }))) return;
    conBoton(b, async () => notif((await orden("cal_auto", { v, i })).msg));
  };
  $("#cal-fab").onclick = async (e) => {
    const b = e.currentTarget;
    if (!(await dialogo({ titulo: "¿Volver a los valores de fábrica?", html: "<p>Se pierde la calibración del equipo.</p>", si: "Volver", peligro: true }))) return;
    conBoton(b, async () => notif((await orden("cal_fabrica")).msg));
  };
  $("#eq-reiniciar").onclick = async (e) => {
    const b = e.currentTarget;
    if (!(await dialogo({ titulo: "¿Reiniciar el equipo?", html: "<p>K1 se abre durante el reinicio (unos 15 s) y luego aplica la política de arranque.</p>", si: "Reiniciar", peligro: true }))) return;
    conBoton(b, async () => notif((await orden("reiniciar")).msg));
  };
  $("#eq-clave").onclick = async (e) => {
    const b = e.currentTarget;
    if (!(await dialogo({ titulo: "¿Clave nueva para el equipo?", html: "<p>La placa deja de conectarse hasta que le pegues el código de enlace nuevo.</p>", si: "Cambiar", peligro: true }))) return;
    conBoton(b, async () => {
      await fb.nuevaClave(id);
      codigo = null;
      $("#enlace").textContent = await traer();
      notif("Clave cambiada. Copia el código nuevo a la placa.");
    });
  };
  $("#eq-borrar").onclick = async (e) => {
    const b = e.currentTarget;
    const d = await dialogo({ titulo: `¿Borrar «${eq?.nombre || id}»?`, html: `<p>Se borran el equipo, su historial, sus permisos y su cuenta. <b>No se puede deshacer.</b></p><label class="campo"><span>Escribe ${esc(id)} para confirmar</span><input name="ok" autocomplete="off"></label>`, si: "Borrar para siempre", peligro: true, formulario: true });
    if (!d) return;
    if (d.get("ok") !== id) return notif("No coincide: no se borró nada.", "ambar");
    conBoton(b, async () => {
      await fb.borrarEquipo(id);
      app.u = await fb.perfil(fb.auth.currentUser);
      notif("Equipo borrado.");
      location.hash = "#/";
    });
  };
  $("#f-nombre").onsubmit = (e) => {
    e.preventDefault();
    const n = new FormData(e.target).get("nombre").trim();
    conBoton($("button", e.target), async () => (await fb.escribir(`equipos/${id}/nombre`, n), notif("Nombre cambiado.")));
  };
  (async () => {
    const lista = await fb.listaFirmware();
    $("#fw-lista").innerHTML = lista.length
      ? `<ul class="lista">${lista.map((f) => `<li><div class="crece"><b>${esc(f.ver)}</b><small>${fmt(f.tam / 1024, 0)} KB · ${esc(f.notas || "")}</small></div><button type="button" class="boton chico" data-c="${esc(f.clave)}" ${f.ver === est?.fw ? "disabled" : ""}>${f.ver === est?.fw ? "Instalada" : "Instalar"}</button></li>`).join("")}</ul>`
      : `<p class="suave">No hay firmware subido.</p>`;
    for (const b of $$("button[data-c]", $("#fw-lista")))
      b.onclick = async () => {
        const f = lista.find((x) => x.clave === b.dataset.c);
        if (!(await dialogo({ titulo: `¿Instalar la ${f.ver}?`, html: "<p>El equipo baja el firmware, revisa el SHA-256 y se reinicia (K1 abierto unos 15 s). No lo hace si hay una carga en curso. Si el nuevo no llega a la app en 3 arranques, vuelve al anterior.</p>", si: "Instalar" }))) return;
        conBoton(b, async () => (await fb.pedirOta(id, f), notif("Pedido enviado. Mira el avance aquí.")));
      };
  })().catch(fallo);
  (async () => {
    const [permisos, usuarios] = await Promise.all([fb.leer(`permisos/${id}`), fb.leer("usuarios")]);
    const us = usuarios || {};
    const pm = permisos || {};
    $("#permisos").innerHTML = Object.keys(pm).length
      ? Object.entries(pm).map(([uid, r]) => `<li><div class="crece">${esc(us[uid]?.nombre || uid)}<small>${esc(us[uid]?.email || "")} · ${r === "propietario" ? "propietario" : "solo lectura"}</small></div>${uid === app.u.uid ? "" : `<button type="button" class="boton chico sec" data-u="${esc(uid)}">Quitar</button>`}</li>`).join("")
      : `<li class="suave">Solo quien administra.</li>`;
    for (const b of $$("button[data-u]", $("#permisos"))) b.onclick = () => conBoton(b, async () => (await fb.quitarPermiso(id, b.dataset.u), notif("Acceso quitado."), navegar()));
    const libres = Object.entries(us).filter(([uid]) => !pm[uid]);
    $("#perm-uid").innerHTML = libres.length ? libres.map(([uid, u]) => `<option value="${esc(uid)}">${esc(u.nombre)} · ${esc(u.email)}</option>`).join("") : `<option value="">(nadie más tiene cuenta)</option>`;
  })().catch(fallo);
  $("#f-perm").onsubmit = (e) => {
    e.preventDefault();
    const d = new FormData(e.target);
    if (!d.get("uid")) return notif("Primero la persona debe crear su cuenta en la app.", "ambar");
    conBoton($("button", e.target), async () => (await fb.darPermiso(id, d.get("uid"), d.get("rol")), notif("Acceso dado."), navegar()));
  };
}

// ------------------------------------------------------------------ perfil
async function vPerfil() {
  const tema = document.documentElement.dataset.tema || "auto";
  vista.innerHTML = `
    <header class="cabecera"><div class="titulo"><h1>${esc(app.u.nombre)}</h1><div class="enlace-estado">${esc(app.u.email)}${app.u.admin ? " · administración" : ""}</div></div></header>
    <section class="riel">
      <article class="mod" style="--d:6"><div class="mod-cab"><span class="rotulo">${icono("usuario")}Tu cuenta</span></div>
        <form class="formulario" id="f-nombre"><label class="campo"><span>Nombre</span><input name="nombre" value="${esc(app.u.nombre)}" maxlength="60" required></label><button class="boton chico sec">Guardar nombre</button></form>
        <p class="ayuda" style="margin-top:14px">Tu identificador (para darte permisos de administración en Firebase):</p>
        <div class="secreto"><code>${esc(app.u.uid)}</code><button class="boton-icono" id="c-uid" aria-label="Copiar identificador">${icono("copiar")}</button></div></article>
      <article class="mod" style="--d:6"><div class="mod-cab"><span class="rotulo">${icono("tema")}Tema</span></div>
        <div class="rango" role="group" aria-label="Tema">${[["auto", "Automático"], ["dia", "Día"], ["noche", "Noche"]].map(([k, t]) => `<button type="button" data-t="${k}" aria-pressed="${k === tema}">${t}</button>`).join("")}</div>
        <p class="ayuda">Automático sigue el modo de tu celular o computador.</p></article>
      <article class="mod" style="--d:6"><div class="mod-cab"><span class="rotulo"><b>*</b> Cambiar clave</span></div>
        <form class="formulario" id="f-clave"><label class="campo"><span>Clave actual</span><input name="actual" type="password" autocomplete="current-password" required></label>
          <label class="campo"><span>Clave nueva</span><input name="nueva" type="password" autocomplete="new-password" minlength="8" required></label><button class="boton chico">Cambiar clave</button></form></article>
      <article class="mod" style="--d:6"><div class="mod-cab"><span class="rotulo">${icono("salir")}Sesión</span></div>
        <p class="ayuda">Cierra la sesión en este navegador.</p><button class="boton sec" id="salir">${icono("salir")}Cerrar sesión</button></article>
    </section>`;
  $("#c-uid").onclick = () => copiar(app.u.uid);
  for (const b of $$(".rango button"))
    b.onclick = () => {
      const t = b.dataset.t;
      if (t === "auto") delete document.documentElement.dataset.tema;
      else document.documentElement.dataset.tema = t;
      try {
        t === "auto" ? localStorage.removeItem("tema") : localStorage.setItem("tema", t);
      } catch {}
      for (const x of $$(".rango button")) x.setAttribute("aria-pressed", String(x === b));
    };
  $("#f-nombre").onsubmit = (e) => {
    e.preventDefault();
    const n = new FormData(e.target).get("nombre").trim();
    conBoton($("button", e.target), async () => {
      await fb.guardarNombre(app.u.uid, app.u.email, n);
      app.u.nombre = n;
      pintarMando(null, "perfil");
      notif("Nombre guardado.");
    });
  };
  $("#f-clave").onsubmit = (e) => {
    e.preventDefault();
    const d = new FormData(e.target);
    conBoton($("button", e.target), async () => (await fb.cambiarClave(d.get("actual"), d.get("nueva")), e.target.reset(), notif("Clave cambiada.")));
  };
  $("#salir").onclick = () => fb.salir();
  encender(vista);
}

// ------------------------------------------------------------------ administración
async function vAdmin() {
  vista.innerHTML = `
    <header class="cabecera"><div class="titulo"><h1>Administración</h1><div class="enlace-estado">Equipos, usuarios, firmware y mantenimiento</div></div></header>
    <section class="riel">
      <article class="mod" style="--d:7"><div class="mod-cab"><span class="rotulo">${icono("equipo")}Equipos</span></div><ul class="lista" id="a-equipos"><li class="suave">Cargando…</li></ul></article>
      ${htmlAgregar()}
    </section>
    <section class="riel">
      <article class="mod" style="--d:6"><div class="mod-cab"><span class="rotulo">${icono("subir")}Subir firmware</span></div>
        <p class="ayuda">El archivo queda en <code>firmware/evse_monitor/.pio/build/placa/firmware.bin</code> al compilar. Escribe la versión que dice <code>FW_VERSION</code> en include/config.h.</p>
        <form class="formulario" id="f-fw"><div class="campos"><label class="campo"><span>Versión</span><input name="ver" required placeholder="1.0.1" pattern="[0-9A-Za-z._\\-]{1,20}"></label><label class="campo"><span>Notas</span><input name="notas" placeholder="qué cambia"></label></div>
          <label class="campo"><span>Archivo .bin</span><input type="file" name="bin" accept=".bin" required></label>
          <div class="barra" hidden id="fw-barra"><i></i></div><button class="boton">${icono("subir")}Subir</button></form></article>
      <article class="mod" style="--d:6"><div class="mod-cab"><span class="rotulo"><b>F</b> Versiones subidas</span></div><ul class="lista" id="a-fw"><li class="suave">Cargando…</li></ul></article>
    </section>
    <section class="riel">
      <article class="mod" style="--d:7"><div class="mod-cab"><span class="rotulo">${icono("usuario")}Usuarios</span></div><div class="desliza" id="a-usuarios"><p class="suave">Cargando…</p></div></article>
      <article class="mod" style="--d:5"><div class="mod-cab"><span class="rotulo"><b>M</b> Mantenimiento</span></div>
        <p class="ayuda">La base gratis guarda 1 GB. Esto borra mediciones, eventos y sesiones más viejos que lo que elijas, en todos los equipos.</p>
        <form class="formulario" id="f-limpiar"><label class="campo"><span>Conservar</span><select name="dias"><option value="730">2 años</option><option value="365">1 año</option><option value="180">6 meses</option></select></label><button class="boton sec">Borrar lo más viejo</button></form></article>
    </section>`;
  enlazarAgregar();
  const [equipos, usuarios] = await Promise.all([fb.leer("equipos"), fb.leer("usuarios")]);
  const eqs = equipos || {}, us = usuarios || {};
  $("#a-equipos").innerHTML = Object.keys(eqs).length
    ? Object.entries(eqs).map(([k, e]) => `<li><span class="piloto ${enLinea(app.estados[k]) ? "verde" : ""}"></span><div class="crece"><b>${esc(e.nombre)}</b><small>${esc(k)} · ${esc(e.correo)}</small></div><a class="boton chico sec" href="#/e/${k}/ajustes">Ajustes</a></li>`).join("")
    : `<li class="suave">Aún no hay equipos.</li>`;
  $("#a-usuarios").innerHTML = `<table class="tabla"><thead><tr><th>Nombre</th><th>Correo</th><th>Última vez</th></tr></thead><tbody>${Object.values(us)
    .sort((a, b) => (b.visto || 0) - (a.visto || 0))
    .map((u) => `<tr><td>${esc(u.nombre)}</td><td>${esc(u.email)}</td><td><small>${u.visto ? hace((Date.now() - u.visto) / 1000) : "—"}</small></td></tr>`)
    .join("")}</tbody></table>`;
  const pintarFw = async () => {
    const lista = await fb.listaFirmware();
    $("#a-fw").innerHTML = lista.length
      ? lista.map((f) => `<li><div class="crece"><b>${esc(f.ver)}</b><small>${fmt(f.tam / 1024, 0)} KB · ${fCorta(Math.floor((f.subido || 0) / 1000))} · ${esc(f.notas || "")}<br>SHA-256 ${esc(f.sha.slice(0, 16))}…</small></div><button type="button" class="boton chico sec" data-c="${esc(f.clave)}">Borrar</button></li>`).join("")
      : `<li class="suave">Ninguna todavía.</li>`;
    for (const b of $$("button[data-c]", $("#a-fw"))) b.onclick = () => conBoton(b, async () => (await fb.borrarFirmware(b.dataset.c), pintarFw()));
  };
  pintarFw().catch(fallo);
  $("#f-fw").onsubmit = (e) => {
    e.preventDefault();
    const d = new FormData(e.target);
    const barra = $("#fw-barra");
    conBoton($("button", e.target), async () => {
      barra.hidden = false;
      const info = await fb.subirFirmware(d.get("ver").trim(), d.get("notas").trim(), d.get("bin"), (f) => ($("i", barra).style.transform = `scaleX(${f.toFixed(3)})`));
      notif(`Subida la ${info.ver} (${fmt(info.tam / 1024, 0)} KB). Instálala desde los ajustes del equipo.`);
      e.target.reset();
      barra.hidden = true;
      pintarFw();
    });
  };
  $("#f-limpiar").onsubmit = async (e) => {
    e.preventDefault();
    const dias = Number(new FormData(e.target).get("dias"));
    const b = $("button", e.target);
    if (!(await dialogo({ titulo: "¿Borrar el historial viejo?", html: `<p>Se borra lo anterior a ${dias} días en todos los equipos. No se puede deshacer.</p>`, si: "Borrar", peligro: true }))) return;
    conBoton(b, async () => {
      let n = 0;
      for (const k of Object.keys(eqs)) n += await fb.limpiar(k, dias);
      notif(`Listo: ${n} registros borrados.`);
    });
  };
  encender(vista);
}

// ------------------------------------------------------------------ arranque
fb.alCambiarSesion(async (u) => {
  limpiar();
  if (!u) {
    app.u = null;
    if (!location.hash.startsWith("#/entrar")) history.replaceState(null, "", "#/entrar");
    return navegar();
  }
  try {
    app.u = await fb.perfil(u, app.nombreNuevo);
    app.nombreNuevo = null;
    app.nombres = {};
    await Promise.all(Object.keys(app.u.equipos).map(async (k) => (app.nombres[k] = (await fb.leer(`equipos/${k}/nombre`).catch(() => null)) || k)));
  } catch (e) {
    fallo(e);
    app.u = { uid: u.uid, email: u.email, nombre: u.email, admin: false, equipos: {} };
  }
  if (location.hash.startsWith("#/entrar") || !location.hash) history.replaceState(null, "", "#/");
  navegar();
});
