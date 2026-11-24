# Protocolo de mensajes — equipo ↔ servidor (Fase 10C)

Lo hablan el firmware (`firmware/evse_monitor/src/red.cpp`), el servidor (`app/src/equipo.js`) y el simulador (`tools/simulador/simulador.py`). Si cambia algo aquí, cambia en los tres.

## 1. Conexión

| Qué | Valor |
|---|---|
| URL | `wss://<servidor>/api/dispositivo/ws` (en pruebas locales sin TLS: `ws://<IP>:8787/api/dispositivo/ws`) |
| Autenticación | cabecera `Authorization: Bearer <id>:<token>` en el saludo HTTP del WebSocket |
| TLS | el ESP32 verifica el certificado con las raíces de `src/ca_raiz.h` |
| Formato | un objeto JSON en UTF-8 por trama de texto; el campo `t` dice el tipo |
| Latido | el equipo manda el texto `ping` cada 30 s y el servidor contesta `pong` sin despertar al Durable Object. Si el equipo no recibe nada en 75 s, cierra y reconecta (cada 5–10 s). Si el servidor no recibe nada en 100 s, lo da por fuera de línea |
| Reconexión | la nueva conexión de un equipo reemplaza la anterior (código 4000) |

Las horas son epoch UTC en segundos. Los números de punto flotante van redondeados (V con 2 decimales, A con 3, W sin decimales, kWh con 3, °C con 1) y `null` si no hay lectura válida.

## 2. Secuencia

```text
equipo                                   servidor
  │ ── WebSocket + Authorization ─────────► │  valida el token (SHA-256 en D1)
  │ ── hola {fw, cfgv, seq_min, seq_max} ──► │
  │ ◄── bienvenida {hora, vivo, seq} ─────── │  seq = último registro que el servidor guardó
  │ ◄── cfg {v, c}   (si la suya es nueva) ── │
  │ ── cfg {v, c}  (la que quedó aplicada) ─► │
  │ ── tel ─────────────────────────────────► │  cada tel_s (15 s) o cada 2 s con «vivo»
  │ ── reg {r:[…], hasta} ──────────────────► │  lotes de ≤ 20 registros del búfer
  │ ◄── regack {hasta} ───────────────────── │  después de escribir en D1
  │ ◄── orden {id, o, a} ─────────────────── │  desde la app (REST → Durable Object)
  │ ── ack {id, ok, msg, datos?} ───────────► │  la app espera hasta 10 s
  │ ◄── vivo {on} ────────────────────────── │  alguien abrió o cerró el panel
  │ ── ping ──► ◄── pong                     │  cada 30 s
```

## 3. Del equipo al servidor

### `hola` (al conectar)

```json
{"t":"hola","fw":"1.0.0","id":"evse-01","reset":"encendido","mac":"F4:12:FA:00:11:22",
 "cfgv":3,"seq_min":1,"seq_max":1532,"up":42,"hora":1795481884,"ota_pend":0}
```

`reset`: encendido, pin_en, software, panic, wdt_int, wdt_tarea, wdt, brownout, otro. `ota_pend` = 1 si corre un firmware nuevo sin confirmar.

### `tel` (telemetría en vivo; no se guarda en el historial)

```json
{"t":"tel","ts":1795481885,"v":242.54,"i":16.152,"p":3878,"pf":0.99,"f":60.00,
 "es":0.774,"et":1236.695,"ses":1,"sini":1795481878,"dur":7,"pmax":3878,
 "tsn":27.9,"tam":29.3,"hum":48,"k1":1,"perm":1,"mot":"","al":["temp_aviso"],"nr":[],
 "rssi":-61,"heap":180000,"up":27,"pend":0}
```

| Campo | Qué es |
|---|---|
| `v`, `i`, `p`, `pf`, `f` | tensión, corriente (CT en I2), potencia activa, factor de potencia y frecuencia |
| `es`, `et` | kWh de la sesión abierta y total |
| `ses`, `sini`, `dur`, `pmax` | número, inicio, duración (s) y potencia máxima de la sesión (`ses` = 0: no hay) |
| `tsn`, `tam`, `hum` | sonda DS18B20, AHT20 (placa) y humedad |
| `k1` | 1 = J2 cerrado = carga permitida |
| `perm` | permiso pedido por el usuario |
| `mot` | motivo de detención: `""` (permitida), `falla`, `temperatura`, `parar`, `red`, `limite`, `horario`, `app`, `arranque` |
| `al`, `nr` | alarmas activas y alarmas graves sin reconocer (códigos de la sección 6) |
| `rssi`, `heap`, `up`, `pend` | WiFi (dBm), memoria libre, segundos encendido, registros por subir |

