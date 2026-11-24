// EVSE Monitor — constantes de la placa Rev 1.0 y valores por defecto.
#pragma once
#include <Arduino.h>

#define FW_VERSION "1.0.0"
#define FW_NOMBRE "evse_monitor"

// ---------------------------------------------------------------- pines (mapa de F4, docs/DECISIONES.md)
namespace pin {
constexpr int MEAS_CS = 10;
constexpr int MEAS_MOSI = 11;
constexpr int MEAS_SCK = 12;
constexpr int MEAS_MISO = 13;
constexpr int MEAS_IRQ = 14;
constexpr int MEAS_WARN = 21;
constexpr int MEAS_ZX = 17;
constexpr int SDA = 8;
constexpr int SCL = 9;
constexpr int OW = 4;
constexpr int RTC_INT = 18;
constexpr int RELAY_EN = 5;    // K1 = AQY214EHAX (NA): 1 = J2 cerrado = carga permitida
constexpr int LED_WIFI = 6;    // LED3 verde
constexpr int LED_CARGA = 7;   // LED4 verde
constexpr int LED_FALLA = 15;  // LED5 rojo
constexpr int PARAR = 16;      // SW1 y J7, activo en bajo
}  // namespace pin

// ---------------------------------------------------------------- tiempos de las tareas
constexpr uint32_t CONTROL_PERIODO_MS = 250;      // lazo de control (botón, K1, LEDs)
constexpr uint32_t MEDICION_PERIODO_MS = 1000;    // ATM90E26 y energía
constexpr uint32_t SENSORES_PERIODO_MS = 5000;    // DS18B20 y AHT20
constexpr uint32_t NVS_ENERGIA_PERIODO_MS = 60000;  // D14: energía en NVS cada minuto
constexpr uint32_t WDT_SEGUNDOS = 30;             // watchdog de tareas (la descarga OTA lo alimenta)

// ---------------------------------------------------------------- protecciones
constexpr uint32_t PARAR_ANTIRREBOTE_MS = 50;
constexpr uint32_t PARAR_LARGO_MS = 3000;        // pulsación larga: suelta el enclavamiento de PARAR
constexpr uint32_t PARAR_PORTAL_MS = 5000;       // PARAR pulsado al arrancar: portal de configuración
constexpr uint32_t SONDA_FALLA_MS = 30000;       // sin lectura de la sonda durante este tiempo = falla
constexpr uint32_t MEDIDOR_FALLA_MS = 5000;      // ATM90E26 sin responder o con CalErr
constexpr uint32_t RED_BAJA_MS = 3000;           // tensión < 70 % de la nominal durante este tiempo
constexpr uint32_t RED_OK_MS = 60000;            // tensión normal durante este tiempo para volver a cargar
constexpr uint32_t TEMP_ESPERA_MS = 5UL * 60000;  // enfriado por debajo de la histéresis este tiempo
constexpr uint8_t TEMP_DISPAROS_MAX = 3;         // disparos por temperatura en una sesión antes de enclavar
constexpr float RED_BAJA_FRACCION = 0.70f;
constexpr uint32_t ARRANQUE_ESPERA_MS = 10000;   // verificaciones antes de restaurar K1

// ---------------------------------------------------------------- red
constexpr uint16_t SERVIDOR_PUERTO = 443;
constexpr const char *SERVIDOR_RUTA_WS = "/api/dispositivo/ws";
constexpr const char *SERVIDOR_RUTA_FW = "/api/dispositivo/firmware/";
constexpr uint32_t PING_PERIODO_MS = 30000;
constexpr uint32_t SIN_DATOS_MS = 75000;         // sin nada del servidor: reconectar
constexpr uint32_t TEL_VIVO_MS = 2000;           // telemetría con la app abierta
constexpr int REG_LOTE = 20;                     // registros por mensaje «reg»
constexpr const char *NTP_1 = "pool.ntp.org";
constexpr const char *NTP_2 = "time.google.com";
constexpr uint32_t PORTAL_DURACION_MS = 10UL * 60000;
