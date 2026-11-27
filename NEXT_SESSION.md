# Siguiente sesión → Fase 10 (continuación): calibración (S7), S8 y cierre de la fase

La **Fase 9 se cerró el 24 nov** (`docs/sesiones/F9_cerrada.md`). **10H va avanzada:** la app está publicada en <https://evse-monitor-d37rs.web.app>, la placa 1 está enlazada (equipo `nico-01`) y se controla desde el PC y el celular. Ya se probó con red a través del transformador de aislamiento (D36): mide 60 Hz, tensión y corriente, pero **sin calibrar**. Falta instalar el firmware 1.0.2 por OTA, calibrar (S7), S8 de punta a punta y cerrar la fase.

## Prompt para iniciar

```text
Seguimos con "Control de carga EVSE" (repo público github.com/NicoGomez4262/control-carga-evse).
Objetivo: terminar la tarea 10H y cerrar la Fase 10: firmware 1.0.2 por OTA, calibración del medidor
(S7) con la placa en la red a través del transformador de aislamiento, S8 de punta a punta y cierre.

Antes de nada, lee: CLAUDE.md; NEXT_SESSION.md; docs/DECISIONES.md (D33–D36);
docs/software/GUIA_INSTALACION.md (partes C, D y D2); docs/pruebas/PROTOCOLO_PRUEBAS.md (S7, S8 y el
registro del 25–26 nov al final).

Estado (26 nov):
- App en https://evse-monitor-d37rs.web.app (Firebase evse-monitor-d37rs; CLI en app\ con npx.cmd).
  Entrada con Google o correo. Yo estoy en admins. Equipo nico-01.
- Placa 1 con evse_monitor 1.0.2 (instalado por OTA el 27 nov). COM8: si dice «Access is denied»,
  otro programa lo tiene abierto.
- Banco con red (D36): TJP 110:110 V 300 VA → regleta sin tierra → J1 (11 y 12); sin fuente en J6.
  Con un bombillo: 60,02 Hz, V 187,4 V, I 1,395 A, P 261 W sin calibrar.
- CT aprobado con corriente real (bombillo). PARAR, Quitar emergencia y Pausar/Reanudar desde la app, bien.

Qué quiero, en este orden:
1. Comprobar con 1.0.2: PARAR en vivo en la app y la reconexión (apagar y prender; hotspot 2 min;
   datos móviles 3 min) con tiempos medidos en la base.
2. S7: anotar TP2/TP3/TP5 con red; calibrar con cal_auto (V del multímetro en la regleta, I de una
   pinza o del Keysight en serie) y verificar con otra carga (error < 1–2 %).
3. S8: protecciones sin internet; historial completo al volver; Telegram (opcional).
4. Pendientes: humedad del AHT20 en 0 %; ¿pierde la hora el DS3231 al apagar? (pila en BT1).
5. Cerrar la Fase 10 (CLAUDE.md, «Al cerrar una fase»), con el bloque de software en el artifact.

Reglas: no toques la zona de red con la regleta encendida. Nada de claves del WiFi, códigos de enlace ni
tokens en git ni en el chat. En cada prueba, dime qué conectar con los números del mapa y su pin de Altium.
```

## Qué se hizo (25–26 nov, 10H segunda parte)

- **App publicada** en Firebase (`evse-monitor-d37rs`): proyecto, app web, base y reglas creados desde la CLI; entrada con correo y **Google**; tu cuenta en `admins`; equipo `nico-01` (D35).
- **Firmware 1.0.1** (USB): el flujo se cortaba a los 3–4 s por una resta sin signo; ahora se queda en línea y subió el búfer (D34). **1.0.2** compilado y cargado en la base para OTA: PARAR en vivo, telemetría inmediata y reconexión más rápida.
- **App:** responsive de verdad (4/8/12 columnas, ancho completo), panel en el orden que pediste, módulo **«Carga»** con pulsador rojo/verde y recorrido de la orden App → Nube → Placa → K1 con tiempos, «Pausa de emergencia / Quitar emergencia», Historial **«En vivo»**, anunciador a lo ancho y fondo vivo.
- **Pruebas:** enlace, lecturas en vivo, PARAR y Quitar emergencia desde la app, **CT con un bombillo** y **la placa alimentada por la red** a través del transformador de aislamiento TJP (D36).

## Qué se hizo (24 nov, 10H primera parte)

