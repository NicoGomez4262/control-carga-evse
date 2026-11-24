#include "sensores.h"
#include <OneWire.h>
#include <Wire.h>
#include "config.h"

namespace sensores {

static constexpr uint8_t AHT = 0x38;
static constexpr uint8_t RTC = 0x68;
static OneWire ow(pin::OW);
static uint32_t ahtT0 = 0;
static bool ahtPendiente = false;
static uint32_t sondaT0 = 0;
static bool sondaPendiente = false;

void begin() {
  Wire.begin(pin::SDA, pin::SCL, 100000);
  Wire.setTimeOut(20);
  pinMode(pin::RTC_INT, INPUT);
  // DS3231: INTCN = 1 y sin onda cuadrada (valor de encendido), para que IO18 quede en alto.
  Wire.beginTransmission(RTC);
  Wire.write(0x0E);
  Wire.write(0x1C);
  Wire.endTransmission();
}

// ------------------------------------------------------------------ AHT20
static uint8_t crc8(const uint8_t *d, int n) {
  uint8_t c = 0xFF;
  for (int i = 0; i < n; i++) {
    c ^= d[i];
    for (int b = 0; b < 8; b++) c = (c & 0x80) ? (uint8_t)((c << 1) ^ 0x31) : (uint8_t)(c << 1);
  }
  return c;
}

void ahtDisparar() {
  Wire.beginTransmission(AHT);
  Wire.write(0x71);
  if (Wire.endTransmission() != 0) {
    ahtPendiente = false;
    return;
  }
  Wire.requestFrom((int)AHT, 1);
  uint8_t est = Wire.available() ? Wire.read() : 0;
  if ((est & 0x18) != 0x18) {
    Wire.beginTransmission(AHT);
    Wire.write(0xBE);
    Wire.write(0x08);
    Wire.write(0x00);
    Wire.endTransmission();
    delay(10);
  }
  Wire.beginTransmission(AHT);
  Wire.write(0xAC);
  Wire.write(0x33);
  Wire.write(0x00);
  ahtPendiente = Wire.endTransmission() == 0;
  ahtT0 = millis();
}

bool ahtLeer(float &t, float &h) {
  if (!ahtPendiente || millis() - ahtT0 < 85) return false;
  ahtPendiente = false;
  uint8_t d[7] = {0};
  if (Wire.requestFrom((int)AHT, 7) != 7) return false;
  for (int i = 0; i < 7; i++) d[i] = Wire.read();
  if (d[0] & 0x80) return false;            // ocupado
  if (crc8(d, 6) != d[6]) return false;
  uint32_t rh = ((uint32_t)d[1] << 12) | ((uint32_t)d[2] << 4) | (d[3] >> 4);
  uint32_t rt = (((uint32_t)d[3] & 0x0F) << 16) | ((uint32_t)d[4] << 8) | d[5];
  h = rh * 100.0f / 1048576.0f;
  t = rt * 200.0f / 1048576.0f - 50.0f;
  return true;
}

// ------------------------------------------------------------------ DS18B20 (una sola sonda: Skip ROM)
bool sondaPresente() { return ow.reset() == 1; }

void sondaDisparar() {
  if (ow.reset() != 1) {
    sondaPendiente = false;
    return;
  }
  ow.skip();
  ow.write(0x44);  // Convert T (12 bits, 750 ms)
  sondaPendiente = true;
  sondaT0 = millis();
}

bool sondaLeer(float &t) {
  if (!sondaPendiente || millis() - sondaT0 < 800) return false;
  sondaPendiente = false;
  if (ow.reset() != 1) return false;
  ow.skip();
  ow.write(0xBE);
  uint8_t sp[9];
  for (int k = 0; k < 9; k++) sp[k] = ow.read();
  if (OneWire::crc8(sp, 8) != sp[8]) return false;
  int16_t raw = (int16_t)((sp[1] << 8) | sp[0]);
  if (raw == 0x0550) return false;  // 85 °C: valor de encendido, conversión no terminada
  t = raw / 16.0f;
  return t > -55 && t < 125;
}

// ------------------------------------------------------------------ DS3231
static uint8_t bcd2bin(uint8_t v) { return (v & 0x0F) + 10 * (v >> 4); }
static uint8_t bin2bcd(uint8_t v) { return (uint8_t)(((v / 10) << 4) | (v % 10)); }

bool rtcPresente() {
  Wire.beginTransmission(RTC);
  return Wire.endTransmission() == 0;
}

bool rtcLeer(uint32_t &epoch, bool &osf) {
  Wire.beginTransmission(RTC);
  Wire.write(0x00);
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom((int)RTC, 7) != 7) return false;
  uint8_t r[7];
  for (int i = 0; i < 7; i++) r[i] = Wire.read();
  Wire.beginTransmission(RTC);
  Wire.write(0x0F);
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom((int)RTC, 1) != 1) return false;
  uint8_t est = Wire.read();
  osf = est & 0x80;
  int y = 2000 + bcd2bin(r[6]) + ((r[5] & 0x80) ? 100 : 0);
  epoch = epochDesdeCivil(y, bcd2bin(r[5] & 0x1F), bcd2bin(r[4] & 0x3F), bcd2bin(r[2] & 0x3F), bcd2bin(r[1] & 0x7F),
                          bcd2bin(r[0] & 0x7F));
  return true;
}

