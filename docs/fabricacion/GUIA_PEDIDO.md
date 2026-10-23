# Guía del pedido — PCBWay y Sigma

Para dejar todo listo y que al final solo falte pagar. Precios y formularios revisados el 22 oct 2026; el 23 oct se quitó DigiKey (ver «Cambio del 23 oct»). Los archivos están en esta carpeta (`docs/fabricacion/`).

**Tiendas:**
- PCBWay, cotización de PCB + ensamble: https://www.pcbway.com/quotesmt.aspx
- Sigma Electrónica (Bogotá), solo lo que va fuera de la placa: parte C

**Por qué en grupo:** PCBWay cobra el envío según el peso de todo el paquete (DHL ≈ US$ 60 solo con las PCB, ≈ US$ 74 con ensamble). Si alguien de la clase pide en la misma cuenta, ese costo se divide.

**Qué se compra dónde:**

| Dónde | Qué | Por qué |
|---|---|---|
| PCBWay | 5 PCB + ensamble de 1 + los 127 componentes que van soldados (K1 incluido) + 2 fusibles de repuesto sueltos | Turnkey: PCBWay compra las piezas con la BOM y las suelda. Lo que no está en LCSC (K1) lo compra en DigiKey o Mouser |
| Sigma | CT, sonda DS18B20 y pila CR2032 (50.813 COP) | Van fuera de la placa. No es urgente: se compran antes de probar |

### Cambio del 23 oct: sin DigiKey

Nadie más del curso pidió en DigiKey y un pedido solo no sale rentable (US$ 100 fijos de envío), así que las líneas de DigiKey se reparten así:

