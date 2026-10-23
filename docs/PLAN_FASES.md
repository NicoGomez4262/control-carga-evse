# Plan por fases — Control de carga EVSE en Altium

**Objetivo final:** esquemático y PCB completos en Altium, archivos enviados a PCBWay (fabricación y ensamble de los SMD) y componentes comprados: todo lo posible ensamblado por PCBWay (turnkey), lo que falte en DigiKey (carrito ≤ US$50 que se suma al pedido del curso) y Sigma Electrónica solo como último recurso (D16).

**Regla de trabajo:** una fase = una hoja o tarea concreta de Altium. La fase se cierra cuando su lista está completa; entonces se escribe el `NEXT_SESSION.md` de la fase siguiente (ver `CLAUDE.md`).

**Mapa interactivo:** https://claude.ai/artifact/EcYNTEBgvaQKugkwZJAJ5y — en la figura 2 eliges una fase y se resaltan sus bloques.

## Resumen

| Fase | Hoja o archivo de Altium | Qué se diseña | Estado |
|---|---|---|---|
| F1 | proyecto + `01_TOP.SchDoc` | estructura del proyecto, plantilla, hoja jerárquica, interfaces entre bloques; respuestas a P1–P7 | cerrada (2026-10-07) |
| F2 | `02_ALIMENTACION.SchDoc` | entrada de red universal (100–264 VAC), protección, AC-DC, riel `+VIN` de 12 V, R-78CK3.3-0.5, filtro LC, `+3V3A`, entrada de banco | cerrada (2026-10-08); `HV_AC` corregido en F4; queda el footprint de F1B/F2B |
| F3 | `03_MEDICION.SchDoc` | sensado de tensión (divisor + AMC3330), entrada del CT (J3), ATM90E26 | cerrada (2026-10-09); pendientes resueltos al inicio de F4 (2026-10-12) |
| F4 | `04_MCU.SchDoc` | ESP32-S3, arranque, USB-C (J5) con puente USB-UART y programación automática (DTR/RTS), LEDs, mapa de pines | cerrada (2026-10-12) |
| F5 | `05_SENSORES.SchDoc` | sonda DS18B20 (J4), sensor de ambiente I²C, RTC con pila (sin FRAM, D14) | cerrada (2026-10-12) |
| F6 | `06_ACTUACION.SchDoc` | driver Q3, PhotoMOS K1 (NC, aislamiento reforzado), salida J2 a los bornes de habilitación del EVSE | cerrada (2026-10-12) |
| F7 | todas las hojas | compilación, footprints, clases de red, librería del proyecto, BOM con proveedores (PCBWay, DigiKey; Sigma último recurso) | cerrada (2026-10-19) |
| F8 | `EVSE_Monitor.PcbDoc` | contorno, stackup, reglas de aislamiento, ubicación, ruteo, DRC, archivos para PCBWay y carrito | cerrada (2026-10-22) |
| F9 | pedido y banco de pruebas | pedido a PCBWay (K1 incluido desde el 23 oct) y Sigma; recepción, soldadura a mano (U1) y primeras pruebas | pendiente |

Estados posibles: pendiente · en curso · cerrada.

## Mapa general

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

## Reglas comunes a todas las fases

- Cada componente nuevo se elige comparando 2 o 3 opciones (tabla con requisito, encapsulado, montaje, stock en Sigma y PCBWay, precio, pros y contras).
- Proveedores, en este orden (D16, 19 oct): PCBWay (ensamble turnkey: lo que tenga en stock) → DigiKey (lo que PCBWay no tenga; consignado a PCBWay o soldado a mano; carrito ≤ US$50) → Sigma Electrónica solo si no queda otra. Mouser ya no se usa.
- Cada componente sale de su fase con símbolo, footprint verificado contra el datasheet y parámetros completos (`Manufacturer`, `MPN`, `Supplier`, `Supplier PN`, `Assembly`).
- Cada hoja se cierra con: compilación sin errores, PDF de todo el proyecto en `docs/revisiones/PROYECTO_F<n>.pdf` y revisión de Claude.
- La lista de componentes de cada fase se separa en (a) piezas sin símbolo ni footprint, por prioridad para SamacSys (cuota diaria), y (b) piezas que se crean copiando otra de la librería con el mismo encapsulado.
- Las redes conectadas a la red eléctrica llevan la clase `HV_AC` desde el esquemático.

---

## Fase 1 — Proyecto Altium y hoja TOP

**Hoja:** `01_TOP.SchDoc` y creación del proyecto · **Estado:** cerrada (2026-10-07)

