# Arquitectura del software — EVSE Monitor Rev 1.0 (Fase 10)

Cómo está hecho el software y por qué. Las decisiones van de D21 a D32 en `docs/DECISIONES.md` (D31 cambió el servidor de Cloudflare a Firebase el 24 nov). Las rutas de la base y lo que escribe cada uno están en `PROTOCOLO_MENSAJES.md`, y los pasos para compilar, subir a la PCB y publicar la app, en `GUIA_INSTALACION.md`.

## 1. Vista general

```text
 PLACA (SELV)                          INTERNET                    FIREBASE (plan Spark, gratis)              USUARIO
 ┌──────────────────────────────┐                                 ┌──────────────────────────────────────┐
 │ ATM90E26 ─SPI─┐              │   1 · inicio de sesión          │ Authentication                       │
 │ AHT20, DS3231 ─I²C─┐         │   (cuenta propia del equipo)    │  usuarios y una cuenta por equipo     │
 │ DS18B20 ─1-Wire─┐  │         │ ──────────────────────────────► │                                      │   https://<id>.web.app
 │ PARAR, LEDs, K1 │  │         │   2 · flujo SSE de /entrada     │ Realtime Database                    │◄── app web (celular / PC)
 │         ┌───────▼──▼──────┐  │ ◄══════════════════════════════ │  /entrada  config · órdenes · OTA    │    SDK web de Firebase:
 │         │ ESP32-S3        │  │   órdenes y configuración       │  /estado   telemetría en vivo        │    escucha en vivo y escribe
 │         │ tarea control ──┼──┼─ protecciones sin internet      │  /respuestas · /bitacora             │    órdenes y ajustes
 │         │ tarea red ──────┼──┼─ 3 · REST: estado, historial,   │  /mediciones · /eventos · /sesiones  │
 │         │ NVS · búfer 7 MB│  │   respuestas, partes de OTA     │  /firmware (el .bin en partes)       │
 │         └─────────────────┘  │ ──────────────────────────────► │  reglas de seguridad por ruta        │
 └──────────────┬───────────────┘                                 │ Hosting: la app web (archivos)       │
                └──► Telegram (lo manda el propio equipo)         └──────────────────────────────────────┘
```

- **El equipo inicia todo**: entra con su cuenta, deja abierta una conexión cifrada que escucha `/entrada/{id}` y escribe por REST (D8). No hay puertos abiertos en el router ni servidor propio que mantener.
- **Las protecciones viven en el ESP32.** El corte por temperatura, PARAR, la falla del medidor o de la sonda, la tensión baja y los límites de sesión los decide la tarea de control, que no depende de la red. La app solo ordena y muestra.
- **Sin internet no se pierde nada.** Cada medición, evento y sesión se escribe primero en un búfer circular de 7 MB en la flash. El equipo anota en la base hasta dónde subió y sigue desde ahí al volver la conexión.
- **Las reglas de seguridad son el servidor.** Firebase revisa cada lectura y escritura contra `app/database.rules.json`: un equipo solo toca lo suyo, un usuario de solo lectura no manda órdenes, la calibración y la OTA son del administrador. `npm run probar` las prueba (64 casos).
- **Costo mensual: US$ 0** con el plan Spark, sin tarjeta (sección 7). El dominio propio es opcional.

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
| **loop de Arduino** (`src/red.cpp`, `fb.cpp`, `portal.cpp`, `consola.cpp`) | 1 | WiFi (TX ≤ 17 dBm), NTP, Firebase con TLS (inicio de sesión, flujo de `/entrada`, REST), telemetría, subida del búfer, órdenes, configuración, OTA, Telegram, portal y consola |

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
| `src/fb.*` | Cliente mínimo de Firebase: inicio de sesión (Identity Toolkit), REST con conexión reutilizada y flujo SSE con redirecciones y `chunked` |
| `src/red.*` | WiFi, NTP, conexión paso a paso (sesión → id del equipo → `subido` → flujo), órdenes, configuración, historial, OTA por partes y avisos de Telegram |
| `src/portal.*` | Punto de acceso «EVSE-XXXX» con clave: WiFi y código de enlace |
| `src/consola.*` | Comandos por el monitor serie |
| `src/ca_raiz.h` | Certificados raíz (Google Trust Services para Firebase, GoDaddy para Telegram, ISRG), generados con `tools/generar_ca.py` desde `certifi` |
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
| 1 | `falla` | ATM90E26 sin responder o con CalErr/AdjErr ≥ 5 s; sonda obligatoria sin lectura ≥ 30 s; 3 reinicios anormales en 10 min | Sola, cuando la causa desaparece; el bloqueo por reinicios, al reconocer |
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

