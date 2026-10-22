# Siguiente sesión → Fase 8: PCB, ruteo y fabricación en PCBWay

**Estado (19 oct 2026):** F7 cerrada. El esquemático está congelado (Rev 1.0): seis hojas revisadas por script, footprints verificados, librería propia en `lib/`, clases de red (`HV_AC`, `ANALOG`, `USB`, `EVSE_EXT`), Validate correcto y `docs/revisiones/PROYECTO_F7.pdf`. La BOM con la regla D16 está en `docs/BOM_F7.md` (D17): **una placa ensamblada**; PCBWay suelda todo lo que tiene en stock (US$ 60,02 en componentes, incluidos los THT); K1 va en el carrito de DigiKey del curso (US$ 3,29) y se suelda a mano junto con U1 (el R-78CK del profesor); CT, sonda y pila se compran en Sigma (50.813 COP). Detalle en `docs/DECISIONES.md`, «Fase 7».

## Prompt para iniciar

Cierra Altium antes de pegar esto en una sesión nueva de Claude abierta en la carpeta del repositorio:

```text
Seguimos con la FASE 8 del proyecto "Control de carga EVSE" (PCB, ruteo y fabricación en PCBWay). Ya cerré Altium.

Lee CLAUDE.md, NEXT_SESSION.md, docs/PLAN_FASES.md (Fase 8), docs/DECISIONES.md (D16, D17 y la sección «Fase 7») y docs/BOM_F7.md.

Sigue el ritmo de CLAUDE.md:
1. Muéstrame el diagrama «ESTÁS AQUÍ» (como gráfico) y la lista de tareas de F8.
2. Antes de ubicar nada, dame la guía de ruteo: distribución general (zona de red, barrera, SELV, antena del ESP32, conectores al borde), planos de tierra, distancias entre piezas y entre zonas, anchos de pista por corriente, mínimos y máximos de PCBWay (pista, espacio, taladro, anillo, ranuras) y las reglas de Altium que se configuran, con pasos ubicados en Altium.
3. Propón stackup (2 o 4 capas), tamaño de la placa y acabado (HASL sin plomo o ENIG) con 2–3 opciones y su precio en PCBWay; yo decido.
4. Haz por script lo que se pueda (clases, reglas, parámetros) y guíame paso a paso en lo que sea de Altium (Update PCB, ubicación, ruteo).
5. Al final: DRC sin violaciones, revisión 3D, salidas (Gerber, taladros, Pick and Place, BOM de ensamble de PCBWay) y el carrito de compras total (PCBWay + DigiKey + Sigma, en COP y USD). Si F8 no alcanza, deja el NEXT_SESSION.md para seguir y sube todo a GitHub con sincronizar_altium.py.
```

## Dónde estamos

