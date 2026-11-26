#include "control.h"
#include <esp_task_wdt.h>
#include <math.h>
#include <sys/time.h>
#include "almacen.h"
#include "atm90e26.h"
#include "config.h"
#include "sensores.h"

namespace control {

// Sobreviven a un reinicio por software o watchdog (no a un corte de energía): detectan un bucle de reinicios.
RTC_NOINIT_ATTR static uint32_t rtcMagia;
RTC_NOINIT_ATTR static uint32_t rtcReinicios;
static constexpr uint32_t RTC_MAGIA = 0x5EB0071E;

static SemaphoreHandle_t mtxEstado = nullptr;
static SemaphoreHandle_t mtxAtm = nullptr;
static QueueHandle_t colaOrdenes = nullptr;
static QueueHandle_t colaRespuestas = nullptr;
static volatile uint8_t estadoRed = RED_NADA;
static volatile bool pedirRtc = false;
static volatile bool pulsoParar = false;

static Config cfg;
static Calibracion cal;
static almacen::Persistente per;
static Instantanea snap;

enum FinSesion : uint8_t { FIN_DESCONOCIDO = 0, FIN_SIN_CORRIENTE = 1, FIN_LIMITE = 2 };

static struct {
  // medición
  MedicionAtm med;
  bool medOk;
  bool medFalla;
  uint32_t medBuenaUltima;
  uint32_t ultReintentoAtm;
  uint32_t ultMedicion;
  uint32_t ultSag;
  // sensores
  float tSonda, tAmb, hum;
  uint32_t sondaUltima, ambUltima, ultSensores;
  // protecciones
  bool tripS, tripA, tempEnclavada;
  uint32_t bajoSDesde, bajoADesde;
  bool redBaja;
  uint32_t redBajaDesde, redOkDesde;
  bool bloqueoReinicios;
  bool reinicioAnormal;
  // botón
  bool btnEstable, btnCrudo, btnEraEnclavado, btnLargoHecho;
  uint32_t btnCambio, btnDesde;
  // arranque
  uint32_t t0;
  bool arranqueHecho;
  // K1
  bool k1;
  uint8_t motivo;
  // sesión
  uint32_t corrienteDesde, ultimaCorriente;
  double durAcum;
  // periodos
  uint32_t ultNvs, ultRegistro, tick;
  // alarmas
  uint32_t alarmas, sinReconocer;
} st;

static constexpr uint32_t ALARMAS_GRAVES =
    A_TEMP_SONDA | A_TEMP_AMB | A_SONDA_FALLA | A_MEDIDOR | A_RED | A_PARAR | A_REINICIO;

// ------------------------------------------------------------------ hora
uint32_t ahora() {
  time_t t = time(nullptr);
  return t > 1700000000 ? (uint32_t)t : 0;
}

void horaSincronizada() { pedirRtc = true; }

static void horaDesdeRtc() {
  uint32_t e;
  bool osf;
  if (sensores::rtcLeer(e, osf) && !osf && e > 1700000000 && e < 4000000000UL) {
    struct timeval tv = {(time_t)e, 0};
    settimeofday(&tv, nullptr);
    Serial.printf("[control] hora tomada del DS3231: %lu\n", (unsigned long)e);
  } else {
    Serial.println("[control] el DS3231 no tiene hora válida (OSF o sin pila): se espera el NTP");
  }
}

// ------------------------------------------------------------------ registros al búfer
static void base(Registro &r, uint8_t tipo) {
  memset(&r, 0, sizeof(r));
  r.tipo = tipo;
  uint32_t t = ahora();
  if (t) {
    r.ts = t;
  } else {
    r.ts = millis() / 1000;
    r.flags |= 1;
  }
  r.k1 = st.k1;
  r.motivo = st.motivo;
}

static void evento(uint16_t codigo, uint16_t nivel, float valor, uint32_t extra = 0) {
  Registro r;
  base(r, 'e');
  r.e.codigo = codigo;
  r.e.nivel = nivel;
  r.e.valor = valor;
  r.e.extra = extra;
  buffer::escribir(r);
  Serial.printf("[evento] %s nivel %u valor %.2f extra %lu\n", eventoCodigo(codigo), nivel, valor, (unsigned long)extra);
}

static void muestra() {
  Registro r;
  base(r, 'm');
  r.m.v = st.medOk ? st.med.v : NAN;
  r.m.i = st.medOk ? st.med.i : NAN;
  r.m.p = st.medOk ? st.med.p : NAN;
  r.m.pf = st.medOk ? st.med.pf : NAN;
  r.m.f = st.medOk ? st.med.f : NAN;
  r.m.es = per.e_ses_kwh;
  r.m.et = (float)per.e_tot_kwh;
  r.m.tsn = snap.sonda_ok ? st.tSonda : NAN;
  r.m.tam = snap.amb_ok ? st.tAmb : NAN;
  r.m.hum = snap.amb_ok ? st.hum : NAN;
  buffer::escribir(r);
}

static void guardar() {
  almacen::estadoGuardar(per);
  st.ultNvs = millis();
}

// ------------------------------------------------------------------ sesión
static void abrirSesion() {
  per.ses_contador++;
  per.ses_num = per.ses_contador;
  per.ses_ini = ahora();
  per.e_ses_kwh = 0;
  per.ses_dur_s = 0;
  per.p_max = 0;
  per.temp_disparos = 0;
  st.durAcum = 0;
  st.ultimaCorriente = millis();
  evento(E_SESION_INICIO, 0, (float)per.ses_num);
  guardar();
}

static void cerrarSesion(uint8_t motivoFin) {
  if (!per.ses_num) return;
  Registro r;
  base(r, 's');
  r.s.num = per.ses_num;
  r.s.ini = per.ses_ini;
  r.s.fin = ahora();
  r.s.kwh = per.e_ses_kwh;
  r.s.pmax = per.p_max;
  r.s.motivo_fin = motivoFin;
  buffer::escribir(r);
  Serial.printf("[sesion] cerrada nº %lu: %.3f kWh, motivo %u\n", (unsigned long)per.ses_num, per.e_ses_kwh, motivoFin);
  per.ses_num = 0;
  per.e_ses_kwh = 0;
  per.ses_dur_s = 0;
  per.p_max = 0;
  st.corrienteDesde = 0;
  guardar();
}

static void limiteAlcanzado(uint8_t tipo) {
  per.limite = true;
  evento(E_LIMITE, 0, tipo);
  cerrarSesion(FIN_LIMITE);
}

// ------------------------------------------------------------------ medición (1 Hz)
static bool aplicarCalibracion(const Calibracion &c) {
  xSemaphoreTake(mtxAtm, portMAX_DELAY);
  bool ok = atm::configurar(c, cfg.vnom);
  xSemaphoreGive(mtxAtm);
  return ok;
}

static void medir(uint32_t ms) {
  float dt = (ms - st.ultMedicion) / 1000.0f;
  if (dt > 5) dt = 5;
  st.ultMedicion = ms;

  MedicionAtm m;
  xSemaphoreTake(mtxAtm, portMAX_DELAY);
  bool ok = atm::medir(m);
  xSemaphoreGive(mtxAtm);
  // La falla se decide con los bits CalErr/AdjErr de SysStatus (lo mismo que activa WarnOut), no con el
  // nivel del pin (el datasheet no dice su polaridad; en la placa 1, S5-4 del 24 nov, WarnOut e IRQ son activos en alto).
  bool calErr = ok && (m.sys & (atm::SYS_CALERR | atm::SYS_ADJERR));
  if (ok && !calErr) {
    if (cfg.inv_ct) m.p = -m.p;
    st.med = m;
    st.medOk = true;
    st.medBuenaUltima = ms;
    // Sag: solo con el medidor calibrado (el umbral depende de Ugain) y como mucho un aviso por minuto.
    if (cal.calibrada && (m.sys & atm::SYS_SAG) && ms - st.ultSag > 60000) {
      st.ultSag = ms;
      evento(E_ALARMA, 1, 4 /* bit de A_RED */, 1 /* sag */);
    }
  } else {
    st.medOk = false;
  }
  st.medFalla = ms - st.medBuenaUltima >= MEDIDOR_FALLA_MS;
  if (st.medFalla && ms - st.ultReintentoAtm > 30000) {
    st.ultReintentoAtm = ms;
    Serial.println("[control] ATM90E26 con falla: se vuelve a configurar");
    aplicarCalibracion(cal);
  }

  // Energía: se integra la potencia activa (P > 0) cada segundo.
  if (st.medOk && st.med.p > 0) {
    double kwh = st.med.p * dt / 3.6e6;
    per.e_tot_kwh += kwh;
    if (per.ses_num) per.e_ses_kwh += kwh;
  }

  // Sesión: empieza con corriente ≥ i_inicio durante 10 s con K1 cerrado; termina tras fin_min sin corriente.
  float I = st.medOk ? st.med.i : 0;
  if (I >= 0.3f) st.ultimaCorriente = ms;
  if (!per.ses_num) {
    if (st.k1 && I >= cfg.i_inicio) {
      if (!st.corrienteDesde) st.corrienteDesde = ms;
      if (ms - st.corrienteDesde >= 10000) abrirSesion();
    } else {
      st.corrienteDesde = 0;
    }
  } else {
    uint32_t t = ahora();
    if (t && per.ses_ini && t >= per.ses_ini) {
      per.ses_dur_s = t - per.ses_ini;
    } else {
      st.durAcum += dt;
      if (st.durAcum >= 1) {
        per.ses_dur_s += (uint32_t)st.durAcum;
        st.durAcum -= (uint32_t)st.durAcum;
      }
    }
    if (st.medOk && st.med.p > per.p_max) per.p_max = st.med.p;
    if (ms - st.ultimaCorriente >= (uint32_t)cfg.fin_min * 60000UL) {
      cerrarSesion(FIN_SIN_CORRIENTE);
    } else if (cfg.lim_kwh > 0 && per.e_ses_kwh >= cfg.lim_kwh) {
      limiteAlcanzado(1);
    } else if (cfg.lim_min > 0 && per.ses_dur_s >= cfg.lim_min * 60) {
      limiteAlcanzado(2);
    } else if (cfg.lim_cop > 0 && per.e_ses_kwh * cfg.tarifa >= cfg.lim_cop) {
      limiteAlcanzado(3);
    }
  }
}

// ------------------------------------------------------------------ sensores (cada 5 s, sin bloquear)
static void sensoresPaso(uint32_t ms) {
  if (ms - st.ultSensores >= SENSORES_PERIODO_MS) {
    st.ultSensores = ms;
    sensores::ahtDisparar();
    sensores::sondaDisparar();
  }
  float t, h;
  if (sensores::ahtLeer(t, h)) {
    st.tAmb = t;
    st.hum = h;
    st.ambUltima = ms;
  }
  if (sensores::sondaLeer(t)) {
    st.tSonda = t;
    st.sondaUltima = ms;
  }
}

// ------------------------------------------------------------------ horario
static bool enHorario() {
  if (!cfg.horario_on || cfg.n_vent == 0) return true;
  uint32_t t = ahora();
  if (!t) return true;  // sin hora no se aplica el horario (queda la alarma de «sin hora»)
  int64_t local = (int64_t)t + (int64_t)cfg.tz_min * 60;
  int dow = (int)(((local / 86400) + 4) % 7);
  int min = (int)((local % 86400) / 60);
  for (int k = 0; k < cfg.n_vent && k < 4; k++) {
    const Ventana &w = cfg.vent[k];
    if (w.ini < w.fin) {
      if ((w.dias >> dow & 1) && min >= w.ini && min < w.fin) return true;
    } else {  // cruza la medianoche
      if ((w.dias >> dow & 1) && min >= w.ini) return true;
      int ayer = (dow + 6) % 7;
      if ((w.dias >> ayer & 1) && min < w.fin) return true;
    }
  }
  return false;
}

// ------------------------------------------------------------------ botón PARAR
static void IRAM_ATTR isrParar() { pulsoParar = true; }

static void boton(uint32_t ms) {
  bool crudo = digitalRead(pin::PARAR) == LOW;
  bool flanco = pulsoParar;
  pulsoParar = false;
  if (crudo != st.btnCrudo) {
    st.btnCrudo = crudo;
    st.btnCambio = ms;
  }
  bool nuevaPulsacion = false;
  if (crudo != st.btnEstable && ms - st.btnCambio >= PARAR_ANTIRREBOTE_MS) {
    st.btnEstable = crudo;
    if (crudo) nuevaPulsacion = true;
  } else if (flanco && !st.btnEstable && !crudo) {
    nuevaPulsacion = true;  // pulsación corta entre dos lecturas del lazo
  }
  if (nuevaPulsacion) {
    st.btnDesde = ms;
    st.btnLargoHecho = false;
    st.btnEraEnclavado = per.parar;
    if (!per.parar) {
      per.parar = true;
      guardar();
      evento(E_ORDEN, 2, 1 /* PARAR pulsado */);
    }
  }
  if (st.btnEstable && !st.btnLargoHecho && st.btnEraEnclavado && ms - st.btnDesde >= PARAR_LARGO_MS) {
    st.btnLargoHecho = true;
    per.parar = false;
    guardar();
    evento(E_ORDEN, 0, 2 /* PARAR soltado en la placa */);
  }
}

// ------------------------------------------------------------------ protecciones y K1
static void disparoTemp(bool &trip, uint32_t &bajoDesde, bool ok, float t, float tmax, uint32_t ms) {
  if (ok && t >= tmax) {
    if (!trip) {
      trip = true;
      per.temp_disparos++;
      if (per.temp_disparos >= TEMP_DISPAROS_MAX) st.tempEnclavada = true;
      guardar();
    }
    bajoDesde = 0;
  } else if (trip) {
    bool frio = !ok || t <= tmax - cfg.t_hist;
    if (frio) {
      if (!bajoDesde) bajoDesde = ms;
      if (ms - bajoDesde >= TEMP_ESPERA_MS && !st.tempEnclavada) trip = false;
    } else {
      bajoDesde = 0;
    }
  }
}

static void evaluar(uint32_t ms) {
  bool sondaOk = st.sondaUltima && ms - st.sondaUltima < SONDA_FALLA_MS;
  bool ambOk = st.ambUltima && ms - st.ambUltima < 20000;
  uint32_t refSonda = st.sondaUltima ? st.sondaUltima : st.t0;
  bool sondaFalla = cfg.sonda_req && ms - refSonda >= SONDA_FALLA_MS;
  uint32_t refAmb = st.ambUltima ? st.ambUltima : st.t0;
  bool ambFalla = ms - refAmb >= 30000;

  disparoTemp(st.tripS, st.bajoSDesde, sondaOk, st.tSonda, cfg.tmax_sonda, ms);
  disparoTemp(st.tripA, st.bajoADesde, ambOk, st.tAmb, cfg.tmax_amb, ms);

  // Red baja: solo con el medidor calibrado (con las ganancias de fábrica la lectura no es confiable).
  if (cal.calibrada && st.medOk) {
    float v = st.med.v;
    if (v < cfg.vnom * RED_BAJA_FRACCION) {
      if (!st.redBajaDesde) st.redBajaDesde = ms;
      if (ms - st.redBajaDesde >= RED_BAJA_MS) st.redBaja = true;
      st.redOkDesde = 0;
    } else {
      st.redBajaDesde = 0;
      if (st.redBaja && v >= cfg.vnom * 0.85f) {
        if (!st.redOkDesde) st.redOkDesde = ms;
        if (ms - st.redOkDesde >= RED_OK_MS) st.redBaja = false;
      } else {
        st.redOkDesde = 0;
      }
    }
  } else if (!cal.calibrada) {
    st.redBaja = false;
  }

  if (!st.arranqueHecho && cfg.arranque != ARR_DETENIDA && ms - st.t0 >= ARRANQUE_ESPERA_MS) st.arranqueHecho = true;

  // Alarmas activas.
  uint32_t al = 0;
  if (st.tripS) al |= A_TEMP_SONDA;
  if (st.tripA) al |= A_TEMP_AMB;
  if (sondaFalla) al |= A_SONDA_FALLA;
  if (st.medFalla) al |= A_MEDIDOR;
  if (st.redBaja) al |= A_RED;
  if (per.parar) al |= A_PARAR;
  if (ambFalla) al |= A_AMB_FALLA;
  if (!ahora() && ms - st.t0 > 60000) al |= A_SIN_HORA;
  if (st.reinicioAnormal || st.bloqueoReinicios) al |= A_REINICIO;
  if (!cal.calibrada) al |= A_SIN_CALIBRAR;
  if (sondaOk && !st.tripS && st.tSonda >= cfg.tmax_sonda - 10) al |= A_TEMP_AVISO;

  uint32_t nuevas = al & ~st.alarmas, idas = st.alarmas & ~al;
  for (int b = 0; b < N_ALARMAS; b++) {
    float medida = (b == 0 || b == 10) ? st.tSonda : (b == 1 ? st.tAmb : (b == 4 ? st.med.v : 0));
    if (nuevas >> b & 1) evento(E_ALARMA, (ALARMAS_GRAVES >> b & 1) ? 2 : 1, (float)b, (uint32_t)lroundf(medida * 10));
    if (idas >> b & 1) evento(E_ALARMA_FIN, 0, (float)b);
  }
  st.sinReconocer |= nuevas & ALARMAS_GRAVES;
  st.alarmas = al;

  // Motivo de detención, por prioridad.
  uint8_t mot = M_NINGUNO;
  if (st.medFalla || sondaFalla || st.bloqueoReinicios) mot = M_FALLA;
  else if (st.tripS || st.tripA) mot = M_TEMP;
  else if (per.parar) mot = M_PARAR;
  else if (st.redBaja) mot = M_RED;
  else if (per.limite) mot = M_LIMITE;
  else if (!enHorario()) mot = M_HORARIO;
  else if (!st.arranqueHecho) mot = M_ARRANQUE;
  else if (!per.permiso) mot = M_APP;

  bool k1 = mot == M_NINGUNO;
  digitalWrite(pin::RELAY_EN, k1 ? HIGH : LOW);  // se reescribe siempre, por si acaso
  if (k1 != st.k1) {
    st.k1 = k1;
    st.motivo = mot;
    evento(E_K1, 0, k1 ? 1 : 0, mot);
    muestra();
  } else if (mot != st.motivo) {
    st.motivo = mot;
  }
}

// ------------------------------------------------------------------ LEDs
static void leds(uint32_t ms) {
  uint32_t fase = st.tick++;
  bool lento = (fase / 2) % 2;   // 1 Hz con el lazo de 250 ms
  bool rapido = fase % 2;        // 2 Hz
  switch (estadoRed) {
    case RED_SERVIDOR: digitalWrite(pin::LED_WIFI, HIGH); break;
    case RED_WIFI: digitalWrite(pin::LED_WIFI, lento); break;
    case RED_PORTAL: digitalWrite(pin::LED_WIFI, rapido); break;
    default: digitalWrite(pin::LED_WIFI, LOW);
  }
  bool corriente = st.medOk && st.med.i >= cfg.i_inicio;
  digitalWrite(pin::LED_CARGA, st.k1 ? (corriente ? HIGH : (fase % 8 < 2)) : LOW);
  bool grave = st.motivo == M_FALLA || st.motivo == M_TEMP;
  bool falla = grave ? true : (per.parar ? rapido : (st.sinReconocer ? lento : false));
  digitalWrite(pin::LED_FALLA, falla);
}

// ------------------------------------------------------------------ órdenes
static void responder(const Orden &o, bool ok, const char *fmt, ...) {
  Respuesta r;
  strlcpy(r.id, o.id, sizeof(r.id));
  r.ok = ok;
  va_list ap;
  va_start(ap, fmt);
  vsnprintf(r.msg, sizeof(r.msg), fmt, ap);
  va_end(ap);
  if (r.id[0]) xQueueSend(colaRespuestas, &r, 0);
  Serial.printf("[orden] %s: %s\n", ok ? "ok" : "error", r.msg);
}

static void procesarOrdenes() {
  Orden o;
  while (xQueueReceive(colaOrdenes, &o, 0) == pdTRUE) {
    switch (o.tipo) {
      case O_PERMITIR:
        per.permiso = true;
        per.limite = false;
        st.arranqueHecho = true;
        guardar();
        responder(o, true, per.parar ? "permitida, pero PARAR sigue enclavado" : "carga permitida");
        break;
      case O_DETENER:
        per.permiso = false;
        guardar();
        responder(o, true, "carga detenida");
        break;
      case O_RECONOCER:
        st.sinReconocer = 0;
        st.reinicioAnormal = false;
        st.bloqueoReinicios = false;
        st.tempEnclavada = false;
        per.temp_disparos = 0;
        rtcReinicios = 0;
        guardar();
        responder(o, true, "alarmas reconocidas");
        break;
      case O_PARAR_SOLTAR:
        per.parar = false;
        guardar();
        evento(E_ORDEN, 0, 3 /* PARAR soltado desde la app */);
        responder(o, true, "PARAR liberado");
        break;
      case O_CONFIG: {
        uint16_t vnomAntes = cfg.vnom;
        almacen::configLeer(cfg);
        if (cfg.vnom != vnomAntes) aplicarCalibracion(cal);  // el umbral de sag depende de la nominal
        evento(E_CONFIG, 0, (float)cfg.version);
        responder(o, true, "configuración %lu aplicada", (unsigned long)cfg.version);
        break;
      }
      case O_CAL_ESCRIBIR: {
        Calibracion n = o.cal;
        if (aplicarCalibracion(n)) {
          cal = n;
          almacen::calGuardar(cal);
          evento(E_CAL, 1, 0);
          responder(o, true, "calibración aplicada (Ugain %04X, IgainN %04X)", cal.ugain, cal.igain_n);
        } else {
          aplicarCalibracion(cal);
          responder(o, false, "el ATM90E26 rechazó la calibración (CalErr/AdjErr); se dejó la anterior");
        }
        break;
      }
      case O_CAL_AUTO: {
        if (!st.medOk) {
          responder(o, false, "sin medición del ATM90E26");
          break;
        }
        Calibracion n = cal;
        if (o.a > 0) {
          if (st.med.v < 20) {
            responder(o, false, "tensión medida %.1f V: muy baja para calibrar", st.med.v);
            break;
          }
          long g = lround(n.ugain * (double)o.a / st.med.v);
          if (g <= 0 || g > 0x7FFF) {
            responder(o, false, "Ugain calculado fuera de rango (%ld)", g);
            break;
          }
          n.ugain = (uint16_t)g;
        }
        if (o.b > 0) {
          if (st.med.i < 0.5f) {
            responder(o, false, "corriente medida %.3f A: muy baja para calibrar (≥ 0,5 A)", st.med.i);
            break;
          }
          long g = lround(n.igain_n * (double)o.b / st.med.i);
          if (g <= 0 || g > 0xFFFF) {
            responder(o, false, "IgainN calculado fuera de rango (%ld)", g);
            break;
          }
          n.igain_n = (uint16_t)g;
        }
        n.calibrada = true;
        if (aplicarCalibracion(n)) {
          cal = n;
          almacen::calGuardar(cal);
          evento(E_CAL, 1, 1);
          responder(o, true, "Ugain %u (%04XH), IgainN %u (%04XH)", cal.ugain, cal.ugain, cal.igain_n, cal.igain_n);
        } else {
          aplicarCalibracion(cal);
          responder(o, false, "el ATM90E26 rechazó la calibración");
        }
        break;
      }
      case O_CAL_FABRICA:
        calibracionPorDefecto(cal);
        almacen::calGuardar(cal);
        aplicarCalibracion(cal);
        evento(E_CAL, 1, 2);
        responder(o, true, "calibración de fábrica");
        break;
      default:
        responder(o, false, "orden desconocida");
    }
  }
}

// ------------------------------------------------------------------ foto para la red
static void publicar(uint32_t ms) {
  Instantanea s;
  s.ts = ahora();
  s.hora_ok = s.ts != 0;
  s.med_ok = st.medOk;
  s.v = st.med.v;
  s.i = st.med.i;
  s.p = st.med.p;
  s.pf = st.med.pf;
  s.f = st.med.f;
  s.sys_status = st.med.sys;
  s.e_ses_kwh = per.e_ses_kwh;
  s.e_tot_kwh = per.e_tot_kwh;
  s.ses_num = per.ses_num;
  s.ses_ini = per.ses_ini;
  s.ses_dur_s = per.ses_dur_s;
  s.p_max = per.p_max;
  s.t_sonda = st.tSonda;
  s.sonda_ok = st.sondaUltima && ms - st.sondaUltima < SONDA_FALLA_MS;
  s.t_amb = st.tAmb;
  s.hum = st.hum;
  s.amb_ok = st.ambUltima && ms - st.ambUltima < 20000;
  s.k1 = st.k1;
  s.permiso = per.permiso;
  s.motivo = st.motivo;
  s.alarmas = st.alarmas;
  s.sin_reconocer = st.sinReconocer;
  s.uptime_s = ms / 1000;
  s.btn = st.btnEstable;
  s.btn_rearma = st.btnEstable && st.btnEraEnclavado && !st.btnLargoHecho;
  s.btn_ms = st.btnEstable ? ms - st.btnDesde : 0;
  xSemaphoreTake(mtxEstado, portMAX_DELAY);
  snap = s;
  xSemaphoreGive(mtxEstado);
}

// ------------------------------------------------------------------ tarea
static void tarea(void *) {
  esp_task_wdt_add(nullptr);
  TickType_t prox = xTaskGetTickCount();
  for (;;) {
    uint32_t ms = millis();
    procesarOrdenes();
    boton(ms);
    if (ms - st.ultMedicion >= MEDICION_PERIODO_MS) medir(ms);
    sensoresPaso(ms);
    if (pedirRtc) {
      pedirRtc = false;
      uint32_t t = ahora();
      if (t && sensores::rtcEscribir(t)) evento(E_HORA, 0, 0);
    }
    evaluar(ms);
    leds(ms);
    publicar(ms);
    uint32_t periodo = (per.ses_num || (st.k1 && st.medOk && st.med.i >= cfg.i_inicio)) ? cfg.reg_carga_s : cfg.reg_reposo_s;
    if (ms - st.ultRegistro >= periodo * 1000UL) {
      st.ultRegistro = ms;
      muestra();
    }
    if (ms - st.ultNvs >= NVS_ENERGIA_PERIODO_MS) guardar();
    esp_task_wdt_reset();
    vTaskDelayUntil(&prox, pdMS_TO_TICKS(CONTROL_PERIODO_MS));
  }
}

void begin(esp_reset_reason_t motivoReset) {
  mtxEstado = xSemaphoreCreateMutex();
  mtxAtm = xSemaphoreCreateMutex();
  colaOrdenes = xQueueCreate(8, sizeof(Orden));
  colaRespuestas = xQueueCreate(8, sizeof(Respuesta));
  memset(&st, 0, sizeof(st));
  memset(&snap, 0, sizeof(snap));

  pinMode(pin::RELAY_EN, OUTPUT);
  digitalWrite(pin::RELAY_EN, LOW);
  for (int p : {pin::LED_WIFI, pin::LED_CARGA, pin::LED_FALLA}) {
    pinMode(p, OUTPUT);
    digitalWrite(p, LOW);
  }
  pinMode(pin::PARAR, INPUT);  // pull-up externo R27
  attachInterrupt(digitalPinToInterrupt(pin::PARAR), isrParar, FALLING);

  almacen::configLeer(cfg);
  almacen::calLeer(cal);
  almacen::estadoLeer(per);

  sensores::begin();
  delay(30);  // AHT20: ≥ 25 ms después del arranque
  horaDesdeRtc();
  atm::begin();
  if (!aplicarCalibracion(cal)) Serial.println("[control] el ATM90E26 no quedó configurado (se reintenta)");

  // Reinicios anormales: alarma hasta reconocer; tres en menos de 10 min dejan la carga detenida.
  bool anormal = motivoReset == ESP_RST_PANIC || motivoReset == ESP_RST_INT_WDT || motivoReset == ESP_RST_TASK_WDT ||
                 motivoReset == ESP_RST_WDT || motivoReset == ESP_RST_BROWNOUT;
  if (rtcMagia != RTC_MAGIA || motivoReset == ESP_RST_POWERON) {
    rtcMagia = RTC_MAGIA;
    rtcReinicios = 0;
  }
  if (anormal) rtcReinicios++;
  st.reinicioAnormal = anormal;
  st.bloqueoReinicios = rtcReinicios >= 3;
  if (st.reinicioAnormal) st.sinReconocer |= A_REINICIO;

  // Política de arranque de K1 (P3 con el AQY214EHAX: sin energía, el EVSE no carga).
  if (cfg.arranque == ARR_PERMITIDA) per.permiso = true;
  st.arranqueHecho = false;
  st.k1 = false;
  st.motivo = M_ARRANQUE;

  uint32_t ms = millis();
  st.t0 = ms;
  st.ultMedicion = ms;
  st.medBuenaUltima = ms;
  st.ultimaCorriente = ms;
  st.ultNvs = ms;
  st.ultRegistro = ms;
  st.ultSensores = ms - SENSORES_PERIODO_MS;

  evento(E_ARRANQUE, st.reinicioAnormal ? 2 : 0, (float)motivoReset, rtcReinicios);
  xTaskCreatePinnedToCore(tarea, "control", 8192, nullptr, 3, nullptr, 1);
}

void instantanea(Instantanea &s) {
  xSemaphoreTake(mtxEstado, portMAX_DELAY);
  s = snap;
  xSemaphoreGive(mtxEstado);
}

void configActual(Config &c) { almacen::configLeer(c); }
void calActual(Calibracion &c) { almacen::calLeer(c); }
bool enviarOrden(const Orden &o) { return xQueueSend(colaOrdenes, &o, pdMS_TO_TICKS(100)) == pdTRUE; }
bool respuesta(Respuesta &r) { return xQueueReceive(colaRespuestas, &r, 0) == pdTRUE; }
void ponerEstadoRed(EstadoRed e) { estadoRed = e; }

void registrosAtm(uint16_t *out, const uint8_t *dirs, int n) {
  xSemaphoreTake(mtxAtm, portMAX_DELAY);
  for (int k = 0; k < n; k++) out[k] = atm::leer(dirs[k]);
  xSemaphoreGive(mtxAtm);
}

}  // namespace control
