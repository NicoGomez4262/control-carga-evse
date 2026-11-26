// Capa de datos: Firebase Authentication + Realtime Database (D31). Rutas en docs/software/PROTOCOLO_MENSAJES.md.
// En 127.0.0.1 / localhost usa el emulador («npm run emular»); publicado, toma la configuración que Firebase
// Hosting sirve en /__/firebase/init.json (no hay claves en el repositorio).

const V = "13.4.0";
const SDK = `https://www.gstatic.com/firebasejs/${V}`;
const { initializeApp, deleteApp } = await import(`${SDK}/firebase-app.js`);
const A = await import(`${SDK}/firebase-auth.js`);
const D = await import(`${SDK}/firebase-database.js`);

export const local = ["127.0.0.1", "localhost"].includes(location.hostname);
const DEMO = "demo-evse";

async function leerConfig() {
  if (local) {
    return { apiKey: "demo-key", projectId: DEMO, authDomain: `${DEMO}.firebaseapp.com`, databaseURL: `https://${DEMO}-default-rtdb.firebaseio.com` };
  }
  const r = await fetch("/__/firebase/init.json");
  if (!r.ok) throw new Error("No se encontró la configuración de Firebase (¿publicaste con «firebase deploy»?).");
  const c = await r.json();
  c.databaseURL ||= `https://${c.projectId}-default-rtdb.firebaseio.com`;
  return c;
}

export const config = await leerConfig();
const app = initializeApp(config);
export const auth = A.getAuth(app);
export const db = D.getDatabase(app);
if (local) {
  A.connectAuthEmulator(auth, `http://${location.hostname}:9099`, { disableWarnings: true });
  D.connectDatabaseEmulator(db, location.hostname, 9000);
}
// Dirección de la base que va en el código de enlace del equipo.
export const dbEnlace = local ? `http://127.0.0.1:9000/?ns=${DEMO}-default-rtdb` : config.databaseURL.replace(/\/$/, "");

const { ref, get, set, update, push, remove, onValue, query, orderByKey, orderByChild, startAt, endAt, limitToLast, limitToFirst, serverTimestamp } = D;
export { serverTimestamp };

export const r = (ruta) => ref(db, ruta);
export async function leer(ruta) {
  return (await get(r(ruta))).val();
}
export const escribir = (ruta, v) => set(r(ruta), v);
export const actualizar = (cambios) => update(ref(db), cambios);
export function escuchar(ruta, cb, error) {
  return onValue(r(ruta), (s) => cb(s.val()), (e) => (error ? error(e) : console.warn(ruta, e.message)));
}

// Diferencia entre el reloj del servidor y el del navegador (para saber si el equipo está en línea).
let desfase = 0;
onValue(ref(db, ".info/serverTimeOffset"), (s) => (desfase = s.val() || 0));
export const ahoraServidor = () => Date.now() + desfase;

// ------------------------------------------------------------------ sesión
export const alCambiarSesion = (cb) => A.onAuthStateChanged(auth, cb);
export const entrar = (correo, clave) => A.signInWithEmailAndPassword(auth, correo, clave);
export const crearCuenta = (correo, clave) => A.createUserWithEmailAndPassword(auth, correo, clave);
// Google: ventana emergente; «select_account» deja elegir cuenta si el navegador tiene varias.
export function entrarConGoogle() {
  const p = new A.GoogleAuthProvider();
  p.setCustomParameters({ prompt: "select_account" });
  return A.signInWithPopup(auth, p);
}
// ¿La cuenta tiene clave propia? (las que entran solo con Google no la tienen)
export const tieneClave = () => !!auth.currentUser?.providerData.some((p) => p.providerId === "password");
export const salir = () => A.signOut(auth);
export const recuperar = (correo) => A.sendPasswordResetEmail(auth, correo);
export async function cambiarClave(actual, nueva) {
  const u = auth.currentUser;
  await A.reauthenticateWithCredential(u, A.EmailAuthProvider.credential(u.email, actual));
  await A.updatePassword(u, nueva);
}

