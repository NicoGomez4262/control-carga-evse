# Sesión cerrada → Fase 6: actuación (`06_ACTUACION.SchDoc`)

**Cerrada el 12 oct 2026.** Resultado en `docs/DECISIONES.md`, «Fase 6», y D15 (K1 = PhotoMOS AQY414EHAX). Texto de trabajo de la fase:

**Estado (12 oct 2026):** Fase 5 cerrada. La hoja `05_SENSORES` está completa, anotada y revisada en `docs/revisiones/PROYECTO_F5.pdf`. Validate solo deja el aviso de `RELAY_EN`, que se cierra en esta fase. Componentes, decisiones (D14: sin FRAM) y lecciones en `docs/DECISIONES.md`, «Fase 5»; cierre de F5 en `docs/sesiones/F5_cerrada.md`.

## Prompt para iniciar

Cierra Altium antes de pegar esto en una sesión nueva de Claude abierta en la carpeta del repositorio:

```text
Iniciamos la FASE 6 del proyecto "Control de carga EVSE" en Altium: hoja 06_ACTUACION.SchDoc. Ya cerré Altium.

Lee CLAUDE.md, NEXT_SESSION.md, docs/PLAN_FASES.md (Fase 6) y docs/DECISIONES.md (D7, P2, P3, «Fase 4», «Fase 5» y «Mapa de pines del ESP32-S3»).

Sigue el ritmo de CLAUDE.md:
1. Muéstrame el diagrama «ESTÁS AQUÍ» (como gráfico) y la lista de tareas.
2. Antes de proponer el relé, pregúntame lo que sepas que falta del EVSE (P3: tensión y corriente de los bornes de habilitación, lógica, NA o NC). Después, en un solo mensaje, todos los componentes de F6 con sus comparaciones (datasheet; Sigma y PCBWay primero, Mouser solo si no hay; 0805 o más grande) y un mini diagrama de la hoja con las referencias que siguen a F5 (U8, R39, C41, D7, Q3, LED6, K1, J2). Revisa la carga mínima de contacto del relé y el aislamiento reforzado bobina–contacto (creepage ≥ 6,4 mm hacia J2). Separa la lista en (a) piezas sin símbolo ni footprint, ordenadas por prioridad para bajarlas de SamacSys, y (b) piezas que se crean copiando una que ya está en SamacSys.SchLib/PcbLib con el mismo encapsulado; esas créalas tú por script.
3. Todo lo de librerías, números de parte, parámetros y ediciones largas que puedas hacer con un .py, hazlo tú (Altium cerrado, con respaldo) y dime siempre qué cambiaste.
4. Cuando apruebe, antes de dibujar dame la lista de TODAS las piezas que debo poner desde SamacSys.SchLib (con designadores) para ponerlas de una vez; luego los esquemas literales por bloque, la revisión de la hoja con lista_redes.py y render_hoja.py y, al final, el PDF de todo el proyecto (docs/revisiones/PROYECTO_F6.pdf).
```

## Dónde estamos

<!--DIAG:F6-->
```text
► ESTÁS AQUÍ: FASE 6 · 06_ACTUACION.SchDoc — relé y salida J2 a los bornes de habilitación del EVSE ▐marcados▌

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
►ACTUACIÓN J2 ◄── contacto seco (aislado) ────────────┨▐  Relé  ▌┠◄─ bobina ─ ▐F6 Driver relé▌ ◄─ GPIO ─ ESP32-S3
                                                      ┃   (F6)   ┃
 CONTROL                                              ┃          ┃   [F4 ESP32-S3] ─ WiFi ─► router ─► internet ─► app
 INTERFAZ                                             ┃          ┃ J5 ─► [F4 USB-C · USB-UART · auto-reset · LEDs] ─► ESP32-S3
 SENSORES                                             ┃          ┃ J4 ─► [F5 Sensores · RTC] ─► ESP32-S3
 BANCO                                                ┃          ┃ J6 ─► [F2 Entrada banco 12 V] ─► D2 ─► +VIN
════════════════════════════════════════════════════════════════════════════════════════════════════════════════
[F# bloque] fase en que se diseña · ▐bloque▌ se diseña en ESTA fase · ► carril con trabajo en esta fase
┃ ┃ barrera de aislamiento · ┨ ┠ componente que cruza la barrera (AC-DC, AMC3330, relé)
│ L1/L2 (L/N en 120 V) con fusibles · J1–J6 conectores · J1 con cable largo a la línea · J2 contacto seco aislado
```
<!--/DIAG-->
<!--/DIAG-->

