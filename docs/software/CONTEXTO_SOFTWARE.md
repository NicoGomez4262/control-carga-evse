# Contexto para el software — EVSE Monitor Rev 1.0

> **Documento de entrada de la Fase 10 (20 nov 2026).** El estado de la sección 1 es el de ese día: U1 ya está soldado desde el 24 nov y la placa funciona con el firmware final (ver `README.md` y `docs/pruebas/PROTOCOLO_PRUEBAS.md`). Lo demás (pines, polaridades y requisitos) sigue vigente.

Lo que el firmware y la app necesitan saber de la placa, sacado del esquemático (hojas 02–06), de `docs/DECISIONES.md`, de `docs/calculos/` y de los datasheets. Es la entrada de la Fase 10. Las decisiones de software se registran desde D21 en `docs/DECISIONES.md`.

## 1. Estado del hardware (20 nov 2026)

- Placa 1 de JLCPCB, ensamblada. Pasó H1 (sin energía), H2 (12 V sin U1) y H3 (3,3 V en TP3, incluido el lado de red del AMC3330). Detalle en `docs/pruebas/PROTOCOLO_PRUEBAS.md`.
- **U1 (R-78CK3.3-0.5) todavía no está soldado.** Mientras tanto:
  - se alimenta con **3,30 V en TP3 (+) y TP1 (−)**, con un límite de 0,25 A. Eso alimenta el CH340C, el ESP32, el ATM90E26, el AMC3330 y los sensores;
  - K1 necesita además **12 V en J6** (segundo canal de la fuente, límite de 0,05 A), porque su LED se alimenta de +VIN;
  - el WiFi no se prueba a plena potencia (picos de 350 mA).
- **Con U1 soldado, nunca más 3,3 V en TP3** (se alimentaría el regulador por su salida). Todo va por J6 (12 V de banco) o por la red.
- La red solo se conecta con transformador de aislamiento (S7). Con la placa energizada no se toca nada.
- SW2 (RESET) y SW3 (BOOT) no están montados: el CH340C hace el auto-reset. J8 tiene EN e IO0 para hacerlo a mano.

## 2. ESP32-S3

| Dato | Valor |
|---|---|
| Módulo | ESP32-S3-WROOM-1-N16R2: flash de 16 MB (QIO), PSRAM de 2 MB quad (QSPI), −40 a 85 °C, antena del módulo sobresaliendo del borde |
| Programación y consola | UART0 (TX IO43, RX IO44) por el CH340C (U5) en J5 (USB-C), con R25/R26 de 1 kΩ en serie. Auto-reset con DTR/RTS (Q1, Q2) hacia EN e IO0. El USB nativo (IO19/IO20) no está conectado |
| La placa no se alimenta por USB | VBUS solo llega a D5 (ESD). Para programar tiene que estar alimentada |
| Arduino IDE | «ESP32S3 Dev Module», Flash Size 16 MB, PSRAM «QSPI PSRAM», USB CDC On Boot «Disabled», Upload por UART |
| J8 (1 × 6, 2,54 mm) | 1 3V3 · 2 TX0 · 3 RX0 · 4 EN · 5 IO0 · 6 GND |

## 3. Mapa de pines (definitivo desde F4)

| GPIO | Red | Función | Nota |
|---|---|---|---|
| IO10 | MEAS_CS | CS del ATM90E26 | pull-up R18 de 10 kΩ |
| IO11 | MEAS_MOSI | SDI del ATM90E26 | |
| IO12 | MEAS_SCK | SCLK del ATM90E26 | |
| IO13 | MEAS_MISO | SDO del ATM90E26 | |
| IO14 | MEAS_IRQ | IRQ del ATM90E26 | |
| IO21 | MEAS_WARN | WarnOut del ATM90E26 | |
| IO17 | MEAS_ZX | cruce por cero del ATM90E26 | |
| IO8 | I2C_SDA | AHT20 y DS3231 | pull-up R32 de 4,7 kΩ; hasta 400 kHz |
| IO9 | I2C_SCL | | pull-up R33 de 4,7 kΩ |
| IO4 | OW_DATA | DS18B20 en J4 | pull-up R35 de 4,7 kΩ y R36 de 100 Ω en serie |
| IO18 | RTC_INT | INT/SQW del DS3231 | drenador abierto, pull-up R34 de 10 kΩ |
| IO5 | RELAY_EN | mando de K1 | R40 de 10 kΩ a GND: K1 abierto durante el arranque |
| IO6 | LED_WIFI | LED3 verde | activo en alto, 1 kΩ |
| IO7 | LED_CARGA | LED4 verde | activo en alto, 1 kΩ |
| IO15 | LED_FALLA | LED5 rojo | activo en alto, 1 kΩ |
| IO16 | BTN_PARAR | SW1 en la placa y botón de panel en J7 | activo en bajo; R27 de 10 kΩ a 3,3 V, R31 de 1 kΩ y C36 de 100 nF (falta antirrebote por software) |
| IO43 / IO44 | TXD0 / RXD0 | consola y programación | por el CH340C |
| IO0 / EN | ESP_IO0 / ESP_EN | auto-reset | |
| libres | IO1, IO2, IO3, IO19, IO20, IO35–IO42, IO45–IO48 | sin conectar | IO38 se reservó para un zumbador; IO3, IO45 e IO46 son de arranque |