export async function perfil(u, nombreNuevo) {
  const [admin, mios, yo] = await Promise.all([
    leer(`admins/${u.uid}`).catch(() => null),
    leer(`mis_equipos/${u.uid}`).catch(() => null),
    leer(`usuarios/${u.uid}`).catch(() => null),
  ]);
  const nombre = yo?.nombre || nombreNuevo || u.displayName || u.email.split("@")[0];
  await set(r(`usuarios/${u.uid}`), { email: u.email, nombre, visto: serverTimestamp() }).catch(() => {});
  let equipos = mios || {};
  if (admin === true) {
    const todos = (await leer("equipos").catch(() => null)) || {};
    equipos = Object.fromEntries(Object.keys(todos).map((k) => [k, "propietario"]));
  }
  return { uid: u.uid, email: u.email, nombre, admin: admin === true, equipos };
}
export const guardarNombre = (uid, email, nombre) => set(r(`usuarios/${uid}`), { email, nombre, visto: serverTimestamp() });

// ------------------------------------------------------------------ órdenes con confirmación del equipo
// al.escrito(): la orden ya quedó en la base (la app lo usa para mostrar el recorrido App → Nube → Placa → K1)
export function orden(eq, o, a, espera = 15000, al = {}) {
  const uid = auth.currentUser.uid;
  const nueva = push(r(`entrada/${eq}/ordenes`));
  const id = nueva.key;
  return new Promise((resolver, rechazar) => {
    let quitar = () => {};
    const t = setTimeout(async () => {
      quitar();
      await remove(nueva).catch(() => {});
      rechazar(new Error("El equipo no respondió en 15 s. ¿Está en línea?"));
    }, espera);
    quitar = onValue(r(`respuestas/${eq}/${id}`), (s) => {
      const v = s.val();
      if (!v) return;
      clearTimeout(t);
      quitar();
      (v.ok ? resolver : (x) => rechazar(Object.assign(new Error(x.msg || "El equipo rechazó la orden"), { datos: x.datos })))(v);
    });
    const cuerpo = { o, por: uid, ts: serverTimestamp() };
    if (a && Object.keys(a).length) cuerpo.a = a;
    Promise.all([set(nueva, cuerpo), set(r(`bitacora/${eq}/${id}`), { o, por: uid, ts: serverTimestamp() }).catch(() => {})]).then(() => al.escrito?.()).catch((e) => {
      clearTimeout(t);
      quitar();
      rechazar(e);
    });
  });
}

// La app avisa cada 20 s que está abierta: el equipo manda telemetría cada 2 s mientras tanto.
export function mirar(eq) {
  const latido = () => document.visibilityState === "visible" && set(r(`entrada/${eq}/mirando`), serverTimestamp()).catch(() => {});
  latido();
  const id = setInterval(latido, 20000);
  document.addEventListener("visibilitychange", latido);
  return () => {
    clearInterval(id);
    document.removeEventListener("visibilitychange", latido);
  };
}

export async function guardarConfig(eq, cfg) {
  const actual = (await leer(`entrada/${eq}/config`)) || {};
  const v = (Number(actual.v) || 0) + 1;
  await set(r(`entrada/${eq}/config`), { ...cfg, v, por: auth.currentUser.uid });
  return v;
}

// ------------------------------------------------------------------ historial
export async function mediciones(eq, desde, hasta) {
  const s = await get(query(r(`mediciones/${eq}`), orderByKey(), startAt(String(desde)), endAt(String(hasta))));
  const out = [];
  s.forEach((h) => void out.push({ ts: Number(h.key), ...h.val() }));
  return out;
}
export async function sesiones(eq, n = 200) {
  const s = await get(query(r(`sesiones/${eq}`), orderByKey(), limitToLast(n)));
  const out = [];
  s.forEach((h) => void out.push({ clave: h.key, ...h.val() }));
  return out.reverse();
}
export async function eventos(eq, n = 150) {
  const s = await get(query(r(`eventos/${eq}`), orderByKey(), limitToLast(n)));
  const out = [];
  s.forEach((h) => void out.push({ clave: h.key, ...h.val() }));
  return out.reverse();
}
export async function bitacora(eq, n = 40) {
  const [b, resp] = await Promise.all([
    get(query(r(`bitacora/${eq}`), orderByChild("ts"), limitToLast(n))),
    get(query(r(`respuestas/${eq}`), orderByChild("ts"), limitToLast(n * 2))),
  ]);
  const rs = resp.val() || {};
  const out = [];
  b.forEach((h) => void out.push({ id: h.key, ...h.val(), resp: rs[h.key] || null }));
  return out.reverse();
}

