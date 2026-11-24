// EVSE Monitor Rev 1.0 — firmware de pruebas (Fase 10B)
//
// Menú por el monitor serie (115200, UART0 por el CH340C) para correr S1–S6 de
// docs/pruebas/PROTOCOLO_PRUEBAS.md, un comando por bloque. No usa WiFi salvo en S6.
// Funciona con o sin U1: sin U1, la placa va con 3,30 V en TP3 (límite 0,25 A) y,
// para K1, 12 V en J6 (límite 0,05 A).
//
// Escribe «ayuda» y Enter para ver los comandos.

#include <Arduino.h>
#include <Wire.h>
#include <SPI.h>
#include <OneWire.h>
#include <WiFi.h>
#include <WiFiUdp.h>
#include <esp_system.h>
#include <esp_mac.h>

// ---------------------------------------------------------------- pines (mapa de F4)
static const int PIN_MEAS_CS = 10;
static const int PIN_MEAS_MOSI = 11;
static const int PIN_MEAS_SCK = 12;
static const int PIN_MEAS_MISO = 13;
static const int PIN_MEAS_IRQ = 14;
static const int PIN_MEAS_WARN = 21;
static const int PIN_MEAS_ZX = 17;
static const int PIN_SDA = 8;
static const int PIN_SCL = 9;
static const int PIN_OW = 4;
static const int PIN_RTC_INT = 18;
static const int PIN_RELAY_EN = 5;
static const int PIN_LED_WIFI = 6;   // LED3 verde
static const int PIN_LED_CARGA = 7;  // LED4 verde
static const int PIN_LED_FALLA = 15; // LED5 rojo
static const int PIN_PARAR = 16;     // SW1 y J7, activo en bajo

static const uint8_t I2C_AHT20 = 0x38;
static const uint8_t I2C_DS3231 = 0x68;

static SPISettings spiAtm(100000, MSBFIRST, SPI_MODE3);
static OneWire ow(PIN_OW);

// ---------------------------------------------------------------- utilidades
static bool hayTecla() {
  if (Serial.available()) {
    while (Serial.available()) Serial.read();
    return true;
  }
  return false;
}

static String leerLinea() {
  static String buf;
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\r' || c == '\n') {
      if (buf.length() == 0) continue;
      Serial.println();
      String l = buf;
      buf = "";
      l.trim();
      return l;
    }
    if (c == 8 || c == 127) {  // retroceso
      if (buf.length()) {
        buf.remove(buf.length() - 1);
        Serial.print("\b \b");
      }
      continue;
    }
    if (buf.length() < 120) {
      buf += c;
      Serial.print(c);
    }
  }
  return String();
}

static void resultado(bool ok, const char *texto) {
  Serial.printf("  [%s] %s\n", ok ? " OK " : "FALLA", texto);
}

static const char *motivoReset(esp_reset_reason_t r) {
  switch (r) {
    case ESP_RST_POWERON: return "encendido (power-on)";
    case ESP_RST_EXT: return "pin EN externo";
    case ESP_RST_SW: return "software (esp_restart)";
    case ESP_RST_PANIC: return "excepción (panic)";
    case ESP_RST_INT_WDT: return "watchdog de interrupciones";
    case ESP_RST_TASK_WDT: return "watchdog de tareas";
    case ESP_RST_WDT: return "otro watchdog";
    case ESP_RST_DEEPSLEEP: return "salida de deep sleep";
    case ESP_RST_BROWNOUT: return "BROWNOUT (cayó la alimentación)";
    case ESP_RST_SDIO: return "SDIO";
    default: return "desconocido";
  }
}

// ---------------------------------------------------------------- info
static void cmdInfo() {
  uint8_t mac[6];
  esp_read_mac(mac, ESP_MAC_WIFI_STA);
  Serial.println("Información del módulo:");
  Serial.printf("  Chip: %s rev %d, %d núcleos, %u MHz\n", ESP.getChipModel(), ESP.getChipRevision(),
                ESP.getChipCores(), (unsigned)ESP.getCpuFreqMHz());
  Serial.printf("  MAC WiFi: %02X:%02X:%02X:%02X:%02X:%02X  (anótala en el protocolo, H5)\n", mac[0], mac[1], mac[2],
                mac[3], mac[4], mac[5]);
  Serial.printf("  Flash: %u MB · PSRAM: %u KB (esperado 16 MB y ~2048 KB)\n", (unsigned)(ESP.getFlashChipSize() >> 20),
                (unsigned)(ESP.getPsramSize() >> 10));
  Serial.printf("  Memoria libre: %u bytes\n", (unsigned)ESP.getFreeHeap());
  Serial.printf("  Último reset: %s\n", motivoReset(esp_reset_reason()));
}

