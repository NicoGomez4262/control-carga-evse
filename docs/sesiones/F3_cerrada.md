# Fase 3 (continuación) — cerrada el 2026-10-09

> Archivo histórico. La fase se cerró el 9 oct (17:45) con pendientes, que pasaron a la sección A del `NEXT_SESSION.md` de la Fase 4. Revisión final: `docs/revisiones/PROYECTO_F3.pdf`.

**Estado (8 oct 2026, noche):** F3 en curso. Componentes elegidos y aprobados (`docs/DECISIONES.md`, «Fase 3»), cálculos hechos (`docs/calculos/F3_MEDICION.md`) y las pasivas ya están dibujadas en la hoja. Falta: bajar las **6 piezas** que no entraron por la cuota diaria de SamacSys, corregir lo que encontró la revisión (lista de abajo), poner las clases de red, anotar, compilar, revisar el PDF y cerrar la fase.

La guía de dibujo son los esquemas literales por bloque en `docs/esquemas/F3_s1_divisor.svg` … `F3_s6_soporte.svg` (ábrelos en el navegador). Las referencias de esos esquemas (R2–R18, C9–C31, U2, U3, Y1, J3, D4, LED2, TP5, TP6) son las que debe tener la hoja.

## Revisión del 9 oct (14:29) — lo que falta exactamente

Ya hecho: las 6 piezas bajadas; U2, U3, Y1, J3, D4 y R2–R5 colocados; divisor completo; U2 y U3 con todos sus pines bien; **C29 corregido** (`ATM_RST` ya no está unida a GND); **R6 = ERA-6AEB103V**; TIP de J3 en el riel de `CT_P` y SLEEVE en el de `CT_N`. Footprints de F3 verificados (AMC3330: 7,50 mm entre filas de pads ≥ 6,4 mm; jack igual al datasheet). La hoja se movió completa +100/+400 mil el 9 oct; las coordenadas de abajo son las nuevas.

Librería (`SamacSys.SchLib`, guardada 12:59):
- [ ] 5 condensadores con 4 pines (`C0805C102J5GAC-TU`, `C0805C120J5GACTU`, `C0805C472J5GACTU`, `CL21B104KBCNNNC`, `CL21B105KAFNNNE`): borrar los 2 repetidos.
- [ ] **Cristal `ECS-81.92-12-30Q-EN-TR`: el pin de la derecha no tiene número ni nombre** → Designator `1`, Name `IN/OUT` (si no, el pad 1 queda sin red en la PCB).
- [ ] `AMC3330DWE` y `ATM90E26-YU-R` traen designador `IC?` → `U?`.
- [ ] Parámetros: Value/Supplier/Supplier PN/Assembly de las 6 piezas nuevas; Supplier/Supplier PN/Assembly de las 6 resistencias; Supplier PN propio de 6 condensadores. Luego Update From Libraries en 02 y 03 (sin KEYSTONE-5016).

Hoja 03:
- [ ] **`+3V3` (8) y `+3V3A` (2) son net labels, no puertos de alimentación**: con el alcance jerárquico las net labels son locales y U2/U3 quedan sin conexión con la hoja 02. Cambiarlas por puertos de alimentación (Bar). La guía S2/S5 tenía este error; ya está corregida.
- [ ] J3: RING (3), TIP_SWITCH (10) y RING_SWITCH (11) están unidos a `CT_N` → borrar 3 cables, redibujar el riel de abajo desde SLEEVE, *No ERC* en 3, 10 y 11 (`docs/esquemas/F3_c1_j3.svg`).
- [ ] Valores: C9 (8900, 10200), C11 (6300, 8500), C14 (6300, 7500) → `C0805C102J5GAC-TU`; R14 (8700, 6000), R15 (8700, 4600), R18 (6900, 1700) → `RC0805FR-071KL`.
- [ ] TP5 en `AMC_DIAG`; net labels `HV_D1`–`HV_D3` en las uniones del divisor (necesarias para que el Blanket las meta en `HV_AC`); `CT_P`/`CT_N`.
- [ ] Designadores a mano antes de anotar: U2, U3, J3 (si no, Altium le da J2, reservado para F6), TP5, TP6.
- [ ] Parámetros de TP1–TP6 (los de TP1–TP4 ya no están en la hoja 02).

