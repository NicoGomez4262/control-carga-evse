# Guía del pedido en grupo — PCBWay y DigiKey

Para dejar todo listo y que al final solo falte pagar. Precios revisados en las dos tiendas el 22 oct 2026. Los archivos están en esta carpeta (`docs/fabricacion/`).

**Tiendas:**
- PCBWay, cotización de PCB + ensamble: https://www.pcbway.com/quotesmt.aspx
- DigiKey, el PhotoMOS K1: https://www.digikey.com/en/products/detail/panasonic-industry/AQY414EHAX/646365

**Por qué en grupo:** DigiKey cobra **US$ 100 fijos** de envío a Colombia por pedido (DHL, FedEx o UPS), y PCBWay cobra el envío según el peso de todo el paquete (DHL ≈ US$ 60 solo con las PCB, ≈ US$ 74 con ensamble). Juntando a la clase, ese costo se divide.

---

## A. PCBWay (PCB + ensamble)

PCBWay solo junta el envío de pedidos que estén **en la misma cuenta**. Una persona del grupo hace todos los pedidos en su cuenta (o el grupo usa una cuenta común) y paga todo junto.

**Hazlo hoy, no mañana:** PCBWay revisa los archivos antes de dejarte pagar (de unas horas a 1–2 días con turnkey, porque revisa la BOM). Mientras tanto el pedido queda en «Under review»; cuando dice «Pass and Payment», ya se puede pagar.

### A1. Subir el pedido

1. Entra a https://www.pcbway.com y crea la cuenta del grupo o inicia sesión. En *My Account › Shipping address* pon la dirección de Colombia donde llega todo.
2. Abre https://www.pcbway.com/quotesmt.aspx (PCB Assembly). Llena **Assembly Service**:
   - **Turnkey** (PCBWay compra las piezas).
   - Board type: **Single pieces** · Assembly side(s): **Top side** · Quantity: **1**.
   - Contains sensitive components/parts: **Yes**. Va en la nota del paso 5: el AHT20 es un sensor de humedad y no se puede lavar.
   - Do you accept alternatives/substitutes made in China?: **No**.
   - Function test: **No** · Firmware loading: **No**.
3. Abre **Other Parameters** y pon: Number of unique parts **57**, Number of SMD parts **117**, Number of BGA/QFP parts **0**, Number of through-hole parts **9**.
4. En **PCB Specifications** (la casilla ya viene marcada):
   - Board type: **Single pieces** · Size: **130 × 100 mm** · Quantity: **5**. Se fabrican 5 PCB, se ensambla 1 y las otras 4 llegan vacías.
   - Layers **2** · FR-4 · TG por defecto (PCBWay sube gratis a S1000H TG150).
   - Thickness **1.6** · Min track/spacing **6/6 mil** · Min hole size **0.3 mm**.
   - Solder mask **Green** · Silkscreen **White** · Edge connector **No**.
   - Surface finish **HASL lead free** · Via process **Tenting vias** · Finished copper **1 oz**.
   - Remove product No.: **No**. PCBWay imprime su número en la serigrafía; quitarlo cuesta US$ 1,50.
5. En **Detailed information of assembly** pega este texto:

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
6. **Calculate** › **Save to Cart**. En el carrito, sube los archivos que pide cada parte:
   - Gerber: `EVSE_Monitor_Gerber.zip`
   - BOM: `BOM_PCBWay.xlsx`
   - Centroid / Pick and Place: `PickPlace_PCBWay.csv`

   Después, **Submit Order Now**. Todavía no se paga: queda en revisión.
7. Revisa el correo de la cuenta. PCBWay puede preguntar por piezas que no encuentra, mínimos de compra o el anillo de J5. Contesta sin aceptar cambios de número de parte en U2, U3, U4, K1 ni J5.

Se ve cómo quedaron los Gerber en el visor de PCBWay (botón «Online Gerber Viewer» del mismo formulario) o en `docs/revisiones/gerber/*.png`.

### A2. Pagar (el día de la compra)

1. *My PCBWay › Shopping Cart*: los pedidos de todo el grupo tienen que estar en **Pass and Payment**.
2. Marca todos los pedidos del grupo → **Proceed to Checkout**.
3. Shipping method: **DHL** (3–6 días hábiles; FedEx-FICP es más barato y tarda 4–7). Global Standard sale muy barato, pero tarda 10–20 días.
4. Paga con tarjeta. Si alguien del grupo pide algo después, se suma desde **Awaiting Payment › Combine Shipping**.

**Lo de este proyecto:** PCB US$ 36,87 + ensamble US$ 29 + componentes ≈ US$ 60 (PCBWay los confirma al revisar la BOM). El envío se reparte en el grupo. Los impuestos de importación no están incluidos.

---

## B. DigiKey (carrito común del curso)

Lo de este proyecto en DigiKey es solo K1, el PhotoMOS AQY414EHAX: **2 unidades** (una de repuesto) a US$ 3,29 = **US$ 6,58**. Hoy hay 570 en stock.

### B1. Si tú armas el carrito y lo compartes

1. Entra a https://www.digikey.com con tu cuenta, con país **Colombia** (bandera arriba a la derecha) y moneda **USD**.
2. Abre https://www.digikey.com/en/products/detail/panasonic-industry/AQY414EHAX/646365. Pon Quantity **2**, deja **Cut Tape (CT)** (no Digi-Reel, que cobra US$ 7) y haz clic en **Add to Cart**.
3. Abre el carrito (ícono arriba a la derecha). En **Customer Reference** de la línea escribe `Nicolas EVSE K1`. DigiKey lo imprime en la bolsita, así cada quien sabe qué es suyo cuando llegue la caja.
4. Arriba a la derecha del carrito, haz clic en **Share Copy**. DigiKey crea un enlace con una copia del carrito. Ese enlace es el que mandas a la clase.

### B2. Si otra persona arma el carrito del curso

Pásale esta línea. En su carrito, en **Bulk Add** («One product per line…»), la pega y le da **Add to Cart**:

```
2,255-6089-1-ND,Nicolas EVSE K1
```

(cantidad, número de parte de DigiKey y referencia; también está en `DigiKey_bulk_add.txt`).

### B3. Pagar

Quien paga revisa el total (el envío a Colombia son US$ 100 fijos para todo el carrito), pone la dirección y paga con tarjeta. Los impuestos dependen del valor total del pedido del curso.

---

## C. Sigma (Bogotá) — lo que va fuera de la placa

No es parte del pedido del grupo. Se compra aparte:
- CT SCT-013-000V, 35.700 COP: https://www.sigmaelectronica.net/producto/sct-013-000/
- Sonda DS18B20 2 m, 11.900 COP: https://www.sigmaelectronica.net/producto/sen-ds18b20-2m/
- Pila CR2032, 3.213 COP: https://www.sigmaelectronica.net/producto/cr2032/

## Carrito con casillas

https://claude.ai/artifact/Vf8NPamJJd74KN2qhytMVX. Es privado: para que la clase lo vea, compártelo desde su menú *Share*.
