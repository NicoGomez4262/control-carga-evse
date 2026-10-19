# Cálculos de la Fase 3 — Medición

Hoja `03_MEDICION.SchDoc`. Datasheets en `docs/datasheets/` (AMC3330 SBASA34B, M90E26 46002B, SJ1-351X-SMT). Designadores según la anotación del 2026-10-09 (tabla de equivalencias en `docs/DECISIONES.md`, «Fase 3»).

## 1. Límites de los chips

| Chip | Dato | Valor |
|---|---|---|
| AMC3330 | entrada lineal / recorte | ±1 V / ±1,25 V (diferencial) |
| AMC3330 | entrada máxima absoluta | HGND − 6 V a HLDO_OUT + 0,5 V (≈ 3,7 V) |
| AMC3330 | ganancia, modo común de salida | 2,0 V/V, 1,44 V |
| AMC3330 | carga en cada salida | ≥ 1 kΩ (nominal 10 kΩ), ≤ 500 pF sin resistencia en serie |
| ATM90E26 | canal V (VP–VN) | 120 µVrms – 600 mVrms, 400 kΩ por entrada, ganancia fija 1 |
| ATM90E26 | canal N (I2P–I2N) | 600 mVrms con ganancia 1 (2 y 4 posibles), 400 kΩ |
| ATM90E26 | entradas analógicas, máximo absoluto | −1 V a VDD respecto a AGND |
| ATM90E26 | SPI | hasta 160 kbps |

La salida del AMC3330 está centrada en 1,44 V y las entradas del ATM90E26 trabajan alrededor de AGND con mínimo de −1 V, por eso el acople es AC.

## 2. Divisor de tensión (R2–R5 + R6)

- R2–R5 = 4 × 1 MΩ (ERJ-P08, 1206 anti-surge, 500 V límite) y R6 = 10 kΩ 0,1 % (valores E24, pedido del usuario). Relación = 10 k / 4,01 M = **1/401**.
- 264 VAC → 0,93 Vpk (dentro del ±1 V lineal); 290 VAC → 1,02 Vpk; recorte en 354 VAC.
- Corriente: 264 V / 4,01 MΩ = 66 µA; 17 mW en total, 4,3 mW por resistencia.
- Por resistencia: 93 Vpk a 264 V; 194 Vpk con el surge de 775 V que deja el varistor (39 % de 500 V).
- Surge en INP: 775 V / 401 = 1,93 V < 3,7 V (máximo absoluto).
- Carga del AMC3330: 10 kΩ frente a 100 MΩ mínimos → 0,01 %. Corriente de polarización de 10 nA × 10 kΩ = 0,1 mV.

## 3. Acople AC y atenuación (C18/C21, R9/R12, R10/R14, C19/C22)

Cada salida: C (10 µF: C18 en P, C21 en N) → Ra (20 kΩ: R9, R12) → nodo ATM_VP/VN → Rb (13 kΩ: R10, R14) y Cf (4,7 nF: C19, C22) a GND.

- Rb efectiva = 13 k ∥ 400 k = 12,59 kΩ; k = 12,59 / 32,59 = **0,386**.
- Paso alto: 1 / (2π × 32,6 kΩ × 10 µF) = 0,49 Hz → adelanto de 0,56° a 50 Hz.
- Paso bajo: Ra ∥ Rb = 7,7 kΩ con 4,7 nF → 4,4 kHz (canal I: 1 kΩ × 33 nF → 4,8 kHz; diferencia de 0,06° a 50 Hz).

| Red | Entrada AMC3330 | Salida AMC3330 (dif.) | ATM VP–VN | % de 600 mVrms |
|---|---|---|---|---|
| 100 VAC | 0,35 Vpk | 0,50 Vrms | 0,19 Vrms | 32 % |
| 120 VAC | 0,42 Vpk | 0,60 Vrms | 0,23 Vrms | 39 % |
| 240 VAC | 0,85 Vpk | 1,20 Vrms | 0,46 Vrms | 77 % |
| 264 VAC | 0,93 Vpk | 1,32 Vrms | 0,51 Vrms | 85 % |
| 290 VAC | 1,02 Vpk | 1,45 Vrms | 0,56 Vrms | 93 % |

Frente a la primera propuesta (R6 = 9,76 kΩ, Rb = 11 kΩ), la señal en el ATM90E26 sube un 12 % (240 V: 0,41 → 0,46 Vrms), todo con valores E24.

## 4. Corriente (CT SCT-013-000V, R11/R13, R8/R15)

- CT 2000:1 → 50 A dan 25 mA. Carga R11 + R13 = 2 × 10 Ω (punto medio a GND) → **0,50 Vrms a 50 A** (83 %), recorte en 60 A.
- 6 A (mínimo de carga de un EV) → 60 mVrms; 0,5 A → 5 mVrms (el ATM90E26 resuelve desde 120 µVrms).
- Potencia en la carga: 25 mA² × 10 Ω = 6 mW por resistencia.
- Filtro: R8/R15 = 1 kΩ, C20/C23 = 33 nF C0G → 4,8 kHz. Error por la entrada de 400 kΩ: 0,25 % (se calibra).
- D4 (SMAJ5.0CA) limita ESD en el jack; a 0,7 Vpk su fuga es despreciable.
- J3: el SCT-013-000 usa solo tip (pin 2 → `CT_P`) y sleeve (pin 1 → `CT_N`); ring (3) y los contactos de conmutación (10, 11) quedan libres con *No ERC*.

## 5. ATM90E26

- MMD1 = MMD0 = 1 (modo flexible): el firmware elige la línea N (LNSel) porque el CT entra por I2. I1P/I1N, USEL y Resv_low a GND.
- Cristal de 8,192 MHz (ECS-81.92-12-30Q-EN-TR, CL = 12 pF) con 12 pF por pin (C26, C27; datasheet). Carga efectiva ≈ 9–11 pF → error ≤ 30 ppm, dentro de los ±100 ppm que exige el ATM90E26.
- Desfase total entre V e I: se calibra con el registro Nphi (y la ganancia con Ugain/IgainN).
