# Pedido a PCBWay — EVSE Monitor Rev 1.0 (F8)

Archivos (en esta carpeta; los arma `docs/tools/paquete_pcbway_f8.py` con lo que genera el OutJob):

| Archivo | Para qué |
|---|---|
| `EVSE_Monitor_Gerber.zip` | Fabricación: Top/Bottom Layer, Overlay, Solder, Paste, Mechanical 1 (contorno) y taladros PTH/NPTH (Excellon, pulgadas 2:5) |
| `BOM_PCBWay.xlsx` | Ensamble: 61 líneas, 126 piezas para PCBWay (118 SMD + 8 THT), 2 a mano y 4 sin montar |
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
| Unique parts / SMD / BGA-QFP / THT | 57 · 118 · 2 (U3 SSOP-28, U4 módulo ESP32-S3; PCBWay cuenta ahí todo integrado de más de 16 pines) · 8 (J1, J2, J4, J5, J6, J7, J8, PS1) |
| Parts by PCBWay | Todas las de la BOM marcadas «PCBWay» (proveedor LCSC) |
| Customer parts | Ninguna consignada: K1 (DigiKey) y U1 (ya disponible) se sueldan a mano |
| Fiducials | 3 (FID1–FID3) |
| Stencil | Incluido con el ensamble |

J3 tiene 2 huecos de 1,8 mm sin anillo de cobre, que son para sus pines plásticos: es SMD.

## Notas para PCBWay

**Detailed information of assembly** (formulario de ensamble):

```
1. Do not modify J5 (Wurth 632723300011 USB-C) land pattern: 0.40 mm holes with 0.65 mm pads (0.125 mm
   annular ring) and 0.6 x 1.2 mm plated slots, as specified by the manufacturer.
2. U4 (ESP32-S3 antenna), J3 (3.5 mm jack) and J5 overhang the top board edge on purpose. Please keep them.
3. All vias are tented (covered with solder mask) on both sides.
4. Mains-voltage board: the strip x = 45-51.7 mm is an isolation gap with no copper. Please do not add copper
   thieving or fill anywhere.
5. Assembly on top side only. Do not place K1 and U1 (customer will hand-solder). DNP: F1B, F2B, SW2, SW3.
6. BT1 center pad (battery contact) has no solder paste on purpose.
7. Sensitive part: U6 (AHT20 humidity sensor). No washing or ultrasonic cleaning after soldering, no coating.
8. Assemble 1 board; ship the other 4 PCBs bare.
```

**Other special request** (PCB Specifications):

```
1. Do not modify J5 (Wurth 632723300011 USB-C) land pattern: 0.40 mm holes with 0.65 mm pads, 0.6 x 1.2 mm
   plated slots and 0.145 mm gaps between its SMD pads, as specified by the manufacturer.
2. U4, J3 and J5 overhang the top board edge on purpose. Board outline: Mechanical 1 layer (GM1), 130 x 100 mm.
3. All vias are tented (covered with solder mask) on both sides.
4. Mains-voltage board: the strip x = 45-51.7 mm is an isolation gap with no copper. Please do not add copper
   thieving or fill anywhere.
```

**Sensitive components** (la caja que se abre con «Yes», máx. 500 caracteres):

```
AHT20 (U6, Aosong humidity and temperature sensor): do not wash after soldering (no water, no ultrasonic cleaning), no conformal coating, do not cover the sensor opening.
```

Piezas a mano después: K1 (AQY414EHAX, DigiKey 255-6089-1-ND) con 2 mm libres alrededor para el cautín, y U1 (RECOM R-78CK3.3-0.5, THT).
