# Arquitectura del software — EVSE Monitor Rev 1.0 (Fase 10)

Cómo está hecho el software y por qué. Las decisiones van de D21 a D30 en `docs/DECISIONES.md`. El protocolo entre el equipo y el servidor está en `PROTOCOLO_MENSAJES.md`, y los pasos para compilar, subir a la PCB y publicar la app, en `GUIA_INSTALACION.md`.

## 1. Vista general

```text
 PLACA (SELV)                         INTERNET                       NUBE (Cloudflare, plan gratis)                  USUARIO
 ┌──────────────────────────────┐                                   ┌────────────────────────────────────────┐
 │ ATM90E26 ─SPI─┐              │                                   │ Worker «evse-monitor»                  │
 │ AHT20, DS3231 ─I²C─┐         │   WebSocket seguro (wss, TLS)     │  ├─ /api/dispositivo/ws ──► Durable    │   https://…
 │ DS18B20 ─1-Wire─┐  │         │   SALIENTE desde el ESP32 (D8)    │  │                          Object     │◄── app web (celular)
 │ PARAR, LEDs, K1 │  │         │ ────────────────────────────────► │  │                          «Equipo»  │    panel en vivo (wss)
 │         ┌───────▼──▼──────┐  │   hola · tel · reg · ack · cfg    │  │                          por equipo │    órdenes (HTTPS)
 │         │ ESP32-S3        │  │ ◄──────────────────────────────── │  ├─ /api/* (REST) ─────────►  │         │
 │         │ tarea control ──┼──┼─ protecciones sin internet        │  │                           ▼         │
 │         │ tarea red ──────┼──┼─ bienvenida · orden · cfg · vivo  │  ├─ D1 (SQLite): usuarios, equipos,    │
 │         │ NVS · búfer 7 MB│  │                                   │  │   mediciones, sesiones, eventos     │
 │         └─────────────────┘  │   HTTPS con token: firmware (OTA) │  ├─ KV: firmware .bin                  │
 └──────────────────────────────┘                                   │  └─ archivos estáticos: la app web     │
                                                                    └──────────────┬─────────────────────────┘
                                                                                   └─► Telegram (alarmas)
```

- **El equipo inicia todo**: abre un WebSocket cifrado hacia el servidor y por ahí sube datos y recibe órdenes (D8). No hay puertos abiertos en el router ni VPN.
- **Las protecciones viven en el ESP32.** El corte por temperatura, PARAR, la falla del medidor o de la sonda, la tensión baja y los límites de sesión los decide la tarea de control, que no depende de la red. La app solo ordena y muestra.
- **Sin internet no se pierde nada.** Cada medición, evento y sesión se escribe primero en un búfer circular de 7 MB en la flash. El servidor confirma lo que guardó y el equipo sube lo pendiente cuando vuelve la conexión.
- **Costo mensual: US$ 0** con el plan gratis de Cloudflare (sección 6). El dominio propio es opcional.

## 2. Firmware (`firmware/`)

Dos proyectos de PlatformIO con Arduino-ESP32 2.0.17 (ESP-IDF 4.4):

| Proyecto | Para qué |
|---|---|
| `prueba_placa/` | Menú por consola para las etapas S1–S6 del protocolo de pruebas, una por comando. Sin WiFi salvo en S6. Funciona sin U1 |
| `evse_monitor/` | Firmware final |

### 2.1 Tareas del firmware final

| Tarea | Prioridad | Qué hace |
|---|---|---|
| **control** (`src/control.cpp`), cada 250 ms | 3 (alta) | PARAR con antirrebote e interrupción; ATM90E26 cada 1 s; AHT20 y DS18B20 cada 5 s sin bloquear; energía (integra P cada segundo); sesiones; protecciones; K1; LEDs; registros al búfer; energía a la NVS cada minuto |
| **loop de Arduino** (`src/red.cpp`, `portal.cpp`, `consola.cpp`) | 1 | WiFi (TX ≤ 17 dBm), NTP, WebSocket con TLS, telemetría, subida del búfer, órdenes, configuración, OTA, portal y consola |

Las dos se suscriben al watchdog de tareas (30 s). Se comunican con una cola de órdenes, una cola de respuestas y una «foto» del estado protegida con un mutex. Todo el I²C y el SPI lo usa solo la tarea de control (la lectura de registros para «cal_leer» pasa por el mismo mutex).

