# Pedido a PCBWay — EVSE Monitor Rev 1.0 (F8)

Archivos (en esta carpeta; los arma `docs/tools/paquete_pcbway_f8.py` con lo que genera el OutJob):

| Archivo | Para qué |
|---|---|
| `EVSE_Monitor_Gerber.zip` | Fabricación: Top/Bottom Layer, Overlay, Solder, Paste, Mechanical 1 (contorno) y taladros PTH/NPTH (Excellon, pulgadas 2:5) |
| `BOM_PCBWay.xlsx` | Ensamble: 61 líneas, 127 piezas para PCBWay (119 SMD + 8 THT), 1 a mano (U1) y 4 sin montar. Desde el 23 oct K1 lo compra y lo suelda PCBWay, y F1/F2 piden 2 fusibles de repuesto |
| `PickPlace_PCBWay.csv` | Ensamble: posiciones en mm (solo las piezas que ensambla PCBWay); la columna Comment lleva el MPN de la BOM |
| `Ensamble_EVSE_Monitor.pdf` | Plano de ensamble (cara superior) |

Paso a paso del pedido en grupo, con cada campo del formulario en el orden de la página: `GUIA_PEDIDO.md`.

## Formulario de la PCB (PCB Specifications)

| Campo | Valor |
|---|---|
| Board type | Single pieces |
| Layers | 2 |
| Size | 130 × 100 mm |
| Quantity | 5 |
| Material / Tg | FR-4, TG 150-160 (el que viene) |
| Thickness | 1.6 mm |
| Min track/spacing | 5/5 mil: mismo precio que 6/6 (22 oct) y cubre los pads de J5 a 0,145 mm (5,7 mil) |
| Min hole size | 0.3 mm |
| Solder mask / Silkscreen | Verde / blanco (azul o negro brillante: mismo precio, la PCB tarda 3–4 días en vez de 24 h) |
| Edge connector | No |
| Surface finish | HASL lead free (Thickness of Immersion Gold no aplica: se deja 1U") |
| Via process | Tenting vias |
| Finished copper | 1 oz (ambas caras) |
| Remove product No. | No (Yes cuesta US$ 1,50) |

## Formulario de ensamble (turnkey)

| Campo | Valor |
|---|---|
| Assembly side | Top |
| Quantity | 1 |
| Sensitive components | Yes: U6 (AHT20) |
| Alternatives made in China | No |
| Unique parts / SMD / BGA-QFP / THT | 58 · 119 · 2 (U3 SSOP-28, U4 módulo ESP32-S3; PCBWay cuenta ahí todo integrado de más de 16 pines) · 8 (J1, J2, J4, J5, J6, J7, J8, PS1) |
| Parts by PCBWay | Todas las de la BOM marcadas «PCBWay»: de LCSC, menos K1, que PCBWay compra en DigiKey o Mouser. F1/F2: 4 fusibles, 2 de repuesto sueltos |
| Customer parts | Ninguna consignada: solo U1 (ya disponible) se suelda a mano |
| Fiducials | 3 (FID1–FID3) |
| Stencil | Incluido con el ensamble |

J3 tiene 2 huecos de 1,8 mm sin anillo de cobre, que son para sus pines plásticos: es SMD.

## Notas para PCBWay

**Detailed information of assembly** (formulario de ensamble):

```
1. Top side only. Do not place U1 (customer hand-solders). DNP: F1B, F2B, SW2, SW3.
2. K1 AQY414EHAX is not in LCSC: please buy it from DigiKey 255-6089-1-ND or Mouser and place it. No substitutes.
3. F1/F2: buy 2 extra 3403.0274.11 and ship them loose with the boards.
4. Keep J5 land pattern as designed (0.125 mm annular ring, plated slots).
5. U4, J3 and J5 overhang the board edge on purpose.
6. BT1 center pad: no paste on purpose.
7. U6 (AHT20 sensor): no washing, no coating.
8. All vias tented. No copper fill in x = 45-51.7 mm (isolation gap).
9. Assemble 1 board; ship the other 4 bare.
```

**Other special request** (PCB Specifications):

```
1. Keep J5 (Wurth 632723300011 USB-C) land pattern as designed: 0.40 mm holes, 0.65 mm pads, 0.6 x 1.2 mm plated slots, 0.145 mm pad gaps.
2. U4, J3 and J5 overhang the top edge on purpose. Outline: GM1 layer, 130 x 100 mm, 4 mm corner radius.
3. All vias tented on both sides.
4. Mains board: x = 45-51.7 mm is an isolation gap. No copper thieving or fill anywhere.
```

**Sensitive components** (la caja que se abre con «Yes», máx. 500 caracteres):

```
AHT20 (U6, Aosong humidity and temperature sensor): do not wash after soldering (no water, no ultrasonic cleaning), no conformal coating, do not cover the sensor opening.
```

Pieza a mano después: U1 (RECOM R-78CK3.3-0.5, THT). K1 (AQY414EHAX) ya no va a mano: desde el 23 oct lo compra y lo suelda PCBWay (no hay pedido de DigiKey).