Frecuencia: `tel_s` de la configuración (15 s por defecto); cada 2 s mientras alguien tiene el panel abierto (`vivo`); y enseguida después de cada orden que cambia algo.

### `reg` (registros del búfer)

```json
{"t":"reg","hasta":1205,"r":[
  {"s":1201,"ts":1795481867,"k":"m","k1":1,"mot":"","v":242.6,"i":16.0,"p":3840,"pf":0.99,"f":60.0,
   "es":0.5,"et":1234.9,"tsn":28.1,"tam":29.0,"hum":48},
  {"s":1202,"ts":1795482175,"k":"e","k1":0,"mot":"temperatura","c":"alarma","n":2,"val":0,"x":600,
   "a":"temp_sonda","txt":"Sobretemperatura en la sonda"},
  {"s":1203,"ts":1795482022,"k":"s","k1":0,"mot":"limite","num":2,"ini":1795482006,"fin":1795482022,
   "kwh":2.024,"pmax":3801,"mf":"limite"}]}
```

| `k` | Tipo | Campos propios |
|---|---|---|
| `m` | muestra para el historial: cada `reg_carga_s` (30 s) cargando y cada `reg_reposo_s` (5 min) en reposo, y en cada cambio de K1 | `v i p pf f es et tsn tam hum` |
| `e` | evento | `c` código (sección 6), `n` nivel (0 info, 1 aviso, 2 alarma), `val`, `x`; en alarmas, `a` y `txt` |
| `s` | sesión cerrada | `num`, `ini`, `fin`, `kwh`, `pmax`, `mf` (`sin_corriente`, `limite`, `otro`) |

Comunes: `s` número de registro (crece siempre), `ts`, `k1`, `mot`. Si el equipo no tenía hora, el registro trae `"sh":1` y `ts` es el uptime en segundos; el servidor lo convierte con el último uptime que conoce. `hasta` es el último número incluido en el lote (aunque haya registros dañados que se saltaron), para que el servidor lo confirme igual.

### `ack` (respuesta a una orden)

```json
{"t":"ack","id":"3f9a1c2b7d4e5f60","ok":true,"msg":"carga detenida"}
```

`cal_leer` agrega `datos` con la calibración guardada, los registros del chip (SysStatus, CalStart, AdjStart, MMode, Ugain, IgainN, CS1, CS2) y la medición actual.

### `cfg` (configuración que quedó aplicada)

```json
{"t":"cfg","v":3,"c":{ … la misma forma de la sección 5 … }}
```

Se manda después de la bienvenida y cada vez que se aplica una configuración. Si `v` es mayor que la del servidor (por ejemplo, porque se borró la base), el servidor la adopta.

### `ota` (avance de una actualización)

```json
{"t":"ota","fase":"descargando","pct":40,"msg":"","ver":"1.0.1"}
```

Fases: `descargando`, `listo` (se reinicia), `ok` (el firmware nuevo llegó al servidor y quedó confirmado), `error` (con `msg`).

## 4. Del servidor al equipo

| Mensaje | Ejemplo | Qué hace el equipo |
|---|---|---|
| `bienvenida` | `{"t":"bienvenida","hora":1795481884,"vivo":false,"seq":1200}` | Sube los registros después de `seq`. Si no tiene hora, la toma de aquí. Si corría un firmware sin confirmar, lo confirma |
| `regack` | `{"t":"regack","hasta":1220}` | Avanza y manda el lote siguiente |
| `vivo` | `{"t":"vivo","on":true}` | Telemetría cada 2 s (`on`) o cada `tel_s` |
| `cfg` | `{"t":"cfg","v":4,"c":{…}}` | Valida los rangos, guarda en NVS, aplica y responde con `cfg` |
| `orden` | `{"t":"orden","id":"…","o":"detener","a":{}}` | Ejecuta y responde con `ack` |

### Órdenes

| `o` | `a` | Quién | Qué hace |
|---|---|---|---|
| `permitir` | — | propietario | permiso = sí; borra el límite alcanzado; confirma el arranque |
| `detener` | — | propietario | permiso = no |
| `reconocer` | — | propietario | marca las alarmas como vistas; suelta el enclavamiento por temperatura y el bloqueo por reinicios |
| `soltar_parar` | — | propietario | libera PARAR |
| `estado` | — | propietario | manda `tel` ya |
| `reiniciar` | — | propietario | responde y se reinicia en 1,5 s |
| `cal_leer` | — | propietario | `ack` con `datos` |
| `cal_auto` | `{"v":120.4,"i":9.87}` | administrador | Ugain e IgainN en proporción a la referencia (0 = no tocar) |
| `cal_escribir` | `{"ugain":"6720","igain_n":"7530",…}` (hex en texto o número) | administrador | escribe los registros, recalcula CS1/CS2 y guarda |
| `cal_fabrica` | — | administrador | vuelve a los valores de fábrica |
| `ota` | `{"ver":"1.0.1","tam":1056816,"sha":"422c…"}` | administrador | baja `https://<servidor>/api/dispositivo/firmware/1.0.1` con su token, revisa tamaño y SHA-256, instala y se reinicia |