// ---------------------------------------------------------------- S1 LEDs y PARAR
static void cmdLeds() {
  struct { int pin; const char *nombre; } leds[] = {
      {PIN_LED_WIFI, "LED3 (WiFi, verde, IO6)"},
      {PIN_LED_CARGA, "LED4 (carga, verde, IO7)"},
      {PIN_LED_FALLA, "LED5 (falla, rojo, IO15)"},
  };
  Serial.println("S1-1 · LEDs uno por uno, 1,5 s cada uno (dos vueltas):");
  for (int vuelta = 0; vuelta < 2; vuelta++) {
    for (auto &l : leds) {
      Serial.printf("  encendido: %s\n", l.nombre);
      digitalWrite(l.pin, HIGH);
      delay(1500);
      digitalWrite(l.pin, LOW);
    }
  }
  Serial.println("  Anota en S1-1 si cada LED encendió en su turno.");
}

static void cmdParar() {
  Serial.println("S1-2 y S1-3 · PARAR durante 20 s (cualquier tecla sale). Pulsa SW1 y después une J7-1 con J7-2.");
  int ultimo = -1;
  uint32_t t0 = millis();
  while (millis() - t0 < 20000) {
    if (hayTecla()) break;
    int v = digitalRead(PIN_PARAR);
    if (v != ultimo) {
      Serial.printf("  PARAR = %d %s\n", v, v == 0 ? "(pulsado)" : "(suelto)");
      digitalWrite(PIN_LED_FALLA, v == 0);
      ultimo = v;
    }
    delay(10);
  }
  digitalWrite(PIN_LED_FALLA, LOW);
  Serial.println("  Fin. Esperado: PARAR = 0 al pulsar SW1 y al unir J7.");
}

// ---------------------------------------------------------------- S2 I²C
static void escanearI2C(uint32_t hz) {
  Wire.setClock(hz);
  Serial.printf("  %u kHz:", (unsigned)(hz / 1000));
  int n = 0;
  bool aht = false, rtc = false;
  for (uint8_t a = 1; a < 127; a++) {
    Wire.beginTransmission(a);
    if (Wire.endTransmission() == 0) {
      Serial.printf(" 0x%02X", a);
      n++;
      if (a == I2C_AHT20) aht = true;
      if (a == I2C_DS3231) rtc = true;
    }
  }
  if (!n) Serial.print(" ninguno");
  Serial.println();
  resultado(aht && rtc && n == 2, "solo 0x38 (AHT20) y 0x68 (DS3231)");
}

static void cmdI2C() {
  Serial.println("S2-1 · Escaneo I²C (SDA IO8, SCL IO9):");
  escanearI2C(100000);
  escanearI2C(400000);
  Wire.setClock(100000);
}

static uint8_t crc8Aht(const uint8_t *d, int n) {
  uint8_t c = 0xFF;
  for (int i = 0; i < n; i++) {
    c ^= d[i];
    for (int b = 0; b < 8; b++) c = (c & 0x80) ? (uint8_t)((c << 1) ^ 0x31) : (uint8_t)(c << 1);
  }
  return c;
}

static bool leerAht20(float &t, float &h) {
  Wire.beginTransmission(I2C_AHT20);
  Wire.write(0x71);
  if (Wire.endTransmission() != 0) return false;
  Wire.requestFrom((int)I2C_AHT20, 1);
  uint8_t est = Wire.available() ? Wire.read() : 0;
  if ((est & 0x18) != 0x18) {  // sin calibrar: inicializar
    Wire.beginTransmission(I2C_AHT20);
    Wire.write(0xBE);
    Wire.write(0x08);
    Wire.write(0x00);
    Wire.endTransmission();
    delay(10);
  }
  Wire.beginTransmission(I2C_AHT20);
  Wire.write(0xAC);
  Wire.write(0x33);
  Wire.write(0x00);
  if (Wire.endTransmission() != 0) return false;
  delay(85);
  uint8_t d[7] = {0};
  for (int intento = 0; intento < 5; intento++) {
    Wire.requestFrom((int)I2C_AHT20, 7);
    for (int i = 0; i < 7 && Wire.available(); i++) d[i] = Wire.read();
    if (!(d[0] & 0x80)) break;  // ya no está ocupado
    delay(10);
  }
  if (d[0] & 0x80) return false;
  if (crc8Aht(d, 6) != d[6]) return false;
  uint32_t rh = ((uint32_t)d[1] << 12) | ((uint32_t)d[2] << 4) | (d[3] >> 4);
  uint32_t rt = (((uint32_t)d[3] & 0x0F) << 16) | ((uint32_t)d[4] << 8) | d[5];
  h = rh * 100.0f / 1048576.0f;
  t = rt * 200.0f / 1048576.0f - 50.0f;
  return true;
}

static void cmdAht() {
  Serial.println("S2-2 · AHT20 (0x38):");
  float t, h;
  if (leerAht20(t, h)) {
    Serial.printf("  Temperatura %.2f °C · humedad %.1f %%HR\n", t, h);
    resultado(t > -10 && t < 60 && h >= 0 && h <= 100, "lectura con CRC correcto; compárala con un termómetro");
  } else {
    resultado(false, "el AHT20 no responde o el CRC no coincide");
  }
}

