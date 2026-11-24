// Driver del ATM90E26 (U3) por SPI de 4 hilos, modo 3, 100 kHz.
// El CT entra por I2 (línea N): MMode con LNSel = 0 y registros «2» (Irms2, Pmean2, PowerF2).
#pragma once
#include <Arduino.h>
#include "tipos.h"

struct MedicionAtm {
  float v;      // Urms (V)
  float i;      // Irms2 (A)
  float p;      // Pmean2 (W), con signo
  float q;      // Qmean2 (var)
  float s;      // Smean2 (VA)
  float pf;     // PowerF2
  float f;      // Freq (Hz)
  uint16_t sys; // SysStatus
};

namespace atm {
constexpr uint8_t SOFTRESET = 0x00, SYSSTATUS = 0x01, FUNCEN = 0x02, SAGTH = 0x03, LASTDATA = 0x06;
constexpr uint8_t CALSTART = 0x20, CS1 = 0x2C, ADJSTART = 0x30, CS2 = 0x3B;
constexpr uint8_t URMS = 0x49, FREQ = 0x4C, IRMS2 = 0x68, PMEAN2 = 0x6A, QMEAN2 = 0x6B, POWERF2 = 0x6D, SMEAN2 = 0x6F;
constexpr uint16_t SYS_CALERR = 0xC000, SYS_ADJERR = 0x3000, SYS_SAG = 0x0002;

void begin();
uint16_t leer(uint8_t dir);
void escribir(uint8_t dir, uint16_t v);
// Escribe la calibración, calcula CS1 y CS2 y arranca en modo verificado (8765H).
// Devuelve false si el chip no contesta o queda con CalErr/AdjErr.
bool configurar(const Calibracion &c, uint16_t vnom);
// Lee U, I2, P2, Q2, S2, FP2, f y SysStatus. Devuelve false si el SPI no responde.
bool medir(MedicionAtm &m);
// Comprueba el SPI con LastData.
bool spiOk();
uint16_t checksum(const uint16_t *regs, int n);
}  // namespace atm
