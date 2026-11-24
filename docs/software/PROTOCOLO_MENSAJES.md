# Protocolo de datos — equipo ↔ Firebase ↔ app (Fase 10C, D31)

Desde el 24 nov no hay servidor propio: el equipo y la app leen y escriben en la **Realtime Database** de Firebase, cada uno con su cuenta de **Authentication**, y las **reglas de seguridad** (`app/database.rules.json`) deciden quién puede qué. Lo hablan el firmware (`firmware/evse_monitor/src/red.cpp` y `fb.cpp`), la app (`app/public/fb.js` y `app.js`) y el simulador (`tools/simulador/simulador.py`). Si cambia algo aquí, cambia en los tres, y en las reglas (`npm run probar` en `app/` las prueba).

## 1. Conexión del equipo

| Qué | Valor |
|---|---|
| Enlace | código `EVSE1.<base64url de {"d": URL de la base, "k": API key web, "e": correo del equipo, "c": clave}>`; lo da la app (Ajustes → Enlace del equipo) y se pega con `enlazar` o en el portal |
| Inicio de sesión | `POST https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=<k>` con `{email, password, returnSecureToken}` → `idToken` (1 h) y `localId`. Se vuelve a entrar 5 min antes de que venza |
| Lecturas y escrituras | REST: `https://<base>/<ruta>.json?auth=<idToken>` con GET, PUT, PATCH y DELETE, sobre una conexión TLS que se reutiliza |
| Escucha en vivo | `GET https://<base>/entrada/<id>.json?auth=…` con `Accept: text/event-stream`: queda abierta y llegan eventos `put` y `patch` (`{"path": "/…", "data": …}`), `keep-alive` cada 30 s, y `auth_revoked` o `cancel` si el token vence o las reglas lo niegan. Si no llega nada en 90 s, se reabre |
| TLS | el ESP32 verifica los certificados con las raíces de `src/ca_raiz.h` (GTS para Firebase y Google, GoDaddy para Telegram) |
| Hora del servidor | `{".sv": "timestamp"}` en cualquier escritura pone la hora del servidor en milisegundos |

Las horas del equipo son epoch UTC en segundos; las del servidor (`ts` de estado, órdenes y respuestas), en milisegundos. Los números van redondeados (V con 2 decimales, A con 3, W sin decimales, kWh con 3, °C con 1). En Firebase un `null` borra la clave: un dato sin lectura válida simplemente no aparece.

## 2. Secuencia

```text
equipo                                         Firebase                                 app
  │ ── signInWithPassword ─────────────────────► │ Authentication
  │ ── GET /dispositivos/{uid} ────────────────► │  → "evse-01"
  │ ── GET /equipos/evse-01/nombre, /subido/… ─► │
  │ ══ GET /entrada/evse-01 (flujo SSE) ═══════► │ ◄── set /entrada/…/mirando (cada 20 s) ── │ panel abierto
  │ ◄══ put "/" {config, ordenes, ota, …} ═════ │
  │ ── PUT /estado/evse-01 ────────────────────► │ ──► onValue /estado/… ─────────────────► │ en vivo
  │ ── PATCH / {mediciones/…, subido/…} ───────► │  cada lote del búfer (≤ 40 registros)
  │ ◄══ put "/ordenes/-N…" {o, por, ts} ═══════ │ ◄── push /entrada/…/ordenes ────────────── │ «Detener»
  │ ── PUT /respuestas/evse-01/-N… {ok, msg} ──► │ ──► onValue /respuestas/…/-N… ──────────► │ confirma (≤ 15 s)
  │ ── DELETE /entrada/evse-01/ordenes/-N… ────► │
  │ ◄══ put "/config" {v, …} ══════════════════ │ ◄── set /entrada/…/config (v + 1) ──────── │ «Guardar»
  │ ── PUT /entrada/evse-01/config (aplicada) ─► │ ──► estado.cfg_v = v ──────────────────► │ «aplicada»
```

## 3. Rutas de la base