bool rtcEscribir(uint32_t t) {
  int y, mo, d, h, mi, s, dow;
  civilDesdeEpoch(t, y, mo, d, h, mi, s, dow);
  uint8_t r[7] = {bin2bcd(s), bin2bcd(mi), bin2bcd(h), (uint8_t)(dow + 1), bin2bcd(d), bin2bcd(mo),
                  bin2bcd((uint8_t)(y - 2000))};
  Wire.beginTransmission(RTC);
  Wire.write(0x00);
  for (uint8_t b : r) Wire.write(b);
  if (Wire.endTransmission() != 0) return false;
  // Borrar OSF.
  Wire.beginTransmission(RTC);
  Wire.write(0x0F);
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom((int)RTC, 1) != 1) return false;
  uint8_t est = Wire.read() & ~0x80;
  Wire.beginTransmission(RTC);
  Wire.write(0x0F);
  Wire.write(est);
  return Wire.endTransmission() == 0;
}

// ------------------------------------------------------------------ fechas (algoritmos de Howard Hinnant)
uint32_t epochDesdeCivil(int y, int mo, int d, int h, int mi, int s) {
  y -= mo <= 2;
  const int era = (y >= 0 ? y : y - 399) / 400;
  const unsigned yoe = (unsigned)(y - era * 400);
  const unsigned doy = (153 * (mo + (mo > 2 ? -3 : 9)) + 2) / 5 + d - 1;
  const unsigned doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
  int64_t dias = (int64_t)era * 146097 + doe - 719468;
  return (uint32_t)(dias * 86400 + h * 3600 + mi * 60 + s);
}

void civilDesdeEpoch(uint32_t t, int &y, int &mo, int &d, int &h, int &mi, int &s, int &dow) {
  int64_t z = t / 86400;
  uint32_t sd = t % 86400;
  h = sd / 3600;
  mi = sd / 60 % 60;
  s = sd % 60;
  dow = (int)((z + 4) % 7);  // 1970-01-01 fue jueves; 0 = domingo
  z += 719468;
  const int64_t era = z / 146097;
  const unsigned doe = (unsigned)(z - era * 146097);
  const unsigned yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365;
  y = (int)yoe + (int)era * 400;
  const unsigned doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
  const unsigned mp = (5 * doy + 2) / 153;
  d = doy - (153 * mp + 2) / 5 + 1;
  mo = mp < 10 ? mp + 3 : mp - 9;
  y += (mo <= 2);
}

}  // namespace sensores