<!--DIAG:F1-->
```text
► ESTÁS AQUÍ: FASE 1 · 01_TOP.SchDoc — este diagrama completo ES la hoja TOP (un símbolo de hoja por cada F#)

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

**Objetivo.** Dejar el proyecto creado con su estructura jerárquica y cerrar las decisiones que cambian el esquemático.

**Tareas**

- [x] Responder P1–P7 y registrarlas en `docs/DECISIONES.md`:
  - [x] P1 · servicio 120/208 V o 120/240 V; ¿hay neutro y tierra en el punto de carga?
  - [x] P2 · EVSE: marca, modelo, corriente configurada; ¿entrada de habilitación, Modbus u OCPP?
  - [x] P3 · el relé corta la potencia (contactor), habilita el EVSE o ambas cosas
  - [x] P4 · dónde se instala (tablero con riel DIN, caja junto al EVSE, dentro del EVSE) y tipo de caja
  - [x] P5 · acceso remoto: solo red local o también desde internet (VPN)
  - [x] P6 · cálculo de potencia en la ESP con muestras (ADS131M02) o IC de medición (ATM90E26)
  - [x] P7 · ¿divisor resistivo obligatorio? (divisor + AMC3330) o ZMPT101B
- [x] Preferencia de riel de entrada: 12 V (recomendado con el R-78CK) o 5 V. La decisión final se toma en F2. → 12 V
- [x] Crear carpetas: `docs/revisiones/`, `docs/sesiones/`, `docs/datasheets/` (el proyecto de Altium quedó fuera del repositorio, D12).
- [x] Crear `Control de Carga IoT.PrjPcb` (D12) con las hojas `01_TOP` a `06_ACTUACION` y un `EVSE_Monitor.PcbDoc` vacío.
- [x] Plantilla de hoja con bloque de título (aplicada; los campos ProjectName/Revision/DrawnBy/Title muestran `*` porque las hojas traen esos parámetros como solo lectura → se arregla en F7) (Title, Revision, Date, DrawnBy, SheetNumber, SheetTotal) y parámetros del proyecto (`ProjectName`, `Revision = 0.1`).
- [x] Estrategia de librerías → SamacSys usada directamente + `EVSE.SchLib/PcbLib` para piezas propias (D10). Listar las piezas que necesitan símbolo o footprint propio (R-78CK, módulo AC-DC, AMC3330, ATM90E26, relé de J2, jack del CT, borneras).
- [x] Parámetros obligatorios de componente definidos en la plantilla o la librería.
- [x] Hoja TOP: un símbolo de hoja por bloque (ALIMENTACION, MEDICION, MCU, SENSORES, ACTUACION) con sus entradas de hoja y las conexiones de la tabla de interfaces (rieles con puertos de alimentación globales; señales y líneas de red con entradas de hoja).
- [x] Opciones del proyecto: Net Identifier Scope jerárquico (entradas de hoja ↔ puertos) y matriz ERC revisada.
- [x] Compilar sin errores (las hojas hijas solo tendrán puertos). → 0 errores; solo advertencias «Off grid» (se desactivan en Error Reporting).
- [x] Exportar `docs/revisiones/F1_TOP.pdf` y revisarlo con Claude. → conexiones y referencias cruzadas correctas; el PDF sale recortado a la derecha (se corrige al inicio de F2).
- [x] Cerrar la fase (ver `CLAUDE.md`).

**Interfaces entre hojas (Rev C, después de P1–P7)**

Rieles de alimentación: **puertos de alimentación globales** (no llevan entrada de hoja). La TOP lleva una nota con los rieles que usa cada hoja.

| Riel | Se genera en | Lo usan | Nota |
|---|---|---|---|
| `+VIN` | ALIMENTACION | ACTUACION | 12 V preferido (se confirma en F2); bobina del relé |
| `+3V3` | ALIMENTACION | MEDICION, MCU, SENSORES, ACTUACION | salida filtrada del R-78CK; también el lado SELV del AMC3330 |
| `+3V3A` | ALIMENTACION | MEDICION | AVDD del ATM90E26 (ferrita) |
| `GND` | — | todas las hojas SELV | tierra única del lado SELV |

Señales y líneas de red: **entradas de hoja ↔ puertos**.

| Red | De | A | Tipo de E/S | Nota |
|---|---|---|---|---|
| `AC_L1_F`, `AC_L2_F` | ALIMENTACION | MEDICION | Unspecified | red eléctrica (`HV_AC`), después de fusibles; en 120 V `AC_L2_F` es el neutro; alimenta el divisor del AMC3330 |
| `MEAS_SCK`, `MEAS_MOSI`, `MEAS_CS` | MCU | MEDICION | Output → Input | SPI del ATM90E26 |
| `MEAS_MISO` | MEDICION | MCU | Output → Input | SPI |
| `MEAS_IRQ`, `MEAS_WARN`, `MEAS_ZX` | MEDICION | MCU | Output → Input | interrupción, alarma, cruce por cero |
| `I2C_SDA`, `I2C_SCL` | MCU ↔ SENSORES | | Bidirectional | pull-ups en SENSORES |
| `OW_DATA` | MCU ↔ SENSORES | | Bidirectional | 1-Wire; pull-up en SENSORES |
| `RTC_INT` | SENSORES | MCU | Output → Input | opcional |
| `RELAY_EN` | MCU | ACTUACION | Output → Input | pull-down en ACTUACION: el relé arranca en reposo |

Cambios frente al borrador: `AC_L1_F/AC_L2_F` ya no van a ACTUACION (sin contactor, D7); `EVSE_EN` se elimina (una sola señal, `RELAY_EN`); `VBUS` queda local en MCU (con el riel de 12 V la placa no se alimenta por USB). Las redes locales de cada hoja (`AC_L1`, `AC_L2`, `USB_DP`, `USB_DN`, `VBUS`, J2) no salen a la TOP.

**Componentes a comparar:** ninguno; solo la estrategia de librerías.

**Termina cuando:** la TOP compila, la tabla de interfaces está congelada y P1–P7 tienen respuesta.

---

## Fase 2 — Alimentación

**Hoja:** `02_ALIMENTACION.SchDoc` · **Estado:** cerrada (2026-10-08), con pendientes al inicio de F3

<!--DIAG:F2-->
```text
► ESTÁS AQUÍ: FASE 2 · 02_ALIMENTACION.SchDoc — se diseñan los bloques ▐marcados▌

EXTERNO · instalación (fuera de la PCB)
  [Breaker del EVSE] ─┬─► [F3 CT en L1] ─► [EVSE] ─► [Vehículo]
                      │         │           ▲  │
                      └─► J1    └─► J3      │  └─ sonda DS18B20 ─► J4
                                            └─ J2 (bornes de habilitación)
════════════════════════════════════════════════════════════════════════════════════════════════════════════════
PCB        ZONA RED · 120–240 VAC                     ┃ BARRERA  ┃      ZONA SELV · 12 V y 3.3 V
                                                      ┃ ≥ 6.4 mm ┃
                                                      ┃          ┃
