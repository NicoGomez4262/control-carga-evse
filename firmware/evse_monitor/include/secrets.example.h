// Copia este archivo como «secrets.h» (está en .gitignore) y llénalo.
// Todo es opcional: si un valor queda vacío, se configura por el portal (PARAR 5 s al encender)
// o por la consola serie («wifi», «servidor», «equipo»). Lo que se guarde por esas vías en la NVS
// tiene prioridad sobre este archivo.
//
// OJO: lo que pongas aquí queda dentro del .bin. El .bin para OTA se sube a la app (es privado),
// pero no lo publiques en GitHub.
#pragma once

#define SECRETO_WIFI_SSID ""
#define SECRETO_WIFI_CLAVE ""

// Servidor de la app, sin «https://» (por ejemplo «evse.nicolasgomez.dev» o «evse-monitor.TU-CUENTA.workers.dev»).
#define SECRETO_SERVIDOR ""

// Identificador y token del equipo: salen en la app al registrar el equipo (Equipos → Agregar).
#define SECRETO_EQUIPO_ID ""
#define SECRETO_EQUIPO_TOKEN ""

// Clave de la red WiFi del portal de configuración (mínimo 8 caracteres).
#define SECRETO_PORTAL_CLAVE "configurar-evse"