## 5. Configuración

```json
{"vnom":120,"tarifa":900,"tz":-300,"tmax_sonda":60,"tmax_amb":60,"t_hist":10,"sonda_req":true,
 "arranque":"restaurar","lim_kwh":0,"lim_min":0,"lim_cop":0,
 "horario":{"on":false,"v":[{"d":127,"i":"22:00","f":"05:00"}]},
 "i_inicio":1,"fin_min":10,"inv_ct":false,"tel_s":15,"reg_carga_s":30,"reg_reposo_s":300}
```

| Campo | Rango | Significado |
|---|---|---|
| `vnom` | 120 o 240 | tensión nominal (protección por tensión baja y umbral de sag) |
| `tarifa` | 0–100 000 | COP/kWh, para el costo y el límite por costo |
| `tz` | −720 a 840 | minutos respecto a UTC (Colombia: −300) para el horario |
| `tmax_sonda`, `tmax_amb`, `t_hist` | 30–90, 30–85, 2–30 | °C de corte y de histéresis |
| `sonda_req` | sí/no | sin sonda = falla |
| `arranque` | `restaurar`, `detenida`, `permitida` | política al volver la energía (D28) |
| `lim_kwh`, `lim_min`, `lim_cop` | 0–500, 0–2880, 0–10 000 000 | límites por sesión (0 = sin límite) |
| `horario` | hasta 4 franjas | `d` días (bit 0 = domingo … bit 6 = sábado), `i` y `f` en «HH:MM»; si `f` ≤ `i`, cruza la medianoche |
| `i_inicio`, `fin_min` | 0,2–10 A, 1–240 min | inicio y fin de la sesión |
| `inv_ct` | sí/no | invierte el signo de la potencia (CT al revés) |
| `tel_s`, `reg_carga_s`, `reg_reposo_s` | 5–300, 10–600, 60–3600 s | periodos de telemetría y de historial |

El servidor (`limpiarConfig` en `app/src/util.js`) y el firmware (`aplicarConfig` en `red.cpp`) recortan los valores a estos rangos.

## 6. Códigos

**Alarmas** (bit en el firmware → código): 0 `temp_sonda`, 1 `temp_amb`, 2 `sonda_falla`, 3 `medidor_falla`, 4 `red_baja`, 5 `parar`, 6 `amb_falla`, 7 `sin_hora`, 8 `reinicio`, 9 `sin_calibrar`, 10 `temp_aviso`. Graves (nivel 2, quedan sin reconocer y avisan por Telegram): 0, 1, 2, 3, 4, 5 y 8.

**Eventos:** `arranque` (val = motivo del reset de ESP-IDF, x = reinicios anormales seguidos), `k1` (val 1 cerrado / 0 abierto; `mot` = por qué), `alarma` y `alarma_fin` (val = bit, x = medida × 10: °C o V), `sesion_inicio` (val = número), `limite` (val 1 kWh, 2 tiempo, 3 costo), `config` (val = versión), `calibracion`, `orden_local` (val 1 PARAR pulsado, 2 soltado en la placa, 3 soltado desde la app), `ota`, `hora` (NTP copiado al DS3231).

## 7. Sin internet

1. Todo lo que va al historial (muestras, eventos y sesiones) se escribe primero en el búfer: partición `buffer` de 7 MB en la flash, registros de 64 bytes con CRC-16, 114 688 en total. Son unos 40 días cargando sin parar (una muestra cada 30 s) o más de un año en reposo (una cada 5 min). Cuando se llena, se borra el sector más viejo (64 registros).
2. La energía total, la de la sesión y el estado de K1 están además en la NVS (cada minuto y en cada cambio, D14). Si se va la luz sin internet, se pierde como mucho 1 min de energía.
3. Al volver la conexión, el equipo manda `hola` con su rango de registros. El servidor contesta con el último que guardó y el equipo sube el resto en lotes de 20, uno a la vez (espera el `regack`; si no llega en 15 s, repite).
4. Si el equipo no tenía hora (sin NTP y con el DS3231 sin pila), los registros van marcados `sh` y el servidor les pone la hora estimada.
5. Las alarmas que llegan con más de 15 min de atraso se guardan, pero no se avisan por Telegram.
