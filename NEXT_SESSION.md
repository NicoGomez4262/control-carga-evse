# Siguiente sesión → Fase 10 (continuación): software en la placa real

El software de la Fase 10 está escrito y probado sin la placa. El 24 nov la app pasó de Cloudflare a **Firebase** (D31, pedido del usuario) y se rediseñó como tablero eléctrico (D32). Falta **10H**: publicar la app en Firebase, correr S1–S8 con el firmware en la PCB, calibrar el ATM90E26 y la prueba de punta a punta. La Fase 9 sigue abierta por H6, SW2/SW3 y la etiqueta Rev 1.0.

## Prompt para iniciar

```text
Seguimos con el proyecto "Control de carga EVSE" (repo público github.com/NicoGomez4262/control-carga-evse).
Toca seguir con las pruebas de la placa 1 conectando todo, y después correr el software en la placa real
(tarea 10H de la Fase 10).

Antes de nada, lee:
- CLAUDE.md (reglas: español, tú; diagramas como gráfico; commits sin coautor; subir a GitHub al final con
  docs/tools/sincronizar_altium.py --commit).
- NEXT_SESSION.md y docs/PLAN_FASES.md (Fases 9 y 10).
- docs/pruebas/PROTOCOLO_PRUEBAS.md (H6, S1–S8 y el registro) y docs/pruebas/mapa_puntos.png.
- docs/software/GUIA_INSTALACION.md (cómo subir cada firmware, S5-4 paso a paso y cómo publicar la app en Firebase)
  y docs/DECISIONES.md (D20–D32).

Estado de la placa 1 (24 nov):
- H0 (lupa), H1, H2, H3, H4 (U1 soldado, encendido escalonado 3 → 6 → 12 V) y H5 aprobadas.
- El CH340C sale en COM8. esptool 5.7.0: ESP32-S3 rev v0.2, PSRAM de 2 MB, flash de 16 MB, MAC 10:bd:a3:65:01:08.
  La flash está vacía. Puedes correr esptool y PlatformIO tú mismo en COM8
  (pio está en ~/.platformio/penv/Scripts/pio.exe, no en el PATH).
- Con U1 soldado, NUNCA 3,3 V en TP3: todo por J6 (12 V, límite 0,15–0,2 A) o por la red en S7.
- Compré en Sigma: CT SCT-013-000V, sonda SEN DS18B20 2M, 4 pulsadores KFC-A04-02 (para SW2 y SW3) y el botón
  de panel SW730RD (va por cables a J7, no en la placa). Ya tenía la CR2032.
- [Di aquí si ya creaste el proyecto de Firebase y publicaste la app (guía, parte B), y la dirección .web.app.]
- [Di qué política de arranque de K1 eliges (D28): restaurar, detenida o permitida.]

Qué quiero en esta sesión, en este orden:
1. Diagrama «ESTÁS AQUÍ» como gráfico y la lista de tareas que falta.
2. Soldar SW2 y SW3 (KFC-A04-02) y probarlos: Ω 2W entre EN (37, J8-4) y GND (39, J8-6) al pulsar SW2, y
   entre IO0 (38, J8-5) y GND al pulsar SW3. Cablear el SW730RD a J7 (sin polaridad) y probarlo.
3. H6: pila, CT y sonda, cada uno conectado con la placa apagada, con lo que hay que medir.
4. Firmware de pruebas (firmware/prueba_placa): súbelo tú a COM8 y acompáñame en S1–S6, anotando cada
   resultado en el registro del protocolo. S5-4: anotar la polaridad de WarnOut e IRQ.
5. Firmware final (firmware/evse_monitor): borrar la flash, subirlo y enlazarlo con `wifi` + `enlazar CÓDIGO`
   (el código sale en la app, Ajustes → Enlace del equipo; nada de eso va a git).
6. S7 con transformador de aislamiento, regleta con interruptor, carga resistiva de 1–1,5 kW y pinza:
   calibración (cal_auto) y verificación con otra carga. Primero repetir el aislamiento de H1-5 y los
   fusibles de H1-6 con la placa apagada.
7. S8: prueba de punta a punta (orden en la app → K1 → J2 medido) y protecciones sin internet.
8. Corregir en el firmware o la app lo que salga mal (registrar cada cambio), y cerrar las Fases 9 y 10 según
   CLAUDE.md si quedaron completas. Subir todo a GitHub.

Reglas:
- En cada prueba, dime qué conectar con los números del mapa y su pin de Altium (por ejemplo, 6 (J6-1)),
  el ajuste de la fuente y del multímetro (Keysight 34461A: DCV, ACV, Ω 2W, Diode) y qué debe salir.
- La red solo con transformador de aislamiento y sin tocar nada energizado; el CT se enchufa en J3 antes de
  abrazar un cable con corriente y nunca se desenchufa con corriente.
- Nada de claves del WiFi, tokens ni credenciales en git.
```