Otros: LED1 (encendido) va fijo en +3V3. LED2 es el pulso de energía de CF1 del ATM90E26. CF2 va a TP6. `AMC_DIAG` **no** llega a ningún GPIO (solo a TP5): la pérdida de red se detecta con Urms y el sag del ATM90E26.

## 4. Periféricos

### ATM90E26 (U3), medidor de energía

- **SPI de 4 hilos, modo 3** (SCLK en reposo alto; el dato entra en flanco de subida y sale en flanco de bajada). Entre 200 bps y **160 kbps**: usar 100 kHz. Trama de 24 ciclos con CS en bajo:
  - bit 23: lectura (1) o escritura (0);
  - bits 22–16: dirección;
  - bits 15–0: dato.
  Si SCLK no cambia en 6 ms, la operación se descarta.
- **Modo:** MMD1 = MMD0 = 1 (modo flexible). **El CT entra por I2 (línea N)**, así que hay que poner **LNSel = 0 en MMode** (por defecto 9422H → 9022H) y usar los registros «2».
- **Registros** (datasheet Atmel-46002B):

| Dir. | Registro | Uso |
|---|---|---|
| 00H | SoftReset | escribir 789AH |
| 01H | SysStatus | CalErr, AdjErr, SagWarn… |
| 02H / 03H | FuncEn / SagTh | habilitar el aviso de sag y su umbral |
| 06H | LastData | último dato leído o escrito (verificación del SPI) |
| 20H | CalStart | 6886H al encender; 5678H = calibrar; 8765H = revisar CS1 y medir |
| 21H–2AH | PLconstH/L, Lgain, Lphi, Ngain, Nphi, umbrales de arranque | calibración de energía |
| 2BH | MMode | 9422H por defecto; LNSel en el bit 10 |
| 2CH | CS1 | suma de verificación de 21H–2BH |
| 30H | AdjStart | 6886H al encender; igual que CalStart para la medición |
| 31H / 33H | Ugain / IgainN | ganancia de tensión y de corriente N |
| 34H–3AH | offsets | |
| 3BH | CS2 | suma de verificación de 31H–3AH |
| 40H–45H | APenergy, ANenergy, ATenergy, RPenergy, RNenergy, RTenergy | energía (se borran al leer) |
| 46H | EnStatus | |
| 49H | Urms | tensión eficaz |
| 4CH | Freq | frecuencia |
| 68H | Irms2 | corriente eficaz de la línea N (el CT) |
| 6AH / 6BH | Pmean2 / Qmean2 | potencia activa y reactiva N |
| 6DH / 6EH / 6FH | PowerF2 / Pangle2 / Smean2 | factor de potencia, ángulo, potencia aparente N |

- **Salidas:** WarnOut se activa con CalErr (suma de verificación mala) y con sag si FuncEn lo habilita. IRQ se activa con los eventos de SysStatus. ZX se configura con ZXCon en MMode. CF1 pulsa LED2.
- **Escalas analógicas** (`docs/calculos/F3_MEDICION.md`):
  - Tensión: divisor de 1/401 → AMC3330 (ganancia 2) → acople AC (k = 0,386) → VP–VN = V_red × 1,925 × 10⁻³. Da 0,231 Vrms a 120 V y 0,462 Vrms a 240 V; recorta en 354 VAC.
  - Corriente: CT SCT-013-000V de 2000:1 con carga de 2 × 10 Ω → 0,01 V por amperio. Da 0,50 Vrms a 50 A y recorta en 60 A. Un EV toma como mínimo unos 6 A (60 mVrms).
- **Calibración** (S7, con transformador de aislamiento, carga resistiva y pinza de referencia): Ugain, IgainN, Ngain, Nphi, PLconst; después CS1/CS2 y 8765H en CalStart y AdjStart. Las constantes se guardan en NVS y se pueden ver desde la app.

### AHT20 (U6), ambiente

I²C 0x38. Se alimenta por un filtro RC que pide el fabricante (R38 de 330 Ω y C37 de 10 µF, τ = 3,3 ms), así que su VDD tarda unos 15 ms en subir. El datasheet de `docs/datasheets/` pide 5 ms después de VDD antes de hablarle: esperar ≥ 25 ms después del arranque. Cada medición (0xAC 0x33 0x00) tarda 80 ms. Precisión de ±0,3 °C y ±2 %HR. La placa calienta un poco el sensor.

### DS3231 (U7), reloj con pila

I²C 0x68. INT/SQW va a IO18. Pila CR2032 en BT1. Al poner la hora se borra OSF. Sirve para fechar mediciones cuando vuelve la luz sin internet (P5, D14).

### DS18B20, sonda externa en J4

1-Wire en IO4. J4: 1 = 3,3 V (por R37 de 68 Ω), 2 = datos, 3 = GND. Si la sonda hace corto, R37 lo limita a 49 mA y la placa sigue funcionando. Código de familia 0x28. Va en el conector o el cable del EVSE para la protección por temperatura.