| Línea de DigiKey | Ahora |
|---|---|
| K1 · AQY414EHAX (×2) | **PCBWay lo compra y lo suelda** (1 u.). No está en LCSC, pero PCBWay compra en DigiKey, Mouser y Arrow lo que no tiene ([componentes](https://www.pcbway.com/pcb_prototype/Electronic_Components.html)); puede sumar unos 5–7 días hábiles. DigiKey tenía 570 el 23 oct, a US$ 3,29. Ya no se suelda a mano |
| F1/F2 · fusibles UMT-H de repuesto (×2) | **2 × 3403.0274.11 extra en el pedido de PCBWay**, sueltos con la placa: es el mismo fusible de la placa (LCSC C6384960, 89 en stock el 23 oct). El .23 era el mismo en otro empaque |
| U1 · R-78CK3.3-0.5 de repuesto | No se pide |
| U3 · ATM90E26 de repuesto | No se pide (se puede sumar como extra de PCBWay, LCSC C616398) |

Se revisaron otras opciones para K1 y para el repuesto de los fusibles:
- **K1:** el AQY414EHAX es el único NC con aislamiento reforzado certificado que cabe en el footprint. El SUPSiC GAQY414AEH (NC, LCSC C54938374) cabe, pero no declara aislamiento reforzado ni ninguna certificación. Sigma no tiene ningún PhotoMOS.
- **Plan B, si PCBWay dice que no consigue K1:** el Panasonic AQY214EHAX (LCSC C371971). Es la misma familia, con aislamiento reforzado y el mismo footprint, pero es **NA**: sin energía, el EVSE deja de cargar. Eso invierte lo decidido en P3, así que hay que decidirlo antes de aceptarlo.
- **Fusibles:** Sigma solo tiene fusibles 5×20 que no sirven: el de 1,6 A rápido está agotado, el de 315 mA se funde con el inrush y el de 10 A no protege.

---

## A. PCBWay (PCB + ensamble)

PCBWay solo junta el envío de pedidos que estén **en la misma cuenta**. Una persona del grupo hace todos los pedidos en su cuenta (o el grupo usa una cuenta común) y paga todo junto.

**Hazlo hoy, no mañana:** PCBWay revisa los archivos antes de dejarte pagar (de unas horas a 1–2 días con turnkey, porque revisa la BOM). Mientras tanto el pedido queda en «Under review»; cuando dice «Pass and Payment», ya se puede pagar.

### A0. Generar los archivos finales en Altium (una vez)

El 22 oct en la noche cambiaron tres cosas:
- las esquinas quedaron redondeadas (R 4 mm);
- se agregaron a la serigrafía el bloque con tu nombre, los símbolos de la zona de red y la tarjeta con el QR atrás;
- los textos se agrandaron al mínimo de PCBWay.

Los archivos de `docs/fabricacion/` que había antes son de la placa vieja.

1. Abre `Control de Carga IoT.PrjPcb` y después `EVSE_Monitor.PcbDoc`.
2. **Tools › Polygon Pours › Repour All.** Así desaparecen las puntas rectas de cobre de las esquinas derechas: era el cobre de GND sin volver a verter.
3. Revisa con la tecla **3** (vista 3D) que las cuatro esquinas queden redondas, sin cobre que se salga. Con **V, B** (View › Flip Board) ves la cara de atrás, con la tarjeta del QR. Ahí, escanéalo desde la pantalla con el celular: tiene que abrir nicolasgomez.dev. Con **V, B** otra vez vuelves a la cara de arriba.
4. **Tools › Design Rule Check › Run Design Rule Check.** Debe dar 0 violaciones eléctricas. Los avisos de serigrafía que ya estaban se quedan.
5. **Ctrl+S** para guardar.
6. Abre `Control de Carga IoT.OutJob` y, en cada contenedor de la derecha (PDF y carpetas de salida), haz clic en **Generate Content**, como el 22 oct.
7. Cierra Altium y avísale a Claude. Él corre `paquete_pcbway_f8.py` y `revisar_gerber_f8.py`, que revisa el cobre contra las esquinas redondeadas, el contorno, los taladros, la máscara y la pasta. Después te dice que ya puedes subir.

**Hecho el 22 oct (21:39).** Revisión de los archivos finales:
- contorno con las 4 esquinas en arco;
- nada de cobre fuera del contorno ni en la barrera;
- 304 taladros iguales al PcbDoc;
- máscara: 447 aberturas arriba y 52 abajo, ninguna en vías;
- pasta: 394 aberturas, sin el contacto de BT1;
- GND en un solo grupo y 0 cortos;
- el QR se lee desde el GBO: `HTTPS://NICOLASGOMEZ.DEV`, corrección Q.

Un relleno de la zona de silencio del QR había quedado corrido 0,635 mm (un paso de la grilla) al mover los símbolos en Altium. Se devolvió a su lugar en el PcbDoc (`marcas_f9.py --reponer`) y en el GBO (una coordenada, X155374 → X157874), así que no hubo que volver a correr el OutJob.

**23 oct: otra vez, por BT1 y las gotas.** El usuario giró BT1 90° para que la pila pueda entrar: ahora entra por un lado y a la derecha no hay nada. Por eso rehízo las pistas de `RTC_VBAT`. `gotas_f9.py` encontró dos problemas:
- **El cobre de GND quedó sin volver a verter** y se monta hasta 0,3 mm sobre tres pistas de `RTC_VBAT`. Son las 6 violaciones del DRC: en el Gerber eso sería un corto de la pila a GND.
- **178 de 609 uniones de pista con pad o vía no tienen gota.** Las dos de BT1 son nuevas. Las demás quedaron sin gota desde la primera vez, sobre todo porque Altium tomó el GND ya vertido como obstáculo.

Pasos en Altium, en este orden:
1. Abre el proyecto y `EVSE_Monitor.PcbDoc`.
2. **Tools › Polygon Pours › Shelve 2 Polygons.** Guarda los dos polígonos de GND sin cobre, para que no estorben a las gotas.
3. **Tools › Teardrops…** y llena el cuadro así:
   - Working Mode: **Add**;
   - Objects: **All**;
   - Options: Teardrop style **Curved**, **Force Teardrops sin marcar**, **Adjust Teardrop Size marcado** y Generate report marcado;
   - Scope: marca **Via / TH Pad** y **SMD Pad**, y deja Tracks y T-Junction sin marcar.

   Dale **OK**. El reporte dice cuáles no cupieron: con Force sin marcar, Altium no pone gotas que violen una regla.
4. **Tools › Polygon Pours › Restore 2 Shelved Polygons**, y después **Tools › Polygon Pours › Repour All**. Esto quita el cobre de GND que está encima de las pistas de la pila.
5. **Tools › Design Rule Check › Run Design Rule Check.** Debe dar 0 violaciones de Clearance, sin las 6 de `Poligono_GND`. Marca **Create Report File** para que quede el reporte nuevo.
6. **Ctrl+S**, OutJob (**Generate Content** en cada contenedor), cierra Altium y avísale a Claude.

Como cambian el Gerber y el Pick & Place (BT1 rotado), el pedido que ya está en PCBWay se reemplaza: ver A2.

**Resultado (23 oct, 14:04).** El OutJob se generó después del Repour. Revisión:
- **Gerber:** el cobre de GND queda a ≥ 0,29 mm de las pistas de `RTC_VBAT` (ya no hay corto). El contorno tiene los 4 arcos, no hay cobre fuera ni en la barrera, los 304 taladros coinciden y la máscara y la pasta están bien.
- **QR:** se lee desde el GBO.
- **Pick & Place:** solo cambió BT1, de 0° a 90°.
- **Gotas:** no se aplicaron. Siguen 431 con gota y 178 sin, ni en el PcbDoc ni en el Gerber. No son necesarias para fabricar, así que el paquete se sube así.

### A1. Llenar el formulario

Entra a https://www.pcbway.com y crea la cuenta del grupo o inicia sesión. En *My Account › Shipping address* pon la dirección de Colombia donde llega todo. Después abre https://www.pcbway.com/quotesmt.aspx y llena los campos en este orden (el mismo de la página).

**1. Assembly Service**

| Campo | Qué poner |
|---|---|
| 3 flexible options | **Turnkey** (PCBWay compra las piezas) |
| Board type | **Single pieces** |
| Assembly side(s) | **Top side** |
| Quantity | **1** |
| Contains sensitive components/parts | **Yes**. Se abre una caja: pega el texto de abajo |
| Do you accept alternatives/substitutes made in China? | **No** (que no cambien ningún número de parte de la BOM) |
| Function test | **No** |
| Firmware loading | **No** |

Texto para la caja de **sensitive components** (máximo 500 caracteres; este tiene 170):

```
AHT20 (U6, Aosong humidity and temperature sensor): do not wash after soldering (no water, no ultrasonic cleaning), no conformal coating, do not cover the sensor opening.
```

Solo el AHT20 es sensible: es un sensor de humedad con una ventanita abierta, y el lavado o el barniz lo dañan.

**2. Other Parameters** (clic en **More** a la derecha)

| Campo | Qué poner |
|---|---|
| Number of Unique Parts | **58** (líneas de la BOM que ensambla PCBWay; desde el 23 oct cuenta K1) |
| Number of SMD Parts | **119** (con K1) |
| Number of BGA/QFP Parts | **2**: U3 (ATM90E26, SSOP-28) y U4 (módulo ESP32-S3) |
| Number of Through-Hole Parts | **8**: J1, J2, J4, J5, J6, J7, J8 y PS1 |

El campo «BGA/QFP» no es solo para BGA: PCBWay cuenta ahí todo integrado de más de 16 pines (SOP, QFP, QFN, BGA). En esta placa no hay ningún BGA.

**3. Customized Services and Advanced Options**: no lo abras; todo queda como viene («Select PCBWay's PCB Order#»: No).

**4. Detailed information of assembly**: es la caja de texto grande que está justo debajo de «Customized Services and Advanced Options» y encima de «PCB Specifications». Adentro dice en gris *«Please fill in detailed technical information about the PCB assembly…»*. Acepta **600 caracteres como máximo**; este texto tiene 597 (23 oct: K1 lo pone PCBWay y se piden 2 fusibles extra). Pega esto:

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

Lo mismo va en la columna «Notes» de la BOM, en las filas de K1 y de F1/F2.

**5. PCB Specifications**: **marca la casilla** que está a la izquierda del título (viene **sin marcar**). Así PCBWay fabrica la PCB en el mismo pedido. Se abren estos campos:

| Campo | Qué poner | Nota |
|---|---|---|
| Board type | **Single pieces** | «Panel» es para pedidos de más de 30 placas o placas pequeñas |
| Different design in panel | **1** | |
| Size (single) | **130 × 100** mm | |
| Quantity (single) | **5** | Se fabrican 5, se ensambla 1 y las otras 4 llegan vacías |
| Layers | **2 Layers** | |
| Material | **FR-4** | |
| FR4-TG | **TG 150-160** (viene marcado) | Temperatura a la que el FR-4 se ablanda; 150–160 °C aguanta bien la soldadura sin plomo |
| Thickness | **1.6** | |
| Min track/spacing | **5/5mil** | Mismo precio que 6/6 (revisado). Los pads de J5 están a 0,145 mm (5,7 mil): con 6/6 PCBWay lo marcaría |
| Min hole size | **0.3mm** | |
| Solder mask | **Green** (o Blue / Black, ver abajo) | |
| Silkscreen | **White** | |
| UV printing Multi-color | **None** | |
| Edge connector | **No** | Es para placas con «dedos dorados» que se enchufan en una ranura (como una tarjeta PCIe). Esta no tiene |
| Surface finish | **HASL lead free** | |
| Thickness of Immersion Gold | déjalo en **1U"** como viene | Solo aplica con acabado ENIG (oro) o dedos dorados; con HASL no se usa y no cambia el precio |
| Via process | **Tenting vias** | |
| Finished copper | **1 oz Cu** | |
| Remove product No. | **No** (gratis) | PCBWay imprime un número de pedido pequeño en una zona libre de la serigrafía. «Yes» lo quita por US$ 1,50; «Specify a location» exige poner el texto «WayWayWay» en la serigrafía (no lo tenemos) |
| Other special request | pega el texto de abajo | |

Texto para **Other special request** (lo lee el ingeniero de la PCB; el de arriba lo lee el de ensamble). Tiene 366 caracteres:

```
1. Keep J5 (Wurth 632723300011 USB-C) land pattern as designed: 0.40 mm holes, 0.65 mm pads, 0.6 x 1.2 mm plated slots, 0.145 mm pad gaps.
2. U4, J3 and J5 overhang the top edge on purpose. Outline: GM1 layer, 130 x 100 mm, 4 mm corner radius.
3. All vias tented on both sides.
4. Mains board: x = 45-51.7 mm is an isolation gap. No copper thieving or fill anywhere.
```

**Color de la máscara.** Se puede pedir azul o negra con letras blancas. Lo revisé en la cotización (22 oct, 5 placas de 130 × 100 mm):

| Máscara | Precio | Tiempo de fabricación de la PCB |
|---|---|---|
| Green | US$ 36,87 | 24 h |
| Blue o Black (brillante) | US$ 36,87 | 3–4 días (en 48 h cuesta US$ 61,53) |
| Matte black | US$ 61,53 | 3–4 días |

- El precio no sube con azul o negro brillante, pero la PCB tarda 2–3 días más. Mientras tanto PCBWay compra los componentes, así que parte de esa demora se pierde en la espera, pero cuenta con hasta 3 días más.
- **Negro:** se ve muy bien, pero tapa las pistas. Es difícil seguirlas con la vista, buscar un corto o revisar una soldadura, y en una placa con red eléctrica eso sirve. También se le notan el polvo y las huellas.
- **Azul:** buen punto medio. Las pistas se siguen viendo y el blanco contrasta bien.
- **Verde:** la más rápida y la más fácil de inspeccionar. Es la que dejo por defecto.
- No elijas «Matte black»: cuesta US$ 24,66 más.

**6. Calculate › Save to Cart.** En el carrito sube los archivos que pide cada parte:
- Gerber: `EVSE_Monitor_Gerber.zip`
- BOM: `BOM_PCBWay.xlsx`
- Centroid / Pick and Place: `PickPlace_PCBWay.csv`

Después, **Submit Order Now**. Todavía no se paga: queda en revisión.

**7.** Revisa el correo de la cuenta. PCBWay puede preguntar por piezas que no encuentra, mínimos de compra o el anillo de J5. Contesta sin aceptar cambios de número de parte en U2, U3, U4, K1 ni J5. En la cotización, revisa que K1 aparezca con precio y que los fusibles F1/F2 digan 4 piezas. Si dicen que no consiguen K1, no aceptes un sustituto chino: el plan B (AQY214EHAX, NA) está en «Cambio del 23 oct» y hay que decidirlo antes.

Se ve cómo quedaron los Gerber en el visor de PCBWay (botón «Online Gerber Viewer» del mismo formulario) o en `docs/revisiones/gerber/*.png`.

### A2. Si ya subiste archivos y cambian (23 oct)

Mientras no esté pago, PCBWay deja borrar el pedido o pedirle a tu representante que cambie los Gerber ([cancelar o cambiar un pedido sin pagar](https://www.pcbway.com/helpcenter/checkingorders/How_do_I_cancel_an_order_.html), [actualizar Gerber o BOM de un ensamble](https://www.pcbway.com/helpcenter/pcb_assembly_ordering/How_should_I_do_if_I_want_to_update_Gerber_or_BOM_.html)). Como esta vez cambian el Gerber y el Pick & Place, lo más limpio es:
1. *My PCBWay › Shopping Cart*: borra el pedido viejo con **Delete**.
2. Vuelve a hacer A1 con los archivos nuevos. Son los mismos valores del formulario, y los tres textos están arriba.
3. Si PCBWay ya te escribió por ese pedido, contéstale al correo: *«Please cancel order ___, I submitted a new one with updated files (rotated BT1, teardrops)»*.

### A3. Pagar (el día de la compra)

1. *My PCBWay › Shopping Cart*: los pedidos de todo el grupo tienen que estar en **Pass and Payment**.
2. Marca todos los pedidos del grupo → **Proceed to Checkout**.
3. Shipping method: **DHL** (3–6 días hábiles; FedEx-FICP es más barato y tarda 4–7). Global Standard sale muy barato, pero tarda 10–20 días.
4. Paga con tarjeta. Si alguien del grupo pide algo después, se suma desde **Awaiting Payment › Combine Shipping**.

**Lo de este proyecto:** PCB US$ 36,87 + ensamble US$ 29 + componentes ≈ US$ 67, con K1 y los 2 fusibles de repuesto (PCBWay los confirma al revisar la BOM). El envío se reparte en el grupo. Los impuestos de importación no están incluidos.

### Sobre el ESP32

U4 (ESP32-S3-WROOM-1-N16R2) **no es BGA**: es un módulo con pads en el borde y abajo, que se suelda con pasta y horno como el resto. **PCBWay lo suelda** (va en la BOM como turnkey). El 22 oct LCSC tenía 289 en stock, y PCBWay también compra en otros distribuidores si hace falta.

### Cambio del 22 oct: puntos de prueba

TP1–TP6 eran Keystone 5016, que hoy está en 0 en LCSC. Quedan como **ronghe RH-5016** (LCSC C5199799, 36.015 en stock), que tiene el mismo plano (3,81 × 2,84 mm) y el mismo footprint. PCBWay los suelda igual; no hay que comprarlos aparte. Ya está en la BOM, el Pick & Place y las hojas de Altium.

---

## B. DigiKey: ya no se usa (23 oct)

El carrito común del curso no se hizo: nadie más pidió, y DigiKey cobra US$ 100 fijos de envío a Colombia. K1 y los fusibles de repuesto pasaron al pedido de PCBWay (ver «Cambio del 23 oct», arriba). Ya no hay nada que pegar en Bulk Add.

---

## C. Sigma (Bogotá): fuera de la placa, sin afán

Sí hay que comprarlo, pero **aparte y no ahora**: son accesorios que se conectan a la placa ya hecha, y se necesitan cuando llegue, para probarla. DigiKey no sirve para estos tres:

| Pieza | COP | Por qué no DigiKey |
|---|---:|---|
| CT SCT-013-000 (100 A : 50 mA), para J3: https://www.sigmaelectronica.net/producto/sct-013-000/ | 35.700 | El de DigiKey (Seeed 101990029) no tiene stock hasta el 18 de diciembre |
| Sonda DS18B20 de 2 m, para J4: https://www.sigmaelectronica.net/producto/sen-ds18b20-2m/ | 11.900 | En DigiKey (DFR0198) cuesta US$ 6,90, casi el doble |
| Pila CR2032, para BT1: https://www.sigmaelectronica.net/producto/cr2032/ | 3.213 | DigiKey no manda pilas de litio en avión, y por tierra no llega a Colombia |
| **Total** | **50.813** | |

La sonda y la pila son genéricas: sirven las de cualquier tienda. El CT de Sigma (SKU SCT-013-000V) es el del diseño: YHDC SCT013 de **100 A : 50 mA con salida en corriente** y plug de 3,5 mm, que entra en J3. La carga de 2 × 10 Ω (R11, R13) está en la placa y da 0,5 V a 50 A. No sirve uno de salida en voltaje (los que dicen «30A:1V», por ejemplo). Como todo CT de salida en corriente, no lo dejes abrazando un cable con corriente mientras está desconectado del jack.

## Carrito con casillas

https://claude.ai/artifact/Vf8NPamJJd74KN2qhytMVX. Es privado: para que la clase lo vea, compártelo desde su menú *Share*.