►ENERGÍA   J1 ─► ▐F2 Protección▌ ─┬───────────────────┨▐ AC-DC  ▌┠─► ▐F2 Riel 12 V▌ ─► ▐F2 R-78CK + LC▌ ─► 3V3
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
►BANCO                                                ┃          ┃ J6 ─► ▐F2 Entrada banco 12 V▌ ─► D2 ─► +VIN
════════════════════════════════════════════════════════════════════════════════════════════════════════════════
[F# bloque] fase en que se diseña · ▐bloque▌ se diseña en ESTA fase · ► carril con trabajo en esta fase
┃ ┃ barrera de aislamiento · ┨ ┠ componente que cruza la barrera (AC-DC, AMC3330, PhotoMOS K1)
│ L1/L2 (L/N en 120 V) con fusibles · J1–J6 conectores · J1 con cable largo a la línea · J2 contacto seco aislado
```
<!--/DIAG-->

**Objetivo.** Hoja de alimentación completa y verificada: de la bornera J1 a los rieles `+VIN`, `+3V3` y `+3V3A`.

**Tareas**

- [x] Arreglar la exportación a PDF recortada de F1 y desactivar el aviso «Off grid object». → causa: escala de Windows al 125 %; se corrige con `docs/tools/arreglar_pdf.py`; rejilla de 100 mil en las hojas 02–06.
- [x] Confirmar el riel de 12 V (preferencia de F1) con la comparación de fuentes. → 12 V
- [x] Entrada universal 100–264 VAC, 50/60 Hz (P1): 120 V L–N o 240 V L1–L2 en el mismo J1. → IRM-20-12 (85–305 VAC)
- [x] Comparar y elegir (2–3 opciones cada uno): todos elegidos (ver `docs/DECISIONES.md`, «Fase 2»).
  - [x] Módulo AC-DC → **IRM-20-12** (Sigma)
  - [x] Bornera J1 → ED1621 (Sigma), modelo CUI TB001-500-02BE
  - [x] Fusibles → dos Schurter UMT-H T1A SMD + portafusibles alternos Littelfuse 01000056Z (DNP)
  - [x] Varistor → TDK CU4032K300G2 (B72660M0301K072)
  - [x] Condensadores → C1 EEE-FK1V101P, C7 EEE-FK1C101P, cerámicos 0805/1206
  - [x] TVS → SMBJ15A
  - [x] Filtro LC → SRR4028-2R2Y; ferrita BLM21PG221SN1D; filtro EMI RECOM (RLS-126 + 10 µF + 1 nF)
  - [x] Entrada de banco J6 → bornera de 3.5 mm (modelo Phoenix 1751248) y diodos OR SS34-E3/57T
- [x] Dibujar la hoja. → dibujada el 2026-10-08; quedan correcciones de conexión de J6/`+VIN` (pendiente al inicio de F3).
- [x] Cálculos documentados (`docs/calculos/F2_ALIMENTACION.md`): potencia, fusible, varistor, filtro LC, R-78CK.
- [x] Verificar el R-78CK: entrada ≥ 5 V, 27 µF en la entrada, carga capacitiva ≤ 2000 µF.
- [ ] Clase de red `HV_AC` en `AC_L1`, `AC_L2`, `AC_L1_F`, `AC_L2_F`. → directivas puestas, pero con el nombre `HV-AC` (corregir a `HV_AC`)
- [x] Serigrafía de J1: «L1/L» y «L2/N». Documentar la protección del cable largo de J1 en el tablero: breaker de 2–6 A o portafusible exclusivo (P4). → nota puesta en la hoja (2026-10-08); la serigrafía se hace en F8
- [x] Footprints y parámetros completos. → parámetros en la librería y en la hoja; pads de J1 1.7 × 3.0 mm (2026-10-08). Pendiente: footprint propio de F1B/F2B (el 01000056Z es un solo clip)
- [x] Compilar, exportar y revisar. → compila; PDF del proyecto en `docs/revisiones/PROYECTO_F3.pdf`
- [x] Cerrar la fase. → cerrada el 2026-10-08 con pendientes trasladados al inicio de la sesión de F3 (pedido del usuario).

**Termina cuando:** la hoja compila, el AC-DC está elegido y el presupuesto de potencia cierra con margen.

---

## Fase 3 — Medición de tensión y corriente

**Hoja:** `03_MEDICION.SchDoc` · **Estado:** cerrada (2026-10-09), con pendientes en paralelo al inicio de F4

<!--DIAG:F3-->
```text
► ESTÁS AQUÍ: FASE 3 · 03_MEDICION.SchDoc — se diseñan los bloques ▐marcados▌

EXTERNO · instalación (fuera de la PCB)
  [Breaker del EVSE] ─┬─► ▐F3 CT en L1▌ ─► [EVSE] ─► [Vehículo]
                      │         │           ▲  │
                      └─► J1    └─► J3      │  └─ sonda DS18B20 ─► J4
                                            └─ J2 (bornes de habilitación)
════════════════════════════════════════════════════════════════════════════════════════════════════════════════
PCB        ZONA RED · 120–240 VAC                     ┃ BARRERA  ┃      ZONA SELV · 12 V y 3.3 V
                                                      ┃ ≥ 6.4 mm ┃
                                                      ┃          ┃
 ENERGÍA   J1 ─► [F2 Protección] ─┬───────────────────┨  AC-DC   ┠─► [F2 Riel 12 V] ─► [F2 R-78CK + LC] ─► 3V3
                                  │                   ┃   (F2)   ┃
►MEDICIÓN V                       └─► ▐F3 Divisor▌ ───┨▐ AMC3330▌┠─► V ─► ▐F3 ATM90E26▌ ═SPI═► ESP32-S3
                                                      ┃   (F3)   ┃              ▲ I
►MEDICIÓN I                                           ┃          ┃              └─◄ ▐F3 Carga CT▌ ◄─ J3
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

**Objetivo.** Cadena de medición completa: tensión por divisor resistivo y amplificador aislado AMC3330, corriente por el CT y digitalización en el IC de medición.

**Tareas**

- [x] P6 y P7 ya respondidas en F1: IC de medición (ATM90E26 como base) y divisor + AMC3330 (D9).
- [x] Comparar y elegir (ver `docs/DECISIONES.md`, «Fase 3»):
  - [x] Amplificador aislado → AMC3330 (frente a AMC1350 y ACPL-C87B)
  - [x] Resistencias del divisor → 4 × ERJ-P08F1004V (1 MΩ 1206 anti-surge)
  - [x] CT → SCT-013-000V (Sigma)
  - [x] Conector J3 → SJ1-3515-SMT (Sigma) + D4 SMAJ5.0CA
  - [x] IC de medición → ATM90E26-YU-R (frente a ADE7953)
  - [x] Cristal → ECS-81.92-12-30Q-EN-TR; precisión → Panasonic ERA-6A
- [x] Dibujar la hoja → completa el 2026-10-09 y anotada (U2, U3, J3, D4, Y1, R2–R18, C9–C31, LED2, TP5, TP6). Numeración real frente a los esquemas: `docs/DECISIONES.md`, «Fase 3».
- [x] Cálculos (`docs/calculos/F3_MEDICION.md`): divisor 1/401, señal a 120 V y 240 V, escala de I (0,5 V a 50 A), filtros (4,4–4,8 kHz), acople AC.
- [x] Verificar que ningún nodo SELV toque la red → solo U2 une redes de red y SELV; footprint del AMC3330 con 7,50 mm entre filas de pads (≥ 6,4 mm).
- [x] Clases de red: `HV_AC` y `ANALOG` con 3 Blankets en polígono y `HV-AC`→`HV_AC` en 02 → hecho por script al inicio de F4 (Blankets en el stream «Additional», 2026-10-12).
- [x] Anotar y exportar `docs/revisiones/PROYECTO_F3.pdf` (9 oct, 17:31) y revisar → revisado. Quedan para el inicio de F4: 5 condensadores de la librería sin pin 2, `+3V3`/`+3V3A` como puertos de alimentación, `HV_D1`–`HV_D3`, Update From Libraries (footprints 0603 → 0805 y parámetros) y parámetros de TP1–TP6.
- [x] Cerrar la fase → cerrada el 2026-10-09 con pendientes (pedido del usuario).

**Termina cuando:** las escalas de V e I están calculadas y documentadas, y la frontera red/SELV de la hoja es clara.

---

## Fase 4 — MCU ESP32-S3

**Hoja:** `04_MCU.SchDoc` · **Estado:** cerrada (2026-10-12)

<!--DIAG:F4-->
```text
► ESTÁS AQUÍ: FASE 4 · 04_MCU.SchDoc — se diseñan los bloques ▐marcados▌

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
►CONTROL                                              ┃          ┃   ▐F4 ESP32-S3▌ ─ WiFi ─► router ─► internet ─► app
►INTERFAZ                                             ┃          ┃ J5 ─► ▐F4 USB-C · USB-UART · auto-reset · LEDs▌ ─► ESP32-S3
 SENSORES                                             ┃          ┃ J4 ─► [F5 Sensores · RTC] ─► ESP32-S3
 BANCO                                                ┃          ┃ J6 ─► [F2 Entrada banco 12 V] ─► D2 ─► +VIN
════════════════════════════════════════════════════════════════════════════════════════════════════════════════
[F# bloque] fase en que se diseña · ▐bloque▌ se diseña en ESTA fase · ► carril con trabajo en esta fase
┃ ┃ barrera de aislamiento · ┨ ┠ componente que cruza la barrera (AC-DC, AMC3330, PhotoMOS K1)
│ L1/L2 (L/N en 120 V) con fusibles · J1–J6 conectores · J1 con cable largo a la línea · J2 contacto seco aislado
```
<!--/DIAG-->

**Objetivo.** ESP32-S3 operativo: alimentación, arranque, USB para programar y la interfaz local.

**Tareas**

- [x] Comparar y elegir (ver `docs/DECISIONES.md`, «Fase 4»):
  - [x] Módulo → **ESP32-S3-WROOM-1-N16R2** (85 °C; N8R2 sin stock en Mouser/DigiKey/Sigma; N16R8 solo 65 °C).
  - [x] Conector USB-C → **Würth 632723300011** (Content Vault de Altium; HRO, UJ20 y CH340G no traían footprint en SamacSys) + ESD **USBLC6-2SC6** + CC de 5,1 kΩ.
  - [x] Puente USB-UART → **CH340C** (creado desde el SN74HC595DR, mismo SOIC-16) y auto-reset del profesor con **2 × MMBT3904LT1G**, R19/R20 12 kΩ y R21 4,7 kΩ.
  - [x] Pulsadores TS-1187A-B-A-B (SW1 PARAR; SW2 RESET y SW3 BOOT DNP), J7 para botón de panel SW730RD, LEDs APT2012SGC/SURCK, J8 1×6; sin zumbador.
- [x] Dibujar la hoja → completa el 2026-10-12 (esquemas `docs/esquemas/F4_s1…s7`). Corregido por script: pulsadores (B1/C1), R21, `BTN_PARAR`, designadores y parámetros.
- [x] Mapa de pines definitivo en `docs/DECISIONES.md`.
- [x] Compilar y exportar `docs/revisiones/PROYECTO_F4.pdf` → revisado. Solo quedan los avisos de I2C, OW_DATA, RTC_INT y RELAY_EN, que se cierran en F5 y F6.
- [x] Cerrar la fase (2026-10-12).

**Termina cuando:** el mapa de pines está cerrado y todas las señales de la TOP llegan a un GPIO válido.

---

## Fase 5 — Sensores, RTC y memoria

**Hoja:** `05_SENSORES.SchDoc` · **Estado:** cerrada (2026-10-12)

<!--DIAG:F5-->
```text
► ESTÁS AQUÍ: FASE 5 · 05_SENSORES.SchDoc — se diseñan los bloques ▐marcados▌

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
►SENSORES                                             ┃          ┃ J4 ─► ▐F5 Sensores · RTC▌ ─► ESP32-S3
 BANCO                                                ┃          ┃ J6 ─► [F2 Entrada banco 12 V] ─► D2 ─► +VIN
════════════════════════════════════════════════════════════════════════════════════════════════════════════════
[F# bloque] fase en que se diseña · ▐bloque▌ se diseña en ESTA fase · ► carril con trabajo en esta fase
┃ ┃ barrera de aislamiento · ┨ ┠ componente que cruza la barrera (AC-DC, AMC3330, PhotoMOS K1)
│ L1/L2 (L/N en 120 V) con fusibles · J1–J6 conectores · J1 con cable largo a la línea · J2 contacto seco aislado
```
<!--/DIAG-->

**Objetivo.** Temperatura del EVSE y del ambiente y hora sin internet. La energía acumulada y el búfer sin internet van en la flash del ESP32 (D14).

**Tareas**

- [x] Comparar y elegir (ver `docs/DECISIONES.md`, «Fase 5»):
  - [x] Sensor de ambiente I²C → **AHT20** (0x38; SHT40 solo en Mouser, TMP117 sin humedad).
  - [x] RTC → **DS3231SN#** (0x68, TCXO) con portapila **BAT-HLD-001** y CR2032; `RTC_INT` con pull-up de 10 kΩ (drenador abierto). RV-3028-C7 sin stock; PCF85063A sin VBAT.
  - [x] Memoria → **sin FRAM** (D14): el búfer sin internet (P5) cabe meses en la flash de 16 MB; la energía se guarda en NVS cada minuto.
  - [x] J4 → bornera 3P de 3,5 mm de Sigma (modelo Phoenix 1751251), ESD **USBLC6-2SC6** (D6), R36 de 100 Ω en serie, R35 de 4,7 kΩ y **R37 de 68 Ω 1206** que limita un corto en el cable de la sonda.
- [x] Dibujar la hoja (esquemas `docs/esquemas/F5_s1…s4`). Corregido por script (`arreglos_hoja05.py`): R32/R33/R35 de 47 kΩ → 4,7 kΩ, R34 estaba en serie con VCC de U7, net labels de U7 14–16, designadores y parámetros.
- [x] Validate: solo queda `RELAY_EN` (F6). `docs/revisiones/PROYECTO_F5.pdf` revisado (esta vez Altium lo exportó sin recorte).
- [x] Cerrar la fase (2026-10-12).

**Termina cuando:** las direcciones I²C están verificadas y la sonda externa tiene protección.

---

## Fase 6 — Actuación

**Hoja:** `06_ACTUACION.SchDoc` · **Estado:** cerrada (2026-10-12). K1 pasó del relé Finder 34.51 al PhotoMOS AQY414EHAX (NC) porque el relé dorado no está en Mouser (ver `docs/DECISIONES.md`, «Fase 6»).

<!--DIAG:F6-->
```text
► ESTÁS AQUÍ: FASE 6 · 06_ACTUACION.SchDoc — PhotoMOS K1 y salida J2 a los bornes de habilitación del EVSE ▐marcados▌

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
►ACTUACIÓN J2 ◄── contacto seco (aislado) ────────────┨▐PhotoMOS▌┠◄─ LED ─ ▐F6 Driver K1▌ ◄─ GPIO ─ ESP32-S3
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

**Objetivo.** Mando seguro de la carga: un relé (o PhotoMOS) que une o separa los bornes de habilitación del EVSE (D7). No hay contactor.

**Tareas**

- [x] P3 (12 oct): EVSE genérico, tensión y corriente desconocidas (peor caso), **sin energía debe cargar → NC**.
- [x] Comparar y elegir: relé Finder 34.51 dorado (no está en Mouser; Phoenix 2961163 a US$22) → **PhotoMOS AQY414EHAX** (NC, 400 V, 120 mA, 5000 Vrms reforzado, US$3,42 en Mouser); Q3 **AO3400A** + R39 1 kΩ + R40 10 kΩ; LED6 **KT-0805Y** + R41 1 kΩ en serie con el LED de K1 desde `+VIN` (≈ 8,4 mA); J2 de 2 polos (ED1621 de Sigma); sin diodo (no hay bobina). NA disponible con AQY214EHAX en el mismo footprint.
- [x] Dibujar la hoja (esquemas `docs/esquemas/F6_s1…s3`); arreglos por script `arreglos_hoja06.py` (3 piezas sueltas borradas, designadores, parámetros de K1).
- [x] Aislamiento: footprint de K1 con 6,70 mm entre los pads del LED y los de la salida (≥ 6,4 mm). Clase `EVSE_EXT` con dos Blankets.
- [x] Validate y `docs/revisiones/PROYECTO_F6.pdf` (6 hojas + BOM) revisado.
- [x] Cerrar la fase (2026-10-12).

**Termina cuando:** K1 arranca sin corriente en el LED (salida NC cerrada, pull-down en el gate) y la separación entrada–salida está verificada.

---

## Fase 7 — Cierre del esquemático y BOM

**Hojas:** todas · **Estado:** cerrada (2026-10-19)

<!--DIAG:F7-->
```text
► ESTÁS AQUÍ: FASE 7 · todas las hojas — revisión completa y BOM (todo ▐marcado▌)

EXTERNO · instalación (fuera de la PCB)
  [Breaker del EVSE] ─┬─► ▐F3 CT en L1▌ ─► [EVSE] ─► [Vehículo]
                      │         │           ▲  │
                      └─► J1    └─► J3      │  └─ sonda DS18B20 ─► J4
                                            └─ J2 (bornes de habilitación)
════════════════════════════════════════════════════════════════════════════════════════════════════════════════
PCB        ZONA RED · 120–240 VAC                     ┃ BARRERA  ┃      ZONA SELV · 12 V y 3.3 V
                                                      ┃ ≥ 6.4 mm ┃
                                                      ┃          ┃
►ENERGÍA   J1 ─► ▐F2 Protección▌ ─┬───────────────────┨▐ AC-DC  ▌┠─► ▐F2 Riel 12 V▌ ─► ▐F2 R-78CK + LC▌ ─► 3V3
                                  │                   ┃   (F2)   ┃
►MEDICIÓN V                       └─► ▐F3 Divisor▌ ───┨▐ AMC3330▌┠─► V ─► ▐F3 ATM90E26▌ ═SPI═► ESP32-S3
                                                      ┃   (F3)   ┃              ▲ I
►MEDICIÓN I                                           ┃          ┃              └─◄ ▐F3 Carga CT▌ ◄─ J3
                                                      ┃          ┃
►ACTUACIÓN J2 ◄── contacto seco (aislado) ────────────┨▐PhotoMOS▌┠◄─ LED ─ ▐F6 Driver K1▌ ◄─ GPIO ─ ESP32-S3
                                                      ┃   (F6)   ┃
►CONTROL                                              ┃          ┃   ▐F4 ESP32-S3▌ ─ WiFi ─► router ─► internet ─► app
►INTERFAZ                                             ┃          ┃ J5 ─► ▐F4 USB-C · USB-UART · auto-reset · LEDs▌ ─► ESP32-S3
►SENSORES                                             ┃          ┃ J4 ─► ▐F5 Sensores · RTC▌ ─► ESP32-S3
►BANCO                                                ┃          ┃ J6 ─► ▐F2 Entrada banco 12 V▌ ─► D2 ─► +VIN
════════════════════════════════════════════════════════════════════════════════════════════════════════════════
[F# bloque] fase en que se diseña · ▐bloque▌ se diseña en ESTA fase · ► carril con trabajo en esta fase
┃ ┃ barrera de aislamiento · ┨ ┠ componente que cruza la barrera (AC-DC, AMC3330, PhotoMOS K1)
│ L1/L2 (L/N en 120 V) con fusibles · J1–J6 conectores · J1 con cable largo a la línea · J2 contacto seco aislado
```
<!--/DIAG-->

**Objetivo.** Esquemático congelado (Rev 1.0) con BOM lista para comprar.

**Tareas**

- [x] Compilar todo el proyecto: 0 errores y warnings revisados (Validate correcto el 19 oct, antes y después de la BOM).
- [x] Anotación final de designadores (sin huecos, 14 oct).
- [x] Revisión cruzada TOP ↔ hojas: nombres de red, puertos y entradas de hoja (14 oct).
- [x] Clases de red y directivas en el esquemático (`HV_AC`, `ANALOG`, `USB`, `EVSE_EXT`); directiva `HV_AC` de 03 en el borde de su Blanket (19 oct).
- [x] Footprints: cada uno verificado contra el datasheet (J5, C2, C3, K1, BT1, F1B/F2B; los sustitutos de la BOM usan el mismo footprint: XY301V, RL4032, LQH43NH, GRM, RT0805).
- [x] BOM con Designator, Qty, Manufacturer, MPN, Description, Footprint, Supplier, Supplier PN, Assembly y precio: `docs/BOM_F7.md`, generada por `docs/tools/bom_f7.py` (19 oct).
- [x] Stock verificado según D16 (19 oct, LCSC/DigiKey/Sigma): 128 piezas por placa; todo a PCBWay salvo K1 (DigiKey, a mano) y U1 (disponible, a mano); CT, sonda y pila en Sigma. `Supplier`/`Supplier PN`/`Assembly` puestos por script en la librería y las hojas (D17).
- [x] Revisión de diseño con lista: seguridad y aislamiento, potencia, arranque, ESD en conectores, puntos de prueba, valores (19 oct, sin cambios; ver `docs/DECISIONES.md`, «Fase 7»).
- [x] Bloque de título: Title por hoja, sin `*`, sin logo ni texto de Altium (14 oct).
- [x] Librería del proyecto en `lib/` y `.PrjPcb` apuntando a ella (14 oct).
- [x] Pendientes heredados de F6: nota de rieles de la TOP; piezas sin uso fuera de la librería; Blankets de 03 agrandadas (14 oct).
- [x] Exportar `docs/revisiones/PROYECTO_F7.pdf` (6 hojas + BOM) y `docs/revisiones/F7_BOM.csv`, y revisarlos (19 oct): el CSV coincide con la BOM en los 132 designadores; en el PDF, tres títulos se salían del bloque y la nota de la TOP quedaba cortada → arreglado por script (`presentacion_f7.py`), se verá en el PDF de F8.
- [x] Cerrar la fase (19 oct).

**Termina cuando:** el esquemático está congelado y cada línea de la BOM tiene proveedor y forma de montaje.

---

## Fase 8 — PCB, ruteo y fabricación en PCBWay

**Archivo:** `EVSE_Monitor.PcbDoc` y OutJob · **Estado:** cerrada (2026-10-22). El pedido, el montaje y las pruebas pasan a F9.

<!--DIAG:F8-->
```text
► ESTÁS AQUÍ: FASE 8 · EVSE_Monitor.PcbDoc — ubicación, ruteo y fabricación de toda la placa ▐marcada▌

EXTERNO · instalación (fuera de la PCB)
  [Breaker del EVSE] ─┬─► [F3 CT en L1] ─► [EVSE] ─► [Vehículo]
                      │         │           ▲  │
                      └─► J1    └─► J3      │  └─ sonda DS18B20 ─► J4
                                            └─ J2 (bornes de habilitación)
════════════════════════════════════════════════════════════════════════════════════════════════════════════════
PCB        ZONA RED · 120–240 VAC                     ┃ BARRERA  ┃      ZONA SELV · 12 V y 3.3 V
                                                      ┃ ≥ 6.4 mm ┃
                                                      ┃          ┃
►ENERGÍA   J1 ─► ▐F2 Protección▌ ─┬───────────────────┨▐ AC-DC  ▌┠─► ▐F2 Riel 12 V▌ ─► ▐F2 R-78CK + LC▌ ─► 3V3
                                  │                   ┃   (F2)   ┃
►MEDICIÓN V                       └─► ▐F3 Divisor▌ ───┨▐ AMC3330▌┠─► V ─► ▐F3 ATM90E26▌ ═SPI═► ESP32-S3
                                                      ┃   (F3)   ┃              ▲ I
►MEDICIÓN I                                           ┃          ┃              └─◄ ▐F3 Carga CT▌ ◄─ J3
                                                      ┃          ┃
►ACTUACIÓN J2 ◄── contacto seco (aislado) ────────────┨▐PhotoMOS▌┠◄─ LED ─ ▐F6 Driver K1▌ ◄─ GPIO ─ ESP32-S3
                                                      ┃   (F6)   ┃
►CONTROL                                              ┃          ┃   ▐F4 ESP32-S3▌ ─ WiFi ─► router ─► internet ─► app
►INTERFAZ                                             ┃          ┃ J5 ─► ▐F4 USB-C · USB-UART · auto-reset · LEDs▌ ─► ESP32-S3
►SENSORES                                             ┃          ┃ J4 ─► ▐F5 Sensores · RTC▌ ─► ESP32-S3
►BANCO                                                ┃          ┃ J6 ─► ▐F2 Entrada banco 12 V▌ ─► D2 ─► +VIN
════════════════════════════════════════════════════════════════════════════════════════════════════════════════
[F# bloque] fase en que se diseña · ▐bloque▌ se diseña en ESTA fase · ► carril con trabajo en esta fase
┃ ┃ barrera de aislamiento · ┨ ┠ componente que cruza la barrera (AC-DC, AMC3330, PhotoMOS K1)
│ L1/L2 (L/N en 120 V) con fusibles · J1–J6 conectores · J1 con cable largo a la línea · J2 contacto seco aislado
```
<!--/DIAG-->

**Objetivo.** Placa ruteada, verificada y pedida; componentes comprados.

**Guía de ruteo (pedido del usuario, 19 oct):** antes de ubicar, Claude explica en general cómo van distribuidos los componentes (zona de red, barrera, SELV, antena, conectores), los planos de tierra, las distancias entre piezas y entre zonas, los anchos de pista por corriente, los mínimos y máximos de fabricación de PCBWay (pista, espacio, taladro, anillo, ranuras) y las reglas de Altium que se configuran, con pasos ubicados en Altium. Si F8 no alcanza, el ruteo sigue en una F9. **Hecha el 19 oct: `docs/GUIA_RUTEO_F8.md`.**

**8A · Preparación**

- [x] Contorno libre (esta versión es PCB desnuda; el gabinete queda para la próxima versión de la PCB y no es tarea), agujeros de montaje M3 en las esquinas, conectores J1–J8 al borde. *Contorno de 130 × 100 mm por script (`reglas_f8.py`, D18), también en Mechanical 1 para los Gerber (`salidas_f8.py`); 4 agujeros M3 sin metalizar en las esquinas; J1–J8 en los bordes.*
- [x] Stackup: **2 capas, 1,6 mm, 1 oz, HASL sin plomo, 130 × 100 mm** (D18, US$ 36,87 las 5 placas). Núcleo de 1,51 mm y εr 4,4 puestos en el Layer Stack Manager (20 oct).
- [x] Reglas: clearance `HV_AC` ↔ resto ≥ 5.5 mm; regla Creepage Distance de Altium ≥ 6.4 mm entre red y SELV; L1 ↔ L2 ≥ 3.2 mm; anchos por clase; par USB de 90 Ω; mínimos de fabricación de PCBWay (traza, espacio, taladro, anillo). *Hecho (20 oct): 66 reglas por script (`reglas_f8.py`), incluidas Minimum Annular Ring y Creepage Distance (sus códigos se leyeron de las que el usuario creó a mano); excepciones de J5 (patrón de Würth: anillo 0,125 mm). Par diferencial `USB_D` creado.*
- [x] Zonas: exclusión de cobre bajo la antena del ESP32 en todas las capas, zona de red sin planos internos, ranura de aislamiento en la capa de contorno si hace falta. *La antena sobresale del borde (sin cobre debajo); keepouts en la barrera y en el hueco red–isla; sin planos en la red; la ranura no hizo falta (6,4 mm de superficie libre).*

**8B · Ubicación**

- [x] Zona de red en un lado con frontera recta; solo el AC-DC, el AMC3330 y el relé de J2 la cruzan.
- [x] Todos los SMD en la cara superior (un solo lado de ensamble en PCBWay). Los THT que suelda PCBWay (PS1, J1, J2, J4, J6, J7, J8) con espacio para su soldadura; lo que va a mano (U1 R-78CK, K1 y, si algún día, F1B/F2B) agrupado y con espacio para el cautín (D17).
- [x] ESP32-S3 en el borde con la antena hacia afuera.
- [x] ATM90E26 y su cadena analógica lejos del relé y del AC-DC; cristal pegado al chip.
- [x] Desacoples junto a cada pin de alimentación; sensor de ambiente lejos de fuentes de calor.
- [x] 3 fiduciales, marcas de polaridad y de pin 1.

**8C · Ruteo**

- [x] Primero la red: pistas de 1 mm o más, sin vías innecesarias, respetando distancias.
- [x] Potencia SELV: `+VIN` y `+3V3` con el ancho adecuado; lazo corto del R-78CK y su filtro.
- [x] Analógico: entradas de V e I en pares simétricos y cortos; AGND unido bajo el ATM90E26.
- [x] USB como par diferencial de 90 Ω; SPI corto; pull-ups de I²C cerca del maestro.
- [x] Plano de GND continuo con vías de costura; sin cobre bajo la antena.
- [x] Serigrafía: designadores legibles, «PELIGRO 240 VAC», contorno de la zona de red, polaridades, nombre y versión.

**8D · Verificación**

- [x] DRC sin violaciones, incluida la regla de creepage. *0 eléctricas (22 oct); quedan 31 avisos de serigrafía: designadores y dibujos de las piezas que sobresalen del borde.*
- [x] Revisión 3D: choques entre piezas y acceso del cautín a lo que se suelda a mano. *Regla de 2 mm alrededor de K1; vías tapadas vistas en 3D.*
- [x] Revisión contra las capacidades de PCBWay. *`revisar_gerber_f8.py`: 304 taladros, máscara, pasta y cobre comparados contra el PcbDoc.*

**8E · Salidas y pedido**

- [x] OutJob: Gerber (X2 o RS-274X), taladros NC, Pick and Place en mm, BOM de ensamble en formato PCBWay, PDF de ensamble y STEP.
- [x] **Carrito de compras (pedido del usuario, F6):** una sola lista con todo lo que hay que pagar, agrupada por proveedor: PCBWay (PCB, ensamble y componentes turnkey), DigiKey y, si hiciera falta, Sigma. Cada línea lleva designadores, número de parte, cantidad, precio unitario, subtotal y enlace. Al final van los subtotales por proveedor, el envío y los impuestos estimados (DigiKey y PCBWay a Colombia) y el **total en COP y USD** con la tasa del día. Se entrega como página interactiva (artifact), con casillas para marcar lo comprado.
- [ ] → F9 · Pedido a PCBWay: FR-4 de 1.6 mm, cobre de 1 oz, HASL sin plomo o ENIG, 5 PCB y **1 ensamblada** (D17); turnkey de todo lo que tiene PCBWay (SMD y THT, `Assembly = PCBWay`); K1 y U1 (`Manual`) y F1B/F2B, SW2, SW3 (`DNP`) sin ensamblar. La BOM de ensamble sale de `docs/BOM_F7.md` / parámetros de Altium.
- [x] **Carrito de DigiKey (pedido del usuario, 19 oct):** lista lista para pasar al carrito común del curso (número de parte DigiKey, cantidad, precio unitario, subtotal), idealmente **≤ US$50**; si se pasa, proponer reemplazos que PCBWay sí ensamble. Según la BOM de F7 solo lleva K1 (AQY414EHAX, 255-6089-1-ND, US$ 3,29) y los repuestos que se quieran (por ejemplo, otro K1, dos fusibles 3403.0274.23).
- [ ] → F9 · Compra en Sigma solo de lo que no se consiguió en PCBWay ni en DigiKey: CT SCT-013-000V, sonda DS18B20 2 m y pila CR2032 (≈ 50.813 COP, F7).
- [ ] → F9 · Plan de montaje y primeras pruebas: primero con la entrada de banco de 12 V, sin red; después con red a través de un transformador de aislamiento.
- [ ] → F9 · Cerrar el proyecto de Altium (Rev 1.0 enviada).

**Termina cuando:** el pedido está hecho en PCBWay y los componentes manuales están comprados. *(22 oct: F8 se cierra con los archivos verificados y el carrito listo; el pedido, la compra y las pruebas pasan a F9.)*

**Cierre (22 oct).** Paquete en `docs/fabricacion/` (Gerber, BOM y Pick & Place para PCBWay, notas del pedido, plano de ensamble). Carrito: https://claude.ai/artifact/Vf8NPamJJd74KN2qhytMVX (US$ 209,38 ≈ 668.235 COP con la TRM del 22 oct). Explicación del diseño: `docs/EXPLICACION_PCB_F8.md`.

## Fase 9 — Pedido, montaje y primeras pruebas

**Estado:** en preparación. Lista de tareas en `NEXT_SESSION.md`.

**22 oct:** pedido preparado con la clase (`docs/fabricacion/GUIA_PEDIDO.md`). Los formularios de PCBWay están revisados campo por campo. TP1–TP6 pasan a ronghe RH-5016 (el Keystone 5016 quedó en 0 en LCSC). DigiKey lleva K1 y repuestos por US$ 17,87, dentro del cupo de US$ 40. Carrito: US$ 220,02 ≈ 702.192 COP.

**23 oct:** sin pedido de DigiKey (nadie más del curso pidió). K1 (AQY414EHAX) lo compra PCBWay en DigiKey o Mouser y lo suelda; F1/F2 llevan 2 fusibles 3403.0274.11 de repuesto sueltos. BOM, Pick & Place, notas del pedido, carrito y parámetros de Altium actualizados (D19 en `docs/DECISIONES.md`).
