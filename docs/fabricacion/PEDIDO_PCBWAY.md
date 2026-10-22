# Pedido a PCBWay — EVSE Monitor Rev 1.0 (F8)

Archivos (en esta carpeta; los arma `docs/tools/paquete_pcbway_f8.py` con lo que genera el OutJob):

| Archivo | Para qué |
|---|---|
| `EVSE_Monitor_Gerber.zip` | Fabricación: Top/Bottom Layer, Overlay, Solder, Paste, Mechanical 1 (contorno) y taladros PTH/NPTH (Excellon, pulgadas 2:5) |
| `BOM_PCBWay.xlsx` | Ensamble: 61 líneas, 126 piezas para PCBWay (117 SMD + 9 THT), 2 a mano y 4 sin montar |
| `PickPlace_PCBWay.csv` | Ensamble: posiciones en mm (solo las piezas que ensambla PCBWay) |
| `Ensamble_EVSE_Monitor.pdf` | Plano de ensamble (cara superior) |

## Formulario de la PCB

| Campo | Valor |
|---|---|
| Layers | 2 |
| Size | 130 × 100 mm |
| Quantity | 5 |
| Material / Tg | FR-4, TG130–140 |
| Thickness | 1.6 mm |
| Min track/spacing | 6/6 mil. Los pads de J5 (USB-C) están a 0,145 mm, que es el patrón de Würth; si PCBWay lo marca, 5/5 mil |
| Min hole size | 0.3 mm |
| Solder mask / Silkscreen | Verde / blanco |
| Surface finish | HASL lead free |
| Via process | Tenting vias |
| Finished copper | 1 oz (ambas caras) |
| Edge connector / castellated | No |

## Notas para PCBWay (pegar en «Remark»)

```
1. Do not modify J5 (Wurth 632723300011 USB-C) land pattern: 0.40 mm holes with 0.65 mm pads (0.125 mm
   annular ring) and 0.6 x 1.2 mm plated slots, as specified by the manufacturer.
2. U4 (ESP32-S3 antenna), J3 (3.5 mm jack) and J5 overhang the top board edge on purpose. Please keep them.
3. All vias are tented (covered with solder mask) on both sides.
4. Mains-voltage board: the strip x = 45-51.7 mm is an isolation gap with no copper. Please do not add copper
   thieving or fill anywhere.
5. Assembly on top side only. Do not place K1 and U1 (customer will hand-solder). DNP: F1B, F2B, SW2, SW3.
6. BT1 center pad (battery contact) has no solder paste on purpose.
```

## Formulario de ensamble (turnkey)

| Campo | Valor |
|---|---|
| Assembly side | Top |
| Quantity | 1 (o 2 si el precio lo justifica) |
| Unique parts / SMD / THT | 57 referencias · 117 SMD · 9 THT (J1, J2, J3, J4, J5, J6, J7, J8, PS1) |
| Parts by PCBWay | Todas las de la BOM marcadas «PCBWay» (proveedor LCSC) |
| Customer parts | Ninguna consignada: K1 (DigiKey) y U1 (ya disponible) se sueldan a mano |
| Fiducials | 3 (FID1–FID3) |
| Stencil | Incluido con el ensamble |

Piezas a mano después: K1 (AQY414EHAX, DigiKey 255-6089-1-ND) con 2 mm libres alrededor para el cautín, y U1 (RECOM R-78CK3.3-0.5, THT).
