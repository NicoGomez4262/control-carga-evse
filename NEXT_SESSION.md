# Siguiente sesión → Fase 10 (continuación): software en la placa real

El software de la Fase 10 ya está escrito y probado sin la placa (23 nov). Falta **10H**: publicar la app, correr S1–S8 con el firmware en la PCB, calibrar el ATM90E26 y la prueba de punta a punta. La Fase 9 sigue abierta solo por U1 (R-78CK), H0 con lupa, H5 y la etiqueta Rev 1.0.

## Prompt para iniciar

```text
Seguimos con el proyecto "Control de carga EVSE" (repo público github.com/NicoGomez4262/control-carga-evse).
La Fase 10 (software) ya tiene el código: firmware/prueba_placa (S1–S6), firmware/evse_monitor (final),
app/ (Cloudflare Workers + Durable Objects + D1, app web) y tools/simulador. Falta la tarea 10H: llevarlo
a la placa real.

Antes de nada, lee:
- CLAUDE.md (reglas: español, tú; diagramas como gráfico; commits sin coautor; subir a GitHub al final con
  docs/tools/sincronizar_altium.py --commit).
- NEXT_SESSION.md (este archivo) y docs/PLAN_FASES.md (Fases 9 y 10).
- docs/software/GUIA_INSTALACION.md (cómo subir cada firmware, qué comando corre cada etapa y cómo publicar
  la app), docs/software/ARQUITECTURA.md y docs/software/PROTOCOLO_MENSAJES.md.
- docs/pruebas/PROTOCOLO_PRUEBAS.md y docs/pruebas/mapa_puntos.png.
- docs/DECISIONES.md: D20–D30 y la sección «Fase 10».

Estado de la placa 1: H1–H3 bien. [Di aquí si ya soldaste U1 y qué pruebas S corriste.]
[Di si ya creaste la cuenta de Cloudflare y publicaste la app (guía, parte B), y la dirección.]
[Di qué política de arranque de K1 eliges (D28): restaurar, detenida o permitida.]

Qué quiero en esta sesión, en este orden:
1. Diagrama «ESTÁS AQUÍ» como gráfico y la lista de tareas que falta.
2. Acompañarme en la placa: S1–S5 con el firmware de pruebas (sin U1: 3,30 V en TP3), después U1 + H4,
   S6 (WiFi) y el firmware final conectado a la app. En cada prueba, qué conectar (puntos del mapa y pin de
   Altium), el ajuste de la fuente y del Keysight 34461A, y qué debe salir. Anotar los resultados en el
   protocolo.
3. Corregir en el firmware o la app lo que salga mal en la placa (registrar cada cambio).
4. S7 con el transformador de aislamiento: calibración (cal_auto) y verificación con otra carga.
5. S8: prueba de punta a punta (orden en la app → K1 → J2 medido) y protecciones sin internet.
6. Cerrar la Fase 10 (y la 9 si U1 y H0–H5 quedaron) según CLAUDE.md, y subir todo a GitHub.
```

## Qué se hizo (23 nov, F10)

- **Arquitectura (D21–D30):** firmware Arduino-ESP32 2.0.17 en PlatformIO con dos tareas (control y red); WebSocket seguro saliente con el certificado verificado; Cloudflare Workers + un Durable Object por equipo + D1 + KV en el plan gratis (US$ 0/mes); app web sin framework; usuarios con clave derivada en el navegador y token propio por equipo; portal cautivo y consola para el WiFi; OTA desde la app con vuelta atrás; Telegram para las alarmas. El usuario pidió que Claude se encargara de todo, así que las decisiones quedaron tomadas y documentadas con sus alternativas; D28 (arranque de K1) es configurable y la decide el usuario.
- **`firmware/prueba_placa`:** menú por consola para H5 y S1–S6 (más ayudas para S5 con generador y S7). Compila (778 KB).
- **`firmware/evse_monitor`:** ATM90E26 con LNSel = 0, CS1/CS2 y arranque verificado; AHT20, DS3231 y DS18B20 sin bloquear; energía por integración de P; sesiones; protecciones locales (falla, temperatura, PARAR, tensión baja, límites, horario); K1 NA con política de arranque; NVS cada minuto; búfer de 7 MB; NTP + DS3231; WiFi a 17 dBm; portal; consola; OTA; watchdog. Compila sin advertencias (1,06 MB de 4 MB).
- **`app/`:** servidor y app web. Probados en local con `tools/simulador`: registro, alta del equipo, búfer sin internet, panel en vivo, órdenes con confirmación, configuración empujada, límite de kWh, sobretemperatura, OTA, historial con costos y CSV.
- **Docs:** `docs/software/ARQUITECTURA.md`, `PROTOCOLO_MENSAJES.md`, `GUIA_INSTALACION.md`; README con la sección Software; `PROTOCOLO_PRUEBAS.md` con los comandos de cada etapa y la calibración de S7.
- Ajustes por seguridad de la placa: sin WiFi guardado, el firmware final no enciende la radio (sin U1, los picos tumbarían la fuente de 0,25 A); la falla del medidor se decide con CalErr/AdjErr y no con el nivel de WarnOut (el datasheet no dice la polaridad: se anota en S5-4).

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

