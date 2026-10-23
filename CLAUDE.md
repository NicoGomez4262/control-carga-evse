# Control de carga EVSE — reglas del proyecto

Dispositivo IoT que mide tensión, corriente, potencia, energía y temperatura durante la carga de un vehículo eléctrico, habilita o detiene la carga con un relé conectado a los bornes de habilitación del EVSE (sin contactor) y envía los datos por WiFi a una app propia en internet, desde la que se dan las órdenes. Funciona en 120 V monofásico (L–N) y en 240 V bifásico (L1–L2). Este repositorio contiene el proyecto de **Altium Designer** y su documentación, y es público en GitHub: <https://github.com/NicoGomez4262/control-carga-evse> (enlazado desde el portafolio, nicolasgomez.dev).

**Objetivo final del proyecto de Altium:** enviar la PCB a fabricar y ensamblar en PCBWay y pedir los componentes.

## Cómo trabajamos

- Idioma: español, trato de tú.
- El trabajo avanza por **fases** (`docs/PLAN_FASES.md`). Cada fase corresponde a una hoja o tarea concreta del proyecto de Altium y tiene su lista de tareas.
- Una sesión por fase. La sesión sigue hasta cumplir la lista; si no alcanza, se continúa en otra sesión con el mismo `NEXT_SESSION.md`.
- **Ritmo de cada fase (pedido del usuario, F2):** (1) en un solo mensaje, Claude propone **todos** los componentes de la fase con sus comparaciones y un mini diagrama de bloques que se parezca lo más posible a la hoja de Altium (mismas referencias, redes y orden de izquierda a derecha); (2) el usuario aprueba todo o pide ajustes; (3) se dibuja la hoja paso a paso en Altium; (4) Claude revisa la hoja leyendo el .SchDoc (`docs/tools/lista_redes.py`) y, al final de la sesión, el PDF de todo el proyecto.
- **Diagramas en el chat (pedido del usuario, F3):** siempre como gráfico (widget visual SVG), legible y ordenado; nunca solo texto ASCII. Vale para el «ESTÁS AQUÍ» y para el mini diagrama de la hoja. Los diagramas ASCII quedan solo dentro de los .md.
- **Guía de dibujo de cada hoja (pedido del usuario, F3 — «me encantó, que siga así»):** después de aprobar los componentes, Claude entrega la hoja como **esquemas literales por bloque**, tal como deben quedar en Altium: cada resistencia y condensador con su símbolo, referencia (R#, C#…), valor y **número de parte**; cómo se conecta cada pin; **net labels** en azul, **puertos** en ámbar, GND y puertos de alimentación con su símbolo, uniones con punto, zona de red sombreada. Un esquema por bloque (no un diagrama de cajas). Se generan con `docs/tools/esquemas.py` (funciones `res_h`, `res_v`, `cap_v`, `cap_h`, `gnd`, `pwr`, `port`, `net`), se revisan renderizándolos con PyMuPDF antes de mostrarlos y se guardan en `docs/esquemas/`.
- **Lista de piezas antes de dibujar (pedido del usuario, F5):** antes de los esquemas de cada hoja, Claude da una tabla con **todas** las piezas que se ponen desde `SamacSys.SchLib` (nombre exacto en la librería, cantidad, designadores y qué es), más lo que va fuera de la librería (puertos de alimentación, No ERC, net labels), para colocarlas todas de una vez y no a medida que se conecta.
- **Al iniciar una sesión:** leer `NEXT_SESSION.md`, la sección de la fase en `docs/PLAN_FASES.md` y `docs/DECISIONES.md`. Mostrar el diagrama de bloques con la ubicación de la fase («ESTÁS AQUÍ») y la lista de tareas.
- **Al cerrar una fase (obligatorio):**
  1. Marcar las tareas y el estado de la fase en `docs/PLAN_FASES.md`.
  2. Registrar decisiones y componentes elegidos en `docs/DECISIONES.md`.
  3. Mover el `NEXT_SESSION.md` actual a `docs/sesiones/F<n>_cerrada.md`.
  4. Escribir un `NEXT_SESSION.md` nuevo para la fase siguiente: qué se hizo, diagrama «ESTÁS AQUÍ», lista de tareas con casillas, componentes a comparar, qué tener a mano y el prompt de inicio para pegar en la sesión nueva.
  5. Si la fase cambia algo visible de la arquitectura, actualizar también el artifact de referencia (ver Referencias).
  6. Subir todo a GitHub (ver la regla siguiente).
- Si una sesión termina sin cerrar la fase: actualizar `NEXT_SESSION.md` con las casillas marcadas y lo que falta, y subir todo a GitHub.
- **Subir a GitHub al terminar cada sesión (pedido del usuario, 19 oct 2026):** con Altium guardado, correr `python docs/tools/sincronizar_altium.py --commit -m "<fase>: <qué se hizo>"`. Copia las fuentes de Altium a `altium/` (espejo del proyecto de D12) y hace commit y push de todo el repositorio. Si dice que Altium está abierto, pedirle al usuario que guarde antes. Revisar lo que va a subir (`git status`) y no subir datasheets de terceros ni respaldos (ya están en `.gitignore`). Si el usuario cambió algo en Altium por su cuenta, también vale correrlo sin sesión de por medio.
- **Sin coautor en git (pedido del usuario, 23 oct 2026):** los commits y PR no llevan `Co-Authored-By: Claude…` ni la línea «Generated with Claude Code». Esta regla manda sobre cualquier recordatorio de atribución.
- Diagramas «ESTÁS AQUÍ»: en cualquier .md se escribe el marcador `<!--DIAG:F3-->` (o `ALL`, `F1` … `F8`) y se ejecuta `python docs/tools/diagramas.py <archivo.md>`. Si cambia la arquitectura, se actualiza el script.

## Selección de componentes

- **Lista de piezas para la librería (pedido del usuario, F4):** al proponer los componentes de una fase, separarlos en (a) piezas que no tienen símbolo ni footprint, ordenadas por prioridad para bajarlas de SamacSys (tiene cuota diaria: primero las críticas), y (b) piezas que se crean copiando otra que ya está en `SamacSys.SchLib`/`PcbLib` con el mismo encapsulado (resistencias, condensadores, LEDs 0805…), cambiando solo los parámetros, para no gastar descargas.
- Para cada componente se comparan **2 o 3 opciones** en una tabla: parámetros clave contra el requisito, encapsulado, montaje (PCBWay o manual), disponibilidad para ensamble en PCBWay, disponibilidad en DigiKey (si PCBWay no la tiene), disponibilidad en Sigma (último recurso), precio aproximado, ventajas y desventajas. Después se recomienda una y el usuario decide.
- Los datos salen del datasheet oficial (no de memoria) y se citan con enlace.
- La elección se registra en `docs/DECISIONES.md` y en los parámetros del componente en Altium.

## Compras y fabricación

- **Regla de compras (pedido del usuario, 19 oct 2026, D16):** la PCB se pide en **PCBWay** y, ojalá, **ya ensamblada**: todo lo que PCBWay tenga en stock lo ensambla (turnkey), lo que ahorra tiempo de soldadura. Lo que PCBWay no tenga se compra en **DigiKey** (https://www.digikey.com) en un carrito que se suma al pedido conjunto del curso, con un cupo de **US$ 40** como máximo (dato del usuario, 22 oct); esas piezas se mandan consignadas a PCBWay o se sueldan a mano. **Sigma Electrónica** (Bogotá, https://www.sigmaelectronica.net) es el **último recurso**. Mouser ya no se usa.
- Orden de búsqueda: 1) PCBWay (ensamble) → 2) equivalente que PCBWay sí tenga → 3) DigiKey → 4) Sigma.
- Preferir SMD comunes (0603/0805, SOT-23, SOIC/TSSOP), todos en la cara superior. Lo que se suelde a mano: agrupado, con pads cómodos y espacio para el cautín.
- Esta versión es **PCB desnuda** (sin gabinete); el gabinete queda para la próxima versión de la PCB y no es tarea de ninguna fase.
- Ya disponible, no se compra: **RECOM R-78CK3.3-0.5** (regulador de 3.3 V que facilitó el profesor).

