#include "portal.h"
#include <DNSServer.h>
#include <WebServer.h>
#include <WiFi.h>
#include "almacen.h"
#include "config.h"
#include "control.h"
#include "red.h"
#include "secretos.h"

namespace portal {

RTC_NOINIT_ATTR static uint32_t rtcPedido;
static constexpr uint32_t PEDIDO = 0x504F5254;  // «PORT»

static bool abierto = false;
static uint32_t t0 = 0;
static DNSServer dns;
static WebServer srv(80);
static char nombreAp[16];

static String escapar(const String &s) {
  String o;
  for (char c : s) {
    if (c == '<') o += "&lt;";
    else if (c == '>') o += "&gt;";
    else if (c == '"') o += "&quot;";
    else if (c == '&') o += "&amp;";
    else o += c;
  }
  return o;
}

static const char ESTILO[] PROGMEM =
    "<meta name=viewport content='width=device-width,initial-scale=1'><style>"
    "body{font-family:system-ui,sans-serif;max-width:28rem;margin:1rem auto;padding:0 1rem;color:#1d2433}"
    "h1{font-size:1.3rem}label{display:block;margin:.8rem 0 .2rem;font-weight:600}"
    "input,select{width:100%;padding:.6rem;font-size:1rem;box-sizing:border-box;border:1px solid #b8c0cc;border-radius:.4rem}"
    "button{margin-top:1.2rem;width:100%;padding:.8rem;font-size:1rem;background:#1f6feb;color:#fff;border:0;border-radius:.4rem}"
    "small{color:#5b6475}</style>";

static void pagina() {
  almacen::Red r;
  almacen::redLeer(r);
  int n = WiFi.scanNetworks();
  String html = "<!doctype html><html lang=es><head><meta charset=utf-8><title>EVSE Monitor</title>";
  html += FPSTR(ESTILO);
  html += "</head><body><h1>EVSE Monitor · configuración</h1>";
  html += "<p><small>Equipo " + escapar(String(nombreAp)) + " · firmware " FW_VERSION "</small></p>";
  html += "<form method=post action=/guardar>";
  html += "<label>Red WiFi</label><input name=ssid list=redes value=\"" + escapar(r.ssid) + "\" required><datalist id=redes>";
  for (int k = 0; k < n; k++) html += "<option value=\"" + escapar(WiFi.SSID(k)) + "\">" + String(WiFi.RSSI(k)) + " dBm</option>";
  html += "</datalist>";
  html += "<label>Clave del WiFi</label><input name=clave type=password placeholder='(sin cambio)'>";
  html += "<label>Servidor</label><input name=servidor value=\"" + escapar(r.servidor) +
          "\" placeholder='evse.ejemplo.com'><small>Sin https://. Para pruebas sin TLS: ws://IP:8787</small>";
  html += "<label>Id del equipo</label><input name=id value=\"" + escapar(r.id) + "\">";
  html += "<label>Token del equipo</label><input name=token type=password placeholder='(sin cambio)'>";
  html += "<small>El id y el token salen en la app, en Equipos → Agregar equipo.</small>";
  html += "<button>Guardar y reiniciar</button></form></body></html>";
  WiFi.scanDelete();
  srv.send(200, "text/html; charset=utf-8", html);
}

static void guardar() {
  almacen::Red r;
  almacen::redLeer(r);
  r.ssid = srv.arg("ssid");
  if (srv.arg("clave").length()) r.clave = srv.arg("clave");
  r.servidor = srv.arg("servidor");
  r.id = srv.arg("id");
  if (srv.arg("token").length()) r.token = srv.arg("token");
  r.ssid.trim();
  r.servidor.trim();
  r.id.trim();
  almacen::redGuardar(r);
  String html = "<!doctype html><html lang=es><head><meta charset=utf-8>";
  html += FPSTR(ESTILO);
  html += "</head><body><h1>Guardado</h1><p>El equipo se reinicia y se conecta a «" + escapar(r.ssid) +
          "». El LED3 queda fijo cuando llega al servidor.</p></body></html>";
  srv.send(200, "text/html; charset=utf-8", html);
  delay(1500);
  ESP.restart();
}

static void redirigir() {
  srv.sendHeader("Location", "http://192.168.4.1/", true);
  srv.send(302, "text/plain", "");
}

void begin() {
  abierto = true;
  t0 = millis();
  control::ponerEstadoRed(control::RED_PORTAL);
  uint8_t mac[6];
  WiFi.mode(WIFI_AP_STA);
  WiFi.macAddress(mac);
  snprintf(nombreAp, sizeof(nombreAp), "EVSE-%02X%02X", mac[4], mac[5]);
  WiFi.softAP(nombreAp, SECRETO_PORTAL_CLAVE);
  WiFi.setTxPower(WIFI_POWER_17dBm);
  delay(100);
  dns.start(53, "*", WiFi.softAPIP());
  srv.on("/", HTTP_GET, pagina);
  srv.on("/guardar", HTTP_POST, guardar);
  srv.onNotFound(redirigir);
  srv.begin();
  Serial.printf("[portal] abierto: red «%s», clave «%s», entra a http://192.168.4.1 (se cierra en 10 min)\n", nombreAp,
                SECRETO_PORTAL_CLAVE);
}

void loop() {
  if (!abierto) return;
  dns.processNextRequest();
  srv.handleClient();
  if (millis() - t0 > PORTAL_DURACION_MS) {
    Serial.println("[portal] cerrado por tiempo; sigue con la configuración que haya");
    srv.stop();
    dns.stop();
    WiFi.softAPdisconnect(true);
    abierto = false;
    red::begin();
  }
}

bool activo() { return abierto; }
void pedirAlReiniciar() { rtcPedido = PEDIDO; }
bool pedidoAlReiniciar() {
  bool p = rtcPedido == PEDIDO;
  rtcPedido = 0;
  return p;
}

}  // namespace portal