[Placa: sensores · ATM90E26 · K1] ─► [ESP32-S3: firmware ✓] ═wss saliente═► [Cloudflare: Worker + DO + D1 ✓] ─► [App web ✓] ─► usuario
          ▲ ▐S1–S8 en la placa▌            │ protecciones locales ✓              ▲   ▐publicar (guía B)▌        │
          └────────────────────────────────┴─ NVS + búfer 7 MB + DS3231 ✓        └────── órdenes ◄─────────────┘
```

## Tareas pendientes de la Fase 9 (hardware)

- [x] Pedido a JLCPCB y recepción de las 2 placas ensambladas (20 nov).
- [x] H1, H2 y H3 en la placa 1 (20 nov).
- [ ] H0 con lupa: puentes en U3, J5 y U4; fotos de las dos caras en `docs/pruebas/fotos/`.
- [ ] H5: USB y `esptool` (se puede hacer ya, con 3,3 V en TP3; el comando `info` del firmware de pruebas da la MAC).
- [ ] Soldar U1 (R-78CK) y hacer H4.
- [ ] Opcional: SW2/SW3 con el KFC-A04-02 de Sigma (comprar 3).
- [ ] Cerrar la Rev 1.0: etiqueta `rev1.0` en git y notas para la Rev 1.1 (gabinete incluido).

## Tareas de la Fase 10 (software)

- [x] 10A · Arquitectura (D21–D30). **Falta tu decisión de D28** (arranque de K1).
- [x] 10B · Firmware de pruebas (`firmware/prueba_placa`).
- [x] 10C · Protocolo de mensajes.
- [x] 10D · Firmware final (`firmware/evse_monitor`).
- [x] 10E · Simulador del equipo.
- [x] 10F · Servidor y base de datos.
- [x] 10G · Aplicación web.
- [ ] 10H · Integración con la placa:
  - [ ] Publicar la app en Cloudflare (guía, parte B): cuenta, `wrangler login`, D1, KV, migraciones, `CODIGO_INICIAL`, `deploy`; crear el administrador y el equipo `evse-01`.
  - [ ] Opcional: dominio `evse.nicolasgomez.dev` y bot de Telegram.
  - [ ] S1–S5 con `firmware/prueba_placa` (sin U1: 3,30 V en TP3; S4 con 12 V en J6). Anotar la polaridad de WarnOut e IRQ (S5-4).
  - [ ] U1 + H4; S6 (`s6 scan`, `s6 con`, `s6 carga`).
  - [ ] Borrar la flash y subir `firmware/evse_monitor`; conectarlo por consola o portal; LED3 fijo y «En línea» en la app.
  - [ ] S7: calibración con `cal_auto` y verificación con otra carga (error < 1–2 %).
  - [ ] S8: Detener/Permitir desde la app y medir J2 (17–18); protecciones sin internet; historial completo al volver la red.
  - [ ] Probar una OTA real (1.0.0 → 1.0.1).
  - [ ] Al cerrar la fase: agregar el bloque de software al artifact de referencia (CLAUDE.md, paso 5).
- [x] 10I · Documentación.

## Ten a mano

- La placa 1, la fuente de banco de dos canales, el Keysight 34461A, el cable USB-C de datos, cables dupont para J8 y caimanes.
- La sonda DS18B20, la pila CR2032, el CT, U1 y el cautín.
- Para S7: transformador de aislamiento, regleta con interruptor, carga resistiva de 1–1,5 kW y pinza amperimétrica.
- El nombre y la clave del WiFi (no van en el repo) y tu correo para la cuenta de Cloudflare.

## Pendientes fuera de esta fase

- Gabinete: lo decide la Rev 1.1 de la PCB.
