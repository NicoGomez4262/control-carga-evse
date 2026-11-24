// Prueba las reglas de seguridad (database.rules.json) contra el emulador de Firebase.
// Uso (con «npm run emular» corriendo en otra terminal):  npm run probar
// Crea usuarios de prueba en el emulador (administrador, propietario, lector, extraño y equipo) y revisa que
// cada uno pueda hacer solo lo que le toca. No toca ningún proyecto real.

const AUTH = "http://127.0.0.1:9099/identitytoolkit.googleapis.com/v1";
const DB = "http://127.0.0.1:9000";
const NS = "demo-evse-default-rtdb";
const TS = { ".sv": "timestamp" };

let fallas = 0, pruebas = 0;

async function crearUsuario(correo) {
  const r = await fetch(`${AUTH}/accounts:signUp?key=demo`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: correo, password: "clave-de-prueba-123", returnSecureToken: true }),
  });
  const d = await r.json();
  if (!d.idToken) {
    const r2 = await fetch(`${AUTH}/accounts:signInWithPassword?key=demo`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: correo, password: "clave-de-prueba-123", returnSecureToken: true }),
    });
    return r2.json();
  }
  return d;
}

async function db(metodo, ruta, cuerpo, token) {
  const q = new URLSearchParams({ ns: NS });
  const cab = { "Content-Type": "application/json" };
  if (token === "dueño") cab.Authorization = "Bearer owner";  // el emulador se salta las reglas
  else if (token) q.set("auth", token);
  const r = await fetch(`${DB}/${ruta}.json?${q}`, {
    method: metodo, headers: cab, body: cuerpo === undefined ? undefined : JSON.stringify(cuerpo),
  });
  return r.status;
}

async function espera(titulo, permitido, promesa) {
  pruebas++;
  const codigo = await promesa;
  const ok = permitido ? codigo === 200 : codigo !== 200;
  if (!ok) fallas++;
  console.log(`${ok ? "  ok " : "  MAL"}  ${permitido ? "permite" : "niega  "}  ${titulo}  (HTTP ${codigo})`);
}

const admin = await crearUsuario("admin@prueba.test");
const prop = await crearUsuario("propietario@prueba.test");
const lect = await crearUsuario("lector@prueba.test");
const extr = await crearUsuario("extrano@prueba.test");
const disp = await crearUsuario("evse-99.abcd@equipos.invalid");
const otro = await crearUsuario("evse-98.efgh@equipos.invalid");
const A = admin.idToken, P = prop.idToken, L = lect.idToken, X = extr.idToken, D = disp.idToken, O = otro.idToken;

await db("DELETE", "", undefined, "dueño");
await db("PUT", `admins/${admin.localId}`, true, "dueño");

console.log("\nAdministrador");
await espera("crea el equipo evse-99 (varias rutas a la vez)", true, db("PATCH", "", {
  "equipos/evse-99": { nombre: "Garaje", uid: disp.localId, correo: "evse-99.abcd@equipos.invalid", creado: TS },
  "equipos/evse-98": { nombre: "Otro", uid: otro.localId, correo: "evse-98.efgh@equipos.invalid", creado: TS },
  [`dispositivos/${disp.localId}`]: "evse-99",
  [`dispositivos/${otro.localId}`]: "evse-98",
  "claves/evse-99": "clave-de-prueba-123",
  [`permisos/evse-99/${prop.localId}`]: "propietario",
  [`permisos/evse-99/${lect.localId}`]: "lectura",
  [`mis_equipos/${prop.localId}/evse-99`]: "propietario",
  [`mis_equipos/${lect.localId}/evse-99`]: "lectura",
  "entrada/evse-99/config": { v: 1, vnom: 240, tarifa: 900 },
}, A));
await espera("lee la lista de equipos", true, db("GET", "equipos", undefined, A));
await espera("sube una parte de firmware", true, db("PUT", "firmware/1_0_1/partes/0", "AAAA", A));
await espera("anota la versión en firmware_lista", true, db("PUT", "firmware_lista/1_0_1", { ver: "1.0.1", tam: 3 }, A));
await espera("pide una OTA", true, db("PUT", "entrada/evse-99/ota",
  { ver: "1.0.1", clave: "1_0_1", sha: "00", tam: 3, partes: 1, tp: 32768, por: admin.localId }, A));