## 4. Servidor: Firebase (`app/`, D31)

No hay código de servidor: el plan Spark no tiene Cloud Functions ni Cloud Storage (los dos piden Blaze, con tarjeta), así que todo se resolvió con tres servicios gratis.

| Pieza | Para qué |
|---|---|
| **Authentication** (correo y clave) | Usuarios de la app y una cuenta por equipo (`<id>.<4 letras>@equipos.invalid`, clave de 24 caracteres). La app crea la cuenta del equipo con una segunda instancia del SDK, sin cerrar la sesión del administrador |
| **Realtime Database** (`us-central1`) | Todo lo demás: configuración, órdenes y respuestas, estado en vivo, historial, permisos, firmware. Rutas en `PROTOCOLO_MENSAJES.md` |
| **Reglas** (`database.rules.json`) | Quién lee y escribe cada ruta; validan órdenes (`por` = quien manda, hora del servidor), versión de la configuración que no baja y el id del equipo |
| **Hosting** | La app web; entrega la configuración del proyecto en `/__/firebase/init.json`, así no hay claves en el repositorio |

- **OTA sin Cloud Storage:** el .bin se guarda en la base en partes de 32 KB en base64 (`/firmware/{versión}/partes/n`, ≈ 1,4 MB por versión) y el equipo las baja una por una.
- **Telegram sin servidor:** lo manda el equipo cuando aparece una alarma grave o termina una carga. Lo que se pierde frente a Cloudflare: el aviso de «equipo fuera de línea» (no hay quién lo detecte); la app lo muestra al abrirla.
- **«Alguien mira el panel»:** la app escribe `/entrada/{id}/mirando` con la hora del servidor cada 20 s; el equipo lo recibe por el flujo y manda telemetría cada 2 s mientras sea de los últimos 45 s.
- **Primer administrador:** se marca a mano en la consola (`/admins/{uid}: true`); las reglas no dejan que nadie se lo ponga solo.

## 5. App web (`app/public/`)

HTML, CSS y JavaScript sin framework ni paso de compilación (D24), con el SDK web de Firebase 13.4 desde gstatic. Diseño (D32): un **tablero eléctrico futurista**, con módulos montados en un riel DIN, rótulos con los designadores de la placa (K1, P1, T1, E1), pilotos de luz y un diagrama mímico del circuito; policarbonato frío de día y vidrio antracita de noche (sigue el tema del sistema o se elige en Perfil). Pensada primero para el celular (barra de mando abajo) y en el computador con columna lateral y rejilla de 12. Detalle del sistema visual en `DESIGN.md` (raíz del repo).

| Pantalla | Contenido |
|---|---|
| Entrar | placa de características del equipo; entrar, crear cuenta, recuperar la clave |
| Equipos | lista con piloto de enlace, potencia y estado (si hay más de uno) |
| Panel | **X0** mímico RED → F1 → K1 → J2 → VE (la cuchilla de K1 se abre y cierra; la energía corre por el bus con la velocidad de la potencia); **P1** medidor de aguja con resorte, lectura grande, I, V y FP; **K1** selector giratorio Detener/Permitir que gira en azul hasta que el equipo confirma, con el motivo y las acciones (nueva sesión, soltar PARAR); **E1** sesión: kWh, costo, tiempo, pico; **H1** anunciador con las alarmas (titila lo no reconocido); **T1/T2** temperaturas con barra y marca de corte; **V1** red; **E0** energía total en un registro de rodillos |
| Historial | 24 h, 7 días o 30 días: resumen, potencia, tensión, temperaturas y energía por día; sesiones con kWh, costo, duración y motivo de fin; CSV de sesiones y de mediciones |
| Alarmas | anunciador completo con «Reconocer»; registro del equipo; bitácora de órdenes (quién, qué y qué contestó el equipo) |
| Ajustes | red, tarifa, límites, horario (hasta 4 franjas), temperaturas, sonda obligatoria, política de arranque, avanzado, Telegram. Administrador: código de enlace, calibración, firmware (instalar por OTA y ver el avance), acceso de usuarios, renombrar, reiniciar, clave nueva y borrar |
| Perfil | nombre, identificador (para hacerse administrador), tema, cambio de clave, salir |
| Administración | equipos (agregar), subir firmware, usuarios, mantenimiento (borrar historial viejo) |

