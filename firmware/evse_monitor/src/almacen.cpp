#include "almacen.h"
#include <Preferences.h>
#include <esp_partition.h>
#include "secretos.h"

namespace almacen {

static constexpr uint32_t MAGIA = 0xE75E0001;

void begin() {}

static String leerTexto(Preferences &p, const char *k, const char *defecto) {
  String v = p.getString(k, "");
  return v.length() ? v : String(defecto);
}

void redLeer(Red &r) {
  Preferences p;
  p.begin("red", true);
  r.ssid = leerTexto(p, "ssid", SECRETO_WIFI_SSID);
  r.clave = leerTexto(p, "clave", SECRETO_WIFI_CLAVE);
  r.servidor = leerTexto(p, "servidor", SECRETO_SERVIDOR);
  r.id = leerTexto(p, "id", SECRETO_EQUIPO_ID);
  r.token = leerTexto(p, "token", SECRETO_EQUIPO_TOKEN);
  p.end();
}

void redGuardar(const Red &r) {
  Preferences p;
  p.begin("red", false);
  p.putString("ssid", r.ssid);
  p.putString("clave", r.clave);
  p.putString("servidor", r.servidor);
  p.putString("id", r.id);
  p.putString("token", r.token);
  p.end();
}

void redBorrar() {
  Preferences p;
  p.begin("red", false);
  p.clear();
  p.end();
}

void configLeer(Config &c) {
  configPorDefecto(c);
  Preferences p;
  p.begin("cfg", true);
  if (p.getBytesLength("c") == sizeof(Config)) p.getBytes("c", &c, sizeof(Config));
  p.end();
}

void configGuardar(const Config &c) {
  Preferences p;
  p.begin("cfg", false);
  p.putBytes("c", &c, sizeof(Config));
  p.end();
}

void calLeer(Calibracion &c) {
  calibracionPorDefecto(c);
  Preferences p;
  p.begin("cal", true);
  if (p.getBytesLength("c") == sizeof(Calibracion)) p.getBytes("c", &c, sizeof(Calibracion));
  p.end();
}

void calGuardar(const Calibracion &c) {
  Preferences p;
  p.begin("cal", false);
  p.putBytes("c", &c, sizeof(Calibracion));
  p.end();
}

void estadoLeer(Persistente &e) {
  memset(&e, 0, sizeof(e));
  Preferences p;
  p.begin("est", true);
  if (p.getBytesLength("e") == sizeof(Persistente)) p.getBytes("e", &e, sizeof(Persistente));
  p.end();
  if (e.magia != MAGIA) {
    memset(&e, 0, sizeof(e));
    e.magia = MAGIA;
  }
}

void estadoGuardar(const Persistente &e) {
  Persistente copia = e;
  copia.magia = MAGIA;
  Preferences p;
  p.begin("est", false);
  p.putBytes("e", &copia, sizeof(Persistente));
  p.end();
}

uint8_t otaPendiente() {
  Preferences p;
  p.begin("ota", true);
  uint8_t v = p.getUChar("pend", 0);
  p.end();
  return v;
}

void otaMarcar(uint8_t v) {
  Preferences p;
  p.begin("ota", false);
  p.putUChar("pend", v);
  p.putUChar("arr", 0);
  p.end();
}

uint8_t arranquesOta() {
  Preferences p;
  p.begin("ota", true);
  uint8_t v = p.getUChar("arr", 0);
  p.end();
  return v;
}

void arranquesOtaSumar() {
  Preferences p;
  p.begin("ota", false);
  p.putUChar("arr", p.getUChar("arr", 0) + 1);
  p.end();
}

}  // namespace almacen

