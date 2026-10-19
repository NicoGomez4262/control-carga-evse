# Siguiente sesión → Fase 4: MCU ESP32-S3 (`04_MCU.SchDoc`) + pendientes de F3 en paralelo

**Estado (9 oct 2026, 17:45):** Fase 3 cerrada con pendientes. Por pedido del usuario, esos pendientes se corrigen en paralelo al inicio de F4 (sección A). La hoja `03_MEDICION` está completa, anotada y revisada en `docs/revisiones/PROYECTO_F3.pdf`; la numeración real y sus equivalencias con los esquemas están en `docs/DECISIONES.md`, «Fase 3».

## Prompt para iniciar

Cierra Altium antes de pegar esto en una sesión nueva de Claude abierta en la carpeta del repositorio:

```text
Iniciamos la FASE 4 del proyecto "Control de carga EVSE" en Altium: hoja 04_MCU.SchDoc. Ya cerré Altium.

Lee CLAUDE.md, NEXT_SESSION.md, docs/PLAN_FASES.md (Fase 4) y docs/DECISIONES.md (D8, D13, P5, «Fase 3» y «Mapa de pines del ESP32-S3»), y mira la imagen docs/referencias/F4_autoprogramacion_profesor.jpg.

Trabajamos en paralelo:
A. Pendientes de F3 (sección A de NEXT_SESSION.md). Primero, con Altium cerrado, ejecuta docs/tools/reparar_pin2_condensadores.py sobre la librería SamacSys y verifica el resultado. Después guíame con el resto, paso a paso y con esquemas, y verifica cada punto leyendo los .SchDoc con docs/tools/lista_redes.py y docs/tools/cobertura_blanket.py.
B. Fase 4, con el ritmo de CLAUDE.md:
  1. Muéstrame el diagrama «ESTÁS AQUÍ» y la lista de tareas.
  2. En un solo mensaje, todos los componentes de F4 con sus comparaciones (datasheet; Sigma y PCBWay primero, Mouser solo si no hay; 0805 o más grande) y un mini diagrama de la hoja. Separa la lista en: (a) piezas que no tengo en la librería (sin símbolo ni footprint), ordenadas por prioridad para bajarlas de SamacSys, porque la cuota diaria es limitada y no quiero gastarla en piezas menores y quedarme esperando las importantes; y (b) piezas que puedo crear copiando una que ya está en SamacSys.SchLib/PcbLib con el mismo encapsulado, cambiando solo los parámetros.
  3. Incluye lo que pidió el profesor: «Circuito de programación de la ESP-32 para que se resetee solo y no con un switch físico. Con comunicación USB serial con DTR y RTS.» Es el circuito de la imagen: DTR → R1 12 kΩ → base de Q2 (emisor a RTS, colector a RESET/EN) y RTS → R2 12 kΩ → base de Q1 (emisor a DTR, colector a GPIO0, con R3 4,7 kΩ a 3,3 V). Compara el puente USB-UART con DTR/RTS y los transistores.
  4. Cuando lo apruebe, guíame con los esquemas literales por bloque, revisa la hoja y, al final, el PDF de todo el proyecto (docs/revisiones/PROYECTO_F4.pdf).
```

## Dónde estamos

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
 ACTUACIÓN J2 ◄── contacto seco (aislado) ────────────┨   Relé   ┠◄─ bobina ─ [F6 Driver relé] ◄─ GPIO ─ ESP32-S3
                                                      ┃   (F6)   ┃
►CONTROL                                              ┃          ┃   ▐F4 ESP32-S3▌ ─ WiFi ─► router ─► internet ─► app
►INTERFAZ                                             ┃          ┃ J5 ─► ▐F4 USB-C · USB-UART · auto-reset · LEDs▌ ─► ESP32-S3
 SENSORES                                             ┃          ┃ J4 ─► [F5 Sensores · RTC · FRAM] ─► ESP32-S3
 BANCO                                                ┃          ┃ J6 ─► [F2 Entrada banco 12 V] ─► D2 ─► +VIN