Movimiento: una secuencia de encendido al abrir cada vista (los módulos se asientan en el riel y los pilotos destellan en orden), transiciones de vista con View Transitions, números que corren hasta su valor, la aguja con resorte, el flujo de energía del mímico y el giro del selector. Todo respeta «reducir movimiento» del sistema.

## 6. Seguridad

- **TLS en todo.** El ESP32 verifica los certificados con las raíces de `src/ca_raiz.h` (no usa `setInsecure`). La hora para TLS sale del NTP, del DS3231 o de la cabecera `Date` del inicio de sesión.
- **Cuenta propia por equipo**, con clave de 24 caracteres al azar. Su token dura 1 h y el equipo vuelve a entrar antes de que venza. La clave se puede cambiar desde la app (Clave nueva) y el código viejo deja de servir.
- **Usuarios:** Firebase Authentication guarda las claves con scrypt y limita los intentos. La sesión del navegador la maneja el SDK.
- **Reglas por ruta** (sección 4) en vez de un servidor: probadas con 64 casos contra el emulador (`app/pruebas/probar_reglas.mjs`).
- **Roles:** administrador (todo), propietario (manda su equipo) y solo lectura (ve; no lee el token de Telegram). La calibración y la OTA son solo para administradores.
- **OTA:** solo el administrador sube y pide; el equipo revisa tamaño y SHA-256 antes de cambiar de partición, no instala con una carga en curso y vuelve al anterior si el nuevo no llega a la app en 3 arranques.
- **Repo público:** nada secreto en git. La configuración web de Firebase (API key) no es secreta y además no está en el repo: la sirve Hosting. `include/secrets.h` y `app/.firebaserc` están en `.gitignore`.

## 7. Límites del plan Spark de Firebase (revisados el 24 nov 2026)

| Recurso | Límite gratis | Uso estimado con 1 equipo |
|---|---|---|
| Realtime Database: conexiones a la vez | 100 | 1 por equipo + 1 por navegador abierto |
| Realtime Database: almacenamiento | 1 GB | ≈ 50 MB/año de historial + ≈ 1,4 MB por versión de firmware |
| Realtime Database: descarga | 10 GB/mes | telemetría cada 2 s con la app abierta ≈ 1 KB → ≈ 1,8 MB/h mirando; historial de 30 días ≈ 3 MB por consulta |
| Hosting | 10 GB guardados, 360 MB/día de descarga | la app pesa ≈ 120 KB |
| Authentication | correo y clave sin costo (con Identity Platform, 50 000 usuarios activos al mes) | 2–5 cuentas |
| Cloud Functions y Cloud Storage | no disponibles en Spark | no se usan |

Fuente: [precios de Firebase](https://firebase.google.com/pricing) (consultada el 24 nov 2026).

## 8. Pruebas hechas (24 nov 2026)

- Los dos firmwares compilan sin errores ni advertencias propias (prueba_placa 779 KB; evse_monitor 1,08 MB de 4 MB por ranura).
- **Reglas de seguridad:** 64 de 64 casos bien en el emulador (administrador, propietario, solo lectura, cuenta extraña, equipo propio y equipo ajeno).
- **App + simulador contra el emulador de Firebase** (Authentication, Realtime Database y Hosting en local): crear cuenta, hacerse administrador, alta del equipo con su cuenta y código de enlace, conexión del simulador con 25 s de búfer sin internet, panel en vivo, Detener/Permitir con confirmación del equipo en ≈ 0,4 s, configuración v2 «aplicada en el equipo», límite de 1 kWh con «Nueva sesión», sobretemperatura con K1 abierto y alarma titilando, reconocer, historial con sesiones y costos, bitácora de órdenes, OTA de 244 KB en 8 partes con SHA-256 y confirmación de la versión nueva. Revisada en celular (375 px) y computador (1280 px), en tema oscuro y claro.
- **Falta en la placa:** S1–S8 con el hardware real (sección «S» del protocolo de pruebas) y publicar en Firebase con tu cuenta (guía, parte B). El cliente de Firebase del firmware (`fb.cpp`) se probó solo a través del simulador, que hace las mismas llamadas: la primera conexión real de la placa es la prueba que falta.
