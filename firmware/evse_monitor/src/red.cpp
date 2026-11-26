#include "red.h"
#include <ArduinoJson.h>
#include <HTTPClient.h>
#include <Update.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <esp_heap_caps.h>
#include <esp_sntp.h>
#include <esp_task_wdt.h>
#include <mbedtls/base64.h>
#include <mbedtls/sha256.h>
#include <sys/time.h>
#include <vector>
#include "almacen.h"
#include "ca_raiz.h"
#include "config.h"
#include "control.h"
#include "fb.h"
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

// Rutas de la Realtime Database (docs/software/PROTOCOLO_MENSAJES.md):
//   lee   /dispositivos/{uid} → id del equipo · /equipos/{id}/nombre · /subido/{id}
//   flujo /entrada/{id}       → config, ordenes, mirando, ota, telegram
//   escribe /estado/{id} (en vivo) · /respuestas/{id}/{orden} · /mediciones, /eventos, /sesiones (del búfer)
//   lee   /firmware/{versión}/partes/{n} (OTA)

namespace red {

static almacen::Red cred;
static Config cfg;
static String eq, nombreEq;
static String fase = "sin configurar";
static String miError;
static bool enlinea = false;
static bool seqConocido = false;
static uint32_t seqServidor = 0;
static uint32_t ultIntentoWifi = 0, proxIntento = 0, espera = 5000, proxRenovar = 0;
static uint32_t vivoHasta = 0, ultTel = 0, ultFalloSubida = 0, ultRevisionOta = 0, ultAvisos = 0;
static uint8_t fallos = 0;
static uint32_t reiniciarEn = 0;
static bool cfgLeer = false, cfgSubir = false, otaLeer = false, otaBorrar = false, tgLeer = false;
static String tgToken, tgChat;

// OTA
static bool otaPedida = false;
static String otaVer, otaSha, otaClave;
static uint32_t otaTam = 0, otaPartes = 0, otaTp = 0;
static String otaFase, otaMsg;
static int otaPct = 0;

// Órdenes pendientes, ya vistas y respuestas por mandar.
struct Pend {
  String id, o, a;
  double ts;
};
struct Resp {
  String id, msg, datos;
  bool ok;
};
static std::vector<Pend> pend;
static std::vector<Resp> resp;
static String hechas[16];
static int iHechas = 0;

// Avisos por Telegram.
static std::vector<String> tgCola;
static uint32_t alarmasAnt = 0;
static uint32_t sesAnt = 0;
static float esAnt = 0, copAnt = 0;

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

static void num(JsonObject o, const char *k, float v, int dec) {
  if (isnan(v) || isinf(v))
    o.remove(k);
  else
    o[k] = serialized(String(v, dec));
}

static bool vivo() { return vivoHasta && (int32_t)(millis() - vivoHasta) < 0; }

static void desconectar(const String &motivo) {
  fb::flujoCerrar();
  if (enlinea) Serial.printf("[red] desconectado: %s\n", motivo.c_str());
  enlinea = false;
  vivoHasta = 0;
  fase = "reconectando";
  proxIntento = millis() + 2000;
}

static void contarFallo(int codigo) {
  if (codigo == 200) {
    fallos = 0;
    return;
  }
  if (codigo == 401 || ++fallos >= 5) {
    fallos = 0;
    desconectar(fb::error());
  }
}

// ------------------------------------------------------------------ configuración
static const char *textoArranque(uint8_t a) {
  return a == ARR_DETENIDA ? "detenida" : (a == ARR_PERMITIDA ? "permitida" : "restaurar");
}

static String hhmm(uint16_t m) {
  char b[6];
  snprintf(b, sizeof(b), "%02u:%02u", m / 60, m % 60);
  return String(b);
}

static void configJson(JsonObject c) {
  c["v"] = cfg.version;
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
  c["por"] = "equipo";
}

static void subirConfig() {
  JsonDocument d;
  configJson(d.to<JsonObject>());
  String b;
  serializeJson(d, b);
  int c = fb::pedir("PUT", "entrada/" + eq + "/config", b);
  if (c == 200) {
    cfgSubir = false;
    if (cfg.local) {  // la nube ya tiene los cambios de la consola
      cfg.local = 0;
      almacen::configGuardar(cfg);
    }
  }
  contarFallo(c);
}

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
  // Lo que se cambió por la consola y la nube no conoce se queda como está (n.local sigue marcado
  // hasta que subirConfig lo sube).
  if (cfg.local & CFG_LOCAL_SONDA) n.sonda_req = cfg.sonda_req;
  if (cfg.local & CFG_LOCAL_VNOM) n.vnom = cfg.vnom;
  n.version = version;
  almacen::configGuardar(n);
  cfg = n;
  Orden o;
  memset(&o, 0, sizeof(o));
  o.tipo = O_CONFIG;
  control::enviarOrden(o);
  cfgSubir = true;  // se devuelve lo aplicado (con los valores ya limitados), con la misma versión
  Serial.printf("[red] configuración v%lu aplicada\n", (unsigned long)version);
}