### K1 y J2, habilitación del EVSE

- K1 es un PhotoMOS **AQY214EHAX, normalmente abierto** (D20): **RELAY_EN = 1 → J2 cerrado → carga permitida**. LED6 encendido = carga permitida.
- Sin energía, en un reset o durante el arranque (por R40), J2 queda abierto: **el EVSE no carga**.
- El LED de K1 va en serie con LED6 desde +VIN (12 V) por R41 de 1 kΩ, a unos 8,4 mA. Sin 12 V, K1 no cierra.
- J2 se trata como circuito externo de potencial desconocido (aislamiento reforzado). K1 aguanta 400 V pico y 120 mA.

## 5. Restricciones de diseño

- **Energía:** el R-78CK da 0,5 A en total. El pico estimado es de unos 429 mA con el WiFi transmitiendo, así que la potencia de TX se limita a ≤ 17 dBm. Hay que dejar el detector de brownout activo y registrar el motivo del reset.
- **Protecciones locales (regla del proyecto):** el corte por temperatura, PARAR y las fallas se deciden en la ESP32 y funcionan sin internet. La app solo ordena y muestra.
- **Arranque:** hay que restaurar el estado de `RELAY_EN` desde NVS (P3). Con el AQY214EHAX, si se va la luz el EVSE deja de cargar. Falta decidir si al volver la energía se restaura «permitido» solo o si se espera una confirmación.
- **D8:** el ESP32 abre una conexión saliente cifrada (TLS) hacia el servidor, sube los datos y recibe las órdenes por la misma conexión. Sin VPN y sin puertos abiertos.
- **D14:** sin FRAM. El búfer sin internet va en una partición de datos de la flash de 16 MB. La energía de la sesión se guarda en NVS cada minuto y al empezar o terminar la sesión.
- **Instalación:** 120 V L–N o 240 V L1–L2 (configurable), 60 Hz (Colombia), CT en L1, EVSE genérico de 0–50 A.
- **Repo público:** nada de contraseñas del WiFi, credenciales ni tokens en git. Van en `secrets.h` y `.env` (ignorados), con `secrets.example.h` y `.env.example`.

## 6. Requisitos de la aplicación web (borrador para confirmar en F10)

1. **Panel en vivo:** V, I, P, FP, frecuencia, energía de la sesión y total, temperatura de la sonda y del ambiente, humedad, estado de K1 y por qué (app, horario, PARAR, temperatura, falla, límite), RSSI, en línea o no, alarmas activas.
2. **Control:** permitir o detener la carga con confirmación, horarios de carga, límites por sesión (kWh, tiempo, costo), umbral de temperatura (el equipo lo aplica localmente) y reconocer alarmas.
3. **Historial:** sesiones con inicio, fin, kWh, duración y costo (tarifa en COP/kWh); gráficas de potencia, tensión, corriente y temperatura; exportar a CSV.
4. **Alertas:** sobretemperatura, sin red o sag, equipo fuera de línea, falla del medidor (WarnOut/CalErr) y PARAR pulsado. Notificación por un canal a elegir.
5. **Configuración del equipo:** nombre, tensión nominal, tarifa, zona horaria (America/Bogota), calibración (solo lectura salvo modo avanzado), versión de firmware y OTA.
6. **Usuarios:** inicio de sesión; propietario y, opcional, usuarios de solo lectura; registro del equipo con credenciales propias.
7. En español y pensada primero para el celular. Si el equipo está fuera de línea, muestra el último estado y desde cuándo.
8. **Simulador del equipo:** un script que habla el mismo protocolo, para desarrollar y probar la app sin la placa.

## 7. Decisiones abiertas para F10 (2–3 opciones cada una, con recomendación)

**Decididas el 23 nov (D21–D30)** y, el 24 nov, cambio a Firebase (D31) y diseño de la app (D32): ver `ARQUITECTURA.md` y la sección «Fase 10» de `docs/DECISIONES.md`.

| Decisión | Opciones a comparar |
|---|---|
| Firmware | Arduino-ESP32 en PlatformIO · ESP-IDF |
| Transporte equipo ↔ servidor | MQTT sobre TLS (broker administrado o propio) · WebSocket seguro al backend · HTTPS |
| Backend y base de datos | servicio administrado con base de datos, autenticación y tiempo real · backend propio con Postgres o una base de series de tiempo · otra |
| Frontend y hosting | framework, librería de gráficas, hosting gratis o de bajo costo, dominio (por ejemplo un subdominio de nicolasgomez.dev) |
| Autenticación | usuarios; credenciales y certificados por equipo |
| Aprovisionamiento del WiFi | portal cautivo · BLE · archivo no versionado |
| OTA | desde la app · solo por USB |
| Notificaciones | correo · Telegram · push |

## 8. Estructura propuesta del repo

```text
firmware/
  prueba_placa/      firmware de pruebas (S1–S5), PlatformIO
  evse_monitor/      firmware final
app/                 backend y frontend
tools/simulador/     simulador del equipo
docs/software/       ARQUITECTURA.md, PROTOCOLO_MENSAJES.md, guía de instalación y uso
```