| Ruta | Quién escribe | Quién lee | Qué es |
|---|---|---|---|
| `admins/{uid}` | nadie (consola de Firebase) | el mismo usuario | `true` = administrador |
| `usuarios/{uid}` | el mismo usuario | administrador | `{email, nombre, visto}` |
| `dispositivos/{uid}` | administrador | la cuenta del equipo | id del equipo de esa cuenta |
| `claves/{id}` | administrador | administrador | clave de la cuenta del equipo (para mostrar el código de enlace) |
| `equipos/{id}` | administrador | administrador, sus usuarios y el equipo | `{nombre, uid, correo, creado}` |
| `permisos/{id}/{uid}` y `mis_equipos/{uid}/{id}` | administrador | administrador; cada usuario lo suyo | `propietario` (manda) o `lectura` |
| `entrada/{id}/config` | administrador, propietarios y el equipo | también solo lectura | configuración (sección 6); `v` nunca baja |
| `entrada/{id}/ordenes/{push}` | administrador y propietarios crean; el equipo borra | el equipo, administrador y propietarios | `{o, a?, por: uid, ts: servidor}` (sección 5) |
| `entrada/{id}/mirando` | todos sus usuarios | todos | hora del servidor; el equipo manda telemetría cada 2 s mientras sea de los últimos 45 s |
| `entrada/{id}/ota` | administrador; el equipo la borra | el equipo, administrador y propietarios | `{ver, clave, sha, tam, partes, tp, por, ts}` |
| `entrada/{id}/telegram` | administrador y propietarios | el equipo, administrador y propietarios (no solo lectura) | `{token, chat}` del bot |
| `estado/{id}` | el equipo | sus usuarios | telemetría en vivo (sección 4) |
| `respuestas/{id}/{push}` | el equipo | sus usuarios | `{ok, msg, datos?, ts}` |
| `bitacora/{id}/{push}` | quien manda la orden (una vez) | sus usuarios | `{o, por, ts}`: quién ordenó qué |
| `mediciones/{id}/{ts}` · `eventos/{id}/{ts}-{seq}` · `sesiones/{id}/{inicio}` | el equipo (el administrador borra lo viejo) | sus usuarios | historial (sección 4) |
| `subido/{id}` | el equipo | el equipo y administrador | último registro del búfer que ya está en la base |
| `firmware/{versión}/partes/{n}` · `…/info` · `firmware_lista/{versión}` | administrador | los equipos (partes); administrador | OTA: el .bin en partes de 32 KB en base64 |

Lo que no está en la tabla está cerrado. Las reglas validan además que una orden lleve `por` = quien la manda y `ts` = hora del servidor, que `cal_*` sea solo del administrador y que el id del equipo sea `[a-z0-9][a-z0-9_-]{1,23}`.

## 4. Lo que escribe el equipo

### `estado/{id}` (telemetría en vivo; se reemplaza entera)

```json
{"ts":{".sv":"timestamp"},"hora":1795481885,"v":242.54,"i":16.152,"p":3878,"pf":0.99,"f":60.00,
 "es":0.774,"et":1236.695,"ses":1,"sini":1795481878,"dur":7,"pmax":3878,"tsn":27.9,"tam":29.3,"hum":48,
 "k1":1,"perm":1,"mot":"","al":["temp_aviso"],"nr":[],"rssi":-61,"heap":180000,"up":27,"pend":0,
 "cfg_v":3,"cal":false,"fw":"1.0.0","mac":"10:BD:A3:65:01:08","ip":"192.168.1.50","reset":"encendido","vivo":1,
 "ota":{"fase":"descargando","pct":40,"msg":"","ver":"1.0.1"}}
```

| Campo | Qué es |
|---|---|
| `v`, `i`, `p`, `pf`, `f` | tensión, corriente (CT en I2), potencia activa, factor de potencia y frecuencia |
| `es`, `et` | kWh de la sesión abierta y total |
| `ses`, `sini`, `dur`, `pmax` | número, inicio, duración (s) y potencia máxima de la sesión (`ses` = 0: no hay) |
| `tsn`, `tam`, `hum` | sonda DS18B20, AHT20 (placa) y humedad |
| `k1`, `perm`, `mot` | J2 cerrado; permiso pedido; motivo de detención: `""`, `falla`, `temperatura`, `parar`, `red`, `limite`, `horario`, `app`, `arranque` |
| `al`, `nr` | alarmas activas y graves sin reconocer (sección 7) |
| `cfg_v`, `cal`, `fw`, `ota` | versión de la configuración aplicada, si el medidor está calibrado, firmware y avance de una OTA |
| `pend` | registros del búfer que faltan por subir |