static void remotaConfig(JsonVariant v) {
  if (!v.is<JsonObject>()) {  // no hay configuración en la nube: se sube la del equipo
    cfgSubir = true;
    return;
  }
  JsonObject c = v.as<JsonObject>();
  uint32_t ver = c["v"] | 0;
  if (cfg.local) {
    // Cambios de la consola hechos sin conexión (p. ej. «sonda 0» antes del primer enlace, cuando la app
    // ya creó su v1): se mezclan con la de la nube y suben con una versión mayor que las dos.
    uint32_t nueva = ver + 1 > cfg.version ? ver + 1 : cfg.version;
    Serial.printf("[red] mezclando la configuración de la nube (v%lu) con la de la consola → v%lu\n",
                  (unsigned long)ver, (unsigned long)nueva);
    aplicarConfig(c, nueva);
  } else if (ver > cfg.version) {
    aplicarConfig(c, ver);
  } else if (ver < cfg.version) {
    cfgSubir = true;
  }
}

// ------------------------------------------------------------------ telemetría en vivo
// Lo que el usuario tiene que ver enseguida en la app: K1, permiso, motivo, botón PARAR y alarmas.
static uint32_t firmaTel = 0, ultUrgente = 0;
static uint32_t firma(const Instantanea &s) {
  uint32_t f = (s.k1 ? 1u : 0u) | (s.permiso ? 2u : 0u) | (s.btn ? 4u : 0u) | (s.btn_rearma ? 8u : 0u) | ((uint32_t)s.motivo << 4);
  return f ^ (s.alarmas * 2654435761u) ^ (s.sin_reconocer * 40503u);
}
static bool cambioUrgente() {
  if ((int32_t)(millis() - ultUrgente) < 250) return false;
  Instantanea s;
  control::instantanea(s);
  if (firma(s) == firmaTel) return false;
  ultUrgente = millis();
  return true;
}

static void subirTel() {
  Instantanea s;
  control::instantanea(s);
  firmaTel = firma(s);
  Calibracion cal;
  control::calActual(cal);
  JsonDocument d;
  JsonObject o = d.to<JsonObject>();
  o["ts"][".sv"] = "timestamp";
  o["hora"] = s.ts;
  if (s.med_ok) {
    num(o, "v", s.v, 2);
    num(o, "i", s.i, 3);
    num(o, "p", s.p, 0);
    num(o, "pf", s.pf, 3);
    num(o, "f", s.f, 2);
  }
  num(o, "es", s.e_ses_kwh, 3);
  num(o, "et", (float)s.e_tot_kwh, 3);
  o["ses"] = s.ses_num;
  o["sini"] = s.ses_ini;
  o["dur"] = s.ses_dur_s;
  num(o, "pmax", s.p_max, 0);
  if (s.sonda_ok) num(o, "tsn", s.t_sonda, 1);
  if (s.amb_ok) {
    num(o, "tam", s.t_amb, 1);
    num(o, "hum", s.hum, 0);
  }
  o["k1"] = s.k1 ? 1 : 0;
  o["perm"] = s.permiso ? 1 : 0;
  o["mot"] = motivoTexto(s.motivo);
  o["btn"] = s.btn ? 1 : 0;  // PARAR oprimido ahora (la app lo muestra y cuenta los 3 s para quitar el paro)
  if (s.btn) {
    o["btn_ms"] = s.btn_ms;
    o["btn_rea"] = s.btn_rearma ? 1 : 0;
  }
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
  o["cfg_v"] = cfg.version;
  o["cal"] = cal.calibrada;
  o["fw"] = FW_VERSION;
  o["mac"] = WiFi.macAddress();
  o["ip"] = WiFi.localIP().toString();
  o["reset"] = textoReset(esp_reset_reason());
  o["vivo"] = vivo() ? 1 : 0;
  if (otaFase.length()) {
    JsonObject t = o["ota"].to<JsonObject>();
    t["fase"] = otaFase;
    t["pct"] = otaPct;
    t["msg"] = otaMsg;
    t["ver"] = otaVer.length() ? otaVer : String(FW_VERSION);
  }
  String b;
  serializeJson(d, b);
  int c = fb::pedir("PUT", "estado/" + eq, b);
  ultTel = millis();
  contarFallo(c);
}

// ------------------------------------------------------------------ búfer → historial
static const char *finTexto(uint8_t m) { return m == 1 ? "sin_corriente" : (m == 2 ? "limite" : "otro"); }

