# Guía de instalación y uso del software — EVSE Monitor Rev 1.0

Partes, en este orden: **A** subir el firmware de pruebas a la PCB y correr S1–S6; **B** publicar la app en **Firebase**; **C** subir el firmware final y enlazarlo con la app. La **D** es para actualizar por OTA, la **E** para probar sin la placa (emulador de Firebase y simulador) y la **F** para cuando algo falla. Los números en negrita son los puntos del mapa `docs/pruebas/mapa_puntos.png`, con su pin de Altium.

> Desde el 24 nov la app usa **Firebase** (D31) en lugar de Cloudflare: Authentication para los usuarios y los equipos, Realtime Database para todo lo demás y Hosting para la página. Plan **Spark**, gratis y sin tarjeta.

## 0. Lo que necesitas

- VS Code con la extensión **PlatformIO** (la primera compilación baja el resto sola).
- Cable USB-C **de datos** a J5. En Windows 11 el CH340C de la placa 1 sale como «USB-SERIAL CH340 (**COM8**)».
- Node.js 18 o más nuevo (tienes la 22) y Python 3 (para el simulador).
- Tu cuenta de Google para Firebase.
- **La placa no se alimenta por el USB.** El USB solo programa y muestra la consola.

| Estado de la placa | Alimentación para programar y probar |
|---|---|
| **Con U1 soldado** (placa 1, desde el 24 nov) | Solo **12,0 V, límite 0,20 A** en J6: + al **6** (J6-1), − al **7** (J6-2). **Nunca más 3,3 V en TP3** |
| Sin U1 (placa 2) | Fuente en **3,30 V, límite 0,25 A**: + al **3** (TP3-1), − al **1** (TP1-1). Para K1 (S4), otro canal en **12,0 V, límite 0,05 A** en J6. **Sin WiFi**: sus picos pasan el límite |

## A. Firmware de pruebas en la PCB (S1–S6)

### A1. Compilar y subir

1. Alimenta la placa como dice la tabla y conecta el USB.
2. En VS Code: **Archivo → Abrir carpeta → `firmware/prueba_placa`** (la carpeta que tiene `platformio.ini`).
3. En la barra azul de abajo: **✓ (Build)** para compilar y **→ (Upload)** para subir. El auto-reset del CH340C hace el resto.
4. **🔌 (Serial Monitor)** abre la consola a 115200. Sale la información del módulo y el menú. Escribe un comando y Enter.

Lo mismo desde PowerShell:

```powershell
& "$env:USERPROFILE\.platformio\penv\Scripts\pio.exe" run -d firmware\prueba_placa -t upload --upload-port COM8
```

```powershell
& "$env:USERPROFILE\.platformio\penv\Scripts\pio.exe" device monitor -p COM8 -b 115200
```

Si al subir sale «Wrong boot mode detected» (falla el auto-reset): une el **38** (J8-5, IO0) con el **39** (J8-6, GND), une un instante el **37** (J8-4, EN) con el **39**, suelta el **38** y vuelve a subir.

### A2. Qué comando corre cada etapa