## Qué se hizo (23 nov, F10)

- **Arquitectura (D21–D30):** firmware Arduino-ESP32 2.0.17 en PlatformIO con dos tareas (control y red); WebSocket seguro saliente con el certificado verificado; Cloudflare Workers + un Durable Object por equipo + D1 + KV en el plan gratis (US$ 0/mes); app web sin framework; usuarios con clave derivada en el navegador y token propio por equipo; portal cautivo y consola para el WiFi; OTA desde la app con vuelta atrás; Telegram para las alarmas. El usuario pidió que Claude se encargara de todo, así que las decisiones quedaron tomadas y documentadas con sus alternativas; D28 (arranque de K1) es configurable y la decide el usuario.
- **`firmware/prueba_placa`:** menú por consola para H5 y S1–S6 (más ayudas para S5 con generador y S7). Compila (778 KB).
- **`firmware/evse_monitor`:** ATM90E26 con LNSel = 0, CS1/CS2 y arranque verificado; AHT20, DS3231 y DS18B20 sin bloquear; energía por integración de P; sesiones; protecciones locales (falla, temperatura, PARAR, tensión baja, límites, horario); K1 NA con política de arranque; NVS cada minuto; búfer de 7 MB; NTP + DS3231; WiFi a 17 dBm; portal; consola; OTA; watchdog. Compila sin advertencias (1,06 MB de 4 MB).
- **`app/`:** servidor y app web. Probados en local con `tools/simulador`: registro, alta del equipo, búfer sin internet, panel en vivo, órdenes con confirmación, configuración empujada, límite de kWh, sobretemperatura, OTA, historial con costos y CSV.
- **Docs:** `docs/software/ARQUITECTURA.md`, `PROTOCOLO_MENSAJES.md`, `GUIA_INSTALACION.md`; README con la sección Software; `PROTOCOLO_PRUEBAS.md` con los comandos de cada etapa y la calibración de S7.
- Ajustes por seguridad de la placa: sin WiFi guardado, el firmware final no enciende la radio (sin U1, los picos tumbarían la fuente de 0,25 A); la falla del medidor se decide con CalErr/AdjErr y no con el nivel de WarnOut (el datasheet no dice la polaridad: se anota en S5-4).

## Qué se hizo (24 nov, F10: Firebase y diseño)

- **Servidor → Firebase (D31):** Authentication (usuarios y una cuenta por equipo), Realtime Database con reglas de seguridad por ruta y Hosting, en el plan Spark gratis. Sin Cloud Functions ni Storage (piden tarjeta): el firmware para OTA va en la base en partes de 32 KB y Telegram lo manda el propio equipo. Vercel se descartó (WebSocket en beta que se corta a los ~5 min y base aparte).
- **Firmware final:** cliente propio de Firebase (`src/fb.cpp`: inicio de sesión, REST con keep-alive y flujo SSE de `/entrada/{id}`), `red.cpp` reescrito, consola y portal con `enlazar CÓDIGO`, raíces TLS de Google y GoDaddy (Telegram), OTA por partes que no se reintenta si una versión no arrancó. Compila sin advertencias (1,08 MB).
- **Firmware de pruebas:** S5-4 imprime la polaridad de WarnOut e IRQ en dos líneas listas para copiar al protocolo.
- **App nueva (D32):** tablero eléctrico futurista elegido por el usuario: mímico del circuito, medidor de aguja, selector K1 que espera la confirmación del equipo, anunciador, rodillos de energía; día y noche; celular y computador.
- **Pruebas:** reglas 64/64 en el emulador; app + simulador contra el emulador (órdenes con confirmación en ≈ 0,4 s, configuración, límites, sobretemperatura, reconocer, historial, bitácora, OTA de 244 KB en 8 partes). Lo único sin probar es la conexión real de la placa a Firebase.

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
SOFTWARE (Fase 10) · ► ESTÁS AQUÍ: integración con la placa (10H)

