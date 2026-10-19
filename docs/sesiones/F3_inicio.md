# Siguiente sesión → Fase 3: medición (`03_MEDICION.SchDoc`)

**Estado del proyecto (8 oct 2026):** Fase 2 cerrada con pendientes. La hoja `02_ALIMENTACION.SchDoc` está dibujada con todos los componentes elegidos, pero falta corregir una conexión y terminar el cierre (parámetros, PDF). **Lo primero de la sesión es terminar esos pendientes**; después se arranca F3.

## Prompt para iniciar

Copia y pega esto en una sesión nueva de Claude abierta en la carpeta del repositorio:

```text
Iniciamos la FASE 3 del proyecto "Control de carga EVSE" en Altium: hoja 03_MEDICION.SchDoc.

Antes de empezar, lee CLAUDE.md, NEXT_SESSION.md, docs/PLAN_FASES.md (secciones Fase 2 y Fase 3), docs/DECISIONES.md y docs/calculos/F2_ALIMENTACION.md.

En esta sesión:
1. Primero, los pendientes de F2: lee el archivo 02_ALIMENTACION.SchDoc del proyecto, saca su lista de redes y verifica que quedaron corregidos los puntos de la sección "Pendientes de F2" de NEXT_SESSION.md (sobre todo J6 y +VIN). Dime qué falta y guíame con los parámetros, la clase HV_AC, los pads de J1, la anotación y el PDF (corrígelo con docs/tools/arreglar_pdf.py antes de revisarlo).
2. Muéstrame el diagrama de bloques con la ubicación de la Fase 3 y la lista de tareas.
3. Con el ritmo acordado en CLAUDE.md: en un solo mensaje, todos los componentes de F3 con sus comparaciones (datasheet; Sigma y PCBWay primero, Mouser solo si no hay; 0805 o más grande) y un mini diagrama de bloques bonito, parecido a la hoja de Altium (con referencias y redes). Usa números de parte que existan en SamacSys.
4. Cuando lo apruebe, guíame paso a paso en Altium 25.4.2 para dibujar la hoja y haz los cálculos (divisor, escalas de V e I, filtros).
5. Revisa la hoja leyendo el .SchDoc (lista de redes) y el PDF, y al terminar cierra la fase como indica CLAUDE.md.
```

## Pendientes de F2 (hacer al inicio de la sesión)

Revisión de la lista de redes del 2026-10-08 (actualizada al iniciar F3 con `python docs/tools/lista_redes.py`):

- [x] **J6 y `+VIN`.** Corregido: `+VIN` une D1/D2/D3, C2 (100 µF), RLS-126 y TP2; `VIN_BANCO` = D2 ánodo + bornera pin 1; pin 2 a GND.
- [x] TP en GND (quedó como TP1; TP2 `+VIN`, TP3 `+3V3`, TP4 `+3V3A`).
- [x] Etiquetas de red AC: `AC_L1`/`AC_L2` del lado de J1 y `AC_L1_F`/`AC_L2_F` del lado de PS1 (verificado 09:22).
- [x] Designadores: C1–C8 como los numeró Altium (C1 1 nF, C2 100 µF 35 V, C3 100 µF 16 V, C4/C5 22 µF, C6 10 µF 50 V, C7 10 µF, C8 10 µF); F1B/F2B, U1 (R-78CK), L1 (RLS-126), L2 (SRR4028), J6 corregidos.
- [x] Nota de texto junto a J1.
- [x] Parámetros en `SamacSys.SchLib` (19 piezas) y en TP1–TP4 (en la hoja).
- [ ] Clase de red: las 4 directivas dicen **`HV-AC`** (guion); cambiar a `HV_AC`.
- [ ] **Update From Libraries** en `02_ALIMENTACION` (los parámetros de la librería no han llegado a la hoja).
- [ ] Error Reporting: «Nets with no driving source» → No Report (los avisos de `+3V3`, `+3V3A`, `+VIN`, GND son normales con pines pasivos).
- [ ] **F1B/F2B (nuevo, seguridad):** el 01000056Z es **un solo clip** (dos patas a 4.6 mm de la misma pieza de metal); si se suelda, puentea el fusible. Hay que medir el BLX-A de Sigma y hacer un footprint propio (`EVSE.PcbLib`) con los dos clips o los pines del portafusible completo.
- [ ] F1B y F2B: medir un BLX-A de Sigma (número de pines, distancia entre pines, sección del pin) para el footprint nuevo.
- [ ] Pads ovalados en J1 (TB001-500-02BE; hoy Ø1.95 mm, agujero 1.3 mm, paso 5.0 mm → 3.05 mm entre pads): de Ø1.95 mm a 1.7 × 3.0 mm (eje largo perpendicular a la línea entre pines), para lograr ≥ 3.2 mm entre L1 y L2. Se hace en `SamacSys.PcbLib`.
- [ ] PDF: se revisa al final de la sesión de F3 junto con todo el proyecto (`docs/revisiones/PROYECTO_F3.pdf`).