Frecuencia: `tel_s` (15 s por defecto); cada 2 s mientras `mirando` esté fresco; y enseguida después de cada orden. La app da el equipo por «en línea» si `ts` tiene menos de max(25 s, 2,5 × `tel_s` + 5 s).

### Historial (del búfer, en lotes de hasta 40 con un solo PATCH a la raíz)

```json
{"mediciones/evse-01/1795481867": {"v":242.6,"i":16.0,"p":3840,"pf":0.99,"f":60.0,"es":0.5,"et":1234.9,"tsn":28.1,"tam":29.0,"hum":48,"k1":1,"mot":""},
 "eventos/evse-01/1795482175-001202": {"ts":1795482175,"c":"alarma","n":2,"val":0,"x":600,"a":"temp_sonda","txt":"Sobretemperatura en la sonda","k1":0,"mot":"temperatura"},
 "sesiones/evse-01/1795482006": {"num":2,"ini":1795482006,"fin":1795482022,"kwh":2.024,"pmax":3801,"cop":1822,"mf":"limite","k1":0,"mot":"limite"},
 "subido/evse-01": 1203}
```

- **Muestras** cada `reg_carga_s` (30 s) cargando, cada `reg_reposo_s` (5 min) en reposo y en cada cambio de K1. La clave es la hora: la app pide rangos con `orderByKey`.
- **Eventos** con `c` (sección 7), `n` nivel (0 info, 1 aviso, 2 alarma), `val`, `x`; en alarmas, `a` y `txt`.
- **Sesiones** cerradas con `cop` = kWh × tarifa en ese momento y `mf` (`sin_corriente`, `limite`, `otro`).
- Todo va en **una** escritura con `subido`: o entra el lote entero o nada. El equipo avanza solo cuando Firebase contesta 200.
- Un registro sin hora (sin NTP ni DS3231) se corrige con el uptime si la hora llegó en el mismo arranque; si no, la muestra se descarta y el evento queda con `ts` = 0 y `sh` = 1.

### `respuestas/{id}/{orden}` y la configuración aplicada

`{"ok":true,"msg":"carga detenida","ts":{".sv":"timestamp"}}`, y después el equipo borra la orden de `entrada`. `cal_leer` agrega `datos` con la calibración, los registros del chip (SysStatus, CalStart, AdjStart, MMode, Ugain, IgainN, CS1, CS2) y la medición actual.

Al aplicar una configuración, el equipo la vuelve a escribir en `entrada/{id}/config` con la misma `v`, `"por":"equipo"` y los valores ya recortados a sus rangos. Si cambia algo por la consola (`sonda`, `tension`), sube la suya con `v` + 1.

## 5. Órdenes

La app hace `push` en `entrada/{id}/ordenes` y escucha `respuestas/{id}/{la misma clave}` hasta 15 s; si no llega, borra la orden y avisa. El equipo descarta las órdenes de más de 2 min (`ts` del servidor contra su hora).

| `o` | `a` | Quién | Qué hace |
|---|---|---|---|
| `permitir` | — | propietario | permiso = sí; borra el límite alcanzado (nueva sesión); confirma el arranque |
| `detener` | — | propietario | permiso = no |
| `reconocer` | — | propietario | marca las alarmas como vistas; suelta el enclavamiento por temperatura y el bloqueo por reinicios |
| `soltar_parar` | — | propietario | libera PARAR |
| `estado` | — | propietario | telemetría ya |
| `reiniciar` | — | propietario | responde y se reinicia en 3 s |
| `telegram_probar` | — | propietario | el equipo manda un mensaje de prueba |
| `cal_leer` | — | administrador | respuesta con `datos` |
| `cal_auto` | `{"v":120.4,"i":9.87}` | administrador | Ugain e IgainN en proporción a la referencia (0 = no tocar) |
| `cal_escribir` | `{"ugain":"6720","igain_n":"7530",…}` (hex en texto o número) | administrador | escribe los registros, recalcula CS1/CS2 y guarda |
| `cal_fabrica` | — | administrador | vuelve a los valores de fábrica |

**OTA** no es una orden: el administrador escribe `entrada/{id}/ota`. El equipo, si no hay una carga en curso, baja `firmware/{clave}/partes/0 … n−1`, decodifica el base64, revisa tamaño y SHA-256, instala, informa en `estado/{id}/ota` (`descargando`, `listo`, `ok`, `error`) y se reinicia. El firmware nuevo, al llegar a la base, se confirma y borra `entrada/{id}/ota`. Si no arranca bien 3 veces, vuelve al anterior y anota esa versión para no reintentarla.