static void llenar(JsonDocument &d, const Registro &r) {
  uint32_t ts = r.ts;
  bool sh = r.flags & 1;  // sin hora: ts es el uptime en segundos
  if (sh) {
    uint32_t t = control::ahora(), up = millis() / 1000;
    if (t && r.ts <= up) {
      ts = t - (up - r.ts);
      sh = false;
    }
  }
  char clave[64];
  JsonObject o;
  if (r.tipo == 'm') {
    if (sh) return;  // una muestra sin hora no sirve para la gráfica
    snprintf(clave, sizeof(clave), "mediciones/%s/%lu", eq.c_str(), (unsigned long)ts);
    o = d[clave].to<JsonObject>();
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
    snprintf(clave, sizeof(clave), "eventos/%s/%010lu-%06lu", eq.c_str(), (unsigned long)(sh ? 0 : ts),
             (unsigned long)(r.seq % 1000000));
    o = d[clave].to<JsonObject>();
    o["ts"] = sh ? 0 : ts;
    if (sh) o["sh"] = 1;
    o["c"] = eventoCodigo(r.e.codigo);
    o["n"] = r.e.nivel;
    num(o, "val", r.e.valor, 2);
    o["x"] = r.e.extra;
    if (r.e.codigo == E_ALARMA || r.e.codigo == E_ALARMA_FIN) {
      o["a"] = alarmaCodigo((int)r.e.valor);
      o["txt"] = alarmaTexto((int)r.e.valor);
    }
  } else if (r.tipo == 's') {
    snprintf(clave, sizeof(clave), "sesiones/%s/%lu", eq.c_str(), (unsigned long)(r.s.ini ? r.s.ini : r.s.num));
    o = d[clave].to<JsonObject>();
    o["num"] = r.s.num;
    o["ini"] = r.s.ini;
    o["fin"] = r.s.fin;
    num(o, "kwh", r.s.kwh, 3);
    num(o, "pmax", r.s.pmax, 0);
    o["cop"] = (long)lroundf(r.s.kwh * cfg.tarifa);
    o["mf"] = finTexto(r.s.motivo_fin);
  } else {
    return;
  }
  o["k1"] = r.k1;
  o["mot"] = motivoTexto(r.motivo);
}

static void subirRegistros(uint32_t ms) {
  if (!seqConocido) return;
  if (ultFalloSubida && ms - ultFalloSubida < 10000) return;
  uint32_t mx = buffer::seqMax(), mn = buffer::seqMin();
  uint32_t desde = seqServidor + 1;
  if (desde < mn) desde = mn;
  if (mx == 0 || desde > mx) return;
  JsonDocument d;
  uint32_t ultimo = desde - 1;
  for (uint32_t s = desde; s <= mx && s < desde + REG_LOTE; s++) {
    ultimo = s;
    Registro r;
    if (buffer::leer(s, r)) llenar(d, r);  // si no, registro perdido (corte a medio escribir)
  }
  d["subido/" + eq] = ultimo;  // en la misma escritura: o entra todo o nada
  String b;
  serializeJson(d, b);
  int c = fb::pedir("PATCH", "", b, nullptr, 15000);
  if (c == 200) {
    seqServidor = ultimo;
    ultFalloSubida = 0;
  } else {
    ultFalloSubida = ms ? ms : 1;
    Serial.printf("[red] no se pudo subir el búfer: %s\n", fb::error().c_str());
  }
  contarFallo(c);
}

// ------------------------------------------------------------------ órdenes
static void responder(const String &id, bool ok, const String &msg, const String &datos = "") {
  if (!id.length()) return;
  if (resp.size() >= 8) resp.erase(resp.begin());
  resp.push_back({id, msg, datos, ok});
  Serial.printf("[orden] %s: %s %s\n", id.c_str(), ok ? "bien" : "NO", msg.c_str());
}

static void enviarRespuestas() {
  while (!resp.empty() && enlinea) {
    Resp &r = resp.front();
    JsonDocument d;
    d["ok"] = r.ok;
    d["msg"] = r.msg;
    d["ts"][".sv"] = "timestamp";
    if (r.datos.length()) d["datos"] = serialized(r.datos);
    String b;
    serializeJson(d, b);
    int c = fb::pedir("PUT", "respuestas/" + eq + "/" + r.id, b);
    contarFallo(c);
    if (c != 200) return;
    fb::pedir("DELETE", "entrada/" + eq + "/ordenes/" + r.id);
    resp.erase(resp.begin());
  }
}

static bool yaVista(const String &id) {
  for (auto &h : hechas)
    if (h == id) return true;
  for (auto &p : pend)
    if (p.id == id) return true;
  return false;
}

static void encolar(const String &id, JsonVariant v) {
  if (!v.is<JsonObject>() || !id.length() || id.length() >= sizeof(Orden::id) || yaVista(id)) return;
  if (pend.size() >= 8) return;  // las demás quedan en la nube y llegan al reconectar
  Pend p;
  p.id = id;
  p.o = v["o"] | "";
  if (!v["a"].isNull()) serializeJson(v["a"], p.a);
  p.ts = v["ts"] | 0.0;
  pend.push_back(p);
}

static bool telegram(const String &texto) {
  if (!tgToken.length() || !tgChat.length()) return false;
  WiFiClientSecure c;
  c.setCACert(CA_RAIZ);
  c.setTimeout(15);
  HTTPClient h;
  if (!h.begin(c, "https://api.telegram.org/bot" + tgToken + "/sendMessage")) return false;
  h.setTimeout(15000);
  h.addHeader("Content-Type", "application/json");
  JsonDocument d;
  d["chat_id"] = tgChat;
  d["text"] = texto;
  String b;
  serializeJson(d, b);
  int codigo = h.POST(b);
  h.end();
  if (codigo != 200) Serial.printf("[telegram] no se pudo enviar (HTTP %d)\n", codigo);
  return codigo == 200;
}

