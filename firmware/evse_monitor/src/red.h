// Red: WiFi (TX ≤ 17 dBm), hora por NTP, WebSocket saliente con TLS hacia la app (D8),
// subida del búfer, órdenes, configuración y OTA. Corre en la tarea de Arduino (loop).
#pragma once
#include <Arduino.h>

namespace red {
void begin();
void loop();
bool enLinea();
void recargarConfig();  // después de cambiar la configuración por la consola
String resumen();  // una línea para la consola
}  // namespace red
