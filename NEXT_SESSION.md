# Siguiente sesión → Fase 10: software (firmware y aplicación web)

La Fase 9 sigue abierta solo por el hardware que falta (U1, WiFi, red y la etiqueta Rev 1.0). El software empieza ya: sin U1, la placa se alimenta con 3,3 V en TP3 y se pueden probar el USB, los sensores, el medidor y K1.

## Prompt para iniciar

```text
Seguimos con el proyecto "Control de carga EVSE" (repo público github.com/NicoGomez4262/control-carga-evse).
La PCB Rev 1.0 ya llegó ensamblada de JLCPCB y pasó las pruebas de hardware H1–H3; falta soldar U1 (el R-78CK).
Empezamos la FASE 10, SOFTWARE, que tiene dos partes: el firmware del ESP32-S3 y la aplicación web propia
desde la que se controla todo.

Antes de nada, lee:
- CLAUDE.md: reglas de trabajo (español, tú; una propuesta completa con comparaciones antes de construir;
  diagramas como gráfico; commits sin coautor; subir a GitHub al final con docs/tools/sincronizar_altium.py --commit).
- NEXT_SESSION.md y docs/PLAN_FASES.md (Fases 9 y 10).
- docs/software/CONTEXTO_SOFTWARE.md: lo que el firmware necesita saber de la placa (mapa de pines, buses,
  registros y escalas del ATM90E26, límites de energía, semántica de K1) y el borrador de requisitos de la app.
- docs/pruebas/PROTOCOLO_PRUEBAS.md y docs/pruebas/mapa_puntos.png: las etapas S1–S8 son las que valida el firmware.
- docs/DECISIONES.md: P2, P3, P5, D7, D8, D14, D15, D20, la sección «Fase 9» y el mapa de pines del ESP32-S3.

Estado de la placa 1:
- H1 (sin energía), H2 (12 V sin U1) y H3 (3,3 V en TP3, incluido el lado de red del AMC3330): todo bien.
- Sin U1, la placa se alimenta con 3,30 V (límite 0,25 A) en TP3 (+) y TP1 (−). Funcionan CH340C, ESP32,
  ATM90E26, AMC3330 y sensores. K1 necesita además 12 V en J6 (segundo canal, límite 0,05 A). El WiFi a plena
  potencia espera a U1. Con U1 soldado, NUNCA más 3,3 V en TP3: todo por J6.
- La red (S7) solo con transformador de aislamiento; nada se toca energizado.
- Tengo el CT, la sonda DS18B20 y la pila CR2032. Me faltan U1 y, opcionales, SW2/SW3 (KFC-A04-02 de Sigma).

Qué quiero de esta fase, en este orden:

1. Diagrama de la arquitectura del software como gráfico (placa → firmware → internet → servidor → app → usuario)
   con «ESTÁS AQUÍ», y la lista de tareas de F10.

2. Propuesta de arquitectura en UN SOLO mensaje, con 2–3 opciones comparadas en tabla por decisión (ventajas,
   desventajas, costo mensual, dificultad, qué tan bien cumple D8), una recomendación y un mini diagrama:
   a. firmware: Arduino-ESP32 en PlatformIO o ESP-IDF;
   b. transporte equipo ↔ servidor (salida TLS desde el ESP32, sin puertos abiertos): MQTT sobre TLS (broker
      administrado o propio), WebSocket seguro al backend o HTTPS;
   c. backend y base de datos (series de tiempo de V, I, P y T; sesiones; usuarios);
   d. frontend (framework y gráficas), hosting y dominio (por ejemplo un subdominio de nicolasgomez.dev).
      Prefiero opciones gratis o de muy bajo costo que pueda mantener solo;
   e. autenticación de usuarios y del equipo (credenciales propias por equipo);
   f. aprovisionamiento del WiFi del equipo y actualizaciones OTA;
   g. notificaciones de alarmas.
   Espera mi aprobación antes de escribir código de producción. Las cuentas en servicios externos las creo yo:
   tú me dices qué crear y dónde.

3. Firmware de pruebas (firmware/prueba_placa, PlatformIO): menú por el monitor serie (115200, UART0 por el
   CH340C), un comando por bloque, para correr S1, S2, S3, S5 y S4 del protocolo sin U1 y sin WiFi:
   LEDs y PARAR; escaneo I²C, AHT20, DS3231 (hora, OSF, salida de 1 Hz en IO18); DS18B20; K1; ATM90E26 por SPI
   (CalStart 6886H, MMode 9422H, escritura y LastData, CalErr/WarnOut/IRQ, SoftReset, Urms e Irms2).
   Dame los pasos para compilar, subir y usarlo, y qué anotar en el protocolo.

4. Protocolo de mensajes (docs/software/PROTOCOLO_MENSAJES.md): telemetría, eventos, órdenes con confirmación,
   estado, configuración, sesiones, alarmas, versión y OTA; formato, frecuencias, y qué se guarda sin internet
   y cómo se reenvía.

5. Firmware final (firmware/evse_monitor), por módulos, cada uno probado en la placa antes del siguiente:
   - drivers: ATM90E26 (escalas, calibración en NVS, LNSel = 0 porque el CT va en I2), AHT20, DS3231, DS18B20,
     K1, LEDs y PARAR;
   - máquina de estados de la carga (permitida; detenida por app, horario, PARAR, temperatura, falla o límite)
     con K1 normalmente abierto: RELAY_EN = 1 = carga permitida;
   - protecciones locales que funcionan sin internet: sobretemperatura (sonda y ambiente), PARAR, pérdida de
     red o sag, falla del medidor (WarnOut/CalErr) y watchdog;
   - energía de la sesión en NVS cada minuto y al empezar o terminar (D14); búfer sin internet en una partición
     de la flash de 16 MB; hora por NTP con respaldo del DS3231;
   - WiFi con TX ≤ 17 dBm (el R-78CK da 0,5 A), reconexión, TLS con verificación del certificado, OTA y
     registro de eventos;
   - arranque: propón la política para restaurar el estado de K1 desde NVS (con el AQY214EHAX, sin energía no
     carga) y la decido yo.

6. Simulador del equipo (tools/simulador): un script que habla el mismo protocolo, para desarrollar la app
   sin la placa.

7. Backend y base de datos: API, tiempo real y usuarios.

8. Aplicación web, en español y pensada primero para el celular:
   - panel en vivo: V, I, P, FP, frecuencia, energía de la sesión y total, temperaturas (sonda y ambiente),
     humedad, estado de K1 y por qué, RSSI, en línea o no, alarmas;
   - control: permitir o detener la carga con confirmación, horarios de carga, límites por sesión (kWh, tiempo,
     costo), umbral de temperatura (lo aplica el equipo) y reconocer alarmas;
   - historial: sesiones con kWh, duración y costo (tarifa en COP/kWh), gráficas y exportar a CSV;
   - configuración: tensión nominal 120/240 V, tarifa, zona horaria America/Bogota, calibración (con cuidado),
     versión de firmware y OTA;
   - usuarios y registro del equipo; si el equipo está fuera de línea, el último estado y desde cuándo.

9. Integración con la placa: S4–S8 del protocolo (S6 y S7 solo con U1 soldado), calibración del ATM90E26 con
   carga resistiva y pinza de referencia, y una prueba de punta a punta (orden en la app → K1 → J2 medido).

10. Documentación: docs/software/ARQUITECTURA.md, PROTOCOLO_MENSAJES.md, guía de instalación y uso, README
    actualizado y decisiones desde D21 en docs/DECISIONES.md.

Reglas:
- El repo es público: nada de contraseñas del WiFi, credenciales del broker o de la base de datos ni tokens en
  git. Usa secrets.h y .env en .gitignore, con secrets.example.h y .env.example.
- En cada prueba en la placa, dime exactamente qué conectar con los números del mapa de puntos y su pin de
  Altium (por ejemplo, 6 (J6-1)), el ajuste de la fuente y del multímetro (Keysight 34461A: DCV, ACV, Ω 2W,
  Diode) y qué debe salir.
- Las protecciones se deciden en la ESP32 y funcionan sin internet; la app solo ordena y muestra.
- Si la fase no alcanza en esta sesión, actualiza NEXT_SESSION.md con las casillas y lo que falta, y sube todo
  a GitHub.
```

