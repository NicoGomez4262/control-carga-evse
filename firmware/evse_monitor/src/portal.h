// Portal de configuración (punto de acceso «EVSE-XXXX» con clave): WiFi, servidor, id y token.
// Se abre si se mantiene PARAR 5 s al encender o con «portal» en la consola (no solo: sin U1 el WiFi
// supera el límite de la fuente de banco).
// La tarea de control sigue funcionando mientras el portal está abierto.
#pragma once
#include <Arduino.h>

namespace portal {
void begin();
void loop();
bool activo();
void pedirAlReiniciar();   // la consola lo usa: el próximo arranque abre el portal
bool pedidoAlReiniciar();  // lo consume
}  // namespace portal