await espera("manda cal_auto", true, db("PUT", "entrada/evse-99/ordenes/-Ncal1",
  { o: "cal_auto", a: { v: 120 }, por: admin.localId, ts: TS }, A));
await espera("lee la clave del equipo", true, db("GET", "claves/evse-99", undefined, A));
await espera("equipo con id inválido", false, db("PUT", "equipos/EVSE 99",
  { nombre: "x", uid: "u", correo: "c" }, A));

console.log("\nPropietario");
await espera("lee el estado", true, db("GET", "estado/evse-99", undefined, P));
await espera("lee /entrada (config, órdenes, Telegram)", true, db("GET", "entrada/evse-99", undefined, P));
await espera("manda «permitir»", true, db("PUT", "entrada/evse-99/ordenes/-Nperm",
  { o: "permitir", por: prop.localId, ts: TS }, P));
await espera("manda una orden a nombre de otro", false, db("PUT", "entrada/evse-99/ordenes/-Nfalsa",
  { o: "detener", por: lect.localId, ts: TS }, P));
await espera("manda una orden con hora inventada", false, db("PUT", "entrada/evse-99/ordenes/-Nhora",
  { o: "detener", por: prop.localId, ts: 1 }, P));
await espera("manda cal_auto (solo administrador)", false, db("PUT", "entrada/evse-99/ordenes/-Ncal2",
  { o: "cal_auto", por: prop.localId, ts: TS }, P));
await espera("cambia la configuración (v2)", true, db("PUT", "entrada/evse-99/config", { v: 2, vnom: 240, lim_kwh: 5 }, P));
await espera("vuelve a una versión vieja de la configuración", false, db("PUT", "entrada/evse-99/config", { v: 1 }, P));
await espera("guarda el Telegram", true, db("PUT", "entrada/evse-99/telegram", { token: "123:abc", chat: "456" }, P));
await espera("pide una OTA (solo administrador)", false, db("PUT", "entrada/evse-99/ota",
  { ver: "9", clave: "9", sha: "0", tam: 1, partes: 1, tp: 1 }, P));
await espera("cambia el nombre del equipo", false, db("PUT", "equipos/evse-99/nombre", "Mío", P));
await espera("se da permisos", false, db("PUT", `permisos/evse-98/${prop.localId}`, "propietario", P));
await espera("lee su lista de equipos", true, db("GET", `mis_equipos/${prop.localId}`, undefined, P));
await espera("lee la lista de otro", false, db("GET", `mis_equipos/${lect.localId}`, undefined, P));
await espera("anota su orden en la bitácora", true, db("PUT", "bitacora/evse-99/-Nperm", { o: "permitir", por: prop.localId, ts: TS }, P));
await espera("cambia una anotación de la bitácora", false, db("PUT", "bitacora/evse-99/-Nperm", { o: "detener", por: prop.localId, ts: TS }, P));
await espera("lee la lista de firmware", false, db("GET", "firmware_lista", undefined, P));
await espera("lee el historial", true, db("GET", "mediciones/evse-99", undefined, P));
await espera("escribe en el historial", false, db("PUT", "mediciones/evse-99/1764000000", { p: 1 }, P));
await espera("lee un equipo ajeno", false, db("GET", "estado/evse-98", undefined, P));
await espera("lee las claves de los equipos", false, db("GET", "claves/evse-99", undefined, P));
await espera("baja el firmware", false, db("GET", "firmware/1_0_1/partes/0", undefined, P));

console.log("\nSolo lectura");
await espera("lee el estado", true, db("GET", "estado/evse-99", undefined, L));
await espera("lee la configuración", true, db("GET", "entrada/evse-99/config", undefined, L));
await espera("lee /entrada entera (incluye el token de Telegram)", false, db("GET", "entrada/evse-99", undefined, L));
await espera("lee el Telegram", false, db("GET", "entrada/evse-99/telegram", undefined, L));
await espera("avisa que mira la app (mirando)", true, db("PUT", "entrada/evse-99/mirando", TS, L));
await espera("manda «detener»", false, db("PUT", "entrada/evse-99/ordenes/-Nlect",
  { o: "detener", por: lect.localId, ts: TS }, L));
