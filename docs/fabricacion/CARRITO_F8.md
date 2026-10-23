# Carrito total — EVSE Monitor (F8)

Precios al 23 de octubre de 2026; TRM 3.181,01 COP/USD. Página interactiva con casillas: ver el enlace en `NEXT_SESSION.md`. Generado por `docs/tools/carrito_f8.py`.

| Proveedor | US$ | COP |
|---|---:|---:|
| PCBWay (PCB, ensamble, componentes, envío, arancel estimado) | 195,51 | 621.919 |
| Sigma Electrónica | 15,97 | 50.813 |
| **Total** | **211,48** | **672.732** |

## PCBWay

| Concepto | Detalle | Cant. | US$ c/u | US$ |
|---|---|---:|---:|---:|
| Fabricación de la PCB | 2 capas, FR-4 1,6 mm, 1 oz, HASL sin plomo, 130 × 100 mm, vías tapadas | 5 | 7,37 | 36,87 |
| Ensamble turnkey (1 placa) | Una cara: 58 referencias, 119 SMD + 8 THT, 2 BGA/QFP (U3, U4); el stencil se cotiza con el ensamble | 1 | 29,00 | 29,00 |
| Componentes que compra PCBWay (1 placa) | 127 piezas (de LCSC; K1 lo compra PCBWay en DigiKey o Mouser) + 2 fusibles de repuesto, detalle abajo | 1 | 67,46 | 67,46 |
| Envío DHL a Colombia | 0,5 kg: US$ 74,41 menos US$ 30 de descuento (cotización del 22 oct); en el pedido del grupo se divide | 1 | 44,41 | 44,41 |
| Arancel de importación (estimado) | 10 % sobre mercancía + envío; si el valor declarado pasa de US$ 200 se suma IVA 19 % | 1 | 17,77 | 17,77 |

## Sigma Electrónica (Bogotá)

| Concepto | Detalle | Cant. | COP c/u | COP |
|---|---|---:|---:|---:|
| CT de J3 · YHDC SCT-013-000V | 100 A : 50 mA (20 u. en stock). En DigiKey (Seeed 101990029) no hay hasta el 18 de diciembre | 1 | 35.700 | 35.700 |
| Sonda de J4 · DS18B20 de 2 m | SEN DS18B20 2M (43 u. en stock). En DigiKey (DFR0198) cuesta US$ 6,90 | 1 | 11.900 | 11.900 |
| Pila de BT1 · CR2032 | 13 u. en stock. DigiKey no la manda a Colombia: las pilas de litio solo van por tierra | 1 | 3.213 | 3.213 |

Ya disponible, no se compra: U1 (RECOM R-78CK3.3-0.5, la del profesor).

Sin DigiKey (23 oct): nadie más del curso pidió. K1 (AQY414EHAX, en 0 en LCSC) lo compra PCBWay en DigiKey o Mouser y lo suelda; los 2 fusibles de repuesto van sueltos en el mismo pedido. Los repuestos de U1 y U3 no se piden.

Supuestos: el precio de PCBWay es el del cotizador del 20 oct (el final sale al revisar los archivos); los componentes turnkey usan el precio de LCSC por unidad (PCBWay puede cobrar mínimos de compra en pasivos); el envío y el arancel son estimados.

Pedido en grupo: el envío de PCBWay se divide entre quienes pidan en la misma cuenta (el total es el máximo, como si se pidiera solo). Paso a paso: `docs/fabricacion/GUIA_PEDIDO.md`.
