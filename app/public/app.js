// EVSE Monitor · app web (Firebase, sin framework). Rutas con #: #/entrar, #/, #/e/<id>[/historial|/alarmas|/ajustes],
// #/perfil, #/admin. Los datos en vivo llegan de la Realtime Database (docs/software/PROTOCOLO_MENSAJES.md).

import * as fb from "./fb.js";
import { Grafica } from "./grafica.js";
import { encender, ESCALAS_P, icono, Medidor, mimico, numero, pintarMimico, rodillos, rodillosSuave, termometro } from "./instrumentos.js";
import "./fondo.js";

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
  temp_sonda: ["Sonda muy caliente", "La sonda pasó el límite de temperatura.", "La carga se pausa y vuelve sola al enfriarse.", "termo"],
  temp_amb: ["Equipo caliente", "La placa pasó su límite de temperatura.", "La carga se pausa; revisa que el equipo ventile.", "termo"],
  sonda_falla: ["Sonda desconectada", "La sonda de temperatura no responde.", "Revisa el cable de la sonda en J4.", "termo"],
  medidor_falla: ["Medidor con falla", "El chip que mide la energía no responde bien.", "Reinicia el equipo; si sigue, recalibra.", "rayo"],
  red_baja: ["Tensión baja", "La red está por debajo del mínimo.", "La carga vuelve sola cuando la red se normaliza.", "rayo"],
  parar: ["Emergencia", "Alguien oprimió el botón PARAR.", "Quítala en Carga o sosteniendo PARAR 3 s.", "alto"],
  amb_falla: ["Sensor de la placa", "El sensor de temperatura de la placa no responde.", "Reinicia el equipo; si sigue, revísalo.", "termo"],
  sin_hora: ["Sin hora", "El equipo no sabe la hora.", "Se arregla sola al conectarse a internet.", "reloj"],
  reinicio: ["Reinicio inesperado", "El equipo se reinició solo.", "Toca «Reconocer»; si se repite, revisa la alimentación.", "reloj"],
  sin_calibrar: ["Sin calibrar", "Las medidas todavía no son exactas.", "Calibra en Ajustes → Calibración del medidor.", "ajustes"],
  temp_aviso: ["Sonda tibia", "La sonda se acerca al límite.", "Solo es un aviso: la carga sigue.", "termo"],
};
const GRAVES = new Set(["temp_sonda", "temp_amb", "sonda_falla", "medidor_falla", "red_baja", "parar", "reinicio"]);
const MOTIVOS = {
  falla: ["rojo", "Pausada por una falla", "El medidor o la sonda no responden. Mira las alarmas."],
  temperatura: ["rojo", "Pausada por temperatura alta", "La sonda o la placa pasaron el límite. Vuelve sola 5 min después de enfriarse."],
  parar: ["rojo", "Carga pausada por emergencia", "Alguien oprimió el botón PARAR del equipo. Por seguridad sigue pausada, aunque se vaya la luz, hasta que la reactives aquí o sosteniendo PARAR 3 s."],
  red: ["rojo", "Pausada por tensión baja", "La red está por debajo del mínimo. Vuelve sola cuando se normaliza durante 1 min."],
  limite: ["ambar", "Límite de la sesión alcanzado", "Se llegó al tope de energía, tiempo o costo que configuraste."],
  horario: ["ambar", "Fuera del horario de carga", "Se reanuda sola en la siguiente franja permitida."],
  app: ["gris", "Carga pausada", "La pausaste desde la app. Toca «Reanudar» cuando quieras cargar."],
  arranque: ["ambar", "Arrancando", "El equipo acaba de encender y revisa todo antes de cargar (unos 10 s)."],
};
const RESETS = { encendido: "encendido", pin_en: "botón EN", software: "software", panic: "excepción", wdt_int: "watchdog", wdt_tarea: "watchdog de tareas", wdt: "watchdog", brownout: "brownout" };
const FIN = { sin_corriente: "terminó la carga", limite: "límite", otro: "otro" };
const ORDENES = { permitir: "Reanudó la carga", detener: "Pausó la carga", reconocer: "Reconoció las alarmas", soltar_parar: "Quitó la pausa de emergencia", reiniciar: "Reinició el equipo", estado: "Pidió el estado", cal_leer: "Leyó la calibración", cal_auto: "Calibró el medidor", cal_escribir: "Escribió la calibración", cal_fabrica: "Volvió a la calibración de fábrica", telegram_probar: "Probó Telegram" };
const DIAS = ["D", "L", "M", "M", "J", "V", "S"];
const NOMBRE_DIAS = ["domingo", "lunes", "martes", "miércoles", "jueves", "viernes", "sábado"];

