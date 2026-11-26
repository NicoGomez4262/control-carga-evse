// Tipos compartidos entre la tarea de control y la de red.
#pragma once
#include <Arduino.h>

// ---------------------------------------------------------------- motivo por el que la carga está detenida
// Orden de prioridad: el primero que se cumple es el que se informa.
enum Motivo : uint8_t {
  M_NINGUNO = 0,  // carga permitida
  M_FALLA,        // medidor o sonda con falla
  M_TEMP,         // sobretemperatura (sonda o ambiente)
  M_PARAR,        // botón PARAR (SW1 o J7)
  M_RED,          // tensión de red baja
  M_LIMITE,       // límite de la sesión (kWh, tiempo o costo)
  M_HORARIO,      // fuera del horario de carga
  M_APP,          // detenida desde la app
  M_ARRANQUE,     // esperando confirmación o verificaciones al arrancar
};
const char *motivoTexto(uint8_t m);

// ---------------------------------------------------------------- alarmas (máscara de bits)
enum Alarma : uint32_t {
  A_TEMP_SONDA = 1u << 0,
  A_TEMP_AMB = 1u << 1,
  A_SONDA_FALLA = 1u << 2,
  A_MEDIDOR = 1u << 3,
  A_RED = 1u << 4,
  A_PARAR = 1u << 5,
  A_AMB_FALLA = 1u << 6,
  A_SIN_HORA = 1u << 7,
  A_REINICIO = 1u << 8,   // reinicio por brownout o watchdog (hasta reconocerla)
  A_SIN_CALIBRAR = 1u << 9,
  A_TEMP_AVISO = 1u << 10,  // sonda a menos de 10 °C del límite
};
constexpr int N_ALARMAS = 11;
const char *alarmaCodigo(int bit);
const char *alarmaTexto(int bit);

// ---------------------------------------------------------------- eventos (registros tipo «e»)
enum Evento : uint16_t {
  E_ARRANQUE = 1,      // valor = motivo del reset
  E_K1 = 2,            // valor = 1 cerrado / 0 abierto; extra = motivo
  E_ALARMA = 3,        // valor = bit de la alarma que se activó; extra = medida
  E_ALARMA_FIN = 4,    // valor = bit de la alarma que se despejó
  E_SESION_INICIO = 5, // valor = número de sesión
  E_LIMITE = 6,        // valor = 1 kWh, 2 tiempo, 3 costo
  E_CONFIG = 7,        // valor = versión de la configuración
  E_CAL = 8,           // calibración cambiada
  E_ORDEN = 9,         // valor = orden local (consola o botón)
  E_OTA = 10,          // valor = 1 actualizado, 0 vuelta atrás
  E_HORA = 11,         // hora puesta por NTP (valor = corrección en s)
};
const char *eventoCodigo(uint16_t e);

// ---------------------------------------------------------------- configuración (la manda la app)
struct Ventana {
  uint8_t dias;      // bit 0 = domingo … bit 6 = sábado
  uint16_t ini;      // minuto del día
  uint16_t fin;      // minuto del día (si fin <= ini, cruza la medianoche)
};

enum PoliticaArranque : uint8_t { ARR_DETENIDA = 0, ARR_RESTAURAR = 1, ARR_PERMITIDA = 2 };

struct Config {
  uint32_t version;
  uint16_t vnom;         // 120 o 240
  float tarifa;          // COP/kWh
  int16_t tz_min;        // diferencia con UTC en minutos (Colombia: -300)
  float tmax_sonda;      // °C: corte por la sonda DS18B20
  float tmax_amb;        // °C: corte por el AHT20 (placa)
  float t_hist;          // °C de histéresis para volver a cargar
  bool sonda_req;        // sin sonda = falla
  uint8_t arranque;      // PoliticaArranque
  float lim_kwh;         // 0 = sin límite
  uint32_t lim_min;
  float lim_cop;
  bool horario_on;
  uint8_t n_vent;
  Ventana vent[4];
  float i_inicio;        // A: corriente que marca el inicio de una sesión
  uint16_t fin_min;      // minutos sin corriente para cerrar la sesión
  bool inv_ct;           // CT puesto al revés: invierte el signo de la potencia
  uint16_t tel_s;        // telemetría sin la app abierta
  uint16_t reg_carga_s;  // registro al historial durante la carga
  uint16_t reg_reposo_s; // registro al historial en reposo
  uint8_t local;         // CFG_LOCAL_*: campos cambiados por la consola que la nube todavía no tiene
};
// Cambios de la consola sin conexión: al llegar la configuración de la nube se conservan estos campos,
// lo demás lo manda la nube, y el resultado sube con una versión nueva (red.cpp, remotaConfig).
constexpr uint8_t CFG_LOCAL_SONDA = 1;  // sonda_req («sonda 0|1»)
constexpr uint8_t CFG_LOCAL_VNOM = 2;   // vnom («tension 120|240»)
void configPorDefecto(Config &c);

