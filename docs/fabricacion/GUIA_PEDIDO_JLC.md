# Pedido en JLCPCB — EVSE Monitor Rev 1.0

**30 oct 2026 (D20).** PCBWay podía tardar más de un mes y la clase va a pedir en JLCPCB, así que el pedido pasa a JLC. **La PCB no cambia:** se suben los mismos Gerber del 23 oct. Cambia la BOM: K1 pasa a AQY214EHAX y 11 líneas genéricas pasan a piezas «Basic» de JLC. Todo lo demás está en el stock de ensamble de JLC (revisado el 30 oct con `paquete_jlc_f9.py --stock`).

## Archivos

| Archivo | Qué es |
|---|---|
| `EVSE_Monitor_Gerber.zip` | Gerber y taladros del 23 oct (los mismos de PCBWay). Origen en la esquina inferior izquierda, 130 × 100 mm |
| `BOM_JLC.csv` | 58 líneas: Comment (MPN), Designator, Footprint, JLCPCB Part # |
| `CPL_JLC.csv` | 127 piezas: Designator, Mid X, Mid Y, Layer, Rotation (centro de pads, mismo origen que los Gerber) |

Se regeneran con `python docs/tools/paquete_jlc_f9.py --stock`, que también vuelve a revisar el stock.

No se ensamblan: U1 (R-78CK3.3-0.5, a mano), F1B/F2B y SW2/SW3 (DNP).

## Qué cambió frente a PCBWay

| Qué | Antes (PCBWay) | Ahora (JLC) | Por qué |
|---|---|---|---|
| K1 | AQY414EHAX (NC), comprado en DigiKey/Mouser | **AQY214EHAX (NA)**, LCSC C371971, 938 en stock | El AQY414EHAX está en 0 y por Global Sourcing tarda 9–15 días. Misma familia, mismo footprint y aislamiento reforzado de 5000 Vrms |
| 11 líneas genéricas | Yageo RC0805, Samsung CL21B, onsemi MMBT3904LT1G | UNI-ROYAL 0805W8F, Yageo CC0805, Samsung CL21B105KBFNNNE, CJ MMBT3904 | Son «Basic»: no pagan los US$ 3,07 por referencia extendida. Misma especificación o mejor |
| Placas ensambladas | 1 | **2** (mínimo de JLC) | La segunda queda de repuesto. U1 hay solo una: va en la primera |
| Fusibles de repuesto | 2 sueltos | ninguno | La segunda placa ya trae F1 y F2 |

**Ojo con K1 (AQY214EHAX, NA):** sin energía o mientras la ESP32 arranca (`RELAY_EN` en bajo por R40), el contacto queda **abierto** y el EVSE **no carga**. El firmware pone `RELAY_EN` en alto para permitir la carga. LED6 encendido = **carga permitida**. Si más adelante consigues el AQY414EHAX, se cambia a mano sin tocar nada más.

## Paso 1 · PCB (jlcpcb.com → Order now → Add gerber file)

Sube `EVSE_Monitor_Gerber.zip`. JLC lee 130 × 100 mm y 2 capas. En el visor de Gerber de JLC, revisa que se vean las dos caras como en `docs/revisiones/gerber/*.png`: el contorno con esquinas redondeadas, el QR atrás y el hueco de la barrera, sin cobre.

| Campo | Valor | Nota |
|---|---|---|
| Base Material | FR-4 | |
| Layers | 2 | |
| Dimensions | 130 × 100 mm | lo detecta del GM1 |
| PCB Qty | 5 | |
| Product Type | Industrial/Consumer electronics | |
| Different Design | 1 | |
| Delivery Format | Single PCB | |
| PCB Thickness | 1.6 mm | |
| PCB Color | **Green** | el más rápido |
| Silkscreen | White | |
| Material Type | FR4 TG135 (el estándar) | |
| Surface Finish | **LeadFree HASL** | |
| Outer Copper Weight | 1 oz | |
| Via Covering | **Tented** | todas las vías van tapadas |
| Min via hole size/diameter | 0.3 mm / (0.4/0.45 mm), el que viene | nuestras vías son de 0,3/0,6 y 0,4/0,8 mm |
| Board Outline Tolerance | ±0.2 mm (Regular) | |
| Mark on PCB / Remove Order Number | la opción gratis | JLC imprime un número pequeño en una zona libre de la serigrafía; es tinta, no afecta la barrera |
| Electrical Test | Flying Probe Fully Test | |
| Gold Fingers, Castellated Holes, Edge Plating | No | |
| Confirm Production File | **Yes** | para ver dónde ponen los agujeros de herramienta antes de fabricar |

## Paso 2 · Ensamble (PCB Assembly → activar)