// ---------------------------------------------------------------- S2 DS3231
static uint8_t bcd2bin(uint8_t v) { return (v & 0x0F) + 10 * (v >> 4); }
static uint8_t bin2bcd(uint8_t v) { return (uint8_t)(((v / 10) << 4) | (v % 10)); }

static bool rtcLeerReg(uint8_t reg, uint8_t *buf, int n) {
  Wire.beginTransmission(I2C_DS3231);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom((int)I2C_DS3231, n) != n) return false;
  for (int i = 0; i < n; i++) buf[i] = Wire.read();
  return true;
}

static bool rtcEscribirReg(uint8_t reg, const uint8_t *buf, int n) {
  Wire.beginTransmission(I2C_DS3231);
  Wire.write(reg);
  for (int i = 0; i < n; i++) Wire.write(buf[i]);
  return Wire.endTransmission() == 0;
}

// Días desde 1970-01-01 (algoritmo de Howard Hinnant).
static int64_t diasDesdeCivil(int y, unsigned m, unsigned d) {
  y -= m <= 2;
  const int era = (y >= 0 ? y : y - 399) / 400;
  const unsigned yoe = (unsigned)(y - era * 400);
  const unsigned doy = (153 * (m + (m > 2 ? -3 : 9)) + 2) / 5 + d - 1;
  const unsigned doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
  return era * 146097 + (int64_t)doe - 719468;
}

static void civilDesdeDias(int64_t z, int &y, unsigned &m, unsigned &d) {
  z += 719468;
  const int64_t era = (z >= 0 ? z : z - 146096) / 146097;
  const unsigned doe = (unsigned)(z - era * 146097);
  const unsigned yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365;
  y = (int)yoe + (int)era * 400;
  const unsigned doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
  const unsigned mp = (5 * doy + 2) / 153;
  d = doy - (153 * mp + 2) / 5 + 1;
  m = mp < 10 ? mp + 3 : mp - 9;
  y += (m <= 2);
}

static void imprimirEpoch(const char *etiqueta, int64_t t) {
  int y;
  unsigned mo, d;
  int64_t dias = t >= 0 ? t / 86400 : (t - 86399) / 86400;
  int64_t s = t - dias * 86400;
  civilDesdeDias(dias, y, mo, d);
  Serial.printf("%s%04d-%02u-%02u %02d:%02d:%02d", etiqueta, y, mo, d, (int)(s / 3600), (int)(s / 60 % 60), (int)(s % 60));
}

static void cmdRtc() {
  Serial.println("S2-5 / S2-7 · DS3231 (0x68). Guarda la hora en UTC; aquí se muestra también la de Colombia (UTC−5).");
  uint8_t r[7], ctl[2], tmp[2];
  if (!rtcLeerReg(0x00, r, 7) || !rtcLeerReg(0x0E, ctl, 2) || !rtcLeerReg(0x11, tmp, 2)) {
    resultado(false, "el DS3231 no responde");
    return;
  }
  int y = 2000 + bcd2bin(r[6]) + ((r[5] & 0x80) ? 100 : 0);
  int mo = bcd2bin(r[5] & 0x1F), d = bcd2bin(r[4] & 0x3F);
  int hh = bcd2bin(r[2] & 0x3F), mi = bcd2bin(r[1] & 0x7F), ss = bcd2bin(r[0] & 0x7F);
  int64_t t = diasDesdeCivil(y, mo, d) * 86400 + hh * 3600 + mi * 60 + ss;
  imprimirEpoch("  UTC:      ", t);
  Serial.println();
  imprimirEpoch("  Colombia: ", t - 5 * 3600);
  Serial.println();
  bool osf = ctl[1] & 0x80;
  Serial.printf("  Control 0x0E = 0x%02X · Estado 0x0F = 0x%02X · OSF = %d · temperatura interna %.2f °C\n", ctl[0], ctl[1],
                osf, (int8_t)tmp[0] + (tmp[1] >> 6) * 0.25f);
  resultado(!osf, osf ? "OSF = 1: el oscilador se detuvo (pila descargada o sin poner la hora)" : "OSF = 0");
}

// «s2 hora AAAA-MM-DD HH:MM:SS» con la hora de Colombia; se guarda en UTC.
static void cmdRtcPoner(const String &arg) {
  int y, mo, d, hh, mi, ss;
  if (sscanf(arg.c_str(), "%d-%d-%d %d:%d:%d", &y, &mo, &d, &hh, &mi, &ss) != 6 || y < 2024 || y > 2099 || mo < 1 ||
      mo > 12 || d < 1 || d > 31 || hh > 23 || mi > 59 || ss > 59) {
    Serial.println("  Formato: s2 hora 2026-11-23 18:30:00   (hora de Colombia)");
    return;
  }
  int64_t t = diasDesdeCivil(y, mo, d) * 86400 + hh * 3600 + mi * 60 + ss + 5 * 3600;  // a UTC
  int64_t dias = t / 86400;
  int64_t s = t - dias * 86400;
  int uy;
  unsigned um, ud;
  civilDesdeDias(dias, uy, um, ud);
  uint8_t dow = (uint8_t)(((dias % 7) + 11) % 7 + 1);  // 1 = domingo... no se usa
  uint8_t r[7] = {bin2bcd(s % 60), bin2bcd(s / 60 % 60), bin2bcd(s / 3600), dow, bin2bcd(ud), bin2bcd(um),
                  bin2bcd(uy - 2000)};
  if (!rtcEscribirReg(0x00, r, 7)) {
    resultado(false, "no se pudo escribir el DS3231");
    return;
  }
  uint8_t est;
  rtcLeerReg(0x0F, &est, 1);
  est &= ~0x80;  // borrar OSF
  rtcEscribirReg(0x0F, &est, 1);
  Serial.println("  Hora puesta y OSF borrado.");
  cmdRtc();
}