## Tareas de la Fase 6

- [x] Diagrama «ESTÁS AQUÍ» y lista de tareas (sesión del 12 oct, cortada por el límite de uso).
- [x] Datos del EVSE (P3), respondidos el 12 oct: **EVSE genérico**; tensión en los bornes **desconocida → peor caso hasta 250 VAC**; corriente **desconocida** (el usuario preguntará más adelante; cubrir de ~2 mA a cientos de mA); lógica unidos = carga (P2); **sin energía debe cargar normal → se usa el contacto NC** (relé en reposo = COM–NC cerrado = carga habilitada; para parar se energiza la bobina). J2 sigue con 3 bornes (COM, NA, NC). Falta registrarlo en `docs/DECISIONES.md` (P3).

**Estado (12 oct, noche):** el usuario aprobó los componentes y pidió reemplazar el relé Finder 34.51.7.012.5010: no está en Mouser y es caro. **K1 pasó a ser el PhotoMOS Panasonic AQY414EHAX** (NC, 400 V, 120 mA, aislamiento reforzado de 5000 Vrms, sin carga mínima; Mouser 769-AQY414EHAX, US$3,42). Desaparece D7 y J2 queda de 2 polos (ED1621 de Sigma, footprint TB001-500-02BE como J1). La decisión y los datos están en `docs/DECISIONES.md`, «Fase 6». Librería: AO3400A y KT-0805Y creados por `piezas_f6.py`, con respaldo en `docs/respaldos/`. Esquemas listos: `docs/esquemas/F6_s1_driver.svg`, `F6_s2_k1.svg` y `F6_s3_j2.svg` (`docs/tools/esquemas_f6.py`).

- [x] Comparar y elegir (12 oct): Q3 AO3400A + R39 1 kΩ + R40 10 kΩ; K1 AQY414EHAX (NC); LED6 KT-0805Y + R41 1 kΩ en serie con el LED de K1 desde `+VIN` (≈ 8,4 mA); J2 de 2 polos; sin D7.
- [x] Lista (a) SamacSys: **solo falta bajar el AQY414EHAX**. El 34.51.7.012.5010 y la TB001-500-03BE ya se bajaron, pero no se usan. Lista (b): AO3400A y KT-0805Y creados por script.
- [x] Lista de piezas para colocar y esquemas literales por bloque (`docs/esquemas/F6_*.svg`).
- [x] AQY414EHAX bajado (SamacSys lo nombra `AQY-414EHAX`; MPN corregido a AQY414EHAX) con parámetros por `piezas_f6.py`. Footprint SOP254P962X315-4N: pads en ±4,30 mm de 1,90 × 0,75 mm → **6,70 mm entre los pads del LED y los de la salida** (≥ 6,4 mm; en F8 nada de cobre debajo de K1).
- [x] Dibujar la hoja (usuario) y arreglos por `arreglos_hoja06.py`: borradas 3 piezas sueltas (relé Finder, TB001-500-03BE, un AQY de más), designadores Q3, R39–R41, LED6, K1, J2 y parámetros de K1. J2.1 = EVSE_EN_B y J2.2 = EVSE_EN_A (sin polaridad). Dibujo: puerto `RELAY_EN` → R39 → Q3 (R40 a GND) → `RELAY_DRV`; `+VIN` → R41 → LED6 → K1 pin 1; K1 pin 2 → `RELAY_DRV`; K1 pines 4 y 3 → `EVSE_EN_A` y `EVSE_EN_B` → J2.
- [x] Clase de red `EVSE_EXT`: dos Blankets (salida de K1 y J2) con Parameter Set, por script; `cobertura_blanket.py` confirma las dos redes.
- [x] `lista_redes.py -p` y `render_hoja.py`: sin pines sueltos, redes y parámetros correctos.
- [ ] Validate en Altium (0 errores; desaparece el aviso de `RELAY_EN`).
- [ ] Exportar `docs/revisiones/PROYECTO_F6.pdf` (todas las hojas) y revisarlo.
- [ ] Cerrar la fase (CLAUDE.md). Firmware: `RELAY_EN` = 1 → salida abierta → carga parada; restaurar el estado desde NVS al arrancar.
- [ ] Pendiente con el usuario: medir la tensión y la corriente de los bornes del EVSE (la salida aguanta ≤ 120 mA y lo recomendado es ≤ 320 V pico).