## 6. Configuración (`entrada/{id}/config`)

```json
{"v":4,"vnom":240,"tarifa":900,"tz":-300,"tmax_sonda":60,"tmax_amb":60,"t_hist":10,"sonda_req":true,
 "arranque":"restaurar","lim_kwh":0,"lim_min":0,"lim_cop":0,
 "horario":{"on":false,"v":[{"d":127,"i":"22:00","f":"05:00"}]},
 "i_inicio":1,"fin_min":10,"inv_ct":false,"tel_s":15,"reg_carga_s":30,"reg_reposo_s":300,"por":"<uid o equipo>"}
```

| Campo | Rango | Significado |
|---|---|---|
| `v` | ≥ 0, nunca baja | versión: el equipo aplica solo si es mayor que la suya |
| `vnom` | 120 o 240 | tensión nominal (protección por tensión baja y umbral de sag) |
| `tarifa` | 0–100 000 | COP/kWh, para el costo y el límite por costo |
| `tz` | −720 a 840 | minutos respecto a UTC (Colombia: −300) para el horario |
| `tmax_sonda`, `tmax_amb`, `t_hist` | 30–90, 30–85, 2–30 | °C de corte y de histéresis |
| `sonda_req` | sí/no | sin sonda = falla |
| `arranque` | `restaurar`, `detenida`, `permitida` | política al volver la energía (D28) |
| `lim_kwh`, `lim_min`, `lim_cop` | 0–500, 0–2880, 0–10 000 000 | límites por sesión (0 = sin límite) |
| `horario` | hasta 4 franjas | `d` días (bit 0 = domingo … bit 6 = sábado), `i` y `f` en «HH:MM»; si `f` ≤ `i`, cruza la medianoche. Firebase no guarda listas vacías: sin franjas, `v` no aparece |
| `i_inicio`, `fin_min` | 0,2–10 A, 1–240 min | inicio y fin de la sesión |
| `inv_ct` | sí/no | invierte el signo de la potencia (CT al revés) |
| `tel_s`, `reg_carga_s`, `reg_reposo_s` | 5–300, 10–600, 60–3600 s | periodos de telemetría y de historial |

## 7. Códigos

**Alarmas** (bit en el firmware → código): 0 `temp_sonda`, 1 `temp_amb`, 2 `sonda_falla`, 3 `medidor_falla`, 4 `red_baja`, 5 `parar`, 6 `amb_falla`, 7 `sin_hora`, 8 `reinicio`, 9 `sin_calibrar`, 10 `temp_aviso`. Graves (nivel 2, quedan sin reconocer y avisan por Telegram): 0, 1, 2, 3, 4, 5 y 8.

**Eventos:** `arranque` (val = motivo del reset de ESP-IDF, x = reinicios anormales seguidos), `k1` (val 1 cerrado / 0 abierto; `mot` = por qué), `alarma` y `alarma_fin` (val = bit, x = medida × 10: °C o V), `sesion_inicio` (val = número), `limite` (val 1 kWh, 2 tiempo, 3 costo), `config` (val = versión), `calibracion`, `orden_local` (val 1 PARAR pulsado, 2 soltado en la placa, 3 soltado desde la app), `ota`, `hora` (NTP copiado al DS3231).

## 8. Sin internet

1. Todo lo que va al historial se escribe primero en el búfer: partición `buffer` de 7 MB en la flash, registros de 64 bytes con CRC-16, 114 688 en total. Son unos 40 días cargando sin parar (una muestra cada 30 s) o más de un año en reposo. Cuando se llena, se borra el sector más viejo (64 registros).
2. La energía total, la de la sesión y el estado de K1 están además en la NVS (cada minuto y en cada cambio, D14).
3. Al volver la conexión, el equipo lee `subido/{id}` y sube el resto en lotes de 40.
4. Las protecciones, los límites y el horario no dependen de nada de esto: viven en la tarea de control del ESP32.
5. **Telegram** lo manda el propio equipo cuando aparece una alarma grave o termina una carga (si está en línea). Sin servidor propio no hay aviso de «equipo fuera de línea»: la app lo muestra al abrirla.