function textoEvento(e) {
  const al = ALARMAS[e.a]?.[0] || e.txt || e.a;
  switch (e.c) {
    case "alarma": {
      const v = Number(e.x) / 10;
      const extra = e.a?.startsWith("temp") && v > 0 ? ` (${fmt(v, 1)} °C)` : "";
      return [GRAVES.has(e.a) ? "rojo" : "ambar", `Alarma: ${al}${extra}`];
    }
    case "alarma_fin": return ["verde", `Se resolvió: ${al}`];
    case "arranque": return Number(e.n) >= 2 ? ["ambar", `El equipo se reinició solo${e.x ? ` (${e.x}.ª vez seguida)` : ""}`] : ["", "El equipo encendió"];
    case "k1": return Number(e.val) ? ["verde", "Carga habilitada (K1 cerrado)"] : ["", `Carga pausada${e.mot && MOTIVOS[e.mot] ? `: ${MOTIVOS[e.mot][1].toLowerCase()}` : ""}`];
    case "sesion_inicio": return ["verde", `Empezó una carga (nº ${fmt(e.val, 0)})`];
    case "limite": return ["ambar", `Se alcanzó el límite de ${["", "energía", "tiempo", "costo"][Number(e.val)] || "la sesión"}`];
    case "config": return ["", `Ajustes aplicados (v${fmt(e.val, 0)})`];
    case "calibracion": return ["ambar", "Calibración del medidor cambiada"];
    case "orden_local": return [Number(e.val) === 1 ? "rojo" : "verde", ["", "Se oprimió PARAR en el equipo", "Emergencia quitada en el equipo", "Emergencia quitada desde la app"][Number(e.val)] || "Orden en el equipo"];
    case "hora": return ["", "Hora sincronizada"];
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
// Cerrar la ventana de Google no es un error que valga la pena mostrar.
const fallo = (e) => (["auth/popup-closed-by-user", "auth/cancelled-popup-request"].includes(e?.code) ? null : notif(traducir(e), "rojo"));

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
    "auth/operation-not-allowed": "Ese método de entrada no está activado en Firebase Authentication.",
    "auth/popup-blocked": "El navegador bloqueó la ventana de Google: permítela y vuelve a intentar.",
    "auth/unauthorized-domain": "Este dominio no está autorizado en Firebase Authentication.",
    "auth/account-exists-with-different-credential": "Ya hay una cuenta con ese correo: entra con correo y clave.",
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
// Logo de Google (los cuatro colores de su guía de marca para el botón «Sign in with Google»).
const G_LOGO = `<svg class="ico g-logo" viewBox="0 0 48 48" aria-hidden="true"><path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/><path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/><path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/><path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/></svg>`;

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
      <button class="boton ancho verde" id="google" type="button">${G_LOGO}Entrar con Google</button>
      <div class="separador"><span>o con correo y clave</span></div>
      <div class="pestanas rango" role="tablist">
        <button type="button" data-m="entrar" aria-pressed="${modo === "entrar"}">Entrar</button>
        <button type="button" data-m="crear" aria-pressed="${modo === "crear"}">Crear cuenta</button>
      </div>
      <form class="formulario" id="f-entrar">
        ${modo === "crear" ? `<label class="campo"><span>Tu nombre</span><input name="nombre" autocomplete="name" required maxlength="60"></label>` : ""}
        <label class="campo"><span>Correo</span><input name="correo" type="email" autocomplete="email" required></label>
        <label class="campo"><span>Clave</span><input name="clave" type="password" autocomplete="${modo === "crear" ? "new-password" : "current-password"}" minlength="${modo === "crear" ? 8 : 1}" required></label>
        <button class="boton ancho sec">${modo === "crear" ? "Crear la cuenta" : "Entrar"}</button>
      </form>
      <div class="pie-enlaces">
        ${modo === "entrar" ? `<button class="enlace-boton" id="olvide" type="button">Olvidé mi clave</button>` : `<span class="suave">Después, quien administra te da acceso a un equipo.</span>`}
        ${fb.local ? `<span class="suave">Emulador local</span>` : ""}
      </div>
      <div class="pilotos-fila" aria-hidden="true"><span class="piloto verde"></span><span class="piloto ambar"></span><span class="piloto rojo"></span><small>Rev 1.0 · firmware evse_monitor</small></div>
    </article></div></div>`;
    $("#google").onclick = (e) => conBoton(e.currentTarget, () => fb.entrarConGoogle());
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
      ${app.u.admin ? htmlPasos() + htmlAgregar(5) : `
      <article class="mod" style="--d:12"><div class="mod-cab"><span class="rotulo"><b>?</b> Acceso</span></div>
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
      <a class="mod tarjeta-equipo" href="#/e/${k}" style="--m:4;--t:4;--d:4;text-decoration:none;color:inherit" data-id="${k}">
        <div class="mod-cab"><span class="rotulo"><b>${esc(k)}</b></span><span class="piloto"></span></div>
        <h2 class="nombre">${esc(app.nombres?.[k] || k)}</h2>
        <p class="lectura l-l pot">—</p><p class="dato-pie txt">Sin datos todavía</p>
      </a>`).join("")}
      ${app.u.admin ? htmlAgregar(4) : ""}
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
        $(".pot", t).innerHTML = on && Number.isFinite(e?.p) ? (Math.abs(e.p) < 1000 ? `${fmt(Math.abs(e.p), 0)}<span class="u">W</span>` : `${fmt(Math.abs(e.p) / 1000, 2)}<span class="u">kW</span>`) : "—";
        $(".txt", t).textContent = !e ? "El equipo aún no se ha conectado" : !on ? `Sin conexión · ${hace(edad(e))}` : corriendo(e) ? `Cargando · ${fmt(e.es, 2)} kWh` : MOTIVOS[e.mot]?.[1] || "En reposo";
      }),
    );
  }
  encender(vista);
}

function htmlPasos() {
  return `<article class="mod" style="--d:7"><div class="mod-cab"><span class="rotulo"><b>1·2·3</b> Primeros pasos</span></div>
    <ol class="pasos">
      <li><b>Agrega el equipo</b><span>Un id corto (por ejemplo <code>evse-01</code>), un nombre y la red donde va a quedar.</span></li>
      <li><b>Copia el código de enlace</b><span>Sale en <b>Ajustes → Enlace del equipo</b> (empieza por <code>EVSE1.</code>) y es lo único que necesita la placa.</span></li>
      <li><b>Enlaza la placa</b><span>Por USB, en la consola: <code>wifi "RED" CLAVE</code>, <code>enlazar CÓDIGO</code> y <code>reiniciar</code>. Sin computador: PARAR 5 s al encender abre el portal <b>EVSE-XXXX</b>.</span></li>
      <li><b>Listo</b><span>LED3 queda fijo y el panel dice «En línea»: ya puedes permitir o detener la carga desde aquí.</span></li>
    </ol></article>`;
}
function htmlAgregar(d = 5) {
  return `<article class="mod" style="--t:${d === 4 ? 4 : 8};--d:${d}"><div class="mod-cab"><span class="rotulo">${icono("mas")}Nuevo equipo</span></div>
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
// Botón principal del módulo de carga según la acción que toca.
const ACCION_CARGA = {
  detener: { txt: "Pausar", ico: "pausa", tono: "rojo", ayuda: "Toca para pausar la carga: la placa abre K1 y el EVSE deja de cargar." },
  permitir: { txt: "Reanudar", ico: "play", tono: "verde", ayuda: "Toca para reanudar la carga: la placa cierra K1 y el EVSE vuelve a cargar." },
  soltar_parar: { txt: "Quitar emergencia", ico: "alto", tono: "alerta", ayuda: "Toca para quitar la pausa de emergencia del botón PARAR." },
};
// Qué le pasa a la carga, dicho para cualquier usuario: tono, ícono, título, detalle y la acción del botón.
function estadoCarga(est, on) {
  const e = est || {};
  if (!est) return { tono: "gris", ico: "reloj", titulo: "Esperando al equipo", detalle: "Cuando el equipo se conecte, aquí verás si está cargando." };
  if (!on) return { tono: "gris", ico: "x", titulo: "Sin conexión con el equipo", detalle: "No llegan datos. Sus protecciones (PARAR y temperatura) siguen funcionando solas." };
  if (e.k1 && corriendo(e)) return { tono: "verde", ico: "rayo", titulo: "Cargando", detalle: "El vehículo está recibiendo energía.", accion: "detener" };
  if (e.k1) return { tono: "verde", ico: "check", titulo: "Lista para cargar", detalle: "El cargador tiene permiso. El vehículo no está tomando energía: puede estar lleno o desconectado.", accion: "detener" };
  const mot = e.mot || "app";
  const m = MOTIVOS[mot] || MOTIVOS.app;
  const ico = { parar: "alto", temperatura: "termo", falla: "alto", red: "rayo", limite: "check", horario: "reloj", arranque: "reloj", app: "pausa" }[mot] || "pausa";
  const accion = mot === "parar" ? "soltar_parar" : mot === "limite" ? "permitir" : mot === "arranque" ? (e.perm ? "detener" : "permitir") : e.perm ? "detener" : "permitir";
  return { tono: m[0], ico, titulo: m[1], detalle: m[2], accion };
}

async function vPanel(id) {
  const manda = puedeMandar(id);
  vista.innerHTML = `
    <header class="cabecera">
      <div class="titulo"><h1 id="t-nombre">${esc(app.nombres?.[id] || id)}</h1>
        <div class="enlace-estado"><span class="piloto" id="p-enlace"></span><span id="t-enlace">Conectando…</span></div></div>
      ${Object.keys(app.u.equipos).length > 1 ? `<a class="boton-icono" href="#/" aria-label="Todos los equipos">${icono("equipo")}</a>` : ""}
      <a class="boton-icono solo-movil" href="#/perfil" aria-label="Tu perfil">${icono("usuario")}</a>
    </header>
    <section class="riel" aria-label="Circuito"><article class="mod" style="--d:12"><div class="mod-cab"><span class="rotulo"><b>X0</b> Circuito de carga</span><small id="t-red"></small></div><div id="mimico"></div></article></section>
    <section class="riel" aria-label="Temperaturas y red">
      <article class="mod" style="--m:2;--t:4;--d:4"><div class="mod-cab"><span class="rotulo"><b>T1</b> Sonda</span></div>
        <div class="lectura l-m"><span id="l-tsn">—</span><span class="u">°C</span></div><div class="termo" id="b-tsn"></div><div class="dato-pie" id="c-tsn"></div></article>
      <article class="mod" style="--m:2;--t:4;--d:4"><div class="mod-cab"><span class="rotulo"><b>T2</b> Placa</span></div>
        <div class="lectura l-m"><span id="l-tam">—</span><span class="u">°C</span></div><div class="termo" id="b-tam"></div><div class="dato-pie" id="c-tam"></div></article>
      <article class="mod" style="--d:4"><div class="mod-cab"><span class="rotulo"><b>V1</b> Red</span></div>
        <div class="fila-lecturas" style="margin-top:0">
          <div><small>Frecuencia</small><span class="lectura l-m"><span id="l-f">—</span><span class="u">Hz</span></span></div>
          <div><small>WiFi</small><span class="lectura l-m"><span id="l-rssi">—</span><span class="u">dBm</span></span></div>
          <div><small>Nominal</small><span class="lectura l-m"><span id="l-vnom">—</span><span class="u">V</span></span></div>
        </div></article>
    </section>
    <section class="riel" aria-label="Consumo y permiso de carga">
      <article class="mod" style="--t:4;--d:4"><div class="mod-cab"><span class="rotulo"><b>P1</b> Potencia</span><span class="piloto" id="p-p1"></span></div>
        <div id="medidor"></div>
        <div class="potencia"><div class="lectura l-xl"><span id="l-p">—</span><span class="u" id="u-p">kW</span></div><div class="dato-pie" id="l-pmax"></div><div class="dato-pie aviso-ct" id="l-inv" hidden>El CT quedó al revés (la potencia llega negativa): gíralo o activa «El CT quedó al revés» en Ajustes → Avanzado.</div></div>
        <div class="fila-lecturas">
          <div><small>Corriente</small><span class="lectura l-m"><span id="l-i">—</span><span class="u">A</span></span></div>
          <div><small>Tensión</small><span class="lectura l-m"><span id="l-v">—</span><span class="u">V</span></span></div>
          <div><small>FP</small><span class="lectura l-m" id="l-pf">—</span></div>
        </div>
      </article>
      <article class="mod" style="--t:4;--d:4"><div class="mod-cab"><span class="rotulo"><b>E1</b> Sesión</span><small id="t-ses"></small></div>
        <div class="lectura l-l"><span id="l-es">—</span><span class="u">kWh</span></div>
        <div class="resumen" style="grid-template-columns:1fr 1fr;margin-top:12px">
          <div><small>Costo</small><b id="l-cop">—</b></div>
          <div><small>Tiempo</small><b id="l-dur">—</b></div>
          <div><small>Pico</small><b id="l-pico">—</b></div>
          <div><small>Tarifa / kWh</small><b id="l-tar">—</b></div>
        </div>
        <div class="total-energia"><small><b>E0</b> Energía total</small><div class="rodillos" id="l-et"></div><div class="dato-pie">kWh medidos desde que se instaló</div></div>
      </article>
      <article class="mod mod-carga" style="--d:4"><div class="mod-cab"><span class="rotulo"><b>K1</b> Carga</span><span class="piloto" id="p-k1"></span></div>
        <div class="carga-estado" id="c-estado" data-tono="gris" role="status" aria-live="polite">
          <span class="ce-icono" id="c-icono"></span>
          <div class="ce-texto"><h3 id="c-titulo">—</h3><p id="c-detalle"></p></div>
        </div>
        <div class="parar-vivo" id="c-parar" hidden>
          <div class="pv-cab"><span class="piloto rojo respira"></span><b>Botón PARAR oprimido ahora</b></div>
          <small id="c-parar-txt"></small>
          <div class="pv-barra" id="c-parar-barra" hidden><i></i></div>
        </div>
        <div class="pulsador-zona">
          <button type="button" class="pulsador" id="c-boton" data-tono="rojo" hidden>
            <span class="pz-halo" aria-hidden="true"></span><span class="pz-halo h2" aria-hidden="true"></span>
            <svg class="pz-espera" viewBox="0 0 140 140" aria-hidden="true"><circle cx="70" cy="70" r="66"/></svg>
            <span class="pz-cara"><span class="pz-ico" id="c-boton-ico"></span><span class="pz-txt" id="c-boton-txt"></span></span>
          </button>
          <small class="pz-ayuda" id="c-boton-ayuda"></small>
        </div>
        <ol class="camino" id="c-camino" aria-label="Recorrido de la orden hasta el relé">
          <li data-p="app"><i></i><span>App</span></li>
          <li data-p="nube"><i></i><span>Nube</span></li>
          <li data-p="placa"><i></i><span>Placa</span></li>
          <li data-p="k1"><i></i><span id="c-k1-txt">K1</span></li>
        </ol>
        <p class="c-resultado" id="c-resultado" aria-live="polite"></p>
        <p class="c-nota" id="c-nota">El botón rojo <b>PARAR</b> del equipo pausa la carga al instante, aunque no haya internet.</p>
      </article>
    </section>
    <section class="riel" id="r-anun" hidden><article class="mod" style="--d:12">
      <div class="mod-cab"><span class="rotulo"><b>H1</b> Anunciador</span><a href="#/e/${id}/alarmas" class="suave" style="margin-left:auto">Ver todo</a></div>
      <div class="anun-fila"><div class="anunciador" id="anun"></div><div class="acciones" id="anun-acc"></div></div>
    </article></section>`;
  const mim = mimico();
  $("#mimico").append(mim);
  const med = new Medidor(8);
  // Contadores en vivo: entre un dato y el siguiente (2 s mientras miras, 15 s si no) la energía sigue sumando con
  // la potencia del último dato, igual que hace la placa (∫P dt solo con P > 0). Nunca retroceden por la estimación;
  // si el dato real queda por debajo, se esperan a que lo alcance.
  let baseE = null, vistoE = { et: NaN, es: NaN };
  function contar() {
    const on = enLinea(est, cfg);
    if (!baseE || !on) return false;
    const dt = Math.min(30000, Math.max(0, performance.now() - baseE.t));
    const kwh = (baseE.p > 0 ? baseE.p : 0) * dt / 3.6e9;
    let et = baseE.et + kwh, es = baseE.ses ? baseE.es + kwh : baseE.es;
    if (Number.isFinite(vistoE.et) && et < vistoE.et && vistoE.et - et < 0.02) et = vistoE.et;
    if (Number.isFinite(vistoE.es) && es < vistoE.es && vistoE.es - es < 0.02 && baseE.ses) es = vistoE.es;
    vistoE = { et, es };
    if (Number.isFinite(et)) rodillosSuave($("#l-et"), et, 3);
    $("#l-es").textContent = fmt(es, 3);
    $("#l-cop").textContent = cop(es * (Number(cfg?.tarifa) || 0));
    return true;
  }
  const relojE = setInterval(contar, 120);
  alSalir(() => clearInterval(relojE));
  $("#medidor").append(med.el);
  let est = app.estados[id] || null, cfg = null, ultimaOrden = 0, animParar = 0;
  // escala del medidor: sube enseguida si la potencia no cabe; baja solo si cabe holgada en la menor durante 6 s
  let escalaP = null, bajarDesde = 0;
  function elegirEscala(kw) {
    const necesaria = ESCALAS_P.findIndex((x) => x.max >= kw);
    const idx = necesaria < 0 ? ESCALAS_P.length - 1 : necesaria;
    if (escalaP === null || idx > escalaP) {
      escalaP = idx;
      bajarDesde = 0;
    } else if (idx < escalaP && kw <= ESCALAS_P[escalaP - 1].max * 0.8) {
      bajarDesde ||= performance.now();
      if (performance.now() - bajarDesde > 6000) {
        escalaP = idx;
        bajarDesde = 0;
      }
    } else bajarDesde = 0;
    return ESCALAS_P[escalaP];
  }
  // orden en curso desde el pulsador: para mostrar el recorrido y cuánto tardó el relé
  let enviando = false, esperaK1 = null, tResultado = 0;

  const pintar = () => {
    const e = est || {};
    const on = enLinea(est, cfg);
    const vnom = Number(cfg?.vnom) || 240;

    $("#p-enlace").className = `piloto ${on ? "verde" : est ? "" : "ambar respira"}`;
    $("#t-enlace").textContent = !est ? "El equipo todavía no se ha conectado" : on ? `En línea · ${hace(edad(est))}${e.fw ? ` · firmware ${e.fw}` : ""}` : `Sin conexión · último dato ${hace(edad(est))}`;
    $("#t-red").textContent = vnom >= 200 ? "240 V L1–L2" : "120 V L–N";
    // potencia en magnitud: si el CT quedó al revés llega negativa, pero la carga es la misma
    const invertida = on && Number(e.p) < -20 && Number(e.i) > 0.2;
    pintarMimico(mim, on ? { ...e, p: Math.abs(Number(e.p) || 0) } : null, vnom);
    const kw = on && Number.isFinite(e.p) ? Math.abs(e.p) / 1000 : NaN;
    const escP = on && Number.isFinite(kw) ? elegirEscala(Math.max(kw, 0.0001)) : ESCALAS_P.find((x) => x.max >= (vnom >= 200 ? 8 : 4));
    med.escala(escP);
    med.ir(Number.isFinite(kw) ? kw : 0, on ? Math.abs(Number(e.pmax) || 0) / 1000 : 0);
    const uP = escP.u;
    if ($("#u-p").textContent !== uP) {
      $("#u-p").textContent = uP;
      $("#l-p").dataset.v = ""; // sin animar el salto entre kW y W
    }
    numero($("#l-p"), uP === "W" && Number.isFinite(kw) ? kw * 1000 : kw, uP === "W" ? 0 : 2);
    $("#l-inv").hidden = !invertida;
    $("#l-pmax").textContent = on && e.ses ? `Pico de la sesión ${fmt((e.pmax || 0) / 1000, 2)} kW` : on ? "Sin sesión abierta" : "";
    numero($("#l-i"), on ? e.i : NaN, 1);
    numero($("#l-v"), on ? e.v : NaN, 1);
    $("#l-pf").textContent = on && Number.isFinite(Number(e.pf)) ? fmt(Math.abs(Number(e.pf)), 2) : "—"; // FP en magnitud, como en un medidor de cargas
    const carga = on && corriendo(e);
    $("#p-p1").className = `piloto ${carga ? "verde respira" : ""}`;
    // K1: el estado en palabras simples y un solo botón con la acción que corresponde
    const c = estadoCarga(est, on);
    $("#p-k1").className = `piloto ${!on ? "" : e.k1 ? "verde" : c.tono === "gris" ? "" : c.tono}${c.tono === "rojo" && on ? " respira" : ""}`;
    $("#c-estado").dataset.tono = c.tono;
    cambia($("#c-icono"), icono(c.ico));
    $("#c-titulo").textContent = c.titulo;
    $("#c-detalle").textContent = c.detalle + (!manda && est ? " Tu usuario es de solo lectura." : "");
    const b = $("#c-boton");
    const acc = on && manda ? ACCION_CARGA[c.accion] : null;
    b.hidden = !acc;
    $("#c-boton-ayuda").textContent = acc ? (c.accion === "permitir" && e.mot === "limite" ? "Toca para empezar otra sesión de carga." : acc.ayuda) : "";
    if (acc && !enviando) {
      const txt = c.accion === "permitir" && e.mot === "limite" ? "Otra sesión" : acc.txt;
      cambia($("#c-boton-ico"), icono(acc.ico));
      $("#c-boton-txt").textContent = txt;
      b.dataset.tono = acc.tono;
      b.dataset.o = c.accion;
      b.setAttribute("aria-label", acc.ayuda);
    }
    pintarCamino(e, on);
    pintarParar(e, on);
    // sesión
    if (!contar()) numero($("#l-es"), on || est ? Number(e.es) : NaN, 3);
    const tarifa = Number(cfg?.tarifa) || 0;
    if (!on) $("#l-cop").textContent = est ? cop((Number(e.es) || 0) * tarifa) : "—";
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
    if (!on) rodillosSuave($("#l-et"), Number.isFinite(e.et) ? Number(e.et) : NaN, 3);
  };

  async function mandar(o) {
    if (!enLinea(est, cfg)) throw new Error("El equipo no está en línea: la orden no le llegaría.");
    ultimaOrden = Date.now();
    const r = await fb.orden(id, o);
    notif(r.msg || "Hecho.");
    return r;
  }
  // botón PARAR del equipo en vivo: mientras está oprimido se ve aquí; si ya había emergencia, cuenta los 3 s
  function pintarParar(e, on) {
    const vivo = on && !!e.btn;
    $("#c-parar").hidden = !vivo;
    cancelAnimationFrame(animParar);
    if (!vivo) return;
    const rearma = !!e.btn_rea;
    $("#c-parar-txt").textContent = rearma ? "Sigue sosteniéndolo para quitar la emergencia (3 s)." : "La carga quedó pausada por emergencia.";
    $("#c-parar-barra").hidden = !rearma;
    if (!rearma) return;
    const t0 = Date.now() - (Number(e.btn_ms) || 0) - Math.max(0, Math.min(3, edad(e))) * 1000;
    const paso = () => {
      const p = Math.min(1, (Date.now() - t0) / 3000);
      $("#c-parar-barra i").style.width = `${Math.round(p * 100)}%`;
      if (p < 1) animParar = requestAnimationFrame(paso);
    };
    paso();
  }
  alSalir(() => cancelAnimationFrame(animParar));

  $("#c-boton").onclick = async (ev) => {
    const b = ev.currentTarget, o = b.dataset.o;
    if (!o) return;
    if (o === "soltar_parar") {
      const ok = await dialogo({
        titulo: "¿Quitar la pausa de emergencia?",
        html: `<p>Hazlo solo si ya revisaste por qué se oprimió PARAR y todo está seguro.</p><p>${est?.perm ? "La carga se <b>reanuda</b> enseguida." : "La carga sigue pausada hasta que oprimas «Reanudar carga»."}</p>`,
        si: "Quitar la emergencia",
      });
      if (!ok) return;
    }
    await pulsar(b, o);
  };

  // ---- recorrido de la orden: App → Nube → Placa → K1 (con el tiempo que tardó cada paso)
  const pasoCamino = (p, estado = "ok") => {
    const li = $(`#c-camino [data-p="${p}"]`);
    if (li) li.className = estado;
  };
  function limpiarCamino() {
    for (const li of $$("#c-camino li")) li.className = "";
  }
  function pintarCamino(e, on) {
    // en reposo, el último paso muestra el estado real del relé y de J2
    const k1 = on && !!e.k1;
    $("#c-camino").classList.toggle("k1-on", k1);
    $("#c-k1-txt").textContent = !on ? "K1" : k1 ? "K1 cerrado" : "K1 abierto";
    if (esperaK1 && on && !!e.k1 === esperaK1.quiere) {
      const s = (performance.now() - esperaK1.t0) / 1000;
      pasoCamino("k1");
      resultado(`${esperaK1.quiere ? "K1 cerrado → J2 habilitado: el EVSE puede cargar" : "K1 abierto → J2 deshabilitado: el EVSE deja de cargar"} · confirmado por la placa en ${fmt(s, 2)} s`, "ok");
      esperaK1 = null;
    } else if (!esperaK1 && !enviando && performance.now() > tResultado) {
      $("#c-resultado").className = "c-resultado";
      $("#c-resultado").textContent = !on ? "" : k1 ? "J2 → EVSE: habilitado (puede cargar)" : "J2 → EVSE: deshabilitado (no carga)";
    }
  }
  function resultado(txt, clase) {
    const r = $("#c-resultado");
    r.className = `c-resultado ${clase}`;
    r.textContent = txt;
    tResultado = performance.now() + 9000;
  }
  async function pulsar(b, o) {
    if (enviando) return;
    const quiere = o === "permitir" ? true : o === "detener" ? false : o === "soltar_parar" ? !!est?.perm : null;
    const t0 = performance.now();
    enviando = true;
    esperaK1 = null;
    limpiarCamino();
    pasoCamino("app");
    pasoCamino("nube", "va");
    b.classList.remove("confirmado", "error");
    b.classList.add("enviando");
    $("#c-boton-txt").textContent = "Enviando…";
    resultado("Orden enviada: esperando a la placa…", "va");
    try {
      if (!enLinea(est, cfg)) throw new Error("El equipo no está en línea: la orden no le llegaría.");
      ultimaOrden = Date.now();
      await fb.orden(id, o, null, 15000, { escrito: () => (pasoCamino("nube"), pasoCamino("placa", "va")) });
      pasoCamino("nube");
      pasoCamino("placa");
      const s = (performance.now() - t0) / 1000;
      b.classList.add("confirmado");
      setTimeout(() => b.classList.remove("confirmado"), 900);
      if (quiere === null || !!est?.k1 === quiere) {
        pasoCamino("k1");
        resultado(`La placa confirmó la orden en ${fmt(s, 2)} s`, "ok");
      } else {
        pasoCamino("k1", "va");
        esperaK1 = { quiere, t0 };
        resultado(`La placa recibió la orden en ${fmt(s, 2)} s · moviendo el relé…`, "va");
        setTimeout(() => {
          if (esperaK1 && esperaK1.t0 === t0) {
            esperaK1 = null;
            pasoCamino("k1", "mal");
            const m = MOTIVOS[est?.mot]?.[1];
            resultado(`La placa aceptó la orden, pero K1 no cambió${m ? `: ${m.toLowerCase()}` : ""}.`, "mal");
          }
        }, 6000);
      }
    } catch (err) {
      fallo(err);
      b.classList.add("error");
      setTimeout(() => b.classList.remove("error"), 600);
      for (const p of ["nube", "placa", "k1"]) if (!$(`#c-camino [data-p="${p}"]`).classList.contains("ok")) pasoCamino(p, "mal");
      resultado(err.message || "La orden no llegó.", "mal");
    } finally {
      enviando = false;
      b.classList.remove("enviando");
      pintar();
    }
  }

  alSalir(fb.mirar(id));
  alSalir(fb.escuchar(`equipos/${id}/nombre`, (n) => n && ($("#t-nombre").textContent = (app.nombres ??= {})[id] = n)));
  alSalir(fb.escuchar(`entrada/${id}/config`, (c) => ((cfg = c), pintar())));
  alSalir(
    fb.escuchar(`estado/${id}`, (e) => {
      // avisos para cualquier usuario cuando la carga se pausa o se reanuda por emergencia
      if (est && e && est.mot !== "parar" && e.mot === "parar") notif("Carga pausada por emergencia: alguien oprimió el botón PARAR del equipo.", "rojo");
      else if (est && e && est.mot === "parar" && e.mot !== "parar") notif("Emergencia quitada.");
      est = e;
      // punto de partida de los contadores: el dato real y el momento en que la placa lo midió
      if (e && Number.isFinite(Number(e.et)))
        baseE = { et: Number(e.et), es: Number(e.es) || 0, ses: !!e.ses, p: Number(e.p) || 0, t: performance.now() - Math.min(30, Math.max(0, edad(e))) * 1000 };
      const antes = (app.estados[id]?.nr || []).length;
      app.estados[id] = e;
      if ((e?.nr || []).length !== antes) pintarMando(id, "panel");
      pintar();
      // latido: el piloto de enlace destella con cada dato que llega de la placa
      const pe = $("#p-enlace");
      if (pe && e) {
        pe.classList.remove("late");
        void pe.offsetWidth;
        pe.classList.add("late");
      }
    }),
  );
  const reloj = setInterval(pintar, 5000);
  alSalir(() => clearInterval(reloj));
  pintar();
  encender(vista);
}

// ------------------------------------------------------------------ historial
async function vHistorial(id) {
  // 0 = «En vivo»: los últimos 15 min, que se llenan con cada estado que manda el equipo (cada 2 s mientras miras)
  let dias = 0;
  const VIVO = 15 * 60;
  const ahoraS = () => Math.floor(fb.ahoraServidor() / 1000);
  vista.innerHTML = `
    <header class="cabecera"><div class="titulo"><h1>Historial</h1><div class="enlace-estado"><span class="piloto" id="p-vivo" hidden></span><span id="t-rango">—</span></div></div>
      <div class="rango" role="group" aria-label="Rango">${[[0, "En vivo"], [1, "24 h"], [7, "7 días"], [30, "30 días"]].map(([d, t]) => `<button type="button" data-d="${d}" aria-pressed="${d === dias}">${t}</button>`).join("")}</div></header>
    <section class="riel"><article class="mod" style="--d:12"><div class="resumen" id="resumen"></div></article></section>
    <section class="riel">
      <article class="mod" style="--d:12"><div class="mod-cab"><span class="rotulo"><b>P1</b> Potencia</span><small>kW</small></div><div id="g-p"></div></article>
      <article class="mod" style="--t:4;--d:4"><div class="mod-cab"><span class="rotulo"><b>V1</b> Tensión</span><small>V</small></div><div id="g-v"></div></article>
      <article class="mod" style="--t:4;--d:4"><div class="mod-cab"><span class="rotulo"><b>I1</b> Corriente</span><small>A</small></div><div id="g-i"></div></article>
      <article class="mod" style="--d:4"><div class="mod-cab"><span class="rotulo"><b>T1</b> Temperaturas</span><small><i class="muestra" style="background:var(--rojo)"></i>sonda <i class="muestra" style="background:var(--azul);margin-left:8px"></i>placa</small></div><div id="g-t"></div></article>
      <article class="mod" style="--d:12" id="m-dias"><div class="mod-cab"><span class="rotulo"><b>E1</b> Energía por día</span><small>kWh</small></div><div id="g-e"></div></article>
    </section>
    <section class="riel"><article class="mod" style="--d:12">
      <div class="mod-cab"><span class="rotulo"><b>S</b> Sesiones</span><small id="t-ses-rango"></small></div>
      <ul class="lista sesiones" id="sesiones"><li class="suave">Cargando…</li></ul>
      <div class="acciones"><button class="boton chico sec" id="csv-s">${icono("bajar")}CSV de sesiones</button><button class="boton chico sec" id="csv-m">${icono("bajar")}CSV de mediciones</button></div>
    </article></section>`;
  const gp = new Grafica($("#g-p"), { series: [{ nombre: "Potencia", color: "--verde", unidad: "kW", dec: 2 }], alto: 220, cero: true, vacio: "Esperando datos del equipo…" });
  const gv = new Grafica($("#g-v"), { series: [{ nombre: "Tensión", color: "--ambar", unidad: "V", dec: 1, relleno: false }], alto: 170, vacio: "Esperando datos del equipo…" });
  const gi = new Grafica($("#g-i"), { series: [{ nombre: "Corriente", color: "--azul", unidad: "A", dec: 2 }], alto: 170, cero: true, vacio: "Esperando datos del equipo…" });
  const gt = new Grafica($("#g-t"), { series: [{ nombre: "Sonda", color: "--rojo", unidad: "°C", dec: 1, relleno: false }, { nombre: "Placa", color: "--azul", unidad: "°C", dec: 1, relleno: false }], alto: 170, vacio: "Esperando datos del equipo…" });
  const ge = new Grafica($("#g-e"), { series: [{ nombre: "Energía", color: "--verde", unidad: "kWh", dec: 2 }], alto: 170, barras: true, vacio: "Sin sesiones en este rango." });
  alSalir(() => [gp, gv, gi, gt, ge].forEach((g) => g.destruir()));
  const cfg = (await fb.leer(`entrada/${id}/config`).catch(() => null)) || {};
  let med = [], ses = [], vivo = [];

  function pintarSesiones() {
    $("#sesiones").innerHTML = ses.length
      ? ses
          .map((s) => `<li><span class="piloto ${s.mf === "limite" ? "ambar" : "verde"}"></span><div class="crece"><b>${fCorta(s.ini)}</b><small>${duracion((s.fin || 0) - (s.ini || 0))} · pico ${fmt((s.pmax || 0) / 1000, 2)} kW · ${esc(FIN[s.mf] || s.mf || "")}</small></div>
            <div class="cifra"><span class="lectura l-m">${fmt(s.kwh, 2)}<span class="u">kWh</span></span><small>${cop(s.cop ?? (s.kwh || 0) * (cfg.tarifa || 0))}</small></div></li>`)
          .join("")
      : `<li class="suave">No hubo sesiones de carga en este rango.</li>`;
  }

  // En vivo: las gráficas corren con el reloj aunque no llegue nada (así se nota si el equipo dejó de mandar)
  function pintarVivo(animar) {
    const hasta = ahoraS(), desde = hasta - VIVO;
    vivo = vivo.filter((m) => m.ts >= desde - 30);
    med = vivo;
    const serie = (k, f = (x) => x) => vivo.filter((m) => Number.isFinite(m[k])).map((m) => [m.ts, f(m[k])]);
    const rango = [desde, hasta];
    gp.datos([serie("p", (w) => Math.abs(w) / 1000)], rango, animar);
    gv.datos([serie("v")], rango, animar);
    gi.datos([serie("i")], rango, animar);
    gt.datos([serie("tsn"), serie("tam")], rango, animar);
    const u = vivo[vivo.length - 1];
    const fresco = u && hasta - u.ts < 30;
    $("#p-vivo").className = `piloto ${fresco ? "verde respira" : "ambar"}`;
    $("#t-rango").textContent = fresco ? "En vivo · últimos 15 min · llega un dato cada 2 s" : u ? `Sin datos nuevos desde hace ${duracion(hasta - u.ts)}` : "Esperando al equipo…";
    $("#resumen").innerHTML = `
      <div><small>Potencia</small><span class="lectura l-m">${u ? fmt(Math.max(0, Number(u.p) || 0) / 1000, 2) : "—"}<span class="u">kW</span></span></div>
      <div><small>Corriente</small><span class="lectura l-m">${fmt(u?.i, 2)}<span class="u">A</span></span></div>
      <div><small>Tensión</small><span class="lectura l-m">${fmt(u?.v, 1)}<span class="u">V</span></span></div>
      <div><small>Sonda · placa</small><span class="lectura l-m">${fmt(u?.tsn, 1)} · ${fmt(u?.tam, 1)}<span class="u">°C</span></span></div>`;
  }

  async function cargar() {
    for (const b of $$(".rango button")) b.setAttribute("aria-pressed", String(Number(b.dataset.d) === dias));
    $("#p-vivo").hidden = dias !== 0;
    if (dias === 0) {
      const hasta = ahoraS(), desde = hasta - VIVO;
      $("#m-dias").hidden = true;
      $("#t-ses-rango").textContent = "últimas 24 h";
      const [guardadas, todas] = await Promise.all([fb.mediciones(id, desde, hasta), fb.sesiones(id, 400)]);
      // une lo que ya estaba en el historial con lo que llegó en vivo
      const porTs = new Map([...guardadas, ...vivo].map((m) => [m.ts, m]));
      vivo = [...porTs.values()].sort((a, b) => a.ts - b.ts);
      ses = todas.filter((s) => (s.ini || s.fin) >= hasta - 86400);
      pintarVivo(true);
      pintarSesiones();
      return;
    }
    const hasta = ahora(), desde = hasta - dias * 86400;
    $("#t-rango").textContent = `${fDia(desde)} – ${fDia(hasta)}`;
    $("#t-ses-rango").textContent = "";
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
    gp.datos([prom("p", (w) => Math.abs(w) / 1000)], rango);
    gv.datos([prom("v")], rango);
    gi.datos([prom("i")], rango);
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
    const pico = Math.max(0, ...med.map((m) => Math.abs(Number(m.p) || 0)), ...ses.map((s) => Math.abs(Number(s.pmax) || 0)));
    $("#resumen").innerHTML = `
      <div><small>Energía</small><span class="lectura l-m">${fmt(kwh, 2)}<span class="u">kWh</span></span></div>
      <div><small>Costo</small><span class="lectura l-m">${cop(costo)}</span></div>
      <div><small>Sesiones</small><span class="lectura l-m">${ses.length}</span></div>
      <div><small>Pico</small><span class="lectura l-m">${fmt(pico / 1000, 2)}<span class="u">kW</span></span></div>`;
    pintarSesiones();
  }

  // telemetría en vivo: el equipo la manda cada 2 s mientras la app avisa que está mirando
  alSalir(fb.mirar(id));
  alSalir(
    fb.escuchar(`estado/${id}`, (e) => {
      if (!e?.ts) return;
      const ts = Math.floor(e.ts / 1000);
      if (vivo.length && vivo[vivo.length - 1].ts >= ts) return;
      vivo.push({ ts, v: e.v, i: e.i, p: e.p, tsn: e.tsn, tam: e.tam, pf: e.pf, f: e.f, es: e.es, et: e.et, hum: e.hum, k1: e.k1 });
      if (dias === 0) pintarVivo(false);
    }),
  );
  const reloj = setInterval(() => dias === 0 && pintarVivo(false), 2000);
  alSalir(() => clearInterval(reloj));

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
      <div class="al-resumen" id="al-resumen" data-tono="gris"></div>
      <div class="al-lista" id="al-lista"></div>
    </article></section>
    <section class="riel">
      <article class="mod" style="--d:7"><div class="mod-cab"><span class="rotulo"><b>R</b> Qué pasó</span><small>lo más reciente arriba</small></div><div id="eventos"><p class="suave">Cargando…</p></div></article>
      <article class="mod" style="--d:5"><div class="mod-cab"><span class="rotulo"><b>O</b> Órdenes desde la app</span></div><div id="bitacora"><p class="suave">Cargando…</p></div></article>
      <article class="mod" style="--d:12"><div class="mod-cab"><span class="rotulo"><b>H1</b> Lo que vigila el equipo</span><small>encendida = activa · titila = sin reconocer</small></div><div class="anunciador" id="anun"></div></article>
    </section>`;
  let est = null;
  const pintar = () => {
    const al = new Set(est?.al || []), nr = new Set(est?.nr || []);
    const visibles = Object.keys(ALARMAS).filter((k) => al.has(k) || nr.has(k));
    const graves = visibles.filter((k) => GRAVES.has(k) && al.has(k));
    const tono = !est ? "gris" : graves.length ? "rojo" : visibles.length ? "ambar" : "verde";
    const titulo = !est ? "Esperando al equipo" : !visibles.length ? "Todo en orden" : al.size ? `${al.size} alarma${al.size > 1 ? "s" : ""} activa${al.size > 1 ? "s" : ""}` : "Nada activo ahora";
    const detalle = !est
      ? "Cuando el equipo se conecte, aquí verás sus alarmas."
      : !visibles.length
        ? "El equipo vigila la temperatura, el medidor, la red y el botón PARAR."
        : nr.size
          ? `${nr.size} sin reconocer: léelas y toca «Reconocer».`
          : "Ya las reconociste; se quitan solas cuando se resuelven.";
    $("#al-resumen").dataset.tono = tono;
    cambia($("#al-resumen"), `<span class="ce-icono">${icono(tono === "verde" ? "check" : tono === "gris" ? "reloj" : "alto")}</span>
      <div class="ce-texto"><h3>${esc(titulo)}</h3><p>${esc(detalle)}</p></div>
      ${nr.size && manda ? `<button class="boton" id="b-rec">${icono("check")}Reconocer</button>` : ""}`);
    if ($("#b-rec"))
      $("#b-rec").onclick = () =>
        conBoton($("#b-rec"), async () => {
          if (!enLinea(est)) throw new Error("El equipo no está en línea.");
          notif((await fb.orden(id, "reconocer")).msg || "Reconocidas.");
        });
    // una tarjeta por alarma: qué pasa y qué hacer, primero las graves
    const orden = [...visibles].sort((a, b) => (GRAVES.has(b) && al.has(b)) - (GRAVES.has(a) && al.has(a)));
    cambia($("#al-lista"), orden.map((k) => {
      const [t, que, hacer, ico] = ALARMAS[k];
      const grave = GRAVES.has(k);
      const etiqueta = !al.has(k) ? "ya pasó" : grave ? "grave" : "aviso";
      return `<div class="al-item" data-tono="${!al.has(k) ? "gris" : grave ? "rojo" : "ambar"}">
        <span class="al-ico">${icono(ico)}</span>
        <div><div class="al-cab"><b>${esc(t)}</b><span class="al-tag">${etiqueta}</span>${nr.has(k) ? `<span class="al-tag nr">sin reconocer</span>` : ""}</div>
          <p>${esc(que)}</p><p class="al-hacer">${esc(hacer)}</p></div></div>`;
    }).join(""));
    $("#t-anun").textContent = !est ? "—" : visibles.length ? `${visibles.length} para revisar` : "Sin alarmas";
    cambia($("#anun"), Object.keys(ALARMAS).map((k) => `<div class="ventana ${al.has(k) ? "activa" : ""} ${GRAVES.has(k) ? "grave" : "leve"} ${nr.has(k) ? "sin-rec" : ""}" title="${esc(ALARMAS[k][1])}">${esc(ALARMAS[k][0])}</div>`).join(""));
  };
  alSalir(fb.escuchar(`estado/${id}`, (e) => ((est = e), (app.estados[id] = e), pintar())));
  pintar();
  const [evs, bit] = await Promise.all([fb.eventos(id, 80), fb.bitacora(id, 30).catch(() => [])]);
  const t0 = ahora();
  $("#eventos").innerHTML = evs.length
    ? evs.map((e) => {
        const [c, t] = textoEvento(e);
        return `<div class="evento"><span class="piloto ${c}"></span><div>${esc(t)}<time>${e.ts ? `${hace(t0 - e.ts)} · ${fCorta(e.ts)}` : "sin hora"}</time></div></div>`;
      }).join("")
    : `<p class="suave">Todavía no hay eventos.</p>`;
  const nombres = app.u.admin ? (await fb.leer("usuarios").catch(() => null)) || {} : {};
  $("#bitacora").innerHTML = bit.length
    ? bit.map((b) => {
        const quien = b.por === app.u.uid ? "Tú" : nombres[b.por]?.nombre || "Otro usuario";
        const r = b.resp;
        const ts = Math.floor((b.ts || 0) / 1000);
        return `<div class="evento"><span class="piloto ${!r ? "" : r.ok ? "verde" : "rojo"}"></span><div><b>${esc(quien)}</b> ${esc((ORDENES[b.o] || b.o).toLowerCase())}<br><small>${r ? (r.ok ? "La placa la cumplió" : `La placa la rechazó: ${esc(r.msg || "")}`) : "Sin respuesta del equipo"}</small><time>${hace(t0 - ts)} · ${fCorta(ts)}</time></div></div>`;
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
      <article class="mod" style="--t:4;--d:6"><div class="mod-cab"><span class="rotulo"><b>G</b> General</span></div>
        <div class="campos">
          <label class="campo"><span>Red</span><select id="vnom" ${dis}><option value="240">240 V (L1–L2)</option><option value="120">120 V (L–N)</option></select></label>
          ${campoNum("tarifa", "Tarifa", c.tarifa, "$/kWh", `min="0" step="1" ${dis}`)}
        </div><p class="ayuda">Hora de Colombia (UTC−5). La tarifa calcula el costo de cada sesión.</p></article>
      <article class="mod" style="--t:4;--d:6"><div class="mod-cab"><span class="rotulo"><b>L</b> Límites por sesión</span></div>
        <div class="campos">${campoNum("lim_kwh", "Energía", c.lim_kwh, "kWh", `min="0" step="0.1" ${dis}`)}${campoNum("lim_min", "Tiempo", c.lim_min, "min", `min="0" step="1" ${dis}`)}${campoNum("lim_cop", "Costo", c.lim_cop, "$", `min="0" step="100" ${dis}`)}</div>
        <p class="ayuda">0 = sin límite. Al llegar, el equipo detiene la carga y cierra la sesión.</p></article>
      <article class="mod" style="--t:4;--d:6"><div class="mod-cab"><span class="rotulo"><b>H</b> Horario de carga</span></div>
        <label class="interruptor"><span>Cargar solo dentro de estas franjas</span><input type="checkbox" id="h_on" ${c.horario.on ? "checked" : ""} ${dis}></label>
        <div id="franjas">${c.horario.v.map(htmlFranja).join("")}</div>
        ${manda ? `<button type="button" class="boton chico sec" id="mas">${icono("mas")}Agregar franja</button>` : ""}
        <p class="ayuda">Hasta 4 franjas. Si «hasta» es menor que «desde», la franja cruza la medianoche (22:00–05:00). Sin hora válida el equipo no aplica el horario.</p></article>
      <article class="mod" style="--t:4;--d:6"><div class="mod-cab"><span class="rotulo"><b>T</b> Temperatura</span></div>
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
    ${manda ? `<section class="riel"><article class="mod" style="--d:12"><div class="mod-cab"><span class="rotulo">${icono("telegram")}Avisos por Telegram</span></div>
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
      <article class="mod" style="--t:4;--d:6"><div class="mod-cab"><span class="rotulo"><b>C</b> Calibración del medidor</span></div>
        <p class="ayuda">Solo en S7, con el transformador de aislamiento, una carga resistiva y una referencia (docs/pruebas/PROTOCOLO_PRUEBAS.md). Ajusta Ugain e IgainN en proporción a tu referencia.</p>
        <div class="campos">${campoNum("cal-v", "Tensión de referencia", "", "V", 'step="0.01" placeholder="120,4"')}${campoNum("cal-i", "Corriente de referencia", "", "A", 'step="0.001" placeholder="9,87"')}</div>
        <pre class="consola" id="cal-datos" hidden></pre>
        <div class="acciones"><button type="button" class="boton chico sec" id="cal-leer">Leer del equipo</button><button type="button" class="boton chico" id="cal-auto">Calibrar</button><button type="button" class="boton chico sec" id="cal-fab">Valores de fábrica</button></div>
      </article>
      <article class="mod" style="--t:4;--d:6"><div class="mod-cab"><span class="rotulo"><b>F</b> Firmware</span><small>instalado ${esc(est?.fw || "—")}</small></div>
        ${ota ? `<p><span class="piloto ${ota.fase === "error" ? "rojo" : ota.fase === "ok" ? "verde" : "ambar respira"}"></span> Actualización a ${esc(ota.ver)}: ${esc(ota.fase)} ${ota.pct ? `${ota.pct} %` : ""} <small>${esc(ota.msg || "")}</small></p>` : ""}
        <div id="fw-lista"><p class="suave">Cargando…</p></div>
        <p class="ayuda">Los .bin se suben en Administración → Firmware.</p>
      </article>
      <article class="mod" style="--t:4;--d:6"><div class="mod-cab"><span class="rotulo">${icono("usuario")}Acceso</span></div>
        <ul class="lista" id="permisos"><li class="suave">Cargando…</li></ul>
        <form class="formulario" id="f-perm" style="margin-top:10px"><div class="campos">
          <label class="campo"><span>Usuario</span><select name="uid" id="perm-uid"></select></label>
          <label class="campo"><span>Rol</span><select name="rol"><option value="propietario">Propietario (manda)</option><option value="lectura">Solo lectura</option></select></label></div>
          <button class="boton chico">Dar acceso</button>
          <p class="ayuda">La persona crea su cuenta en esta app y aparece en la lista.</p></form>
      </article>
      <article class="mod" style="--t:4;--d:6"><div class="mod-cab"><span class="rotulo">${icono("equipo")}Equipo ${esc(id)}</span></div>
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
      <article class="mod" style="--t:4;--d:6"><div class="mod-cab"><span class="rotulo">${icono("usuario")}Tu cuenta</span></div>
        <form class="formulario" id="f-nombre"><label class="campo"><span>Nombre</span><input name="nombre" value="${esc(app.u.nombre)}" maxlength="60" required></label><button class="boton chico sec">Guardar nombre</button></form>
        <p class="ayuda" style="margin-top:14px">Tu identificador (para darte permisos de administración en Firebase):</p>
        <div class="secreto"><code>${esc(app.u.uid)}</code><button class="boton-icono" id="c-uid" aria-label="Copiar identificador">${icono("copiar")}</button></div></article>
      <article class="mod" style="--t:4;--d:6"><div class="mod-cab"><span class="rotulo">${icono("tema")}Tema</span></div>
        <div class="rango" role="group" aria-label="Tema">${[["auto", "Automático"], ["dia", "Día"], ["noche", "Noche"]].map(([k, t]) => `<button type="button" data-t="${k}" aria-pressed="${k === tema}">${t}</button>`).join("")}</div>
        <p class="ayuda">Automático sigue el modo de tu celular o computador.</p></article>
      <article class="mod" style="--t:4;--d:6" ${fb.tieneClave() ? "" : "hidden"}><div class="mod-cab"><span class="rotulo"><b>*</b> Cambiar clave</span></div>
        <form class="formulario" id="f-clave"><label class="campo"><span>Clave actual</span><input name="actual" type="password" autocomplete="current-password" required></label>
          <label class="campo"><span>Clave nueva</span><input name="nueva" type="password" autocomplete="new-password" minlength="8" required></label><button class="boton chico">Cambiar clave</button></form></article>
      <article class="mod" style="${fb.tieneClave() ? "--t:4;--d:6" : "--d:12"}"><div class="mod-cab"><span class="rotulo">${icono("salir")}Sesión</span></div>
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
      <article class="mod" style="--t:4;--d:6"><div class="mod-cab"><span class="rotulo">${icono("subir")}Subir firmware</span></div>
        <p class="ayuda">El archivo queda en <code>firmware/evse_monitor/.pio/build/placa/firmware.bin</code> al compilar. Escribe la versión que dice <code>FW_VERSION</code> en include/config.h.</p>
        <form class="formulario" id="f-fw"><div class="campos"><label class="campo"><span>Versión</span><input name="ver" required placeholder="1.0.1" pattern="[0-9A-Za-z._\\-]{1,20}"></label><label class="campo"><span>Notas</span><input name="notas" placeholder="qué cambia"></label></div>
          <label class="campo"><span>Archivo .bin</span><input type="file" name="bin" accept=".bin" required></label>
          <div class="barra" hidden id="fw-barra"><i></i></div><button class="boton">${icono("subir")}Subir</button></form></article>
      <article class="mod" style="--t:4;--d:6"><div class="mod-cab"><span class="rotulo"><b>F</b> Versiones subidas</span></div><ul class="lista" id="a-fw"><li class="suave">Cargando…</li></ul></article>
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