Ya verificado y correcto: fusibles con alternos en paralelo, varistor, IRM-20-12, D1, D2 y D3 en el sentido correcto, filtro EMI con C3 entre Vin y Vout, R-78CK, filtro LC, FB1 desde `+3V3`, R1–LED1, TP en `+VIN`, `+3V3` y `+3V3A`, puertos `AC_L1_F`/`AC_L2_F`.

### Parámetros de F2 (se ponen en la librería)

| Ref. | Número de parte | `Value` | `Supplier` | `Supplier PN` | `Assembly` |
|---|---|---|---|---|---|
| PS1 | IRM-20-12 | 12V 1.8A | Sigma | IRM-20-12 | Manual |
| U1 | R-78CK3.3-0.5 | 3.3V 0.5A | Disponible | - | Manual |
| J1 | TB001-500-02BE (equivale a la ED1621) | 2P 5.0mm 300V | Sigma | ED1621 | Manual |
| J6 | 1751248 (equivale a la bornera de 3.5 mm) | 2P 3.5mm | Sigma | BORNE 3.5MM 2P V | Manual |
| F1, F2 | 3403.0274.23 | T1A 277VAC | PCBWay | 3403.0274.23 | PCBWay |
| F1B, F2B | 01000056Z (equivale al BLX-A) | 5x20 | Sigma | BLX-A | DNP |
| RV1 | B72660M0301K072 | 300VAC | PCBWay | B72660M0301K072 | PCBWay |
| D1, D2 | SS34-E3/57T | 40V 3A | PCBWay | SS34-E3/57T | PCBWay |
| D3 | SMBJ15A | 15V 600W | PCBWay | SMBJ15A | PCBWay |
| C1 | EEE-FK1V101P | 100uF 35V | PCBWay | EEE-FK1V101P | PCBWay |
| C7 | EEE-FK1C101P | 100uF 16V | PCBWay | EEE-FK1C101P | PCBWay |
| L1 | RLS-126 | 12uH | PCBWay | RLS-126 | PCBWay |
| L2 | SRR4028-2R2Y | 2.2uH | PCBWay | SRR4028-2R2Y | PCBWay |
| C2 | CL31B106KBHNNNE | 10uF 50V | PCBWay | CL31B106KBHNNNE | PCBWay |
| C3 | C0805C102J5GAC-TU | 1nF 50V C0G | PCBWay | C0805C102J5GACTU | PCBWay |
| C4, C8 | CL21A106KAYNNNE | 10uF 25V | PCBWay | CL21A106KAYNNNE | PCBWay |
| C5, C6 | CL21A226MAQNNNE | 22uF 25V | PCBWay | CL21A226MAQNNNE | PCBWay |
| FB1 | BLM21PG221SN1D | 220R@100MHz | PCBWay | BLM21PG221SN1D | PCBWay |
| R1 | RC0805FR-071KL | 1k | PCBWay | RC0805FR-071KL | PCBWay |
| LED1 | APT2012SGC | verde | PCBWay | APT2012SGC | PCBWay |
| TP1–TP4 | Keystone 5016 | TP | PCBWay | 5016 | PCBWay |

## Qué se hizo en la Fase 2

- PDF recortado: la causa es la escala de Windows al 125 %; `docs/tools/arreglar_pdf.py` lo corrige.
- Rejilla de 100 mil en las hojas 02–06; aviso «Off grid object» en «No Report».
- Componentes elegidos y registrados en `docs/DECISIONES.md` («Fase 2»): IRM-20-12, ED1621, dos UMT-H T1A con portafusibles alternos DNP, CU4032K300G2, SS34 ×2, SMBJ15A, filtro EMI de RECOM, filtro LC de 2.2 µH, ferrita para `+3V3A`, LED y puntos de prueba.
- Cálculos en `docs/calculos/F2_ALIMENTACION.md`: presupuesto de potencia (`+3V3` ≈ 417 mA en el pico, `+VIN` ≈ 2.1 W), fusible (I²t), varistor, filtro LC y verificación del R-78CK.
- Corrección: el rizado del R-78CK es de 50 mVpp (Rev. 1-2025), no el 10 % de Vout.
- Nuevo ritmo de trabajo por fase y regla de 0805 (ver `CLAUDE.md` y la memoria).

## Dónde estamos

