# Decisiones del proyecto

## Registro

| ID | Fecha | Decisión | Estado | Fase |
|---|---|---|---|---|
| D1 | 2026-10-02 | Arquitectura Rev A: medición aislada (ZMPT101B + CT), IC de medición ATM90E26, ESP32-S3, relé G5RL y contactor externo | propuesta; el contactor lo reemplaza D7 y el ZMPT101B lo reemplaza D9; el resto se confirma en su fase | — |
| D2 | 2026-10-06 | El riel de 3.3 V usa el RECOM R-78CK3.3-0.5 disponible (reemplaza el LDO de Rev A) | adoptada | F2 |
| D3 | 2026-10-06 | La fuente AC-DC será un módulo de PCB certificado, no un cargador de celular; preferencia por salida de 12 V | adoptada (2026-10-07): **Mean Well IRM-20-12** de Sigma y riel `+VIN` de 12 V (ver «Fase 2») | F2 |
| D4 | 2026-10-06 | Proyecto jerárquico en Altium, 8 fases, una hoja por bloque | adoptada | F1 |
| D5 | 2026-10-06 | Compras en Sigma Electrónica; ensamble automático en PCBWay de lo que tenga en stock; el resto se suelda a mano | reemplazada por D16 | F7–F8 |
| D6 | 2026-10-06 | Mouser es el proveedor de última opción: solo para piezas que no estén en Sigma ni en el stock de ensamble de PCBWay y sin equivalente disponible en ellos; un solo pedido consolidado | reemplazada por D16 (DigiKey) | F2–F8 |
| D7 | 2026-10-06 | Sin contactor: la carga se habilita o detiene con un contacto seco (relé) en la entrada de habilitación del EVSE; la placa solo mide la corriente | adoptada; reemplaza el contactor de D1 | F1, F6 |
| D8 | 2026-10-06 | Conectividad: la ESP32 abre una conexión saliente cifrada (TLS) hacia el servidor de la app del usuario, sube datos y recibe órdenes por ella; sin VPN ni puertos abiertos. Las protecciones funcionan sin internet. Reemplaza «app web local, sin nube» | adoptada | F1, F4, F5 |
| D9 | 2026-10-06 | Medición de tensión con divisor resistivo + amplificador aislado TI AMC3330 (reemplaza al ZMPT101B de D1) | adoptada | F3 |
| D10 | 2026-10-06 | Librerías: `SamacSys.SchLib/PcbLib` (Library Loader) usadas directamente como librería del proyecto; `EVSE.SchLib/PcbLib` solo para piezas hechas a mano. Parámetros con los nombres de SamacSys (`Manufacturer_Name`, `Manufacturer_Part_Number`) más `Supplier`, `Supplier PN`, `Assembly`, `Value` y `Description`, puestos en la librería. Altium Designer 25.4.2 | adoptada | F1–F8 |
| D11 | 2026-10-06 | Conexión jerárquica: Net Identifier Scope «Hierarchical (sheet entry ↔ port, power ports global)»; rieles con puertos de alimentación globales, señales y líneas de red con entradas de hoja; parámetros `ProjectName`, `Revision`, `DrawnBy` solo a nivel de proyecto (los de la hoja tienen prioridad y se borran) | adoptada | F1 |
| D12 | 2026-10-06 | Proyecto de Altium en `C:/Nicolas/UNIVERSIDAD - 2026/Hardware en IoT/Control de Carga IoT/Control de Carga IoT/Control de Carga IoT.PrjPcb`; ProjectName «Control de Carga IoT», Revision 0.1. La documentación y los PDF de revisión siguen en este repositorio | adoptada | F1 |
| D13 | 2026-10-09 | Programación de la ESP32-S3 con puente USB-UART (DTR y RTS) y circuito de auto-reset de dos NPN hacia EN y GPIO0, para no depender de pulsadores (requisito del profesor; imagen en `docs/referencias/F4_autoprogramacion_profesor.jpg`) | adoptada como requisito; componentes en F4 | F4 |
| D14 | 2026-10-12 | Sin FRAM: el búfer sin internet (P5) va en la flash de 16 MB del ESP32 (partición de datos) y la energía acumulada de la sesión se guarda en NVS cada minuto y al empezar o terminar la sesión. Con internet los datos ya están en el servidor a los pocos segundos; lo peor es perder ≤ 1 min de energía (≈ 0,16 kWh a 40 A/240 V) si se va la luz estando sin internet. El RTC con pila se mantiene para fechar mediciones cuando vuelve la luz sin internet | adoptada | F5 |
| D15 | 2026-10-12 | K1 = PhotoMOS AQY414EHAX (NC, aislamiento reforzado de 5000 Vrms) en lugar de un relé: no tiene carga mínima (la entrada de un EVSE genérico es de pocos mA), es NC sin energía (P3) y cuesta US$3,42 en Mouser; el relé dorado no está en Mouser (Phoenix, US$22). Salida: ≤ 120 mA, ≤ 400 V pico; si los bornes resultan ser de red, se pone un relé externo | adoptada | F6 |
| D16 | 2026-10-19 | Compras: PCB en PCBWay con ensamble turnkey de todo lo que tenga en stock; lo que falte, en DigiKey (carrito ≤ US$50 que se suma al pedido conjunto del curso; consignado a PCBWay o soldado a mano); Sigma solo como último recurso; Mouser deja de usarse (reemplaza D5 y D6). Esta versión es PCB desnuda: el gabinete queda para la próxima versión y no es tarea | adoptada | F7–F8 |
| D17 | 2026-10-19 | BOM de F7: **una placa ensamblada**. Todo lo que PCBWay tiene (stock en LCSC) llega soldado, también los THT (PS1, J1, J2, J4, J6–J8); lo que PCBWay no tiene se compra en DigiKey y se suelda a mano (solo K1, AQY414EHAX); U1 es el R-78CK del profesor, a mano; CT, sonda y pila en Sigma (DigiKey sin stock o sin envío aéreo). Sustitutos por stock: AMC3330DWER, 3403.0274.11, XY301V-A-5.0-2P (J1, J2), Murata LQH43NH120J03L (L1), Ruilon RL4032P471KJ (RV1), Murata GRM31C5C1H104JA01L (C16) y GRM3195C1H333JA01D (C20, C23), Yageo RT0805BRD0710RL (R11, R13) | adoptada | F7 |

## D2 · Verificación del R-78CK3.3-0.5

