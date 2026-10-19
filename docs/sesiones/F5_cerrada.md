# Sesión cerrada → Fase 5: sensores, RTC y memoria (`05_SENSORES.SchDoc`)

**Cerrada el 12 oct 2026 (misma sesión).** Resultado en `docs/DECISIONES.md`, «Fase 5», y D14 (sin FRAM). Texto original del inicio de la fase:

**Estado (12 oct 2026):** Fase 4 cerrada. La hoja `04_MCU` está completa, anotada y revisada en `docs/revisiones/PROYECTO_F4.pdf`; los pendientes de F3 también quedaron resueltos (Blankets de `HV_AC` y `ANALOG`, puertos de alimentación, parámetros de los TP). Componentes, mapa de pines definitivo y lecciones en `docs/DECISIONES.md`, «Fase 4». El cierre de F4 está en `docs/sesiones/F4_cerrada.md`.

## Prompt para iniciar

Cierra Altium antes de pegar esto en una sesión nueva de Claude abierta en la carpeta del repositorio:

```text
Iniciamos la FASE 5 del proyecto "Control de carga EVSE" en Altium: hoja 05_SENSORES.SchDoc. Ya cerré Altium.

Lee CLAUDE.md, NEXT_SESSION.md, docs/PLAN_FASES.md (Fase 5) y docs/DECISIONES.md (P5, «Fase 4» y «Mapa de pines del ESP32-S3»).

Sigue el ritmo de CLAUDE.md:
1. Muéstrame el diagrama «ESTÁS AQUÍ» (como gráfico) y la lista de tareas.
2. En un solo mensaje, todos los componentes de F5 con sus comparaciones (datasheet; Sigma y PCBWay primero, Mouser solo si no hay; 0805 o más grande) y un mini diagrama de la hoja con las referencias que siguen a F4 (U6, R32, C37, D6, J4…). Verifica que las direcciones I²C no choquen. Separa la lista en: (a) piezas sin símbolo ni footprint, ordenadas por prioridad para bajarlas de SamacSys (la cuota diaria es limitada), y (b) piezas que se crean copiando una que ya está en SamacSys.SchLib/PcbLib con el mismo encapsulado; esas créalas tú con docs/tools/libreria.py --copiar.
3. Todo lo de librerías, números de parte, parámetros y ediciones largas que puedas hacer con un .py, hazlo tú (Altium cerrado, con respaldo) y dime siempre qué cambiaste.
4. Cuando apruebe los componentes, dame los esquemas literales por bloque, revisa la hoja con lista_redes.py y render_hoja.py y, al final, el PDF de todo el proyecto (docs/revisiones/PROYECTO_F5.pdf).
```

## Dónde estamos

<!--DIAG:F5-->
```text
► ESTÁS AQUÍ: FASE 5 · 05_SENSORES.SchDoc — se diseñan los bloques ▐marcados▌

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
 ACTUACIÓN J2 ◄── contacto seco (aislado) ────────────┨   Relé   ┠◄─ bobina ─ [F6 Driver relé] ◄─ GPIO ─ ESP32-S3
                                                      ┃   (F6)   ┃
 CONTROL                                              ┃          ┃   [F4 ESP32-S3] ─ WiFi ─► router ─► internet ─► app
 INTERFAZ                                             ┃          ┃ J5 ─► [F4 USB-C · USB-UART · auto-reset · LEDs] ─► ESP32-S3
►SENSORES                                             ┃          ┃ J4 ─► ▐F5 Sensores · RTC · FRAM▌ ─► ESP32-S3
 BANCO                                                ┃          ┃ J6 ─► [F2 Entrada banco 12 V] ─► D2 ─► +VIN
════════════════════════════════════════════════════════════════════════════════════════════════════════════════
[F# bloque] fase en que se diseña · ▐bloque▌ se diseña en ESTA fase · ► carril con trabajo en esta fase
┃ ┃ barrera de aislamiento · ┨ ┠ componente que cruza la barrera (AC-DC, AMC3330, relé)
│ L1/L2 (L/N en 120 V) con fusibles · J1–J6 conectores · J1 con cable largo a la línea · J2 contacto seco aislado
```
<!--/DIAG-->

## Tareas de la Fase 5

- [x] Diagrama «ESTÁS AQUÍ» y lista de tareas.
- [x] Comparar y elegir (2–3 opciones cada uno, en un solo mensaje):
  - [x] Sensor de ambiente I²C: SHT40, TMP117 o AHT20.
  - [x] RTC: DS3231, RV-3028-C7 o PCF85063A; portapila CR2032 (o supercondensador) y si `RTC_INT` necesita pull-up (salida de drenador abierto).
  - [x] Memoria: FRAM MB85RC256V, FM24CL64B o EEPROM 24LC256. Dimensionar con el búfer de mediciones sin internet (P5) y decidir si basta la flash de 16 MB del módulo N16R2.
  - [x] J4 para la sonda DS18B20 (3 polos: 3V3, DATA, GND), su ESD y la resistencia serie.
