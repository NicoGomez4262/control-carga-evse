// AHT20 (ambiente, I²C 0x38), DS3231 (RTC, I²C 0x68) y DS18B20 (sonda, 1-Wire en IO4).
#pragma once
#include <Arduino.h>

namespace sensores {
void begin();

// AHT20: dispara una medición y la lee 80 ms después (no bloquea).
void ahtDisparar();
bool ahtLeer(float &t, float &h);  // true si hay una lectura nueva y válida

// DS18B20: busca la sonda, dispara la conversión y la lee 750 ms después (no bloquea).
bool sondaPresente();
void sondaDisparar();
bool sondaLeer(float &t);  // true si la lectura es válida (CRC bien)

// DS3231 en UTC.
bool rtcLeer(uint32_t &epoch, bool &osf);
bool rtcEscribir(uint32_t epoch);
bool rtcPresente();

// Utilidades de fecha (UTC).
uint32_t epochDesdeCivil(int y, int mo, int d, int h, int mi, int s);
void civilDesdeEpoch(uint32_t t, int &y, int &mo, int &d, int &h, int &mi, int &s, int &dow);
}  // namespace sensores