// ---------------------------------------------------------------- calibración del ATM90E26
struct Calibracion {
  // metering (21H–2BH)
  uint16_t plconst_h, plconst_l, lgain, lphi, ngain, nphi, pstart, pnol, qstart, qnol, mmode;
  // measurement (31H–3AH)
  uint16_t ugain, igain_l, igain_n, uoffset, ioffset_l, ioffset_n, poffset_l, qoffset_l, poffset_n, qoffset_n;
  bool calibrada;  // false = valores estimados de diseño, sin calibrar con la red (S7)
};
void calibracionPorDefecto(Calibracion &c);

// ---------------------------------------------------------------- foto del estado para la red y la consola
struct Instantanea {
  uint32_t ts;        // epoch UTC (0 si no hay hora)
  bool hora_ok;
  float v, i, p, pf, f;
  bool med_ok;
  uint16_t sys_status;
  float e_ses_kwh;
  double e_tot_kwh;
  uint32_t ses_num;   // 0 = sin sesión abierta
  uint32_t ses_ini;
  uint32_t ses_dur_s;
  float p_max;
  float t_sonda;
  bool sonda_ok;
  float t_amb, hum;
  bool amb_ok;
  bool k1;
  bool permiso;       // permiso de la app (lo que el usuario pidió)
  uint8_t motivo;
  uint32_t alarmas;
  uint32_t sin_reconocer;
  uint32_t uptime_s;
  bool btn;           // PARAR (SW1 o J7) oprimido en este momento
  bool btn_rearma;    // si se sostiene 3 s, quita el paro (ya estaba enclavado al oprimirlo)
  uint32_t btn_ms;    // cuánto lleva oprimido
};

// ---------------------------------------------------------------- registro de 64 bytes del búfer en la flash
struct __attribute__((packed)) Registro {
  uint32_t seq;   // 0xFFFFFFFF = vacío
  uint32_t ts;    // epoch UTC (0 = sin hora)
  uint8_t tipo;   // 'm' muestra, 'e' evento, 's' sesión cerrada
  uint8_t k1;
  uint8_t motivo;
  uint8_t flags;  // bit 0 = sin hora (ts es el uptime en s)
  union {
    struct __attribute__((packed)) {
      float v, i, p, pf, f, es, et, tsn, tam, hum;
    } m;
    struct __attribute__((packed)) {
      uint16_t codigo;
      uint16_t nivel;
      float valor;
      uint32_t extra;
    } e;
    struct __attribute__((packed)) {
      uint32_t num, ini, fin;
      float kwh, pmax;
      uint8_t motivo_fin;
    } s;
    uint8_t bruto[40];
  };
  uint8_t reserva[10];
  uint16_t crc;
};
static_assert(sizeof(Registro) == 64, "Registro debe medir 64 bytes");

// ---------------------------------------------------------------- órdenes hacia la tarea de control
enum TipoOrden : uint8_t {
  O_PERMITIR = 1,
  O_DETENER,
  O_RECONOCER,
  O_CONFIG,         // se cargó una configuración nueva
  O_CAL_ESCRIBIR,   // calibración nueva en `cal`
  O_CAL_AUTO,       // a = tensión de referencia, b = corriente de referencia
  O_CAL_FABRICA,
  O_PARAR_SOLTAR,   // libera el enclavamiento de PARAR (desde la app)
};

struct Orden {
  uint8_t tipo;
  char id[24];      // id de la orden de la app ("" si es local)
  float a, b;
  Calibracion cal;
};

struct Respuesta {
  char id[24];
  bool ok;
  char msg[96];
};