static volatile uint32_t flancosRtc = 0;
static void IRAM_ATTR isrRtc() { flancosRtc++; }

static void cmdRtc1Hz() {
  Serial.println("S2-6 · Salida de 1 Hz del DS3231 en IO18 (INTCN = 0, RS = 00), 10 s:");
  uint8_t ctl;
  if (!rtcLeerReg(0x0E, &ctl, 1)) {
    resultado(false, "el DS3231 no responde");
    return;
  }
  uint8_t nuevo = ctl & ~(0x04 | 0x18);  // INTCN = 0, RS2:RS1 = 00
  rtcEscribirReg(0x0E, &nuevo, 1);
  flancosRtc = 0;
  attachInterrupt(digitalPinToInterrupt(PIN_RTC_INT), isrRtc, FALLING);
  for (int i = 0; i < 10; i++) {
    delay(1000);
    Serial.printf("  %2d s: %u flancos\n", i + 1, (unsigned)flancosRtc);
  }
  detachInterrupt(digitalPinToInterrupt(PIN_RTC_INT));
  uint8_t restaurar = 0x1C;  // valor de encendido: INTCN = 1, sin onda cuadrada
  rtcEscribirReg(0x0E, &restaurar, 1);
  uint32_t n = flancosRtc;
  resultado(n >= 9 && n <= 11, "10 flancos en 10 s (9–11 por el inicio y fin de la ventana)");
}

// ---------------------------------------------------------------- S3 DS18B20
static void cmdSonda() {
  Serial.println("S3-2 / S3-3 · Sonda DS18B20 en J4 (1-Wire en IO4):");
  uint8_t rom[8];
  int n = 0;
  bool hayValida = false;
  uint8_t elegida[8];
  ow.reset_search();
  while (ow.search(rom)) {
    n++;
    Serial.print("  Encontrado:");
    for (int i = 0; i < 8; i++) Serial.printf(" %02X", rom[i]);
    bool crcOk = OneWire::crc8(rom, 7) == rom[7];
    Serial.printf("  familia 0x%02X, CRC %s\n", rom[0], crcOk ? "bien" : "MAL");
    if (crcOk && rom[0] == 0x28 && !hayValida) {
      memcpy(elegida, rom, 8);
      hayValida = true;
    }
  }
  resultado(n == 1 && hayValida, "un dispositivo, familia 0x28");
  if (!hayValida) return;
  Serial.println("  Leyendo cada 2 s durante 20 s (apriétala con la mano: debe subir). Cualquier tecla sale.");
  for (int i = 0; i < 10; i++) {
    ow.reset();
    ow.select(elegida);
    ow.write(0x44);  // convertir
    uint32_t t0 = millis();
    while (!ow.read_bit() && millis() - t0 < 1000) delay(10);
    ow.reset();
    ow.select(elegida);
    ow.write(0xBE);  // leer scratchpad
    uint8_t sp[9];
    for (int k = 0; k < 9; k++) sp[k] = ow.read();
    if (OneWire::crc8(sp, 8) != sp[8]) {
      Serial.println("  CRC del scratchpad MAL");
    } else {
      int16_t raw = (int16_t)((sp[1] << 8) | sp[0]);
      float tA;
      float tC = raw / 16.0f;
      float hA;
      if (leerAht20(tA, hA))
        Serial.printf("  Sonda %.2f °C · AHT20 %.2f °C\n", tC, tA);
      else
        Serial.printf("  Sonda %.2f °C\n", tC);
    }
    if (hayTecla()) break;
    delay(1000);
  }
}

// ---------------------------------------------------------------- S4 K1
static void cmdK1(const String &arg) {
  if (arg == "1") {
    digitalWrite(PIN_RELAY_EN, HIGH);
    Serial.println("S4-2 · RELAY_EN = 1 → K1 cerrado (carga permitida).");
    Serial.println("  Esperado: J2 (17–18) 25–40 Ω · R41 (34–33) ≈ 8,4 V · LED6 encendido. Necesita 12 V en J6.");
  } else if (arg == "0") {
    digitalWrite(PIN_RELAY_EN, LOW);
    Serial.println("S4-3 · RELAY_EN = 0 → K1 abierto.");
    Serial.println("  Esperado: J2 (17–18) OL · R41 (34–33) 0 V · LED6 apagado.");
  } else {
    Serial.printf("  RELAY_EN = %d. Uso: s4 k1 1  |  s4 k1 0\n", digitalRead(PIN_RELAY_EN));
    Serial.println("  S4-4: con «s4 k1 1», une un instante 37 (J8-4, EN) con 39 (J8-6, GND): J2 debe abrir (R40).");
  }
}

