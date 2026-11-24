// Tarea de control: medición, energía, sesiones, protecciones locales, K1, LEDs y PARAR.
// Corre sola, con más prioridad que la red: las protecciones funcionan sin internet.
#pragma once
#include <Arduino.h>
#include "tipos.h"

namespace control {

// Estado de la conexión, para el LED3 (lo pone la tarea de red).
enum EstadoRed : uint8_t { RED_NADA = 0, RED_WIFI = 1, RED_SERVIDOR = 2, RED_PORTAL = 3 };

void begin(esp_reset_reason_t motivoReset);
void instantanea(Instantanea &s);
void configActual(Config &c);
void calActual(Calibracion &c);
bool enviarOrden(const Orden &o);
bool respuesta(Respuesta &r);       // no bloquea
void ponerEstadoRed(EstadoRed e);
void horaSincronizada();            // la red avisa que el NTP puso la hora (se copia al DS3231)
uint32_t ahora();                   // epoch UTC, 0 si no hay hora válida
// Último registro de medición del ATM90E26 (para «cal_leer»).
void registrosAtm(uint16_t *out, const uint8_t *dirs, int n);

}  // namespace control