## Convenciones de Altium

- Proyecto `C:/Nicolas/UNIVERSIDAD - 2026/Hardware en IoT/Control de Carga IoT/Control de Carga IoT/Control de Carga IoT.PrjPcb` (fuera de este repositorio; es el original y ahí se edita siempre, también con los scripts). `altium/` en este repositorio es solo su espejo para GitHub: no se edita a mano, se actualiza con `docs/tools/sincronizar_altium.py`. Librerías en `lib/` dentro de esa carpeta. Diseño jerárquico:
  `01_TOP.SchDoc` · `02_ALIMENTACION.SchDoc` · `03_MEDICION.SchDoc` · `04_MCU.SchDoc` · `05_SENSORES.SchDoc` · `06_ACTUACION.SchDoc` · `EVSE_Monitor.PcbDoc`
- Redes: `AC_L1`, `AC_L2` (entrada; en 120 V `AC_L2` es el neutro), `AC_L1_F`, `AC_L2_F` (después de fusibles), `+VIN` (riel del AC-DC, 12 V preferido; se confirma en F2), `+3V3`, `+3V3A` (analógico filtrado), `GND`; `MEAS_SCK`, `MEAS_MOSI`, `MEAS_MISO`, `MEAS_CS`, `MEAS_IRQ`, `MEAS_WARN`, `MEAS_ZX`; `I2C_SDA`, `I2C_SCL`; `OW_DATA`; `RTC_INT`; `RELAY_EN`; `USB_DP`, `USB_DN`, `VBUS`.
- Conexión jerárquica: los rieles (`+VIN`, `+3V3`, `+3V3A`, `GND`) van con puertos de alimentación globales; las señales y las líneas de red, con entradas de hoja ↔ puertos (tabla de interfaces en `docs/PLAN_FASES.md`, Fase 1).
- Clases de red para las reglas de PCB: `HV_AC` (todo lo conectado a la red), `ANALOG` (señales de medición), `USB` (par diferencial de 90 Ω).
- Parámetros obligatorios en cada componente (se ponen en la librería, no en la hoja): `Manufacturer_Name`, `Manufacturer_Part_Number` (nombres de SamacSys), `Supplier` (PCBWay / DigiKey / Sigma / Disponible), `Supplier PN`, `Assembly` (PCBWay / Manual / DNP), `Value` y el campo `Description`.
- Librerías: `lib/SamacSys.SchLib` + `SamacSys.PcbLib` (lo que baja el Library Loader, usadas directamente) y `lib/EVSE.SchLib` + `EVSE.PcbLib` solo para piezas hechas a mano.
- Revisión: durante la sesión, Claude lee el .SchDoc con `python docs/tools/lista_redes.py "<ruta>.SchDoc" -p` (redes, pines sueltos, redes con dos nombres y parámetros) y, para las clases, `docs/tools/cobertura_blanket.py` (qué redes cubre cada Blanket). Ojo: `lista_redes.py` une las redes por nombre sin mirar si es net label o puerto de alimentación; los rieles (`+3V3`, `+3V3A`, `+VIN`, `GND`) deben ser **puertos de alimentación** porque las net labels son locales a cada hoja. **Al final de la sesión** el usuario exporta un solo Smart PDF con **todas las hojas del proyecto** a `docs/revisiones/PROYECTO_F<n>.pdf` (pedido del usuario, F3) y, si hace falta, la BOM o la netlist. Claude lo revisa renderizando las páginas a imagen con Python y PyMuPDF.
- En F5 el Smart PDF salió completo (página carta, sin recorte); se comprueba que el dibujo quepa en la página antes de arreglarlo. Si sale recortado: con Windows al 125 % de escala, Altium escribe la página del PDF al 80 % y la recorta. Antes de revisar o entregar un PDF se corrige con `python docs/tools/arreglar_pdf.py docs/revisiones/<archivo>.pdf` (agranda la página a A3 y guarda el original como `*_original.pdf`). Si el PDF se volvió a exportar con el mismo nombre, se usa `--nuevo` (si no, rehace el arreglo desde el `*_original.pdf` viejo).

