#include "consola.h"
#include <Arduino.h>
#include <WiFi.h>
#include "almacen.h"
#include "config.h"
#include "control.h"
#include "portal.h"
#include "red.h"
#include "tipos.h"

namespace consola {

static String buf;

void ayuda() {
  Serial.println();
  Serial.println("=== EVSE Monitor " FW_VERSION " · consola ===");
  Serial.println("  estado                    medición, K1, motivo, alarmas, sesión y energía");
  Serial.println("  red                       WiFi, Firebase, equipo y registros sin subir");
  Serial.println("  wifi RED CLAVE            guarda el WiFi (si la red tiene espacios: wifi \"Mi red\" clave)");
  Serial.println("  enlazar CODIGO            pega el código de enlace de la app (empieza por EVSE1.)");
  Serial.println("  borrar_red                borra el WiFi y el enlace de la NVS");
  Serial.println("  portal                    reinicia y abre el portal de configuración");
  Serial.println("  permitir | detener        permiso de carga (como desde la app)");
  Serial.println("  reconocer                 reconoce las alarmas");
  Serial.println("  soltar_parar              libera PARAR (también: mantener PARAR 3 s)");
  Serial.println("  cal                       calibración guardada y registros del ATM90E26");
  Serial.println("  cal_auto V I              calibra Ugain con V voltios e IgainN con I amperios de referencia (0 = no)");
  Serial.println("  cal_fabrica               vuelve a los valores de fábrica del ATM90E26");
  Serial.println("  sonda 0|1                 sonda DS18B20 obligatoria o no (para el banco sin sonda)");
  Serial.println("  tension 120|240           tensión nominal");
  Serial.println("  buffer                    estado del búfer de registros en la flash");
  Serial.println("  reiniciar | version | ayuda");
  Serial.println();
}

static void estado() {
  Instantanea s;
  control::instantanea(s);
  Serial.printf("Hora: %s (epoch %lu) · uptime %lu s\n", s.hora_ok ? "válida" : "SIN HORA", (unsigned long)s.ts,
                (unsigned long)s.uptime_s);
  if (s.med_ok)
    Serial.printf("Medición: %.2f V · %.3f A · %.0f W · FP %.3f · %.2f Hz · SysStatus %04X\n", s.v, s.i, s.p, s.pf, s.f,
                  s.sys_status);
  else
    Serial.println("Medición: sin lectura válida del ATM90E26");
  Serial.printf("Sonda: %s · Ambiente: %s\n", s.sonda_ok ? String(s.t_sonda, 1).c_str() : "sin lectura",
                s.amb_ok ? (String(s.t_amb, 1) + " °C, " + String(s.hum, 0) + " %HR").c_str() : "sin lectura");
  Serial.printf("K1: %s · permiso de la app: %s · motivo: %s\n", s.k1 ? "CERRADO (carga permitida)" : "abierto",
                s.permiso ? "sí" : "no", s.motivo ? motivoTexto(s.motivo) : "—");
  Serial.printf("Sesión: %s · %.3f kWh · %lu s · energía total %.3f kWh\n",
                s.ses_num ? String(s.ses_num).c_str() : "ninguna", s.e_ses_kwh, (unsigned long)s.ses_dur_s, s.e_tot_kwh);
  Serial.print("Alarmas:");
  if (!s.alarmas) Serial.print(" ninguna");
  for (int b = 0; b < N_ALARMAS; b++)
    if (s.alarmas >> b & 1) Serial.printf(" [%s%s]", alarmaTexto(b), (s.sin_reconocer >> b & 1) ? " *" : "");
  Serial.println();
}

static void ordenLocal(uint8_t tipo, float a = 0, float b = 0) {
  Orden o;
  memset(&o, 0, sizeof(o));
  o.tipo = tipo;
  o.a = a;
  o.b = b;
  control::enviarOrden(o);
}

static void cal() {
  Calibracion c;
  control::calActual(c);
  Serial.printf("Calibración guardada (%s):\n", c.calibrada ? "calibrada" : "SIN CALIBRAR, valores de fábrica");
  Serial.printf("  Ugain %04X · IgainN %04X · Uoffset %04X · IoffsetN %04X · PoffsetN %04X\n", c.ugain, c.igain_n,
                c.uoffset, c.ioffset_n, c.poffset_n);
  Serial.printf("  PLconst %04X%04X · Ngain %04X · Nphi %04X · PStartTh %04X · MMode %04X\n", c.plconst_h, c.plconst_l,
                c.ngain, c.nphi, c.pstart, c.mmode);
  static const uint8_t dirs[] = {0x01, 0x20, 0x30, 0x2B, 0x31, 0x33};
  uint16_t v[6];
  control::registrosAtm(v, dirs, 6);
  Serial.printf("En el chip: SysStatus %04X · CalStart %04X · AdjStart %04X · MMode %04X · Ugain %04X · IgainN %04X\n",
                v[0], v[1], v[2], v[3], v[4], v[5]);
}

// Separa el primer argumento (admite comillas) del resto.
static String primero(String &resto) {
  resto.trim();
  String a;
  if (resto.startsWith("\"")) {
    int fin = resto.indexOf('"', 1);
    if (fin < 0) fin = resto.length();
    a = resto.substring(1, fin);
    resto = fin < (int)resto.length() ? resto.substring(fin + 1) : "";
  } else {
    int sp = resto.indexOf(' ');
    a = sp < 0 ? resto : resto.substring(0, sp);
    resto = sp < 0 ? "" : resto.substring(sp + 1);
  }
  resto.trim();
  return a;
}

static void cambiarConfig(void (*f)(Config &)) {
  Config c;
  almacen::configLeer(c);
  f(c);
  c.version++;  // la app ve el cambio como una versión nueva
  almacen::configGuardar(c);
  ordenLocal(O_CONFIG);
  red::recargarConfig();
}

static int argEntero = 0;

static void ejecutar(String linea) {
  String resto = linea;
  String cmd = primero(resto);
  cmd.toLowerCase();
  almacen::Red r;
  if (cmd == "ayuda" || cmd == "?") ayuda();
  else if (cmd == "estado" || cmd == "e") estado();
  else if (cmd == "red") Serial.println(red::resumen());
  else if (cmd == "version") Serial.println(FW_NOMBRE " " FW_VERSION " (" __DATE__ " " __TIME__ ")");
  else if (cmd == "wifi") {
    almacen::redLeer(r);
    r.ssid = primero(resto);
    r.clave = resto;
    almacen::redGuardar(r);
    Serial.printf("WiFi guardado: «%s». Escribe «reiniciar» para usarlo.\n", r.ssid.c_str());
  } else if (cmd == "enlazar") {
    almacen::redLeer(r);
    if (almacen::enlaceLeer(primero(resto), r)) {
      almacen::redGuardar(r);
      Serial.printf("Enlace guardado: cuenta %s en %s. Escribe «reiniciar» para usarlo.\n", r.correo.c_str(),
                    r.db.c_str());
    } else {
      Serial.println("Código inválido. Cópialo completo desde la app (Ajustes → Enlace del equipo); empieza por EVSE1.");
    }
  } else if (cmd == "borrar_red") {
    almacen::redBorrar();
    Serial.println("WiFi y enlace borrados de la NVS (quedan los valores de secrets.h, si hay).");
  } else if (cmd == "portal") {
    portal::pedirAlReiniciar();
    Serial.println("Reiniciando en modo portal…");
    delay(300);
    ESP.restart();
  } else if (cmd == "permitir") ordenLocal(O_PERMITIR);
  else if (cmd == "detener") ordenLocal(O_DETENER);
  else if (cmd == "reconocer") ordenLocal(O_RECONOCER);
  else if (cmd == "soltar_parar") ordenLocal(O_PARAR_SOLTAR);
  else if (cmd == "cal") cal();
  else if (cmd == "cal_auto") {
    float v = primero(resto).toFloat();
    float i = primero(resto).toFloat();
    if (v <= 0 && i <= 0)
      Serial.println("Uso: cal_auto 120.3 9.87   (tensión y corriente de referencia; 0 para no tocar una)");
    else
      ordenLocal(O_CAL_AUTO, v, i);
  } else if (cmd == "cal_fabrica") ordenLocal(O_CAL_FABRICA);
  else if (cmd == "sonda") {
    argEntero = primero(resto).toInt();
    cambiarConfig([](Config &c) { c.sonda_req = argEntero != 0; });
    Serial.printf("Sonda %s.\n", argEntero ? "obligatoria" : "opcional");
  } else if (cmd == "tension") {
    argEntero = primero(resto).toInt();
    if (argEntero != 120 && argEntero != 240) {
      Serial.println("Uso: tension 120  |  tension 240");
    } else {
      cambiarConfig([](Config &c) { c.vnom = (uint16_t)argEntero; });
      Serial.printf("Tensión nominal: %d V.\n", argEntero);
    }
  } else if (cmd == "buffer") {
    Serial.printf("Búfer: registros %lu a %lu (caben %lu, 64 bytes cada uno)\n", (unsigned long)buffer::seqMin(),
                  (unsigned long)buffer::seqMax(), (unsigned long)buffer::capacidad());
  } else if (cmd == "reiniciar") {
    Serial.println("Reiniciando…");
    delay(200);
    ESP.restart();
  } else {
    Serial.println("Comando desconocido. Escribe «ayuda».");
  }
}

void loop() {
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\r' || c == '\n') {
      if (buf.length()) {
        Serial.println();
        String l = buf;
        buf = "";
        l.trim();
        ejecutar(l);
        Serial.print("> ");
      }
    } else if (c == 8 || c == 127) {
      if (buf.length()) {
        buf.remove(buf.length() - 1);
        Serial.print("\b \b");
      }
    } else if (buf.length() < 480) {
      buf += c;
      Serial.print(c);
    }
  }
}

}  // namespace consola
