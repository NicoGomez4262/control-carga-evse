# Guía de instalación y uso del software — EVSE Monitor Rev 1.0

Tres partes, en este orden: **A** subir el firmware de pruebas a la PCB y correr S1–S6; **B** publicar la app en Cloudflare; **C** subir el firmware final y conectarlo. La **D** es para actualizar por OTA y la **E**, para probar sin la placa. Los números en negrita son los puntos del mapa `docs/pruebas/mapa_puntos.png`, con su pin de Altium.

## 0. Lo que necesitas

- VS Code con la extensión **PlatformIO** (ya la tienes; la primera compilación baja el resto solo).
- Cable USB-C **de datos** a J5. En Windows 11 el CH340C sale como «USB-SERIAL CH340 (COMx)» en el Administrador de dispositivos; si sale «dispositivo desconocido», instala el driver CH341SER de WCH.
- Node.js 18 o más nuevo (tienes la 22) y Python 3 (para el simulador).
- **La placa no se alimenta por el USB.** El USB solo programa y muestra la consola.

| Estado de la placa | Alimentación para programar y probar |
|---|---|
| **Sin U1** (hoy) | Fuente en **3,30 V, límite 0,25 A**: + al **3** (TP3-1), − al **1** (TP1-1). Para K1 (S4), segundo canal en **12,0 V, límite 0,05 A**: + al **6** (J6-1), − al **7** (J6-2). **Sin WiFi**: sus picos de 350 mA pasan el límite |
| **Con U1 soldado** | Solo **12,0 V, límite 0,20 A** en J6: + al **6** (J6-1), − al **7** (J6-2). **Nunca más 3,3 V en TP3** |

## A. Firmware de pruebas en la PCB (S1–S6)

### A1. Compilar y subir

1. Alimenta la placa como dice la tabla y conecta el USB.
2. En VS Code: **Archivo → Abrir carpeta → `firmware/prueba_placa`** (la carpeta que tiene `platformio.ini`).
3. En la barra azul de abajo: **✓ (Build)** para compilar y **→ (Upload)** para subir. El CH340C hace el auto-reset solo: no hay que tocar nada.
4. **🔌 (Serial Monitor)** abre la consola a 115200. Sale la información del módulo y el menú. Escribe un comando y Enter.

Lo mismo desde PowerShell, si prefieres (cambia COM5 por tu puerto):

```powershell
& "$env:USERPROFILE\.platformio\penv\Scripts\pio.exe" run -d firmware\prueba_placa -t upload --upload-port COM5
```

```powershell
& "$env:USERPROFILE\.platformio\penv\Scripts\pio.exe" device monitor -p COM5 -b 115200
```

Si al subir sale «Wrong boot mode detected» (falla el auto-reset): une el **38** (J8-5, IO0) con el **39** (J8-6, GND), une un instante el **37** (J8-4, EN) con el **39**, suelta el **38** y vuelve a subir.

### A2. Qué comando corre cada etapa

