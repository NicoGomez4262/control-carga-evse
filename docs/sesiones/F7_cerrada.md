# Siguiente sesión → Fase 7 (continuación): BOM con PCBWay y DigiKey, PDF y cierre

**Cerrada el 19 oct 2026** (BOM en `docs/BOM_F7.md`, D17; PDF y BOM en `docs/revisiones/`). Estado al abrir esta sesión: F7 iba por la mitad. Ya están la revisión por script de las seis hojas, los footprints verificados, la librería propia en `lib/`, el bloque de título, las clases de red y Validate (compila; el aviso de la directiva `HV_AC` de 03 ya se corrigió). Falta la BOM con la nueva regla de compras (D16), el PDF de todo el proyecto y cerrar la fase. Detalle en `docs/DECISIONES.md`, «Fase 7».

## Prompt para iniciar

Cierra Altium antes de pegar esto en una sesión nueva de Claude abierta en la carpeta del repositorio:

```text
Seguimos con la FASE 7 del proyecto "Control de carga EVSE" (cierre del esquemático y BOM). Ya cerré Altium.

Lee CLAUDE.md, NEXT_SESSION.md, docs/PLAN_FASES.md (Fase 7 y Fase 8) y docs/DECISIONES.md (D15, D16 y la sección «Fase 7»).

Sigue el ritmo de CLAUDE.md:
1. Muéstrame el diagrama «ESTÁS AQUÍ» (como gráfico) y lo que falta de F7.
2. Arma la BOM completa con la regla de compras D16: la PCB va a PCBWay y quiero que llegue soldada con todo lo posible (turnkey); lo que PCBWay no tenga se compra en DigiKey (en un carrito que idealmente no pase de US$50, porque se suma al pedido conjunto del curso), y Sigma solo como último recurso. Mouser ya no se usa. Para cada línea: designadores, cantidad, fabricante, MPN, proveedor, número de parte del proveedor, forma de montaje (PCBWay / consignada a PCBWay / a mano) y precio. Revisa stock de verdad (PCBWay/LCSC y DigiKey), empezando por lo que hoy dice Mouser (AMC3330DWE, ESP32-S3-WROOM-1-N16R2, J5 632723300011, AQY414EHAX) y Sigma (IRM-20-12, borneras ED1621 y Phoenix, J8, BLX-A, CT SCT-013-000, jack, pila CR2032, sonda DS18B20). Si algo no está, propón equivalentes con 2–3 opciones (datasheet oficial, mismo footprint si se puede).
3. Cuando apruebe, actualiza por script Supplier, Supplier PN y Assembly en lib/SamacSys.SchLib y en las hojas (Altium cerrado, con respaldo) y dime qué cambiaste.
4. Revisión de diseño con lista: seguridad y aislamiento, potencia, arranque, ESD en conectores, puntos de prueba, valores.
5. Al final: Validate, el PDF de todo el proyecto (docs/revisiones/PROYECTO_F7.pdf) y la BOM exportada (docs/revisiones/F7_BOM.*); revísalos, cierra la fase según CLAUDE.md, deja el NEXT_SESSION.md de F8 y sube todo a GitHub con sincronizar_altium.py.
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
- [x] Informe por script de las 6 hojas y de la librería: sin pines sueltos ni redes con dos nombres; parámetros completos; rieles como puertos de alimentación.
- [x] Anotación: sin huecos, no hace falta re-anotar.
- [x] Revisión cruzada TOP ↔ hojas; nota de rieles de la TOP corregida.
- [x] Clases de red: `USB` agregada; Blankets `ANALOG` de 03 agrandadas; directiva `HV_AC` de 03 movida al borde de su Blanket (estaba flotando, 19 oct).
- [x] Footprints contra datasheet: J5 ✓, C2 ✓, C3 ✓, K1 ✓, BT1 corregido (TE rev E1), F1B/F2B → `BLX-A_5X20`.
- [x] Librería propia en `lib/` (58 piezas), rutas de modelos y `.PrjPcb` apuntando a `lib/`; sin `Job1.OutJob`; Revision 1.0.
- [x] Bloque de título: Title por hoja, sin `*`, sin logo ni texto de Altium.
- [x] Validate (19 oct): compila; único aviso (directiva flotante en 03) corregido. Repetir Validate al final.
- [x] BOM con D16 (PCBWay turnkey → DigiKey ≤ US$50 → Sigma último recurso): stock real, equivalentes para lo que falte, montaje de cada línea.
- [x] Actualizar `Supplier`, `Supplier PN` y `Assembly` en la librería y las hojas por script.
- [x] Revisión de diseño con lista: seguridad y aislamiento, potencia, arranque, ESD, puntos de prueba, valores.
- [x] Exportar `docs/revisiones/PROYECTO_F7.pdf` y la BOM (`docs/revisiones/F7_BOM.*`) y revisarlos.
- [x] Cerrar la fase (CLAUDE.md) y subir a GitHub.

**El gabinete ya no es tarea** (D16): esta versión es PCB desnuda; la caja queda para la próxima versión de la PCB.

## Herramientas (`docs/tools/`)

- `lista_redes.py -p`, `cobertura_blanket.py`, `render_hoja.py`, `pcblib.py`, `libreria.py` (`--pieza`, `--poner`, `--copiar`), `arreglar_pdf.py`, `diagramas.py`, `sincronizar_altium.py --commit`.
- Nuevas en F7: `pcblib_editar.py` (leer y armar footprints, mover pads, crear un footprint nuevo en la PcbLib), `libreria_f7.py` y `arreglos_hojas_f7.py` (ejemplos de cambios en la librería y en las seis hojas).
- La librería que se edita es `lib/SamacSys.SchLib`/`PcbLib` del proyecto, no la de `Documents/AltiumLL` (el Library Loader sigue bajando allá: si llega una pieza nueva, se copia a `lib/`).

## Ten a mano

- **Altium cerrado al empezar** (que no quede `X2.EXE`).
- Acceso a PCBWay (lista de piezas de ensamble / LCSC) y DigiKey.
- La tasa de cambio COP/USD del día.

## Pendientes para F8 (y F9 si hace falta)

- **Guía de ruteo (pedido del usuario):** Claude explica en general la distribución de componentes (zona de red, barrera, SELV, antena del ESP32, conectores al borde), planos de tierra, distancias entre piezas y entre zonas, anchos de pista por corriente, mínimos y máximos de PCBWay (pista, espacio, taladro, anillo, ranuras) y las reglas de Altium, con pasos ubicados.
- **Carrito de DigiKey** para el pedido conjunto del curso (≤ US$50) y el carrito de compras total (PCBWay + DigiKey + Sigma si hace falta).
- J5: agujeros de 0,4 mm con pad de 0,65 mm (anillo de 0,125 mm): confirmar con PCBWay. BT1 sin pasta en el contacto central. Sin cobre bajo K1 ni U6; C39 pegado a U7; D6 junto a J4; reglas de `EVSE_EXT` (≥ 6,4 mm hacia SELV y `HV_AC`).
- Firmware: SPI del ATM90E26 ≤ 160 kbps y LNSel = N; CH340C con esptool en auto-reset; AHT20 espera ≥ 5 ms; búfer sin internet y energía en NVS (D14); hora por NTP; `RELAY_EN` = 1 → carga parada y restaurar el estado desde NVS al arrancar.
- Instalación: confirmar si el tercer conductor es neutro o tierra; P10 (dónde va la sonda DS18B20).