## Qué se hizo (20 nov, F9)

- Llegaron las 2 placas de JLCPCB, ensambladas.
- Protocolo de pruebas por etapas en `docs/pruebas/PROTOCOLO_PRUEBAS.md`, con un mapa de 39 puntos numerados (`docs/pruebas/mapa_puntos.png`, de `docs/tools/mapa_puntos_f9.py`). Cada punto lleva su pin de Altium.
- Polaridades revisadas con fotos contra el PcbDoc. Orientación de U1 sacada del dibujo de RECOM: la cara con el punto (●) mira hacia J6 y el pin 1 va en el pad cuadrado.
- Placa 1: H1, H2 y H3 dentro de lo esperado, incluido el convertidor aislado del AMC3330.
- Contexto para el software en `docs/software/CONTEXTO_SOFTWARE.md` y Fase 10 agregada a `docs/PLAN_FASES.md`.

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
SOFTWARE (Fase 10) · ► ESTÁS AQUÍ: arquitectura y firmware de pruebas

[Placa: sensores · ATM90E26 · K1] ─► ▐ESP32-S3: firmware▌ ═TLS saliente═► [Servidor: backend + BD] ─► [App web] ─► usuario
                                          │ protecciones locales (sin internet)          ▲                     │
                                          └─ NVS + búfer en flash + DS3231               └──── órdenes ◄───────┘