// ---------------------------------------------------------------- S5 ATM90E26
static uint16_t atmTrama(bool leer, uint8_t dir, uint16_t dato) {
  SPI.beginTransaction(spiAtm);
  digitalWrite(PIN_MEAS_CS, LOW);
  delayMicroseconds(10);
  SPI.transfer((uint8_t)((leer ? 0x80 : 0x00) | (dir & 0x7F)));
  delayMicroseconds(5);
  uint16_t r;
  if (leer) {
    uint8_t hi = SPI.transfer(0x00);
    uint8_t lo = SPI.transfer(0x00);
    r = (uint16_t)((hi << 8) | lo);
  } else {
    SPI.transfer((uint8_t)(dato >> 8));
    SPI.transfer((uint8_t)(dato & 0xFF));
    r = dato;
  }
  delayMicroseconds(5);
  digitalWrite(PIN_MEAS_CS, HIGH);
  SPI.endTransaction();
  delayMicroseconds(10);
  return r;
}
static uint16_t atmLeer(uint8_t dir) { return atmTrama(true, dir, 0); }
static void atmEscribir(uint8_t dir, uint16_t v) { atmTrama(false, dir, v); }

static float atmPotencia(uint16_t raw) { return (int16_t)raw * 1.0f; }  // complemento a 2, 1 LSB = 1 W
static float atmSignoMagnitud(uint16_t raw, float escala) {
  float v = (raw & 0x7FFF) * escala;
  return (raw & 0x8000) ? -v : v;
}

static void cmdAtmLeer() {
  Serial.println("ATM90E26 · registros principales:");
  struct { uint8_t dir; const char *nombre; } regs[] = {
      {0x01, "SysStatus"}, {0x02, "FuncEn"}, {0x03, "SagTh"}, {0x20, "CalStart"}, {0x2B, "MMode"},
      {0x30, "AdjStart"}, {0x31, "Ugain"}, {0x33, "IgainN"}, {0x2C, "CS1 (calculada)"}, {0x3B, "CS2 (calculada)"},
  };
  for (auto &r : regs) Serial.printf("  %02XH %-16s = %04XH\n", r.dir, r.nombre, atmLeer(r.dir));
  uint16_t urms = atmLeer(0x49), irms2 = atmLeer(0x68), freq = atmLeer(0x4C), p2 = atmLeer(0x6A), pf2 = atmLeer(0x6D);
  Serial.printf("  Urms %.2f V · Irms2 %.3f A · Freq %.2f Hz · Pmean2 %.0f W · PowerF2 %.3f\n", urms / 100.0f,
                irms2 / 1000.0f, freq / 100.0f, atmPotencia(p2), atmSignoMagnitud(pf2, 0.001f));
  Serial.printf("  WarnOut (IO21) = %d · IRQ (IO14) = %d · ZX (IO17) = %d\n", digitalRead(PIN_MEAS_WARN),
                digitalRead(PIN_MEAS_IRQ), digitalRead(PIN_MEAS_ZX));
}

// Espera una línea cualquiera (también vacía) sin usar el búfer de leerLinea.
static bool pausa() {
  Serial.println("  … Enter para seguir, «x» y Enter para salir");
  String l;
  while (true) {
    if (Serial.available()) {
      char c = (char)Serial.read();
      if (c == '\r' || c == '\n') {
        delay(5);
        while (Serial.available() && (Serial.peek() == '\n' || Serial.peek() == '\r')) Serial.read();
        Serial.println();
        return !(l == "x" || l == "X");
      }
      l += c;
      Serial.print(c);
    }
    delay(5);
  }
}

