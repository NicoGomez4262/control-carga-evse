#include "atm90e26.h"
#include <SPI.h>
#include <math.h>
#include "config.h"

namespace atm {

static SPISettings ajuste(100000, MSBFIRST, SPI_MODE3);

void begin() {
  pinMode(pin::MEAS_CS, OUTPUT);
  digitalWrite(pin::MEAS_CS, HIGH);
  pinMode(pin::MEAS_IRQ, INPUT);
  pinMode(pin::MEAS_WARN, INPUT);
  pinMode(pin::MEAS_ZX, INPUT);
  SPI.begin(pin::MEAS_SCK, pin::MEAS_MISO, pin::MEAS_MOSI, -1);
}

// Trama de 24 ciclos: 1 bit L/E, 7 de dirección, 16 de dato. Tiempos de la tabla 11 del datasheet
// (T = 122 ns): CS alto ≥ 3,7 µs y reloj alto ≥ 3,7 µs; a 100 kHz sobra.
static uint16_t trama(bool lectura, uint8_t dir, uint16_t dato) {
  SPI.beginTransaction(ajuste);
  digitalWrite(pin::MEAS_CS, LOW);
  delayMicroseconds(10);
  SPI.transfer((uint8_t)((lectura ? 0x80 : 0x00) | (dir & 0x7F)));
  delayMicroseconds(5);
  uint16_t r = dato;
  if (lectura) {
    uint8_t hi = SPI.transfer(0);
    uint8_t lo = SPI.transfer(0);
    r = (uint16_t)((hi << 8) | lo);
  } else {
    SPI.transfer((uint8_t)(dato >> 8));
    SPI.transfer((uint8_t)dato);
  }
  delayMicroseconds(5);
  digitalWrite(pin::MEAS_CS, HIGH);
  SPI.endTransaction();
  delayMicroseconds(10);
  return r;
}

uint16_t leer(uint8_t dir) { return trama(true, dir, 0); }
void escribir(uint8_t dir, uint16_t v) { trama(false, dir, v); }

// CS1/CS2: byte bajo = suma de todos los bytes mod 256; byte alto = XOR de todos los bytes.
uint16_t checksum(const uint16_t *regs, int n) {
  uint8_t suma = 0, x = 0;
  for (int k = 0; k < n; k++) {
    uint8_t h = regs[k] >> 8, l = regs[k] & 0xFF;
    suma += h;
    suma += l;
    x ^= h;
    x ^= l;
  }
  return (uint16_t)((x << 8) | suma);
}

bool spiOk() {
  uint16_t a = leer(CALSTART);
  uint16_t b = leer(LASTDATA);
  return a == b && a != 0xFFFF;
}

bool configurar(const Calibracion &c, uint16_t vnom) {
  escribir(SOFTRESET, 0x789A);
  delay(50);
  if (leer(CALSTART) != 0x6886) return false;  // no contesta

  // Aviso de sag solo por IRQ (SagEn); WarnOut queda solo para CalErr. Sin avisos de cambio de sentido.
  escribir(FUNCEN, 0x0020);
  // Umbral de sag (fórmula del datasheet): Vth × 100 × √2 / (4 × Ugain / 32768), con Vth = 70 % de la nominal.
  float vth = vnom * RED_BAJA_FRACCION;
  float sag = vth * 100.0f * 1.41421356f / (4.0f * c.ugain / 32768.0f);
  if (sag > 65535) sag = 65535;
  escribir(SAGTH, (uint16_t)sag);

  // Metering: 5678H, registros 21H–2BH, CS1 y 8765H.
  const uint16_t met[11] = {c.plconst_h, c.plconst_l, c.lgain, c.lphi, c.ngain, c.nphi,
                            c.pstart,    c.pnol,      c.qstart, c.qnol, c.mmode};
  escribir(CALSTART, 0x5678);
  for (int k = 0; k < 11; k++) escribir(0x21 + k, met[k]);
  escribir(CS1, checksum(met, 11));
  escribir(CALSTART, 0x8765);

  // Measurement: 5678H, registros 31H–3AH, CS2 y 8765H.
  const uint16_t mea[10] = {c.ugain,     c.igain_l,   c.igain_n,   c.uoffset,   c.ioffset_l,
                            c.ioffset_n, c.poffset_l, c.qoffset_l, c.poffset_n, c.qoffset_n};
  escribir(ADJSTART, 0x5678);
  for (int k = 0; k < 10; k++) escribir(0x31 + k, mea[k]);
  escribir(CS2, checksum(mea, 10));
  escribir(ADJSTART, 0x8765);

  delay(20);
  uint16_t st = leer(SYSSTATUS);
  return (st & (SYS_CALERR | SYS_ADJERR)) == 0 && leer(CALSTART) == 0x8765 && leer(ADJSTART) == 0x8765;
}

static float signoMagnitud(uint16_t raw, float escala) {
  float v = (raw & 0x7FFF) * escala;
  return (raw & 0x8000) ? -v : v;
}

bool medir(MedicionAtm &m) {
  uint16_t u = leer(URMS);
  if (leer(LASTDATA) != u) return false;  // el SPI no responde bien
  m.v = u / 100.0f;
  m.i = leer(IRMS2) / 1000.0f;
  m.p = (int16_t)leer(PMEAN2) * 1.0f;   // complemento a 2, XX.XXX kW → 1 LSB = 1 W
  m.q = (int16_t)leer(QMEAN2) * 1.0f;
  m.s = (leer(SMEAN2) & 0x7FFF) * 1.0f;
  m.pf = signoMagnitud(leer(POWERF2), 0.001f);
  m.f = leer(FREQ) / 100.0f;
  m.sys = leer(SYSSTATUS);
  return true;
}

}  // namespace atm
