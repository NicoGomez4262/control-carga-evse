// Persistencia: NVS (configuración, calibración, energía, estado de K1) y búfer circular de
// registros en la partición «buffer» de la flash de 16 MB (D14).
#pragma once
#include <Arduino.h>
#include "tipos.h"

namespace almacen {

// WiFi y enlace con Firebase (D31). El «código de enlace» de la app trae db, apikey, correo y pass.
struct Red {
  String ssid, clave;
  String db;      // URL de la Realtime Database, p. ej. https://evse-monitor-default-rtdb.firebaseio.com
  String apikey;  // API key web del proyecto (es pública: identifica el proyecto, no da permisos)
  String correo;  // cuenta del equipo en Firebase Authentication
  String pass;    // clave de esa cuenta
};

// «EVSE1.<base64url de {"d":db,"k":apikey,"e":correo,"c":pass}>» → campos de `r` (no toca el WiFi).
bool enlaceLeer(const String &codigo, Red &r);

// Lo que tiene que sobrevivir a un corte de energía (se guarda cada minuto y en cada cambio).
struct Persistente {
  uint32_t magia;
  bool permiso;          // lo que pidió el usuario (P3)
  bool parar;            // PARAR enclavado
  bool limite;           // límite de sesión alcanzado (espera «permitir»)
  double e_tot_kwh;
  float e_ses_kwh;
  uint32_t ses_num;      // 0 = sin sesión abierta
  uint32_t ses_ini;      // epoch de inicio
  uint32_t ses_dur_s;
  uint32_t ses_contador; // último número de sesión usado
  float p_max;
  uint8_t temp_disparos;
};

void begin();

void redLeer(Red &r);  // NVS y, si falta algo, secrets.h
void redGuardar(const Red &r);
void redBorrar();

void configLeer(Config &c);
void configGuardar(const Config &c);
void calLeer(Calibracion &c);
void calGuardar(const Calibracion &c);
void estadoLeer(Persistente &p);
void estadoGuardar(const Persistente &p);

// OTA: 0 = nada, 1 = firmware nuevo sin confirmar.
uint8_t otaPendiente();
void otaMarcar(uint8_t v);
uint8_t arranquesOta();       // arranques desde que se instaló el firmware nuevo
void arranquesOtaSumar();
void otaVersion(const String &ver);  // versión que se está instalando
String otaVersion();
void otaMala(const String &ver);     // versión que no arrancó bien (no se vuelve a intentar)
String otaMala();

}  // namespace almacen

namespace buffer {
bool begin();                         // busca la partición y el último registro
uint32_t escribir(Registro &r);       // asigna seq y CRC; devuelve seq (0 si falla)
bool leer(uint32_t seq, Registro &r); // false si no existe o el CRC no coincide
uint32_t seqMin();                    // registro más viejo que queda
uint32_t seqMax();                    // último escrito (0 = vacío)
uint32_t capacidad();
}  // namespace buffer