// ------------------------------------------------------------------ administración de equipos
const base64url = (txt) => btoa(String.fromCharCode(...new TextEncoder().encode(txt))).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
const azar = (n) => {
  const abc = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789";
  return Array.from(crypto.getRandomValues(new Uint8Array(n)), (b) => abc[b % abc.length]).join("");
};

async function conCuentaAparte(f) {
  const otra = initializeApp(config, "alta-" + Date.now());
  const aa = A.getAuth(otra);
  if (local) A.connectAuthEmulator(aa, `http://${location.hostname}:9099`, { disableWarnings: true });
  try {
    return await f(aa);
  } finally {
    await A.signOut(aa).catch(() => {});
    await deleteApp(otra).catch(() => {});
  }
}

export const ID_VALIDO = /^[a-z0-9][a-z0-9_-]{1,23}$/;
export const CONFIG_DEFECTO = {
  vnom: 240, tarifa: 900, tz: -300, tmax_sonda: 60, tmax_amb: 60, t_hist: 10, sonda_req: true, arranque: "restaurar",
  lim_kwh: 0, lim_min: 0, lim_cop: 0, horario: { on: false, v: [] }, i_inicio: 1, fin_min: 10, inv_ct: false,
  tel_s: 15, reg_carga_s: 30, reg_reposo_s: 300,
};

export async function crearEquipo(id, nombre, vnom) {
  if (!ID_VALIDO.test(id)) throw new Error("El id lleva minúsculas, números, - o _ (2 a 24), p. ej. evse-01.");
  if (await leer(`equipos/${id}`)) throw new Error(`Ya existe un equipo «${id}».`);
  const correo = `${id}.${azar(4).toLowerCase()}@equipos.invalid`;
  const clave = azar(24);
  const uid = await conCuentaAparte(async (aa) => (await A.createUserWithEmailAndPassword(aa, correo, clave)).user.uid);
  const yo = auth.currentUser.uid;
  await actualizar({
    [`equipos/${id}`]: { nombre, uid, correo, creado: serverTimestamp() },
    [`dispositivos/${uid}`]: id,
    [`claves/${id}`]: clave,
    [`permisos/${id}/${yo}`]: "propietario",
    [`mis_equipos/${yo}/${id}`]: "propietario",
    [`entrada/${id}/config`]: { ...CONFIG_DEFECTO, vnom, v: 1, por: yo },
  });
  return id;
}

export async function codigoEnlace(id) {
  const [eq, clave] = await Promise.all([leer(`equipos/${id}`), leer(`claves/${id}`)]);
  if (!eq || !clave) throw new Error("No encontré la cuenta del equipo.");
  return "EVSE1." + base64url(JSON.stringify({ d: dbEnlace, k: config.apiKey, e: eq.correo, c: clave }));
}

export async function nuevaClave(id) {
  const [eq, vieja] = await Promise.all([leer(`equipos/${id}`), leer(`claves/${id}`)]);
  const nueva = azar(24);
  await conCuentaAparte(async (aa) => {
    const c = await A.signInWithEmailAndPassword(aa, eq.correo, vieja);
    await A.updatePassword(c.user, nueva);
  });
  await escribir(`claves/${id}`, nueva);
}

export async function borrarEquipo(id) {
  const [eq, clave, permisos] = await Promise.all([leer(`equipos/${id}`), leer(`claves/${id}`), leer(`permisos/${id}`)]);
  const cambios = {};
  for (const k of ["equipos", "entrada", "estado", "respuestas", "mediciones", "eventos", "sesiones", "subido", "claves", "permisos", "bitacora"])
    cambios[`${k}/${id}`] = null;
  for (const uid of Object.keys(permisos || {})) cambios[`mis_equipos/${uid}/${id}`] = null;
  if (eq?.uid) cambios[`dispositivos/${eq.uid}`] = null;
  await actualizar(cambios);
  if (eq?.correo && clave)
    await conCuentaAparte(async (aa) => {
      const c = await A.signInWithEmailAndPassword(aa, eq.correo, clave);
      await A.deleteUser(c.user);
    }).catch(() => {});
}