[Placa: sensores · ATM90E26 · K1] ─► [ESP32-S3: firmware ✓] ═TLS saliente═► [Firebase: Auth + Realtime DB + reglas ✓] ─► [App web ✓] ─► usuario
          ▲ ▐S1–S8 en la placa▌            │ protecciones locales ✓                  ▲   ▐publicar (guía B)▌          │
          └────────────────────────────────┴─ NVS + búfer 7 MB + DS3231 ✓            └────── órdenes ◄───────────────┘
```

## Tareas pendientes de la Fase 9 (hardware)

- [x] Pedido a JLCPCB y recepción de las 2 placas ensambladas (20 nov).
- [x] H1, H2 y H3 en la placa 1 (20 nov).
- [x] H0 con lupa (24 nov). Faltan las fotos de las dos caras en `docs/pruebas/fotos/`.
- [x] H5: USB y `esptool` (24 nov): COM8, ESP32-S3 rev v0.2, 16 MB + PSRAM de 2 MB, MAC 10:bd:a3:65:01:08.
- [x] Soldar U1 (R-78CK) (24 nov).
- [x] H4: sin energía y encendido escalonado 3 → 6 → 12 V (24 nov).
- [ ] H6: pila, CT y sonda antes de conectarlos.
- [ ] SW2/SW3 con el KFC-A04-02 (comprados, 4) y el SW730RD cableado a J7.
- [ ] Cerrar la Rev 1.0: etiqueta `rev1.0` en git y notas para la Rev 1.1 (gabinete incluido).

## Tareas de la Fase 10 (software)

- [x] 10A · Arquitectura (D21–D32; Firebase desde el 24 nov). **Falta tu decisión de D28** (arranque de K1).
- [x] 10B · Firmware de pruebas (`firmware/prueba_placa`).
- [x] 10C · Protocolo de mensajes.
- [x] 10D · Firmware final (`firmware/evse_monitor`).
- [x] 10E · Simulador del equipo.
- [x] 10F · Servidor y base de datos.
- [x] 10G · Aplicación web.
- [ ] 10H · Integración con la placa:
  - [ ] Publicar la app en Firebase (guía, parte B): proyecto, Authentication con correo, Realtime Database en us-central1, app web con Hosting, `npx firebase login`, `npx firebase use --add`, `npm run desplegar`; crear tu cuenta, ponerte en `admins` y crear el equipo `evse-01`.
  - [ ] Opcional: dominio `evse.nicolasgomez.dev` (Hosting → dominio personalizado) y bot de Telegram (Ajustes → Avisos por Telegram).
  - [ ] S1–S5 con `firmware/prueba_placa` (12 V en J6; U1 ya está). Anotar la polaridad de WarnOut e IRQ (S5-4, guía A3).
  - [x] U1 + H4 (24 nov). [ ] S6 (`s6 scan`, `s6 con`, `s6 carga`).
  - [ ] Borrar la flash y subir `firmware/evse_monitor`; `wifi` + `enlazar CÓDIGO` (o el portal); LED3 fijo y «En línea» en la app.
  - [ ] S7: calibración con `cal_auto` y verificación con otra carga (error < 1–2 %).
  - [ ] S8: Detener/Permitir desde la app y medir J2 (17–18); protecciones sin internet; historial completo al volver la red.
  - [ ] Probar una OTA real (1.0.0 → 1.0.1).
  - [ ] Al cerrar la fase: agregar el bloque de software al artifact de referencia (CLAUDE.md, paso 5).
- [x] 10I · Documentación.

## Ten a mano

- La placa 1, la fuente de banco de dos canales, el Keysight 34461A, el cable USB-C de datos, cables dupont para J8 y caimanes.
- La sonda DS18B20, la pila CR2032, el CT, U1 y el cautín.
- Para S7: transformador de aislamiento, regleta con interruptor, carga resistiva de 1–1,5 kW y pinza amperimétrica.
- El nombre y la clave del WiFi (no van en el repo) y tu cuenta de Google para Firebase.

## Pendientes fuera de esta fase

- Gabinete: lo decide la Rev 1.1 de la PCB.
