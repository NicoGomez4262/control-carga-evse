# BOM de la Fase 7 (regla de compras D16)

Generada con `python docs/tools/bom_f7.py --md` (la lista `LINEAS` de ese script es la fuente única; los mismos datos quedan en los parámetros `Manufacturer_Name`, `Manufacturer_Part_Number`, `Supplier`, `Supplier PN` y `Assembly` de la librería y las hojas).

- **Stock revisado el 19 oct 2026** en LCSC (API de JLCPCB/LCSC), DigiKey y Sigma. Precio en US$ por pieza a cantidad 1 (LCSC o DigiKey); PCBWay cotiza el suyo al hacer el pedido.
- **30 oct (D20): pedido en JLCPCB**, ensamble Economic de **2 placas** (mínimo de JLC) con piezas de su stock. K1 pasa a AQY214EHAX (NA) y 11 líneas genéricas a piezas Basic de JLC. U1 es el R-78CK del profesor y se suelda a mano en la primera placa. Archivos: `paquete_jlc_f9.py`.
- TRM del día: 3.174,67 COP/USD ([dolarhoy.co](https://www.dolarhoy.co/2026-10-19)).
- JLC cobra US$ 3,07 por cada referencia extendida en el ensamble Economic; las Basic no pagan ([precios](https://jlcpcb.com/help/article/pcb-assembly-price)).

## A · JLCPCB, ensamble Economic con piezas de su stock (desde el 30 oct, D20): llega soldado

| Designadores | Cant. | Fabricante | MPN | Proveedor | PN proveedor | Montaje | US$ c/u | US$ línea | Nota |
|---|---|---|---|---|---|---|---|---|---|
| BT1 | 1 | TE Connectivity | `BAT-HLD-001` | JLCPCB | LCSC C7501066 | JLCPCB | 1,1381 | 1,14 |  |
| C1, C9, C11, C15, C17, C31 | 6 | KEMET | `C0805C102J5GACTU` | JLCPCB | LCSC C2167084 | JLCPCB | 0,0294 | 0,18 |  |
| C2 | 1 | Panasonic | `EEE-FK1V101P` | JLCPCB | LCSC C128462 | JLCPCB | 0,4394 | 0,44 |  |
| C3 | 1 | Panasonic | `EEE-FK1C101P` | JLCPCB | LCSC C128532 | JLCPCB | 0,2762 | 0,28 |  |
| C4, C5, C33 | 3 | Samsung Electro-Mechanics | `CL21A226MAQNNNE` | JLCPCB | LCSC C45783 | JLCPCB | 0,1940 | 0,58 |  |
| C6 | 1 | Samsung Electro-Mechanics | `CL31B106KBHNNNE` | JLCPCB | LCSC C89632 | JLCPCB | 0,2837 | 0,28 |  |
| C7, C8, C18, C21, C24, C37 | 6 | Samsung Electro-Mechanics | `CL21A106KAYNNNE` | JLCPCB | LCSC C15850 | JLCPCB | 0,0874 | 0,52 |  |
| C10, C14, C30, C32 | 4 | Samsung Electro-Mechanics | `CL21B105KBFNNNE` | JLCPCB | LCSC C28323 | JLCPCB | 0,0422 | 0,17 | cambio (30 oct, D20): pieza Basic de JLC, misma especificación; antes CL21B105KAFNNNE (25 V); este es de 50 V |
| C12, C13, C25, C28, C29, C34, C35, C36, C38, C39, C40 | 11 | YAGEO | `CC0805KRX7R9BB104` | JLCPCB | LCSC C49678 | JLCPCB | 0,0205 | 0,23 | cambio (30 oct, D20): pieza Basic de JLC, misma especificación; antes CL21B104KBCNNNC |
| C16 | 1 | Murata | `GRM31C5C1H104JA01L` | JLCPCB | LCSC C97946 | JLCPCB | 0,3801 | 0,38 | cambio: el TDK C3216NP01H104J160AA está en 0 |
| C19, C22 | 2 | KEMET | `C0805C472J5GACTU` | JLCPCB | LCSC C2170898 | JLCPCB | 0,0592 | 0,12 |  |
| C20, C23 | 2 | Murata | `GRM3195C1H333JA01D` | JLCPCB | LCSC C97930 | JLCPCB | 0,1333 | 0,27 | cambio: el KEMET C1206C333J5GACTU no está en LCSC |
| C26, C27 | 2 | KEMET | `C0805C120J5GACTU` | JLCPCB | LCSC C2168859 | JLCPCB | 0,0188 | 0,04 |  |
| D1, D2 | 2 | Vishay | `SS34-E3/57T` | JLCPCB | LCSC C13354 | JLCPCB | 0,2788 | 0,56 |  |
| D3 | 1 | Littelfuse | `SMBJ15A` | JLCPCB | LCSC C83846 | JLCPCB | 0,1473 | 0,15 | la librería decía Vishay |
| D4 | 1 | Littelfuse | `SMAJ5.0CA` | JLCPCB | LCSC C83324 | JLCPCB | 0,1117 | 0,11 |  |
| D5, D6 | 2 | STMicroelectronics | `USBLC6-2SC6` | JLCPCB | LCSC C7519 | JLCPCB | 0,1774 | 0,35 |  |
| F1, F2 | 2 | Schurter | `3403.0274.11` | JLCPCB | LCSC C6384960 | JLCPCB | 2,5720 | 5,14 | JLC arma 2 placas: la segunda sirve de repuesto (antes: 2 fusibles sueltos en PCBWay) |
| FB1 | 1 | Murata | `BLM21PG221SN1D` | JLCPCB | LCSC C85840 | JLCPCB | 0,0345 | 0,03 |  |
| J1, J2 | 2 | Xinlaiya | `XY301V-A-5.0-2P` | JLCPCB | LCSC C557651 | JLCPCB | 0,1141 | 0,23 | cambio: TB001-500-02BE sin stock; 300 V 15 A, pin de 1,0 mm, mismo footprint (THT) |
| J3 | 1 | Same Sky | `SJ1-3515-SMT-TR` | JLCPCB | LCSC C22359767 | JLCPCB | 1,8745 | 1,87 | antes Sigma |
| J4 | 1 | Phoenix Contact | `1751251` | JLCPCB | LCSC C91152 | JLCPCB | 1,3422 | 1,34 | antes Sigma (THT) |
| J5 | 1 | Wurth Elektronik | `632723300011` | JLCPCB | LCSC C2830802 | JLCPCB | 6,4413 | 6,44 | antes Mouser; DigiKey 732-9618-1-ND a US$ 4,37 |
| J6, J7 | 2 | Phoenix Contact | `1751248` | JLCPCB | LCSC C89122 | JLCPCB | 0,9666 | 1,93 | antes Sigma (THT) |
| J8 | 1 | Wurth Elektronik | `61300611121` | JLCPCB | LCSC C5444523 | JLCPCB | 0,4703 | 0,47 | antes Sigma (THT) |
| L1 | 1 | Murata | `LQH43NH120J03L` | JLCPCB | LCSC C3224514 | JLCPCB | 0,2911 | 0,29 | cambio: RECOM RLS-126 sin stock en LCSC; 12 uH, 0,25 ohm, 420 mA, AEC-Q200 |
| L2 | 1 | Bourns | `SRR4028-2R2Y` | JLCPCB | LCSC C2041777 | JLCPCB | 1,0728 | 1,07 |  |
| LED1, LED2, LED3, LED4 | 4 | Kingbright | `APT2012SGC` | JLCPCB | LCSC C5353439 | JLCPCB | 0,1250 | 0,50 |  |
| LED5 | 1 | Kingbright | `APT2012SURCK` | JLCPCB | LCSC C5875730 | JLCPCB | 0,1254 | 0,13 |  |
| LED6 | 1 | Hubei KENTO Electronic | `KT-0805Y` | JLCPCB | LCSC C2296 | JLCPCB | 0,0146 | 0,01 |  |
| PS1 | 1 | Mean Well | `IRM-20-12` | JLCPCB | LCSC C5278499 | JLCPCB | 6,3695 | 6,37 | antes Sigma, 71.400 COP (THT) |
| Q1, Q2 | 2 | Jiangsu Changjing Electronics | `MMBT3904` | JLCPCB | LCSC C20526 | JLCPCB | 0,0117 | 0,02 | cambio (30 oct, D20): pieza Basic de JLC, misma especificación; antes MMBT3904LT1G |
| Q3 | 1 | Alpha & Omega Semiconductor | `AO3400A` | JLCPCB | LCSC C20917 | JLCPCB | 0,0972 | 0,10 |  |
| R1, R8, R15, R17, R25, R26, R28, R29, R30, R31, R39, R41 | 12 | UNI-ROYAL | `0805W8F1001T5E` | JLCPCB | LCSC C17513 | JLCPCB | 0,0035 | 0,04 | cambio (30 oct, D20): pieza Basic de JLC, misma especificación; antes RC0805FR-071KL |
| R2, R3, R4, R5 | 4 | Panasonic | `ERJ-P08F1004V` | JLCPCB | LCSC C41369755 | JLCPCB | 0,0319 | 0,13 |  |
| R6 | 1 | Panasonic | `ERA-6AEB103V` | JLCPCB | LCSC C191101 | JLCPCB | 0,0918 | 0,09 |  |
| R7 | 1 | UNI-ROYAL | `0805W8F4702T5E` | JLCPCB | LCSC C17713 | JLCPCB | 0,0068 | 0,01 | cambio (30 oct, D20): pieza Basic de JLC, misma especificación; antes RC0805FR-0747KL |
| R9, R12 | 2 | Panasonic | `ERA-6AEB203V` | JLCPCB | LCSC C473304 | JLCPCB | 0,1204 | 0,24 |  |
| R10, R14 | 2 | Panasonic | `ERA-6AEB133V` | JLCPCB | LCSC C445658 | JLCPCB | 0,0833 | 0,17 |  |
| R11, R13 | 2 | Yageo | `RT0805BRD0710RL` | JLCPCB | LCSC C865142 | JLCPCB | 0,1015 | 0,20 | cambio: ERA-6AHD100V en 0 en LCSC; 0,1 % y 25 ppm (mejor) |
| R16, R18, R22, R27, R34, R40 | 6 | UNI-ROYAL | `0805W8F1002T5E` | JLCPCB | LCSC C17414 | JLCPCB | 0,0034 | 0,02 | cambio (30 oct, D20): pieza Basic de JLC, misma especificación; antes RC0805FR-0710KL |
| R19, R20 | 2 | UNI-ROYAL | `0805W8F1202T5E` | JLCPCB | LCSC C17444 | JLCPCB | 0,0028 | 0,01 | cambio (30 oct, D20): pieza Basic de JLC, misma especificación; antes RC0805FR-0712KL |
| R21, R32, R33, R35 | 4 | UNI-ROYAL | `0805W8F4701T5E` | JLCPCB | LCSC C17673 | JLCPCB | 0,0039 | 0,02 | cambio (30 oct, D20): pieza Basic de JLC, misma especificación; antes RC0805FR-074K7L |
| R23, R24 | 2 | UNI-ROYAL | `0805W8F5101T5E` | JLCPCB | LCSC C27834 | JLCPCB | 0,0055 | 0,01 | cambio (30 oct, D20): pieza Basic de JLC, misma especificación; antes RC0805FR-075K1L |
| R36 | 1 | UNI-ROYAL | `0805W8F1000T5E` | JLCPCB | LCSC C17408 | JLCPCB | 0,0042 | 0,00 | cambio (30 oct, D20): pieza Basic de JLC, misma especificación; antes RC0805FR-07100RL |
| R37 | 1 | Yageo | `RC1206FR-0768RL` | JLCPCB | LCSC C137238 | JLCPCB | 0,0092 | 0,01 |  |
| R38 | 1 | UNI-ROYAL | `0805W8F3300T5E` | JLCPCB | LCSC C17630 | JLCPCB | 0,0044 | 0,00 | cambio (30 oct, D20): pieza Basic de JLC, misma especificación; antes RC0805FR-07330RL |
| RV1 | 1 | Ruilon | `RL4032P471KJ` | JLCPCB | LCSC C2935514 | JLCPCB | 0,2595 | 0,26 | cambio: TDK B72660M0301K072 sin stock en LCSC; 300 VAC, 2500 A, 30 J, mismos pads |
| SW1 | 1 | XKB Connectivity | `TS-1187A-B-A-B` | JLCPCB | LCSC C318884 | JLCPCB | 0,0206 | 0,02 |  |
| TP1, TP2, TP3, TP4, TP5, TP6 | 6 | ronghe | `RH-5016` | JLCPCB | LCSC C5199799 | JLCPCB | 0,0926 | 0,56 | cambio (22 oct): el Keystone 5016 está en 0 en LCSC; el RH-5016 es el mismo plano (3,81 × 2,84 mm) |
| U2 | 1 | Texas Instruments | `AMC3330DWER` | JLCPCB | LCSC C2999368 | JLCPCB | 5,0242 | 5,02 | cambio de MPN: DWE (tubo) en 0; DWER es la misma pieza en carrete |
| U3 | 1 | Microchip | `ATM90E26-YU-R` | JLCPCB | LCSC C616398 | JLCPCB | 2,2320 | 2,23 |  |
| U4 | 1 | Espressif Systems | `ESP32-S3-WROOM-1-N16R2` | JLCPCB | LCSC C2913205 | JLCPCB | 5,2673 | 5,27 | antes Mouser |
| U5 | 1 | WCH | `CH340C` | JLCPCB | LCSC C84681 | JLCPCB | 0,5438 | 0,54 |  |
| U6 | 1 | Aosong | `AHT20` | JLCPCB | LCSC C2757850 | JLCPCB | 0,7968 | 0,80 |  |
| U7 | 1 | Analog Devices | `DS3231SN#T&R` | JLCPCB | LCSC C9866 | JLCPCB | 9,9329 | 9,93 |  |
| Y1 | 1 | ECS | `ECS-81.92-12-30Q-EN-TR` | JLCPCB | LCSC C2450755 | JLCPCB | 1,7128 | 1,71 |  |
| K1 | 1 | Panasonic | `AQY214EHAX` | JLCPCB | LCSC C371971 | JLCPCB | 0,9702 | 0,97 | cambio (30 oct, D20): NA en lugar del AQY414EHAX (NC, en 0 en JLC); sin energía el EVSE no carga |

**Subtotal A: US$ 60,02 por placa**

## C · Ya disponible, se suelda a mano

| Designadores | Cant. | Fabricante | MPN | Proveedor | PN proveedor | Montaje | US$ c/u | US$ línea | Nota |
|---|---|---|---|---|---|---|---|---|---|
| U1 | 1 | RECOM Power | `R-78CK3.3-0.5` | Disponible | - | Manual | 0,0000 | 0,00 | la del profesor; otra: DigiKey 945-R-78CK3.3-0.5-ND, US$ 3,57 |

**Subtotal C: US$ 0,00 por placa**

## D · No se monta (DNP)

| Designadores | Cant. | Fabricante | MPN | Proveedor | PN proveedor | Montaje | US$ c/u | US$ línea | Nota |
|---|---|---|---|---|---|---|---|---|---|
| F1B, F2B | 2 | XC Electronics | `BLX-A` | Sigma | BLX-A | DNP | 0,0000 | 0,00 | solo si se funde un UMT-H (LCSC C3131) |
| SW2, SW3 | 2 | XKB Connectivity | `TS-1187A-B-A-B` | JLCPCB | LCSC C318884 | DNP | 0,0000 | 0,00 | RESET y BOOT |

**Subtotal D: US$ 0,00 por placa**

## E · Fuera de la PCB (Sigma: DigiKey no las tiene o no las envía)

| Pieza | Fabricante | Referencia | Proveedor | COP | DigiKey |
|---|---|---|---|---|---|
| CT de J3 | YHDC | `SCT-013-000V` | Sigma | 35.700 | Seeed 101990029 sin stock (llega el 18 de diciembre) |
| Sonda de J4 | genérica | `SEN DS18B20 2M` | Sigma | 11.900 | DFR0198 cuesta US$ 6,90 |
| Pila de BT1 | — | `CR2032` | Sigma | 3.213 | 11-CR2032-ND solo se envía por tierra |

**Subtotal E: 50.813 COP ≈ US$ 16,01**

## Resumen

61 líneas, 128 piezas montadas por placa.

| Grupo | US$ | COP |
|---|---|---|
| A · JLCPCB (por placa) | 60,02 | 190.529 |
| B · DigiKey, carrito del curso | 0,00 | 0 |
| E · Sigma, fuera de la PCB | 16,01 | 50.813 |
| **Total en componentes** | **76,02** | **241.342** |

Sin la PCB, el costo de ensamble de PCBWay (SMD y THT), el envío ni los impuestos: eso va en el carrito de compras de F8.

Stock justo en LCSC (sobra para una placa): APT2012SGC 62 u., Y1 70, SRR4028 66, BAT-HLD-001 55, 3403.0274.11 89 (23 oct; con los 2 de repuesto se piden 4).
