# BOM de la Fase 7 (regla de compras D16)

Generada con `python docs/tools/bom_f7.py --md` (la lista `LINEAS` de ese script es la fuente única; los mismos datos quedan en los parámetros `Manufacturer_Name`, `Manufacturer_Part_Number`, `Supplier`, `Supplier PN` y `Assembly` de la librería y las hojas).

- **Stock revisado el 19 oct 2026** en LCSC (API de JLCPCB/LCSC), DigiKey y Sigma. Precio en US$ por pieza a cantidad 1 (LCSC o DigiKey); PCBWay cotiza el suyo al hacer el pedido.
- **Una placa ensamblada** (decisión del usuario): U1 es el R-78CK del profesor. Todo lo que tiene PCBWay llega soldado; lo que no, se compra en DigiKey y se suelda a mano.
- TRM del día: 3.174,67 COP/USD ([dolarhoy.co](https://www.dolarhoy.co/2026-10-19)).
- PCBWay compra por número de parte, primero en proveedores locales y si no en DigiKey, Mouser o Arrow ([componentes](https://www.pcbway.com/pcb_prototype/Electronic_Components.html)).

## A · PCBWay turnkey (stock en LCSC): llega soldado

| Designadores | Cant. | Fabricante | MPN | Proveedor | PN proveedor | Montaje | US$ c/u | US$ línea | Nota |
|---|---|---|---|---|---|---|---|---|---|
| BT1 | 1 | TE Connectivity | `BAT-HLD-001` | PCBWay | LCSC C7501066 | PCBWay | 1,1381 | 1,14 |  |
| C1, C9, C11, C15, C17, C31 | 6 | KEMET | `C0805C102J5GACTU` | PCBWay | LCSC C2167084 | PCBWay | 0,0294 | 0,18 |  |
| C2 | 1 | Panasonic | `EEE-FK1V101P` | PCBWay | LCSC C128462 | PCBWay | 0,4394 | 0,44 |  |
| C3 | 1 | Panasonic | `EEE-FK1C101P` | PCBWay | LCSC C128532 | PCBWay | 0,2762 | 0,28 |  |
| C4, C5, C33 | 3 | Samsung Electro-Mechanics | `CL21A226MAQNNNE` | PCBWay | LCSC C45783 | PCBWay | 0,1940 | 0,58 |  |
| C6 | 1 | Samsung Electro-Mechanics | `CL31B106KBHNNNE` | PCBWay | LCSC C89632 | PCBWay | 0,2837 | 0,28 |  |
| C7, C8, C18, C21, C24, C37 | 6 | Samsung Electro-Mechanics | `CL21A106KAYNNNE` | PCBWay | LCSC C15850 | PCBWay | 0,0874 | 0,52 |  |
| C10, C14, C30, C32 | 4 | Samsung Electro-Mechanics | `CL21B105KAFNNNE` | PCBWay | LCSC C116352 | PCBWay | 0,0405 | 0,16 |  |
| C12, C13, C25, C28, C29, C34, C35, C36, C38, C39, C40 | 11 | Samsung Electro-Mechanics | `CL21B104KBCNNNC` | PCBWay | LCSC C1711 | PCBWay | 0,0144 | 0,16 |  |
| C16 | 1 | Murata | `GRM31C5C1H104JA01L` | PCBWay | LCSC C97946 | PCBWay | 0,3801 | 0,38 | cambio: el TDK C3216NP01H104J160AA está en 0 |
| C19, C22 | 2 | KEMET | `C0805C472J5GACTU` | PCBWay | LCSC C2170898 | PCBWay | 0,0592 | 0,12 |  |
| C20, C23 | 2 | Murata | `GRM3195C1H333JA01D` | PCBWay | LCSC C97930 | PCBWay | 0,1333 | 0,27 | cambio: el KEMET C1206C333J5GACTU no está en LCSC |
| C26, C27 | 2 | KEMET | `C0805C120J5GACTU` | PCBWay | LCSC C2168859 | PCBWay | 0,0188 | 0,04 |  |
| D1, D2 | 2 | Vishay | `SS34-E3/57T` | PCBWay | LCSC C13354 | PCBWay | 0,2788 | 0,56 |  |
| D3 | 1 | Littelfuse | `SMBJ15A` | PCBWay | LCSC C83846 | PCBWay | 0,1473 | 0,15 | la librería decía Vishay |
| D4 | 1 | Littelfuse | `SMAJ5.0CA` | PCBWay | LCSC C83324 | PCBWay | 0,1117 | 0,11 |  |
| D5, D6 | 2 | STMicroelectronics | `USBLC6-2SC6` | PCBWay | LCSC C7519 | PCBWay | 0,1774 | 0,35 |  |
| F1, F2 | 2 | Schurter | `3403.0274.11` | PCBWay | LCSC C6384960 | PCBWay | 2,5720 | 5,14 | cambio: el mismo UMT-H T1A en bolsa; el .23 (carrete) está en 0 en LCSC |
| FB1 | 1 | Murata | `BLM21PG221SN1D` | PCBWay | LCSC C85840 | PCBWay | 0,0345 | 0,03 |  |
| J1, J2 | 2 | Xinlaiya | `XY301V-A-5.0-2P` | PCBWay | LCSC C557651 | PCBWay | 0,1141 | 0,23 | cambio: TB001-500-02BE sin stock; 300 V 15 A, pin de 1,0 mm, mismo footprint (THT) |
| J3 | 1 | Same Sky | `SJ1-3515-SMT-TR` | PCBWay | LCSC C22359767 | PCBWay | 1,8745 | 1,87 | antes Sigma |
| J4 | 1 | Phoenix Contact | `1751251` | PCBWay | LCSC C91152 | PCBWay | 1,3422 | 1,34 | antes Sigma (THT) |
| J5 | 1 | Wurth Elektronik | `632723300011` | PCBWay | LCSC C2830802 | PCBWay | 6,4413 | 6,44 | antes Mouser; DigiKey 732-9618-1-ND a US$ 4,37 |
| J6, J7 | 2 | Phoenix Contact | `1751248` | PCBWay | LCSC C89122 | PCBWay | 0,9666 | 1,93 | antes Sigma (THT) |
| J8 | 1 | Wurth Elektronik | `61300611121` | PCBWay | LCSC C5444523 | PCBWay | 0,4703 | 0,47 | antes Sigma (THT) |
| L1 | 1 | Murata | `LQH43NH120J03L` | PCBWay | LCSC C3224514 | PCBWay | 0,2911 | 0,29 | cambio: RECOM RLS-126 sin stock en LCSC; 12 uH, 0,25 ohm, 420 mA, AEC-Q200 |
| L2 | 1 | Bourns | `SRR4028-2R2Y` | PCBWay | LCSC C2041777 | PCBWay | 1,0728 | 1,07 |  |
| LED1, LED2, LED3, LED4 | 4 | Kingbright | `APT2012SGC` | PCBWay | LCSC C5353439 | PCBWay | 0,1250 | 0,50 |  |
| LED5 | 1 | Kingbright | `APT2012SURCK` | PCBWay | LCSC C5875730 | PCBWay | 0,1254 | 0,13 |  |
| LED6 | 1 | Hubei KENTO Electronic | `KT-0805Y` | PCBWay | LCSC C2296 | PCBWay | 0,0146 | 0,01 |  |
| PS1 | 1 | Mean Well | `IRM-20-12` | PCBWay | LCSC C5278499 | PCBWay | 6,3695 | 6,37 | antes Sigma, 71.400 COP (THT) |
| Q1, Q2 | 2 | onsemi | `MMBT3904LT1G` | PCBWay | LCSC C81464 | PCBWay | 0,0164 | 0,03 |  |
| Q3 | 1 | Alpha & Omega Semiconductor | `AO3400A` | PCBWay | LCSC C20917 | PCBWay | 0,0972 | 0,10 |  |
| R1, R8, R15, R17, R25, R26, R28, R29, R30, R31, R39, R41 | 12 | Yageo | `RC0805FR-071KL` | PCBWay | LCSC C95781 | PCBWay | 0,0037 | 0,04 |  |
| R2, R3, R4, R5 | 4 | Panasonic | `ERJ-P08F1004V` | PCBWay | LCSC C41369755 | PCBWay | 0,0319 | 0,13 |  |
| R6 | 1 | Panasonic | `ERA-6AEB103V` | PCBWay | LCSC C191101 | PCBWay | 0,0918 | 0,09 |  |
| R7 | 1 | Yageo | `RC0805FR-0747KL` | PCBWay | LCSC C126351 | PCBWay | 0,0075 | 0,01 |  |
| R9, R12 | 2 | Panasonic | `ERA-6AEB203V` | PCBWay | LCSC C473304 | PCBWay | 0,1204 | 0,24 |  |
| R10, R14 | 2 | Panasonic | `ERA-6AEB133V` | PCBWay | LCSC C445658 | PCBWay | 0,0833 | 0,17 |  |
| R11, R13 | 2 | Yageo | `RT0805BRD0710RL` | PCBWay | LCSC C865142 | PCBWay | 0,1015 | 0,20 | cambio: ERA-6AHD100V en 0 en LCSC; 0,1 % y 25 ppm (mejor) |
| R16, R18, R22, R27, R34, R40 | 6 | Yageo | `RC0805FR-0710KL` | PCBWay | LCSC C84376 | PCBWay | 0,0053 | 0,03 |  |
| R19, R20 | 2 | Yageo | `RC0805FR-0712KL` | PCBWay | LCSC C114556 | PCBWay | 0,0069 | 0,01 |  |
| R21, R32, R33, R35 | 4 | Yageo | `RC0805FR-074K7L` | PCBWay | LCSC C60816 | PCBWay | 0,0072 | 0,03 |  |
| R23, R24 | 2 | Yageo | `RC0805FR-075K1L` | PCBWay | LCSC C84375 | PCBWay | 0,0072 | 0,01 |  |
| R36 | 1 | Yageo | `RC0805FR-07100RL` | PCBWay | LCSC C105577 | PCBWay | 0,0044 | 0,00 |  |
| R37 | 1 | Yageo | `RC1206FR-0768RL` | PCBWay | LCSC C137238 | PCBWay | 0,0092 | 0,01 |  |
| R38 | 1 | Yageo | `RC0805FR-07330RL` | PCBWay | LCSC C105878 | PCBWay | 0,0060 | 0,01 |  |
| RV1 | 1 | Ruilon | `RL4032P471KJ` | PCBWay | LCSC C2935514 | PCBWay | 0,2595 | 0,26 | cambio: TDK B72660M0301K072 sin stock en LCSC; 300 VAC, 2500 A, 30 J, mismos pads |
| SW1 | 1 | XKB Connectivity | `TS-1187A-B-A-B` | PCBWay | LCSC C318884 | PCBWay | 0,0206 | 0,02 |  |
| TP1, TP2, TP3, TP4, TP5, TP6 | 6 | Keystone Electronics | `5016` | PCBWay | LCSC C238129 | PCBWay | 0,2590 | 1,55 |  |
| U2 | 1 | Texas Instruments | `AMC3330DWER` | PCBWay | LCSC C2999368 | PCBWay | 5,0242 | 5,02 | cambio de MPN: DWE (tubo) en 0; DWER es la misma pieza en carrete |
| U3 | 1 | Microchip | `ATM90E26-YU-R` | PCBWay | LCSC C616398 | PCBWay | 2,2320 | 2,23 |  |
| U4 | 1 | Espressif Systems | `ESP32-S3-WROOM-1-N16R2` | PCBWay | LCSC C2913205 | PCBWay | 5,2673 | 5,27 | antes Mouser |
| U5 | 1 | WCH | `CH340C` | PCBWay | LCSC C84681 | PCBWay | 0,5438 | 0,54 |  |
| U6 | 1 | Aosong | `AHT20` | PCBWay | LCSC C2757850 | PCBWay | 0,7968 | 0,80 |  |
| U7 | 1 | Analog Devices | `DS3231SN#T&R` | PCBWay | LCSC C9866 | PCBWay | 9,9329 | 9,93 |  |
| Y1 | 1 | ECS | `ECS-81.92-12-30Q-EN-TR` | PCBWay | LCSC C2450755 | PCBWay | 1,7128 | 1,71 |  |

**Subtotal A: US$ 60,02 por placa**

## B · DigiKey (carrito del curso), se suelda a mano: PCBWay no lo tiene

| Designadores | Cant. | Fabricante | MPN | Proveedor | PN proveedor | Montaje | US$ c/u | US$ línea | Nota |
|---|---|---|---|---|---|---|---|---|---|
| K1 | 1 | Panasonic | `AQY414EHAX` | DigiKey | 255-6089-1-ND | Manual | 3,2900 | 3,29 | LCSC en 0, sin equivalente NC con aislamiento reforzado |

**Subtotal B: US$ 3,29 por placa**

## C · Ya disponible, se suelda a mano

| Designadores | Cant. | Fabricante | MPN | Proveedor | PN proveedor | Montaje | US$ c/u | US$ línea | Nota |
|---|---|---|---|---|---|---|---|---|---|
| U1 | 1 | RECOM Power | `R-78CK3.3-0.5` | Disponible | - | Manual | 0,0000 | 0,00 | la del profesor; otra: DigiKey 945-R-78CK3.3-0.5-ND, US$ 3,57 |

**Subtotal C: US$ 0,00 por placa**

## D · No se monta (DNP)

| Designadores | Cant. | Fabricante | MPN | Proveedor | PN proveedor | Montaje | US$ c/u | US$ línea | Nota |
|---|---|---|---|---|---|---|---|---|---|
| F1B, F2B | 2 | XC Electronics | `BLX-A` | Sigma | BLX-A | DNP | 0,0000 | 0,00 | solo si se funde un UMT-H (LCSC C3131) |
| SW2, SW3 | 2 | XKB Connectivity | `TS-1187A-B-A-B` | PCBWay | LCSC C318884 | DNP | 0,0000 | 0,00 | RESET y BOOT |

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
| A · PCBWay (LCSC) | 60,02 | 190.545 |
| B · DigiKey, carrito del curso | 3,29 | 10.445 |
| E · Sigma, fuera de la PCB | 16,01 | 50.813 |
| **Total en componentes** | **79,32** | **251.802** |

Sin la PCB, el costo de ensamble de PCBWay (SMD y THT), el envío ni los impuestos: eso va en el carrito de compras de F8.

Stock justo en LCSC (sobra para una placa): APT2012SGC 62 u., Y1 70, SRR4028 66, BAT-HLD-001 55, 3403.0274.11 79.