```

## Tareas pendientes de la Fase 9 (hardware)

- [x] Pedido a JLCPCB y recepción de las 2 placas ensambladas (20 nov).
- [x] H1, H2 y H3 en la placa 1 (20 nov).
- [ ] H0 con lupa: puentes en U3, J5 y U4; fotos de las dos caras en `docs/pruebas/fotos/`.
- [ ] H5: USB y `esptool` (se puede hacer ya, con 3,3 V en TP3).
- [ ] Soldar U1 (R-78CK) y hacer H4.
- [ ] Opcional: SW2/SW3 con el KFC-A04-02 de Sigma (comprar 3).
- [ ] S1–S8 del protocolo (con el firmware de la Fase 10).
- [ ] Cerrar la Rev 1.0: etiqueta `rev1.0` en git y notas para la Rev 1.1 (gabinete incluido).

## Tareas de la Fase 10 (software)

- [ ] 10A · Arquitectura: framework del firmware, transporte, backend y base de datos, frontend y hosting, autenticación, aprovisionamiento del WiFi, OTA y notificaciones (D21+).
- [ ] 10B · Firmware de pruebas (`firmware/prueba_placa`): S1–S5 sin WiFi.
- [ ] 10C · Protocolo de mensajes (`docs/software/PROTOCOLO_MENSAJES.md`).
- [ ] 10D · Firmware final (`firmware/evse_monitor`).
- [ ] 10E · Simulador del equipo (`tools/simulador`).
- [ ] 10F · Backend y base de datos.
- [ ] 10G · Aplicación web.
- [ ] 10H · Integración con la placa: S4–S8, calibración y prueba de punta a punta.
- [ ] 10I · Documentación y README.

## Ten a mano

- La placa 1, la fuente de banco (dos canales si se puede: 3,3 V y 12 V), el Keysight 34461A, un cable USB-C de datos, cables dupont para J8 y caimanes.
- La sonda DS18B20, la pila CR2032 y el CT.
- El nombre y la contraseña del WiFi (no van en el repo) y acceso al DNS de nicolasgomez.dev, si la app va en un subdominio.
- Python con `esptool` y `pyserial`, y VS Code con PlatformIO.

## Pendientes fuera de esta fase

- Gabinete: lo decide la Rev 1.1 de la PCB.