| Etapa | Comando | Qué conectar o hacer | Esperado (anótalo en `PROTOCOLO_PRUEBAS.md`) |
|---|---|---|---|
| H5 | `info` | — | ESP32-S3, flash 16 MB, PSRAM ≈ 2048 KB, MAC (anótala) |
| S1-1 | `s1 leds` | — | LED3, LED4 y LED5 uno por uno, dos vueltas |
| S1-2/3 | `s1 parar` | pulsa SW1; después une los dos tornillos de J7 | «PARAR = 0 (pulsado)» en los dos casos |
| S2-1 | `s2 i2c` | — | solo 0x38 y 0x68, a 100 y a 400 kHz |
| S2-2 | `s2 aht` | un termómetro al lado | temperatura y humedad razonables (la placa calienta un poco) |
| S2-3/4 | — | V⎓: pila suelta; luego en BT1 con el «+» arriba, roja en el **35** (BT1-1), negra en el **1** | 3,0–3,3 V |
| S2-5 | `s2 hora 2026-11-24 10:30:00` (hora de Colombia) y `s2 rtc` | — | «OSF = 0» y la hora avanza (se guarda en UTC) |
| S2-6 | `s2 1hz` | — | 10 flancos en 10 s (9–11) |
| S2-7 | `s2 rtc` | apaga 5 min y vuelve a encender | la hora siguió y OSF = 0 |
| S3 | `s3 sonda` | placa apagada: rojo → J4-1 (**31**), datos → J4-2, negro → J4-3 | un dispositivo, familia 0x28; sube al apretarla |
| S4 | `s4 k1 1` / `s4 k1 0` | 12 V en J6; Ω entre el **17** (J2-1) y el **18** (J2-2); V⎓ entre el **34** (R41-2) y el **33** (R41-1) | cerrado: 25–40 Ω, ≈ 8,4 V, LED6 encendido; abierto: OL, 0 V, LED6 apagado. S4-4: con `s4 k1 1`, une un instante el **37** con el **39**: J2 abre |
| S5 | `s5` | sin red ni CT | paso a paso: CalStart 6886H, MMode 9422H, 5678H en CalStart y LastData, CalErr con 8765H (WarnOut e IRQ cambian; anota la polaridad), SoftReset, Urms e Irms2 ≈ 0 |
| S5 (generador) | `s5 monitor` | seno de 60 Hz en J3 (punta al +); V~ entre el **19** (D4-2) y el **20** (D4-1) | Irms2 crece en proporción a 50, 100 y 200 mVrms |
| S6 (con U1) | `s6 scan`, `s6 con RED CLAVE`, `s6 carga` | 12 V en J6; osciloscopio en el **3** con tierra en el **1** | RSSI anotado; 60 s transmitiendo sin reiniciarse; mínimo ≥ 3,0 V en el **3** |
| S7-8/9 | `s5 monitor`, `s5 zx` | montaje de S7 (transformador de aislamiento) | ≈ 60,00 Hz; 120 pulsos/s de ZX |

`s5 reg XX` y `s5 esc XX YYYY` leen o escriben cualquier registro del ATM90E26 (hexadecimal).

## B. La app en Cloudflare (una vez)

Las cuentas las creas tú; aquí va qué crear y dónde. Todo es gratis.

1. **Cuenta de Cloudflare:** <https://dash.cloudflare.com/sign-up> con tu correo. No pide tarjeta para lo que se usa aquí.
2. En PowerShell, dentro de `app\`:

```powershell
npm install
```

```powershell
npx wrangler login
```

   Se abre el navegador para autorizar a wrangler en tu cuenta.

3. Crea la base de datos y copia el `database_id` que te muestra en `app/wrangler.toml` (en `[[d1_databases]]`):

```powershell
npx wrangler d1 create evse-monitor
```

4. Crea el almacén del firmware y copia el `id` en `app/wrangler.toml` (en `[[kv_namespaces]]`):

```powershell
npx wrangler kv namespace create FIRMWARE
```

   Esos dos id no son secretos: se pueden subir a GitHub.

5. Crea las tablas en la base de la nube:

```powershell
npx wrangler d1 migrations apply evse-monitor --remote
```

6. Pon el código para crear el administrador (te lo pide; inventa uno largo y no lo pongas en el repo):

```powershell
npx wrangler secret put CODIGO_INICIAL
```

7. Publica:

```powershell
npx wrangler deploy
```

   Al final sale la dirección, algo como `https://evse-monitor.TU-SUBDOMINIO.workers.dev`.

8. Abre esa dirección en el celular o el PC. La primera vez sale **«Crear el administrador»**: nombre, correo, clave (mínimo 10 caracteres) y el código del paso 6. Después el registro queda cerrado; los demás usuarios los creas tú en **Administración**.
9. **Administración → Agregar un equipo:** id `evse-01` y un nombre. Te muestra **una sola vez** el token y los comandos para el equipo. Cópialos (si lo pierdes: Ajustes → «Generar token nuevo»).

