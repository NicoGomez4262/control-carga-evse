# Cálculos de la Fase 2 — Alimentación

Hoja `02_ALIMENTACION.SchDoc`. Los datos salen de los datasheets enlazados; lo que todavía no está elegido (IC de medición, relé, sensores) entra como reserva y se confirma en su fase.

## 1. Presupuesto de potencia

### Riel `+3V3` (salida del R-78CK3.3-0.5, 500 mA)

| Carga | Pico | Típico | Fuente |
|---|---|---|---|
| ESP32-S3-WROOM-1 | 355 mA (TX 802.11b, 1 Mbps, 20.5 dBm, 100 % de ciclo) | ≈ 120 mA (conectado, RX 95 mA + CPU) | [datasheet v1.8, tabla 6-4](https://documentation.espressif.com/esp32-s3-wroom-1_wroom-1u_datasheet_en.pdf) |
| AMC3330 (su DC/DC interno también alimenta el lado de red) | 41 mA (máx.) | 28.5 mA | [SBASA34B, IDD](https://www.ti.com/lit/ds/symlink/amc3330.pdf) |
| IC de medición (ATM90E26) | ≤ 10 mA (reserva) | ≈ 5 mA | se confirma en F3 |
| Sensores, RTC, FRAM, sonda DS18B20 | ≤ 5 mA (reserva) | ≈ 1 mA | se confirma en F5 |
| LEDs de 3.3 V (3 × 2 mA) | 6 mA | 2 mA | F4 |
| **Total** | **≈ 417 mA (1.38 W)** | **≈ 157 mA (0.52 W)** | |

- Uso del R-78CK en el pico: 417 / 500 = **83 %**. Cumple, pero con poco margen.
- Espressif pide una fuente capaz de entregar ≥ 0.5 A al módulo (`I_VDD`, mismo datasheet); el R-78CK da justo 0.5 A en total. Medidas: limitar la potencia de TX a ≤ 18 dBm en el firmware (pico ≈ 300 mA → 72 %) y dejar capacidad de reserva después del filtro LC para las ráfagas de TX.

### Riel `+VIN` (12 V del AC-DC)

| Carga | Pico | Típico | Nota |
|---|---|---|---|
| Entrada del R-78CK | 135 mA (1.38 W / 0.85) | ≈ 55 mA (0.52 W / 0.80) | eficiencia ≈ 85 % con 12 V a plena carga (curva del datasheet, D2) |
| Bobina del relé | 38 mA (reserva de 0.45 W) | 38 mA si queda energizada | se confirma en F6 |
| LED de encendido | 2 mA | 2 mA | |
| **Total** | **≈ 175 mA (2.1 W)** | **≈ 95 mA (1.1 W)** | |

Uso del módulo AC-DC en el pico:

| Módulo | Corriente nominal | Uso en el pico |
|---|---|---|
| Mean Well IRM-20-12 | 1.8 A | 10 % |
| Mean Well IRM-10-12 | 0.85 A | 21 % |
| Mean Well IRM-05-12 | 0.42 A | 42 % |
| Hi-Link HLK-PM12 | 0.25 A | 70 % |

### ¿Por qué 12 V y no 5 V?

- El R-78CK necesita ≥ 5 V en sus pines (UVLO 4.4 V). Un módulo de 5 V ±2.5 % puede dar 4.875 V, por debajo de la entrada mínima, y no admite el diodo OR de la entrada de banco.
- La bobina del relé se alimenta de `+VIN` (D2) y la entrada de banco J6 es de 12 V.
- Con 12 V el R-78CK trabaja con ≈ 85 % de eficiencia y disipa ≈ 0.24 W en el pico.

## 2. Fusibles F1 y F2 (Schurter UMT-H T1A, uno por línea)

| Dato | Valor | Fuente |
|---|---|---|
| Corriente de entrada de la IRM-20-12 a plena carga | 0.6 A a 115 VAC, 0.4 A a 230 VAC | datasheet IRM-20 |
| Corriente real con nuestra carga (2.1 W de salida, ≈ 2.8 W de entrada) | ≈ 0.03–0.06 A rms | estimación |
| Inrush en frío | 20 A a 115 VAC, 40 A a 230 VAC | datasheet IRM-20 |
| Inrush a 264 VAC (peor caso) | 40 × 264 / 230 ≈ **46 A** de pico | escalado lineal |

**I²t del inrush.** Mean Well no da la duración. Se modela como una exponencial con τ ≈ 0.5 ms (el condensador del bus se carga a través del puente y la impedancia de línea; RC ≈ 47 µF × 8 Ω ≈ 0.4 ms):

I²t ≈ I_pk² × τ / 2 = 46² × 0.5 ms / 2 ≈ **0.53 A²s**

**Margen por pulsos repetidos.** Para que el fusible soporte unos 100 000 arranques, el I²t del pulso no debe pasar del ≈ 22 % del I²t de fusión (regla usual de Littelfuse para fusibles lentos). Se necesita entonces un I²t de fusión ≥ 0.53 / 0.22 ≈ **2.4 A²s**.

| Candidato | I²t de fusión | Relación con el inrush | Ruptura | ¿Cumple? |
|---|---|---|---|---|
| Schurter UMT-H T1A (3403.0274.23) | 3.6 A²s | 6.8 × | 1500 A a 250 VAC (IEC) / 277 VAC (UL) | **sí** |
| Littelfuse 0215001 T1A (5×20) | 1.52 A²s | 2.9 × | 1500 A | no (justo) |
| Littelfuse 0215002 T2A (5×20) | 11.7 A²s | 22 × | 1500 A | sí (para el portafusible alterno) |

- Corriente continua: 0.06 A frente a 1 A nominales (6 %). El fusible no se calienta (710 mW a 1.25 In según el datasheet; aquí es despreciable).
- Fallas: un cortocircuito en la placa saca cientos de amperios y el UMT-H abre en < 10 ms (10 In: 10–100 ms de pre-arco).
- Tensión: 277 VAC ≥ 264 VAC.
- Portafusibles alternos F1B/F2B (DNP): si se usan, fusible 5×20 **lento de 2 A** (por ejemplo 0215002.MXP) o, para pruebas con transformador de aislamiento, uno de vidrio lento de 1–2 A.

## 3. Varistor RV1 (TDK CU4032K300G2)

- Tensión continua máxima: 264 VAC ≤ 300 VAC del varistor (margen del 14 %). Uno de 275 VAC dejaría solo un 4 %.
- Pico de red: 264 × √2 = 373 V, por debajo del mínimo de V₁ₘₐ (470 V − 10 % = 423 V): no conduce en operación normal.
- Surge de 2 kV con la onda combinada (2 Ω, L–N): I ≈ (2000 − 775) / 2 ≈ 610 A < 1200 A (un pulso, 8/20 µs). Recorte ≈ 775 V; la IRM-20 está probada a 2 kV.
- Va después de los fusibles: si el varistor falla en corto, abren F1/F2.
- Nota para F3: el divisor del AMC3330 debe soportar ≈ 775 V de pico durante un surge.

## 4. Filtro LC de `+3V3` y ferrita de `+3V3A`

Rizado de entrada al filtro: 50 mVpp a 800 kHz (R-78CK3.3-0.5, datasheet Rev. 1-2025, medido con 10 µF MLCC = C4).

- L2 = 2.2 µH (Bourns SRR4028-2R2Y, DCR 28 mΩ máx., 2.5 A). C5 + C6 = 2 × 22 µF 0805 X5R 25 V, ≈ 26 µF efectivos a 3.3 V. C7 = 100 µF 16 V (Panasonic EEE-FK1C101P, ESR ≈ 0.36 Ω) como amortiguador y reserva para las ráfagas de WiFi.
- Frecuencia de corte con los cerámicos: f₀ = 1 / (2π √(2.2 µH × 26 µF)) ≈ **21 kHz**. Impedancia característica Z₀ = √(L/C) ≈ 0.29 Ω.
- Amortiguamiento: la rama C7 (ESR 0.36 Ω ≈ Z₀, 100 µF ≥ 4 × 26 µF) deja Q ≈ 0.8, sin pico de resonancia apreciable.
- Atenuación a 800 kHz: X_L = 2π × 800 kHz × 2.2 µH ≈ 11 Ω frente a ≈ 0.008 Ω de los cerámicos → ≈ 60 dB ideales; con la ESL y el trazado se esperan ≥ 30 dB → < 2 mVpp en `+3V3`.
- Caída en DC: 0.42 A × 28 mΩ ≈ 12 mV.
- Ráfaga de TX de 0.3 A: hundimiento ≈ ΔI × Z₀ ≈ 85 mV, amortiguado. Peor caso apilando tolerancias típicas del R-78CK (±3 % de precisión, 3 % de regulación de carga): ≈ 3.10 − 0.012 − 0.085 ≈ 3.0 V, en el límite de la ESP32 (3.0 V). Típico: ≈ 3.2 V. En F4 se suman 22 µF + 100 nF junto al módulo, lo que reduce el hundimiento local.
- `+3V3A`: FB1 Murata BLM21PG221SN1D (220 Ω a 100 MHz, 2 A, 45 mΩ) + C8 10 µF (+ 100 nF junto al ATM90E26 en F3). Con unos mA, la caída es despreciable.

## 5. Verificación del R-78CK

| Condición | Valor | Límite | ¿Cumple? |
|---|---|---|---|
| Entrada mínima | 12 V × 0.975 − 0.35 V (SS34) − 0.06 V (L1) ≈ 11.3 V | ≥ 5 V (UVLO 4.4 V) | sí |
| Entrada máxima (transitorio) | 24.4 V (recorte del SMBJ15A) | 40 V | sí |
| Condensador electrolítico en la entrada (conexión en caliente de J6) | C1 = 100 µF 35 V | ≥ 27 µF | sí |
| Carga capacitiva en la salida | C4 10 + C5/C6 44 + C7 100 ≈ 154 µF en F2, + ≈ 60 µF de las otras hojas ≈ 214 µF | ≤ 2000 µF | sí |
| Corriente en el pico | ≈ 417 mA | 500 mA | sí (83 %) |
| Filtro EMI clase B de RECOM | L1 RLS-126 + C2 10 µF + C3 1 nF entre Vin y Vout | — | incluido |
| J6 (banco) | aceptar 9–15 V (el TVS empieza a conducir a 16.7 V) | — | se rotula «12 V» |