Clases y cierre:
- [ ] 02: `HV-AC` → `HV_AC` (4 banderitas).
- [ ] 03: 3 Blankets en polígono (`docs/esquemas/F3_c3_clases.svg`): HV_AC, ANALOG A (acople), ANALOG B (CT). No sirven rectángulos: los símbolos de GND meterían GND en ANALOG.
- [ ] Anotar, Validate, PDF del proyecto → `python docs/tools/arreglar_pdf.py --nuevo docs/revisiones/PROYECTO_F3.pdf`.
- [ ] Restaurar `F1_TOP.pdf` (cerrar el visor y ejecutar `python docs/tools/arreglar_pdf.py docs/revisiones/F1_TOP.pdf`, sin `--nuevo`).

## Prompt para iniciar

```text
Seguimos con la FASE 3 del proyecto "Control de carga EVSE" (hoja 03_MEDICION.SchDoc).

Lee CLAUDE.md, NEXT_SESSION.md, docs/PLAN_FASES.md (Fase 3), docs/DECISIONES.md («Fase 3») y docs/calculos/F3_MEDICION.md. Los esquemas de guía están en docs/esquemas/F3_*.svg.

Hoy ya bajé (o voy a bajar) las 6 piezas de SamacSys y estoy haciendo las correcciones de NEXT_SESSION.md.
1. Verifica la librería SamacSys.SchLib (pines duplicados, footprints y parámetros de las piezas de F3).
2. Lee 03_MEDICION.SchDoc con docs/tools/lista_redes.py y compara red por red contra los esquemas F3_*.svg; dime exactamente qué falta o está mal, con esquemas literales (referencia, número de parte y net labels) cuando haya que redibujar algo.
3. Guíame con las clases de red (Blanket HV_AC y ANALOG), la anotación y la compilación.
4. Cuando exporte docs/revisiones/PROYECTO_F3.pdf, corrígelo con docs/tools/arreglar_pdf.py, revísalo y cierra la Fase 3 como indica CLAUDE.md (incluido el NEXT_SESSION de la Fase 4).
```

## Dónde estamos

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
 ACTUACIÓN J2 ◄── contacto seco (aislado) ────────────┨   Relé   ┠◄─ bobina ─ [F6 Driver relé] ◄─ GPIO ─ ESP32-S3
                                                      ┃   (F6)   ┃
 CONTROL                                              ┃          ┃   [F4 ESP32-S3] ─ WiFi ─► router ─► internet ─► app
 INTERFAZ                                             ┃          ┃ J5 ─► [F4 USB-C · botones · LEDs] ─► ESP32-S3
 SENSORES                                             ┃          ┃ J4 ─► [F5 Sensores · RTC · FRAM] ─► ESP32-S3
 BANCO                                                ┃          ┃ J6 ─► [F2 Entrada banco 12 V] ─► D2 ─► +VIN
