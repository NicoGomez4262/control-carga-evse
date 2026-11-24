// Red: WiFi (TX ≤ 17 dBm), hora por NTP y Firebase (D31): flujo de /entrada/{id} para órdenes y
// configuración, telemetría en /estado, subida del búfer, OTA y avisos por Telegram.
// Corre en la tarea de Arduino (loop); la tarea de control no depende de esto.
#pragma once
#include <Arduino.h>

namespace red {
void begin();
void loop();
bool enLinea();
void recargarConfig();  // después de cambiar la configuración por la consola
String resumen();  // una línea para la consola
}  // namespace red