- **Cotejo app ↔ firmware:** el código de enlace (`EVSE1.` + base64url de `{d,k,e,c}`) es igual en `app/public/fb.js` y `almacen.cpp`. Las 13 rutas que usa el equipo están permitidas por `database.rules.json`, y los campos de `estado` y de la configuración coinciden con la app.
- **Corregido (D33):** (1) `particiones.csv`. PlatformIO sube la app en 0x10000 y `boot_app0` en 0xE000, y la tabla ponía `app0` en 0x20000, así que el bootloader quedaba en bucle. Ahora la NVS de 64 KB va en 0x810000. (2) Un `sonda`/`tension` hecho sin conexión se mezcla con la configuración de la nube en vez de quedar con la misma versión. (3) Ya no salen avisos `[E]` de NVS vacía.
- Comentarios de S5-4 en el firmware final (WarnOut e IRQ activos en alto; CS1 antes de 8765H).
- **`evse_monitor` 1.0.0 en la placa 1** (flash borrada). Compila sin advertencias (1.079.381 bytes). En el arranque: hora del DS3231, sonda 25,4 °C, AHT20 28,3 °C con 0 %HR, ATM90E26 en 8765H sin CalErr, «sin calibrar», sin WiFi. En el último arranque PARAR salió enclavado; se suelta con 3 s de SW1/J7 o `soltar_parar`.
- La app **no está publicada** todavía: no hay `app/.firebaserc` y la sesión de la CLI de Firebase estaba vencida (401). Guía B, paso 5, ahora explica `login --reauth`.

## Qué se hizo (24 nov, cierre de la Fase 9)

- U1 soldado; H0 (lupa), H4, H5 y H6 aprobadas. SW2/SW3 (KFC-A04-02) soldados y el SW730RD cableado a J7.
- `firmware/prueba_placa` subido por Claude a COM8 y **S1–S6 aprobadas** (detalle en el registro del protocolo).
- S5-4: WarnOut e IRQ **activos en alto**; la prueba ahora escribe una CS1 equivocada (al encender, el chip no marca error sin ella).
- Canal de corriente probado sin red con `s5 inyectar` (IO0 → 1 kΩ → D4-2): I2 de 0,008 a 2,985 A.
- Firmware de pruebas corregido: CR + LF del monitor, comillas y red guardada en `s6 con` (`s6 olvidar`), ritmo de `s6 carga`, `s2 aht` de 20 s con la trama.
- Cierre de la Fase 9: PLAN_FASES, DECISIONES (con notas para la Rev 1.1) y etiqueta `rev1.0`.

## Dónde estamos

<!--DIAG:ALL-->
```text
MAPA GENERAL · cada bloque indica la fase en que se diseña

EXTERNO · instalación (fuera de la PCB)
  [Breaker del EVSE] ─┬─► [F3 CT en L1] ─► [EVSE] ─► [Vehículo]
                      │         │           ▲  │
                      └─► J1    └─► J3      │  └─ sonda DS18B20 ─► J4
                                            └─ J2 (bornes de habilitación)
════════════════════════════════════════════════════════════════════════════════════════════════════════════════
PCB        ZONA RED · 120–240 VAC                     ┃ BARRERA  ┃      ZONA SELV · 12 V y 3.3 V
                                                      ┃ ≥ 6.4 mm ┃
                                                      ┃          ┃
 ENERGÍA   J1 ─► [F2 Protección] ─┬───────────────────┨  AC-DC   ┠─► [F2 Riel 12 V] ─► [F2 R-78CK + LC] ─► 3V3
                                  │                   ┃   (F2)   ┃
 MEDICIÓN V                       └─► [F3 Divisor] ───┨  AMC3330 ┠─► V ─► [F3 ATM90E26] ═SPI═► ESP32-S3
                                                      ┃   (F3)   ┃              ▲ I
 MEDICIÓN I                                           ┃          ┃              └─◄ [F3 Carga CT] ◄─ J3
                                                      ┃          ┃
 ACTUACIÓN J2 ◄── contacto seco (aislado) ────────────┨ PhotoMOS ┠◄─ LED ─ [F6 Driver K1] ◄─ GPIO ─ ESP32-S3
                                                      ┃   (F6)   ┃
 CONTROL                                              ┃          ┃   [F4 ESP32-S3] ─ WiFi ─► router ─► internet ─► app
 INTERFAZ                                             ┃          ┃ J5 ─► [F4 USB-C · USB-UART · auto-reset · LEDs] ─► ESP32-S3
 SENSORES                                             ┃          ┃ J4 ─► [F5 Sensores · RTC] ─► ESP32-S3
 BANCO                                                ┃          ┃ J6 ─► [F2 Entrada banco 12 V] ─► D2 ─► +VIN
════════════════════════════════════════════════════════════════════════════════════════════════════════════════
[F# bloque] fase en que se diseña · ▐bloque▌ se diseña en ESTA fase · ► carril con trabajo en esta fase
┃ ┃ barrera de aislamiento · ┨ ┠ componente que cruza la barrera (AC-DC, AMC3330, PhotoMOS K1)
│ L1/L2 (L/N en 120 V) con fusibles · J1–J6 conectores · J1 con cable largo a la línea · J2 contacto seco aislado
```
<!--/DIAG-->

