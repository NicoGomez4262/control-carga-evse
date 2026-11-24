// Utilidades comunes del Worker y del Durable Object.

export const ahora = () => Math.floor(Date.now() / 1000);

export function json(datos, estado = 200, cabeceras = {}) {
  return new Response(JSON.stringify(datos), {
    status: estado,
    headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store", ...cabeceras },
  });
}

export const error = (estado, msg) => json({ error: msg }, estado);

export function hex(buf) {
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

export async function sha256(texto) {
  const datos = typeof texto === "string" ? new TextEncoder().encode(texto) : texto;
  return hex(await crypto.subtle.digest("SHA-256", datos));
}

export function aleatorio(bytes = 32) {
  const b = crypto.getRandomValues(new Uint8Array(bytes));
  return btoa(String.fromCharCode(...b)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

// Token de equipo: 24 bytes al azar en base64url, que empiece por letra o número (cómodo en consolas).
export function tokenEquipo() {
  let t;
  do t = aleatorio(24);
  while (!/^[A-Za-z0-9]/.test(t));
  return t;
}

// Comparación en tiempo constante de dos cadenas hexadecimales.
export function iguales(a, b) {
  if (typeof a !== "string" || typeof b !== "string" || a.length !== b.length) return false;
  let d = 0;
  for (let k = 0; k < a.length; k++) d |= a.charCodeAt(k) ^ b.charCodeAt(k);
  return d === 0;
}

export function cookies(req) {
  const out = {};
  for (const par of (req.headers.get("cookie") || "").split(";")) {
    const i = par.indexOf("=");
    if (i > 0) out[par.slice(0, i).trim()] = decodeURIComponent(par.slice(i + 1).trim());
  }
  return out;
}

export async function cuerpo(req) {
  try {
    return await req.json();
  } catch {
    return {};
  }
}

export const ID_EQUIPO = /^[a-z0-9][a-z0-9-]{2,31}$/;
export const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

// Configuración por defecto del equipo (la misma que tiene el firmware, src/tipos.cpp).
export const CONFIG_DEFECTO = {
  vnom: 120,
  tarifa: 900,
  tz: -300,
  tmax_sonda: 60,
  tmax_amb: 60,
  t_hist: 10,
  sonda_req: true,
  arranque: "restaurar",
  lim_kwh: 0,
  lim_min: 0,
  lim_cop: 0,
  horario: { on: false, v: [] },
  i_inicio: 1,
  fin_min: 10,
  inv_ct: false,
  tel_s: 15,
  reg_carga_s: 30,
  reg_reposo_s: 300,
};

const num = (v, a, b, d) => {
  const x = Number(v);
  return Number.isFinite(x) ? Math.min(b, Math.max(a, x)) : d;
};
const hhmm = (s, d) => (typeof s === "string" && /^([01]\d|2[0-3]):[0-5]\d$/.test(s) ? s : d);

// Valida y completa una configuración que llega de la app. El firmware vuelve a revisar los rangos.
export function limpiarConfig(c, base = CONFIG_DEFECTO) {
  const b = { ...CONFIG_DEFECTO, ...base };
  c = c || {};
  const out = {
    vnom: Number(c.vnom ?? b.vnom) >= 200 ? 240 : 120,
    tarifa: num(c.tarifa, 0, 100000, b.tarifa),
    tz: Math.round(num(c.tz, -720, 840, b.tz)),
    tmax_sonda: num(c.tmax_sonda, 30, 90, b.tmax_sonda),
    tmax_amb: num(c.tmax_amb, 30, 85, b.tmax_amb),
    t_hist: num(c.t_hist, 2, 30, b.t_hist),
    sonda_req: typeof c.sonda_req === "boolean" ? c.sonda_req : b.sonda_req,
    arranque: ["detenida", "restaurar", "permitida"].includes(c.arranque) ? c.arranque : b.arranque,
    lim_kwh: num(c.lim_kwh, 0, 500, b.lim_kwh),
    lim_min: Math.round(num(c.lim_min, 0, 2880, b.lim_min)),
    lim_cop: num(c.lim_cop, 0, 10000000, b.lim_cop),
    horario: { on: false, v: [] },
    i_inicio: num(c.i_inicio, 0.2, 10, b.i_inicio),
    fin_min: Math.round(num(c.fin_min, 1, 240, b.fin_min)),
    inv_ct: typeof c.inv_ct === "boolean" ? c.inv_ct : b.inv_ct,
    tel_s: Math.round(num(c.tel_s, 5, 300, b.tel_s)),
    reg_carga_s: Math.round(num(c.reg_carga_s, 10, 600, b.reg_carga_s)),
    reg_reposo_s: Math.round(num(c.reg_reposo_s, 60, 3600, b.reg_reposo_s)),
  };
  const h = c.horario ?? b.horario ?? {};
  out.horario.on = !!h.on;
  out.horario.v = (Array.isArray(h.v) ? h.v : []).slice(0, 4).map((w) => ({
    d: Math.round(num(w.d, 0, 127, 127)),
    i: hhmm(w.i, "00:00"),
    f: hhmm(w.f, "00:00"),
  }));
  return out;
}
