# Carrito total — EVSE Monitor (F8)

Precios al 22 de octubre de 2026; TRM 3.191,47 COP/USD. Página interactiva con casillas: ver el enlace en `NEXT_SESSION.md`. Generado por `docs/tools/carrito_f8.py`.

| Proveedor | US$ | COP |
|---|---:|---:|
| PCBWay (PCB, ensamble, componentes, envío, arancel estimado) | 186,23 | 594.347 |
| DigiKey (carrito del curso) | 17,87 | 57.032 |
| Sigma Electrónica | 15,92 | 50.813 |
| **Total** | **220,02** | **702.192** |

## PCBWay

| Concepto | Detalle | Cant. | US$ c/u | US$ |
|---|---|---:|---:|---:|
| Fabricación de la PCB | 2 capas, FR-4 1,6 mm, 1 oz, HASL sin plomo, 130 × 100 mm, vías tapadas | 5 | 7,37 | 36,87 |
| Ensamble turnkey (1 placa) | Una cara: 57 referencias, 118 SMD + 8 THT, 2 BGA/QFP (U3, U4); el stencil se cotiza con el ensamble | 1 | 29,00 | 29,00 |
| Componentes que compra PCBWay (1 placa) | 126 piezas de LCSC, detalle abajo | 1 | 59,02 | 59,02 |
| Envío DHL a Colombia | 0,5 kg: US$ 74,41 menos US$ 30 de descuento (cotización del 22 oct); en el pedido del grupo se divide | 1 | 44,41 | 44,41 |
| Arancel de importación (estimado) | 10 % sobre mercancía + envío; si el valor declarado pasa de US$ 200 se suma IVA 19 % | 1 | 16,93 | 16,93 |

## DigiKey (carrito del curso, ≤ US$ 40)

| Concepto | Detalle | Cant. | US$ c/u | US$ |
|---|---|---:|---:|---:|
| K1 · PhotoMOS AQY414EHAX (Panasonic) | 255-6089-1-ND · se suelda a mano (570 en stock) | 1 | 3,29 | 3,29 |
| K1 de repuesto (recomendado) | 255-6089-1-ND · por si se daña al soldar | 1 | 3,29 | 3,29 |
| Repuesto F1/F2 · fusible UMT-H T1A (Schurter 3403.0274.23) | 486-3065-1-ND · el mismo de la placa, en cinta; si uno se funde se cambia sin los portafusibles F1B/F2B | 2 | 3,03 | 6,06 |
| Repuesto U1 · RECOM R-78CK3.3-0.5 | 945-R-78CK3.3-0.5-ND · por si se daña el del profesor | 1 | 3,57 | 3,57 |
| Repuesto U3 · medidor ATM90E26-YU-R (Microchip) | ATM90E26-YU-RCT-ND · el chip del lado de la red, el que más se arriesga en las pruebas | 1 | 1,66 | 1,66 |

## Sigma Electrónica (Bogotá)

| Concepto | Detalle | Cant. | COP c/u | COP |
|---|---|---:|---:|---:|
| CT de J3 · YHDC SCT-013-000V | 100 A : 50 mA (20 u. en stock). En DigiKey (Seeed 101990029) no hay hasta el 18 de diciembre | 1 | 35.700 | 35.700 |
| Sonda de J4 · DS18B20 de 2 m | SEN DS18B20 2M (43 u. en stock). En DigiKey (DFR0198) cuesta US$ 6,90 | 1 | 11.900 | 11.900 |
| Pila de BT1 · CR2032 | 13 u. en stock. DigiKey no la manda a Colombia: las pilas de litio solo van por tierra | 1 | 3.213 | 3.213 |

Ya disponible, no se compra: U1 (RECOM R-78CK3.3-0.5, la del profesor).

Por qué DigiKey trae tan poco: los otros 126 componentes de la placa los compra PCBWay con la BOM y llegan soldados (línea «Componentes que compra PCBWay»). En DigiKey va solo K1, que PCBWay no consigue, más repuestos.

Supuestos: el precio de PCBWay es el del cotizador del 20 oct (el final sale al revisar los archivos); los componentes turnkey usan el precio de LCSC por unidad (PCBWay puede cobrar mínimos de compra en pasivos); el envío y el arancel son estimados.

Pedido en grupo: el envío de PCBWay se divide entre quienes pidan en la misma cuenta (el total es el máximo, como si se pidiera solo) y DigiKey cobra US$ 100 fijos de envío a Colombia por todo el carrito del curso (tu parte no está sumada). Paso a paso: `docs/fabricacion/GUIA_PEDIDO.md`.