static String calLeerJson() {
  Calibracion c;
  control::calActual(c);
  static const uint8_t dirs[] = {0x01, 0x20, 0x30, 0x2B, 0x31, 0x33, 0x2C, 0x3B};
  uint16_t v[8];
  control::registrosAtm(v, dirs, 8);
  JsonDocument d;
  d["calibrada"] = c.calibrada;
  d["ugain"] = c.ugain;
  d["igain_n"] = c.igain_n;
  d["uoffset"] = c.uoffset;
  d["ioffset_n"] = c.ioffset_n;
  d["poffset_n"] = c.poffset_n;
  d["qoffset_n"] = c.qoffset_n;
  d["ngain"] = c.ngain;
  d["nphi"] = c.nphi;
  d["plconst_h"] = c.plconst_h;
  d["plconst_l"] = c.plconst_l;
  d["pstart"] = c.pstart;
  d["mmode"] = c.mmode;
  char b[8];
  const char *nombres[] = {"sysstatus", "calstart", "adjstart", "mmode_chip", "ugain_chip", "igain_n_chip", "cs1", "cs2"};
  JsonObject chip = d["chip"].to<JsonObject>();
  for (int k = 0; k < 8; k++) {
    snprintf(b, sizeof(b), "%04X", v[k]);
    chip[nombres[k]] = b;
  }
  Instantanea s;
  control::instantanea(s);
  d["v"] = s.v;
  d["i"] = s.i;
  d["p"] = s.p;
  d["pf"] = s.pf;
  String out;
  serializeJson(d, out);
  return out;
}

static uint16_t u16(JsonVariant v, uint16_t defecto) {
  if (v.is<const char *>()) return (uint16_t)strtoul(v.as<const char *>(), nullptr, 16);  // «6720» en hexadecimal
  if (v.is<unsigned>() || v.is<int>()) return (uint16_t)v.as<unsigned>();
  return defecto;
}

static void ejecutar(const Pend &p) {
  hechas[iHechas] = p.id;
  iHechas = (iHechas + 1) % 16;
  uint32_t t = control::ahora();
  if (t && p.ts > 1e12) {
    double dif = (double)t * 1000.0 - p.ts;
    if (dif > ORDEN_VENCE_MS || dif < -(double)ORDEN_VENCE_MS)
      return responder(p.id, false, "orden vencida: llegó al equipo más de 2 min después");
  }
  JsonDocument d;
  deserializeJson(d, p.a.length() ? p.a : String("{}"));
  JsonObject a = d.as<JsonObject>();
  Orden ord;
  memset(&ord, 0, sizeof(ord));
  strlcpy(ord.id, p.id.c_str(), sizeof(ord.id));
  const String &o = p.o;
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
    if (c.ugain > 0x7FFF) return responder(p.id, false, "Ugain debe ser ≤ 7FFFH (bit 15 en 0)");
  } else if (o == "estado") {
    ultTel = 0;
    return responder(p.id, true, "estado enviado");
  } else if (o == "cal_leer") {
    return responder(p.id, true, "calibración actual", calLeerJson());
  } else if (o == "reiniciar") {
    reiniciarEn = millis() + 3000;
    return responder(p.id, true, "reiniciando");
  } else if (o == "telegram_probar") {
    if (!tgToken.length() || !tgChat.length()) return responder(p.id, false, "falta el token o el chat de Telegram");
    bool ok = telegram("✅ " + (nombreEq.length() ? nombreEq : eq) + ": los avisos de Telegram funcionan.");
    return responder(p.id, ok, ok ? "mensaje enviado" : "Telegram no aceptó el mensaje (revisa el token y el chat)");
  } else {
    return responder(p.id, false, "orden desconocida: " + o);
  }
  if (!control::enviarOrden(ord)) responder(p.id, false, "cola de órdenes llena");
  // La respuesta llega por control::respuesta() y se manda en loop().
}

// ------------------------------------------------------------------ OTA desde la base (partes en base64)
static void otaInforme(const char *f, int pct, const String &msg) {
  otaFase = f;
  otaPct = pct;
  otaMsg = msg;
  Serial.printf("[ota] %s %d%% %s\n", f, pct, msg.c_str());
  if (!enlinea) return;
  JsonDocument d;
  d["fase"] = otaFase;
  d["pct"] = pct;
  d["msg"] = msg;
  d["ver"] = otaVer.length() ? otaVer : String(FW_VERSION);
  String b;
  serializeJson(d, b);
  fb::pedir("PUT", "estado/" + eq + "/ota", b);
}

