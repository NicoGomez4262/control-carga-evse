# Guía del pedido en grupo — PCBWay y DigiKey

Para dejar todo listo y que al final solo falte pagar. Precios y formularios revisados en las dos tiendas el 22 oct 2026. Los archivos están en esta carpeta (`docs/fabricacion/`).

**Tiendas:**
- PCBWay, cotización de PCB + ensamble: https://www.pcbway.com/quotesmt.aspx
- DigiKey: https://www.digikey.com (la lista para pegar está en la parte B)

**Por qué en grupo:** DigiKey cobra **US$ 100 fijos** de envío a Colombia por pedido (DHL, FedEx o UPS), y PCBWay cobra el envío según el peso de todo el paquete (DHL ≈ US$ 60 solo con las PCB, ≈ US$ 74 con ensamble). Juntando a la clase, ese costo se divide.

**Qué se compra dónde:**

| Dónde | Qué | Por qué |
|---|---|---|
| PCBWay | 5 PCB + ensamble de 1 + los 126 componentes que van soldados | Turnkey: PCBWay compra las piezas con la BOM y las suelda. No hay que comprarlas aparte |
| DigiKey | K1 y repuestos (US$ 17,87) | K1 (AQY414EHAX) es lo único de la placa que PCBWay no consigue. Lo demás son repuestos |
| Sigma | CT, sonda DS18B20 y pila CR2032 (50.813 COP) | Van fuera de la placa y DigiKey no los tiene o no los envía. No es urgente: se compran antes de probar |

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
| Number of Unique Parts | **57** (líneas de la BOM que ensambla PCBWay) |
| Number of SMD Parts | **118** |
| Number of BGA/QFP Parts | **2**: U3 (ATM90E26, SSOP-28) y U4 (módulo ESP32-S3) |
| Number of Through-Hole Parts | **8**: J1, J2, J4, J5, J6, J7, J8 y PS1 |

El campo «BGA/QFP» no es solo para BGA: PCBWay cuenta ahí todo integrado de más de 16 pines (SOP, QFP, QFN, BGA). En esta placa no hay ningún BGA.