| Campo | Valor | Nota |
|---|---|---|
| PCBA Type | **Economic** | una cara, SMD y THT, se arma en 1–3 días; no pide rieles ni fiduciales |
| Assembly Side | Top Side | todo va arriba |
| PCBA Qty | **2** | mínimo de JLC |
| Tooling holes | Added by JLCPCB | JLC agrega 2–3 agujeros sin cobre de 1,152 mm en esquinas opuestas. Con «Confirm Production File» los ves antes |
| Confirm Parts Placement | **Yes** | JLC te manda la ubicación final de cada pieza para aprobarla. Responde rápido: el pedido espera tu respuesta |

Después: **Next** → sube `BOM_JLC.csv` y `CPL_JLC.csv`. Si pregunta por las columnas, asigna Comment, Designator, Footprint y JLCPCB Part # en la BOM, y Designator, Mid X, Mid Y, Layer y Rotation en el CPL.

## Paso 3 · Revisar la BOM en JLC

- Las 58 líneas tienen que salir **confirmadas** con el código de la columna «JLCPCB Part #» y sin «shortfall».
- Que no aparezca ninguna pieza sin asignar. U1, F1B, F2B, SW2 y SW3 no están en la BOM: es a propósito.
- Las THT que JLC suelda a mano: J1, J2, J4, J6, J7, J8 y PS1. J5 tiene patas THT de anclaje.
- Conteo esperado: 16 líneas Basic y 42 extendidas.

## Paso 4 · Revisar la ubicación (Component Placements)

JLC dibuja cada pieza de su librería sobre nuestros pads. La rotación del CPL es la de Altium, y la librería de JLC no siempre tiene el mismo cero: **revisa cada pieza con polaridad o pin 1** y, si una sale girada, gírala ahí mismo con el botón de rotar hasta que el pin 1 o la marca coincida con la serigrafía.

| Piezas | Qué mirar |
|---|---|
| C2, C3 | lado «+» del electrolítico sobre el pad 1 (marca + de la serigrafía) |
| D1, D2, D3 | franja del cátodo sobre el lado marcado en la serigrafía (D4 es bidireccional) |
| D5, D6 | pin 1 del USBLC6-2SC6 (punto) |
| LED1–LED6 | cátodo sobre la marca de cátodo |
| Q1, Q2, Q3 | las 3 patas sobre los 3 pads (el SOT-23 solo calza de dos formas; mira el pin 1) |
| U2, U3, U5, U7 | pin 1 (punto o bisel) sobre la marca de pin 1 |
| U4 | antena hacia el borde superior, sobresaliendo |
| U6 (AHT20), Y1 | pin 1 |
| K1 | pin 1 = ánodo del LED, del lado del SELV (derecha de la barrera) |
| BT1 | polo + según la serigrafía |
| J3, J5 | la boca hacia el borde superior |
| **J1, J2, J4, J6, J7 (borneras)** | **la entrada de los cables hacia afuera de la placa**: tienen pines simétricos y se pueden soldar al revés |
| PS1 | sus pines solo calzan de una forma; revisa que el cuerpo quede dentro del contorno de la serigrafía |

Si quieres, haz este paso con Claude en el navegador del panel: entras a tu cuenta y lo revisamos pieza por pieza.

## Paso 5 · Cotización y envío

- Revisa el total del ensamble: Economic, 2 placas, piezas ≈ US$ 118, cargo de extendidas 42 × 3,07 ≈ US$ 129, más setup US$ 8,18, stencil US$ 1,53 y soldadura.
- Envío: **DHL Express o FedEx** (3–6 días a Colombia). Si la clase usa una sola cuenta, los pedidos pueden ir juntos en un envío y se divide el costo.
- Arancel en Colombia: si el valor declarado pasa de US$ 200, se paga IVA del 19 % además del arancel. Cuenta con eso en el presupuesto.

## Paso 6 · DFM: respuestas si JLC pregunta

| Pregunta de JLC | Respuesta |
|---|---|
| Anillo de los agujeros de J5 menor de 0,18 mm (0,40 mm de agujero, pad de 0,65 mm) o pads a 0,145 mm | *Keep J5 (Wurth 632723300011, your part C2830802) land pattern as designed. Do not enlarge pads.* |
| U4, J3 y J5 sobresalen del borde superior | *Intentional: the ESP32 antenna, the audio jack and the USB-C overhang the top edge.* |
| Zona sin cobre entre x = 45 y 51,7 mm | *Isolation gap between mains and low voltage. No copper fill or thieving there.* |
| Dónde poner los agujeros de herramienta | En cualquier esquina sin cobre ni piezas; lejos de los pads de J1 y de la zona de red |
| Sustituir una pieza | Solo si es el mismo MPN (por ejemplo, otro empaque). K1 no se cambia por otro modelo |

## Paso 7 · Pagar

Lo haces tú. Después, anota el número de pedido en `NEXT_SESSION.md`.

## Lo que sigue igual

- **Sigma** (antes de las pruebas): CT SCT-013-000V, sonda DS18B20 de 2 m y pila CR2032.
- U1 (R-78CK3.3-0.5 del profesor) se suelda a mano en la primera placa.
- Pruebas por etapas: primero 12 V por J6, con la red solo a través de un transformador de aislamiento (lista en `NEXT_SESSION.md`).