| Etapa | Comando | Qué conectar o hacer | Esperado (anótalo en `PROTOCOLO_PRUEBAS.md`) |
|---|---|---|---|
| H5 | `info` | — | ESP32-S3, flash 16 MB, PSRAM ≈ 2048 KB, MAC |
| S1-1 | `s1 leds` | — | LED3, LED4 y LED5 uno por uno, dos vueltas |
| S1-2/3 | `s1 parar` | pulsa SW1; después une los dos tornillos de J7 | «PARAR = 0 (pulsado)» en los dos casos |
| S2-1 | `s2 i2c` | — | solo 0x38 y 0x68, a 100 y a 400 kHz |
| S2-2 | `s2 aht` | un termómetro al lado | temperatura y humedad razonables |
| S2-5 | `s2 hora 2026-11-24 10:30:00` (hora de Colombia) y `s2 rtc` | — | «OSF = 0» y la hora avanza |
| S2-6 | `s2 1hz` | — | 10 flancos en 10 s (9–11) |
| S3 | `s3 sonda` | placa apagada: rojo → J4-1 (**31**), datos → J4-2, negro → J4-3 | un dispositivo, familia 0x28 |
| S4 | `s4 k1 1` / `s4 k1 0` | Ω entre el **17** (J2-1) y el **18** (J2-2) | cerrado: 25–40 Ω y LED6 encendido; abierto: OL |
| S5 | `s5` | sin red ni CT | paso a paso; en S5-4 el firmware escribe la polaridad de WarnOut e IRQ (A3) |
| S5 (generador) | `s5 monitor` | seno de 60 Hz en J3 | Irms2 crece en proporción a 50, 100 y 200 mVrms |
| S6 | `s6 scan`, `s6 con RED CLAVE` (nombre con espacios entre comillas: `s6 con "Mi Red" CLAVE`), `s6 carga` | 12 V en J6; osciloscopio en el **3** con tierra en el **1** | RSSI anotado; 60 s transmitiendo sin reiniciarse; mínimo ≥ 3,0 V en el **3** |
| S7-8/9 | `s5 monitor`, `s5 zx` | montaje de S7 (transformador de aislamiento) | ≈ 60,00 Hz; 120 pulsos/s de ZX |

`s5 reg XX` y `s5 esc XX YYYY` leen o escriben cualquier registro del ATM90E26 (hexadecimal).

### A3. S5-4 · polaridad de WarnOut e IRQ, paso a paso

**Qué es:** el ATM90E26 tiene dos salidas de aviso. **WarnOut** (red `MEAS_WARN`, llega al IO21) marca un error grave, como una suma de verificación mal; **IRQ** (red `MEAS_IRQ`, al IO14) avisa eventos. El datasheet no dice si se «activan» subiendo a 3,3 V o bajando a 0 V. No es grave: el firmware final detecta las fallas leyendo el registro SysStatus, no estos pines. Se anota para que quede documentado y para una versión futura que use el pin como interrupción.

**Cómo se hace:** el firmware provoca el error a propósito (escribe una CS1 equivocada y 8765H en CalStart) y lee los dos pines antes y después. Sin escribir CS1 no sirve: al encender, el chip no marca error con 8765H (se vio en la placa 1 el 24 nov).

1. Placa con 12 V en J6 y el USB conectado; firmware de pruebas subido (A1). Sin red ni CT.
2. En la consola, escribe `s5` y Enter. Va de a un paso: con Enter pasas al siguiente.
3. Al llegar a **S5-4** sale un recuadro como este:

```text
S5-4 · CS1 = AA34H (equivocada) y 8765H → SysStatus (01H) = C000H, CalErr = 11
  [ OK ] CalErr = 11
  [ OK ] WarnOut e IRQ cambiaron de estado
  ┌─ Copia estas dos líneas en el registro del protocolo (S5-4):
  │ WarnOut (red MEAS_WARN, IO21): normal BAJO (0 V) → con error ALTO (3,3 V) ⇒ ACTIVO EN ALTO
  │ IRQ (red MEAS_IRQ, IO14): normal BAJO (0 V) → con error ALTO (3,3 V) ⇒ ACTIVO EN ALTO
  └─ (el datasheet no dice la polaridad; el firmware final no depende de ella)
```

   (Es lo que salió en la placa 1 el 24 nov: los dos son activos en alto.)

4. Copia las dos líneas del recuadro en `docs/pruebas/PROTOCOLO_PRUEBAS.md`, en la tabla de S5, fila 4, columna de resultado. O pégamelas en el chat y yo las anoto.
5. El paso siguiente (S5-5, SoftReset) devuelve los pines a su nivel normal: así se confirma que el cambio vino del error.

