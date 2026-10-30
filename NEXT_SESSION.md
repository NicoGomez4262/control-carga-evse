# Siguiente sesión → Fase 9: pedido, montaje y primeras pruebas

F8 se cerró el 22 oct 2026. La PCB está ruteada y verificada: 0 violaciones eléctricas, GND en un solo grupo y Gerber comparados contra el PcbDoc. Desde el 30 oct el pedido va por JLCPCB (D20): la BOM y el CPL de JLC están listos. Lo que sigue ya no es diseño: es pedir, recibir, soldar lo que va a mano y probar la placa por etapas.

## Prompt para iniciar

```text
Seguimos con la FASE 9 del proyecto "Control de carga EVSE" (pedido, montaje y primeras pruebas).

Lee CLAUDE.md, NEXT_SESSION.md, docs/PLAN_FASES.md (Fases 8 y 9), docs/DECISIONES.md (secciones «Fase 8» y «Fase 9», D20),
docs/fabricacion/GUIA_PEDIDO_JLC.md y docs/EXPLICACION_PCB_F8.md.

1. Muéstrame el diagrama general (como gráfico) y la lista de tareas de F9.
2. Acompáñame en el pedido de JLCPCB paso a paso (docs/fabricacion/GUIA_PEDIDO_JLC.md: formulario, BOM y CPL,
   revisión de la ubicación, cotización y DFM). El pago lo hago yo.
3. Actualiza el carrito con la cotización real de JLC y deja lista la compra en Sigma.
4. Cuando lleguen las placas: plan de inspección, soldadura a mano de U1 y pruebas por etapas, primero sin red.
```

## Qué se hizo en F8

- **Placa:** 130 × 100 mm, 2 capas, 1,6 mm, 1 oz, HASL sin plomo (D18). Zona de red, isla EVSE y SELV separadas por una barrera de 6,7 mm sin cobre; solo la cruzan PS1, U2 y K1.
- **Ruteo:** a mano, por el usuario. Lo que faltaba se terminó por script (`rutear_f8.py`), con planos de GND en Top y Bottom, una vía junto a cada pad de GND y vías de costura. Las vías van tapadas.
- **Verificación:** DRC de Altium con 0 violaciones eléctricas (quedan 31 avisos de serigrafía, aceptados). Revisión propia del cobre (`revisar_ruteo_f8.py`) y de los Gerber (`revisar_gerber_f8.py`: 304 taladros, máscara, pasta y cobre iguales al PcbDoc).
- **Paquete en `docs/fabricacion/`:** `EVSE_Monitor_Gerber.zip`, `BOM_PCBWay.xlsx`, `PickPlace_PCBWay.csv`, `Ensamble_EVSE_Monitor.pdf` y `PEDIDO_PCBWAY.md` (formulario y notas en inglés para el «Remark»). El STEP se regenera con el OutJob y no va a GitHub.
- **Carrito:** https://claude.ai/artifact/Vf8NPamJJd74KN2qhytMVX. **US$ 211,48 ≈ 672.732 COP** (TRM 3.181,01 del 23 oct): PCBWay US$ 195,51 (estimado, con K1 y 2 fusibles de repuesto) y Sigma 50.813 COP. Sin DigiKey desde el 23 oct (D19).
- **Preparación del pedido (22 oct, ya en F9):** `docs/fabricacion/GUIA_PEDIDO.md` tiene el paso a paso del pedido en grupo, con cada campo de PCBWay revisado en su formulario. TP1–TP6 pasaron a ronghe RH-5016, porque el Keystone 5016 quedó en 0 en LCSC. Conteo para el formulario: 57 referencias, 118 SMD, 8 THT y 2 BGA/QFP.

## Dónde estamos