════════════════════════════════════════════════════════════════════════════════════════════════════════════════
[F# bloque] fase en que se diseña · ▐bloque▌ se diseña en ESTA fase · ► carril con trabajo en esta fase
┃ ┃ barrera de aislamiento · ┨ ┠ componente que cruza la barrera (AC-DC, AMC3330, relé)
│ L1/L2 (L/N en 120 V) con fusibles · J1–J6 conectores · J1 con cable largo a la línea · J2 contacto seco aislado
```
<!--/DIAG-->

## A. Pendientes de F3 (en paralelo, al inicio de la sesión)

Revisión del 9 oct (17:23 la hoja, 16:43 la librería). Ya está bien: hoja completa y anotada; J3 con tip y sleeve y *No ERC* en 3, 10 y 11; C29, R6, R8, R15 y R17 corregidos; TP5, `CT_P` y `CT_N` puestos; designadores U2, U3, J3 y TP5/TP6; parámetros de la librería llenos; solo U2 une redes de red y SELV.

**Avance del 11 oct (sesión F4):** A1, A2, A4, A5, A6, A7 y A8 hechos por script con Altium cerrado (copias en `docs/respaldos/`; redes de 02 y 03 idénticas antes y después; cobertura de Blankets verificada). Quedan A3 y A9 en Altium. Herramientas nuevas: `altium_ole.py`, `libreria.py`, `hoja.py`, `pendientes_f3.py`, `corregir_libreria_f4.py`, `render_hoja.py`.

- [x] **A1. Reparar 5 condensadores de la librería (lo primero, con Altium cerrado).** → hecho el 11 oct; los 5 tienen pin 1 a la izquierda y pin 2 a la derecha. Al borrar los pines repetidos se borraron los dos «2»: `C0805C102J5GAC-TU`, `C0805C120J5GACTU`, `C0805C472J5GACTU`, `CL21B104KBCNNNC` y `CL21B105KAFNNNE` quedaron con dos pines «1» y sin pin «2». Claude ejecuta `python docs/tools/reparar_pin2_condensadores.py "C:/Users/nico/Documents/AltiumLL/SamacSys.SchLib"` (probado el 9 oct en una copia; guarda `SamacSys_antes_reparar.SchLib`). Luego: abrir Altium → `SamacSys.SchLib` → panel **SCH Library** → cada uno de los 5 debe tener el pin 1 a la izquierda y el 2 a la derecha. **No ejecutar Update From Libraries antes de esto.**
- [x] **A2.** `ATM90E26-YU-R` → `Manufacturer_Name` = `Microchip` → hecho por script (`corregir_libreria_f4.py`), junto con la limpieza de Datasheet Link, Mouser y Arrow copiados mal en 13 piezas.
- [ ] **A3. Update From Libraries** en `02_ALIMENTACION` y en `03_MEDICION` (**Tools → Update From Libraries**, todos los tipos; KEYSTONE-5016 no aparece en la lista y es normal). Arregla: C9, C11 y C17 de la hoja 03, que hoy no tienen pin 2 (su lado `AC_L2_F` está **abierto**); los parámetros viejos de la hoja; el footprint **0603** (RESC1608X55N) de R7, R9–R14, R16 y R18, que pasa a 0805; y el pin 1 de Y1. Claude verifica: cada condensador con `.1` y `.2` una sola vez.
- [x] **A4 → hecho por script (`pendientes_f3.py`)**: 10 puertos Bar; cables en U rectificados; U3 pines 1/3/5 con puertos a la izquierda y GND de los pines 2/6 en x = 10900; U2 pin 12 con puerto arriba en (3600, 8000) y GND del pin 15 en (3400, 8300) apuntando a la derecha. Texto original del paso: **`+3V3` y `+3V3A` como puertos de alimentación**, en la hoja **03_MEDICION** (no en la TOP). Hoy son 10 net labels azules; con el alcance jerárquico las net labels son locales y U2/U3 quedan sin alimentación. Para cada una: clic en el texto azul `+3V3` → Delete (queda el cable) → **Place → Power Port** → antes de hacer clic pulsa **Tab** → en Properties: Name `+3V3` (o `+3V3A`), Style **Bar** → Enter → lleva el símbolo al extremo libre de ese cable (aparece una cruz roja cuando engancha) → clic → Esc. Copia el primero (Ctrl+C / Ctrl+V) para los demás. Dónde: U2 pin 12; riel de C14, C15 y R7; U3 pines 1, 3 y 28; riel de C24 y C25; encima de R16; encima de R18 → `+3V3`. U3 pin 5 y encima de C28 → `+3V3A`. Esquema: `docs/esquemas/F3_c4_puerto_alim.svg`.
- [x] **A5 → ya estaba hecho (9 oct, 17:59), verificado.** **Net labels `HV_D1`, `HV_D2`, `HV_D3`** en los 3 puntos donde se tocan R2–R3, R3–R4 y R4–R5 (las resistencias están pegadas pin con pin, sin cable). **Place → Net Label** → Tab → Net Name `HV_D1` → pon la esquina inferior izquierda del texto sobre el punto de unión R2–R3 (cruz roja) → repite con R3–R4 y R4–R5. Por qué: el Blanket de `HV_AC` solo mete una red si tiene un nombre o un extremo de cable debajo; sin eso, esos 3 nodos de red eléctrica quedarían fuera de la clase y las reglas de aislamiento de la PCB no los verían. Esquema: `docs/esquemas/F3_c5_divisor_etiquetas.svg`.
- [x] **A6 → hecho por script (4 directivas).** **Hoja 02: `HV-AC` → `HV_AC`.** Son las 4 directivas que en la hoja se ven como un **circulito rojo con una «i» y el texto rojo «Parameter Set»**: dos sobre los cables `AC_L1` y `AC_L2` (junto a F1 y F2) y dos sobre `AC_L1_F` y `AC_L2_F` (junto a PS1). Doble clic en el circulito → Properties → Parameters → la fila de la clase dice `HV-AC` → cámbiala a `HV_AC` → Enter.
- [x] **A7 → hecho por script: 3 Blankets (registro 225) + Parameter Set con `ClassName`; cobertura verificada con `cobertura_blanket.py` (HV_AC: AC_L1_F, AC_L2_F, HV_D1–3, HV_DCDC, HV_INP, HV_LDO; ANALOG: AMC_OUT*, ATM_V*, ATM_I*, CT_*).** **Blankets en 03** (Place → Directives → Blanket: clic en cada vértice, clic derecho para cerrar; luego Place → Directives → Parameter Set, Tab, Parameters → Add → Net Class, con la punta de la banderita sobre el borde). Coordenadas calculadas con la hoja de las 17:23; si algo se movió, Claude las recalcula con `cobertura_blanket.py` antes de dibujar. Mapa: `docs/esquemas/F3_c3_clases.svg`.

  | Blanket | Vértices (mil) | Banderita |
  |---|---|---|
  | HV_AC | (400, 10800) → (9400, 10800) → (9400, 6900) → (3800, 6900) → (3800, 8800) → (1800, 8800) → (1800, 7500) → (400, 7500) | (1000, 10800) |
  | ANALOG (acople) | (400, 6600) → (5400, 6600) → (5400, 6200) → (3400, 6200) → (3400, 5300) → (5400, 5300) → (5400, 4900) → (400, 4900) | (400, 5700) |
  | ANALOG (CT) | (6100, 6200) → (10700, 6200) → (10700, 5800) → (7600, 5800) → (7600, 4800) → (10700, 4800) → (10700, 4300) → (6100, 4300) | (6100, 5300) |

- [x] **A8 → hecho por script (6 parámetros en cada TP).** **Parámetros de TP1–TP6** (los de TP1–TP4 no están en la hoja 02): **Tools → Parameter Manager** con todas las hojas del proyecto → filas TP1–TP6: Manufacturer_Name `Keystone`, Manufacturer_Part_Number `5016`, Value `TP`, Supplier `PCBWay`, Supplier PN `5016`, Assembly `PCBWay` → Accept Changes → Execute.
- [ ] **A9.** Project → Project Options → Error Reporting → *Nets with no driving source* → No Report. Luego **Project → Validate PCB Project**: 0 errores (los avisos de `MEAS_*` con un solo pin desaparecen cuando la hoja 04 tenga la ESP32).

## B. Tareas de la Fase 4

Detalle en `docs/PLAN_FASES.md`, Fase 4.

- [x] Diagrama «ESTÁS AQUÍ» y lista de tareas (11 oct).
- [x] Componentes en un solo mensaje, aprobados el 11 oct (ver `docs/DECISIONES.md`, «Fase 4»): U4 ESP32-S3-WROOM-1-N16R2, U5 CH340C, Q1/Q2 MMBT3904LT1G, J5 TYPE-C-31-M-12, D5 USBLC6-2SC6, SW1–SW3 TS-1187A-B-A-B (SW2/SW3 DNP), J7 bornera 3,5 mm, J8 61300611121, LED3–LED5, sin zumbador. Piezas (b) ya creadas por script: RC0805FR-0712KL, RC0805FR-074K7L, RC0805FR-075K1L, APT2012SURCK.
- [ ] Bajar de SamacSys, en orden: ESP32-S3-WROOM-1-N16R2, CH340G (Broadchip, base del CH340C), TYPE-C-31-M-12, USBLC6-2SC6, MMBT3904LT1G, TS-1187A-B-A-B, 61300611121. Luego Claude completa parámetros y crea el CH340C por script (Altium cerrado).
- [x] Bajadas e integradas (12 oct): ESP32-S3-WROOM-1-N16R2, USBLC6-2SC6, MMBT3904LT1G, TS-1187A-B-A-B, 61300611121; CH340C creado por script desde SN74HC595DR. CH340G, TYPE-C-31-M-12 y UJ20-C-H-G-SMT-TR no traían footprint.
- [ ] **J5 USB-C:** bajar Würth `632723300011` (USB-C receptáculo, THR/SMT, PCB de 1,6 mm; Mouser 38 882 u) y dibujar el bloque `docs/esquemas/F4_s6_usb.svg` con D5, R23 y R24. Plan B: micro-USB Molex 105017-0001 (Sigma).
- [x] Hoja 04 dibujada salvo USB (12 oct). Arreglado por script (`ronda2_f4.py`): designadores, R21 47 k → 4,7 k, LED_PARAR → BTN_PARAR, pines B1/C1 de los pulsadores (estaban en corto con GND), parámetros de U4/Q1/Q2/J8, SW2/SW3 DNP, No ERC repetido. Blankets de 03 creados en el stream «Additional» (verificar en Altium que se vean y que no aparezca *Floating Directive Object*).
- Lista original de la fase (referencia):
  - [ ] Módulo ESP32-S3-WROOM-1-N16R8 (preferido, P5), N8R2 o 1U-N16R8.
  - [ ] Conector USB-C de 16 pines, ESD (por ejemplo USBLC6-2SC6) y CC de 5,1 kΩ.
  - [ ] **Puente USB-UART con DTR y RTS** (CH340C, CP2102N, CH343P…): stock en Sigma y PCBWay; alimentado a 3,3 V para que su TX no saque 5 V hacia la ESP32; qué pasa si se conecta el USB con la placa sin alimentar.
  - [ ] **Circuito de programación automática (D13, imagen del profesor):** Q1 y Q2 NPN (2 × SOT-23, por ejemplo MMBT3904/S8050, o uno doble en SOT-363), R1 y R2 de 12 kΩ, R3 de 4,7 kΩ en GPIO0. Revisar con la guía de hardware de Espressif el RC de EN (10 kΩ + 1 µF) con el auto-reset.
  - [ ] Botón PARAR; RESET y BOOT solo de respaldo (decidir si van o quedan DNP); LEDs (copiar `APT2012SGC`); zumbador opcional.
  - [ ] Conector de prueba (UART0, 3V3, GND).
- [ ] Dibujar la hoja con esquemas literales por bloque (`docs/tools/esquemas.py`, funciones de F3 incluidas `pwr_h` y `noerc`).
- [ ] Mapa de pines definitivo en `docs/DECISIONES.md`: UART0 = GPIO43/44; SPI del ATM90E26 (`MEAS_*`), IRQ, WarnOut, ZX, I²C, 1-Wire, `RELAY_EN`, `RTC_INT`, LEDs, PARAR. Sin strapping (GPIO0, 3, 45, 46) para salidas críticas ni GPIO35–37 (PSRAM octal del N16R8).
- [ ] Compilar, exportar `PROYECTO_F4.pdf` **directo a `docs/revisiones/`** (en el asistente del Smart PDF, *Output File Name*) y revisar.
- [x] Cerrar la fase (CLAUDE.md) — 12 oct 2026.

## Ten a mano

- **Altium cerrado al empezar** (para A1).
- La cuota del día del Library Loader de SamacSys: primero las piezas críticas (módulo ESP32-S3, puente USB-UART, conector USB-C, ESD, transistores si no hay uno equivalente).
- La página de Sigma Electrónica para stock y precios.
- La imagen del profesor: `docs/referencias/F4_autoprogramacion_profesor.jpg`.

## Qué se hizo en la Fase 3

- Componentes elegidos y registrados (`docs/DECISIONES.md`, «Fase 3»): AMC3330DWE (U2), divisor 4 × ERJ-P08F1004V + ERA-6AEB103V, acople AC, ATM90E26-YU-R (U3) con cristal de 8,192 MHz, CT SCT-013-000V con J3 SJ1-3515-SMT-TR y D4 SMAJ5.0CA.
- Cálculos en `docs/calculos/F3_MEDICION.md` (divisor 1/401; 0,46 Vrms a 240 V en el ATM90E26; 0,5 Vrms a 50 A en el canal de corriente).
- Hoja dibujada, anotada y revisada en PDF; footprints de F3 verificados contra datasheet (AMC3330: 7,50 mm entre filas de pads ≥ 6,4 mm).
- Herramientas nuevas: `arreglar_pdf.py --nuevo`, `cobertura_blanket.py`, `reparar_pin2_condensadores.py`; `esquemas.py` con `pwr_h` y `noerc` y la numeración real de F3.
- Decisión D13: programación automática por USB-UART con DTR/RTS (requisito del profesor).

## Pendientes que no son de esta fase

- F1B/F2B: el 01000056Z es un solo clip y puentearía el fusible; medir el BLX-A de Sigma y hacer un footprint propio (antes de F8).
- F7: verificar los footprints de C2 y C3 de la hoja 02 (vienen con nombres de otras piezas: `EEHZT1E331UP`, `EEE1AA101SP`) y limpiar los parámetros `Datasheet Link` y `Mouser Part Number` que SamacSys copió mal en las ERA-6A y varios condensadores.
- Modelo y manual del EVSE (antes de F6): tensión y corriente de los bornes de habilitación, NA o NC.
- Confirmar si el tercer conductor de la instalación es neutro o tierra; el EVSE necesita tierra.
- Requisitos del profesor para el gabinete (F7); la IRM-20-12 mide 24 mm de alto.
- F7: corregir los `*` del bloque de título, copiar las librerías SamacSys a `lib/` y quitar `Job1.OutJob` del proyecto.
- Firmware: el SPI del ATM90E26 va a ≤ 160 kbps y, en modo flexible, hay que poner LNSel = N.