**Pin del ESP32-S3 ya asignado:** `RELAY_EN` = IO5 (no es de strapping). Presupuesto de `+VIN`: la IRM-20-12 da 1,8 A; la bobina de un relé de señal de 12 V consume del orden de 10–30 mA.

**Numeración de F6:** Q3, R39–R41, LED6, K1, J2 (D7 no se usa). Siguiente libre después de F6: U8, R42, C41, D7, Q4, LED7, SW4, TP7.

## Herramientas disponibles (`docs/tools/`)

- `libreria.py` (`--pieza`, `--poner`, `--copiar`), `piezas_f4.py`/`piezas_f5.py` (ejemplos de copia con pines renombrados).
- `hoja.py` + `altium_ole.py`: edición del .SchDoc registro por registro (respaldo en `docs/respaldos/`). `altium_ole.poner()` ya borra la copia `%UTF8%` de un campo al cambiarlo.
- `arreglos_hoja05.py`: ejemplo de cambio de pieza, designadores, parámetros desde la librería, cables, uniones, net labels y puertos de alimentación por script.
- `lista_redes.py -p` (ahora reconoce los No ERC), `cobertura_blanket.py`, `render_hoja.py`, `pcblib.py`, `arreglar_pdf.py`, `diagramas.py`.
- `esquemas.py`, `esquemas_f4.py` (`ic`, `conectar`, `npn`, `led_v`, `sw_v`) y `esquemas_f5.py` (`port2`, puerto bidireccional).

## Ten a mano

- **Altium cerrado al empezar.**
- **El modelo y el manual del EVSE** (o fotos de la placa de bornes), para P3.
- La cuota del día del Library Loader de SamacSys: primero el relé (o PhotoMOS), después la bornera J2.
- La página de Sigma Electrónica para stock y precios.

## Qué se hizo en la Fase 5

- Componentes (`docs/DECISIONES.md`, «Fase 5»): AHT20 (U6) con filtro RC, DS3231SN# (U7) con BAT-HLD-001 (BT1) y pull-up de `RTC_INT`, J4 bornera 3P 3,5 mm con USBLC6-2SC6 (D6), R35/R36 en el 1-Wire y R37 de 68 Ω que protege el 3V3 de la sonda. Direcciones I²C 0x38 y 0x68.
- D14: sin FRAM; el búfer sin internet va en la flash del ESP32 y la energía en NVS cada minuto. El RTC con pila se queda para fechar mediciones cuando vuelve la luz sin internet.
- Por script: DS3231SN copiado del AMC3330DWE (16 pines renombrados), resistencias nuevas, parámetros del AHT20 y la 1751251; arreglos de la hoja (47 kΩ → 4,7 kΩ, R34 que estaba en serie con VCC, net labels de U7 y designadores).
- Lecciones: copia `%UTF8%` de los campos con «±»/«Ω»; las piezas colocadas pueden traer parámetros viejos; otra vez 47 kΩ en lugar de 4,7 kΩ.

## Pendientes que no son de esta fase

- F7: comparar el footprint del Content Vault de J5 (Würth 632723300011) con el plano del datasheet.
- F7: verificar los footprints de C2 y C3 de la hoja 02 (`EEHZT1E331UP`, `EEE1AA101SP`) y el de BT1 (`BATHLD001`: pads en ±11,45 mm frente a ±10,5 mm del plano TE rev E1).
- F1B/F2B: el 01000056Z es un solo clip y puentearía el fusible; medir el BLX-A de Sigma y hacer un footprint propio (antes de F8).
- Confirmar si el tercer conductor de la instalación es neutro o tierra; el EVSE necesita tierra.
- Requisitos del profesor para el gabinete (F7); la IRM-20-12 mide 24 mm de alto.
- F7: corregir los `*` del bloque de título, copiar las librerías SamacSys a `lib/` y quitar `Job1.OutJob` del proyecto.
- F8: sin pistas ni cobre bajo U6 (AHT20) y, si cabe, ranura de 1,5 mm alrededor; C39 pegado al pin 2 de U7; D6 junto a J4.
- Firmware: SPI del ATM90E26 ≤ 160 kbps y LNSel = N; CH340C con esptool en auto-reset; AHT20 espera ≥ 5 ms tras encender; búfer sin internet en partición de datos y energía en NVS cada minuto (D14); hora del DS3231 ajustada por NTP.
- P10: dónde va la sonda DS18B20 y qué temperatura máxima acepta el EVSE.