**3. Customized Services and Advanced Options**: no lo abras; todo queda como viene («Select PCBWay's PCB Order#»: No).

**4. Detailed information of assembly**: es la caja de texto grande que está justo debajo de «Customized Services and Advanced Options» y encima de «PCB Specifications». Adentro dice en gris *«Please fill in detailed technical information about the PCB assembly…»*. Acepta **600 caracteres como máximo**; este texto tiene 516. Pega esto:

```
1. Top side only. Do not place K1, U1 (customer hand-solders). DNP: F1B, F2B, SW2, SW3.
2. Keep J5 (Wurth 632723300011) land pattern as designed: 0.125 mm annular ring and plated slots per manufacturer.
3. U4, J3 and J5 overhang the board edge on purpose.
4. BT1 center pad: no paste on purpose.
5. U6 (AHT20 humidity sensor): no washing, no ultrasonic cleaning, no coating.
6. All vias tented. Mains board: no copper thieving or fill (x = 45-51.7 mm is an isolation gap).
7. Assemble 1 board; ship the other 4 bare.
```

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

**7.** Revisa el correo de la cuenta. PCBWay puede preguntar por piezas que no encuentra, mínimos de compra o el anillo de J5. Contesta sin aceptar cambios de número de parte en U2, U3, U4, K1 ni J5.

Se ve cómo quedaron los Gerber en el visor de PCBWay (botón «Online Gerber Viewer» del mismo formulario) o en `docs/revisiones/gerber/*.png`.

### A2. Pagar (el día de la compra)

1. *My PCBWay › Shopping Cart*: los pedidos de todo el grupo tienen que estar en **Pass and Payment**.
2. Marca todos los pedidos del grupo → **Proceed to Checkout**.
3. Shipping method: **DHL** (3–6 días hábiles; FedEx-FICP es más barato y tarda 4–7). Global Standard sale muy barato, pero tarda 10–20 días.
4. Paga con tarjeta. Si alguien del grupo pide algo después, se suma desde **Awaiting Payment › Combine Shipping**.

**Lo de este proyecto:** PCB US$ 36,87 + ensamble US$ 29 + componentes ≈ US$ 59 (PCBWay los confirma al revisar la BOM). El envío se reparte en el grupo. Los impuestos de importación no están incluidos.

### Sobre el ESP32

U4 (ESP32-S3-WROOM-1-N16R2) **no es BGA**: es un módulo con pads en el borde y abajo, que se suelda con pasta y horno como el resto. **PCBWay lo suelda** (va en la BOM como turnkey). El 22 oct LCSC tenía 289 en stock, y PCBWay también compra en otros distribuidores si hace falta.

### Cambio del 22 oct: puntos de prueba

TP1–TP6 eran Keystone 5016, que hoy está en 0 en LCSC. Quedan como **ronghe RH-5016** (LCSC C5199799, 36.015 en stock), que tiene el mismo plano (3,81 × 2,84 mm) y el mismo footprint. PCBWay los suelda igual; no hay que comprarlos aparte. Ya está en la BOM, el Pick & Place y las hojas de Altium.

---

## B. DigiKey (carrito común del curso, cupo de US$ 40)

**Por qué es tan poco:** los 126 componentes que van soldados los compra PCBWay con la BOM. DigiKey solo trae lo que PCBWay no consigue (K1) y unos repuestos de lo que más se puede dañar en las pruebas con la red. Revisé el 22 oct otras piezas que podrían ir de repuesto: el AMC3330 (U2) no tiene stock en DigiKey hasta el 29 oct.

| Línea | DigiKey PN | Cant. | US$ c/u | US$ | Para qué |
|---|---|---:|---:|---:|---|
| K1 · Panasonic AQY414EHAX | 255-6089-1-ND | 2 | 3,29 | 6,58 | El relé de la placa (se suelda a mano) y uno de repuesto |
| F1/F2 · Schurter UMT-H T1A 3403.0274.23 | 486-3065-1-ND | 2 | 3,03 | 6,06 | Repuesto de los fusibles: el mismo de la placa, en cinta (PCBWay pone el .11, en bolsa) |
| U1 · RECOM R-78CK3.3-0.5 | 945-R-78CK3.3-0.5-ND | 1 | 3,57 | 3,57 | Repuesto del regulador del profesor |
| U3 · Microchip ATM90E26-YU-R | ATM90E26-YU-RCT-ND | 1 | 1,66 | 1,66 | Repuesto del medidor (el chip del lado de la red) |
| | | | **Total** | **17,87** | Sobran US$ 22 del cupo |

Todas son en **Cut Tape (CT)**, no Digi-Reel (que cobra US$ 7 más).

### B1. Si tú armas el carrito y lo compartes

1. Entra a https://www.digikey.com con tu cuenta, con país **Colombia** (bandera arriba a la derecha) y moneda **USD**.
2. Abre el carrito (ícono arriba a la derecha). En la caja **Bulk Add** («One product per line…») pega esto y haz clic en **Add to Cart**:

   ```
   2,255-6089-1-ND,Nicolas EVSE K1
   2,486-3065-1-ND,Nicolas EVSE F1 F2 repuesto
   1,945-R-78CK3.3-0.5-ND,Nicolas EVSE U1 repuesto
   1,ATM90E26-YU-RCT-ND,Nicolas EVSE U3 repuesto
   ```

   Cada línea es cantidad, número de parte de DigiKey y **Customer Reference**. DigiKey imprime la referencia en cada bolsita, así cada quien sabe qué es suyo cuando llegue la caja. (También está en `DigiKey_bulk_add.txt`.)
3. Revisa que queden 4 líneas y **US$ 17,87**. Si alguna no entra (al ATM90E26 le pasó el 22 oct), agrégala en **Manual Entry**, debajo de la lista: Quantity `1`, Part Number `ATM90E26-YU-RCT-ND`, Customer Reference y **Add to Cart**. También se puede desde su página, https://www.digikey.com/en/products/detail/microchip-technology/ATM90E26-YU-R/4899918, con **Cut Tape (CT)** y cantidad 1. Ese día tenía 8.729 en stock, a US$ 1,66.
4. Arriba a la derecha del carrito, haz clic en **Share Copy**. DigiKey crea un enlace con una copia del carrito. Ese enlace es el que mandas a la clase.

### B2. Si otra persona arma el carrito del curso

Pásale las 4 líneas de arriba para que las pegue en su **Bulk Add**.

### B3. Pagar

Quien paga revisa el total (el envío a Colombia son US$ 100 fijos para todo el carrito), pone la dirección y paga con tarjeta. Los impuestos dependen del valor total del pedido del curso.

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
