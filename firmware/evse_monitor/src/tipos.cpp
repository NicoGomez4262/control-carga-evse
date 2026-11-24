#include "tipos.h"

const char *motivoTexto(uint8_t m) {
  switch (m) {
    case M_NINGUNO: return "";
    case M_FALLA: return "falla";
    case M_TEMP: return "temperatura";
    case M_PARAR: return "parar";
    case M_RED: return "red";
    case M_LIMITE: return "limite";
    case M_HORARIO: return "horario";
    case M_APP: return "app";
    case M_ARRANQUE: return "arranque";
    default: return "?";
  }
}

static const char *CODIGOS[N_ALARMAS] = {
    "temp_sonda", "temp_amb", "sonda_falla", "medidor_falla", "red_baja", "parar",
    "amb_falla",  "sin_hora", "reinicio",    "sin_calibrar",  "temp_aviso",
};
static const char *TEXTOS[N_ALARMAS] = {
    "Sobretemperatura en la sonda",
    "Sobretemperatura en la placa",
    "Sonda DS18B20 sin respuesta",
    "Falla del medidor ATM90E26",
    "Tensión de red baja",
    "PARAR pulsado",
    "Sensor de ambiente sin respuesta",
    "Sin hora (sin NTP ni RTC)",
    "Reinicio inesperado",
    "Medidor sin calibrar",
    "Sonda cerca del límite de temperatura",
};

const char *alarmaCodigo(int bit) { return (bit >= 0 && bit < N_ALARMAS) ? CODIGOS[bit] : "?"; }
const char *alarmaTexto(int bit) { return (bit >= 0 && bit < N_ALARMAS) ? TEXTOS[bit] : "?"; }

const char *eventoCodigo(uint16_t e) {
  switch (e) {
    case E_ARRANQUE: return "arranque";
    case E_K1: return "k1";
    case E_ALARMA: return "alarma";
    case E_ALARMA_FIN: return "alarma_fin";
    case E_SESION_INICIO: return "sesion_inicio";
    case E_LIMITE: return "limite";
    case E_CONFIG: return "config";
    case E_CAL: return "calibracion";
    case E_ORDEN: return "orden_local";
    case E_OTA: return "ota";
    case E_HORA: return "hora";
    default: return "evento";
  }
}

void configPorDefecto(Config &c) {
  memset(&c, 0, sizeof(c));
  c.version = 0;
  c.vnom = 120;
  c.tarifa = 900.0f;
  c.tz_min = -300;
  c.tmax_sonda = 60.0f;
  c.tmax_amb = 60.0f;
  c.t_hist = 10.0f;
  c.sonda_req = true;
  c.arranque = ARR_RESTAURAR;
  c.lim_kwh = 0;
  c.lim_min = 0;
  c.lim_cop = 0;
  c.horario_on = false;
  c.n_vent = 0;
  c.i_inicio = 1.0f;
  c.fin_min = 10;
  c.inv_ct = false;
  c.tel_s = 15;
  c.reg_carga_s = 30;
  c.reg_reposo_s = 300;
}

// Valores de encendido del datasheet (Atmel-46002B), salvo MMode: LNSel = 0 porque el CT entra por I2.
void calibracionPorDefecto(Calibracion &c) {
  c.plconst_h = 0x0015;
  c.plconst_l = 0xD174;
  c.lgain = 0;
  c.lphi = 0;
  c.ngain = 0;
  c.nphi = 0;
  c.pstart = 0x08BD;
  c.pnol = 0;
  c.qstart = 0x0AEC;
  c.qnol = 0;
  c.mmode = 0x9022;  // 9422H con LNSel (bit 10) = 0 → mide la línea N (I2)
  c.ugain = 0x6720;
  c.igain_l = 0x7A13;
  c.igain_n = 0x7530;
  c.uoffset = 0;
  c.ioffset_l = 0;
  c.ioffset_n = 0;
  c.poffset_l = 0;
  c.qoffset_l = 0;
  c.poffset_n = 0;
  c.qoffset_n = 0;
  c.calibrada = false;
}