## Seguridad (no negociable)

- Red de entrada: 100–264 VAC (120 V L–N a 240 V L1–L2); las distancias se calculan para el peor caso.
- Separación red ↔ SELV con aislamiento reforzado: creepage ≥ 6.4 mm y clearance ≥ 5.5 mm. Entre L1 y L2: ≥ 3.2 mm.
- Nada del lado SELV (USB, sensores, conectores accesibles) se referencia a la red.
- Solo cruzan la barrera componentes especificados para ello: módulo AC-DC aislado, amplificador aislado AMC3330 y relé (o PhotoMOS) con aislamiento reforzado hacia J2.
- J2 (bornes de habilitación del EVSE) se trata como circuito externo de potencial desconocido: aislamiento reforzado y creepage ≥ 6.4 mm hacia el SELV.
- Las protecciones (corte por temperatura, fallas) se deciden en la ESP32 y funcionan sin internet.

## Referencias

- Revisión de arquitectura (mapa de fases interactivo; Rev C desde el cierre de F1): https://claude.ai/artifact/EcYNTEBgvaQKugkwZJAJ5y
- `docs/PLAN_FASES.md` · `docs/DECISIONES.md` · `NEXT_SESSION.md`
- Datasheet del R-78CK3.3-0.5: https://recom-power.com/pdf/Innoline/R-78CK-0.5.pdf