await espera("cambia la configuración", false, db("PUT", "entrada/evse-99/config", { v: 3 }, L));
await espera("lee la bitácora", true, db("GET", "bitacora/evse-99", undefined, L));
await espera("escribe en la bitácora", false, db("PUT", "bitacora/evse-99/-Nl", { o: "detener", por: lect.localId, ts: TS }, L));

console.log("\nExtraño (cuenta sin permisos)");
await espera("lee el estado", false, db("GET", "estado/evse-99", undefined, X));
await espera("lee la lista de equipos", false, db("GET", "equipos", undefined, X));
await espera("lee los usuarios", false, db("GET", "usuarios", undefined, X));
await espera("escribe su perfil", true, db("PUT", `usuarios/${extr.localId}`,
  { email: "extrano@prueba.test", nombre: "X", visto: TS }, X));
await espera("escribe el perfil de otro", false, db("PUT", `usuarios/${lect.localId}`, { email: "a@b.c" }, X));
await espera("se hace administrador", false, db("PUT", `admins/${extr.localId}`, true, X));
await espera("se asigna un equipo", false, db("PUT", `dispositivos/${extr.localId}`, "evse-99", X));
await espera("sin sesión lee algo", false, db("GET", "estado/evse-99", undefined, null));

console.log("\nEquipo evse-99");
await espera("lee su id", true, db("GET", `dispositivos/${disp.localId}`, undefined, D));
await espera("lee su nombre", true, db("GET", "equipos/evse-99/nombre", undefined, D));
await espera("escucha /entrada", true, db("GET", "entrada/evse-99", undefined, D));
await espera("escribe el estado", true, db("PUT", "estado/evse-99", { ts: TS, p: 3800, k1: 1 }, D));
await espera("sube el búfer (varias rutas a la vez)", true, db("PATCH", "", {
  "mediciones/evse-99/1764000000": { p: 3800, v: 240 },
  "eventos/evse-99/1764000000-000001": { c: "k1", ts: 1764000000 },
  "sesiones/evse-99/1764000000": { kwh: 1.2 },
  "subido/evse-99": 3,
}, D));
await espera("responde una orden", true, db("PUT", "respuestas/evse-99/-Nperm", { ok: true, msg: "bien", ts: TS }, D));
await espera("borra la orden respondida", true, db("DELETE", "entrada/evse-99/ordenes/-Nperm", undefined, D));
await espera("crea una orden", false, db("PUT", "entrada/evse-99/ordenes/-Nd",
  { o: "permitir", por: disp.localId, ts: TS }, D));
await espera("sube su configuración", true, db("PUT", "entrada/evse-99/config", { v: 2, vnom: 240, por: "equipo" }, D));
await espera("borra la OTA terminada", true, db("DELETE", "entrada/evse-99/ota", undefined, D));
await espera("baja el firmware", true, db("GET", "firmware/1_0_1/partes/0", undefined, D));
await espera("lee las claves", false, db("GET", "claves/evse-99", undefined, D));
await espera("escribe el estado de otro equipo", false, db("PUT", "estado/evse-98", { p: 1 }, D));
await espera("lee /entrada de otro equipo", false, db("GET", "entrada/evse-98", undefined, D));
await espera("escribe un perfil de usuario", false, db("PUT", `usuarios/${disp.localId}`, { email: "x@y.z" }, D));
await espera("equipo evse-98 escribe en evse-99", false, db("PUT", "mediciones/evse-99/1", { p: 1 }, O));

console.log("\nAdministrador borra el equipo evse-98");
await espera("borra todo de una vez", true, db("PATCH", "", {
  "equipos/evse-98": null, "entrada/evse-98": null, "estado/evse-98": null, "mediciones/evse-98": null,
  "eventos/evse-98": null, "sesiones/evse-98": null, "respuestas/evse-98": null, "subido/evse-98": null,
  [`dispositivos/${otro.localId}`]: null,
}, A));

console.log(`\n${pruebas - fallas} de ${pruebas} pruebas bien${fallas ? ` · ${fallas} MAL` : ""}`);
await db("DELETE", "", undefined, "dueño");
process.exit(fallas ? 1 : 0);
