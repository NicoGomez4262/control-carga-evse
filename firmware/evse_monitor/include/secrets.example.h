// Copia este archivo como «secrets.h» (está en .gitignore) y llénalo.
// Todo es opcional: si un valor queda vacío, se configura por la consola serie («wifi», «enlazar») o por
// el portal (PARAR 5 s al encender). Lo que se guarde por esas vías en la NVS tiene prioridad.
//
// OJO: lo que pongas aquí queda dentro del .bin. Si lo usas, no subas ese .bin a GitHub ni lo compartas.
#pragma once

#define SECRETO_WIFI_SSID ""
#define SECRETO_WIFI_CLAVE ""

// Código de enlace del equipo: sale en la app (Equipo → Ajustes → Enlace del equipo). Empieza por «EVSE1.».
// Trae la base de datos de Firebase, la API key del proyecto y la cuenta del equipo.
#define SECRETO_ENLACE ""

// Clave de la red WiFi del portal de configuración (mínimo 8 caracteres).
#define SECRETO_PORTAL_CLAVE "configurar-evse"
