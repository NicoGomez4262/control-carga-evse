# Siguiente sesión → Fase 7: cierre del esquemático y BOM (todas las hojas)

**Estado (12 oct 2026):** Fase 6 cerrada. La hoja `06_ACTUACION` está completa, anotada y revisada en `docs/revisiones/PROYECTO_F6.pdf` (6 hojas + BOM). Las seis hojas ya están dibujadas. Componentes, D15 (K1 = PhotoMOS) y lecciones en `docs/DECISIONES.md`, «Fase 6»; cierre en `docs/sesiones/F6_cerrada.md`.

## Prompt para iniciar

Cierra Altium antes de pegar esto en una sesión nueva de Claude abierta en la carpeta del repositorio:

```text
Iniciamos la FASE 7 del proyecto "Control de carga EVSE" en Altium: cierre del esquemático (todas las hojas) y BOM. Ya cerré Altium.

Lee CLAUDE.md, NEXT_SESSION.md, docs/PLAN_FASES.md (Fase 7) y docs/DECISIONES.md (registro D1–D15, «Componentes elegidos» y «Fase 6»).

Sigue el ritmo de CLAUDE.md:
1. Muéstrame el diagrama «ESTÁS AQUÍ» (como gráfico) y la lista de tareas.
2. Revisa por script todas las hojas (lista_redes.py -p, cobertura_blanket.py) y la librería (libreria.py): pines sueltos, redes con dos nombres, parámetros obligatorios vacíos, footprints que falten. Dame un informe por hoja con lo que está bien y lo que hay que corregir.
3. Todo lo que se pueda arreglar con un .py (parámetros, nota de la TOP, Blankets, piezas que sobran en la librería, bloque de título), hazlo tú (Altium cerrado, con respaldo) y dime siempre qué cambiaste.
4. Verifica los footprints pendientes contra el datasheet (J5, C2, C3, BT1, F1B/F2B, K1) con pcblib.py.
5. Arma la BOM con proveedor, número de parte, forma de montaje y precio, revisando stock en Sigma, PCBWay (LCSC) y Mouser; dime qué piezas de Mouser conviene mandar consignadas a PCBWay y cuáles soldar a mano.
6. Gabinete: pregúntame los requisitos del profesor y compara 2–3 opciones en un solo mensaje.
7. Al final, el PDF de todo el proyecto (docs/revisiones/PROYECTO_F7.pdf) y la BOM exportada.
```

## Dónde estamos

<!--DIAG:F7-->
```text
► ESTÁS AQUÍ: FASE 7 · todas las hojas — revisión completa y BOM (todo ▐marcado▌)

EXTERNO · instalación (fuera de la PCB)
  [Breaker del EVSE] ─┬─► ▐F3 CT en L1▌ ─► [EVSE] ─► [Vehículo]
                      │         │           ▲  │
                      └─► J1    └─► J3      │  └─ sonda DS18B20 ─► J4
                                            └─ J2 (bornes de habilitación)
════════════════════════════════════════════════════════════════════════════════════════════════════════════════
PCB        ZONA RED · 120–240 VAC                     ┃ BARRERA  ┃      ZONA SELV · 12 V y 3.3 V
                                                      ┃ ≥ 6.4 mm ┃
                                                      ┃          ┃
►ENERGÍA   J1 ─► ▐F2 Protección▌ ─┬───────────────────┨▐ AC-DC  ▌┠─► ▐F2 Riel 12 V▌ ─► ▐F2 R-78CK + LC▌ ─► 3V3
                                  │                   ┃   (F2)   ┃
►MEDICIÓN V                       └─► ▐F3 Divisor▌ ───┨▐ AMC3330▌┠─► V ─► ▐F3 ATM90E26▌ ═SPI═► ESP32-S3
                                                      ┃   (F3)   ┃              ▲ I
►MEDICIÓN I                                           ┃          ┃              └─◄ ▐F3 Carga CT▌ ◄─ J3
                                                      ┃          ┃
►ACTUACIÓN J2 ◄── contacto seco (aislado) ────────────┨▐PhotoMOS▌┠◄─ LED ─ ▐F6 Driver K1▌ ◄─ GPIO ─ ESP32-S3
                                                      ┃   (F6)   ┃
►CONTROL                                              ┃          ┃   ▐F4 ESP32-S3▌ ─ WiFi ─► router ─► internet ─► app
►INTERFAZ                                             ┃          ┃ J5 ─► ▐F4 USB-C · USB-UART · auto-reset · LEDs▌ ─► ESP32-S3
►SENSORES                                             ┃          ┃ J4 ─► ▐F5 Sensores · RTC▌ ─► ESP32-S3
►BANCO                                                ┃          ┃ J6 ─► ▐F2 Entrada banco 12 V▌ ─► D2 ─► +VIN
════════════════════════════════════════════════════════════════════════════════════════════════════════════════
[F# bloque] fase en que se diseña · ▐bloque▌ se diseña en ESTA fase · ► carril con trabajo en esta fase
┃ ┃ barrera de aislamiento · ┨ ┠ componente que cruza la barrera (AC-DC, AMC3330, PhotoMOS K1)
│ L1/L2 (L/N en 120 V) con fusibles · J1–J6 conectores · J1 con cable largo a la línea · J2 contacto seco aislado
```
<!--/DIAG-->
<!--/DIAG-->