static void cmdAtmSecuencia() {
  Serial.println("S5 · ATM90E26 por SPI (modo 3, 100 kHz). Sin red y sin CT.");
  uint16_t v;

  v = atmLeer(0x20);
  Serial.printf("S5-1 · CalStart (20H) = %04XH\n", v);
  resultado(v == 0x6886, "6886H (valor de encendido)");
  if (v == 0xFFFF || v == 0x0000) Serial.println("  Pista: FFFFH o 0000H = el ATM90E26 no contesta (SPI, CS, reloj Y1).");
  if (!pausa()) return;

  v = atmLeer(0x2B);
  Serial.printf("S5-2 · MMode (2BH) = %04XH\n", v);
  resultado(v == 0x9422, "9422H");
  if (!pausa()) return;

  atmEscribir(0x20, 0x5678);
  uint16_t a = atmLeer(0x20);
  uint16_t b = atmLeer(0x06);
  Serial.printf("S5-3 · escrito 5678H en CalStart → CalStart = %04XH · LastData (06H) = %04XH\n", a, b);
  resultado(a == 0x5678 && b == 0x5678, "5678H en los dos");
  if (!pausa()) return;

  int warnAntes = digitalRead(PIN_MEAS_WARN), irqAntes = digitalRead(PIN_MEAS_IRQ);
  atmEscribir(0x20, 0x8765);
  delay(50);
  uint16_t st = atmLeer(0x01);
  int warn = digitalRead(PIN_MEAS_WARN), irq = digitalRead(PIN_MEAS_IRQ);
  Serial.printf("S5-4 · escrito 8765H sin CS1 válido → SysStatus (01H) = %04XH, CalErr = %d%d\n", st, (st >> 15) & 1,
                (st >> 14) & 1);
  resultado((st & 0xC000) == 0xC000, "CalErr = 11");
  resultado(warn != warnAntes && irq != irqAntes, "WarnOut e IRQ cambiaron de estado");
  // Polaridad: el nivel «sin error» es el de antes; el nivel «con error» es el de ahora.
  const char *nombres[2] = {"WarnOut (red MEAS_WARN, IO21)", "IRQ (red MEAS_IRQ, IO14)"};
  int antes[2] = {warnAntes, irqAntes}, ahora[2] = {warn, irq};
  Serial.println("  ┌─ Copia estas dos líneas en el registro del protocolo (S5-4):");
  for (int k = 0; k < 2; k++) {
    if (antes[k] == ahora[k])
      Serial.printf("  │ %s: NO cambió (se quedó en %s). Revisa la soldadura de ese pin y la pista al ESP32.\n", nombres[k],
                    ahora[k] ? "ALTO, 3,3 V" : "BAJO, 0 V");
    else
      Serial.printf("  │ %s: normal %s → con error %s ⇒ ACTIVO EN %s\n", nombres[k], antes[k] ? "ALTO (3,3 V)" : "BAJO (0 V)",
                    ahora[k] ? "ALTO (3,3 V)" : "BAJO (0 V)", ahora[k] ? "ALTO" : "BAJO");
  }
  Serial.println("  └─ (el datasheet no dice la polaridad; el firmware final no depende de ella)");
  if (!pausa()) return;

  atmEscribir(0x00, 0x789A);
  delay(100);
  v = atmLeer(0x20);
  uint16_t st2 = atmLeer(0x01);
  Serial.printf("S5-5 · SoftReset (789AH en 00H) → CalStart = %04XH · SysStatus = %04XH · WarnOut %d · IRQ %d\n", v, st2,
                digitalRead(PIN_MEAS_WARN), digitalRead(PIN_MEAS_IRQ));
  resultado(v == 0x6886, "CalStart vuelve a 6886H");
  if (!pausa()) return;

  // Para medir hace falta un modo con la medición activa: 5678H en CalStart y AdjStart
  // (registros de encendido, sin revisar sumas). Es solo para la prueba.
  atmEscribir(0x20, 0x5678);
  atmEscribir(0x30, 0x5678);
  delay(1500);
  uint16_t urms = atmLeer(0x49), irms2 = atmLeer(0x68);
  Serial.printf("S5-6 · Urms (49H) = %.2f V · Irms2 (68H) = %.3f A (sin red ni CT)\n", urms / 100.0f, irms2 / 1000.0f);
  resultado(urms < 1000 && irms2 < 100, "≈ 0 (menos de 10 V y 0,1 A, ruido con las ganancias de fábrica)");
  Serial.println("Fin de S5. El chip quedó con CalStart = AdjStart = 5678H (medición con valores de fábrica).");
}

static void cmdAtmMonitor() {
  Serial.println("ATM90E26 · cada segundo (cualquier tecla sale). LNSel = 0 (CT en I2), registros «2».");
  Serial.println("  Ojo: pone MMode = 9022H y CalStart/AdjStart = 5678H (ganancias de fábrica, sin calibrar).");
  atmEscribir(0x20, 0x5678);
  atmEscribir(0x2B, 0x9022);
  atmEscribir(0x30, 0x5678);
  delay(1000);
  while (!hayTecla()) {
    uint16_t urms = atmLeer(0x49), irms2 = atmLeer(0x68), freq = atmLeer(0x4C), p2 = atmLeer(0x6A), pf2 = atmLeer(0x6D),
             st = atmLeer(0x01);
    Serial.printf("  U %7.2f V · I2 %6.3f A · P2 %6.0f W · FP %6.3f · f %5.2f Hz · Sys %04XH · Warn %d\n", urms / 100.0f,
                  irms2 / 1000.0f, atmPotencia(p2), atmSignoMagnitud(pf2, 0.001f), freq / 100.0f, st,
                  digitalRead(PIN_MEAS_WARN));
    delay(1000);
  }
}

static volatile uint32_t flancosZx = 0;
static void IRAM_ATTR isrZx() { flancosZx++; }

