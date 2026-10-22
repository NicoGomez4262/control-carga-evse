# Guía de ubicación y ruteo — Fase 8 (EVSE_Monitor.PcbDoc)

Escrita el 19 oct 2026, antes de ubicar. Base: reglas de seguridad de `CLAUDE.md`, BOM de F7 (`docs/BOM_F7.md`), footprints de `lib/SamacSys.PcbLib` y capacidades de PCBWay ([capabilities](https://www.pcbway.com/capabilities.html), cotizador [orderonline](https://www.pcbway.com/orderonline.aspx), 19 oct 2026). La decisión de stackup, tamaño y acabado se registra en `docs/DECISIONES.md` (Fase 8).

## 1. Distribución general (placa de 130 × 100 mm, D18; origen abajo a la izquierda)

La ubicación completa de los 132 componentes está en `docs/tools/ubicacion_f8.py` (lista `POS`, revisada por el mismo script: choques de courtyard, distancias pad a pad por clase de red, bordes de transporte, agujeros y fiduciales) y se aplica en Altium con `docs/tools/ubicar_f8.pas`. Dibujo: `docs/revisiones/F8_ubicacion.png`.

```text
 y=100 ┌(M3)──────────────────────────┬──────┬──────────────────────────────────────────────────────┐ ← antenas de U4, J3 y J5 sobresalen
       │ J2 ═════ ISLA EVSE ══════ K1 ┼──────┼ K1 driver   J3 (CT)   J5 USB   LEDs  ┌──U4 ESP32-S3──┐(M3)│
  y=80 │ ── hueco ≥ 6,4 mm ────────── │      │                                    └───────────────┘ J8 │
  y=75 │ J1 → F2 F1 (verticales)  C10–│ BAR- │ C13–15  ATM90E26 (U3)  Y1   CH340C (U5)   SW2  SW3      │
       │      F2B F1B (DNP)   R2–R5 U2┼ RERA ┼ U2 → cadena V   ← CT     U6 AHT20               J4 │
       │           RV1                │ 6,7  │                  U7 RTC     BT1 (pila)                   │
       │  PS1 (entrada) ══════════════╪══════╪═ PS1 (salida) → D1 · C2 · D3 · L1 · U1 · L2 · C3     J7 │
 y=0   └(M3)──────────────────────────┴──────┴──────────────── J6 (banco) ─────────── SW1 ───────(M3)┘
       x=0                         x=45  x=51,7                                                   x=130
```

- **Zona de red (x 0–45, cobre hasta y = 75):** PS1 abajo (pines de red en x = 13), J1 en el borde izquierdo (L1 arriba, L2 abajo), F2/F1 verticales con la entrada arriba, RV1 debajo de las salidas de los fusibles, el divisor R2–R5 en columna junto a U2 y los condensadores del lado HV de U2 (C9–C12, C16, C17) y R6 a su lado. Sin planos de cobre (ni GND ni otro): solo pistas. F1B/F2B (DNP) se ponen **anidados** sobre F1/F2: los pads del BLX-A (Ø3,4 mm a ±11 mm) quedan por fuera de los del UMT-H (±6,9 mm) y son de la misma red, así que no hay problema de distancia; solo se excluye el choque de cuerpos F1↔F1B y F2↔F2B en la regla de Component Clearance.
- **Isla EVSE_EXT (x 0–45, y ≥ 80):** J2 en el borde izquierdo y la salida de K1 (pines 3 y 4). Separada ≥ 6,4 mm de la zona de red (hueco horizontal) y del SELV (barrera). Solo dos pistas: `EVSE_EN_A` y `EVSE_EN_B`.
- **Barrera (x 45–51,7, de arriba abajo):** 6,7 mm sin cobre en ninguna capa (es la distancia entre los pads de K1; U2 deja 7,5 mm y PS1 45 mm). Solo la cruzan los cuerpos de **PS1, U2 y K1**. No hace falta ranura: con 6,7 mm de superficie ya se cumplen la distancia en el aire (≥ 5,5 mm) y la de superficie (≥ 6,4 mm).
- **SELV (x 51,7–130):** potencia (D1, D2, D3, C2, C3, U1, L1, L2, C4–C8, FB1) junto a la salida de PS1; medición (U3, Y1 y los filtros del CT y de tensión) junto a la salida de U2 y lejos de PS1, U1 y L2; ESP32-S3 arriba con la antena afuera; USB (J5, D5, U5) abajo a la derecha; sensores y RTC (BT1, U7, U6, J4, D6) a la derecha.
- **Antena del ESP32-S3:** Espressif recomienda que la antena del módulo quede **fuera de la placa**, con el punto de alimentación de la antena pegado al borde; si no, recortar la placa a los lados y debajo de la antena ([guía de hardware ESP32-S3](https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32s3/pcb-layout-design.html)). U4 va con el origen en (112; 93,5): el borde superior pasa por el inicio de la antena (≈ 6,3 mm de antena sobresalen). J5 queda a 15 mm de la antena. Debajo del resto del módulo, GND continuo y muchas vías de GND; ningún cobre en la proyección de la antena. 15 mm libres alrededor es la recomendación para la carcasa (la próxima versión).
- **Conectores al borde y ensamble:** la banda transportadora de la línea SMT agarra dos bordes opuestos; PCBWay recomienda ≥ 5 mm libres en esos bordes o agregar rieles de proceso ([PCBWay, requisitos de equipos SMT](https://www.pcbway.com/blog/PCB_Assembly/PCB_Requirements_for_Typical_SMT_Equipment.html)). Se usan como bordes de transporte el **izquierdo y el derecho**, donde solo van conectores THT (J1, J2 a la izquierda; J6, J4, J7, J8 a la derecha) y **ningún SMD a menos de 5 mm**. Las piezas SMD de borde van arriba (U4, J3, J5). Así no hacen falta rieles de proceso.
- **Lo que se suelda a mano (U1, K1):** K1 (SMD, en la barrera) tiene 2 mm libres alrededor para el cautín; U1 es THT (SIP-3) y se suelda por abajo, así que no necesita espacio extra arriba.
- **Agujeros M3:** NPTH Ø3,2 mm en (4; 4), (126; 4), (4; 96) y (126; 96). Los de la zona de red y la isla EVSE, a ≥ 6,4 mm del cobre de red y con separadores de **nylon** (la placa no tiene gabinete).
- **Fiduciales:** 3 (cobre Ø1 mm, máscara Ø2 mm) en el SELV, en triángulo asimétrico: (55; 46), (123,5; 46) y (77,5; 84,5).

## 2. Planos de tierra

- **Dos capas:** capa inferior = GND casi entera en el SELV; capa superior = señales + GND de relleno con vías de costura cada ≈ 5 mm (y alrededor del ESP32-S3 y del cristal).
- **Un solo GND** (no se separa AGND de DGND): la sección analógica (U3, filtros, U2 salida) queda sobre GND continuo sin pistas que corten el plano por debajo; los pines AGND y DGND del ATM90E26 se unen bajo el chip.
- **Ningún plano en la zona de red, la barrera ni la isla EVSE.** Los polígonos de GND guardan automáticamente 6,4 mm por la regla de clearance.
- **Sin cobre bajo la antena** (todas las capas) — keepout + recorte de polígono.
- Relieves térmicos (4 rayos de 0,3 mm) en los pads THT conectados a GND (J6, J4, PS1 −V) para que se puedan soldar; conexión directa en vías y SMD.

## 3. Distancias

| Entre | Mínimo | Por qué |
|---|---|---|
| `HV_AC` ↔ cualquier red que no sea `HV_AC` (incluido el GND de relleno) | **6,4 mm** (clearance y creepage) | aislamiento reforzado; en placa plana sin ranura la distancia en el aire y la de superficie son la misma, así que la regla de clearance se pone en 6,4 (cubre también ≥ 5,5) |
| `EVSE_EXT` ↔ cualquier otra red (SELV y `HV_AC`) | **6,4 mm** | J2 es de potencial desconocido |
| Lado L1 (`AC_L1`, `AC_L1_F`, `HV_D1`, `HV_D2`) ↔ lado L2 (`AC_L2`, `AC_L2_F`, `HV_INP`, `HV_DCDC`, `HV_LDO`) | **3,2 mm** | aislamiento funcional L1–L2 (hasta 373 Vpk). J1 deja 3,3 mm entre pads y RV1 6,5 mm ✓ |
| Otras redes dentro de `HV_AC` | 0,5 mm | escalones de 93 Vpk del divisor; U2 tiene 0,62 mm entre pads del lado HV |
| `EVSE_EN_A` ↔ `EVSE_EN_B` | 1,5 mm (salvo en los pads de K1, 1,79 mm) | hasta 400 Vpk que aguanta K1 |
| Resto (SELV) | 0,2 mm (0,15 mm en pads finos de U3/J5 si hace falta) | PCBWay permite 0,1 mm; el cotizador usa 6/6 mil (0,15 mm) por defecto |
| Cobre `HV_AC` ↔ borde de la placa | 1,0 mm | manipulación (placa desnuda); los pads de J1 quedan a ≈ 1,5 mm |
| Cobre SELV ↔ borde | 0,3 mm (polígonos 0,5 mm) | PCBWay ≥ 0,25 mm |
| Cobre de red o EVSE ↔ borde de agujero M3 | 6,4 mm | tornillo accesible (los agujeros no tienen red: los cubre `HV_SELV`) |
| Cuerpo ↔ cuerpo (SMD) | 0,25 mm | pick and place |
| Alrededor de K1 | 2,0 mm | cautín (U1 es THT, se suelda por abajo) |
| SMD ↔ bordes izquierdo y derecho | 5,0 mm | banda transportadora |
| Analógico (U3, Y1, filtros) ↔ PS1, U1, L2 | ≈ 10 mm | ruido de conmutación |

## 4. Anchos de pista (cobre de 1 oz, capa externa, IPC-2221 con ΔT = 10 °C)

| Red | Corriente | Ancho mínimo por cálculo | Se usa |
|---|---|---|---|
| `AC_L1`, `AC_L2`, `AC_L1_F`, `AC_L2_F` (J1 → F → RV1 → PS1) | ≤ 0,5 A rms (IRM-20 a 115 VAC); fusible de 1 A | 0,30 mm para 1 A | **1,5 mm** (mín. 1,0 mm en el camino de potencia; 0,5 mm solo en los ramales hacia U2 y sus condensadores). Ancho y corto también por el pico de RV1 |
| `HV_D1–3`, `HV_INP`, `HV_DCDC`, `HV_LDO` | µA–mA | — | 0,3–0,4 mm |
| `VIN_ACDC`, `VIN_BANCO`, `+VIN` | hasta 1,67 A (máx. del IRM-20-12) | 0,65 mm para 1,67 A | **1,0 mm** |
| `+3V3` | ≤ 0,5 A (R-78CK) | 0,12 mm | 0,6 mm el tronco, 0,3 mm los ramales |
| `+3V3A` | mA | — | 0,4 mm |
| `GND` | — | — | polígono; pistas de 0,5 mm |
| `EVSE_EN_A/B` | ≤ 120 mA (K1) | — | 0,5 mm |
| `USB_DP` / `USB_DN` | USB Full Speed (CH340C) | 90 Ω diferencial | 0,50 mm con 0,15 mm entre ellas y 0,15 mm al GND da **92,6 Ω** (cálculo 2D, εr 4,4, núcleo 1,51 mm), pero los pads de J5 miden 0,3 mm a 0,5 mm de paso: el autorouter usa **0,3 mm** (preferido de `Ancho_USB`). A 12 Mbps y ≈ 20 mm de largo la impedancia no es crítica; si se quiere, después se rehace con el ruteo interactivo de par diferencial (0,50/0,15) donde haya espacio |
| Señales | — | — | 0,25 mm (mín. 0,2 mm) |
| Vías | — | — | señal 0,3 / 0,6 mm (anillo 0,15); potencia 0,4 / 0,8 mm, varias en paralelo |

Referencia del cálculo de ancho: I = 0,048 · ΔT^0,44 · A^0,725 (A en mil², capa externa).

**Anchos preferidos para el autorouter (20 oct):** los troncos de red (1,5 mm), 12 V (1,0 mm) y R-78CK (0,6–0,8 mm) van prerruteados (`ruteo_f8.py`); el resto lo rutea Situs con el ancho preferido de cada regla: red 0,5 · 12 V 0,8 · 3,3 V 0,4 · GND 0,3 · USB 0,3 · señales 0,25 mm (los pads de U3 miden 0,45 mm a 0,65 mm de paso y los de J5, 0,3 mm a 0,5 mm).

## 5. Mínimos y máximos de PCBWay (servicio estándar, sin costo extra)

| Parámetro | PCBWay | En este diseño |
|---|---|---|
| Pista / espacio | mín. 0,1 mm (4 mil); el cotizador usa 6/6 mil (0,15 mm) | mín. 0,2 mm (0,15 mm en pads finos) |
| Taladro mecánico | 0,15–6,0 mm; < 0,2 mm o > 6 mm cuesta más; el cotizador usa 0,3 mm | vías de 0,3 mm; el más chico de las piezas es 0,4 mm (J5) |
| Tolerancia de agujero | PTH ± 0,08 mm; NPTH ± 0,05 mm | M3 NPTH 3,2 mm |
| Anillo mínimo | 0,15 mm | vías 0,15 mm ✓; **J5: 0,125 mm ✗** (agujero 0,4 / pad 0,65) → agrandar el pad a ≥ 0,70 mm si el paso lo permite, o confirmarlo con PCBWay |
| Ranura metalizada | ancho ≥ 0,5 mm, largo ≥ 2 × ancho | J5: 0,6 × 1,2 mm ✓ |
| Ranura sin metalizar | ancho ≥ 0,8 mm | no se usa (si se pusiera una de aislamiento: ≥ 1,0 mm) |
| Agujero ↔ agujero | ≥ 0,41 mm (piezas); vías ≥ 0,28 mm | regla 0,4 mm |
| Cobre / agujero ↔ borde | ≥ 0,25 mm (pads SMD ≥ 0,3 mm) | 0,3 mm; red 1,0 mm |
| Serigrafía | línea ≥ 0,15 mm; texto ≥ 0,8 mm de alto | 0,15 mm / 1,0 mm |
| Puente de máscara | ≥ 0,1 mm (verde, < 2 oz) | regla 0,1 mm |
| Apertura de máscara | ≥ 0,05 mm (2 mil) | expansión 0,05 mm |
| Espesor / cobre | 0,2–3,2 mm; 1–8 oz | 1,6 mm, 1 oz |
| Contorno | fresado ± 0,2 mm | 130 × 100 mm |

## 6. Reglas de Altium (Design » Rules…, «PCB Rules and Constraints Editor»)

Se escriben por script (`docs/tools/reglas_f8.py`) en `EVSE_Monitor.PcbDoc` con Altium cerrado (stream `Rules6`, 66 reglas); en Altium solo se revisan. J5 tiene además `J5_pads` (0,145 mm entre sus pads) y `Mascara_J5` (sin mínimo de puente de máscara). Las consultas usan los nombres de clase y de red del esquemático.

| Carpeta del editor | Regla | Alcance | Valor |
|---|---|---|---|
| Electrical › Clearance | `HV_SELV` | `InNetClass('HV_AC')` ↔ `Not InNetClass('HV_AC')` | 6,4 mm |
| Electrical › Clearance | `EVSE_resto` | `InNetClass('EVSE_EXT')` ↔ `Not InNetClass('EVSE_EXT')` | 6,4 mm |
| Electrical › Clearance | `L1_L2` | redes del lado L1 ↔ redes del lado L2 (tabla 3) | 3,2 mm |
| Electrical › Clearance | `EVSE_A_B` | `InNet('EVSE_EN_A')` ↔ `InNet('EVSE_EN_B')` | 1,5 mm (excepción de 1,7 mm en los pads de K1) |
| Electrical › Clearance | `HV_interna` | `InNetClass('HV_AC')` ↔ `InNetClass('HV_AC')` | 0,5 mm |
| Electrical › Clearance | `Clearance` (general) | All ↔ All | 0,2 mm |
| Electrical › Creepage Distance | `Creepage_HV`, `Creepage_EVSE`, `Creepage_L1_L2` | los mismos alcances | 6,4 / 6,4 / 3,2 mm |
| Routing › Width | `Ancho_red`, `Ancho_HV`, `Ancho_12V`, `Ancho_3V3`, `Ancho_EVSE`, `Width` | tabla 4 | mín / preferido / máx |
| Routing › Differential Pairs Routing | `USB_90` | par `USB_DP`/`USB_DN` | 0,50 mm, separación 0,15 mm, desacople ≤ 3 mm |
| Routing › Routing Via Style | `Vias` / `Vias_potencia` | All / redes de potencia | 0,3/0,6 mm y 0,4/0,8 mm |
| Plane › Polygon Connect Style | `Polygon_THT` / `Polygon` | pads THT / resto | relieve de 4 rayos de 0,3 mm / directo |
| Manufacturing › Minimum Annular Ring | `Anillo_J5` / `Anillo` | J5 / All | 0,12 / 0,15 mm (J5: patrón de Würth, agujero 0,4 y pad 0,65) |
| Manufacturing › Hole Size | `Agujeros` | All | 0,3–6,0 mm |
| Manufacturing › Hole To Hole Clearance | `Agujero_agujero` | All | 0,4 mm |
| Manufacturing › Minimum Solder Mask Sliver | `Mascara` | All | 0,1 mm |
| Manufacturing › Silk To Solder Mask Clearance | — | All | 0,05 mm |
| Manufacturing › Board Outline Clearance | `Borde` / `Borde_HV` | All / `HV_AC` | 0,3 / 1,0 mm |
| Placement › Component Clearance | `ComponentClearance` / `Cautin_K1` | All / K1 | 0,25 / 2,0 mm (F1B y F2B solo contra el resto) |
| Mask › Solder Mask Expansion | — | All | 0,05 mm |
| Mask › Paste Mask Expansion | `BT1_sin_pasta` | pad 3 de BT1 | sin pasta (expansión negativa) |

### Pasos en Altium (resumen; el detalle va en la sesión)

1. **Update PCB:** con el proyecto abierto, en el esquemático: **Design » Update PCB Document EVSE_Monitor.PcbDoc** → **Validate Changes** → **Execute Changes**. Revisar que lleguen los 132 componentes, las clases `HV_AC`, `EVSE_EXT`, `ANALOG`, `USB` y que no haya footprints faltantes (J5 y TP1–TP6 vienen de las librerías de Altium/Content Vault).
2. **Stackup:** **Design » Layer Stack Manager**: 2 capas, núcleo FR-4 1,51 mm, cobre 1 oz; pestaña **Impedance** → perfil diferencial coplanar de 90 Ω (0,50 / 0,15 / 0,15 mm). Guardar con Ctrl+S.
3. **Contorno:** hecho por script (130 × 100 mm, origen en la esquina inferior izquierda).
4. **Reglas:** hechas por script (con Altium cerrado). En Altium: **Design » Rules…** para revisarlas.
5. **Par diferencial:** panel **PCB** (View » Panels » PCB) → lista desplegable **Differential Pairs Editor** → **Add** → positivo `USB_DP`, negativo `USB_DN`, nombre `USB_D`.
6. **Zonas:** **Place » Keepout » Solid Region** en la barrera, el hueco red–isla y bajo la antena (Keep-Out Layer = todas las capas); **Place » Polygon Pour** de GND en Bottom y Top solo sobre el SELV.
7. **Ubicación:** AD 25 solo corre scripts que están en un proyecto de script. **File » Open Project…** → `docs/tools/ubicar_f8.PrjScr` (contiene `ubicar_f8.pas`). Con la pestaña de `EVSE_Monitor.PcbDoc` activa: **File » Run Script…** → `ubicar_f8.pas` → `UbicarF8` (mueve las 132 piezas) y después `AgujerosF8` (agujeros M3 y fiduciales). **Ruteo** por pasos (sección 8C de `docs/PLAN_FASES.md`).
8. **Tools » Design Rule Check…** → **Run Design Rule Check** hasta 0 violaciones.

## 7. Ruteo manual (20 oct)

El prerruteo y el autorouter se descartaron: el usuario rutea a mano. La ubicación se reorganizó pensando en eso (`ubicacion_f8.py`, `autoubicar_f8.py`, `ratsnest_f8.py`: 227 → 140 cruces de ratsnest y 2019 → 1738 mm de conexiones sin GND) y se aplica con `docs/tools/reorganizar_f8.PrjScr` → `ReorganizarF8` (borra el prerruteo, ubica las 132 piezas y los fiduciales, pone designadores de 0,8/1,0 mm con trazo de 0,15 mm y la serigrafía fija). Después de guardar y cerrar Altium, `python docs/tools/limpiar_conexiones.py --escribir` borra el ratsnest viejo guardado para que Altium lo recalcule al abrir.

### Anchos por red

| Redes | Ancho | Tramo |
|---|---|---|
| `AC_L1`, `AC_L2` | **1,5 mm** | J1 → F1/F1B y F2/F2B (entrada de red) |
| `AC_L1_F` | **1,5 mm** (1,0 mm el ramal a R2) | F1 → RV1 → PS1 pin 4 (AC/L) |
| `AC_L2_F` | **1,5 mm** el tronco; **0,5 mm** los ramales | F2 → RV1 → PS1 pin 1 (AC/N); ramales a U2 (pines 2, 4, 7, 8), R6, C9–C12, C16, C17 |
| `HV_D1`–`HV_D3`, `HV_INP`, `HV_DCDC`, `HV_LDO` | 0,4 mm | divisor R2–R5 → U2 y condensadores del lado HV |
| `EVSE_EN_A`, `EVSE_EN_B` | 0,8 mm | J2 → K1 (isla) |
| `VIN_ACDC`, `+VIN`, `VIN_BANCO` | **1,0 mm** (0,5 mm el ramal a R41) | PS1 → D1 → C2, D3, L1, TP2; J6 → D2 |
| `NetC1_2`, `NetC1_1` | 0,6–0,8 mm | L1 → C6/C1 → U1 (entrada) y U1 → C1/C7 → L2 (salida) |
| `+3V3` | 0,6 mm el tronco; 0,4 mm los ramales | L2 → C3/C4/C5 → U4, U5, U3, U7, U6, pull-ups |
| `+3V3A` | 0,4 mm | FB1 → C8, C28 → U3 pin 5 |
| `GND` | polígono; pistas cortas de 0,3–0,5 mm hasta su vía | — |
| `USB_DP`, `USB_DN` | 0,3 mm, juntas (0,15–0,2 mm), mismo largo, sin vías | J5 → D5 → U5 |
| `CT_P/N`, `ATM_IP/IN`, `AMC_OUTP/N`, `ATM_VP/VN` | 0,3 mm, en pares paralelos y simétricos | J3 → U3; U2 → U3 |
| `XTAL_I`, `XTAL_O` | 0,25 mm, lo más cortas posible, con GND alrededor | U3 → Y1 |
| Resto de señales | 0,25 mm | SPI, I²C, UART, LEDs, EN, IO0, OW, botones |

Vías: 0,3/0,6 mm en señales y 0,4/0,8 mm en potencia y GND (reglas `Vias` y `Vias_potencia`).

El ancho preferido de cada regla es el del tronco (`Ancho_red` 1,5, `Ancho_EVSE` 0,8, `Ancho_12V` 1,0 mm): Altium empieza la pista con ese ancho y los ramales se angostan con Tab durante el ruteo. Verificado el 21 oct después de `ReorganizarF8`: 132/132 piezas y designadores en su lugar, 312/312 conexiones de pad a pad, sin pistas ni vías sueltas, 5 textos y 2 líneas de serigrafía, keepouts y agujeros M3 intactos.

### GND mientras se rutea

GND no se rutea como red: al lado de cada pad de GND de condensadores e integrados va una vía de 0,4/0,8 mm con una pista corta (0,3–0,5 mm); el polígono de Bottom las une. Para no ver el ratsnest de GND: N » Hide Connections » Net y clic en un pad de GND.

### Atajos de Altium para el ruteo

| Atajo | Qué hace |
|---|---|
| Ctrl+W | ruteo interactivo |
| Tab (ruteando) | ancho, vía y capa de la pista en curso |
| Shift+Espacio | modo de esquina (45°, 45° con arco, 90°…): dejar 45° |
| Espacio | cambia de qué lado va la esquina |
| `*` del teclado numérico | cambia de capa y pone una vía |
| Shift+R | modo de conflicto: Walkaround o Push, nunca Ignore |
| Ctrl+clic en un pad (sin estar ruteando) | resalta la red (Shift+C limpia) |
| Ctrl+clic en el pad destino (ruteando) | termina la pista sola (autocompletar) |
| Shift+S | ver una sola capa |

### Orden y consejos

1. Red primero: anchas, cortas, en Top, sin vías; respetar 3,2 mm entre el lado L1 y el lado L2 (DRC).
2. Potencia: lazo del R-78CK compacto (L1–C6–U1–C1–C7–L2) y cada condensador con su vía a GND al lado.
3. Analógico: pares del CT y del AMC juntos y simétricos, lejos de U1, L2 y del SPI.
4. Cristal: pistas cortas, sin nada que pase por debajo de Y1.
5. USB: par diferencial (Route » Interactive Differential Pair Routing, par `USB_D`), sin vías y sobre GND continuo.
6. SPI agrupado y corto; I²C con los pull-ups R32/R33 junto a U4.
7. Capa Bottom = plano de GND: usarla solo para saltos cortos; nada por debajo del módulo ESP32-S3.
8. 45° (sin ángulos de 90° ni agudos), sin ramales colgando, angostar al entrar a pads finos (U3 0,65 mm, J5 0,5 mm).
9. DRC en línea encendido; correr Tools » Design Rule Check seguido.

Cruces que necesitan una vía (vienen del pinout, no de la ubicación): IN cruza a IP entre J3 y U3; VP/VN del AMC se cruzan una vez; CS cruza MOSI/MISO/SCK y ZX cruza el SPI junto a U4; EN de Q2 al pin 3 de U4 y OW de U4 a J4 van por abajo rodeando U4; RELAY_EN cruza la cadena del CT; `+VIN` a R41 es largo.

### Planos de tierra (plan del 20 oct; hechos el 22 oct, ver la sección 8)

Bottom: polígono de GND en todo el SELV (de la barrera, x = 51,4, al borde derecho), «Pour Over All Same Net Objects», sin cobre muerto, relieve de 4 rayos en pads THT. Top: relleno de GND en el SELV donde quede espacio. Ningún polígono en la zona de red, la barrera ni la isla. Vías de costura cada ≈ 5 mm en los bordes y alrededor de U4, U3 y Y1.

## 8. Revisión y terminación del ruteo (22 oct)

El usuario ruteó a mano. La revisión se hizo leyendo el PcbDoc con `revisar_ruteo_f8.py`, que es un DRC propio con la misma tabla de reglas.

**Resultado:** 0 cortos, 0 pistas colgando y 0 cobre suelto. Hay una sola distancia en el límite: M1 a un arco de `AC_L2_F`, 6,399 mm contra 6,4 mm (aproximación del arco). Anchos y vías dentro de las reglas.

**Lo que marcaba Altium en verde:** 71 violaciones guardadas, todas de `HV_SELV` y `EVSE_resto` contra los dos rellenos de keepout de la barrera y del hueco red–isla. El segundo alcance de esas reglas («Not InNetClass(...)») incluía los keepouts, que no son cobre, así que todo lo de red a menos de 6,4 mm de la barrera salía en verde aunque estuviera bien. Arreglo: «And Not IsKeepOut» en las dos reglas. Contra los keepouts rige la general de 0,2 mm.

**Faltaba conectar (sin contar GND):**
- `AC_L2_F`: 8 grupos. El lado L2 de U2 tiene que cruzar el lado L1 (F1/F1B, `AC_L1`, `AC_L1_F`, el divisor R2–R4), y por Top la regla L1–L2 de 3,2 mm no dejaba pasar. Esa era la conexión imposible. Se resolvió por Bottom, debajo de F1 (lejos de sus pads), con vías de 0,4/0,8 mm.
- `HV_DCDC` (U2.1–U2.3), `HV_LDO` (C17), `AMC_LDO` (U2.13–U2.16), `NetLED6_2` (LED6–R41) y `VBUS` (A4 y A9/B4 de J5).

**Cómo se terminó (`rutear_f8.py` + `aplicar_ruteo_f8.py`, Altium cerrado):**
- **Ruteador:** A* en rejilla de 0,1 mm, a 45°, que respeta cada regla más medio ancho de pista y pone las vías respetando las reglas en las dos capas.
- **Sobre lo del usuario:** no se borró nada. En U2, la vía de `AMC_DIAG` se pasó a la diagonal que va a R7 (su pista de Bottom se reconectó) para que `AMC_LDO` saliera del pin 13 por el lugar que dejó. Se reescribieron 4 pistas y 1 vía en su propio registro.
- **GND:**
  - 85 vías de 0,4/0,8 mm (6 de 0,3/0,6 donde no cabía), cada una junto a un pad SMD de GND con una pista de 0,3–0,4 mm de 2,5 mm como máximo.
  - 103 vías de costura cada 7,5 mm donde hay al menos 0,8 mm libres.
  - Polígonos de GND en Top y Bottom de x = 52 al borde derecho (0,5 mm de margen), sólidos, sin cobre muerto y con relieve en los pads. Regla `Poligono_GND` de 0,3 mm.
  - U2.15, C30.2, U3.2, U4.41 y una pata del blindaje de J5 no tienen lugar para una vía y quedan para el polígono de Top.
- **Fiduciales:** anillo de keepout en Top de 1,0 a 2,0 mm alrededor de los tres, para que el polígono no entre a la abertura de máscara (Ø 2 mm).
- **USB:** la regla del par admite 30 mm sin acoplar. El par quedó separado 23 mm entre U5 y D5, y en Full Speed (flancos ≥ 4 ns) eso no importa.
- **Datos borrados:** se vaciaron las conexiones y las violaciones guardadas; Altium las recalcula.

**Pendiente en Altium:**
1. Volver a poner F1B, que se borró de la PCB (quedaron 131 piezas): Design » Update PCB Document y en X = 28,25 mm, Y = 55,6 mm, 270°, igual que F1. Sus pads coinciden con las puntas de `AC_L1` y `AC_L1_F` que ya estaban ruteadas.
2. Tools » Polygon Pours » Repour All.
3. Correr el DRC.

### Después del primer Repour All (22 oct, tarde)

- **Capa V7:** una pista guarda la capa dos veces, en el byte 0 y en la «capa V7» de los bytes 41–44 (`01000001` Top, `ffff0001` Bottom), y Altium lee la segunda. `aplicar_ruteo_f8.py` solo había cambiado el byte 0, así que al abrir y guardar las 15 pistas nuevas de Bottom quedaron en Top (30 cortos). `corregir_capas_f8.py` las devolvió a Bottom y `aplicar_ruteo_f8.py` ya escribe los dos campos.
- **Par USB_D:** el ECO que trajo F1B también borró el par diferencial USB_D, que solo existe en la PCB. Se repuso desde el respaldo. En los próximos ECO hay que desmarcar «Remove Differential Pair USB_D».
- **GND (`terminar_gnd_f8.py`):** el vertido dejó 7 pads de GND sueltos y se unieron con pistas cortas:
  - J5.B1 y dos patas del blindaje, a A12/A1/B12.
  - U4.41 a U4.45/U4.49.
  - U2.15 a una vía propia; para hacerle lugar, la vía de AMC_LDO subió a y = 69,5.
  - U3.2 a C25.2, con una pista de 0,25 mm por un pasillo de 0,73 mm.
  - C30.2 al GND vecino.

  Con el vertido anterior ya forman un solo grupo de 394 objetos, sin vías sueltas.
- **Distancia en el límite:** el arco de `AC_L2_F` alrededor de M1 está centrado en el agujero, a 6,40 mm exactos. Cumple la regla.
- **F1B:** quedó en X = 28,475 mm y va en 28,25 mm, igual que F1.

**Por qué hay vías de costura en grilla:** unen los planos de Top y Bottom en muchos puntos para que GND sea uno solo y de baja impedancia. También dan retorno corto a las señales que cambian de cara, conectan las islas de Top que quedan encerradas entre pistas (sin vía, Altium las borraría como cobre muerto) y bajan el ruido del regulador y de la radio. Van cada 7,5 mm y solo donde hay al menos 0,8 mm libres. Son vías normales de 0,4/0,8 mm tapadas con máscara y no cuestan extra en PCBWay.

### DRC de Altium (22 oct, 15:47 y 16:03)

Las reglas eléctricas (distancias, cortos, anchos, anillos, agujeros, par USB y polígonos) dieron **0 violaciones**. Las 481 y luego 500 que marcó Altium eran estas:

| Regla | Cantidad | Qué era | Arreglo |
|---|---|---|---|
| Silk To Solder Mask | 375 → 417 | Unas 330 eran serigrafía sobre cobre cubierto por máscara (pistas, vías, gotas, polígono), que no es un defecto: `CLEARANCETOEXPOSEDCOPPER=TRUE` comparaba con todo el cobre. Otras 86 eran designadores sobre pads, en su mayoría de la pieza vecina tras mover piezas en el ruteo. 4 son arcos del propio footprint BLX-A sobre sus pads. | La regla ahora compara solo con las aberturas de máscara (`FALSE`). `designadores_f8.py` reubicó 63 designadores; C18 y LED4 quedan para moverlos a mano. Los arcos de F1B/F2B los recorta PCBWay. |
| Minimum Solder Mask Sliver | 82 | Puentes de máscara de menos de 0,1 mm entre pad y vía: las vías tenían la máscara abierta. | Regla `Vias_tapadas` (IsVia, tapada en Top y Bottom). |
| Un-Routed Net + Net Antennae | 1 + 1 | La vía de GND de D5.2 quedaba encerrada en Bottom por el camino de VBUS que bajaba de J5.B4. | `vbus_d5_f8.py`: VBUS baja de A9 por Top a la izquierda de USB_DN y pasa a Bottom debajo de su vía. |
| Board Clearance | 22 → 0 | Designadores fuera del borde (los movió el usuario) y los dibujos de J3, J4, J5 y U4. | Ya no aparecen. |

Que U4 (la antena, por recomendación de Espressif) y J3 (el jack de 3,5 mm del TC, para que entre la clavija) sobresalgan del borde es a propósito. Se avisa en el pedido a PCBWay.