static void otaEvaluar(JsonVariant v) {
  if (!v.is<JsonObject>()) {
    otaPedida = false;
    return;
  }
  String ver = v["ver"] | "";
  if (!ver.length()) return;
  if (ver == FW_VERSION) {
    if (!almacen::otaPendiente()) {
      otaBorrar = true;
      if (otaFase != "ok") {
        otaFase = "ok";
        otaPct = 100;
        otaMsg = "versión " + ver + " instalada";
      }
    }
    return;
  }
  if (ver == almacen::otaMala()) {
    otaFase = "error";
    otaPct = 0;
    otaMsg = "la " + ver + " no arrancó bien y el equipo volvió a la " FW_VERSION;
    otaBorrar = true;
    return;
  }
  if (otaPedida) return;
  otaVer = ver;
  otaSha = v["sha"] | "";
  otaTam = v["tam"] | 0;
  otaPartes = v["partes"] | 0;
  otaTp = v["tp"] | 0;
  otaClave = v["clave"] | "";
  otaPedida = true;
}

static void otaError(const String &msg) {
  otaInforme("error", 0, msg);
  otaBorrar = true;  // no se reintenta sola: se pide otra vez desde la app
}

static void hacerOta() {
  otaPedida = false;
  Instantanea s;
  control::instantanea(s);
  if (s.k1 && s.med_ok && s.i >= cfg.i_inicio) return otaError("hay una carga en curso: detenla o espera a que termine");
  if (!otaTam || !otaPartes || !otaTp || otaTp > OTA_PARTE_MAX || !otaClave.length() ||
      (uint64_t)otaPartes * otaTp < otaTam)
    return otaError("datos de la actualización incompletos");
  static uint8_t *buf = nullptr;
  if (!buf) buf = (uint8_t *)heap_caps_malloc(OTA_PARTE_MAX, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
  if (!buf) buf = (uint8_t *)malloc(OTA_PARTE_MAX);
  if (!buf) return otaError("sin memoria para la descarga");
  if (!Update.begin(otaTam, U_FLASH)) return otaError(Update.errorString());
  otaInforme("descargando", 0, "");
  mbedtls_sha256_context sha;
  mbedtls_sha256_init(&sha);
  SHA_INICIO(&sha, 0);
  uint32_t recibido = 0;
  int pctAnt = 0;
  for (uint32_t n = 0; n < otaPartes; n++) {
    esp_task_wdt_reset();
    String r;
    int c = 0;
    for (int intento = 0; intento < 3 && c != 200; intento++) {
      c = fb::pedir("GET", "firmware/" + otaClave + "/partes/" + String(n), "", &r, 30000);
      esp_task_wdt_reset();
    }
    size_t dec = 0;
    int a = r.indexOf('"'), b = r.lastIndexOf('"');
    if (c != 200 || a < 0 || b <= a ||
        mbedtls_base64_decode(buf, OTA_PARTE_MAX, &dec, (const uint8_t *)r.c_str() + a + 1, b - a - 1) != 0 ||
        dec == 0 || (n + 1 < otaPartes && dec != otaTp)) {
      Update.abort();
      mbedtls_sha256_free(&sha);
      return otaError(c != 200 ? "no se pudo bajar la parte " + String(n) + ": " + fb::error()
                               : "parte " + String(n) + " dañada");
    }
    if (Update.write(buf, dec) != dec) {
      Update.abort();
      mbedtls_sha256_free(&sha);
      return otaError(Update.errorString());
    }
    SHA_SUMAR(&sha, buf, dec);
    recibido += dec;
    int pct = (int)((uint64_t)recibido * 100 / otaTam);
    if (pct - pctAnt >= 10) {
      pctAnt = pct;
      otaInforme("descargando", pct, "");
    }
  }
  uint8_t dig[32];
  SHA_FIN(&sha, dig);
  mbedtls_sha256_free(&sha);
  char hex[65];
  for (int k = 0; k < 32; k++) sprintf(hex + 2 * k, "%02x", dig[k]);
  if (recibido != otaTam) {
    Update.abort();
    return otaError("tamaño inesperado");
  }
  if (otaSha.length() && !otaSha.equalsIgnoreCase(hex)) {
    Update.abort();
    return otaError("SHA-256 no coincide");
  }
  if (!Update.end(true)) return otaError(Update.errorString());
  almacen::otaVersion(otaVer);
  almacen::otaMarcar(1);
  otaInforme("listo", 100, "reiniciando con el firmware nuevo");
  delay(300);
  ESP.restart();
}

// ------------------------------------------------------------------ flujo de /entrada/{id}
static void mirando(JsonVariant v) {
  double ms = v | 0.0;
  bool antes = vivo();
  if (ms <= 0) {
    vivoHasta = 0;
    return;
  }
  uint32_t t = control::ahora();
  double edad = t ? (double)t * 1000.0 - ms : 0;
  if (edad > MIRANDO_MS) return;  // aviso viejo (la app ya se cerró)
  if (edad < 0) edad = 0;
  vivoHasta = millis() + (uint32_t)(MIRANDO_MS - edad);
  if (!vivoHasta) vivoHasta = 1;
  if (!antes) ultTel = 0;  // alguien abrió la app: telemetría enseguida
}

static void tocar(const String &ruta, JsonVariant v) {
  if (ruta == "/" || !ruta.length()) {
    if (!v.is<JsonObject>()) {
      cfgSubir = true;
      tgToken = tgChat = "";
      otaPedida = false;
      return;
    }
    if (v["config"].isNull()) cfgSubir = true;
    if (v["telegram"].isNull()) tgToken = tgChat = "";
    if (v["ota"].isNull()) otaPedida = false;
    for (JsonPair kv : v.as<JsonObject>()) tocar(String("/") + kv.key().c_str(), kv.value());
    return;
  }
  String r = ruta.substring(1);
  int b = r.indexOf('/');
  String primero = b < 0 ? r : r.substring(0, b);
  String resto = b < 0 ? String() : r.substring(b + 1);
  if (primero == "config") {
    if (resto.length()) cfgLeer = true;
    else remotaConfig(v);
  } else if (primero == "ordenes") {
    if (!resto.length()) {
      if (v.is<JsonObject>())
        for (JsonPair kv : v.as<JsonObject>()) encolar(kv.key().c_str(), kv.value());
    } else if (resto.indexOf('/') < 0) {
      encolar(resto, v);
    }
  } else if (primero == "mirando") {
    mirando(v);
  } else if (primero == "ota") {
    if (resto.length()) otaLeer = true;
    else otaEvaluar(v);
  } else if (primero == "telegram") {
    if (resto.length()) {
      tgLeer = true;
    } else {
      tgToken = v["token"] | "";
      tgChat = v["chat"] | "";
    }
  }
}

static void manejar(const fb::Evento &e) {
  JsonDocument d;
  if (deserializeJson(d, e.datos)) return;
  String ruta = d["path"] | "/";
  JsonVariant data = d["data"];
  if (e.tipo == "put") {
    tocar(ruta, data);
  } else if (e.tipo == "patch" && data.is<JsonObject>()) {
    for (JsonPair kv : data.as<JsonObject>())
      tocar((ruta == "/" ? String() : ruta) + "/" + kv.key().c_str(), kv.value());
  }
}

static void releer(const char *sub, bool &bandera, void (*f)(JsonVariant)) {
  if (!bandera) return;
  String r;
  int c = fb::pedir("GET", "entrada/" + eq + "/" + sub, "", &r);
  contarFallo(c);
  if (c != 200) return;
  bandera = false;
  JsonDocument d;
  if (deserializeJson(d, r)) return;
  f(d.as<JsonVariant>());
}

// ------------------------------------------------------------------ avisos por Telegram
static void avisos(uint32_t ms) {
  if (ms - ultAvisos < 1000) return;
  ultAvisos = ms;
  Instantanea s;
  control::instantanea(s);
  const uint32_t GRAVES = A_TEMP_SONDA | A_TEMP_AMB | A_SONDA_FALLA | A_MEDIDOR | A_RED | A_PARAR | A_REINICIO;
  uint32_t nuevas = s.alarmas & ~alarmasAnt & GRAVES;
  alarmasAnt = s.alarmas;
  String nombre = nombreEq.length() ? nombreEq : (eq.length() ? eq : String("EVSE Monitor"));
  bool tg = tgToken.length() && tgChat.length();
  for (int b = 0; b < N_ALARMAS && tg; b++) {
    if (!(nuevas >> b & 1) || tgCola.size() >= 6) continue;
    String t = "⚠️ " + nombre + ": " + alarmaTexto(b);
    if ((1u << b) == A_TEMP_SONDA && s.sonda_ok) t += " (" + String(s.t_sonda, 1) + " °C)";
    if ((1u << b) == A_TEMP_AMB && s.amb_ok) t += " (" + String(s.t_amb, 1) + " °C)";
    if ((1u << b) == A_RED && s.med_ok) t += " (" + String(s.v, 0) + " V)";
    if (!s.k1) t += ". La carga está detenida.";
    tgCola.push_back(t);
  }
  if (tg && sesAnt && !s.ses_num && tgCola.size() < 6) {
    char b[160];
    snprintf(b, sizeof(b), "🔌 %s: carga terminada · %.2f kWh · $%.0f", nombre.c_str(), esAnt, copAnt);
    tgCola.push_back(String(b));
  }
  sesAnt = s.ses_num;
  if (s.ses_num) {
    esAnt = s.e_ses_kwh;
    copAnt = s.e_ses_kwh * cfg.tarifa;
  }
}

// ------------------------------------------------------------------ conexión paso a paso
static void horaRespaldo() {
  uint32_t t = fb::horaServidor();
  if (control::ahora() || t < 1700000000) return;  // respaldo si el NTP está bloqueado y el DS3231 sin hora
  struct timeval tv = {(time_t)t, 0};
  settimeofday(&tv, nullptr);
  control::horaSincronizada();
  Serial.println("[red] hora puesta con la del servidor");
}

static bool idValido(const String &s) {
  if (!s.length() || s.length() > 24) return false;
  for (char c : s)
    if (!isalnum((unsigned char)c) && c != '-' && c != '_') return false;
  return true;
}

static bool paso() {
  miError = "";
  if (!fb::conSesion()) {
    fase = "iniciando sesión";
    if (!fb::entrar()) return false;
    horaRespaldo();
    Serial.printf("[red] sesión iniciada en Firebase (%s)\n", cred.correo.c_str());
  }
  if (!eq.length()) {
    fase = "buscando el equipo";
    String r;
    if (fb::pedir("GET", "dispositivos/" + fb::uid(), "", &r) != 200) return false;
    JsonDocument d;
    deserializeJson(d, r);
    String id = d.is<const char *>() ? String(d.as<const char *>()) : String();
    if (!idValido(id)) {
      miError = "esta cuenta no está asignada a ningún equipo (crea el equipo en la app)";
      return false;
    }
    eq = id;
    if (fb::pedir("GET", "equipos/" + eq + "/nombre", "", &r) == 200) {
      JsonDocument n;
      if (!deserializeJson(n, r) && n.is<const char *>()) nombreEq = n.as<const char *>();
    }
  }
  if (!seqConocido) {
    fase = "leyendo el historial";
    String r;
    if (fb::pedir("GET", "subido/" + eq, "", &r) != 200) return false;
    uint32_t s = (uint32_t)r.toInt();  // «null» → 0
    if (s > buffer::seqMax()) s = buffer::seqMin() ? buffer::seqMin() - 1 : 0;  // se borró la flash
    seqServidor = s;
    seqConocido = true;
  }
  if (!fb::flujoActivo()) {
    fase = "abriendo el flujo";
    if (!fb::flujoAbrir("entrada/" + eq)) return false;
  }
  enlinea = true;
  fase = "en línea";
  fallos = 0;
  ultTel = 0;
  Serial.printf("[red] en línea: equipo «%s» (%s)\n", eq.c_str(), nombreEq.c_str());
  if (almacen::otaPendiente()) {
    almacen::otaMarcar(0);  // el firmware nuevo arrancó y llegó al servidor: queda confirmado
    otaVer = "";
    otaFase = "ok";
    otaPct = 100;
    otaMsg = "firmware " FW_VERSION " instalado y confirmado";
  }
  return true;
}

static void conectar(uint32_t ms) {
  if (enlinea) {
    // El token dura 1 h: se renueva antes y se reabre el flujo con el nuevo.
    if (!fb::conSesion() && (int32_t)(ms - proxRenovar) >= 0) {
      proxRenovar = ms + 60000;
      if (fb::entrar()) desconectar("renovación del token");
    }
    return;
  }
  if ((int32_t)(ms - proxIntento) < 0) return;
  if (paso()) {
    espera = 5000;
    return;
  }
  proxIntento = millis() + espera;
  Serial.printf("[red] %s · reintento en %lu s\n", (miError.length() ? miError : fb::error()).c_str(),
                (unsigned long)(espera / 1000));
  espera = espera >= 60000 ? 60000 : espera * 2;  // tope de 1 min: al volver internet, en línea en ≤ 1 min
}

// ------------------------------------------------------------------ WiFi y NTP
static void alSincronizarNtp(struct timeval *) { control::horaSincronizada(); }

void begin() {
  almacen::redLeer(cred);
  almacen::configLeer(cfg);
  fb::configurar(cred.db, cred.apikey, cred.correo, cred.pass);
  if (!cred.ssid.length()) {
    // Sin WiFi guardado ni se enciende la radio (en una placa sin U1, sus picos tumban la fuente de banco).
    fase = "sin WiFi";
    Serial.println("[red] sin WiFi configurado: funciona sin internet (portal: PARAR 5 s al encender, o «wifi» en la consola)");
    return;
  }
  uint8_t mac[6];
  WiFi.macAddress(mac);
  char nombre[20];
  snprintf(nombre, sizeof(nombre), "evse-%02x%02x", mac[4], mac[5]);
  WiFi.persistent(false);
  WiFi.mode(WIFI_STA);
  WiFi.setHostname(nombre);
  WiFi.setAutoReconnect(true);
  WiFi.onEvent(
      [](WiFiEvent_t, WiFiEventInfo_t) {
        WiFi.setTxPower(WIFI_POWER_17dBm);
        espera = 5000;  // volvió el WiFi: se intenta entrar a Firebase enseguida, sin la espera acumulada
        proxIntento = millis();
      },
      ARDUINO_EVENT_WIFI_STA_GOT_IP);
  sntp_set_time_sync_notification_cb(alSincronizarNtp);
  configTime(0, 0, NTP_1, NTP_2);
  WiFi.begin(cred.ssid.c_str(), cred.clave.c_str());
  WiFi.setTxPower(WIFI_POWER_17dBm);  // D2: el R-78CK da 0,5 A; pico ≈ 429 mA con TX ≤ 17 dBm
  ultIntentoWifi = millis();
  fase = "conectando al WiFi";
  Serial.printf("[red] WiFi «%s»\n", cred.ssid.c_str());
  if (!fb::configurado())
    Serial.println("[red] falta el enlace con la app («enlazar CÓDIGO» en la consola o el portal): funciona sin internet");
}

void loop() {
  uint32_t ms = millis();
  bool wifi = WiFi.status() == WL_CONNECTED;
  if (!wifi) {
    if (enlinea) desconectar("se perdió el WiFi");
    if (cred.ssid.length()) {
      fase = "conectando al WiFi";
      if (ms - ultIntentoWifi > 30000) {
        ultIntentoWifi = ms;  // la reconexión automática no siempre vuelve: se insiste cada 30 s
        WiFi.disconnect();
        WiFi.begin(cred.ssid.c_str(), cred.clave.c_str());
        WiFi.setTxPower(WIFI_POWER_17dBm);
      }
    }
  } else if (fb::configurado()) {
    conectar(ms);
  } else {
    fase = "WiFi bien, falta el enlace";
  }

  if (enlinea) {
    fb::Evento e;
    for (int n = 0; n < 4 && fb::flujoLeer(e); n++) manejar(e);
    if (fb::flujoRevocado()) {
      fb::olvidarSesion();
      desconectar(fb::error());
    } else if (!fb::flujoActivo()) {
      desconectar(fb::error());
    } else if ((int32_t)(millis() - fb::flujoUltimo()) > (int32_t)FLUJO_SIN_DATOS_MS) {
      // millis() y con signo: «ms» se tomó al empezar la vuelta, antes de abrir el flujo o de leer un dato
      // (que dejan flujoUltimo() más nuevo que ms); sin signo, ms − flujoUltimo() daba un número enorme y
      // desconectaba a los pocos segundos de entrar (D34, 25 nov).
      desconectar("el flujo no recibe nada");
    }
  }

  control::ponerEstadoRed(enlinea ? control::RED_SERVIDOR : (wifi ? control::RED_WIFI : control::RED_NADA));

  if (enlinea) {
    releer("config", cfgLeer, remotaConfig);
    releer("ota", otaLeer, otaEvaluar);
    releer("telegram", tgLeer, [](JsonVariant v) {
      tgToken = v["token"] | "";
      tgChat = v["chat"] | "";
    });
    if (enlinea && cfgSubir) subirConfig();
    if (enlinea && otaBorrar && fb::pedir("DELETE", "entrada/" + eq + "/ota") == 200) otaBorrar = false;
    if (enlinea && !pend.empty()) {
      Pend p = pend.front();
      pend.erase(pend.begin());
      ejecutar(p);
    }
  }

  Respuesta r;
  while (control::respuesta(r)) {
    responder(r.id, r.ok, r.msg);
    if (r.ok) ultTel = 0;  // tras permitir, detener o reconocer, el panel se actualiza enseguida
  }
  avisos(ms);

  if (enlinea) {
    enviarRespuestas();
    uint32_t periodo = vivo() ? TEL_VIVO_MS : (uint32_t)cfg.tel_s * 1000UL;
    if (enlinea && (ultTel == 0 || millis() - ultTel >= periodo || cambioUrgente())) subirTel();
    if (enlinea) subirRegistros(millis());
    if (enlinea && !tgCola.empty()) {
      telegram(tgCola.front());
      tgCola.erase(tgCola.begin());
    }
    if (enlinea && otaPedida) hacerOta();
  }

  if (reiniciarEn && (int32_t)(millis() - reiniciarEn) >= 0) ESP.restart();
  if (ms - ultRevisionOta > 60000) {
    ultRevisionOta = ms;
    if (ms > 600000 && almacen::otaPendiente()) almacen::otaMarcar(0);  // 10 min sin fallar: confirmado
  }
}

bool enLinea() { return enlinea; }

void recargarConfig() {
  almacen::configLeer(cfg);
  cfgSubir = true;
}

String resumen() {
  String s = "WiFi: ";
  if (WiFi.status() == WL_CONNECTED)
    s += "conectado a «" + WiFi.SSID() + "» (" + String(WiFi.RSSI()) + " dBm, IP " + WiFi.localIP().toString() + ")";
  else
    s += cred.ssid.length() ? "sin conexión a «" + cred.ssid + "»" : "sin configurar";
  s += "\nFirebase: ";
  s += fb::configurado() ? fb::host() + " · cuenta " + cred.correo : String("sin enlace («enlazar CÓDIGO»)");
  s += "\nEstado: " + fase;
  if (eq.length()) s += " · equipo «" + eq + "»" + (nombreEq.length() ? " (" + nombreEq + ")" : String());
  if (vivo()) s += " · app abierta";
  uint32_t mx = buffer::seqMax();
  s += "\nRegistros sin subir: " + String(seqConocido && mx > seqServidor ? mx - seqServidor : (seqConocido ? 0 : mx));
  String e = miError.length() ? miError : fb::error();
  if (e.length()) s += "\nÚltimo error: " + e;
  if (tgToken.length()) s += "\nTelegram: configurado";
  return s;
}

}  // namespace red