### 2.2 Módulos

| Archivo | Contenido |
|---|---|
| `include/config.h` | Pines (mapa de F4), tiempos, umbrales y versión (`FW_VERSION`) |
| `src/tipos.h/.cpp` | Motivos de detención, alarmas, eventos, `Config`, `Calibracion`, `Instantanea`, `Registro` de 64 bytes, órdenes |
| `src/atm90e26.*` | SPI modo 3 a 100 kHz, trama de 24 bits, configuración con CS1/CS2 y arranque en 8765H, lectura de U, I2, P2, Q2, S2, FP2 y f |
| `src/sensores.*` | AHT20 (CRC), DS18B20 por Skip ROM (CRC, descarta 85 °C de encendido), DS3231 en UTC (OSF) |
| `src/almacen.*` | NVS (red, configuración, calibración, estado persistente, OTA) y búfer circular en la partición `buffer` |
| `src/control.*` | Tarea de control (sección 3) |
| `src/red.*` | WiFi, NTP, WebSocket, protocolo y OTA |
| `src/portal.*` | Punto de acceso «EVSE-XXXX» con clave y formulario de configuración |
| `src/consola.*` | Comandos por el monitor serie |
| `src/ca_raiz.h` | Certificados raíz (Google Trust Services, Let's Encrypt, SSL.com), generados con `tools/generar_ca.py` desde `certifi` |
| `particiones.csv` | NVS de 64 KB, 2 × 4 MB de aplicación (OTA), búfer de 7 MB, coredump |

### 2.3 Medición

- **CT en I2:** MMode = 9022H (9422H con LNSel = 0). Se leen Urms, Irms2, Pmean2, Qmean2, Smean2, PowerF2 y Freq.
- **Formatos** (datasheet Atmel-46002B): Urms 0,01 V; Irms 0,001 A; Pmean en complemento a 2 con 1 W por LSB; PowerF en signo y magnitud con 0,001; Freq 0,01 Hz.
- **Arranque del chip:** SoftReset, FuncEn = 0020H (sag solo por IRQ, WarnOut solo para CalErr), SagTh al 70 % de la nominal, 5678H, registros 21H–2BH, CS1, 8765H; lo mismo con 30H–3AH y CS2. Si queda CalErr o AdjErr, es falla del medidor y se reintenta cada 30 s.
- **Energía (D29):** el firmware integra Pmean2 (P > 0) cada segundo. No depende de PL_constant, que solo afecta los pulsos de CF1 (LED2).
- **Calibración (S7):** `cal_auto V I` (consola o app) ajusta Ugain e IgainN en proporción a la referencia: Ugain_nuevo = Ugain × V_ref / V_medida. Se guarda en la NVS y se reescribe con sus sumas de verificación. Mientras no se calibre, la protección por tensión baja no actúa y la app muestra el aviso «Medidor sin calibrar».

## 3. Carga, protecciones y K1

K1 es el AQY214EHAX, normalmente abierto: `RELAY_EN = 1` cierra J2 y permite la carga. Sin energía, en un reset y durante el arranque (por R40), el EVSE no carga.

Cada 250 ms se calcula el motivo de detención. Manda el primero que se cumpla:

| Prioridad | Motivo | Cuándo | Cómo se sale |
|---|---|---|---|
| 1 | `falla` | ATM90E26 sin responder, con CalErr/AdjErr o WarnOut ≥ 5 s; sonda obligatoria sin lectura ≥ 30 s; 3 reinicios anormales en 10 min | Sola, cuando la causa desaparece; el bloqueo por reinicios, al reconocer |
| 2 | `temperatura` | Sonda ≥ `tmax_sonda` o placa (AHT20) ≥ `tmax_amb` | Sola, 5 min por debajo de (límite − histéresis). Al tercer disparo en la misma sesión queda enclavada hasta reconocer |
| 3 | `parar` | Pulsación de SW1 o del botón de J7 (enclavado y guardado en la NVS) | Mantener PARAR 3 s, o «Liberar PARAR» en la app (con confirmación) |
| 4 | `red` | Con el medidor calibrado: tensión < 70 % de la nominal durante 3 s | Sola, con tensión ≥ 85 % durante 1 min |
| 5 | `limite` | La sesión llegó al límite de kWh, minutos o COP | «Permitir» (empieza otra sesión) |
| 6 | `horario` | Fuera de las franjas, con el horario activo y hora válida | Sola, al entrar a una franja |
| 7 | `arranque` | Los primeros 10 s después de arrancar, o hasta confirmar con la política «detenida» | Sola, o «Permitir» |
| 8 | `app` | El usuario detuvo la carga | «Permitir» |

- **Política de arranque (D28, la decides tú):** `restaurar` (por defecto: el último permiso guardado, después de 10 s), `detenida` (espera «Permitir») o `permitida`. Se cambia en Ajustes → «Al volver la energía».
- **Sesión:** empieza con I ≥ `i_inicio` (1 A) durante 10 s con K1 cerrado. Termina con `fin_min` (10 min) sin corriente o al llegar a un límite. La energía, la duración y la potencia máxima se guardan en la NVS cada minuto y al empezar o terminar (D14).
- **Alarmas:** temp_sonda, temp_amb, sonda_falla, medidor_falla, red_baja, parar y reinicio son graves: quedan «sin reconocer» y avisan por Telegram. temp_aviso (sonda a 10 °C del corte), amb_falla, sin_hora y sin_calibrar son avisos.
- **LEDs:** LED3 fijo = en línea, lento = WiFi sin servidor, rápido = portal. LED4 fijo = cargando, destello corto = permitida sin consumo. LED5 fijo = falla o temperatura, rápido = PARAR enclavado, lento = alarmas sin reconocer.

## 4. Servidor (`app/`)

Cloudflare Workers con tres piezas:

| Pieza | Para qué |
|---|---|
| **Worker** (`src/index.js`) | API REST, autenticación, rutas del equipo y del navegador, limpieza diaria (cron) |
| **Durable Object `Equipo`** (`src/equipo.js`), uno por equipo | Tiene el WebSocket del ESP32 y los de los navegadores con la API de hibernación (no se cobra duración en reposo). Guarda el último estado, escribe el historial en D1, reenvía órdenes y espera su confirmación (10 s), pide telemetría cada 2 s cuando alguien mira el panel, detecta «fuera de línea» con una alarma cada minuto y avisa por Telegram |
| **D1** (SQLite, `migrations/0001_inicial.sql`) | usuarios, sesiones web, equipos y su configuración, permisos, mediciones, sesiones de carga, eventos, órdenes, firmware |
| **KV `FIRMWARE`** | los .bin para la OTA |

La configuración del equipo vive en D1 con un número de versión. Si el equipo se conecta con una versión menor, el servidor le manda la nueva; el equipo la valida, la guarda y devuelve la que quedó.

## 5. App web (`app/public/`)

HTML, CSS y JavaScript sin framework ni paso de compilación, servidos como archivos estáticos. Las gráficas se dibujan en un `<canvas>` con `grafica.js`, sin librerías. En español, pensada primero para el celular, con modo claro u oscuro según el sistema.

| Pantalla | Contenido |
|---|---|
| Entrar | correo y clave; la primera vez, crear el administrador con `CODIGO_INICIAL` |
| Equipos | lista con estado en línea y resumen |
| Panel | estado de la carga y su motivo, botones de permitir/detener, liberar PARAR y reconocer (con confirmación); alarmas activas; P, V, I, FP, f, energía y costo de la sesión, duración, energía total, temperaturas, humedad y WiFi; gráfica de la última media hora en vivo; último estado y «hace cuánto» si está fuera de línea |
| Historial | 24 h, 7 días, 30 días o 1 año: potencia, tensión, corriente y temperaturas; sesiones con kWh, duración, costo y motivo de fin; totales; CSV de sesiones y de mediciones |
| Alarmas | alarmas y avisos (o todos los eventos) de 90 días, reconocer, bitácora de órdenes |
| Ajustes | nombre, tensión nominal, tarifa, límites por sesión, hasta 4 franjas de horario, temperaturas, sonda obligatoria, política de arranque, avanzado. Para administradores: calibración, firmware y OTA, reiniciar, token nuevo, permisos y borrar |
| Perfil | nombre, chat de Telegram y prueba, cambio de clave, salir |
| Administración | agregar equipos (muestra el token una vez y los comandos para el equipo), crear y borrar usuarios |

## 6. Seguridad

- **TLS en todo.** El ESP32 verifica el certificado del servidor con las raíces de `src/ca_raiz.h` (no usa `setInsecure`). La hora para TLS sale del NTP, del DS3231 o de la «bienvenida» del servidor.
- **Credencial propia por equipo:** id + token de 192 bits, enviado en la cabecera `Authorization` del WebSocket y de la descarga OTA. En D1 solo queda su SHA-256. Se puede regenerar desde la app.
- **Usuarios:** la clave se deriva en el navegador con PBKDF2-SHA256 (300 000 iteraciones, sal = «evse-monitor|» + correo) y el servidor guarda SHA-256(sal aleatoria : derivada). Así el plan gratis (10 ms de CPU por petición) alcanza, y un volcado de la base no sirve sin repetir el PBKDF2. Sesión en una cookie HttpOnly, SameSite=Lax y Secure, de 30 días. Bloqueo de 15 min después de 5 intentos fallidos.
- **CSRF:** toda petición que cambia algo exige la cabecera `X-EVSE: 1`, que otro sitio no puede poner sin CORS.
- **Roles:** administrador (todo), propietario (controla su equipo) y solo lectura. La calibración y la OTA son solo para administradores.
- **OTA:** el .bin se sube con sesión de administrador, se guarda privado en KV y el equipo lo baja con su token. Se revisa tamaño y SHA-256 antes de cambiar de partición. Si el firmware nuevo se reinicia más de 3 veces sin llegar al servidor, el equipo vuelve al anterior.
- **Repo público:** nada secreto en git. `include/secrets.h` y `app/.dev.vars` están en `.gitignore`; en la nube, los secretos van con `wrangler secret put`.

## 7. Límites del plan gratis de Cloudflare (revisados el 23 nov 2026)

| Recurso | Límite gratis | Uso estimado con 1 equipo |
|---|---|---|
| Peticiones al Worker | 100 000/día | cientos (la app web es estática y no cuenta) |
| Durable Objects: peticiones | 100 000/día; los mensajes entrantes de WebSocket cuentan 20:1 | ≈ 12 000 mensajes → ≈ 600 |
| Durable Objects: duración | 13 000 GB-s/día; no se cobra mientras hiberna | poca: despierta solo con cada mensaje |
| Durable Objects: filas escritas | 100 000/día | ≈ 6 000 (una por telemetría cada 15 s) |
| D1: filas escritas / leídas | 100 000 / 5 000 000 por día | ≈ 3 000 escritas cargando 24 h; lecturas según cuánto se mire el historial |
| D1: tamaño | 500 MB por base | ≈ 25 MB/año (se borran mediciones de más de 2 años) |
| KV | 1 000 escrituras/día, 1 GB, 25 MiB por valor | una escritura por .bin |
| CPU | 10 ms por petición | por eso el PBKDF2 corre en el navegador |

Fuentes: [Durable Objects](https://developers.cloudflare.com/durable-objects/platform/pricing/), [D1](https://developers.cloudflare.com/d1/platform/limits/), [KV](https://developers.cloudflare.com/kv/platform/limits/), [Workers](https://developers.cloudflare.com/workers/platform/limits/), [archivos estáticos](https://developers.cloudflare.com/workers/static-assets/billing-and-limitations/).

## 8. Pruebas hechas en esta fase (23 nov 2026)

- Los dos firmwares compilan sin errores ni advertencias propias (prueba_placa 778 KB; evse_monitor 1,06 MB de 4 MB por ranura).
- Servidor y app en local (`wrangler dev`) con el simulador: registro del administrador con código y cierre del registro, alta del equipo, conexión con el búfer acumulado sin internet, telemetría en vivo, órdenes con confirmación (detener, permitir, cal_leer, orden inválida), configuración v1→v3 empujada y aplicada, límite de 2 kWh que cierra la sesión y detiene la carga, sobretemperatura que abre K1 y queda como alarma sin reconocer, OTA de un .bin real (subida, descarga con token, SHA-256 y «reinicio» con la versión nueva), CSV de sesiones y bitácora de órdenes. Se revisó la app en tamaño de celular.
- **Falta en la placa:** todo lo de S1–S8 con el hardware real (sección «S» del protocolo de pruebas) y la publicación en Cloudflare con tu cuenta.