<!--DIAG:ALL-->
```text
MAPA GENERAL · cada bloque indica la fase en que se diseña

EXTERNO · instalación (fuera de la PCB)
  [Breaker del EVSE] ─┬─► [F3 CT en L1] ─► [EVSE] ─► [Vehículo]
                      │         │           ▲  │
                      └─► J1    └─► J3      │  └─ sonda DS18B20 ─► J4
                                            └─ J2 (bornes de habilitación)
════════════════════════════════════════════════════════════════════════════════════════════════════════════════
PCB        ZONA RED · 120–240 VAC                     ┃ BARRERA  ┃      ZONA SELV · 12 V y 3.3 V
                                                      ┃ ≥ 6.4 mm ┃
                                                      ┃          ┃
 ENERGÍA   J1 ─► [F2 Protección] ─┬───────────────────┨  AC-DC   ┠─► [F2 Riel 12 V] ─► [F2 R-78CK + LC] ─► 3V3
                                  │                   ┃   (F2)   ┃
 MEDICIÓN V                       └─► [F3 Divisor] ───┨  AMC3330 ┠─► V ─► [F3 ATM90E26] ═SPI═► ESP32-S3
                                                      ┃   (F3)   ┃              ▲ I
 MEDICIÓN I                                           ┃          ┃              └─◄ [F3 Carga CT] ◄─ J3
                                                      ┃          ┃
 ACTUACIÓN J2 ◄── contacto seco (aislado) ────────────┨ PhotoMOS ┠◄─ LED ─ [F6 Driver K1] ◄─ GPIO ─ ESP32-S3
                                                      ┃   (F6)   ┃
 CONTROL                                              ┃          ┃   [F4 ESP32-S3] ─ WiFi ─► router ─► internet ─► app
 INTERFAZ                                             ┃          ┃ J5 ─► [F4 USB-C · USB-UART · auto-reset · LEDs] ─► ESP32-S3
 SENSORES                                             ┃          ┃ J4 ─► [F5 Sensores · RTC] ─► ESP32-S3
 BANCO                                                ┃          ┃ J6 ─► [F2 Entrada banco 12 V] ─► D2 ─► +VIN
════════════════════════════════════════════════════════════════════════════════════════════════════════════════
[F# bloque] fase en que se diseña · ▐bloque▌ se diseña en ESTA fase · ► carril con trabajo en esta fase
┃ ┃ barrera de aislamiento · ┨ ┠ componente que cruza la barrera (AC-DC, AMC3330, PhotoMOS K1)
│ L1/L2 (L/N en 120 V) con fusibles · J1–J6 conectores · J1 con cable largo a la línea · J2 contacto seco aislado
```
<!--/DIAG-->
<!--/DIAG-->

## Tareas de la Fase 9

**9A · Pedido**

- [x] Esquinas redondeadas de R 4 mm y bloque de identificación en la serigrafía (`esquinas_f9.py`, `serigrafia_f9.py`, 22 oct).
- [x] Símbolos de alta tensión, RAEE y ESD en la zona de red, y tarjeta con el QR a nicolasgomez.dev atrás (`marcas_f9.py`, 22 oct).
- [x] En Altium (`GUIA_PEDIDO.md`, A0): Repour All, revisar esquinas, serigrafía y QR, DRC y OutJob. Después `paquete_pcbway_f8.py` y `revisar_gerber_f8.py` (22 oct, 21:39: todo bien y el QR se lee desde el GBO).
- [x] 23 oct: BT1 girado, Repour y OutJob (14:04). Paquete revisado: sin corto en `RTC_VBAT`, Gerber y QR bien. Las gotas nuevas no se aplicaron; se sube sin ellas.
- [x] 23 oct: sin DigiKey (nadie más del curso pidió). K1 (AQY414EHAX) lo compra PCBWay en DigiKey o Mouser y lo suelda, y F1/F2 llevan 2 fusibles 3403.0274.11 de repuesto sueltos. BOM, Pick & Place (127 piezas), notas (597 de 600 caracteres), parámetros de Altium y carrito actualizados. Formulario: **58 referencias, 119 SMD**, 8 THT, 2 BGA/QFP (D19).
- [x] 30 oct (D20): **el pedido pasa a JLCPCB** (PCBWay podía tardar más de un mes; la clase pide en JLC). Stock revisado: todo en JLC menos el AQY414EHAX. K1 → **AQY214EHAX (NA)**, elegido por el usuario, y 11 líneas genéricas → piezas Basic. `BOM_JLC.csv`, `CPL_JLC.csv` y `GUIA_PEDIDO_JLC.md` listos; la PCB no cambia.
- [ ] Si quedó un pedido sin pagar en PCBWay, cancelarlo.
- [ ] JLC, PCB: subir `EVSE_Monitor_Gerber.zip`, revisar el visor y llenar el formulario (`GUIA_PEDIDO_JLC.md`, paso 1: 5 placas, verde, HASL sin plomo, vías tapadas, «Confirm Production File» = Yes).
- [ ] JLC, ensamble: Economic, Top, **2 placas**, «Confirm Parts Placement» = Yes; subir `BOM_JLC.csv` y `CPL_JLC.csv` (paso 2). Las 58 líneas tienen que salir confirmadas, 16 Basic y 42 extendidas (paso 3).
- [ ] Revisar la ubicación pieza por pieza en «Component Placements» (paso 4): polaridad, pin 1 y la entrada de cables de las borneras. Se puede hacer con Claude en el navegador del panel.
- [ ] Revisar la cotización (paso 5): piezas ≈ US$ 118 y extendidas ≈ US$ 129 para 2 placas, más PCB, envío DHL/FedEx y arancel. Actualizar el carrito (`carrito_f8.py` todavía es de PCBWay) con los valores reales.
- [ ] Responder el DFM de JLC (paso 6): J5 se deja como está (anillo de 0,125 mm, pads a 0,145 mm); el voladizo de U4, J3 y J5 es a propósito; agujeros de herramienta lejos de la red. Aprobar la ubicación final que manda JLC.
- [ ] Pagar y anotar el número de pedido.
- [ ] Altium: poner en la librería y en las hojas los nuevos MPN (K1 y las 11 Basic) y `Supplier`/`Assembly` = JLCPCB (`bom_f7.LINEAS` ya los tiene). No cambia el Gerber.
- [x] ~~DigiKey~~: no se pide (23 oct, D19). Desde el 30 oct, K1 va en el ensamble de JLC (AQY214EHAX) y no hay fusibles de repuesto sueltos: la segunda placa sirve de repuesto.
- [ ] Sigma, sin afán (antes de las pruebas): SCT-013-000V, SEN DS18B20 2M y CR2032.