## Tareas de la Fase 7

- [x] Diagrama «ESTÁS AQUÍ» y lista de tareas (14 oct).
- [x] Informe por script de todas las hojas y de la librería: sin pines sueltos ni redes con dos nombres; los 6 parámetros obligatorios completos; rieles como puertos de alimentación (14 oct).
- [ ] Compilar todo el proyecto (Validate): 0 errores y warnings revisados.
- [x] Anotación final de designadores: sin huecos (D1–D6 y la siguiente libre es D7); no hace falta re-anotar.
- [x] Revisión cruzada TOP ↔ hojas: entradas de hoja y puertos coinciden en nombre y dirección. Nota de rieles corregida por script (`+3V3` ya no va a ACTUACION) y línea de clases de red.
- [x] Clases de red: `USB` agregada (Blanket junto a U5); las dos Blankets `ANALOG` de 03 agrandadas 100 mil (`arreglos_hojas_f7.py`).
- [x] Footprints verificados contra el datasheet: J5 ✓ (plano Würth rev 003.000), C2 ✓ y C3 ✓ (tabla de pads del FK), K1 ✓ (se queda el de SamacSys: 6,70 mm entre lados), BT1 corregido al plano TE rev E1, F1B/F2B → footprint nuevo `BLX-A_5X20` (`libreria_f7.py`).
- [x] Librería: SamacSys copiada a `lib/` del proyecto (58 piezas + BLX-A; 38 sin uso fuera), modelos de footprint y `.PrjPcb` apuntando a `lib/`. La de `Documents/AltiumLL` no se tocó.
- [ ] BOM (ActiveBOM): Designator, Qty, Manufacturer, MPN, Description, Footprint, Supplier, Supplier PN, Assembly y precio.
- [ ] Stock verificado (Sigma, PCBWay/LCSC y Mouser). Decidir qué piezas de Mouser van consignadas a PCBWay (AMC3330DWE, ESP32-S3-WROOM-1-N16R2, J5, AQY414EHAX) y qué se suelda a mano.
- [ ] Gabinete (2–3 opciones según los requisitos del profesor): define el contorno de la PCB y dónde van los conectores (J1–J4, J6, J7 en un borde).
- [ ] Revisión de diseño con lista: seguridad y aislamiento, potencia, arranque, ESD en conectores, puntos de prueba, valores.
- [x] Bloque de título: `Title` en cada hoja, sin `*` en las direcciones, texto «PROPERTY OF ALTIUM» reemplazado y sin logo de Altium (tapaba el nombre del proyecto); `Job1.OutJob` fuera del proyecto; Revision 1.0. ProjectName, Revision y DrawnBy ya salían del proyecto (no hizo falta renombrarlos).
- [ ] Exportar `docs/revisiones/PROYECTO_F7.pdf` y la BOM (`docs/revisiones/F7_BOM.*`) y revisarlos.
- [ ] Cerrar la fase (CLAUDE.md). La BOM con precios es la base del **carrito de compras** de F8.

