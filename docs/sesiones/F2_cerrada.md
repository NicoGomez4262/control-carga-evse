# Siguiente sesión → Fase 2: alimentación (`02_ALIMENTACION.SchDoc`)

**Estado del proyecto (7 oct 2026):** Fase 1 cerrada. Arquitectura en **Rev C** y proyecto de Altium creado con la hoja TOP conectada (0 errores).
**Esta sesión cubre:** la hoja de alimentación completa, de J1 (red 100–264 VAC) a los rieles `+VIN` (12 V), `+3V3` y `+3V3A`.

## Prompt para iniciar

Copia y pega esto en una sesión nueva de Claude abierta en la carpeta del repositorio:

```text
Iniciamos la FASE 2 del proyecto "Control de carga EVSE" en Altium: hoja 02_ALIMENTACION.SchDoc.

Antes de empezar, lee CLAUDE.md, NEXT_SESSION.md, docs/PLAN_FASES.md (sección Fase 2) y docs/DECISIONES.md.

En esta sesión:
1. Muéstrame el diagrama de bloques con la ubicación de la Fase 2 y la lista de tareas.
2. Primero ayúdame a arreglar la exportación a PDF recortada que quedó de F1.
3. Para cada componente de la lista, compara 2–3 opciones con datos del datasheet (Sigma y PCBWay primero, Mouser solo si no hay) y recomiéndame una; registra mis elecciones en docs/DECISIONES.md.
4. Guíame paso a paso en Altium 25.4.2 (dónde estar parado, qué clic, qué debo ver) para dibujar la hoja, con componentes bajados de SamacSys y los parámetros obligatorios.
5. Haz los cálculos (potencia, fusible, varistor, filtro LC) y documéntalos.
6. Cuando exporte docs/revisiones/F2_ALIMENTACION.pdf, revísalo y dime qué corregir.
7. Al completar la lista, cierra la fase como indica CLAUDE.md y deja listo el NEXT_SESSION.md de la Fase 3.
```

## Qué se hizo en la Fase 1

- P1–P7 respondidas (detalle en `docs/DECISIONES.md`):
  - **P1:** red universal de 120 V L–N a 240 V L1–L2 → **100–264 VAC**. En 120 V, `AC_L2` es el neutro.
  - **P2/D7:** **sin contactor**. Un relé une o separa los bornes de habilitación del EVSE; la placa solo mide la corriente (0–50 A).
  - **P3:** relé 1C con J2 de 3 bornes; NA o NC se define con el modelo del EVSE.
  - **P4:** caja plástica junto al EVSE, bajo techo, clase II; **cable largo** de J1 a la línea.
  - **P5/D8:** la ESP32 sube los datos por internet a la app propia (conexión saliente con TLS, sin VPN).
  - **P6:** IC de medición ATM90E26.
  - **P7/D9:** divisor resistivo + **AMC3330** (reemplaza al ZMPT101B).
  - Riel de entrada: **12 V** preferido.
- Mouser como proveedor de última opción (D6).
- Proyecto en `C:/Nicolas/UNIVERSIDAD - 2026/Hardware en IoT/Control de Carga IoT/Control de Carga IoT/Control de Carga IoT.PrjPcb` (D12): hojas 01–06, PCB vacía, alcance jerárquico, TOP con 13 conexiones; valida con 0 errores.
- Librerías: SamacSys usada directamente (hoy en `C:/Users/nico/Documents/AltiumLL/`); el R-78CK3.3-0.5 ya tiene footprint y parámetros (D10).

## Dónde estamos

<!--DIAG:F2-->
```text
► ESTÁS AQUÍ: FASE 2 · 02_ALIMENTACION.SchDoc — se diseñan los bloques ▐marcados▌

EXTERNO · instalación (fuera de la PCB)
  [Breaker del EVSE] ─┬─► [F3 CT en L1] ─► [EVSE] ─► [Vehículo]
                      │         │           ▲  │
                      └─► J1    └─► J3      │  └─ sonda DS18B20 ─► J4
                                            └─ J2 (bornes de habilitación)
════════════════════════════════════════════════════════════════════════════════════════════════════════════════
PCB        ZONA RED · 120–240 VAC                     ┃ BARRERA  ┃      ZONA SELV · 12 V y 3.3 V
                                                      ┃ ≥ 6.4 mm ┃
                                                      ┃          ┃
►ENERGÍA   J1 ─► ▐F2 Protección▌ ─┬───────────────────┨▐ AC-DC  ▌┠─► ▐F2 Riel 12 V▌ ─► ▐F2 R-78CK + LC▌ ─► 3V3
                                  │                   ┃   (F2)   ┃
 MEDICIÓN V                       └─► [F3 Divisor] ───┨  AMC3330 ┠─► V ─► [F3 ATM90E26] ═SPI═► ESP32-S3
                                                      ┃   (F3)   ┃              ▲ I
 MEDICIÓN I                                           ┃          ┃              └─◄ [F3 Carga CT] ◄─ J3
                                                      ┃          ┃
 ACTUACIÓN J2 ◄── contacto seco (aislado) ────────────┨   Relé   ┠◄─ bobina ─ [F6 Driver relé] ◄─ GPIO ─ ESP32-S3
                                                      ┃   (F6)   ┃
 CONTROL                                              ┃          ┃   [F4 ESP32-S3] ─ WiFi ─► router ─► internet ─► app
 INTERFAZ                                             ┃          ┃ J5 ─► [F4 USB-C · botones · LEDs] ─► ESP32-S3
 SENSORES                                             ┃          ┃ J4 ─► [F5 Sensores · RTC · FRAM] ─► ESP32-S3
►BANCO                                                ┃          ┃ J6 ─► ▐F2 Jack 12 V banco▌ ─► riel (propuesta)
════════════════════════════════════════════════════════════════════════════════════════════════════════════════
[F# bloque] fase en que se diseña · ▐bloque▌ se diseña en ESTA fase · ► carril con trabajo en esta fase
┃ ┃ barrera de aislamiento · ┨ ┠ componente que cruza la barrera (AC-DC, AMC3330, relé)
│ L1/L2 (L/N en 120 V) con fusibles · J1–J6 conectores · J1 con cable largo a la línea · J2 contacto seco aislado
```
<!--/DIAG-->