// ===================================================================== búfer circular
// Registros de 64 bytes, 64 por sector de 4 KB. Se escribe en orden; al entrar a un sector nuevo se
// borra entero (se pierden los 64 registros más viejos). La posición de un registro sale de su número:
// pos = cabeza − (seqMax − seq). Un registro a medio escribir (corte de energía) gasta su número y se
// salta al subir.
namespace buffer {

static const esp_partition_t *part = nullptr;
static uint32_t N = 0;            // registros que caben
static constexpr uint32_t RPS = 64;  // registros por sector
static uint32_t cabeza = 0;       // posición del último escrito
static uint32_t sMax = 0;         // seq del último escrito (0 = vacío)
static bool dioVuelta = false;
static SemaphoreHandle_t mtx = nullptr;

static uint16_t crc16(const uint8_t *d, size_t n) {
  uint16_t c = 0xFFFF;
  for (size_t i = 0; i < n; i++) {
    c ^= (uint16_t)d[i] << 8;
    for (int b = 0; b < 8; b++) c = (c & 0x8000) ? (uint16_t)((c << 1) ^ 0x1021) : (uint16_t)(c << 1);
  }
  return c;
}

static bool leerPos(uint32_t pos, Registro &r) {
  return esp_partition_read(part, (size_t)pos * sizeof(Registro), &r, sizeof(Registro)) == ESP_OK;
}

static bool vacio(const Registro &r) {
  const uint8_t *b = (const uint8_t *)&r;
  for (size_t i = 0; i < sizeof(Registro); i++)
    if (b[i] != 0xFF) return false;
  return true;
}

static bool valido(const Registro &r) {
  return r.seq != 0xFFFFFFFF && r.seq != 0 && crc16((const uint8_t *)&r, sizeof(Registro) - 2) == r.crc;
}

uint32_t capacidad() { return N; }

bool begin() {
  mtx = xSemaphoreCreateMutex();
  part = esp_partition_find_first(ESP_PARTITION_TYPE_DATA, (esp_partition_subtype_t)0x40, "buffer");
  if (!part) return false;
  N = part->size / sizeof(Registro);
  const uint32_t S = N / RPS;
  // 1) El sector cuyo primer registro válido tiene el seq más alto.
  uint32_t mejorSector = UINT32_MAX, mejorSeq = 0;
  Registro r;
  for (uint32_t s = 0; s < S; s++) {
    for (uint32_t k = 0; k < 4; k++) {
      if (!leerPos(s * RPS + k, r)) break;
      if (valido(r)) {
        if (r.seq > mejorSeq) {
          mejorSeq = r.seq;
          mejorSector = s;
        }
        break;
      }
      if (vacio(r)) break;
    }
  }
  if (mejorSector == UINT32_MAX) {  // vacío
    sMax = 0;
    cabeza = N - 1;
    dioVuelta = false;
    return true;
  }
  // 2) Dentro del sector, el último registro escrito.
  uint32_t base = mejorSector * RPS;
  cabeza = base;
  sMax = 0;
  for (uint32_t k = 0; k < RPS; k++) {
    if (!leerPos(base + k, r)) break;
    if (vacio(r)) break;
    if (valido(r)) {
      cabeza = base + k;
      sMax = r.seq;
    } else {
      // A medio escribir: gasta un número y se marca con ceros para no confundirlo.
      cabeza = base + k;
      sMax += 1;
      Registro cero;
      memset(&cero, 0, sizeof(cero));
      esp_partition_write(part, (size_t)(base + k) * sizeof(Registro), &cero, sizeof(cero));
    }
  }
  // 3) ¿Ya dio la vuelta? Sí, si el sector siguiente tiene datos.
  uint32_t sig = ((mejorSector + 1) % S) * RPS;
  dioVuelta = leerPos(sig, r) && !vacio(r) && sig != base;
  return true;
}

uint32_t seqMax() { return sMax; }

uint32_t seqMin() {
  if (sMax == 0) return 0;
  uint32_t ocupados;
  if (!dioVuelta) {
    ocupados = cabeza + 1;
  } else {
    ocupados = N - (RPS - 1 - (cabeza % RPS));
  }
  return sMax >= ocupados ? sMax - ocupados + 1 : 1;
}

uint32_t escribir(Registro &r) {
  if (!part) return 0;
  xSemaphoreTake(mtx, portMAX_DELAY);
  uint32_t pos = (cabeza + 1) % N;
  if (pos == 0 && sMax > 0) dioVuelta = true;
  if (pos % RPS == 0) esp_partition_erase_range(part, (size_t)pos * sizeof(Registro), RPS * sizeof(Registro));
  r.seq = sMax + 1;
  r.crc = crc16((const uint8_t *)&r, sizeof(Registro) - 2);
  esp_err_t e = esp_partition_write(part, (size_t)pos * sizeof(Registro), &r, sizeof(Registro));
  cabeza = pos;
  sMax = r.seq;  // aunque falle, el número queda gastado
  xSemaphoreGive(mtx);
  return e == ESP_OK ? r.seq : 0;
}

bool leer(uint32_t seq, Registro &r) {
  if (!part) return false;
  xSemaphoreTake(mtx, portMAX_DELAY);
  uint32_t mn = seqMin(), mx = sMax;
  uint32_t cab = cabeza;
  xSemaphoreGive(mtx);
  if (seq == 0 || seq < mn || seq > mx) return false;
  uint32_t atras = mx - seq;
  uint32_t pos = (cab + N - (atras % N)) % N;
  if (!leerPos(pos, r)) return false;
  return valido(r) && r.seq == seq;
}

}  // namespace buffer
