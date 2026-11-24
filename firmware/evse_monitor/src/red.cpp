#include "red.h"
#include <ArduinoJson.h>
#include <HTTPClient.h>
#include <Update.h>
#include <WebSocketsClient.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <esp_ota_ops.h>
#include <esp_sntp.h>
#include <esp_task_wdt.h>
#include <mbedtls/sha256.h>
#include <sys/time.h>
#include "almacen.h"
#include "ca_raiz.h"
#include "config.h"
#include "control.h"
#include "tipos.h"

#if ESP_IDF_VERSION_MAJOR >= 5
#define SHA_INICIO mbedtls_sha256_starts
#define SHA_SUMAR mbedtls_sha256_update
#define SHA_FIN mbedtls_sha256_finish
#else
#define SHA_INICIO mbedtls_sha256_starts_ret
#define SHA_SUMAR mbedtls_sha256_update_ret
#define SHA_FIN mbedtls_sha256_finish_ret
#endif

namespace red {

static almacen::Red cred;
static Config cfg;
static WebSocketsClient ws;
static bool wsIniciado = false;
static bool conectado = false;
static bool vivo = false;
static bool tls = true;
static String host;
static uint16_t puerto = SERVIDOR_PUERTO;
static String cabecera;
static uint32_t ultRx = 0, ultPing = 0, ultTel = 0, ultIntentoWifi = 0, ultRevisionOta = 0;
static uint32_t seqServidor = 0;
static bool seqConocido = false;
static uint32_t loteHasta = 0, loteEnviado = 0;
static bool otaPedida = false;
static String otaVer, otaSha, otaId;
static uint32_t otaTam = 0;
static uint32_t reiniciarEn = 0;

static const char *textoReset(esp_reset_reason_t r) {
  switch (r) {
    case ESP_RST_POWERON: return "encendido";
    case ESP_RST_EXT: return "pin_en";
    case ESP_RST_SW: return "software";
    case ESP_RST_PANIC: return "panic";
    case ESP_RST_INT_WDT: return "wdt_int";
    case ESP_RST_TASK_WDT: return "wdt_tarea";
    case ESP_RST_WDT: return "wdt";
    case ESP_RST_BROWNOUT: return "brownout";
    default: return "otro";
  }
}

// «host», «host:puerto», «wss://host», «ws://host:8787» (sin TLS, solo para pruebas en la red local).
static void leerServidor() {
  String s = cred.servidor;
  s.trim();
  tls = true;
  puerto = SERVIDOR_PUERTO;
  if (s.startsWith("ws://") || s.startsWith("http://")) {
    tls = false;
    puerto = 80;
    s = s.substring(s.indexOf("//") + 2);
  } else if (s.startsWith("wss://") || s.startsWith("https://")) {
    s = s.substring(s.indexOf("//") + 2);
  }
  int barra = s.indexOf('/');
  if (barra >= 0) s = s.substring(0, barra);
  int dos = s.indexOf(':');
  if (dos >= 0) {
    puerto = (uint16_t)s.substring(dos + 1).toInt();
    s = s.substring(0, dos);
  }
  host = s;
}

// ------------------------------------------------------------------ envío
static void enviar(JsonDocument &d) {
  if (!conectado) return;
  String s;
  serializeJson(d, s);
  ws.sendTXT(s);
}

static void num(JsonObject o, const char *k, float v, int dec) {
  if (isnan(v) || isinf(v))
    o[k] = nullptr;
  else
    o[k] = serialized(String(v, dec));
}

static void enviarAck(const char *id, bool ok, const char *msg, JsonDocument *datos = nullptr) {
  JsonDocument d;
  d["t"] = "ack";
  d["id"] = id;
  d["ok"] = ok;
  d["msg"] = msg;
  if (datos) d["datos"] = *datos;
  enviar(d);
}

static void enviarOta(const char *fase, int pct, const char *msg) {
  JsonDocument d;
  d["t"] = "ota";
  d["fase"] = fase;
  d["pct"] = pct;
  d["msg"] = msg;
  d["ver"] = otaVer.length() ? otaVer.c_str() : FW_VERSION;
  enviar(d);
  Serial.printf("[ota] %s %d%% %s\n", fase, pct, msg);
}

static const char *textoArranque(uint8_t a) {
  return a == ARR_DETENIDA ? "detenida" : (a == ARR_PERMITIDA ? "permitida" : "restaurar");
}

static String hhmm(uint16_t m) {
  char b[6];
  snprintf(b, sizeof(b), "%02u:%02u", m / 60, m % 60);
  return String(b);
}

static void enviarCfg() {
  JsonDocument d;
  d["t"] = "cfg";
  d["v"] = cfg.version;
  JsonObject c = d["c"].to<JsonObject>();
  c["vnom"] = cfg.vnom;
  c["tarifa"] = cfg.tarifa;
  c["tz"] = cfg.tz_min;
  c["tmax_sonda"] = cfg.tmax_sonda;
  c["tmax_amb"] = cfg.tmax_amb;
  c["t_hist"] = cfg.t_hist;
  c["sonda_req"] = cfg.sonda_req;
  c["arranque"] = textoArranque(cfg.arranque);
  c["lim_kwh"] = cfg.lim_kwh;
  c["lim_min"] = cfg.lim_min;
  c["lim_cop"] = cfg.lim_cop;
  JsonObject h = c["horario"].to<JsonObject>();
  h["on"] = cfg.horario_on;
  JsonArray v = h["v"].to<JsonArray>();
  for (int k = 0; k < cfg.n_vent && k < 4; k++) {
    JsonObject w = v.add<JsonObject>();
    w["d"] = cfg.vent[k].dias;
    w["i"] = hhmm(cfg.vent[k].ini);
    w["f"] = hhmm(cfg.vent[k].fin);
  }
  c["i_inicio"] = cfg.i_inicio;
  c["fin_min"] = cfg.fin_min;
  c["inv_ct"] = cfg.inv_ct;
  c["tel_s"] = cfg.tel_s;
  c["reg_carga_s"] = cfg.reg_carga_s;
  c["reg_reposo_s"] = cfg.reg_reposo_s;
  enviar(d);
}

static void enviarHola() {
  JsonDocument d;
  d["t"] = "hola";
  d["fw"] = FW_VERSION;
  d["id"] = cred.id;
  d["reset"] = textoReset(esp_reset_reason());
  d["mac"] = WiFi.macAddress();
  d["cfgv"] = cfg.version;
  d["seq_min"] = buffer::seqMin();
  d["seq_max"] = buffer::seqMax();
  d["up"] = millis() / 1000;
  d["hora"] = control::ahora();
  d["ota_pend"] = almacen::otaPendiente();
  enviar(d);
}

static void enviarTel() {
  Instantanea s;
  control::instantanea(s);
  JsonDocument d;
  JsonObject o = d.to<JsonObject>();
  o["t"] = "tel";
  o["ts"] = s.ts;
  if (s.med_ok) {
    num(o, "v", s.v, 2);
    num(o, "i", s.i, 3);
    num(o, "p", s.p, 0);
    num(o, "pf", s.pf, 3);
    num(o, "f", s.f, 2);
  } else {
    o["v"] = nullptr;
    o["i"] = nullptr;
    o["p"] = nullptr;
    o["pf"] = nullptr;
    o["f"] = nullptr;
  }
  num(o, "es", s.e_ses_kwh, 3);
  num(o, "et", (float)s.e_tot_kwh, 3);
  o["ses"] = s.ses_num;
  o["sini"] = s.ses_ini;
  o["dur"] = s.ses_dur_s;
  num(o, "pmax", s.p_max, 0);
  num(o, "tsn", s.sonda_ok ? s.t_sonda : NAN, 1);
  num(o, "tam", s.amb_ok ? s.t_amb : NAN, 1);
  num(o, "hum", s.amb_ok ? s.hum : NAN, 0);
  o["k1"] = s.k1 ? 1 : 0;
  o["perm"] = s.permiso ? 1 : 0;
  o["mot"] = motivoTexto(s.motivo);
  JsonArray al = o["al"].to<JsonArray>();
  JsonArray nr = o["nr"].to<JsonArray>();
  for (int b = 0; b < N_ALARMAS; b++) {
    if (s.alarmas >> b & 1) al.add(alarmaCodigo(b));
    if (s.sin_reconocer >> b & 1) nr.add(alarmaCodigo(b));
  }
  o["rssi"] = WiFi.RSSI();
  o["heap"] = ESP.getFreeHeap();
  o["up"] = s.uptime_s;
  uint32_t mx = buffer::seqMax();
  o["pend"] = mx > seqServidor ? mx - seqServidor : 0;
  enviar(d);
}

// ------------------------------------------------------------------ búfer → servidor
static const char *finTexto(uint8_t m) { return m == 1 ? "sin_corriente" : (m == 2 ? "limite" : "otro"); }

static void llenar(JsonObject o, const Registro &r) {
  o["s"] = r.seq;
  o["ts"] = r.ts;
  if (r.flags & 1) o["sh"] = 1;  // sin hora: ts es el uptime en segundos
  char k[2] = {(char)r.tipo, 0};
  o["k"] = k;
  o["k1"] = r.k1;
  o["mot"] = motivoTexto(r.motivo);
  if (r.tipo == 'm') {
    num(o, "v", r.m.v, 2);
    num(o, "i", r.m.i, 3);
    num(o, "p", r.m.p, 0);
    num(o, "pf", r.m.pf, 3);
    num(o, "f", r.m.f, 2);
    num(o, "es", r.m.es, 3);
    num(o, "et", r.m.et, 3);
    num(o, "tsn", r.m.tsn, 1);
    num(o, "tam", r.m.tam, 1);
    num(o, "hum", r.m.hum, 0);
  } else if (r.tipo == 'e') {
    o["c"] = eventoCodigo(r.e.codigo);
    o["n"] = r.e.nivel;
    num(o, "val", r.e.valor, 2);
    o["x"] = r.e.extra;
    if (r.e.codigo == E_ALARMA || r.e.codigo == E_ALARMA_FIN) {
      o["a"] = alarmaCodigo((int)r.e.valor);
      o["txt"] = alarmaTexto((int)r.e.valor);
    }
  } else if (r.tipo == 's') {
    o["num"] = r.s.num;
    o["ini"] = r.s.ini;
    o["fin"] = r.s.fin;
    num(o, "kwh", r.s.kwh, 3);
    num(o, "pmax", r.s.pmax, 0);
    o["mf"] = finTexto(r.s.motivo_fin);
  }
}

static void subirRegistros() {
  if (!conectado || !seqConocido) return;
  if (loteHasta && millis() - loteEnviado < 15000) return;  // esperando «regack»
  uint32_t mx = buffer::seqMax(), mn = buffer::seqMin();
  uint32_t desde = seqServidor + 1;
  if (desde < mn) desde = mn;
  if (mx == 0 || desde > mx) {
    loteHasta = 0;
    return;
  }
  JsonDocument d;
  d["t"] = "reg";
  JsonArray arr = d["r"].to<JsonArray>();
  uint32_t ultimo = desde - 1;
  int n = 0;
  for (uint32_t s = desde; s <= mx && n < REG_LOTE; s++) {
    ultimo = s;
    Registro r;
    if (!buffer::leer(s, r)) continue;  // registro perdido (corte a medio escribir)
    llenar(arr.add<JsonObject>(), r);
    n++;
  }
  d["hasta"] = ultimo;
  enviar(d);
  loteHasta = ultimo;
  loteEnviado = millis();
}

// ------------------------------------------------------------------ configuración desde la app
static float rango(float v, float a, float b) { return v < a ? a : (v > b ? b : v); }

static uint16_t minutos(const char *s, uint16_t defecto) {
  int h, m;
  if (!s || sscanf(s, "%d:%d", &h, &m) != 2 || h < 0 || h > 24 || m < 0 || m > 59) return defecto;
  int t = h * 60 + m;
  return t >= 1440 ? 0 : (uint16_t)t;
}

static void aplicarConfig(JsonObject c, uint32_t version) {
  Config n = cfg;
  if (!c["vnom"].isNull()) n.vnom = (c["vnom"].as<int>() >= 200) ? 240 : 120;
  n.tarifa = rango(c["tarifa"] | n.tarifa, 0, 100000);
  n.tz_min = (int16_t)rango(c["tz"] | (float)n.tz_min, -720, 840);
  n.tmax_sonda = rango(c["tmax_sonda"] | n.tmax_sonda, 30, 90);
  n.tmax_amb = rango(c["tmax_amb"] | n.tmax_amb, 30, 85);
  n.t_hist = rango(c["t_hist"] | n.t_hist, 2, 30);
  n.sonda_req = c["sonda_req"] | n.sonda_req;
  if (c["arranque"].is<const char *>()) {
    String a = c["arranque"].as<const char *>();
    n.arranque = a == "detenida" ? ARR_DETENIDA : (a == "permitida" ? ARR_PERMITIDA : ARR_RESTAURAR);
  }
  n.lim_kwh = rango(c["lim_kwh"] | n.lim_kwh, 0, 500);
  n.lim_min = (uint32_t)rango(c["lim_min"] | (float)n.lim_min, 0, 2880);
  n.lim_cop = rango(c["lim_cop"] | n.lim_cop, 0, 10000000);
  if (c["horario"].is<JsonObject>()) {
    JsonObject h = c["horario"];
    n.horario_on = h["on"] | false;
    n.n_vent = 0;
    for (JsonObject w : h["v"].as<JsonArray>()) {
      if (n.n_vent >= 4) break;
      Ventana &v = n.vent[n.n_vent++];
      v.dias = (uint8_t)((w["d"] | 127) & 0x7F);
      v.ini = minutos(w["i"] | "00:00", 0);
      v.fin = minutos(w["f"] | "00:00", 0);
    }
  }
  n.i_inicio = rango(c["i_inicio"] | n.i_inicio, 0.2f, 10);
  n.fin_min = (uint16_t)rango(c["fin_min"] | (float)n.fin_min, 1, 240);
  n.inv_ct = c["inv_ct"] | n.inv_ct;
  n.tel_s = (uint16_t)rango(c["tel_s"] | (float)n.tel_s, 5, 300);
  n.reg_carga_s = (uint16_t)rango(c["reg_carga_s"] | (float)n.reg_carga_s, 10, 600);
  n.reg_reposo_s = (uint16_t)rango(c["reg_reposo_s"] | (float)n.reg_reposo_s, 60, 3600);
  n.version = version;
  almacen::configGuardar(n);
  cfg = n;
  Orden o;
  memset(&o, 0, sizeof(o));
  o.tipo = O_CONFIG;
  control::enviarOrden(o);
  enviarCfg();
}

// ------------------------------------------------------------------ órdenes desde la app
static void calLeer(const char *id) {
  Calibracion c;
  control::calActual(c);
  static const uint8_t dirs[] = {0x01, 0x20, 0x30, 0x2B, 0x31, 0x33, 0x2C, 0x3B};
  uint16_t v[8];
  control::registrosAtm(v, dirs, 8);
  JsonDocument datos;
  datos["calibrada"] = c.calibrada;
  datos["ugain"] = c.ugain;
  datos["igain_n"] = c.igain_n;
  datos["uoffset"] = c.uoffset;
  datos["ioffset_n"] = c.ioffset_n;
  datos["poffset_n"] = c.poffset_n;
  datos["qoffset_n"] = c.qoffset_n;
  datos["ngain"] = c.ngain;
  datos["nphi"] = c.nphi;
  datos["plconst_h"] = c.plconst_h;
  datos["plconst_l"] = c.plconst_l;
  datos["pstart"] = c.pstart;
  datos["mmode"] = c.mmode;
  char b[8];
  const char *nombres[] = {"sysstatus", "calstart", "adjstart", "mmode_chip", "ugain_chip", "igain_n_chip", "cs1", "cs2"};
  JsonObject chip = datos["chip"].to<JsonObject>();
  for (int k = 0; k < 8; k++) {
    snprintf(b, sizeof(b), "%04X", v[k]);
    chip[nombres[k]] = b;
  }
  Instantanea s;
  control::instantanea(s);
  datos["v"] = s.v;
  datos["i"] = s.i;
  datos["p"] = s.p;
  datos["pf"] = s.pf;
  enviarAck(id, true, "calibración actual", &datos);
}

static uint16_t u16(JsonVariant v, uint16_t defecto) {
  if (v.is<const char *>()) return (uint16_t)strtoul(v.as<const char *>(), nullptr, 16);  // «6720» en hexadecimal
  if (v.is<unsigned>() || v.is<int>()) return (uint16_t)v.as<unsigned>();
  return defecto;
}

static void orden(JsonDocument &d) {
  const char *id = d["id"] | "";
  String o = d["o"] | "";
  JsonObject a = d["a"];
  Orden ord;
  memset(&ord, 0, sizeof(ord));
  strlcpy(ord.id, id, sizeof(ord.id));
  if (o == "permitir") ord.tipo = O_PERMITIR;
  else if (o == "detener") ord.tipo = O_DETENER;
  else if (o == "reconocer") ord.tipo = O_RECONOCER;
  else if (o == "soltar_parar") ord.tipo = O_PARAR_SOLTAR;
  else if (o == "cal_fabrica") ord.tipo = O_CAL_FABRICA;
  else if (o == "cal_auto") {
    ord.tipo = O_CAL_AUTO;
    ord.a = a["v"] | 0.0f;
    ord.b = a["i"] | 0.0f;
  } else if (o == "cal_escribir") {
    ord.tipo = O_CAL_ESCRIBIR;
    control::calActual(ord.cal);
    Calibracion &c = ord.cal;
    c.ugain = u16(a["ugain"], c.ugain);
    c.igain_n = u16(a["igain_n"], c.igain_n);
    c.uoffset = u16(a["uoffset"], c.uoffset);
    c.ioffset_n = u16(a["ioffset_n"], c.ioffset_n);
    c.poffset_n = u16(a["poffset_n"], c.poffset_n);
    c.qoffset_n = u16(a["qoffset_n"], c.qoffset_n);
    c.ngain = u16(a["ngain"], c.ngain);
    c.nphi = u16(a["nphi"], c.nphi);
    c.plconst_h = u16(a["plconst_h"], c.plconst_h);
    c.plconst_l = u16(a["plconst_l"], c.plconst_l);
    c.pstart = u16(a["pstart"], c.pstart);
    c.calibrada = a["calibrada"] | true;
    if (c.ugain > 0x7FFF) {
      enviarAck(id, false, "Ugain debe ser ≤ 7FFFH (bit 15 en 0)");
      return;
    }
  } else if (o == "estado") {
    enviarTel();
    enviarAck(id, true, "estado enviado");
    return;
  } else if (o == "cal_leer") {
    calLeer(id);
    return;
  } else if (o == "reiniciar") {
    enviarAck(id, true, "reiniciando");
    reiniciarEn = millis() + 1500;
    return;
  } else if (o == "ota") {
    otaVer = a["ver"] | "";
    otaSha = a["sha"] | "";
    otaTam = a["tam"] | 0;
    otaId = id;
    if (!otaVer.length()) {
      enviarAck(id, false, "falta la versión");
      return;
    }
    enviarAck(id, true, "descargando el firmware");
    otaPedida = true;
    return;
  } else {
    enviarAck(id, false, "orden desconocida");
    return;
  }
  if (!control::enviarOrden(ord)) enviarAck(id, false, "cola de órdenes llena");
  // La respuesta llega por control::respuesta() y se manda en loop().
}

static void alRecibir(const char *txt, size_t len) {
  ultRx = millis();
  if (len == 4 && memcmp(txt, "pong", 4) == 0) return;
  JsonDocument d;
  if (deserializeJson(d, txt, len)) return;
  String t = d["t"] | "";
  if (t == "bienvenida") {
    seqServidor = d["seq"] | 0;
    if (seqServidor > buffer::seqMax()) seqServidor = buffer::seqMin() ? buffer::seqMin() - 1 : 0;  // el equipo se borró
    seqConocido = true;
    loteHasta = 0;
    vivo = d["vivo"] | false;
    uint32_t hora = d["hora"] | 0;
    if (!control::ahora() && hora > 1700000000) {  // respaldo si el NTP está bloqueado
      struct timeval tv = {(time_t)hora, 0};
      settimeofday(&tv, nullptr);
      control::horaSincronizada();
    }
    if (almacen::otaPendiente()) {
      almacen::otaMarcar(0);  // el firmware nuevo arrancó y llegó al servidor: queda confirmado
      otaVer = "";
      enviarOta("ok", 100, "firmware confirmado");
    }
    enviarCfg();
    enviarTel();
  } else if (t == "regack") {
    uint32_t h = d["hasta"] | 0;
    if (h >= seqServidor) seqServidor = h;
    loteHasta = 0;
  } else if (t == "vivo") {
    vivo = d["on"] | false;
    ultTel = 0;
  } else if (t == "cfg") {
    if (d["c"].is<JsonObject>()) aplicarConfig(d["c"].as<JsonObject>(), d["v"] | (cfg.version + 1));
  } else if (t == "orden") {
    orden(d);
  }
}

static void alEvento(WStype_t tipo, uint8_t *datos, size_t largo) {
  switch (tipo) {
    case WStype_CONNECTED:
      conectado = true;
      ultRx = ultPing = millis();
      seqConocido = false;
      Serial.printf("[red] conectado a %s\n", host.c_str());
      enviarHola();
      break;
    case WStype_DISCONNECTED:
      if (conectado) Serial.println("[red] desconectado del servidor");
      conectado = false;
      seqConocido = false;
      vivo = false;
      break;
    case WStype_TEXT:
      alRecibir((const char *)datos, largo);
      break;
    case WStype_PONG:
    case WStype_PING:
      ultRx = millis();
      break;
    default:
      break;
  }
}

// ------------------------------------------------------------------ OTA
static void otaError(const char *msg) {
  enviarOta("error", 0, msg);
  if (otaId.length()) otaId = "";
  otaVer = "";
}

static void hacerOta() {
  otaPedida = false;
  enviarOta("descargando", 0, "");
  String url = String(tls ? "https://" : "http://") + host + ":" + String(puerto) + SERVIDOR_RUTA_FW + otaVer;
  WiFiClientSecure seguro;
  WiFiClient plano;
  HTTPClient http;
  bool ok;
  if (tls) {
    seguro.setCACert(CA_RAIZ);
    seguro.setTimeout(20);
    ok = http.begin(seguro, url);
  } else {
    ok = http.begin(plano, url);
  }
  if (!ok) return otaError("URL inválida");
  http.addHeader("Authorization", "Bearer " + cred.id + ":" + cred.token);
  http.setTimeout(20000);
  int codigo = http.GET();
  if (codigo != 200) {
    http.end();
    char m[48];
    snprintf(m, sizeof(m), "HTTP %d", codigo);
    return otaError(m);
  }
  int tam = http.getSize();
  if (tam <= 0 || (otaTam && (uint32_t)tam != otaTam)) {
    http.end();
    return otaError("tamaño inesperado");
  }
  if (!Update.begin(tam, U_FLASH)) {
    http.end();
    return otaError(Update.errorString());
  }
  mbedtls_sha256_context sha;
  mbedtls_sha256_init(&sha);
  SHA_INICIO(&sha, 0);
  WiFiClient *flujo = http.getStreamPtr();
  static uint8_t buf[4096];
  int recibido = 0, pctAnt = -10;
  uint32_t ult = millis();
  while (recibido < tam) {
    esp_task_wdt_reset();
    size_t disp = flujo->available();
    if (disp) {
      int n = flujo->readBytes(buf, disp > sizeof(buf) ? sizeof(buf) : disp);
      if (n <= 0) continue;
      if (Update.write(buf, n) != (size_t)n) {
        Update.abort();
        http.end();
        mbedtls_sha256_free(&sha);
        return otaError(Update.errorString());
      }
      SHA_SUMAR(&sha, buf, n);
      recibido += n;
      ult = millis();
      int pct = (int)((int64_t)recibido * 100 / tam);
      if (pct - pctAnt >= 10) {
        pctAnt = pct;
        enviarOta("descargando", pct, "");
        ws.loop();
      }
    } else {
      if (!http.connected() || millis() - ult > 20000) {
        Update.abort();
        http.end();
        mbedtls_sha256_free(&sha);
        return otaError("se cortó la descarga");
      }
      delay(5);
    }
  }
  http.end();
  uint8_t dig[32];
  SHA_FIN(&sha, dig);
  mbedtls_sha256_free(&sha);
  char hex[65];
  for (int k = 0; k < 32; k++) sprintf(hex + 2 * k, "%02x", dig[k]);
  if (otaSha.length() && !otaSha.equalsIgnoreCase(hex)) {
    Update.abort();
    return otaError("SHA-256 no coincide");
  }
  if (!Update.end(true)) return otaError(Update.errorString());
  almacen::otaMarcar(1);
  enviarOta("listo", 100, "reiniciando con el firmware nuevo");
  for (int k = 0; k < 20; k++) {
    ws.loop();
    delay(25);
  }
  ESP.restart();
}

// ------------------------------------------------------------------ WiFi y NTP
static void alSincronizarNtp(struct timeval *) {
  control::horaSincronizada();
}

static void iniciarWs() {
  if (tls)
    ws.beginSslWithCA(host.c_str(), puerto, SERVIDOR_RUTA_WS, CA_RAIZ, "");
  else
    ws.begin(host.c_str(), puerto, SERVIDOR_RUTA_WS, "");
  ws.setExtraHeaders(cabecera.c_str());
  ws.onEvent(alEvento);
  ws.setReconnectInterval(5000 + (esp_random() % 5000));
  wsIniciado = true;
  Serial.printf("[red] servidor %s://%s:%u%s\n", tls ? "wss" : "ws", host.c_str(), puerto, SERVIDOR_RUTA_WS);
}

void begin() {
  almacen::redLeer(cred);
  almacen::configLeer(cfg);
  leerServidor();
  cabecera = "Authorization: Bearer " + cred.id + ":" + cred.token;
  if (!cred.ssid.length()) {
    // Sin WiFi guardado ni se enciende la radio (sin U1, sus picos tumban la fuente de banco).
    Serial.println("[red] sin WiFi configurado: funciona sin internet (portal: PARAR 5 s al encender, o «wifi» en la consola)");
    return;
  }
  WiFi.persistent(false);
  WiFi.mode(WIFI_STA);
  WiFi.setHostname(("evse-" + (cred.id.length() ? cred.id : String("monitor"))).c_str());
  WiFi.setAutoReconnect(true);
  WiFi.onEvent([](WiFiEvent_t, WiFiEventInfo_t) { WiFi.setTxPower(WIFI_POWER_17dBm); },
               ARDUINO_EVENT_WIFI_STA_GOT_IP);
  sntp_set_time_sync_notification_cb(alSincronizarNtp);
  configTime(0, 0, NTP_1, NTP_2);
  WiFi.begin(cred.ssid.c_str(), cred.clave.c_str());
  WiFi.setTxPower(WIFI_POWER_17dBm);  // D2: el R-78CK da 0,5 A; pico ≈ 429 mA con TX ≤ 17 dBm
  ultIntentoWifi = millis();
  Serial.printf("[red] WiFi «%s»\n", cred.ssid.c_str());
  if (!host.length() || !cred.id.length() || !cred.token.length())
    Serial.println("[red] falta el servidor, el id o el token del equipo: funciona sin internet");
}

void loop() {
  uint32_t ms = millis();
  bool wifi = WiFi.status() == WL_CONNECTED;
  if (wifi) {
    if (!wsIniciado && host.length() && cred.id.length() && cred.token.length()) iniciarWs();
  } else if (cred.ssid.length() && ms - ultIntentoWifi > 60000) {
    ultIntentoWifi = ms;  // la reconexión automática no siempre vuelve: se insiste cada minuto
    WiFi.disconnect();
    WiFi.begin(cred.ssid.c_str(), cred.clave.c_str());
    WiFi.setTxPower(WIFI_POWER_17dBm);
  }
  if (wsIniciado) ws.loop();

  control::ponerEstadoRed(conectado ? control::RED_SERVIDOR : (wifi ? control::RED_WIFI : control::RED_NADA));

  if (conectado) {
    if (ms - ultPing >= PING_PERIODO_MS) {
      ultPing = ms;
      ws.sendTXT("ping");
    }
    if (ms - ultRx > SIN_DATOS_MS) {
      Serial.println("[red] sin respuesta del servidor: se reconecta");
      ws.disconnect();
      conectado = false;
    }
    uint32_t periodo = vivo ? TEL_VIVO_MS : (uint32_t)cfg.tel_s * 1000UL;
    if (seqConocido && (ultTel == 0 || ms - ultTel >= periodo)) {
      ultTel = ms;
      enviarTel();
    }
    subirRegistros();
  }

  Respuesta r;
  while (control::respuesta(r)) {
    if (conectado) enviarAck(r.id, r.ok, r.msg);
    if (r.ok) {
      // Tras permitir, detener o reconocer, el panel se actualiza enseguida.
      ultTel = 0;
    }
  }

  if (otaPedida) hacerOta();
  if (reiniciarEn && (int32_t)(ms - reiniciarEn) >= 0) ESP.restart();
  if (ms - ultRevisionOta > 60000) {
    ultRevisionOta = ms;
    if (ms > 600000 && almacen::otaPendiente()) almacen::otaMarcar(0);  // 10 min sin fallar: confirmado
  }
}

bool enLinea() { return conectado; }

void recargarConfig() {
  almacen::configLeer(cfg);
  enviarCfg();
}

String resumen() {
  String s = "WiFi: ";
  if (WiFi.status() == WL_CONNECTED)
    s += "conectado a «" + WiFi.SSID() + "» (" + String(WiFi.RSSI()) + " dBm, IP " + WiFi.localIP().toString() + ")";
  else
    s += cred.ssid.length() ? "sin conexión a «" + cred.ssid + "»" : "sin configurar";
  s += " · servidor: ";
  s += host.length() ? (String(tls ? "wss://" : "ws://") + host + ":" + String(puerto)) : String("sin configurar");
  s += conectado ? " (en línea)" : " (desconectado)";
  uint32_t mx = buffer::seqMax();
  s += " · registros sin subir: " + String(mx > seqServidor ? mx - seqServidor : 0);
  return s;
}

}  // namespace red