```text
SOFTWARE (Fase 10) · ► ESTÁS AQUÍ: calibración y S8 (10H, final)

[Placa: S1–S6 ✓ · CT ✓ · red ✓] ─► [ESP32-S3: 1.0.2 ✓ en línea · OTA ✓] ═TLS═► [Firebase ✓] ─► [App web ✓ publicada] ─► PC y celular
          ▲ ▐S7 red + cal · S8▌             │ protecciones locales ✓                       ▲                                  │
          └─────────────────────────────────┴─ NVS + búfer 7 MB + DS3231 ✓                 └────────── órdenes ◄─────────────────┘
```

## Tareas de la Fase 10 (software)

- [x] 10A · Arquitectura (D21–D32; Firebase desde el 24 nov). **Falta tu decisión de D28** (arranque de K1).
- [x] 10B · Firmware de pruebas (`firmware/prueba_placa`), corrido en la placa 1: S1–S6 aprobadas (24 nov).
- [x] 10C · Protocolo de mensajes.
- [x] 10D · Firmware final (`firmware/evse_monitor`).
- [x] 10E · Simulador del equipo.
- [x] 10F · Servidor y base de datos.
- [x] 10G · Aplicación web.
- [ ] 10H · Integración con la placa:
  - [x] S1–S6 con `firmware/prueba_placa`, U1 + H4 y el canal de corriente sin red (24 nov).
  - [x] Publicar la app en Firebase; tu cuenta en `admins`; equipo `nico-01` (25 nov, D35).
  - [ ] Opcional: dominio `evse.nicolasgomez.dev` y bot de Telegram.
  - [x] Cotejar el enlace, las rutas y las reglas; borrar la flash y subir `firmware/evse_monitor` 1.0.0 (24 nov, D33).
  - [x] `wifi` + `enlazar CÓDIGO`; LED3 fijo y «En línea» en la app (25 nov, con el 1.0.1 de D34).
  - [x] Desde la app: lecturas en vivo, PARAR y Quitar emergencia, Pausar/Reanudar (25 nov).
  - [x] OTA 1.0.1 → 1.0.2 (27 nov, ≈ 70 s en total).
  - [ ] Pruebas de reconexión; sonda caliente; sin internet.
  - [x] CT con corriente real (bombillo, 25 nov).
  - [ ] S7: placa en la red por el transformador TJP ✓ (25 nov); falta anotar TP2/TP3/TP5, calibrar con `cal_auto` y verificar con otra carga (error < 1–2 %).
  - [ ] S8: de punta a punta con red; protecciones sin internet; historial completo al volver la red.
  - [ ] Al cerrar la fase: agregar el bloque de software al artifact de referencia (CLAUDE.md, paso 5).
- [x] 10I · Documentación.

## Ten a mano

- La placa 1, la fuente de banco (12 V, 0,2 A en J6), el Keysight 34461A, el cable USB-C de datos y cables dupont.
- La sonda DS18B20 y el CT. Un cable dúplex (paralelo) o un separador de línea para el CT.
- El celular con el hotspot y tu cuenta de Google para Firebase. El nombre y la clave del WiFi no van en el repo.
- Para S7: el transformador TJP 110:110 V (D36), la regleta con interruptor, el bombillo u otra carga resistiva, y una referencia de corriente (pinza o el Keysight en serie).
- Para mostrar el relé: pila de 9 V, resistencia de 1 kΩ y un LED en J2 (guía, D2).

## Pendientes fuera de esta fase

- Rev 1.1 de la PCB: gabinete, punto de prueba para el canal de corriente y lo demás de las notas en `docs/DECISIONES.md` (Fase 9).
- Fotos de las dos caras de la placa 1 para `docs/pruebas/fotos/` (opcional).