════════════════════════════════════════════════════════════════════════════════════════════════════════════════
[F# bloque] fase en que se diseña · ▐bloque▌ se diseña en ESTA fase · ► carril con trabajo en esta fase
┃ ┃ barrera de aislamiento · ┨ ┠ componente que cruza la barrera (AC-DC, AMC3330, relé)
│ L1/L2 (L/N en 120 V) con fusibles · J1–J6 conectores · J1 con cable largo a la línea · J2 contacto seco aislado
```
<!--/DIAG-->
<!--/DIAG-->

## Paso a paso para mañana (en Altium)

### A. Antes de bajar piezas: arreglar la librería (pestaña `SamacSys.SchLib`)

1. **Pines duplicados (importante).** Cinco condensadores tienen **4 pines** (1, 2, 1, 2) en vez de 2: `C0805C102J5GAC-TU`, `C0805C120J5GACTU`, `C0805C472J5GACTU`, `CL21B104KBCNNNC`, `CL21B105KAFNNNE` (el primero se dañó y los otros se copiaron de él). Para cada uno: panel **SCH Library** → clic en la pieza → en **Properties** pestaña **Pins** → se ven 4 filas → selecciona las 2 últimas (las repetidas) → icono de papelera → Ctrl+S. Comprobación: en la hoja, cada condensador debe tener solo un «1» y un «2».
2. **Parámetros que faltan** (Tools → Parameter Manager):
   - 6 resistencias (`RC0805FR-0747KL`, `RC0805FR-0710KL`, `ERA-6AEB103V`, `ERA-6AEB203V`, `ERA-6AEB133V`, `ERA-6AHD100V`): Supplier = `PCBWay`, Supplier PN = su número de parte, Assembly = `PCBWay`.
   - 6 condensadores (`CL21B105KAFNNNE`, `CL21B104KBCNNNC`, `C0805C472J5GACTU`, `C0805C120J5GACTU`, `C1206C333J5GACTU`, `C3216NP01H104J160AA`): **Supplier PN** = su propio número de parte (hoy dicen `C0805C102J5GACTU` o `CL31B106KBHNNNE`).
   - Accept Changes → Execute → Ctrl+S.

### B. Bajar las 6 piezas (Library Loader de SamacSys)

`ERJ-P08F1004V` · `AMC3330DWER` · `ATM90E26-YU-R` · `ECS-81.92-12-30Q-EN-TR` · `SJ1-3515-SMT-TR` · `SMAJ5.0CA` (Littelfuse). Guardar las dos librerías (Ctrl+S en `SamacSys.SchLib` y `SamacSys.PcbLib`). Parámetros:

| Fila | Value | Supplier | Supplier PN | Assembly |
|---|---|---|---|---|
| ERJ-P08F1004V | 1M 1206 | PCBWay | ERJ-P08F1004V | PCBWay |
| AMC3330DWER | ±1V iso amp | Mouser | 595-AMC3330DWE | PCBWay |
| ATM90E26-YU-R | energy meter | PCBWay | ATM90E26-YU-R | PCBWay |
| ECS-81.92-12-30Q-EN-TR | 8.192MHz 12pF | PCBWay | ECS-81.92-12-30Q-EN-TR | PCBWay |
| SJ1-3515-SMT-TR | jack 3.5mm | PCBWay | SJ1-3515-SMT-TR | PCBWay |
| SMAJ5.0CA | 5V TVS bidir | PCBWay | SMAJ5.0CA | PCBWay |

### C. Correcciones en `03_MEDICION` (encontradas en la revisión del 8 oct)

- [ ] **Divisor (esquema 1):** hay **5** resistencias provisionales de 20 kΩ; deben ser **4 × ERJ-P08F1004V** (R2–R5). Además el cable no toca ni el puerto `AC_L1_F` (hueco entre el puerto y la primera resistencia) ni la red `HV_INP` (hueco después de la última). Borra las 5, pon las 4 nuevas y cablea `AC_L1_F` → R2 → R3 → R4 → R5 → `HV_INP`, con net labels `HV_D1`, `HV_D2`, `HV_D3` entre ellas.
- [ ] **Piezas cambiadas** (doble clic → Properties → botón «…» junto a *Design Item ID* → elegir en `SamacSys.SchLib`):
  - R6 (entre `HV_INP` y `AC_L2_F`): está como ERA-6AEB133V (13 k) → **ERA-6AEB103V** (10 k).
  - C9 (junto a R6): está como C0805C120J5GACTU (12 pF) → **C0805C102J5GAC-TU** (1 nF).
  - C11 (en `HV_DCDC`, el del medio) y C14 (en `HV_LDO`, el de la derecha): están como 12 pF → **C0805C102J5GAC-TU** (1 nF).
  - R14 y R15 (serie hacia `ATM_IP`/`ATM_IN`) y R18 (del LED): están como RC0805FR-0710KL (10 k) → **RC0805FR-071KL** (1 k).
- [ ] **C29 en corto:** el cable que baja de `ATM_RST` pasa por encima de C29 y une sus dos pines (la red `ATM_RST` quedó unida a GND). Borra ese cable y redibuja: nodo `ATM_RST` → pin 1 de C29; pin 2 de C29 → GND.
- [ ] **Cristal:** el cable de arriba va seguido de `XTAL_I` a `XTAL_O` (las dos redes quedaron unidas). Al poner Y1, corta el cable entre C30 y C31 y conecta Y1 en medio (esquema 6).
- [ ] **Falta TP5** (Keystone 5016) en `AMC_DIAG` (esquema 2).
- [ ] **Net labels `CT_P` y `CT_N`** en los dos rieles del CT (esquema 4).
- [ ] TP5 y TP6: parámetros en la hoja como en F2 (Keystone, 5016, TP, PCBWay, 5016, PCBWay).

### D. Colocar las piezas nuevas (esquemas 1, 2, 4, 5 y 6)

- [ ] U2 en lugar de la nota «AMC»: un cable corto en cada pin con su net label (las etiquetas ya están escritas a la izquierda de la nota); pines 9 y 15 a GND.
- [ ] U3 en lugar de la nota «ATM»: igual; los pines SPI, ZX, IRQ y WarnOut van a los puertos `MEAS_*` que ya están; pines 2, 6, 9, 10, 11, 12 y 14 a GND; 1 y 28 a `+3V3`.
- [ ] J3 + D4 en lugar de la nota (tip = pin 2 → `CT_P`, sleeve = pin 1 → `CT_N`, ring = pin 3 sin conexión con una cruz *No ERC*; D4 entre `CT_P` y `CT_N`).
- [ ] Y1 entre `XTAL_I` y `XTAL_O`.

### E. Clases de red, anotación, compilación y PDF

- [ ] En `02_ALIMENTACION`: las 4 banderitas dicen `HV-AC` → `HV_AC` (doble clic en la banderita → Properties → *Parameters* → valor de *Net Class*).
- [ ] En `03_MEDICION`: **Place → Directives → Blanket** alrededor de toda la zona de red (divisor, R6/C9, condensadores C10–C14 y el lado izquierdo de U2) + **Parameter Set** tocando el borde con Net Class `HV_AC`. Otro Blanket sobre el acople (C18–C21, R8–R11) y la entrada del CT (R12–R15, C22, C23) con Net Class `ANALOG`.
- [ ] Anotar: **Tools → Annotation → Annotate Schematics Quietly**. Si los números no coinciden con los esquemas, no importa: Claude actualiza la documentación con los que queden.
- [ ] Project → Validate PCB Project: 0 errores (ya no deben aparecer `ATM_RST`/GND ni `XTAL_I`/`XTAL_O` unidas).
- [ ] Exportar el Smart PDF de todo el proyecto como **`docs/revisiones/PROYECTO_F3.pdf`** (en el asistente, cambia el nombre de salida: la última vez se sobrescribió `F1_TOP.pdf`).

## Ya verificado (8 oct)

- Librería: footprints de las 6 resistencias nuevas = RESC2012X60N (0805) ✓; fabricante, número de parte y valor de las 12 pasivas ✓.
- Hoja 02: parámetros llegaron a la hoja (Update From Libraries) ✓; pads de J1 1.7 × 3.0 mm ✓.
- Hoja 03, conexiones correctas: condensadores de `HV_DCDC`/`HV_LDO` a `AC_L2_F`; C15 en `AMC_LDO`; C16/C17 y R7 en `+3V3`; acople completo (C18–C21, R8–R11 → `ATM_VP`/`ATM_VN`); carga del CT con punto medio a GND; filtros C22/C23; DVDD, AVDD, Vref; pull-up de CS a `MEAS_CS`; LED2 en el sentido correcto; TP6 en `ATM_CF2`.

## Pendientes que no son de esta fase

- F1B/F2B: el 01000056Z es un solo clip y puentearía el fusible; medir el BLX-A de Sigma y hacer un footprint propio (antes de F8).
- Error Reporting: «Nets with no driving source» → No Report (si todavía no se hizo).
- Restaurar `docs/revisiones/F1_TOP.pdf` (se sobrescribió con la exportación del 8 oct): cerrar el PDF y ejecutar `python docs/tools/arreglar_pdf.py docs/revisiones/F1_TOP.pdf` (lo rehace desde `F1_TOP_original.pdf`).
- Modelo y manual del EVSE (antes de F6): tensión y corriente de los bornes de habilitación, NA o NC.
- Confirmar si el tercer conductor de la instalación es neutro o tierra; el EVSE necesita tierra.
- Requisitos del profesor para el gabinete (F7); la IRM-20-12 mide 24 mm de alto.
- F7: corregir los `*` del bloque de título, copiar las librerías SamacSys a `lib/` y quitar `Job1.OutJob` del proyecto.
- Firmware (F4): el SPI del ATM90E26 va a ≤ 160 kbps; en modo flexible hay que poner LNSel = N.
- Actualizar el artifact de referencia al cerrar F3 (J6 confirmada; medición con AMC3330 + ATM90E26 + SCT-013-000V).