- [x] Lista (a) SamacSys por prioridad y (b) copias hechas por script.
- [x] Esquemas literales por bloque (`docs/esquemas/F5_*.svg`, con las funciones de `esquemas.py` y `esquemas_f4.py`).
- [x] Dibujar la hoja: bus I²C con pull-ups de 4,7 kΩ (una sola pareja en todo el bus), direcciones sin conflicto, J4 con 4,7 kΩ de pull-up, 100 Ω en serie y ESD; RTC con pila e INT; memoria; desacoples de 100 nF por IC.
- [x] La hoja ya tiene los puertos `I2C_SCL`, `I2C_SDA`, `OW_DATA` y `RTC_INT`; al conectarlos desaparecen los avisos «only one pin» de esas redes.
- [x] Revisar con `lista_redes.py -p`, `render_hoja.py` y Validate (Messages sin errores; solo queda `RELAY_EN`, que se cierra en F6).
- [x] Exportar `docs/revisiones/PROYECTO_F5.pdf` (todas las hojas), arreglarlo con `arreglar_pdf.py` y revisarlo.
- [x] Cerrar la fase (CLAUDE.md).

**Pines del ESP32-S3 ya asignados en F4:** `I2C_SDA` IO8, `I2C_SCL` IO9, `OW_DATA` IO4, `RTC_INT` IO18. Libres para F5 si hicieran falta: IO1, IO2, IO3, IO19, IO20, IO35–IO42 (IO38 reservado para un zumbador), IO45–IO48 (45 y 46 son de strapping: no usarlos como salida).

**Siguiente numeración:** U6, R32, C37, D6, Q3, LED6, SW4, TP7, BT1; J4 está reservado para la sonda DS18B20.

## Herramientas disponibles (`docs/tools/`)

- `libreria.py`: auditoría de `SamacSys.SchLib`, `--pieza`, `--poner` (parámetros) y `--copiar ORIG NUEVA k=v` (piezas del mismo encapsulado sin gastar descargas).
- `hoja.py` + `altium_ole.py`: edición de un .SchDoc registro por registro (respaldo en `docs/respaldos/`). Los Blankets van en el stream «Additional»; el «Weight» de la cabecera = número de registros.
- `lista_redes.py -p`, `cobertura_blanket.py`, `render_hoja.py` (hoja → SVG/PNG para revisarla), `pcblib.py` (pads de un footprint), `arreglar_pdf.py`, `diagramas.py`.
- `esquemas.py` y `esquemas_f4.py` (agrega `ic`, `conectar`, `npn`, `led_v`, `sw_v`).

## Ten a mano

- **Altium cerrado al empezar.**
- La cuota del día del Library Loader de SamacSys: primero el RTC, el sensor y la memoria; el portapila y el conector J4 después.
- La página de Sigma Electrónica para stock y precios.

## Qué se hizo en la Fase 4

- Componentes elegidos (`docs/DECISIONES.md`, «Fase 4»): ESP32-S3-WROOM-1-N16R2 (U4), CH340C (U5) con auto-reset de 2 × MMBT3904 (Q1, Q2), USB-C Würth 632723300011 (J5) con USBLC6-2SC6 (D5) y Rd de 5,1 kΩ, RC de EN 10 kΩ/1 µF, SW1 (RESET) + J7 para el botón PARAR del panel, SW2/SW3 de prueba sin montar, 3 LEDs y J8 de programación.
- Pendientes de F3 resueltos: Blankets `HV_AC` y `ANALOG`, puertos de alimentación en 03, parámetros de los TP, librería corregida.
- Herramientas nuevas: `altium_ole.py`, `libreria.py`, `hoja.py`, `render_hoja.py`, `pcblib.py`, `esquemas_f4.py`.
- Lecciones: en una misma hoja una net label y un puerto con el mismo nombre **no se unen**; *Update From Libraries → Full replacement* borra los parámetros de las piezas del Content Vault (se reponen por script).

## Pendientes que no son de esta fase

- F7: comparar el footprint del Content Vault de J5 (Würth 632723300011) con el plano del datasheet: patas de la carcasa y agujeros redondos de 0,6 mm frente a ranuras.
- F7: verificar los footprints de C2 y C3 de la hoja 02 (`EEHZT1E331UP`, `EEE1AA101SP`).
- F1B/F2B: el 01000056Z es un solo clip y puentearía el fusible; medir el BLX-A de Sigma y hacer un footprint propio (antes de F8).
- Modelo y manual del EVSE (antes de F6): tensión y corriente de los bornes de habilitación, NA o NC.
- Confirmar si el tercer conductor de la instalación es neutro o tierra; el EVSE necesita tierra.
- Requisitos del profesor para el gabinete (F7); la IRM-20-12 mide 24 mm de alto.
- F7: corregir los `*` del bloque de título, copiar las librerías SamacSys a `lib/` y quitar `Job1.OutJob` del proyecto.
- Firmware: el SPI del ATM90E26 va a ≤ 160 kbps y, en modo flexible, hay que poner LNSel = N; CH340C con esptool en modo auto-reset por defecto.
