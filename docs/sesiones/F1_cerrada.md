# Siguiente sesión → Fase 1: proyecto Altium y hoja TOP

**Estado del proyecto (6 oct 2026):** arquitectura en revisión B, R-78CK3.3-0.5 verificado y plan de 8 fases listo. Todavía no hay nada creado en Altium.
**Esta sesión cubre:** la creación de `altium/EVSE_Monitor.PrjPcb` y la hoja `01_TOP.SchDoc`, y las respuestas a P1–P7.

## Prompt para iniciar

Copia y pega esto en una sesión nueva de Claude abierta en la carpeta del proyecto:

```text
Iniciamos la FASE 1 del proyecto "Control de carga EVSE" en Altium: crear el proyecto y la hoja TOP jerárquica.

Antes de empezar, lee CLAUDE.md, NEXT_SESSION.md, docs/PLAN_FASES.md (sección Fase 1) y docs/DECISIONES.md.

En esta sesión:
1. Muéstrame el diagrama de bloques con la ubicación de la Fase 1 y la lista de tareas.
2. Hazme las preguntas P1 a P7 una por una, cada una con tu recomendación, y registra mis respuestas en docs/DECISIONES.md.
3. Guíame paso a paso en Altium para crear altium/EVSE_Monitor.PrjPcb, la plantilla de hoja, las hojas 01 a 06 y los símbolos de hoja con sus entradas en 01_TOP.SchDoc, según la tabla de interfaces del plan.
4. Cuando exporte el PDF de la TOP a docs/revisiones/, revísalo y dime qué corregir.
5. Al completar la lista, cierra la fase como indica CLAUDE.md y deja listo el NEXT_SESSION.md de la Fase 2.
```

## Dónde estamos

<!--DIAG:F1-->
```text
► ESTÁS AQUÍ: FASE 1 · 01_TOP.SchDoc — este diagrama completo ES la hoja TOP (un símbolo de hoja por cada F#)

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
 INTERFAZ                                             ┃          ┃ J5 ─► [F4 USB-C · botones · LEDs] ─► ESP32-S3
 SENSORES                                             ┃          ┃ J4 ─► [F5 Sensores · RTC · FRAM] ─► ESP32-S3
 BANCO                                                ┃          ┃ J6 ─► [F2 Jack 12 V banco] ─► riel (propuesta)
════════════════════════════════════════════════════════════════════════════════════════════════════════════════
[F# bloque] fase en que se diseña · ▐bloque▌ se diseña en ESTA fase · ► carril con trabajo en esta fase
┃ ┃ barrera de aislamiento · ┨ ┠ componente que cruza la barrera (AC-DC, AMC3330, relé)
│ L1/L2 (L/N en 120 V) con fusibles · J1–J6 conectores · J1 con cable largo a la línea · J2 contacto seco aislado
```
<!--/DIAG-->

## Tareas de la Fase 1

- [ ] Responder P1–P7 y registrarlas en `docs/DECISIONES.md`.
- [ ] Preferencia de riel de entrada: 12 V (recomendado) o 5 V.
- [ ] Crear carpetas `altium/`, `docs/revisiones/`, `docs/sesiones/`, `docs/datasheets/`.
- [ ] Crear `altium/EVSE_Monitor.PrjPcb` con `01_TOP` a `06_ACTUACION` y un `EVSE_Monitor.PcbDoc` vacío.
- [ ] Plantilla de hoja con bloque de título y parámetros del proyecto.
- [ ] Estrategia de librerías y lista de piezas que necesitan símbolo o footprint propio.
- [ ] Parámetros obligatorios de componente en la plantilla o la librería.
- [ ] Hoja TOP con un símbolo de hoja por bloque, entradas de hoja y conexiones de la tabla de interfaces.
- [ ] Opciones del proyecto (alcance jerárquico de redes, matriz ERC).
- [ ] Compilar sin errores.
- [ ] Exportar `docs/revisiones/F1_TOP.pdf` y revisarlo.
- [ ] Cerrar la fase.

El detalle de cada tarea y la tabla de interfaces están en `docs/PLAN_FASES.md`, sección Fase 1.

## Ten a mano

- Altium Designer abierto y, si lo usas, tu cuenta de Altium 365 para las librerías.
- Datos del EVSE para P2: marca, modelo, manual o fotos de la placa de datos y de los bornes.
- El tipo de servicio eléctrico donde va el cargador (P1): se ve en el medidor o en el tablero.
- Dónde vas a instalar el dispositivo (P4).

## Ya decidido

- Regulador de 3.3 V: RECOM R-78CK3.3-0.5 (D2), con filtro LC a la salida.
- Fuente AC-DC: módulo Mean Well de la serie IRM, preferiblemente de 12 V; se elige en F2 (D3).
- Medición aislada: ningún componente del lado SELV toca la red.
- Ensamble SMD en PCBWay; módulos y THT de Sigma soldados a mano (D5).
- Mouser solo como última opción, para lo que no esté en Sigma ni en PCBWay (D6).

## Al cerrar la Fase 1

1. Marcar la Fase 1 como cerrada en `docs/PLAN_FASES.md`.
2. Pasar las respuestas y decisiones a `docs/DECISIONES.md`.
3. Mover este archivo a `docs/sesiones/F1_cerrada.md`.
4. Escribir el nuevo `NEXT_SESSION.md` para la Fase 2 (alimentación), con su diagrama «ESTÁS AQUÍ» (marcador DIAG de F2 y `docs/tools/diagramas.py`), lista de tareas, componentes a comparar y prompt de inicio.
