# Por qué la PCB quedó así — EVSE Monitor Rev 1.0

Explicación de la Fase 8 (pedida por el usuario el 20 oct, para el final de la fase): cómo se separaron las piezas, los planos de tierra, qué quedó por fuera y qué medidas se usaron y por qué. Los detalles de cada paso están en `GUIA_RUTEO_F8.md` y en `DECISIONES.md`.

## 1. La idea central: tres zonas que no se tocan

La placa mide 230–240 V de la red y, al mismo tiempo, tiene un USB que se conecta a un computador y sensores que se pueden tocar. Si una falla une la red con ese lado, la persona que toca el USB recibe la red. Por eso la placa se divide en tres zonas:

```
 ┌──────────────── 130 mm ────────────────────────────────────────────┐
 │ ISLA EVSE (J2, salida de K1)  ┃B┃  K1 (driver)  J7  J3   U4 (antena ↑) │
 │ ── hueco sin cobre ────────── ┃A┃                                     │
 │                               ┃R┃   U3 + cadena del CT   USB / CH340  │
 │ ZONA DE RED 120–240 VAC       ┃R┃   U2 (lado bajo)       sensores, RTC│
 │ J1 → fusibles → varistor      ┃E┃                                     │
 │ → divisor → U2 (lado alto)    ┃R┃   SELV: 12 V → R-78CK → 3,3 V      │
 │ → PS1 (AC-DC)                 ┃A┃   planos de GND en Top y Bottom     │
 └───────────────────────────────┸─┸─────────────────────────────────────┘
          x = 0 … 45 mm          45–51,7         51,7 … 130 mm
```

- **Zona de red (abajo a la izquierda):** todo lo que está conectado a L1/L2. J1, fusibles F1/F2 (y los portafusibles alternos F1B/F2B), varistor RV1, divisor de tensión R2–R5 y el lado de alta tensión del AMC3330 (U2).
- **Isla EVSE (arriba a la izquierda):** J2 y la salida del PhotoMOS K1. Se trata como un circuito de **potencial desconocido**: los bornes de habilitación del EVSE pueden estar a cualquier tensión respecto a la red o a tierra. Por eso va aparte de la red y aparte del SELV.
- **SELV (a la derecha):** lo de baja tensión que se puede tocar: 12 V, 3,3 V, ESP32, USB, sensores, conectores.
- **La barrera (x = 45 a 51,7 mm)** es una franja vertical **sin cobre en ninguna capa**. Solo la cruzan las tres piezas hechas para eso: **PS1** (fuente AC-DC aislada), **U2** (amplificador aislado AMC3330) y **K1** (PhotoMOS con aislamiento reforzado). La barrera mide 6,7 mm porque es la distancia entre los pads de entrada y de salida de K1, la pieza que más la limita.

**Por qué recta y vertical:** una frontera recta se verifica a simple vista y con una sola regla. Las tres piezas que cruzan quedan alineadas sobre ella, cada una con un lado en cada zona.

## 2. Las distancias de aislamiento

| Entre | Distancia | Por qué |
|---|---|---|
| Red ↔ SELV (incluido GND) | **6,4 mm** (creepage y clearance) | Aislamiento **reforzado** para 240 VAC (grado de contaminación 2). La norma pide ≥ 6,4 mm de creepage y ≥ 5,5 mm de clearance; se usó 6,4 mm para las dos, por simplicidad y margen. |
| Isla EVSE (J2) ↔ todo lo demás | **6,4 mm** | Potencial desconocido: se trata igual que la red. |
| L1 ↔ L2 | **3,2 mm** | Aislamiento funcional entre las dos fases (hasta 373 V pico en 264 VAC). Es menos que hacia el SELV porque una falla ahí la corta el fusible, no afecta a una persona. |
| Dentro de la red, entre redes distintas | 0,5 mm | Los escalones del divisor (≈ 93 V pico cada uno) y el paso de 0,65 mm de los pines de U2. |
| Salidas A y B de K1 | 1,5 mm (1,7 entre sus pads) | Hasta 400 V pico en los bornes del EVSE. |
| General (SELV) | 0,2 mm | Holgado frente al mínimo de PCBWay (0,1 mm). |
| Polígonos de GND | 0,3 mm | Para que el cobre vertido no quede pegado a pistas finas. |

En Altium cada distancia es una regla, y el DRC dio **0 violaciones eléctricas**. Los keepouts de la barrera y del hueco red–isla se excluyeron de las reglas de 6,4 mm («Not IsKeepOut»), porque no son cobre y solo servían para que nada se ruteara por ahí.

## 3. Cómo se ubicó cada bloque

La ubicación sigue el camino de la señal, para que las pistas sean cortas y no se crucen. Se pasó de 227 a 140 cruces de ratsnest antes de rutear:

- **Red:** J1 en el borde izquierdo (por ahí entra el cable). Después, en orden: fusibles, varistor, divisor y U2. PS1 en la esquina de abajo, cruzando la barrera.
- **Medición:** U3 (ATM90E26) en el centro, junto a las salidas de U2. El jack del CT (J3) arriba, en el borde, con su cadena de resistencias y filtros en línea recta hasta U3. El cristal Y1 pegado a U3.
- **MCU:** el ESP32-S3 (U4) arriba, con la **antena sobresaliendo del borde**, como recomienda Espressif: así no hay cobre debajo ni cerca de la antena. A su derecha, USB-C (J5), ESD (D5), CH340C (U5) y el auto-reset.
- **Potencia SELV:** abajo, en orden: salida de PS1 → D1 → 12 V → R-78CK (U1) → filtro LC → 3,3 V. Su lazo de corriente queda compacto y lejos de la medición.
- **Sensores, RTC y pila:** a la derecha, lejos del calor del regulador y de PS1.
- **Bordes izquierdo y derecho:** ningún SMD a menos de 5 mm, porque esos bordes los usa la banda de la máquina de PCBWay. Así no hacen falta rieles.
- **K1 con 2 mm libres alrededor:** se suelda a mano con cautín.