## Tareas de la Fase 2

- [x] Arreglar la exportación a PDF recortada (quedó de F1) y desactivar el aviso «Off grid object». → rejilla de 100 mil en las hojas 02–06 y aviso en «No Report»; el PDF sale al 80 % por la escala de Windows al 125 % («Source Document» no lo arregla): se corrige con `python docs/tools/arreglar_pdf.py <pdf>`.
- [x] Confirmar el riel de 12 V con la comparación de fuentes. → 12 V (presupuesto en `docs/calculos/F2_ALIMENTACION.md`).
- [ ] Entrada universal 100–264 VAC, 50/60 Hz: 120 V L–N o 240 V L1–L2 en el mismo J1.
- [ ] Comparar y elegir (2–3 opciones cada uno):
  - [x] Módulo AC-DC → **Mean Well IRM-20-12** (Sigma); símbolo y footprint de SamacSys verificados; faltan sus parámetros `Supplier`, `Supplier PN`, `Assembly`, `Value`.
  - [x] Bornera J1 de 2 polos → **ED1621** (Sigma), pads ovalados para L1–L2 ≥ 3.2 mm.
  - [x] Fusibles → **dos Schurter UMT-H T1A** (PCBWay), uno por línea, con footprint alterno DNP para portafusible BLX-A (F1B, F2B).
  - [x] Varistor RV1 → **TDK CU4032K300G2** (PCBWay).
  - [x] Condensador de entrada del R-78CK y bulk de `+VIN` → C1 Panasonic EEE-FK1V101P (100 µF 35 V); filtro EMI RECOM: L1 RLS-126 + C2 10 µF 50 V + C3 1 nF.
  - [x] TVS de `+VIN` → D3 SMBJ15A.
  - [x] Filtro LC → L2 Sunlord SWPA4030S2R2MT 2.2 µH + C4 10 µF + C5/C6 22 µF + C7 100 µF 16 V (EEE-FK1C101P); `+3V3A` → FB1 BLM18PG221SN1D + C8 10 µF.
  - [x] Entrada de banco J6 → bornera de 3.5 mm 2P (Sigma); diodos OR D1/D2 SS34. LED1 verde 0603 + R1 1 kΩ en `+3V3`; TP1–TP4 Keystone 5015.
  - Todo aprobado por el usuario el 2026-10-07 (diagrama de la hoja en la conversación de F2).
- [ ] Dibujar la hoja: J1 → fusibles → RV1 → AC-DC → `+VIN` (TVS, bulk) → R-78CK3.3-0.5 → filtro LC → `+3V3`; ferrita → `+3V3A`; LED de encendido; puntos de prueba `TP_VIN`, `TP_3V3`, `TP_GND`; puertos `AC_L1_F`, `AC_L2_F` (ya existen en la hoja).
- [ ] Cálculos documentados: presupuesto de potencia por riel (incluye el AMC3330 y la bobina del relé), disipación, filtro LC, fusible (corriente, I²t, inrush del AC-DC), varistor.
- [ ] Verificar el R-78CK: entrada ≥ 5 V siempre (UVLO 4.4 V), 27 µF en la entrada, carga capacitiva ≤ 2000 µF.
- [ ] Clase de red `HV_AC` en `AC_L1`, `AC_L2`, `AC_L1_F`, `AC_L2_F`.
- [ ] Serigrafía de J1 («L1/L», «L2/N») y nota sobre la protección del cable largo en el tablero (breaker de 2–6 A o portafusible).
- [ ] Footprints y parámetros completos.
- [ ] Compilar, exportar `docs/revisiones/F2_ALIMENTACION.pdf` y revisar.
- [ ] Cerrar la fase.

## Ten a mano

- Altium abierto con el proyecto y el Library Loader de SamacSys.
- Acceso a la página de Sigma Electrónica para confirmar precios y stock.
- El R-78CK3.3-0.5 y su datasheet: https://recom-power.com/pdf/Innoline/R-78CK-0.5.pdf

## Pendientes que no son de esta fase

- Modelo y manual del EVSE (antes de F6): tensión y corriente de los bornes de habilitación, NA o NC.
- Confirmar si el tercer conductor de la instalación es neutro o tierra (color y barra del tablero); el EVSE necesita tierra.
- Requisitos del profesor para el gabinete (F7).
- F7: corregir los `*` del bloque de título y copiar las librerías SamacSys a `lib/` del proyecto.