**Dominio propio (opcional):** `evse.nicolasgomez.dev` funciona si el DNS de nicolasgomez.dev está en Cloudflare (se pasa gratis cambiando los nameservers en tu registrador). Luego: Cloudflare → Workers & Pages → evse-monitor → Settings → Domains & Routes → Add → Custom domain → `evse.nicolasgomez.dev`. Si el DNS sigue en otro lado, usa la dirección de workers.dev: funciona igual y con TLS.

**Notificaciones por Telegram (opcional):**

1. En Telegram, habla con **@BotFather** → `/newbot` → nombre y usuario del bot. Te da un token.
2. Guárdalo en el servidor:

```powershell
npx wrangler secret put TELEGRAM_TOKEN
```

3. Cada usuario le escribe `/start` a su bot, saca su número de chat con **@userinfobot**, lo pone en **Perfil → Chat id de Telegram** y pulsa **Probar notificación**.

Avisa de las alarmas graves (sobretemperatura, PARAR, falla del medidor o de la sonda, tensión baja, reinicio inesperado) y de «fuera de línea» después de 2 min.

## C. Firmware final en la PCB

### C1. Antes de la primera vez

- **Borra la flash** antes de subir `evse_monitor` por primera vez (cambia la tabla de particiones): en VS Code, ícono de PlatformIO (hormiga) → `placa` → Platform → **Erase Flash**. O:

```powershell
& "$env:USERPROFILE\.platformio\penv\Scripts\pio.exe" run -d firmware\evse_monitor -t erase --upload-port COM5
```

- **Opcional:** copia `firmware/evse_monitor/include/secrets.example.h` como `secrets.h` (está en `.gitignore`) y llena el WiFi, el servidor, el id y el token. Si no, se configura por la consola o el portal (C3).

### C2. Subir

1. **Archivo → Abrir carpeta → `firmware/evse_monitor`** → **→ (Upload)** → **🔌 (Serial Monitor)**.

   O en PowerShell:

```powershell
& "$env:USERPROFILE\.platformio\penv\Scripts\pio.exe" run -d firmware\evse_monitor -t upload --upload-port COM5
```

2. En la consola sale la versión, el búfer y la ayuda. Escribe `estado`. Sin red, con 3,3 V en TP3 y sin la sonda, lo normal es: K1 abierto, motivo «falla» (sonda obligatoria sin lectura). Para el banco: `sonda 0`.

### C3. Conectarlo a la app (con U1 soldado)

Por la **consola** (lo más rápido, con el USB conectado), con lo que te dio la app en B9:

```text
wifi "NOMBRE DE TU RED" CLAVE_DEL_WIFI
servidor evse-monitor.TU-SUBDOMINIO.workers.dev
equipo evse-01 TOKEN
reiniciar
```

O por el **portal**, sin computador: mantén **PARAR** (SW1) **5 s al encender** (LED3 parpadea rápido) → conéctate desde el celular a la red **EVSE-XXXX** con la clave `configurar-evse` (o la de `secrets.h`) → abre <http://192.168.4.1> → llena el formulario → «Guardar y reiniciar». El portal se cierra solo a los 10 min.

Cuando llega al servidor, **LED3 queda fijo** y en la app el equipo sale «En línea». `red` en la consola muestra el WiFi, el servidor y los registros por subir.

### C4. Primer uso

