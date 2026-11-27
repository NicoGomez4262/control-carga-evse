#include "fb.h"
#include <ArduinoJson.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>
#include <esp_attr.h>
#include <esp_task_wdt.h>
#include "ca_raiz.h"
#include "config.h"
#include "sensores.h"

namespace fb {

// Marca «esperando a la red» en la RAM del RTC: si el watchdog reinicia la placa en medio de una espera larga,
// al arrancar se sabe que fue la red y no una falla del control (las protecciones van en otra tarea).
static constexpr uint32_t OCUPADA = 0x4E45540Au;
RTC_NOINIT_ATTR static uint32_t rtcRedOcupada;
static const bool ocupadaAlArrancar = rtcRedOcupada == OCUPADA;
bool redOcupadaAlReiniciar() { return ocupadaAlArrancar; }
struct EnRed {
  EnRed() {
    esp_task_wdt_reset();
    rtcRedOcupada = OCUPADA;
  }
  ~EnRed() {
    rtcRedOcupada = 0;
    esp_task_wdt_reset();
  }
};

static String dbHost, apiKey, correo, pass;
static String token, miUid, ultError;
static bool hayToken = false;
static uint32_t tokenVence = 0;  // millis()
static uint32_t horaEpoch = 0, horaMs = 0;

// ------------------------------------------------------------------ conexión de datos (keep-alive)
static WiFiClientSecure cliDatos;
static HTTPClient http;
static bool datosListo = false;

// ------------------------------------------------------------------ conexión del flujo (SSE)
static WiFiClientSecure cliFlujo;
static bool flujoOn = false, revocado = false, chunked = false;
static uint32_t ultimoDato = 0;
static String linea, evTipo, evDatos;
static uint8_t chunkEstado = 0;  // 0 tamaño · 1 datos · 2 CRLF del final del trozo · 3 terminó
static int32_t chunkRestante = 0;
static String chunkTam;
static uint8_t rbuf[512];
static int rlen = 0, rpos = 0;

void configurar(const String &db, const String &k, const String &c, const String &p) {
  String h = db;
  h.trim();
  if (h.startsWith("https://")) h = h.substring(8);
  int b = h.indexOf('/');
  if (b >= 0) h = h.substring(0, b);
  dbHost = h;
  apiKey = k;
  correo = c;
  pass = p;
  hayToken = false;
}

bool configurado() { return dbHost.length() && apiKey.length() && correo.length() && pass.length(); }
const String &uid() { return miUid; }
String error() { return ultError; }
String host() { return dbHost; }
void olvidarSesion() { hayToken = false; }
bool conSesion() { return hayToken && (int32_t)(millis() - tokenVence) < 0; }
uint32_t horaServidor() { return horaEpoch ? horaEpoch + (millis() - horaMs) / 1000 : 0; }

// «Tue, 24 Nov 2026 15:04:05 GMT» → epoch UTC.
static uint32_t fechaHttp(const String &s) {
  char mes[4] = {0};
  int d, y, h, mi, se;
  if (sscanf(s.c_str(), "%*[^,], %d %3s %d %d:%d:%d", &d, mes, &y, &h, &mi, &se) != 6) return 0;
  static const char *M = "JanFebMarAprMayJunJulAugSepOctNovDec";
  const char *p = strstr(M, mes);
  if (!p || y < 2024) return 0;
  return sensores::epochDesdeCivil(y, (int)(p - M) / 3 + 1, d, h, mi, se);
}

bool entrar() {
  hayToken = false;
  if (!configurado()) {
    ultError = "falta el enlace con Firebase («enlazar» en la consola)";
    return false;
  }
  EnRed enRed;
  WiFiClientSecure c;
  c.setCACert(CA_RAIZ);
  c.setTimeout(15);
  c.setHandshakeTimeout(10);
  HTTPClient h;
  if (!h.begin(c, String(FB_LOGIN) + apiKey)) {
    ultError = "URL de inicio de sesión inválida";
    return false;
  }
  h.setTimeout(15000);
  h.setConnectTimeout(10000);
  h.addHeader("Content-Type", "application/json");
  const char *cabeceras[] = {"Date"};
  h.collectHeaders(cabeceras, 1);
  JsonDocument q;
  q["email"] = correo;
  q["password"] = pass;
  q["returnSecureToken"] = true;
  String cuerpo;
  serializeJson(q, cuerpo);
  int codigo = h.POST(cuerpo);
  String resp = codigo > 0 ? h.getString() : String();
  uint32_t t = fechaHttp(h.header("Date"));
  if (t) {
    horaEpoch = t;
    horaMs = millis();
  }
  h.end();
  if (codigo != 200) {
    String msg;
    JsonDocument e;
    if (codigo > 0 && !deserializeJson(e, resp)) msg = e["error"]["message"] | "";
    if (!msg.length()) msg = codigo > 0 ? String("HTTP ") + codigo : HTTPClient::errorToString(codigo);
    ultError = "inicio de sesión: " + msg;
    return false;
  }
  JsonDocument d;
  if (deserializeJson(d, resp)) {
    ultError = "inicio de sesión: respuesta ilegible";
    return false;
  }
  token = d["idToken"] | "";
  miUid = d["localId"] | "";
  long dura = String(d["expiresIn"] | "3600").toInt();
  if (dura < 600) dura = 600;
  tokenVence = millis() + (uint32_t)(dura - FB_TOKEN_RENOVAR_S) * 1000UL;
  hayToken = token.length() > 0 && miUid.length() > 0;
  if (!hayToken) ultError = "inicio de sesión: sin token";
  return hayToken;
}

int pedir(const char *metodo, const String &ruta, const String &cuerpo, String *respuesta, uint32_t espera_ms) {
  if (!hayToken) {
    ultError = "sin sesión";
    return -100;
  }
  if (!datosListo) {
    cliDatos.setCACert(CA_RAIZ);
    datosListo = true;
  }
  String url = "https://" + dbHost + "/" + ruta + ".json?auth=" + token;
  int codigo = 0;
  String r;
  EnRed enRed;
  for (int intento = 0; intento < 2; intento++) {
    esp_task_wdt_reset();  // cada intento tiene su propio plazo: el watchdog no debe sumar los dos
    cliDatos.setTimeout((espera_ms + 999) / 1000);
    cliDatos.setHandshakeTimeout(10);
    http.setReuse(true);
    if (!http.begin(cliDatos, url)) {
      ultError = "URL inválida";
      return -101;
    }
    http.setTimeout(espera_ms);
    http.setConnectTimeout(10000);
    bool get = strcmp(metodo, "GET") == 0;
    if (!get) http.addHeader("Content-Type", "application/json");
    codigo = get ? http.GET() : http.sendRequest(metodo, cuerpo);
    r = codigo > 0 ? http.getString() : String();
    http.end();
    if (codigo > 0) break;
    cliDatos.stop();  // la conexión reutilizada estaba muerta: una nueva y otra vez
  }
  if (respuesta) *respuesta = r;
  if (codigo == 401) {
    hayToken = false;
    ultError = "el servidor rechazó el token";
  } else if (codigo != 200) {
    ultError = String(metodo) + " /" + ruta + ": " +
               (codigo > 0 ? String("HTTP ") + codigo + " " + r.substring(0, 80) : HTTPClient::errorToString(codigo));
  }
  return codigo;
}

// ------------------------------------------------------------------ flujo (Server-Sent Events)
static String leerLineaBloq(uint32_t espera) {
  String s;
  uint32_t t0 = millis();
  while (millis() - t0 < espera) {
    while (cliFlujo.available()) {
      char c = (char)cliFlujo.read();
      if (c == '\n') {
        s.trim();
        return s;
      }
      if (c != '\r' && s.length() < 2048) s += c;
    }
    if (!cliFlujo.connected()) break;
    delay(5);
  }
  return String("\x01");  // se acabó el tiempo
}

bool flujoAbrir(const String &ruta) {
  flujoCerrar();
  if (!hayToken) {
    ultError = "sin sesión";
    return false;
  }
  EnRed enRed;
  String h = dbHost, camino = "/" + ruta + ".json?auth=" + token;
  for (int salto = 0; salto < 3; salto++) {
    esp_task_wdt_reset();
    cliFlujo.setCACert(CA_RAIZ);
    cliFlujo.setTimeout(15);
    cliFlujo.setHandshakeTimeout(10);
    if (!cliFlujo.connect(h.c_str(), 443)) {
      ultError = "flujo: sin conexión TLS con " + h;
      return false;
    }
    cliFlujo.print(String("GET ") + camino + " HTTP/1.1\r\nHost: " + h +
                   "\r\nAccept: text/event-stream\r\nCache-Control: no-cache\r\nUser-Agent: evse-monitor/" FW_VERSION
                   "\r\n\r\n");
    String estado = leerLineaBloq(15000);
    int codigo = estado.startsWith("HTTP/1.") ? estado.substring(9, 12).toInt() : 0;
    String destino;
    chunked = false;
    while (codigo) {
      String l = leerLineaBloq(5000);
      if (!l.length()) break;  // fin de las cabeceras
      if (l == "\x01") {
        codigo = 0;
        break;
      }
      int dos = l.indexOf(':');
      if (dos < 0) continue;
      String k = l.substring(0, dos), v = l.substring(dos + 1);
      k.toLowerCase();
      v.trim();
      if (k == "location") destino = v;
      else if (k == "transfer-encoding" && v.indexOf("chunked") >= 0) chunked = true;
    }
    if ((codigo == 307 || codigo == 302 || codigo == 301) && destino.startsWith("https://")) {
      cliFlujo.stop();
      String d = destino.substring(8);
      int b = d.indexOf('/');
      h = b < 0 ? d : d.substring(0, b);
      camino = b < 0 ? String("/") : d.substring(b);
      continue;
    }
    if (codigo != 200) {
      ultError = "flujo: " + (codigo ? String("HTTP ") + codigo : String("sin respuesta"));
      if (codigo == 401) hayToken = false;
      cliFlujo.stop();
      return false;
    }
    flujoOn = true;
    revocado = false;
    ultimoDato = millis();
    linea = "";
    linea.reserve(512);
    evTipo = "";
    evDatos = "";
    chunkEstado = 0;
    chunkRestante = 0;
    chunkTam = "";
    rlen = rpos = 0;
    return true;
  }
  ultError = "flujo: demasiadas redirecciones";
  return false;
}

void flujoCerrar() {
  if (flujoOn || cliFlujo.connected()) cliFlujo.stop();
  flujoOn = false;
}

bool flujoActivo() { return flujoOn; }
bool flujoRevocado() { return revocado; }
uint32_t flujoUltimo() { return ultimoDato; }

// Un carácter del texto SSE; true cuando cierra un evento «put» o «patch».
static bool alimentar(char c, Evento &e) {
  if (c == '\r') return false;
  if (c != '\n') {
    if (linea.length() < 32768) linea += c;
    return false;
  }
  if (!linea.length()) {  // línea vacía: fin del evento
    bool listo = false;
    if (evTipo == "put" || evTipo == "patch") {
      e.tipo = evTipo;
      e.datos = evDatos;
      listo = true;
    } else if (evTipo == "auth_revoked" || evTipo == "cancel") {
      revocado = true;
      ultError = "flujo: " + evTipo;
    }
    evTipo = "";
    evDatos = "";
    return listo;
  }
  if (linea.startsWith("event:")) {
    evTipo = linea.substring(6);
    evTipo.trim();
  } else if (linea.startsWith("data:")) {
    evDatos += linea.substring(linea.length() > 5 && linea[5] == ' ' ? 6 : 5);
  }
  linea = "";
  return false;
}

bool flujoLeer(Evento &e) {
  if (!flujoOn) return false;
  int vueltas = 0;
  while (vueltas++ < 32) {
    if (rpos >= rlen) {
      int disp = cliFlujo.available();
      if (disp <= 0) break;
      rlen = cliFlujo.read(rbuf, disp > (int)sizeof(rbuf) ? sizeof(rbuf) : disp);
      rpos = 0;
      if (rlen <= 0) {
        rlen = 0;
        break;
      }
      ultimoDato = millis();
    }
    while (rpos < rlen) {
      char c = (char)rbuf[rpos++];
      if (chunked) {
        if (chunkEstado == 0) {
          if (c == '\n') {
            chunkRestante = strtol(chunkTam.c_str(), nullptr, 16);
            chunkTam = "";
            chunkEstado = chunkRestante > 0 ? 1 : 3;
          } else if (c != '\r') {
            chunkTam += c;
          }
          continue;
        }
        if (chunkEstado == 2) {
          if (c == '\n') chunkEstado = 0;
          continue;
        }
        if (chunkEstado == 3) {
          flujoOn = false;
          ultError = "flujo: el servidor terminó la respuesta";
          return false;
        }
        if (--chunkRestante <= 0) chunkEstado = 2;
      }
      if (alimentar(c, e)) return true;
    }
  }
  if (!cliFlujo.connected() && !cliFlujo.available() && rpos >= rlen) {
    if (flujoOn) ultError = "flujo: el servidor cerró la conexión";
    flujoOn = false;
  }
  return false;
}

}  // namespace fb