static void cmdZx() {
  Serial.println("S7-9 · Pulsos de ZX (IO17) durante 5 s:");
  flancosZx = 0;
  attachInterrupt(digitalPinToInterrupt(PIN_MEAS_ZX), isrZx, RISING);
  delay(5000);
  detachInterrupt(digitalPinToInterrupt(PIN_MEAS_ZX));
  Serial.printf("  %u flancos en 5 s = %.1f por segundo (60 o 120 según ZXCon; 0 sin red)\n", (unsigned)flancosZx,
                flancosZx / 5.0f);
}

// ---------------------------------------------------------------- S6 WiFi (solo con U1)
static void cmdWifiScan() {
  Serial.println("S6 · Escaneo WiFi (solo con U1 soldado y 12 V en J6; los picos llegan a 350 mA).");
  WiFi.mode(WIFI_STA);
  WiFi.setTxPower(WIFI_POWER_17dBm);
  int n = WiFi.scanNetworks();
  for (int i = 0; i < n; i++)
    Serial.printf("  %-32s %4d dBm  canal %2d %s\n", WiFi.SSID(i).c_str(), WiFi.RSSI(i), WiFi.channel(i),
                  WiFi.encryptionType(i) == WIFI_AUTH_OPEN ? "abierta" : "");
  if (n <= 0) Serial.println("  No se encontraron redes.");
  WiFi.scanDelete();
}

static void cmdWifiConectar(const String &arg) {
  int sp = arg.indexOf(' ');
  if (sp < 1) {
    Serial.println("  Uso: s6 con NOMBRE_RED CLAVE   (no se guarda en ningún lado)");
    return;
  }
  String ssid = arg.substring(0, sp), clave = arg.substring(sp + 1);
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid.c_str(), clave.c_str());
  WiFi.setTxPower(WIFI_POWER_17dBm);
  Serial.printf("S6-1/2 · Conectando a «%s» con TX = 17 dBm", ssid.c_str());
  uint32_t t0 = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - t0 < 20000) {
    delay(500);
    Serial.print('.');
  }
  Serial.println();
  if (WiFi.status() != WL_CONNECTED) {
    resultado(false, "no conectó en 20 s");
    return;
  }
  digitalWrite(PIN_LED_WIFI, HIGH);
  Serial.printf("  IP %s · RSSI %d dBm · TX %d (×0,25 dBm)\n", WiFi.localIP().toString().c_str(), WiFi.RSSI(),
                (int)WiFi.getTxPower());
  resultado(true, "conectado; anota el RSSI a 1 m y donde va a quedar la placa");
}

static void cmdWifiCarga() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("  Primero «s6 con NOMBRE_RED CLAVE».");
    return;
  }
  Serial.println("S6-3 · Transmisión continua 60 s (UDP de difusión, 1400 bytes). Mira el 3 (TP3) con el osciloscopio.");
  WiFiUDP udp;
  uint8_t paquete[1400];
  memset(paquete, 0xA5, sizeof(paquete));
  IPAddress difusion = WiFi.broadcastIP();
  uint32_t t0 = millis(), n = 0, ultimo = 0;
  while (millis() - t0 < 60000) {
    udp.beginPacket(difusion, 9);  // puerto 9 = «discard»
    udp.write(paquete, sizeof(paquete));
    if (udp.endPacket()) n++;
    if (millis() - ultimo > 5000) {
      ultimo = millis();
      Serial.printf("  %2lu s · %lu paquetes · RSSI %d dBm\n", (unsigned long)((millis() - t0) / 1000), (unsigned long)n,
                    WiFi.RSSI());
    }
    if (hayTecla()) break;
    delay(1);
  }
  Serial.printf("  Fin: %lu paquetes. Si la placa no se reinició, no hubo brownout (S6-3).\n", (unsigned long)n);
}

// ---------------------------------------------------------------- menú
static void ayuda() {
  Serial.println();
  Serial.println("=== EVSE Monitor Rev 1.0 · firmware de pruebas (S1–S6) ===");
  Serial.println("  info                      chip, MAC, flash, PSRAM y motivo del último reset (H5)");
  Serial.println("  s1 leds                   LED3, LED4 y LED5 uno por uno (S1-1)");
  Serial.println("  s1 parar                  muestra PARAR durante 20 s: SW1 y J7 (S1-2, S1-3)");
  Serial.println("  s2 i2c                    escaneo I²C a 100 y 400 kHz (S2-1)");
  Serial.println("  s2 aht                    temperatura y humedad del AHT20 (S2-2)");
  Serial.println("  s2 rtc                    hora y OSF del DS3231 (S2-5, S2-7)");
  Serial.println("  s2 hora AAAA-MM-DD HH:MM:SS   pone la hora (de Colombia) y borra OSF (S2-5)");
  Serial.println("  s2 1hz                    cuenta los flancos de 1 Hz en IO18 durante 10 s (S2-6)");
  Serial.println("  s3 sonda                  busca la DS18B20 y lee la temperatura (S3-2, S3-3)");
  Serial.println("  s4 k1 1 | s4 k1 0         RELAY_EN en alto o en bajo (S4-2, S4-3)");
  Serial.println("  s5                        ATM90E26 paso a paso (S5-1 a S5-6)");
  Serial.println("  s5 leer                   registros principales y medición");
  Serial.println("  s5 reg XX | s5 esc XX YYYY   lee o escribe un registro (hexadecimal)");
  Serial.println("  s5 monitor                U, I2, P, FP y frecuencia cada segundo (generador o S7)");
  Serial.println("  s5 zx                     cuenta los pulsos de cruce por cero en 5 s (S7-9)");
  Serial.println("  s6 scan | s6 con RED CLAVE | s6 carga   WiFi: solo con U1 soldado (S6)");
  Serial.println("  ayuda");
  Serial.println();
}

