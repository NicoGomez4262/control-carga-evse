// Cliente mínimo de Firebase para el ESP32 (D31): Authentication (correo y clave del equipo) y Realtime
// Database por REST, con TLS verificado (ca_raiz.h).
//   · pedir(): GET, PUT, PATCH y DELETE sobre una conexión que se reutiliza (keep-alive).
//   · flujo: una segunda conexión que queda abierta escuchando una ruta (Server-Sent Events): llegan
//     «put» y «patch» al instante cuando la app escribe ahí.
// Todo es bloqueante y corre en la tarea de red; la de control no depende de esto.
#pragma once
#include <Arduino.h>

namespace fb {

struct Evento {
  String tipo;   // «put» o «patch»
  String datos;  // JSON {"path": "/…", "data": …}
};

void configurar(const String &db, const String &apikey, const String &correo, const String &pass);
bool configurado();

bool entrar();             // inicia sesión (bloquea hasta ~15 s); true si quedó con token
bool conSesion();          // hay token y no está por vencer
void olvidarSesion();      // el servidor rechazó el token: se vuelve a entrar
const String &uid();
uint32_t horaServidor();   // epoch UTC según la cabecera Date del último inicio de sesión (0 si no hay)

// Devuelve el código HTTP (200 = bien; < 0 = error de conexión). `ruta` sin «/» inicial ni «.json»;
// "" es la raíz (para escribir varias rutas a la vez con PATCH).
int pedir(const char *metodo, const String &ruta, const String &cuerpo = "", String *respuesta = nullptr,
          uint32_t espera_ms = 10000);

bool flujoAbrir(const String &ruta);
void flujoCerrar();
bool flujoActivo();
bool flujoLeer(Evento &e);   // no bloquea: true cuando hay un evento completo
uint32_t flujoUltimo();      // millis() del último dato recibido (incluye «keep-alive»)
bool flujoRevocado();        // llegó «auth_revoked» o «cancel»: hay que volver a entrar

String error();              // último error, para la consola
String host();

}  // namespace fb