- **Fabricante y número de parte:** RECOM Power, `R-78CK3.3-0.5` (serie R-78CK-0.5). El código `215071V15` impreso en la pieza no es el número de parte; parece ser el lote de fabricación.
- **Datasheet:** https://recom-power.com/pdf/Innoline/R-78CK-0.5.pdf
- **Distribuidores:** [DigiKey](https://www.digikey.com/en/products/detail/recom-power/R-78CK3-3-0-5/21284863) · [Mouser](https://www.mouser.com/ProductDetail/RECOM-Power/R-78CK3.3-0.5?qs=Imq1NPwxi74a1HN1pJq5mQ%3D%3D)

| Parámetro | Datasheet | Lo que necesita el proyecto | ¿Cumple? |
|---|---|---|---|
| Entrada | 5–40 VDC; UVLO: enciende a 4.4 V, apaga a 4.3 V | 12 V o 5 V del AC-DC | sí; con 5 V no se puede poner un diodo en serie |
| Salida | 3.3 V ±3 %, 500 mA | ESP32-S3: 3.0–3.6 V; Espressif pide fuente de ≥ 500 mA | sí, justo |
| Carga estimada | — | ≈ 0.15–0.2 A promedio; ≈ 0.38 A de pico (WiFi transmitiendo) | sí, 75 % en el pico |
| Eficiencia a plena carga | 91 % con 5 V, 72 % con 40 V; ≈ 85 % con 12 V (curva) | — | sí |
| Rizado y ruido | 50 mVpp (20 MHz, plena carga, con 10 µF MLCC a la salida; datasheet Rev. 1-2025). La cifra anterior de «10 % de Vout» era errónea | alimentación limpia para ADC y radio | sí; el filtro LC lo baja a pocos mV |
| Frecuencia de conmutación | 800 kHz | — | se filtra con facilidad |
| Protecciones | cortocircuito continuo con recuperación automática; apagado térmico | — | sí |
| Temperatura | −40 a +100 °C; plena carga hasta ≈ 100 °C con 5–9 V de entrada | caja cerrada | sí |
| Carga capacitiva máxima | 2000 µF | bulk y filtro de salida | sí |
| Certificación | IEC/EN 62368-1 | — | sí |
| Encapsulado | SIP3 THT, 11.5 × 7.55 × 10.2 mm; pines 1 Vin, 2 GND, 3 Vout (como un LM78xx) | — | soldadura manual |
| Notas del fabricante | 27 µF electrolítico en Vin con conexión en caliente o Vin > 18 V; filtro EMI clase B: RLS-126 + 10 µF + 1 nF | — | incluir en F2 |

**Conclusión:** sirve. Condiciones para F2: la entrada nunca baja de 5 V en sus pines (por eso se prefiere 12 V), filtro LC a la salida (recomendado; con 50 mVpp de rizado ya no es obligatorio) más una ferrita para `+3V3A`, y la bobina del relé se alimenta de `+VIN`, nunca de 3.3 V.

## D3 · Candidatos de fuente AC-DC (se comparan en F2)

Precios y stock de Sigma Electrónica consultados el 6 oct 2026.

| Opción | Salida | Entrada | Dónde | Precio (COP) | Nota |
|---|---|---|---|---|---|
| Mean Well IRM-20-12 | 12 V, 1.8 A | 85–305 VAC según la hoja de datos de nov 2025 (la ficha de Sigma dice 85–264) | Sigma, 19 unidades | 71.400 | preferida: 12 V y calidad Mean Well; sobrada en potencia; 52.4 × 27.2 × 24 mm |
| Mean Well IRM-10-5 | 5 V, 2 A | 85–305 VAC | Sigma, 16 unidades | 49.980 | el R-78CK queda en su mínimo de 5 V |
| Hi-Link HLK-PM12 | 12 V, 0.25 A (3 W) | 90–264 VAC | Sigma, 21 unidades | 19.992 | económica; margen corto; requiere protección externa |
| Mean Well IRM-05-12 / IRM-10-12 | 12 V, 0.42 / 0.85 A | 85–305 VAC | importación | — | tamaño justo; no está en Sigma |
| Cargador de celular | 5 V USB | 100–240 VAC | — | — | solo para pruebas de banco |

Fuentes: [IRM-20](https://www.meanwell.com/Upload/PDF/IRM-20/IRM-20-SPEC.PDF) · [IRM-10](https://www.meanwell.com/Upload/PDF/IRM-10/IRM-10-SPEC.PDF) · [IRM-05](https://www.meanwell.com/Upload/PDF/IRM-05/IRM-05-SPEC.PDF) · [Sigma: fuentes conmutadas](https://www.sigmaelectronica.net/categoria-producto/fuentes/fuentes-conmutadas/) · [Sigma: HLK-PM12](https://www.sigmaelectronica.net/producto/hlk-pm12/)

## Preguntas abiertas

Las siete primeras cambian el esquemático y se responden en F1.

| ID | Pregunta | Respuesta | Fecha |
|---|---|---|---|
| P1 | ¿Servicio 120/208 V o 120/240 V? ¿Hay neutro y tierra en el punto de carga? | Diseño universal: de 120 V monofásico (L–N) a 240 V bifásico (L1–L2); rango 100–264 VAC. Llega un tercer conductor marcado N; falta confirmar si es neutro o tierra. Ver «Respuestas de la Fase 1» | 2026-10-06 |
| P2 | Marca, modelo y corriente del EVSE. ¿Tiene entrada de habilitación, Modbus u OCPP? | EVSE genérico con 2 bornes de habilitación (cerrados = carga, abiertos = para). El relé que maneja la ESP32 cierra o abre esos bornes; no hay contactor. Medición de 0–50 A | 2026-10-06 |
| P3 | ¿El relé corta la potencia, habilita el EVSE o ambas cosas? | Solo habilita el EVSE (P2/D7). F6: EVSE genérico; tensión de los bornes desconocida (se diseña para 250 VAC); corriente desconocida (de ~2 mA a cientos de mA); **sin energía debe cargar → contacto NC** (K1 = PhotoMOS AQY414EHAX, D15, J2 de 2 polos). F7 (profesor): los bornes son una entrada lógica tipo interruptor (baja tensión, pocos mA o menos según el pull-up); unidos = carga, separados = para | 2026-10-06 / 2026-10-12 / 2026-10-14 |
| P4 | ¿Dónde se instala el dispositivo y en qué tipo de caja? | Caja plástica independiente junto al EVSE, bajo techo; cable de alimentación largo hasta la línea. Gabinete e IP se definen en F7 según los requisitos del profesor | 2026-10-06 |
| P5 | ¿Acceso solo en la red local o también desde internet (VPN)? | Por internet, sin VPN: la ESP32 se conecta por WiFi al router y envía los datos a la base de datos de una app propia; los usuarios entran desde el celular con cuenta. Ver D8 | 2026-10-06 |
| P6 | ¿La ESP debe calcular la potencia a partir de muestras (ADS131M02) o basta un IC de medición (ATM90E26)? | IC de medición: ATM90E26 como base, se compara con ADE7953 en F3 | 2026-10-06 |
| P7 | ¿Es obligatorio el divisor resistivo (divisor + AMC3330) o se usa ZMPT101B? | Divisor resistivo + AMC3330 (aislamiento reforzado certificado, SMD). Reemplaza al ZMPT101B. Ver D9 | 2026-10-06 |
| P8 | Precisión objetivo (clase 1 = ±1 % en energía) | pendiente | |
| P9 | Tras un corte de luz, ¿la sesión se reanuda sola o queda en pausa? | pendiente | |
| P10 | ¿Dónde va la sonda 1-Wire y qué temperatura máxima acepta el EVSE? | pendiente | |
| P11 | Fabricación: 2 o 4 capas, ensamble en PCBWay y soldadura manual de THT | parcialmente resuelta (D5) | 2026-10-06 |
| P12 | Interfaz local (LEDs, botón de parar, pantalla) y número de usuarios de la app | pendiente | |

## Respuestas de la Fase 1

### P1 · Servicio eléctrico (2026-10-06)

**Respuesta:** el diseño debe funcionar tanto en 120 V monofásico (fase–neutro) como en 240 V bifásico (fase–fase). En el punto de carga llegan L1, L2 y un tercer conductor marcado N; no se sabe si es neutro o tierra.

**Decisiones que salen de aquí:**

- Rango de entrada de la placa: **100–264 VAC, 50/60 Hz** (120 V − 15 % a 240 V + 10 %). La zona de red deja de ser «208–240 VAC» y pasa a «120–240 VAC».
- J1 se conecta a los dos conductores que alimentan el EVSE: L1 + L2 (240 V) o L + N (120 V). Se mantienen los nombres `AC_L1` y `AC_L2`; en 120 V, `AC_L2` es el neutro (anotarlo en la serigrafía de J1: «L1/L» y «L2/N»).
- La placa no usa neutro ni tierra. La tierra entra a la placa solo si la caja es metálica (se decide con P4).
- Las distancias no cambian: se diseña para el peor caso (240 V + 10 %).

**Pendientes para otras fases:**

- **F2:** AC-DC de entrada universal (los IRM de Mean Well cubren el rango). El varistor se elige para 264 VAC con margen. Fusible: en 120 V el borne `AC_L2` es el neutro, así que se decide si se protege solo `AC_L1` o las dos líneas con fusibles que no dejen la placa energizada si abre solo uno.
- **F3:** resistencia serie del ZMPT101B calculada para 264 VAC; a 120 V la señal queda en ≈ 45 % de la escala. Verificar resolución y calibración en los dos casos.
- **F6:** la bobina del contactor se alimenta de la misma red, así que se elige una bobina de 120 V, una de 240 V o una de rango amplio.

**Verificación en la instalación (seguridad):** el EVSE necesita conductor de tierra de protección. Con el multímetro no se distingue neutro de tierra (se unen en el tablero principal); hay que revisar el color (RETIE: neutro blanco; tierra verde, verde-amarillo o desnuda) y a qué barra llega en el tablero. Si es neutro y no hay tierra, la instalación se corrige antes de conectar el cargador.

### P2 · EVSE y forma de control (2026-10-06)

**Respuesta:** EVSE genérico, sin modelo definido. Quien permite o detiene la carga es el EVSE: tiene dos bornes de habilitación en la parte superior; si están unidos permite la carga y si están separados la detiene. Esa decisión la toma un relé controlado por la ESP32. El dispositivo no corta ni conduce la corriente de carga.

**Decisiones que salen de aquí (D7):**

- **Se elimina el contactor externo 2P 40 A** del Rev A y, con él, el snubber de la bobina y la elección de bobina de 120/240 V que había quedado para F6 en P1.
- **J2 = salida de contacto seco** hacia los bornes de habilitación del EVSE. La hoja ACTUACION ya no recibe `AC_L1_F` ni `AC_L2_F`.
- **Una sola señal de mando:** `RELAY_EN` (MCU → ACTUACION, con pull-down). La red `EVSE_EN` desaparece.
- **Corriente:** el CT solo mide. Rango de medición genérico de 0–50 A (cubre nivel 1 a 120 V y nivel 2 de hasta 40 A a 240 V); se cierra en F3.
- Modbus y OCPP no aplican (no se agrega RS-485).

**Pendientes para F6:**

- El contacto maneja unos mA a 5–12 V: un relé de potencia (G5RL, AgSnO₂) no es confiable con esa carga mínima. Comparar un relé de señal con contactos dorados y aislamiento reforzado contra un PhotoMOS (AQY212EH o similar), revisando la carga mínima de contacto en el datasheet.
- En un EVSE genérico no se sabe a qué potencial está la entrada de habilitación, así que J2 se trata como circuito externo: aislamiento reforzado y creepage ≥ 6.4 mm hacia el lado SELV.

### P3 · Contacto del relé (2026-10-06)

**Respuesta:** la pregunta original quedó resuelta en P2 (el relé solo habilita el EVSE). Falta definir el comportamiento sin energía (NA: sin energía el EVSE no carga; NC: sin energía carga normal); el usuario consultará el modelo del EVSE.

**Decisión provisional:** relé con contacto conmutado (1C) y J2 de 3 bornes (COM, NA, NC), de modo que cualquiera de los dos comportamientos se elige con el cableado sin cambiar la placa. No afecta la TOP.

**Pendiente antes de F6:** modelo del EVSE y su manual, para conocer la tensión y corriente en los bornes de habilitación, la lógica (cerrado = carga) y si la entrada es SELV. Con eso se elige NA o NC, el relé (contactos dorados o PhotoMOS) y se confirma el aislamiento de J2.

**Respuesta en F6 (2026-10-12):** sigue siendo un EVSE genérico. La tensión entre los bornes es desconocida, así que se diseña para el peor caso (hasta 250 VAC, J2 como circuito externo con aislamiento reforzado). La corriente también es desconocida; el usuario la averiguará más adelante, y mientras tanto el contacto debe servir desde señales de ~2 mA (contactos dorados) hasta cientos de mA. Sin energía el EVSE debe **cargar normal**: se usa el contacto **NC** (relé en reposo = COM–NC cerrado = carga habilitada; para parar se energiza la bobina). J2 conserva los 3 bornes, con el orden 1 NC, 2 COM y 3 NA, para cambiar a NA solo con el cableado. Consecuencia: si la placa se apaga o la ESP32 se reinicia, la carga queda habilitada y la placa no puede cortar por temperatura (quedan las protecciones del EVSE); el firmware debe restaurar el estado de `RELAY_EN` desde NVS al arrancar.

**Respuesta del profesor en F7 (2026-10-14):** los bornes de habilitación son un interruptor sobre una entrada del EVSE, así que no se espera más tensión que la de una entrada lógica; la corriente con los bornes unidos es de unos pocos mA o menos, según la resistencia de pull-up; unidos permiten la carga y separados la detienen. No dijo si es DC o AC; para K1 da igual, porque la salida del AQY414EHAX es AC/DC (dos MOSFET en antiserie).

Consecuencias:
- K1 = AQY414EHAX queda confirmado: no tiene carga mínima (un contacto de relé de potencia no sería confiable con pocos mA); 120 mA y 400 V sobran. Con Ron ≤ 35 Ω y unos mA, la caída es de 0,1–0,2 V (la entrada lee «cerrado»). Con la salida abierta, la fuga es de ≤ 10 µA: con un pull-up de 10 kΩ son 0,1 V, y con uno de 100 kΩ, 1 V (la entrada lee «abierto»).
- Ya no hace falta el relé externo «si los bornes son de red»; queda solo como nota por si el EVSE real resulta distinto.
- J2 se sigue tratando como circuito externo con aislamiento reforzado (`EVSE_EXT`, ≥ 6,4 mm hacia el SELV): no cuesta nada y el dato del profesor no es una medición del equipo real.

### P4 · Ubicación y caja (2026-10-06)

**Respuesta:** caja plástica independiente junto al EVSE, en un punto de carga bajo techo. El cable de alimentación hasta la línea debe ser largo. El gabinete y su grado IP se definen después, según los requisitos del profesor.

**Decisiones que salen de aquí:**

- Diseño **clase II**: caja plástica, la placa no lleva tierra de protección (J1 de 2 polos). Si el profesor exige caja metálica, se agrega un borne de PE y se revisa.
- Antena integrada en el módulo ESP32-S3 (la caja plástica no bloquea el WiFi); la antena externa (WROOM-1U) deja de ser necesaria, aunque se compara en F4.
- Conectores J1 a J4 en un mismo borde, con prensaestopas: J1 hacia la línea (cable largo), CT, J2 a los bornes de habilitación del EVSE y J4 a la sonda.

**Seguridad del cable largo de J1:** el cable que alimenta el dispositivo debe quedar protegido en su origen. Opciones: breaker pequeño (2–6 A) o portafusible en el tablero exclusivo para el dispositivo, o un cable del calibre que exige el breaker del EVSE. El fusible de la placa no protege ese cable. La caída de tensión no importa (consumo de mA).

**Pendiente para F7:** gabinete (2–3 opciones) según los requisitos del profesor; bajo techo basta IP54.

### P5 · Acceso y conectividad (2026-10-06)

**Respuesta:** la ESP32 se conecta por WiFi al router y sube los datos a una base de datos dentro de una aplicación que hará el usuario; cualquier celular entra con un enlace y una cuenta, y desde ahí da órdenes. Cada usuario tiene su control de acceso.

**Decisión (D8):** modelo IoT con conexión saliente. La ESP32 inicia una conexión cifrada (TLS) hacia el servidor de la app (por ejemplo MQTT o WebSocket), envía mediciones y recibe órdenes por ese mismo canal. No hace falta VPN ni abrir puertos en el router; la VPN solo era necesaria en el modelo anterior, en el que la ESP servía la página web. Reemplaza «app web local, sin nube».

**Requisitos que salen de aquí:**

- Las protecciones (corte por temperatura, fallas de medición) se deciden localmente en la ESP32 y funcionan sin internet; la app informa y manda órdenes.
- Sin internet, las mediciones se guardan con la hora del RTC y se suben al volver la conexión (refuerza RTC y memoria en F5).
- Credencial única por dispositivo y TLS; actualización de firmware por OTA.
- Página local mínima solo para configurar el WiFi la primera vez (modo punto de acceso activado con un botón).
- F4: preferir el módulo ESP32-S3 N16R8 (16 MB de flash, 8 MB de PSRAM) por TLS, OTA y búfer de datos.

### P6 · Cálculo de potencia (2026-10-06)

**Respuesta:** IC de medición dedicado. La ESP32 solo lee registros por SPI; la medición no depende del firmware ni compite con WiFi/TLS (P5).

**Para F3:** ATM90E26 (Microchip, SSOP-28, en producción; 0.1 % en energía activa sobre 5000:1 de rango dinámico según el fabricante) como base, comparado con ADE7953 (Analog Devices). Revisar stock en PCBWay y Sigma, y Mouser como última opción. Fuentes: [DigiKey ATM90E26-YU-R](https://www.digikey.com/en/products/detail/microchip-technology/ATM90E26-YU-R/4899918) · [datasheet](https://www.radiolocman.com/datasheet/pdf.html?di=128209) (en F3 se baja la versión oficial a `docs/datasheets/`).

### P7 · Medición de tensión (2026-10-06)

**Respuesta:** divisor resistivo + AMC3330.

**Por qué (D9):** el AMC3330 tiene aislamiento reforzado certificado (6000 Vpk según DIN EN IEC 60747-17 / VDE 0884-17; 4250 Vrms durante 1 min según UL1577), error de ganancia ±0.2 % máx., no linealidad ±0.02 % máx. y no tiene desfase de transformador; es SMD y lo ensambla PCBWay. El ZMPT101B solo declara 4000 V de prueba sin certificación de aislamiento reforzado y no aparece en Sigma. Un divisor directo al ATM90E26 no está permitido (dejaría el SELV referenciado a la red). Fuentes: [TI AMC3330](https://www.ti.com/product/AMC3330) · [datasheet ZMPT101B](https://www.electroniclinic.com/wp-content/uploads/2023/07/ZMPT101B-datasheet.pdf).

**Para F3:**

- Lado de baja tensión alimentado desde 3.3 V del lado SELV; el DC/DC integrado alimenta el lado de red. Seguir el desacople y el layout del datasheet (el DC/DC es fuente de ruido y EMI).
- Divisor en la zona de red: cadena de resistencias de alta tensión en serie (tensión de trabajo y creepage por resistencia) que lleva 264 V + 10 % (≈ 410 Vpk) a menos de ±1 V; referencia del lado de red a `AC_L2_F`.
- Adaptar la salida diferencial del AMC3330 a la entrada de tensión del ATM90E26.
- Proveedor: no está en Sigma; PCBWay (turnkey) o Mouser como última opción.
- Bajar el datasheet oficial a `docs/datasheets/` y verificar el creepage del encapsulado contra la regla de 6.4 mm.

## Cierre de la Fase 1 (2026-10-07)

- Arquitectura **Rev C**: sin contactor (D7), conexión a internet (D8), divisor + AMC3330 (D9), red de 100–264 VAC (P1), riel de 12 V preferido.
- Proyecto de Altium creado (D12), jerárquico, con la TOP conectada según la tabla de interfaces Rev C de `docs/PLAN_FASES.md`; valida con 0 errores.
- Pendientes heredados: modelo del EVSE (P3, antes de F6), tercer conductor N/PE en la instalación (P1), gabinete según el profesor (P4, F7), bloque de título con `*` (F7), copiar SamacSys al proyecto (F7), PDF recortado (inicio de F2).

## Fase 2 — Alimentación

Cálculos en `docs/calculos/F2_ALIMENTACION.md`.

### Fuente AC-DC y riel de 12 V (2026-10-07)

Presupuesto de potencia en el pico: `+3V3` ≈ 417 mA (83 % del R-78CK) y `+VIN` ≈ 175 mA (2.1 W), con reservas para el relé, el IC de medición y los sensores.

| | IRM-20-12 (elegida) | HLK-PM12 | IRM-10-12 |
|---|---|---|---|
| Salida | 12 V, 1.8 A | 12 V, 0.25 A | 12 V, 0.85 A |
| Uso en el pico | 10 % | 70 % | 21 % |
| Entrada | 85–305 VAC | 85–265 VAC | 85–305 VAC |
| Aislamiento E/S | 4.2 kVAC; IEC/UL 62368-1 e IEC 61558 | 3 kVAC declarado, sin certificado verificable | 4.2 kVAC; IEC/UL 62368-1 |
| Surge EN 61000-4-5 | 2 kV L–N (nivel 4) | sin dato | 1 kV L–N (nivel 3) |
| Inrush en frío | 20 A/115 VAC, 40 A/230 VAC | sin dato | 20 A/115 VAC, 40 A/230 VAC |
| Temperatura | −30 a +85 °C | −25 a +60 °C | −30 a +85 °C |
| Tamaño | 52.4 × 27.2 × 24 mm | ≈ 34 × 20 × 15 mm | 45.7 × 25.4 × 21.5 mm |
| Proveedor y precio | Sigma, 71.400 COP | Sigma, 19.992 COP | Mouser, ≈ 7.2 USD + envío |

**Decisión:** Mean Well IRM-20-12, comprada en Sigma y soldada a mano. Cumple la regla de aislamiento con certificación, está en stock local y tolera 2 kV de surge (cable largo hasta el tablero). Queda sobredimensionada; solo cuesta tamaño (24 mm de alto, se revisa con el gabinete en F7). La HLK-PM12 se descarta por certificación no verificable, 70 % de carga y 60 °C máximo; la IRM-10-12 obligaría a pedir a Mouser una sola pieza.

**Riel `+VIN` = 12 V confirmado:** con 5 V ±2.5 % el R-78CK podría quedar por debajo de su entrada mínima de 5 V, sin margen para el diodo OR de la entrada de banco.

**Librería (SamacSys):** símbolo `IRM-20-12` y footprint `IRM2012` verificados contra el plano del datasheet (case 219A): pines 1 AC/N, 2 −V, 3 +V, 4 AC/L; separaciones de 20.8 mm (AC/N–AC/L), 45 mm (entrada–salida) y 8 mm (−V–+V); agujero de 1.24 mm para pin de 1.0 mm; contorno de 52.4 × 27.2 mm. El módulo no tiene fusible interno (el diagrama de bloques empieza en el filtro EMI): el fusible externo es obligatorio.

Fuentes: [IRM-20 (2025-11-21)](https://www.meanwell.com/Upload/PDF/IRM-20/IRM-20-SPEC.PDF) · [IRM-10](https://www.meanwell.com/Upload/PDF/IRM-10/IRM-10-SPEC.PDF) · [IRM-05](https://www.meanwell.com/Upload/PDF/IRM-05/IRM-05-SPEC.PDF) · [HLK-PMxx](https://www.radiolocman.com/datasheet/data.html?di=692287) · [Sigma](https://www.sigmaelectronica.net/categoria-producto/fuentes/fuentes-conmutadas/)

### Protección de red: J1, fusibles y varistor (2026-10-07)

| Pieza | Elegida | Alternativas comparadas | Motivo |
|---|---|---|---|
| J1 | **ED1621** (tipo KF301, 2 polos, paso 5.0 mm, 300 V/10 A, 22–14 AWG), Sigma 952 COP | TER BLOCK 7.5M (7.5 mm, sin hoja de datos), BORNE 2P EMPAL (desmontable, sin hoja de datos) | tiene hoja de datos y stock; cumple L1–L2 ≥ 3.2 mm con pads ovalados de 1.8 mm de ancho (footprint propio en `EVSE.PcbLib`) |
| F1, F2 | **Schurter UMT-H T1A** (3403.0274.23), SMD 16 × 5.3 mm, 277 VAC, ruptura 1500 A, I²t de fusión 3.6 A²s; uno por línea | Littelfuse 0215002.MXP T2A 5×20 cerámico + BLX-A (fusible solo en Mouser); Littelfuse 0443 NANO² (ruptura de 50 A, descartado) | ruptura alta, lento, lo compra y suelda PCBWay, evita Mouser |
| RV1 | **TDK CU4032K300G2** (B72660M0301K072), SMD 10 × 8 mm, 300 VAC, 1200 A (8/20 µs), 23 J | TDK S14K300 (disco de 14 mm, 4.5 kA, Mouser y soldadura a mano) | suficiente para una instalación residencial bajo techo (la IRM-20 sola aguanta 2 kV); lo ensambla PCBWay |

- **Dos fusibles, uno por línea:** en 240 V las dos líneas son vivas; en 120 V el instalador puede invertir L y N. Ningún fusible deja la placa sin tensión: eso lo hace el breaker del tablero (bipolar en 240 V).
- **Resiliencia ante fusibles quemados (pedido del usuario):** (1) la entrada de banco J6 alimenta todo el lado SELV sin pasar por los fusibles ni por el AC-DC, así que la placa sigue funcionando si F1/F2 se funden en una prueba (solo se pierde la medición de tensión de red); (2) cada fusible tiene en paralelo un footprint DNP (F1B, F2B) para el portafusible 5×20 BLX-A de Sigma: si un UMT-H se funde, se suelda el portafusible con un fusible 5×20 lento sin desoldar el SMD (queda abierto). **Nunca se puentea un fusible con la red conectada.**
- Cálculos (I²t del inrush, varistor) en `docs/calculos/F2_ALIMENTACION.md`.

Fuentes: [hoja KF301/ED1621](https://www.sigmaelectronica.net/wp-content/uploads/2009/05/tblock_x2.pdf) · [Schurter UMT-H](https://sy-dep-epc-lpc.web.cern.ch/components/datasheets/epc-lpc%20(converters)/UMT-H_Fuse_(SCHURTER).pdf) · [TDK CU4032K300 (EPCOS)](https://static6.arrow.com/aropdfconversion/37e52ae61e332406dd9da286850b4ca98a904659/datasheetepcos.pdf) · [LCSC B72660M0301K072](https://lcsc.com/product-detail/varistors_tdk_b72660m0301k072_C541608.html) · [BLX-A (LCSC C3131)](https://www.lcsc.com/product-detail/C3131.html)

## Fase 3 — Medición (cerrada 2026-10-09)

Cálculos en `docs/calculos/F3_MEDICION.md`; esquemas por bloque en `docs/esquemas/F3_*.svg`; datasheets en `docs/datasheets/`.

| Pieza | Elegida | Alternativas comparadas | Motivo |
|---|---|---|---|
| U2 amplificador aislado | **TI AMC3330** (SOIC-16 DWE, creepage ≥ 8 mm; en la PCB, 7,50 mm entre filas de pads) | AMC1350, ACPL-C87B | DC/DC aislado integrado (nada más cruza la barrera), entrada bipolar ±1 V, ±0,2 %. Stock: solo Mouser **AMC3330DWE** (tubo); DWER sin stock en DigiKey/TI |
| R2–R5 divisor | **4 × Panasonic ERJ-P08F1004V** (1 MΩ 1206 anti-surge, 500 V) | 6 × Yageo RC1206 680 kΩ (200 V) | 93 Vpk por resistencia a 264 V, 194 Vpk con el surge de 775 V (39 % de 500 V) |
| R6 shunt | Panasonic ERA-6AEB103V (10 kΩ 0,1 %) | 9,76 k / 10,7 k (E96) | valores E24 (pedido del usuario); 264 V → 0,93 Vpk |
| Acople AC | C18/C21 10 µF + R9/R12 20 kΩ + R10/R14 13 kΩ + C19/C22 4,7 nF | acople DC | salida del AMC3330 centrada en 1,44 V; el ATM90E26 trabaja alrededor de AGND (mín. −1 V) |
| CT | **YHDC SCT-013-000V** (100 A : 50 mA), Sigma 35.700 COP | SCT-013-050 (1 V a 50 A) | carga de precisión en la placa (R11/R13 2 × 10 Ω → 0,5 V a 50 A), margen hasta 60 A |
| J3 | **Same Sky SJ1-3515-SMT** (jack 3,5 mm; pin 2 tip → `CT_P`, 1 sleeve → `CT_N`; 3 ring, 10 y 11 sin conexión con *No ERC*; el SCT-013-000 solo usa tip y sleeve), Sigma 2.975 COP | bornera 1751248, jack genérico | conserva el plug del CT |
| D4 | Littelfuse SMAJ5.0CA | — | ESD en el jack |
| U3 IC de medición | **Microchip ATM90E26-YU-R** (SSOP-28), DigiKey US$1,66 | ADE7953 (LFCSP, US$6,08) | encaja con IRQ/WarnOut/ZX de la TOP; SSOP retrabajable. CT por **I2P/I2N**, MMD1 = MMD0 = 1 (modo flexible, LNSel = N); SPI ≤ 160 kbps |
| Y1 | ECS-81.92-12-30Q-EN-TR (8,192 MHz, 12 pF, 5032, 2 pads) + C26/C27 12 pF | ABLS-8.192MHZ-B2-T (18 pF) | carga de 12 pF que pide el datasheet |
| Precisión | Panasonic ERA-6A 0,1 % 25 ppm (R6, R9, R10, R12, R14), ERA-6AHD100V 10 Ω 0,5 % (R11/R13) | RC0805 1 % | estabilidad con la temperatura |

**Numeración real en Altium (anotación del 2026-10-09)** frente a los esquemas de la primera guía. Los `docs/esquemas/F3_*.svg` ya usan la numeración real.

| Función | Esquema original | Altium |
|---|---|---|
| Divisor, R6, C9 | R2–R5, R6, C9 | igual |
| Lado de red de U2 (`HV_DCDC`: 1 µF, 1 nF, 100 nF) | C10, C11, C12 | igual |
| `HV_LDO`: 100 nF C0G 1206 y 1 nF | C13, C14 | **C16, C17** |
| `AMC_LDO` 100 nF · VDD 1 µF y 1 nF | C15 · C16, C17 | **C13 · C14, C15** |
| Acople P: 10 µF, 20 k, 13 k, 4,7 nF | C18, R8, R10, C20 | **C18, R9, R10, C19** |
| Acople N: 10 µF, 20 k, 13 k, 4,7 nF | C19, R9, R11, C21 | **C21, R12, R14, C22** |
| Carga del CT (10 Ω arriba y abajo) | R12, R13 | **R11, R13** |
| Serie y filtro del CT (1 k, 33 nF), P y N | R14, C22 · R15, C23 | **R8, C20 · R15, C23** |
| DVDD 10 µF y 100 nF · AVDD 100 nF | C24, C25 · C26 | C24, C25 · **C28** |
| Vref 1 µF y 1 nF | C27, C28 | **C30, C31** |
| Reset (10 k y 100 nF) | R16, C29 | igual |
| Cristal 12 pF (OSCI, OSCO) | C30, C31 | **C26, C27** |
| LED de CF1 (1 k) · pull-up de CS (10 k) | R18 · R17 | **R17 · R18** |
| U2, U3, J3, D4, Y1, LED2, TP5 (DIAG), TP6 (CF2), R7 | — | igual |

**Cierre (2026-10-09).** Hoja completa, anotada y revisada en `docs/revisiones/PROYECTO_F3.pdf`. Verificado: solo U2 une redes de red y SELV; J3 con tip y sleeve; C29 y R6 corregidos; footprints de F3 contra datasheet (AMC3330, jack, SSOP-28, SMA, 1206, cristal de 2 pads). Pendientes que pasan al inicio de F4 (`NEXT_SESSION.md`): 5 condensadores de `SamacSys.SchLib` con dos pines «1» y sin pin «2» (C9, C11 y C17 ya lo heredaron en la hoja: su lado `AC_L2_F` está abierto), `Manufacturer_Name` del ATM90E26 = «PCBWay», Update From Libraries (resistencias de la hoja con footprint 0603 viejo), `+3V3`/`+3V3A` como net labels (deben ser puertos de alimentación), `HV_D1`–`HV_D3`, `HV-AC`→`HV_AC` en 02, Blankets y parámetros de TP1–TP6.

## Fase 4 — MCU (cerrada 2026-10-12)

Componentes aprobados por el usuario (comparaciones completas en la sesión de F4; stock del 11 oct):

| Pieza | Elegida | Alternativas comparadas | Motivo |
|---|---|---|---|
| U4 módulo | **ESP32-S3-WROOM-1-N16R2** (16 MB flash, 2 MB PSRAM quad, −40 a 85 °C) | N8R2 (preferido, pero 0 u en Mouser, DigiKey y Sigma), N16R8 (solo 65 °C; reemplaza la preferencia de P5) | condición del usuario: en stock en Mouser, DigiKey o Sigma → Mouser 1694 u (`356-ESP32S3WRM1N16R2`); mismo footprint en todas las variantes |
| U5 puente USB-UART | **WCH CH340C** (SOP-16, reloj interno, alimentado de `+3V3`: TX a 3,3 V; −20 a 70 °C, lotes «4…» −40 a 85 °C) | CP2102N-A02-GQFN24R (Sigma, QFN-24), CH340G (Sigma, cristal de 12 MHz) | sin cristal, 1 condensador, LCSC 134 k u; modelo creado a partir del CH340G de SamacSys (mismo SOP-16) |
| Q1, Q2 auto-reset | **onsemi MMBT3904LT1G** (SOT-23) + R19/R20 12 kΩ + R21 4,7 kΩ (circuito del profesor, D13) | S8050 J3Y, MMDT3904 (SOT-363) | en Sigma (MMBT3904) y LCSC; saturan con 0,22 mA de base |
| J5 USB-C | **Würth 632723300011** (receptáculo USB 3.1, horizontal THR/SMT, PCB de 1,6 mm; Mouser 38 882 u, `710-632723300011`) + R23/R24 5,1 kΩ en CC1/CC2 | HRO TYPE-C-31-M-12, GCT USB4105-GF-A, Same Sky UJ20-C-H-G-SMT-TR (sin footprint en SamacSys), Würth 632723100011 (PCB 1,0 mm), 632712000011 (es un plug) | símbolo y footprint del Content Vault de Altium (CMP-1502-03214-4); solo se usan los pines USB 2.0; B5 «VCONN» = CC2. Footprint pendiente de comparar con el plano de Würth (F7) |
| D5 ESD | **ST USBLC6-2SC6** (3,5 pF, IEC 61000-4-2 nivel 4) | clon UMW | protege D+, D− y VBUS |
| SW1–SW3 | **XKB TS-1187A-B-A-B** (5,1 × 5,1 mm); SW2 RESET y SW3 BOOT DNP | KFC-A04-02 y SW-761SMD (Sigma) | PARAR (SW1) + J7 (bornera 3,5 mm igual a J6) para botón de panel SW730RD (Sigma) |
| LEDs | LED3 WiFi y LED4 carga APT2012SGC (verde), LED5 falla APT2012SURCK (rojo), 1 kΩ | LED azul (Vf alta) | igual que LED1 |
| J8 | Würth 61300611121 (1 × 6, 2,54 mm): 3V3, TX0, RX0, EN, IO0, GND | regleta de Sigma | R25/R26 de 1 kΩ en serie entre el CH340C y el UART0 |
| Zumbador | no | — | alarmas por la app y LED5; GPIO38 libre |

**Cierre (2026-10-12).** Hoja `04_MCU` completa, anotada (U4, U5, J5, J7, J8, D5, Q1, Q2, R19–R31, C32–C36, LED3–LED5, SW1–SW3) y revisada en `docs/revisiones/PROYECTO_F4.pdf`. Correcciones hechas por script durante la fase:
- CH340C: SamacSys no tenía modelo; se creó copiando el SN74HC595DR (mismo SOIC-16) y renombrando los 16 pines.
- TS-1187A-B-A-B: A1-B1 y C1-D1 están unidos por dentro; el símbolo de SamacSys los ponía en lados opuestos y el cableado dejaba EN, IO0 y PARAR en corto con GND. Se intercambiaron B1 y C1 en la librería y en la hoja.
- R21 se había puesto de 47 kΩ → 4,7 kΩ; `LED_PARAR` → `BTN_PARAR`.
- Hoja 03: el segundo puerto `MEAS_CS` (R18) pasó a net label, pero en Altium una net label y un puerto del mismo nombre **no se unen** en la misma hoja; se agregó la net label `MEAS_CS` también en el cable de U3.24.
- Formato de Altium aprendido: los Blankets van en el stream «Additional»; el «Weight» de la cabecera debe ser igual al número de registros; *Full replacement* borra los parámetros de las piezas del Content Vault (TP, J5).

`VBUS` solo llega a D5: la placa no se alimenta por USB y para programar debe estar alimentada (J6 o red). El CH340C suma ≤ 12 mA a `+3V3` (pico ≈ 429 mA, 86 % del R-78CK).

## Fase 5 — Sensores y RTC (cerrada 2026-10-12)

Comparaciones completas en la sesión de F5 (stock del 12 oct; LCSC como referencia de lo que ensambla PCBWay). Datasheets en `docs/datasheets/`.

| Pieza | Elegida | Alternativas comparadas | Motivo |
|---|---|---|---|
| U6 sensor de ambiente | **Aosong AHT20** (I²C 0x38, ±0,3 °C, ±2 %HR, DFN-6 3 × 3 mm; LCSC C2757850) + filtro R38 330 Ω / C37 10 µF que pide el fabricante + C38 100 nF | Sensirion SHT40-AD1B-R2 (0x44; original solo en Mouser), TI TMP117 (sin humedad) | en stock para PCBWay, mide humedad (condensación en la caja), barato |
| U7 RTC | **DS3231SN#** (0x68, TCXO ±2 ppm 0–40 °C, VBAT con conmutación, UL contra carga inversa; LCSC C9866 `DS3231SN#T&R`) + C39 100 nF; INT/SQW → `RTC_INT` con R34 10 kΩ; pines 5–12 a GND (datasheet); 1 y 4 con No ERC | RV-3028-C7 (sin stock en Mouser ni LCSC), PCF85063A (sin VBAT), MCP7940N (cristal externo) | todo integrado, sin cristal; sirve para fechar mediciones cuando vuelve la luz sin internet (P5) |
| BT1 | **TE BAT-HLD-001** (CR2032 SMD; LCSC C7501066) + pila CR2032 de Sigma | BH-106 y BK-913 de Sigma (THT) | ya estaba en SamacSys; lo ensambla PCBWay; > 8 años con 3 µA |
| Memoria | **ninguna** (D14) | FM24CL64B (8 KB FRAM), MB85RC256V, 24LC256 | la flash del ESP32 basta |
| J4 | bornera **3P 3,5 mm de Sigma** «BORNE 3.5MM 3P V» (footprint Phoenix 1751251) | JST XH, pines 2,54 mm | la sonda trae hilos sueltos; igual a J6 y J7 |
| D6 | **ST USBLC6-2SC6** (I/O1 en DATA de paso, VBUS en `J4_3V3`) | SMAJ5.0CA, diodo ESD nuevo | ya en la BOM (D5) |
| 1-Wire | R35 4,7 kΩ (pull-up, lado ESP32), R36 100 Ω en serie, **R37 68 Ω 1206 + C40 100 nF** en el 3V3 de J4 | sin limitación | un corto en el cable de la sonda queda en 49 mA (0,16 W) y la placa sigue funcionando; la sonda recibe ≥ 3,1 V |
| Bus I²C | R32/R33 4,7 kΩ, una sola pareja; direcciones 0x38, 0x68 sin conflicto | — | flanco ≈ 240 ns con 60 pF (< 300 ns a 400 kHz) |

**Librería (SamacSys, por script `piezas_f5.py`):** `DS3231SN` copiado del AMC3330DWE (mismo SOIC-16 de 7,5 mm, MS-013) con 16 pines renombrados; `RC0805FR-07100RL`, `RC0805FR-07330RL`, `RC1206FR-0768RL` por copia; AHT20 y 1751251 bajados de SamacSys (el AHT20 venía rotulado «Adafruit» y se corrigió). `FM24CL64B-GTR` quedó creado en la librería pero no se usa.

**Lecciones:**
- Un campo de Altium con caracteres no ASCII («±», «Ω») tiene una copia `%UTF8%…` que Altium lee primero; si se cambia solo el campo normal, Altium repone el valor viejo al guardar. `altium_ole.poner()` ahora borra esa copia.
- Las piezas colocadas desde el panel Components pueden traer parámetros viejos (caché): se revisan siempre con `lista_redes.py -p`.
- Otra vez `RC0805FR-0747KL` (47 kΩ) en lugar de `RC0805FR-074K7L` (4,7 kΩ): revisar el número al colocar.
- `lista_redes.py` ahora reconoce las marcas No ERC.
- El Smart PDF de F5 salió sin recorte (página carta con el dibujo completo); no hizo falta `arreglar_pdf.py`.

## Fase 6 — Actuación (cerrada 2026-10-12)

Datasheets en `docs/datasheets/F6/`. El usuario aprobó la propuesta del 12 oct y pidió cambiar el relé: el Finder 34.51.7.012.5010 (AgNi + Au) no está en Mouser (Mouser no trabaja Finder) y es caro.

**¿Hace falta el contacto dorado?** Sí, si la entrada del EVSE es de señal. Una entrada de habilitación genérica suele ser una entrada lógica con pull-up de 5–12 V y 1–5 mA. Un contacto AgNi pide al menos 500 mW (12 V/10 mA, Finder …0010), y el Panasonic APF30212 100 mA a 5 V. Con 1–5 mA esos contactos no son confiables. Los dorados disponibles cuestan US$9–22: Finder en TME, Phoenix 2961163 en Mouser a US$22,22 (y su oro solo aguanta 30 V/50 mA).

| Pieza | Elegida | Alternativas comparadas | Motivo |
|---|---|---|---|
| K1 | **Panasonic PhotoMOS AQY414EHAX** (1 Form B = NC, 400 V pico, 120 mA, Ron ≤ 35 Ω, fuga ≤ 10 µA; aislamiento reforzado de 5000 Vrms según EN 60950; SMD DIP-4), Mouser 769-AQY414EHAX, 521 u, US$3,42 | Finder 34.51.7.012.5010 (no está en Mouser), Phoenix 2961163 (US$22,22), APF30212 (AgNi, carga mínima de 100 mA) | NC sin energía, como pide P3; sin carga mínima ni desgaste; barato y en Mouser. NA disponible con el **AQY214EHAX** (1 Form A, mismo footprint, US$2,04, 2005 u) |
| Mando de K1 | +VIN → R41 1 kΩ → LED6 → LED de K1 → Q3: ≈ 8,4 mA (recomendado 5–10 mA; la salida se abre con ≤ 3 mA a 25 °C y ≈ 3,4 mA a 85 °C) | GPIO directo (a 3,3 V no alcanza para LED6 en serie) | no carga el +3V3; LED6 muestra la corriente real del LED de K1 |
| Q3 | **AO3400A** (LCSC C20917) + R39 1 kΩ + R40 10 kΩ | 2N7002 (VGS(th) hasta 2,5 V), BSS138 | conduce de sobra con 3,0 V |
| D7 | **eliminado** | SS34 (era para la bobina del relé) | sin carga inductiva |
| J2 | **2 polos: ED1621 de Sigma** (footprint TB001-500-02BE, el de J1) | ED1610 de 3 polos | el PhotoMOS es solo NC; NA se obtiene cambiando K1 por AQY214EHAX |
| LED6 | **KT-0805Y** amarillo (LCSC C2296) | APT2012SYCK/J3-PRV, APT2012SGC | barato, mucho stock |

**Límites que quedan:** 120 mA en la salida y 400 V pico (el recomendado es ≤ 320 V pico, ≈ 226 VAC). Si al medir los bornes del EVSE resultan ser de red, hay que poner un relé auxiliar externo. Redes `RELAY_EN`, `RELAY_DRV`, `EVSE_EN_A` y `EVSE_EN_B`; clase `EVSE_EXT` con Blanket.

**Cierre (2026-10-12).** Hoja dibujada por el usuario y arreglada con `arreglos_hoja06.py`: se borraron 3 piezas sueltas (relé, TB001-500-03BE y un AQY de más) y se pusieron los designadores Q3, R39–R41, LED6, K1 y J2, los parámetros de K1 y las dos Blankets `EVSE_EXT`. Validate correcto y `PROYECTO_F6.pdf` revisado (6 hojas + BOM). J2: pin 1 = `EVSE_EN_B` y pin 2 = `EVSE_EN_A` (sin polaridad). SamacSys nombra la pieza `AQY-414EHAX`; el MPN real va sin guion. Footprint SOP254P962X315-4N: pads en ±4,30 mm (1,90 × 0,75 mm) → 6,70 mm entre el lado del LED y el de la salida. En F8 no puede haber cobre debajo de K1.

**Lecciones:** Mouser no trabaja Finder y bloquea a ratos el navegador (se reintenta después); antes de colocar piezas nuevas, borra de la hoja las del diseño anterior (quedaron 3 sueltas); la Library Loader de SamacSys puede nombrar la pieza distinto del MPN (`AQY-414EHAX`).

**Librería (por script `piezas_f6.py`, 12 oct):** AO3400A copiado del MMBT3904LT1G (pines G/S/D, dibujo de MOSFET de canal N) y KT-0805Y copiado del APT2012SGC. Los parámetros del AQY414EHAX se ponen cuando se baje de SamacSys. El 34.51.7.012.5010 y la TB001-500-03BE quedaron bajados pero no se usan.

## Fase 7 — Cierre del esquemático (cerrada 2026-10-19)

**Revisión por script (14 oct):** seis hojas sin pines sueltos ni redes con dos nombres; los 6 parámetros obligatorios completos en los 136 componentes; rieles como puertos de alimentación; entradas de hoja de la TOP iguales a los puertos (nombre y dirección); designadores sin huecos.

**Footprints contra datasheet:** J5 ✓ (Content Vault = plano Würth rev 003.000, 2025-09-04, incluidas las ranuras de 0,6 × 1,2 mm); C2 (FK tamaño F) y C3 (tamaño D) ✓ con la tabla de pads del FK (10-feb-26) y pad 1 = +; K1 se queda con el de SamacSys (6,70 mm entre lados; Panasonic recomienda pads de 1,5 × 1,9 mm a 8,3 mm, que dejarían 6,40 mm); BT1 corregido al plano TE rev E1 (pads en ±10,5 mm, 1,8 × 5,2 mm; contacto Ø17,0 mm); F1B/F2B: el 01000056Z era un solo clip (puenteaba el fusible) → footprint nuevo `BLX-A_5X20` (XC Electronics BLX-A, LCSC C3131: pines planos de 1,5 × 0,35 mm a 22 ± 0,5 mm → agujero Ø1,9, pad Ø3,4).

**Cambios por script (`libreria_f7.py`, `arreglos_hojas_f7.py`, 14 oct; directiva de 03 el 19 oct):**
- Librería del proyecto: SamacSys copiada a `lib/` (57 piezas usadas + BLX-A; 38 sin uso fuera); los 125 modelos de footprint de las hojas y los de la SchLib apuntan a `lib\SamacSys.PcbLib` (antes, ruta absoluta a `Documents\AltiumLL`); sin los «Mouser Part Number» ajenos (Y1, FB1, D1, D2). La librería de `Documents/AltiumLL` no se tocó.
- `.PrjPcb`: librerías en `lib\`, sin `Job1.OutJob`, Revision 1.0.
- Hojas: Title en cada una, direcciones sin `*`, texto de plantilla propio y sin logo de Altium (también en `templates/EVSE_A3.SchDoc`); nota de rieles de la TOP; clase `USB` (Blanket junto a U5); Blankets `ANALOG` de 03 agrandadas; J4, U6, K1 con librería de origen; F1B/F2B → BLX-A.
- Validate (19 oct): compila; el único aviso era «Floating Parameter Set» en 03: la directiva `HV_AC` estaba 200 mil dentro de su Blanket y no aplicaba la clase a `HV_D1–3`, `HV_DCDC`, `HV_INP`, `HV_LDO`. Se movió al borde (1000, 11000).

**BOM con la regla D16 (19 oct, D17).** Tabla completa en `docs/BOM_F7.md`, generada por `docs/tools/bom_f7.py` (la lista `LINEAS` del script es la fuente única; el mismo script puso los parámetros en la librería y las hojas). Stock revisado en LCSC (API de JLCPCB/LCSC, como referencia de lo que ensambla PCBWay), DigiKey y Sigma; TRM 3.174,67 COP/USD. PCBWay en turnkey compra por MPN, primero en LCSC y si no en DigiKey/Mouser ([componentes](https://www.pcbway.com/pcb_prototype/Electronic_Components.html)); el usuario decidió que lo que PCBWay no tenga se compre en DigiKey y se suelde a mano.

| Por placa | Líneas | US$ | Montaje |
|---|---|---|---|
| A · PCBWay (stock en LCSC) | 57 | 60,02 | PCBWay (SMD y THT) |
| B · DigiKey, carrito del curso | K1 | 3,29 | a mano |
| C · Disponible | U1 | — | a mano |
| D · DNP | F1B/F2B, SW2/SW3 | — | — |
| E · Sigma, fuera de la PCB | CT, sonda, pila | 16,01 (50.813 COP) | — |

Sustitutos (el original estaba en 0 o no estaba en LCSC; mismo footprint, verificado contra el datasheet):

| Designador | Antes | Ahora | Por qué sirve |
|---|---|---|---|
| U2 | AMC3330DWE (tubo, Mouser) | **AMC3330DWER** (carrete), LCSC C2999368 | la misma pieza |
| F1, F2 | Schurter 3403.0274.23 | **3403.0274.11**, LCSC C6384960 | el mismo UMT-H T1A en bolsa (1 A, 277 VAC, 1500 A, 3,6 A²s) |
| J1, J2 | Same Sky TB001-500-02BE / ED1621 de Sigma | **Xinlaiya XY301V-A-5.0-2P**, LCSC C557651 | 300 V 15 A, paso 5,0 mm, pin Ø1,0 mm en agujero de 1,30 mm ([plano](https://datasheet.lcsc.com/datasheet/pdf/365cd490152737f9c602c462cbc5755e.pdf?productCode=C557651)). La KF301 y la DG301 de LCSC son de 250 V: no sirven para 264 VAC |
| L1 | RECOM RLS-126 | **Murata LQH43NH120J03L**, LCSC C3224514 | 12 µH ±5 %, 0,25 Ω, 420 mA (L1 lleva ≤ 0,17 A), AEC-Q200, 1812 ([spec](https://datasheet.lcsc.com/datasheet/pdf/8edb8b255c580e6accc90a1332550501.pdf?productCode=C3224514)). El filtro de RECOM (C3 = 1 nF entre Vin y Vout) se mantiene; la clase B de EMC no se verificó con el sustituto |
| RV1 | TDK B72660M0301K072 (1200 A, 23 J) | **Ruilon RL4032P471KJ**, LCSC C2935514 | 300 VAC, 2500 A (8/20 µs), 30 J; pads recomendados 3,50 × 2,80 mm a 6,50 mm, iguales al footprint CU4032 ([datasheet](https://datasheet.lcsc.com/datasheet/pdf/1a5b1623e8458213c7164fb853a09779.pdf?productCode=C2935514)). UL «pendiente» |
| C16 | TDK C3216NP01H104J160AA | **Murata GRM31C5C1H104JA01L**, LCSC C97946 | 100 nF C0G 50 V 1206 |
| C20, C23 | KEMET C1206C333J5GACTU | **Murata GRM3195C1H333JA01D**, LCSC C97930 | 33 nF C0G 50 V 1206 |
| R11, R13 | Panasonic ERA-6AHD100V (0,5 %) | **Yageo RT0805BRD0710RL**, LCSC C865142 | 10 Ω 0,1 % 25 ppm (mejor) |
| D3 | «Vishay» SMBJ15A | Littelfuse SMBJ15A, LCSC C83846 | como se eligió en F2 |

Antes en Mouser y ahora en LCSC/PCBWay: U4 (C2913205), J5 (C2830802; en DigiKey cuesta US$ 4,37). Antes en Sigma y ahora en PCBWay: PS1 IRM-20-12 (C5278499, US$ 6,37 frente a 71.400 COP), J3, J4 y J6/J7 (Phoenix originales), J8. K1 (AQY414EHAX) no está en LCSC y no tiene equivalente NC con aislamiento reforzado: DigiKey 255-6089-1-ND, US$ 3,29, a mano. Fuera de la PCB: CT SCT-013-000V (Sigma 35.700 COP; el de Seeed en DigiKey está sin stock), sonda DS18B20 2 m (Sigma 11.900 COP), pila CR2032 (Sigma 3.213 COP; DigiKey solo la envía por tierra).

**Cambios por script (`bom_f7.py`, 19 oct):** 8 piezas nuevas en `lib/SamacSys.SchLib` por copia de la que reemplazan (mismo símbolo y footprint; las reemplazadas se borraron; quedan 58); `Manufacturer_Name`, `Manufacturer_Part_Number`, `Supplier`, `Supplier PN` (LCSC C…, DigiKey o Sigma) y `Assembly` iguales a la BOM en la librería y en los 128 componentes de las hojas (SW2/SW3 y F1B/F2B siguen DNP); sin campos de Mouser, Arrow ni RS. Redes idénticas antes y después (`lista_redes.py`); `libreria.py` sin avisos (acepta un MPN igual al nombre más un sufijo de empaque, como `DS3231SN#T&R`).

**Revisión de diseño (19 oct, sobre las redes de las 6 hojas):**

| Punto | Resultado |
|---|---|
| Aislamiento | Solo PS1, U2 y K1 tienen pines en red/`EVSE_EXT` y en SELV; los pasivos de red (R2–R6, C9–C12, C16, C17, RV1, F1/F2) tienen los dos pines del lado de red. `EVSE_EN_A/B` solo van de J2 a K1. Clases: `HV_AC` (4 directivas en 02 y Blanket en 03), `ANALOG`, `USB`, `EVSE_EXT` |
| Tensiones nominales | J1 300 V, F1/F2 277 VAC, RV1 300 VAC, PS1 85–305 VAC, R2–R5 500 V (93 Vpk cada una a 264 VAC), K1 400 Vpk y 5000 Vrms reforzado |
| Potencia | `+3V3` ≈ 429 mA en el pico del WiFi (86 % del R-78CK, F4); L1 ≤ 0,17 A de 420 mA; R41 72 mW (0805); R37 0,16 W con la sonda en corto (1206) |
| Arranque | EN con 10 kΩ + 1 µF; IO0 con 4,7 kΩ a 3,3 V; IO3, IO45 e IO46 sin conectar (valores por defecto: flash a 3,3 V); RELAY_EN con R40 a GND → K1 cerrado (carga permitida) mientras arranca; reset del ATM90E26 10 kΩ + 100 nF |
| ESD en conectores | J1 fusibles + RV1; J3 D4 SMAJ5.0CA + 1 kΩ + 33 nF; J4 D6 + R36/R37; J5 D5; J6 D2 + D3; J7 solo R31 1 kΩ + C36 100 nF (sin TVS; se acepta sin gabinete); J2 sin TVS (K1 aguanta 400 Vpk); J8 interno con 1 kΩ en TX/RX |
| Puntos de prueba | TP1 GND, TP2 `+VIN`, TP3 `+3V3`, TP4 `+3V3A`, TP5 `AMC_DIAG`, TP6 CF2; ninguno en la red (seguridad). Las señales analógicas se miden en los pads de C19/C20 |
| Valores | R7 47 kΩ (pull-up de DIAG), R41 → 8,4 mA en el LED de K1, CC1/CC2 5,1 kΩ, I²C 4,7 kΩ, cristal con 12 pF, divisor 4 × 1 MΩ / 10 kΩ, carga del CT 2 × 10 Ω. C1 (1 nF entre la entrada y la salida del R-78CK) es el C3 del filtro de EMC de RECOM ([datasheet, p. 5](https://recom-power.com/pdf/Innoline/R-78CK-0.5.pdf)) |

Sin cambios en el esquemático. Opcional (no se hizo, se mantiene el esquemático congelado): llevar `AMC_DIAG` a un GPIO libre; la caída de la red ya se ve en la tensión que mide el ATM90E26.

**Cierre (19 oct).** Validate correcto después de la BOM. `docs/revisiones/F7_BOM.csv` (60 filas, 132 designadores) coincide con `bom_f7.py` en fabricante, MPN, proveedor, PN del proveedor y montaje. La única diferencia es de agrupación: Altium junta SW1 (PCBWay) con SW2/SW3 (DNP) en una fila con «PCBWay, DNP», aunque cada componente tiene su valor bien puesto. En F8, la BOM de ensamble de PCBWay se agrupa también por `Assembly`. `docs/revisiones/PROYECTO_F7.pdf` (6 hojas + BOM, carta, sin recorte) revisado página por página: los títulos de 02, 04 y 06 se salían del bloque de título (caben ≈ 31 caracteres) y la nota de rieles de la TOP mostraba 6 de sus 7 líneas. Se arregló por script (`presentacion_f7.py`: títulos «Alimentación: red, 12 V y 3,3 V», «ESP32-S3, USB y programación», «Actuación: PhotoMOS K1 al EVSE»; nota 400 mil más alta), con las redes iguales; se verá en el PDF de F8. Quedan sin arreglar, por ser solo de presentación, las banderas «Parameter Set» de 03 encimadas sobre el texto de la plantilla (`HV_AC`) y sobre J3 (`ANALOG`).

**Lecciones:** la API de búsqueda de JLCPCB y la ficha de LCSC dan el stock real que ensambla PCBWay; la búsqueda de LCSC está bloqueada. DigiKey se lee bien con WebFetch, y en Sigma la búsqueda no encuentra todo, pero sí la página directa del producto (`/producto/<referencia>/`). Un parámetro con «&» (`DS3231SN#T&R`) se guarda sin problema.

**Notas para F8:** J5 tiene agujeros de 0,4 mm con pad de 0,65 mm (anillo de 0,125 mm): confirmar con PCBWay; BT1 sin pasta en el contacto central; reglas de `EVSE_EXT`, `HV_AC`, `USB` y `ANALOG`.

## Componentes elegidos

Se llena al cerrar cada fase.

| Bloque | Función | Elegido | Alternativas comparadas | Proveedor | Montaje | Fase |
|---|---|---|---|---|---|---|
| Alimentación | Regulador de 3.3 V | RECOM R-78CK3.3-0.5 | — (disponible) | ya se tiene | manual | F2 |
| Alimentación | Fuente AC-DC aislada, 12 V | Mean Well IRM-20-12 | Hi-Link HLK-PM12, Mean Well IRM-10-12 (IRM-05-12) | PCBWay (LCSC C5278499; antes Sigma) | PCBWay (THT) | F2, F7 |
| Alimentación | Bornera de red J1 | Xinlaiya XY301V-A-5.0-2P (300 V 15 A, 5,0 mm; antes ED1621) | TER BLOCK 7.5M, BORNE 2P EMPAL; KF301/DG301 de 250 V | PCBWay (LCSC C557651) | PCBWay (THT) | F2, F7 |
| Alimentación | Fusibles F1, F2 | Schurter UMT-H T1A 3403.0274.11 (bolsa; antes .23) | Littelfuse 0215002.MXP + BLX-A, Littelfuse 0443 | PCBWay | PCBWay (SMD) | F2 |
| Alimentación | Portafusibles alternos F1B, F2B | BLX-A 5×20 | — | Sigma (595 COP) | DNP | F2 |
| Alimentación | Varistor RV1 | Ruilon RL4032P471KJ (antes TDK B72660M0301K072, sin stock) | TDK S14K300, Bourns PV300K4032R2 | PCBWay (LCSC C2935514) | PCBWay (SMD) | F2, F7 |
| Alimentación | Diodos OR D1, D2 | Vishay SS34-E3/57T (SMC) | TI TPS2121, un solo diodo | PCBWay | PCBWay | F2 |
| Alimentación | Entrada de banco J6 | Phoenix 1751248 (2P 3,5 mm) | jack de barril SMD, ED1621 | PCBWay (LCSC C89122) | PCBWay (THT) | F2, F7 |
| Alimentación | TVS D3 | Littelfuse SMBJ15A | SMAJ15A, sin TVS | PCBWay | PCBWay | F2 |
| Alimentación | Bulk `+VIN` C1 | Panasonic EEE-FK1V101P (100 µF 35 V) | Sigma 100 µF 25 V, 470 µF 35 V THT | PCBWay | PCBWay | F2 |
| Alimentación | Filtro EMI del R-78CK | L1 Murata LQH43NH120J03L (antes RLS-126) + C2 CL31B106KBHNNNE + C3 KEMET C0805C102J5GAC-TU | sin L1 | PCBWay | PCBWay | F2 |
| Alimentación | Filtro LC de `+3V3` | L2 Bourns SRR4028-2R2Y + C4 CL21A106KAYNNNE + C5/C6 CL21A226MAQNNNE + C7 EEE-FK1C101P | ferrita de potencia, solo condensadores | PCBWay | PCBWay | F2 |
| Alimentación | Filtro `+3V3A` | FB1 Murata BLM21PG221SN1D + C8 CL21A106KAYNNNE | RC 10 Ω, LDO | PCBWay | PCBWay | F2 |
| Alimentación | LED de encendido | LED1 Kingbright APT2012SGC + R1 RC0805FR-071KL (en `+3V3`) | — | PCBWay | PCBWay | F2 |
| Alimentación | Puntos de prueba | Keystone 5016 (librería de Altium) | Keystone 5015, pad propio | PCBWay | PCBWay | F2 |
| Medición | Amplificador aislado U2 | TI AMC3330DWER (carrete) | AMC1350, ACPL-C87B | PCBWay (LCSC C2999368) | PCBWay | F3, F7 |
| Medición | Divisor R2–R5 + R6 | 4 × Panasonic ERJ-P08F1004V + ERA-6AEB103V | 6 × RC1206 680 kΩ | PCBWay | PCBWay | F3 |
| Medición | IC de medición U3 | Microchip ATM90E26-YU-R + Y1 ECS-81.92-12-30Q-EN-TR | ADE7953 | PCBWay | PCBWay | F3 |
| Medición | CT y conector | YHDC SCT-013-000V + J3 Same Sky SJ1-3515-SMT-TR + D4 SMAJ5.0CA | SCT-013-050, bornera | Sigma (CT) / PCBWay (J3, D4) | CT externo; resto PCBWay | F3, F7 |
| Medición | Acople y carga de precisión | Panasonic ERA-6A (0,1 %), Yageo RT0805BRD0710RL (R11/R13), Murata GRM C0G 1206 (C16, C20, C23), C0G/X7R 0805 | RC0805 1 % | PCBWay | PCBWay | F3 |
| MCU | Módulo U4 | Espressif ESP32-S3-WROOM-1-N16R2 | N8R2, N16R8 | PCBWay (LCSC C2913205) | PCBWay | F4, F7 |
| MCU | Puente USB-UART U5 | WCH CH340C | CP2102N, CH340G | PCBWay | PCBWay | F4 |
| MCU | Auto-reset | 2 × onsemi MMBT3904LT1G + RC0805 12 k, 4,7 k | S8050, MMDT3904 | PCBWay | PCBWay | F4 |
| MCU | USB-C J5 + ESD D5 | Würth 632723300011 + ST USBLC6-2SC6 + 2 × 5,1 k | HRO TYPE-C-31-M-12, GCT USB4105/4085, micro-USB Molex 105017-0001 | PCBWay (LCSC C2830802) | PCBWay | F4, F7 |
| MCU | Pulsadores SW1–SW3 | XKB TS-1187A-B-A-B (SW2, SW3 DNP) + botón de panel SW730RD en J7 | KFC-A04-02, SW-761SMD | PCBWay / Sigma | PCBWay / manual | F4 |
| MCU | LEDs y conectores | APT2012SGC ×2, APT2012SURCK; J7 Phoenix 1751248; J8 Würth 61300611121 | — | PCBWay | PCBWay (J7, J8 THT) | F4, F7 |
| Sensores | Sensor de ambiente U6 | Aosong AHT20 + R38/C37/C38 | SHT40-AD1B-R2, TMP117 | PCBWay (LCSC C2757850) | PCBWay | F5 |
| Sensores | RTC U7 + pila BT1 | DS3231SN#T&R + TE BAT-HLD-001 + CR2032 | RV-3028-C7, PCF85063A, MCP7940N; BH-106, BK-913 | PCBWay (LCSC C9866, C7501066) / Sigma (pila) | PCBWay / pila a mano | F5 |
| Actuación | Salida a los bornes del EVSE K1 | Panasonic PhotoMOS AQY414EHAX (NC) | Finder 34.51.7.012.5010, Phoenix 2961163, Panasonic APF30212; NA: AQY214EHAX | DigiKey (255-6089-1-ND), carrito del curso | manual | F6, F7 |
| Actuación | Driver Q3 + R39/R40 | AO3400A + RC0805 1 k / 10 k | 2N7002, BSS138 | PCBWay | PCBWay | F6 |
| Actuación | LED6 + R41 | Hubei KENTO KT-0805Y + RC0805 1 k | APT2012SYCK/J3-PRV | PCBWay (LCSC C2296) | PCBWay | F6 |
| Actuación | J2 | Xinlaiya XY301V-A-5.0-2P (footprint TB001-500-02BE) | ED1610 3P, BORNE 3P EMPAL | PCBWay (LCSC C557651) | PCBWay (THT) | F6, F7 |
| Sensores | Sonda DS18B20 J4 + ESD D6 | Phoenix 1751251 + USBLC6-2SC6 + R35–R37, C40 | JST XH, SMAJ5.0CA | PCBWay (LCSC C91152) / Sigma (sonda SEN DS18B20 2M) | PCBWay (THT); sonda externa | F5, F7 |

Desde F7 (D17) el proveedor, el número de parte del proveedor y el montaje de cada línea están en `docs/BOM_F7.md`.

Regla desde F2: pasivos y LEDs en 0805 o más grandes; 0603 solo si no existe en 0805.

Numeración real de F2 en Altium (anotación del 2026-10-08): C1 1 nF (EMI), C2 100 µF 35 V (bulk `+VIN`), C3 100 µF 16 V (`+3V3`), C4/C5 22 µF, C6 10 µF 50 V (entrada R-78CK), C7 10 µF (salida R-78CK), C8 10 µF (`+3V3A`); L1 RLS-126, L2 SRR4028; U1 R-78CK; J6 banco; F1B/F2B portafusibles. D3 en la librería es el SMBJ15A de Vishay (equivale al de Littelfuse).

## Mapa de pines del ESP32-S3

Se cierra en F4. Propuesta inicial de Rev A: SPI 12/11/13/10, IRQ 14, WarnOut 21, ZX 17, I²C 8/9, 1-Wire 4, relé 5 (`RELAY_EN`), LEDs 6/7, botón PARAR 15, zumbador 16, USB 19/20. Rev C: `EVSE_EN` desaparece (D7); `RTC_INT` necesita un GPIO si se usa.

**Definitivo (F4, 2026-10-12):** MEAS_CS 10, MEAS_MOSI 11, MEAS_SCK 12, MEAS_MISO 13 (pines nativos de FSPI), MEAS_IRQ 14, MEAS_WARN 21, MEAS_ZX 17, I2C_SDA 8, I2C_SCL 9, OW_DATA 4, RTC_INT 18, RELAY_EN 5, LED3/LED4/LED5 6/7/15, PARAR 16, TXD0 43, RXD0 44, EN e IO0 al auto-reset. Sin uso (No ERC): 1, 2, 3, 19, 20, 35–42, 45–48 (38 reservado para un zumbador). F5 usa I2C 8/9, OW 4 y RTC_INT 18 sin cambios. Ninguna salida en pines de strapping.