**Componentes a comparar en F7:** solo el gabinete (2–3 opciones) y los reemplazos de lo que no tenga stock.

## Herramientas disponibles (`docs/tools/`)

- `lista_redes.py -p`, `cobertura_blanket.py`, `render_hoja.py`, `pcblib.py`, `libreria.py` (`--pieza`, `--poner`, `--copiar`), `arreglar_pdf.py`, `diagramas.py`.
- `hoja.py` + `altium_ole.py`: edición del .SchDoc registro por registro; Blankets en el stream «Additional».
- Ejemplos de arreglos: `arreglos_hoja05.py`, `arreglos_hoja06.py` (borrar piezas, designadores, parámetros desde la librería, Blankets); `piezas_f6.py` (copia con el símbolo redibujado).
- Esquemas: `esquemas.py`, `esquemas_f4.py`, `esquemas_f5.py`, `esquemas_f6.py` (con `revisar()` para renderizar antes de mostrar).

## Ten a mano

- **Altium cerrado al empezar** (revisar en el Administrador de tareas que no quede `X2.EXE`).
- Los requisitos del profesor para el gabinete (tamaño, material, IP, montaje).
- Acceso a Sigma, LCSC y Mouser (si Mouser bloquea el navegador de Claude, revisar a mano algún número).
- La tasa de cambio COP/USD del día (para los precios).

## Qué se hizo en la Fase 6

- P3: EVSE genérico, tensión y corriente desconocidas (peor caso) y **NC** sin energía.
- K1: el relé Finder 34.51 dorado no está en Mouser (el Phoenix equivalente cuesta US$22). Se cambió por el **PhotoMOS AQY414EHAX** (D15): NC, 400 V, 120 mA, 5000 Vrms reforzado, sin carga mínima, US$3,42. Para NA se usa el AQY214EHAX en el mismo footprint.
- Driver: `RELAY_EN` → R39 1 kΩ → Q3 AO3400A (R40 10 kΩ a GND); `+VIN` → R41 1 kΩ → LED6 KT-0805Y → LED de K1 (≈ 8,4 mA). J2 = ED1621 (2 polos). Clase `EVSE_EXT` con dos Blankets.
- Por script: AO3400A (símbolo de MOSFET redibujado) y KT-0805Y en la librería; parámetros de `AQY-414EHAX`; arreglos de la hoja (3 piezas sueltas borradas, designadores, Blankets).
- Se verificó que todos los rieles (`+VIN`, `+3V3`, `+3V3A`, `GND`) son **puertos de alimentación** en todas las hojas (ninguno es net label) y que el proyecto usa «power ports global».
- Plan: se agregó el **carrito de compras** a F8 (pedido del usuario).

## Pendientes que no son de esta fase

- F1B/F2B: el 01000056Z es un solo clip y puentearía el fusible; medir el BLX-A de Sigma y hacer un footprint propio (antes de F8).
- Confirmar si el tercer conductor de la instalación es neutro o tierra; el EVSE necesita tierra.
- Medir la tensión y la corriente de los bornes de habilitación del EVSE: K1 aguanta ≤ 120 mA y lo recomendado es ≤ 320 V pico. Si son de red, poner un relé externo.
- F8: sin cobre debajo de K1 ni de U6 (AHT20) y, si cabe, ranura de 1,5 mm alrededor de U6; C39 pegado al pin 2 de U7; D6 junto a J4; reglas de `EVSE_EXT` (≥ 6,4 mm hacia SELV y `HV_AC`); carrito de compras con el total.
- Firmware: SPI del ATM90E26 ≤ 160 kbps y LNSel = N; CH340C con esptool en auto-reset; AHT20 espera ≥ 5 ms tras encender; búfer sin internet en partición de datos y energía en NVS cada minuto (D14); hora del DS3231 por NTP; `RELAY_EN` = 1 → carga parada, y al arrancar restaurar el estado desde NVS.
- P10: dónde va la sonda DS18B20 y qué temperatura máxima acepta el EVSE.