Si una línea dice **«NO cambió»**, el pin del ATM90E26 o su pista hasta el ESP32 tiene un problema: revisa la soldadura con la lupa (H0). Confirmación con el multímetro (opcional): DCV con la negra en el **1** (GND) y la roja en el pin del ATM90E26 o del ESP32 de esa red; debe medir lo mismo que dice la consola (0 V o 3,3 V).

## B. La app en Firebase (una vez)

Las cuentas las creas tú; aquí va qué crear y dónde. Todo es gratis (plan Spark).

1. **Proyecto:** <https://console.firebase.google.com> → **Agregar proyecto** (o «Crear un proyecto») → nombre `evse-monitor` → Google Analytics no hace falta → **Crear proyecto**. Firebase le pone un id, por ejemplo `evse-monitor-1a2b3`.
2. **Usuarios:** en el menú, **Compilación → Authentication → Comenzar → Método de acceso → Correo electrónico/contraseña → Habilitar** (solo la primera opción) → **Guardar**.
3. **Base de datos:** **Compilación → Realtime Database → Crear una base de datos** → ubicación **Estados Unidos (us-central1)** → **Comenzar en modo bloqueado** → **Habilitar**. La dirección queda arriba del árbol de datos: `https://evse-monitor-1a2b3-default-rtdb.firebaseio.com`.
4. **App web:** engranaje ⚙ → **Configuración del proyecto → General → Tus apps →** ícono **`</>`** → apodo `app web` → marca **«Configurar también Firebase Hosting»** → **Registrar app** → Siguiente → Siguiente → **Ir a la consola**. No hace falta copiar el código que muestra: Hosting se lo entrega a la página solo.
> **Hecho el 25 nov:** el proyecto es `evse-monitor-d37rs` (<https://evse-monitor-d37rs.web.app>). Los pasos 1 a 4 se pueden hacer con la CLI: `npx.cmd firebase projects:create`, `npx.cmd firebase apps:create WEB "app web"`, y la base por defecto como en D35. En PowerShell usa **`npx.cmd`** (la política de scripts bloquea `npx`). Si una carpeta superior tiene otro proyecto activo, la CLI lo usa en vez de `.firebaserc`: corre `npx.cmd firebase use default` dentro de `app\`. **Google:** Authentication → Método de acceso → Agregar proveedor → Google → Habilitar → correo de asistencia → Guardar.

5. **Publicar** (PowerShell, dentro de `app\`):

```powershell
npm install
```

```powershell
npx firebase login
```

   Se abre el navegador para autorizar con tu cuenta de Google. Si la CLI ya tenía una sesión vieja (al listar proyectos sale «401» o «Failed to list Firebase projects»), usa `npx firebase login --reauth`. Si tiene varias cuentas, `npx firebase login:list` las muestra y `npx firebase login:use CORREO` elige la del proyecto.

```powershell
npx firebase use --add
```

   Elige el proyecto del paso 1 y ponle de alias `default`. Queda en `app/.firebaserc` (no se sube a git).

```powershell
npm run desplegar
```

   Sube las reglas de seguridad (`database.rules.json`) y la app. Al final sale la dirección: `https://evse-monitor-1a2b3.web.app`.

6. **Tu cuenta:** abre esa dirección en el celular o el PC → **Crear cuenta** (nombre, correo, clave de 8 o más caracteres). Sale «Pídele acceso a quien administra»: abre **«¿Eres tú quien administra?»** y copia tu identificador con el botón.
7. **Hazte administrador** (solo esta vez): en la consola de Firebase, **Realtime Database → Datos**, pasa el mouse por la raíz (la dirección de la base) → **+** → Clave `admins` → en el **+** de esa fila agrega un hijo: Clave = tu identificador, Valor = `true` → **Agregar**. Recarga la app: ya entras como administrador.
8. **El equipo:** en la app, **Nuevo equipo** → id `evse-01`, nombre (por ejemplo «Garaje») y la red (240 V L1–L2 o 120 V L–N) → **Agregar equipo**. Te lleva a **Ajustes → Enlace del equipo**: con el botón de copiar tienes el **código de enlace** (empieza por `EVSE1.`). Es lo único que necesita la placa. Puedes volver a verlo cuando quieras; si se filtra, **Clave nueva** lo invalida.
9. **Más usuarios:** cada persona crea su cuenta en la app; luego tú, en **Ajustes → Acceso**, la eliges y le das **Propietario** (manda) o **Solo lectura**.

**Telegram (opcional):** en Telegram, **@BotFather** → `/newbot` → te da el token del bot. Escríbele `/start` a tu bot y saca tu número de chat con **@userinfobot**. En la app: **Ajustes → Avisos por Telegram** → token y chat → **Guardar** → **Probar** (el equipo mismo manda el mensaje). Avisa de alarmas graves y del fin de cada carga.

**Dominio propio (opcional):** **Hosting → Agregar dominio personalizado** → `evse.nicolasgomez.dev` → Firebase te da dos registros (TXT y A) para poner en el DNS de nicolasgomez.dev, donde esté. No hace falta mover el DNS.

**Límites del plan gratis** que importan aquí: base de datos de 1 GB y 10 GB de descarga al mes; 100 conexiones a la vez; Hosting de 10 GB y 360 MB de descarga al día. Un equipo usa unos 50 MB al año de historial. **Administración → Mantenimiento** borra lo más viejo que 2 años.

## C. Firmware final en la PCB

### C1. Antes de la primera vez

- **Borra la flash** antes de subir `evse_monitor` por primera vez (cambia la tabla de particiones): ícono de PlatformIO (hormiga) → `placa` → Platform → **Erase Flash**. O:

```powershell
& "$env:USERPROFILE\.platformio\penv\Scripts\pio.exe" run -d firmware\evse_monitor -t erase --upload-port COM8
```

- **Opcional:** copia `firmware/evse_monitor/include/secrets.example.h` como `secrets.h` (está en `.gitignore`) y pon el WiFi y el código de enlace. Si no, se configura por la consola o el portal (C3).

### C2. Subir

**Archivo → Abrir carpeta → `firmware/evse_monitor`** → **→ (Upload)** → **🔌 (Serial Monitor)**. O:

```powershell
& "$env:USERPROFILE\.platformio\penv\Scripts\pio.exe" run -d firmware\evse_monitor -t upload --upload-port COM8
```

En la consola sale la versión, el búfer y la ayuda. Escribe `estado`. Sin red y sin la sonda, lo normal es K1 abierto con motivo «falla» (sonda obligatoria sin lectura). Para el banco: `sonda 0` (puede ir antes o después de enlazar: si va antes, al conectarse se mezcla con la configuración de la app, D33). Con la sonda puesta y sin permiso, lo normal es K1 abierto con motivo «app».

La placa 1 ya tiene `evse_monitor` 1.0.0 desde el 24 nov: no hace falta borrar ni volver a subir para enlazarla. Si después de subir la consola repite `rst:0x3 (RTC_SW_SYS_RST)` sin llegar a «EVSE Monitor», revisa que `particiones.csv` tenga `otadata` en 0xE000 y `app0` en 0x10000 (D33).

Si `estado` dice «motivo: parar» y la alarma «PARAR pulsado», PARAR quedó enclavado (se guarda en la NVS y sobrevive a los reinicios). Se suelta manteniendo SW1 o el botón de J7 **3 s**, con `soltar_parar` o desde la app.

### C3. Enlazarlo con la app

Por la **consola** (con el USB), pegando el código del paso B8:

```text
wifi "NOMBRE DE TU RED" CLAVE_DEL_WIFI
enlazar EVSE1.xxxxxxxx…
reiniciar
```

O por el **portal**, sin computador: mantén **PARAR** (SW1) **5 s al encender** (LED3 parpadea rápido) → conéctate desde el celular a la red **EVSE-XXXX** con la clave `configurar-evse` → abre <http://192.168.4.1> → elige tu WiFi, pon su clave y pega el código de enlace → **Guardar y reiniciar**. El portal se cierra solo a los 10 min.

Cuando llega a la app, **LED3 queda fijo** y el panel dice «En línea». `red` en la consola muestra el WiFi, la base de Firebase, el equipo, los registros por subir y el último error.

### C4. Primer uso

1. **Ajustes:** red (120 o 240 V), tarifa, sonda obligatoria, temperaturas, horario, límites y **«Al volver la energía»** (D28: restaurar, quedar detenida o permitir siempre). **Guardar y enviar al equipo**: arriba sale «aplicada en el equipo» cuando la placa la confirma.
2. **Calibración (S7)**, con el transformador de aislamiento, una carga resistiva y la pinza de referencia: con la carga encendida y lecturas estables, **Ajustes → Calibración del medidor →** tensión del multímetro y corriente de la pinza → **Calibrar**. O en la consola: `cal_auto 120.4 9.87`. Después P ≈ V × I con FP ≈ 1; si P sale negativa, el CT está al revés (gíralo o activa «El CT quedó al revés» en Avanzado).
3. **Prueba de punta a punta (S8):** Ω entre el **17** (J2-1) y el **18** (J2-2); en el panel gira el selector a **Detener** → OL; a **Permitir** → 25–40 Ω y LED6 encendido. El selector queda girando en azul hasta que el equipo confirma.
4. **Protecciones sin internet:** desconecta el router y comprueba que PARAR, la sonda caliente (o un corte bajo) y los límites siguen abriendo K1. Al volver la red, el historial se completa solo.

### C5. Consola del firmware final

`ayuda`, `estado`, `red`, `wifi`, `enlazar`, `borrar_red`, `portal`, `permitir`, `detener`, `reconocer`, `rearmar` (= `soltar_parar`, desde 1.0.2), `cal`, `cal_auto V I`, `cal_fabrica`, `sonda 0|1`, `tension 120|240`, `buffer`, `reiniciar`, `version`.

## D. Actualizar por OTA

1. Cambia `FW_VERSION` en `firmware/evse_monitor/include/config.h` (por ejemplo, `"1.0.1"`) y compila (✓).
2. En la app: **Administración → Subir firmware**: versión `1.0.1` y el archivo `firmware/evse_monitor/.pio/build/placa/firmware.bin`. La app lo parte en trozos de 32 KB, calcula el SHA-256 y lo guarda en la base.
3. **Ajustes del equipo → Firmware → Instalar.** El equipo baja los trozos con su cuenta, revisa el SHA-256, se reinicia (K1 abierto unos 15 s) y queda confirmado al volver a la app. No lo hace si hay una carga en curso. Si el nuevo se reinicia 3 veces sin llegar a la app, vuelve solo al anterior y no lo reintenta.
4. Por USB se puede subir siempre, como en C2.

## D2. Banco con red y demostración del relé (D36)

1. **Transformador de aislamiento** (TJP 110:110 V, 300 VA): desenchufado, en Ω 2W, entre los dos devanados y contra el chasis debe marcar **OL** (si hay continuidad es un autotransformador: no sirve).
2. Toma → fusible de 3 A → primario; chasis a la tierra de la clavija. Secundario **sin tierra** → regleta con interruptor → J1: un cable al **11** (J1-1) y otro al **12** (J1-2); da igual cuál. Sin la fuente en J6 (la placa se alimenta por PS1) y la primera vez sin USB.
3. Con la regleta encendida, DCV con la negra en el **1**: **2** (TP2-1) 11,5–11,9 V; **3** (TP3-1) 3,20–3,40 V; **5** (TP5-1) ≈ 3,3 V. La placa se pone en línea sola.
4. **Testigo del relé en J2** (aislado de todo lo demás): pila de 9 V (+) → 1 kΩ → LED (ánodo) → **17** (J2-1); **18** (J2-2) → (−) de la pila. En la app, **Pausar** apaga el LED y **Reanudar** lo prende; el módulo «Carga» muestra el recorrido App → Nube → Placa → K1 y el tiempo. También: Ω entre el 17 y el 18 (OL ↔ 25–40 Ω) y LED6.
5. No toques la zona de red con la regleta encendida; mide solo en los puntos amarillos; la pinza de tierra del osciloscopio nunca en la zona de red.

## E. Probar sin la placa (emulador + simulador)

El emulador de Firebase corre todo en tu PC (usuarios, base y página), sin tocar el proyecto real. Necesita Java 21: hay uno portátil en `C:\Users\nico\.herramientas\` (sin instalar; para quitarlo, borra la carpeta).

1. En PowerShell, dentro de `app\`:

```powershell
$env:Path = "$env:USERPROFILE\.herramientas\jdk-21.0.13.1+2-jre\bin;$env:Path"; npm run emular
```

2. Abre <http://127.0.0.1:5000> → **Crear cuenta**. Para hacerte administrador: <http://127.0.0.1:4000/database> → en la raíz, **+** → `admins` → hijo con tu identificador y valor `true`. Recarga.
3. **Nuevo equipo** `evse-01` → **Ajustes → Enlace del equipo → copiar**.
4. En otra terminal, desde la raíz del repo:

```powershell
python -m pip install -r tools\simulador\requirements.txt
```

```powershell
python tools\simulador\simulador.py --enlace "EVSE1.…" --rapido 60
```

   Teclas: `p` PARAR · `l` soltar PARAR · `c` calentar la sonda · `d` desconectar el vehículo · `r` cortar 20 s la conexión · `q` salir. `--sin-internet 60` arranca sin conexión para probar el búfer.

5. **Pruebas de las reglas de seguridad** (con el emulador corriendo): `npm run probar` en `app\`. Deben salir todas bien (64 de 64 el 24 nov).

## F. Si algo falla

| Síntoma | Qué revisar |
|---|---|
| No sale el puerto COM | cable de datos; driver CH341SER; H1-4 f (D5) |
| «Could not open COM8 … Access is denied» justo después de subir o borrar | casi siempre se pasa solo en unos segundos: vuelve a intentar. Si sigue, cierra el monitor serie y cualquier programa que revise los puertos COM |
| La consola repite `rst:0x3 (RTC_SW_SYS_RST)` sin llegar a «EVSE Monitor» | tabla de particiones: `otadata` en 0xE000 y `app0` en 0x10000 (D33); borra la flash y sube otra vez |
| «Wrong boot mode detected» | auto-reset (Q1, Q2, R19, R20); mientras tanto, el arranque manual de A1 |
| La placa se reinicia con «brownout» al conectar el WiFi | la fuente: con U1, 12 V en J6 con límite de 0,20 A |
| LED3 parpadea lento (WiFi sí, app no) | `red` en la consola: «Último error» lo dice. Ver las tres filas siguientes |
| «inicio de sesión: INVALID_LOGIN_CREDENTIALS» | el código de enlace es viejo (se cambió la clave): cópialo otra vez de la app y `enlazar` |
| «esta cuenta no está asignada a ningún equipo» | el equipo se borró en la app: créalo de nuevo y enlaza el código nuevo |
| «flujo: HTTP 401» o «permission denied» | faltan las reglas: `npm run reglas` en `app\` |
| TLS que no conecta | la hora: el ESP32 la toma del NTP o del DS3231; sin hora no valida certificados |
| Medidor con «falla» | `cal` en la consola: CalStart y AdjStart en 8765 y SysStatus sin CalErr; `cal_fabrica` |
| Sonda «sin respuesta» | cableado de J4 (S3); para el banco, `sonda 0` |
| La app dice «Sin conexión» aunque la placa está en línea | la hora del celular o del PC muy corrida; recarga la página |
| La app muestra «No tienes permiso» | tu cuenta no tiene acceso a ese equipo: pídelo en Ajustes → Acceso |