<!--DIAG:F3-->
```text
► ESTÁS AQUÍ: FASE 3 · 03_MEDICION.SchDoc — se diseñan los bloques ▐marcados▌

EXTERNO · instalación (fuera de la PCB)
  [Breaker del EVSE] ─┬─► ▐F3 CT en L1▌ ─► [EVSE] ─► [Vehículo]
                      │         │           ▲  │
                      └─► J1    └─► J3      │  └─ sonda DS18B20 ─► J4
                                            └─ J2 (bornes de habilitación)
════════════════════════════════════════════════════════════════════════════════════════════════════════════════
PCB        ZONA RED · 120–240 VAC                     ┃ BARRERA  ┃      ZONA SELV · 12 V y 3.3 V
                                                      ┃ ≥ 6.4 mm ┃
                                                      ┃          ┃
 ENERGÍA   J1 ─► [F2 Protección] ─┬───────────────────┨  AC-DC   ┠─► [F2 Riel 12 V] ─► [F2 R-78CK + LC] ─► 3V3
                                  │                   ┃   (F2)   ┃
►MEDICIÓN V                       └─► ▐F3 Divisor▌ ───┨▐ AMC3330▌┠─► V ─► ▐F3 ATM90E26▌ ═SPI═► ESP32-S3
                                                      ┃   (F3)   ┃              ▲ I
►MEDICIÓN I                                           ┃          ┃              └─◄ ▐F3 Carga CT▌ ◄─ J3
                                                      ┃          ┃
 ACTUACIÓN J2 ◄── contacto seco (aislado) ────────────┨   Relé   ┠◄─ bobina ─ [F6 Driver relé] ◄─ GPIO ─ ESP32-S3
                                                      ┃   (F6)   ┃
 CONTROL                                              ┃          ┃   [F4 ESP32-S3] ─ WiFi ─► router ─► internet ─► app
 INTERFAZ                                             ┃          ┃ J5 ─► [F4 USB-C · botones · LEDs] ─► ESP32-S3
 SENSORES                                             ┃          ┃ J4 ─► [F5 Sensores · RTC · FRAM] ─► ESP32-S3
 BANCO                                                ┃          ┃ J6 ─► [F2 Entrada banco 12 V] ─► D2 ─► +VIN
════════════════════════════════════════════════════════════════════════════════════════════════════════════════
[F# bloque] fase en que se diseña · ▐bloque▌ se diseña en ESTA fase · ► carril con trabajo en esta fase
┃ ┃ barrera de aislamiento · ┨ ┠ componente que cruza la barrera (AC-DC, AMC3330, relé)
│ L1/L2 (L/N en 120 V) con fusibles · J1–J6 conectores · J1 con cable largo a la línea · J2 contacto seco aislado
```
<!--/DIAG-->

## Tareas de la Fase 3

Detalle en `docs/PLAN_FASES.md`, sección Fase 3.

- [ ] Comparar y elegir, en un solo mensaje, con mini diagrama de la hoja:
  - [ ] Amplificador aislado: AMC3330 (elegido en P7) frente a 1–2 alternativas, para justificarlo.
  - [ ] Resistencias del divisor (1206 de alta tensión en serie, MELF o THT): tensión de trabajo, creepage y el surge de ≈ 775 V que deja pasar el varistor.
  - [ ] CT para 0–50 A (SCT-013-000, SCT-013-050 o de núcleo cerrado) y su conector J3.
  - [ ] IC de medición: ATM90E26 frente a ADE7953.
  - [ ] Cristal de 8.192 MHz y resistencias de carga de precisión (0.1 %).
- [ ] Dibujar la hoja: `AC_L1_F` → divisor → AMC3330 (referido a `AC_L2_F`); lado SELV desde `+3V3`; salida → ATM90E26 (AVDD desde `+3V3A`); J3 → carga del CT → filtro → entradas de corriente; IRQ, WarnOut, ZX y SPI a los puertos.
- [ ] Cálculos: divisor para 100–264 VAC, señal a 120 V y a 240 V, escala de I para 0–50 A, filtros.
- [ ] Verificar que ningún nodo SELV toque la red y el creepage del AMC3330 (≥ 8 mm según el datasheet).
- [ ] Clases de red `HV_AC` y `ANALOG`.
- [ ] Compilar, exportar `docs/revisiones/F3_MEDICION.pdf`, corregir y revisar.
- [ ] Cerrar la fase.

## Ten a mano

- Altium con el proyecto, el Library Loader de SamacSys y la librería de Altium.
- La página de Sigma Electrónica para precios y stock.
- Un BLX-A de Sigma y un calibrador (pendiente de F2).

## Pendientes que no son de esta fase

- Modelo y manual del EVSE (antes de F6): tensión y corriente de los bornes de habilitación, NA o NC.
- Confirmar si el tercer conductor de la instalación es neutro o tierra; el EVSE necesita tierra.
- Requisitos del profesor para el gabinete (F7); la IRM-20-12 mide 24 mm de alto.
- F7: corregir los `*` del bloque de título, copiar las librerías SamacSys a `lib/` y quitar `Job1.OutJob` del proyecto.
- Actualizar el artifact de referencia: la entrada de banco J6 quedó confirmada (antes era «propuesta»).