<!--DIAG:F8-->
```text
► ESTÁS AQUÍ: FASE 8 · EVSE_Monitor.PcbDoc — ubicación, ruteo y fabricación de toda la placa ▐marcada▌

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

## Tareas de la Fase 8

**8A · Preparación**

- [ ] Guía de ruteo (pedido del usuario): distribución, planos, distancias, anchos de pista, mínimos de PCBWay y reglas de Altium, con pasos ubicados.
- [ ] Update PCB desde el esquemático (Design » Update PCB Document) y revisar que lleguen los 132 componentes con su footprint.
- [ ] Contorno libre (PCB desnuda), agujeros de montaje M3 en las esquinas, conectores J1–J8 al borde.
- [ ] Stackup: 2 capas (1,6 mm, 1 oz) o 4 capas; decidir con la cotización de PCBWay.
- [ ] Reglas: clearance `HV_AC` ↔ resto ≥ 5,5 mm; Creepage Distance ≥ 6,4 mm entre red y SELV y entre `EVSE_EXT` y SELV; L1 ↔ L2 ≥ 3,2 mm; anchos por clase; par USB de 90 Ω; mínimos de PCBWay.
- [ ] Zonas: sin cobre bajo la antena del ESP32 (todas las capas), sin cobre bajo K1 ni U2, zona de red sin planos, ranura de aislamiento si hace falta.

**8B · Ubicación**

- [ ] Zona de red en un lado con frontera recta; solo PS1, U2 y K1 cruzan la barrera.
- [ ] SMD en la cara superior; THT de PCBWay (PS1, J1, J2, J4, J6, J7, J8) con espacio para soldar; lo de mano (U1, K1) agrupado y cómodo para el cautín.
- [ ] ESP32-S3 en el borde con la antena hacia afuera; ATM90E26 y su cadena analógica lejos de PS1; Y1 pegado a U3; C39 pegado a U7; D6 junto a J4; D5 junto a J5.
- [ ] Desacoples junto a cada pin; U6 (AHT20) lejos de fuentes de calor; 3 fiduciales y marcas de pin 1.

**8C · Ruteo**

- [ ] Primero la red (≥ 1 mm, sin vías innecesarias); luego `+VIN`/`+3V3` (lazo corto del R-78CK y su filtro L1/C1/C6); analógico en pares cortos; USB 90 Ω; SPI corto.
- [ ] GND continuo con vías de costura; sin cobre bajo la antena; serigrafía con «PELIGRO 240 VAC», contorno de la zona de red, polaridades, nombre y versión.

**8D · Verificación**

- [ ] DRC sin violaciones (incluida la regla de creepage); revisión 3D (choques y acceso del cautín); revisión contra las capacidades de PCBWay.

**8E · Salidas y pedido**

- [ ] OutJob: Gerber, taladros NC, Pick and Place (mm), BOM de ensamble de PCBWay, PDF de ensamble y STEP.
- [ ] Carrito de compras total (artifact con casillas): PCBWay (PCB, ensamble y componentes), DigiKey (K1 y repuestos, ≤ US$ 50), Sigma (CT, sonda, pila); subtotales, envío, impuestos y total en COP y USD con la TRM del día.
- [ ] Pedido a PCBWay: 5 PCB, 1 ensamblada (D17); K1, U1, F1B/F2B, SW2, SW3 sin ensamblar.
- [ ] Plan de montaje y primeras pruebas: primero con la entrada de banco J6 (12 V), sin red; después con red a través de un transformador de aislamiento.

## Lo que hay que comparar en F8

- Stackup: 2 capas frente a 4 capas (precio en PCBWay, plano de GND, aislamiento).
- Acabado: HASL sin plomo frente a ENIG (J5 tiene pines finos; el SSOP-28 del ATM90E26 tiene paso de 0,65 mm).
- Tamaño de la placa (lo pone el AC-DC de 52,4 × 27,2 mm y la separación de 6,4 mm).

## Ten a mano

- Altium cerrado al empezar (que no quede `X2.EXE`).
- Cuenta de PCBWay para cotizar (PCB y ensamble) y la página de capacidades de PCBWay.
- La TRM del día para el carrito.

## Notas de F7 para el layout

- J5: agujeros de 0,4 mm con pad de 0,65 mm (anillo de 0,125 mm): confirmar con PCBWay.
- BT1: sin pasta en el contacto central.
- K1: pads a ±4,30 mm (6,70 mm entre lados); sin cobre debajo. U2: 7,50 mm entre filas de pads; sin cobre debajo.
- Sustitutos de la BOM con el mismo footprint: J1/J2 XY301V (agujero 1,30 mm para pin de 1,0 mm), RV1 Ruilon (pads iguales a CU4032), L1 Murata LQH43NH (footprint RLS126: Murata recomienda 1,5 mm entre pads y el footprint tiene 0,8 mm; suelda igual), C16/C20/C23 Murata 1206.
- Clases: `HV_AC`, `EVSE_EXT` (≥ 6,4 mm hacia SELV y hacia `HV_AC`), `ANALOG`, `USB`.
- BOM de ensamble para PCBWay: agrupar también por `Assembly` (en el CSV de F7, Altium juntó SW1 con SW2/SW3 DNP en una fila «PCBWay, DNP»).
- Después del PDF de F7 se acortaron por script los títulos de 02, 04 y 06 y se alargó la nota de la TOP (`presentacion_f7.py`): revisarlo en el PDF de F8. Quedan dos banderas «Parameter Set» encimadas en 03 (sobre el texto de la plantilla y sobre J3), solo de presentación.

## Pendientes fuera de Altium

- Firmware: SPI del ATM90E26 ≤ 160 kbps y LNSel = N; CH340C con esptool en auto-reset; AHT20 espera ≥ 5 ms; búfer sin internet y energía en NVS (D14); hora por NTP; `RELAY_EN` = 1 → carga parada y restaurar el estado desde NVS al arrancar.
- Instalación: confirmar si el tercer conductor es neutro o tierra; P10 (dónde va la sonda DS18B20); medir los bornes del EVSE antes de conectar J2 (K1 aguanta ≤ 400 Vpk y 120 mA).