1. **Ajustes:** tensión nominal (120 o 240 V), tarifa, sonda obligatoria, temperaturas, horario, límites y **«Al volver la energía»** (D28: decide entre restaurar, quedar detenida o permitir siempre).
2. **Calibración (S7)**, con el transformador de aislamiento, una carga resistiva y la pinza de referencia: con la carga encendida y lecturas estables, **Ajustes → Calibración del medidor →** escribe la tensión del multímetro y la corriente de la pinza → **Calibrar**. O en la consola: `cal_auto 120.4 9.87`. Después revisa que P ≈ V × I con FP ≈ 1; si P sale negativa, el CT está al revés (gíralo o activa «El CT quedó al revés»).
3. **Prueba de punta a punta (S8):** Ω entre el **17** (J2-1) y el **18** (J2-2); en el panel, **Detener carga** → OL; **Permitir carga** → 25–40 Ω y LED6 encendido.
4. **Protecciones sin internet:** desconecta el router y comprueba que PARAR, la sonda caliente (o `tmax_sonda` bajo) y los límites siguen abriendo K1. Al volver la red, el historial se completa solo.

### C5. Consola del firmware final

`ayuda`, `estado`, `red`, `wifi`, `servidor`, `equipo`, `borrar_red`, `portal`, `permitir`, `detener`, `reconocer`, `soltar_parar`, `cal`, `cal_auto V I`, `cal_fabrica`, `sonda 0|1`, `tension 120|240`, `buffer`, `reiniciar`, `version`.

## D. Actualizar por OTA

1. Cambia `FW_VERSION` en `firmware/evse_monitor/include/config.h` (por ejemplo, `"1.0.1"`) y compila (✓).
2. En la app: **Ajustes → Firmware → Subir un .bin nuevo**: versión `1.0.1` y el archivo `firmware/evse_monitor/.pio/build/placa/firmware.bin`.
3. **Instalar** en esa versión. El equipo la baja con su token, revisa el SHA-256, se reinicia y queda confirmada cuando vuelve a conectarse («OTA: ok»). Si el firmware nuevo se reinicia más de 3 veces sin llegar al servidor, vuelve solo al anterior.
4. Por USB se puede subir siempre, como en C2.

## E. Probar sin la placa (simulador)

1. En `app\`: copia `.dev.vars.example` como `.dev.vars` y cambia `CODIGO_INICIAL`.

```powershell
npm run db:local
```

```powershell
npm run dev
```

2. Abre <http://localhost:8787>, crea el administrador y agrega el equipo `evse-01`.
3. En otra terminal, desde la raíz del repo (el `=` va pegado porque el token puede empezar por «-»):

```powershell
python -m pip install -r tools\simulador\requirements.txt
```

```powershell
python tools\simulador\simulador.py --id evse-01 --token=TOKEN --rapido 60
```

   Teclas: `p` PARAR · `l` soltar PARAR · `c` calentar la sonda · `d` desconectar el vehículo · `r` cortar 20 s la conexión · `q` salir. `--sin-internet 60` arranca sin conexión para probar el búfer.

**La placa real contra tu PC, sin TLS:** con `npm run dev` corriendo (escucha en toda la red local; Windows puede pedir permiso en el firewall), en la consola del equipo `servidor ws://192.168.1.50:8787` (la IP de tu PC) y `reiniciar`.

## F. Si algo falla

| Síntoma | Qué revisar |
|---|---|
| No sale el puerto COM | cable de datos; driver CH341SER; H1-4 f (D5) |
| «Wrong boot mode detected» | auto-reset (Q1, Q2, R19, R20); mientras tanto, el arranque manual de A1 |
| La placa se reinicia con «brownout» al conectar el WiFi | sin U1: es la fuente de 0,25 A en TP3; el WiFi espera a U1 (S6) |
| LED3 parpadea lento (WiFi sí, servidor no) | `red` en la consola: servidor, id y token; la hora (TLS necesita NTP o el DS3231); en la app, que el equipo exista |
| «credenciales del equipo inválidas» en los registros del Worker (`npx wrangler tail`) | token mal copiado: genera uno nuevo en Ajustes |
| Medidor con «falla» | `cal` en la consola: CalStart y AdjStart deben ser 8765 y SysStatus sin CalErr; `cal_fabrica` |
| Sonda «sin respuesta» | cableado de J4 (S3); para el banco, `sonda 0` |
| La app no muestra datos en vivo | la página usa WebSocket: recarga; en `npx wrangler tail` se ven los errores |