## 4. Planos de tierra

- **Dos planos de GND (Top y Bottom), solo en el SELV** (desde x = 52 mm hasta el borde derecho). En la zona de red, la barrera y la isla **no hay planos**: no se puede referenciar nada del SELV a la red, y un plano ahí acercaría GND a la red.
- **Una vía de GND junto a cada pad SMD de GND:** la corriente de cada condensador de desacople vuelve por el camino más corto.
- **Vías de costura cada 7,5 mm:**
  - unen los dos planos en un solo GND de baja impedancia;
  - dan un retorno corto a las señales que cambian de cara;
  - conectan las islas de cobre que las pistas dejan encerradas (sin ellas, D5 se quedó sin tierra);
  - bajan el ruido para las señales de milivoltios del medidor y para la radio.
- **Relieve de 4 rayos en los pads y conexión directa en las vías:** los pads se sueldan bien porque el plano no les roba calor, y las vías quedan bien unidas al plano.
- **Anillo de keepout alrededor de los fiduciales:** la cámara de PCBWay los ve limpios.
- **Vías tapadas con máscara:** no se ven como anillos dorados y no quedan puentes de máscara diminutos junto a los pads.

## 5. Anchos de pista y vías

Con cobre de 1 oz por fuera (IPC-2221, unos 10 °C de calentamiento): ≈ 0,3 mm aguanta 1 A, ≈ 0,8 mm 2 A y ≈ 1,3 mm 3 A.

| Redes | Ancho | Corriente / motivo |
|---|---|---|
| Red (`AC_L1`, `AC_L2`, troncos después de los fusibles) | 1,5 mm | La fuente toma unos 0,3 A, pero la pista tiene que aguantar la falla hasta que el fusible de 1 A abra. |
| Ramales de red al divisor y a U2 | 0,5 mm | Microamperios. |
| 12 V (`+VIN`, `VIN_ACDC`, `VIN_BANCO`) | 1,0 mm | IRM-20-12: hasta 1,67 A. |
| Lazo del R-78CK | 0,6–1,0 mm | Corriente conmutada: corto y ancho. |
| `+3V3` | 0,6 mm el tronco, 0,4 mm los ramales | ≤ 0,5 A. |
| EVSE (J2–K1) | 0,8 mm | ≤ 120 mA; robustez. |
| Señales | 0,25–0,4 mm | mA. |
| USB D+/D− | 0,25–0,3 mm, en par | Full Speed (12 Mb/s): la impedancia no es crítica; el par puede ir separado hasta 30 mm. |

**Vías:** 0,3/0,6 mm en señales (anillo de 0,15 mm, el mínimo de PCBWay sin costo extra) y 0,4/0,8 mm en potencia y GND.

**El cruce de L2 por debajo de L1:** para llegar al lado de red de U2, `AC_L2_F` tenía que cruzar el lado L1. Por Top no se puede, por la regla de 3,2 mm, así que cruza por Bottom, debajo de F1 y lejos de sus pads. Entre las dos caras hay 1,6 mm de FR-4, que aíslan cientos de veces más que lo necesario.

## 6. Lo que no ensambla PCBWay y lo que va fuera de la placa

| Pieza | Qué pasa | Por qué |
|---|---|---|
| K1 (AQY414EHAX) | Se compra en DigiKey y se suelda a mano | Ni LCSC ni PCBWay tienen un PhotoMOS normalmente cerrado con aislamiento reforzado. |
| U1 (R-78CK3.3-0.5) | Se suelda a mano | Ya está disponible (lo dio el profesor). Es THT. |
| F1B, F2B | No se montan (DNP) | Portafusibles 5×20 de repuesto: si un fusible SMD se quema en las pruebas, se suelda el portafusible sin desoldar nada. |
| SW2, SW3 | No se montan (DNP) | RESET y BOOT a mano. No hacen falta porque el CH340C hace el auto-reset por USB. |
| CT, sonda DS18B20, pila CR2032 | Sigma | Van fuera de la placa. DigiKey no los tiene o no los envía (la pila de litio solo viaja por tierra). |

## 7. Las demás medidas

- **130 × 100 mm:** los courtyards de las 132 piezas suman 66 cm². En 100 × 100 mm la placa quedaba al 78 % y J1 con el portafusible BLX-A no cabía en la zona de red. 130 × 100 mm cuesta casi lo mismo (US$ 36,87 las 5 placas).
- **2 capas, 1,6 mm, 1 oz, HASL sin plomo:** lo estándar y más barato de PCBWay. El ruteo cupo en dos capas, así que cuatro capas no aportaban nada.
- **Agujeros M3 en las esquinas, sin metalizar:** el cobre de la red queda a más de 6,4 mm (el arco de `AC_L2_F` alrededor de M1 está a 6,40 mm justos). Así un tornillo, que se puede tocar, nunca queda cerca de la red.
- **3 fiduciales y serigrafía de seguridad:** «PELIGRO 240 VAC», las líneas de la barrera y «HABILITACION EVSE (J2)».
- **BT1 sin pasta en el contacto:** la pila toca el pad directamente; con pasta quedaría un bulto de soldadura debajo.