**9B · Recepción y montaje**

- [ ] Inspección visual de las 2 placas: puentes de soldadura en U3, J5 y U4, polaridad de diodos, LEDs y electrolíticos (C2, C3), orientación de K1 (pin 1), que las borneras tengan la entrada hacia afuera y que F1B, F2B, SW2 y SW3 estén vacíos.
- [ ] Sin alimentar, con el multímetro: ningún corto entre `+VIN`, `+3V3`, `+3V3A` y GND; ninguna continuidad entre la red (J1) y cualquier punto del SELV (GND, J5, J6).
- [ ] Soldar a mano U1 (R-78CK3.3-0.5) en la primera placa. K1 llega soldado por JLC.

**9C · Primeras pruebas (por etapas)**

- [ ] **1. Sin red:** 12 V por J6, con una fuente de banco limitada a 150–200 mA. Medir `+VIN`, `+3V3` y `+3V3A`, y anotar el consumo.
- [ ] **2. USB:** J5 al computador. Que el CH340C aparezca; programar el ESP32-S3 con el auto-reset; encender los LEDs.
- [ ] **3. Buses:** AHT20 y DS3231 por I²C, DS18B20 por 1-Wire (J4), `RTC_INT`.
- [ ] **4. Medidor y actuación:** leer los registros del ATM90E26 por SPI, sin red. Conmutar K1 desde el ESP32 y medir J2 con el multímetro. Con el AQY214EHAX (NA): `RELAY_EN` en alto = J2 cerrado = carga permitida, y LED6 encendido.
- [ ] **5. Con red:** solo a través de un **transformador de aislamiento** y un breaker; nada se toca con la placa energizada. Medir V e I con una carga conocida y calibrar el ATM90E26.
- [ ] Cerrar la Rev 1.0: etiqueta `rev1.0` en git y notas de lo que cambiaría en la Rev 1.1 (gabinete incluido).

## Ten a mano

- Carrito: https://claude.ai/artifact/Vf8NPamJJd74KN2qhytMVX
- Mapa del proyecto: https://claude.ai/artifact/EcYNTEBgvaQKugkwZJAJ5y
- `docs/fabricacion/` (paquete y notas del pedido) y `docs/EXPLICACION_PCB_F8.md` (por qué la placa quedó así).
- Fuente de banco de 12 V con límite de corriente, multímetro, cautín de punta fina, flux y malla.

## Pendientes fuera de esta fase

- Firmware del ESP32 y la app en internet (fuera del proyecto de Altium).
- Gabinete: lo decide la Rev 1.1 de la PCB.