export const darPermiso = (id, uid, rol) => actualizar({ [`permisos/${id}/${uid}`]: rol, [`mis_equipos/${uid}/${id}`]: rol });
export const quitarPermiso = (id, uid) => actualizar({ [`permisos/${id}/${uid}`]: null, [`mis_equipos/${uid}/${id}`]: null });

// ------------------------------------------------------------------ firmware (OTA): partes de 32 KB en base64
export const TAM_PARTE = 32768;
export const claveVersion = (ver) => ver.replace(/[^0-9A-Za-z_-]/g, "_");

export async function subirFirmware(ver, notas, archivo, progreso) {
  const datos = new Uint8Array(await archivo.arrayBuffer());
  if (datos[0] !== 0xe9) throw new Error("Ese archivo no parece un firmware del ESP32 (debe empezar por E9h).");
  if (datos.length < 100e3 || datos.length > 4 * 1024 * 1024) throw new Error("El .bin debe pesar entre 100 KB y 4 MB.");
  const sha = [...new Uint8Array(await crypto.subtle.digest("SHA-256", datos))].map((b) => b.toString(16).padStart(2, "0")).join("");
  const clave = claveVersion(ver);
  const partes = Math.ceil(datos.length / TAM_PARTE);
  await remove(r(`firmware/${clave}`)).catch(() => {});
  for (let n = 0; n < partes; n++) {
    const trozo = datos.subarray(n * TAM_PARTE, (n + 1) * TAM_PARTE);
    let bin = "";
    for (let k = 0; k < trozo.length; k += 8192) bin += String.fromCharCode(...trozo.subarray(k, k + 8192));
    await set(r(`firmware/${clave}/partes/${n}`), btoa(bin));
    progreso?.((n + 1) / partes);
  }
  const info = { ver, clave, tam: datos.length, sha, partes, tp: TAM_PARTE, notas: notas || "", subido: serverTimestamp(), por: auth.currentUser.uid };
  await actualizar({ [`firmware/${clave}/info`]: info, [`firmware_lista/${clave}`]: info });
  return info;
}
export async function listaFirmware() {
  return Object.values((await leer("firmware_lista")) || {}).sort((a, b) => (b.subido || 0) - (a.subido || 0));
}
export async function pedirOta(id, info) {
  const { ver, clave, sha, tam, partes, tp } = info;
  await escribir(`entrada/${id}/ota`, { ver, clave, sha, tam, partes, tp, por: auth.currentUser.uid, ts: serverTimestamp() });
}
export async function borrarFirmware(clave) {
  await actualizar({ [`firmware/${clave}`]: null, [`firmware_lista/${clave}`]: null });
}

// ------------------------------------------------------------------ mantenimiento: borra lo más viejo que N días
export async function limpiar(id, dias) {
  const corte = Math.floor(Date.now() / 1000) - dias * 86400;
  let total = 0;
  for (const [ruta, fin] of [["mediciones", String(corte)], ["eventos", String(corte).padStart(10, "0") + "-999999"], ["sesiones", String(corte)]]) {
    for (;;) {
      const s = await get(query(r(`${ruta}/${id}`), orderByKey(), endAt(fin), limitToFirst(500)));
      const cambios = {};
      s.forEach((h) => void (cambios[`${ruta}/${id}/${h.key}`] = null));
      const n = Object.keys(cambios).length;
      if (!n) break;
      await actualizar(cambios);
      total += n;
      if (n < 500) break;
    }
  }
  for (const ruta of ["respuestas", "bitacora"]) {
    const s = await get(query(r(`${ruta}/${id}`), orderByChild("ts"), endAt(corte * 1000)));
    const cambios = {};
    s.forEach((h) => void (cambios[`${ruta}/${id}/${h.key}`] = null));
    if (Object.keys(cambios).length) await actualizar(cambios);
  }
  return total;
}