static void ejecutar(const String &linea) {
  String l = linea;
  String cmd = l, arg;
  int sp = l.indexOf(' ');
  if (sp > 0) {
    cmd = l.substring(0, sp);
    arg = l.substring(sp + 1);
    arg.trim();
  }
  cmd.toLowerCase();
  String sub = arg, resto;
  int sp2 = arg.indexOf(' ');
  if (sp2 > 0) {
    sub = arg.substring(0, sp2);
    resto = arg.substring(sp2 + 1);
    resto.trim();
  }
  sub.toLowerCase();

  if (cmd == "ayuda" || cmd == "?" || cmd == "help") ayuda();
  else if (cmd == "info") cmdInfo();
  else if (cmd == "s1" && sub == "leds") cmdLeds();
  else if (cmd == "s1" && sub == "parar") cmdParar();
  else if (cmd == "s2" && sub == "i2c") cmdI2C();
  else if (cmd == "s2" && sub == "aht") cmdAht();
  else if (cmd == "s2" && sub == "rtc") cmdRtc();
  else if (cmd == "s2" && sub == "hora") cmdRtcPoner(resto);
  else if (cmd == "s2" && sub == "1hz") cmdRtc1Hz();
  else if (cmd == "s3") cmdSonda();
  else if (cmd == "s4" && sub == "k1") cmdK1(resto);
  else if (cmd == "s5" && arg.length() == 0) cmdAtmSecuencia();
  else if (cmd == "s5" && sub == "leer") cmdAtmLeer();
  else if (cmd == "s5" && sub == "monitor") cmdAtmMonitor();
  else if (cmd == "s5" && sub == "zx") cmdZx();
  else if (cmd == "s5" && sub == "reg") {
    uint8_t dir = (uint8_t)strtoul(resto.c_str(), nullptr, 16);
    Serial.printf("  %02XH = %04XH\n", dir, atmLeer(dir));
  } else if (cmd == "s5" && sub == "esc") {
    unsigned dir, val;
    if (sscanf(resto.c_str(), "%x %x", &dir, &val) == 2) {
      atmEscribir((uint8_t)dir, (uint16_t)val);
      Serial.printf("  escrito %04XH en %02XH → se lee %04XH\n", val, dir, atmLeer((uint8_t)dir));
    } else {
      Serial.println("  Uso: s5 esc 2B 9022");
    }
  } else if (cmd == "s6" && sub == "scan") cmdWifiScan();
  else if (cmd == "s6" && sub == "con") cmdWifiConectar(resto);
  else if (cmd == "s6" && sub == "carga") cmdWifiCarga();
  else Serial.println("  Comando desconocido. Escribe «ayuda».");
}

void setup() {
  // Primero las salidas: K1 abierto y LEDs apagados.
  pinMode(PIN_RELAY_EN, OUTPUT);
  digitalWrite(PIN_RELAY_EN, LOW);
  for (int p : {PIN_LED_WIFI, PIN_LED_CARGA, PIN_LED_FALLA}) {
    pinMode(p, OUTPUT);
    digitalWrite(p, LOW);
  }
  pinMode(PIN_PARAR, INPUT);  // pull-up externo R27
  pinMode(PIN_MEAS_IRQ, INPUT);
  pinMode(PIN_MEAS_WARN, INPUT);
  pinMode(PIN_MEAS_ZX, INPUT);
  pinMode(PIN_RTC_INT, INPUT);  // pull-up externo R34
  pinMode(PIN_MEAS_CS, OUTPUT);
  digitalWrite(PIN_MEAS_CS, HIGH);

  Serial.begin(115200);
  delay(300);
  Wire.begin(PIN_SDA, PIN_SCL, 100000);
  SPI.begin(PIN_MEAS_SCK, PIN_MEAS_MISO, PIN_MEAS_MOSI, -1);
  delay(100);  // el AHT20 necesita ≥ 25 ms después del arranque (filtro RC de su VDD)

  Serial.println();
  Serial.println("EVSE Monitor · firmware de pruebas listo.");
  cmdInfo();
  ayuda();
  Serial.print("> ");
}

void loop() {
  String l = leerLinea();
  if (l.length()) {
    ejecutar(l);
    Serial.print("> ");
  }
  delay(5);
}
