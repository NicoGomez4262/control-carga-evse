// EVSE Monitor Rev 1.0 — firmware final (Fase 10D).
//
// Dos tareas:
//   · control (prioridad 3): ATM90E26, sensores, energía, sesiones, protecciones, K1, LEDs y PARAR.
//     No depende de la red: las protecciones funcionan sin internet.
//   · loop de Arduino (prioridad 1): WiFi, WebSocket con TLS hacia la app, búfer, OTA, portal y consola.
// Las dos alimentan el watchdog de tareas (30 s).

#include <Arduino.h>
#include <esp_ota_ops.h>
#include <esp_task_wdt.h>
#include "almacen.h"
#include "config.h"
#include "consola.h"
#include "control.h"
#include "portal.h"
#include "red.h"

static void watchdog() {
#if ESP_IDF_VERSION_MAJOR >= 5
  esp_task_wdt_config_t c = {.timeout_ms = WDT_SEGUNDOS * 1000, .idle_core_mask = 0, .trigger_panic = true};
  if (esp_task_wdt_reconfigure(&c) != ESP_OK) esp_task_wdt_init(&c);
#else
  esp_task_wdt_init(WDT_SEGUNDOS, true);
#endif
  esp_task_wdt_add(nullptr);  // la tarea de loop
}

// Si un firmware nuevo no llega al servidor y se reinicia más de 3 veces, se vuelve al anterior.
static void revisarOta() {
  if (!almacen::otaPendiente()) return;
  almacen::arranquesOtaSumar();
  uint8_t n = almacen::arranquesOta();
  Serial.printf("[ota] firmware nuevo sin confirmar, arranque %u de 3\n", n);
  if (n > 3) {
    const esp_partition_t *otra = esp_ota_get_next_update_partition(nullptr);
    if (otra && esp_ota_set_boot_partition(otra) == ESP_OK) {
      Serial.println("[ota] se vuelve al firmware anterior");
      almacen::otaMarcar(0);
      delay(200);
      ESP.restart();
    }
  }
}

// PARAR pulsado 5 s al encender = portal. Mientras tanto K1 sigue abierto.
static bool pararAlArrancar() {
  pinMode(pin::PARAR, INPUT);
  pinMode(pin::LED_WIFI, OUTPUT);
  if (digitalRead(pin::PARAR) != LOW) return false;
  Serial.println("[arranque] PARAR pulsado: mantenlo 5 s para abrir el portal");
  uint32_t t0 = millis();
  while (digitalRead(pin::PARAR) == LOW) {
    digitalWrite(pin::LED_WIFI, (millis() / 100) % 2);
    if (millis() - t0 >= PARAR_PORTAL_MS) {
      digitalWrite(pin::LED_WIFI, HIGH);
      uint32_t t1 = millis();
      while (digitalRead(pin::PARAR) == LOW && millis() - t1 < 10000) delay(10);  // esperar a que lo suelte
      return true;
    }
    delay(10);
  }
  digitalWrite(pin::LED_WIFI, LOW);
  return false;
}

void setup() {
  pinMode(pin::RELAY_EN, OUTPUT);
  digitalWrite(pin::RELAY_EN, LOW);  // K1 abierto hasta que el control decida
  Serial.begin(115200);
  delay(200);
  esp_reset_reason_t motivo = esp_reset_reason();
  Serial.println();
  Serial.println("EVSE Monitor " FW_VERSION " · " __DATE__);
  Serial.printf("Reset: %d · flash %u MB · PSRAM %u KB\n", (int)motivo, (unsigned)(ESP.getFlashChipSize() >> 20),
                (unsigned)(ESP.getPsramSize() >> 10));

  almacen::begin();
  if (!buffer::begin()) Serial.println("[buffer] ¡no está la partición «buffer»! (¿particiones.csv?)");
  Serial.printf("[buffer] registros %lu a %lu\n", (unsigned long)buffer::seqMin(), (unsigned long)buffer::seqMax());
  revisarOta();

  // Sin WiFi guardado NO se abre el portal solo: sin U1 (3,3 V en TP3 con 0,25 A) los picos del WiFi
  // tumbarían la fuente. El portal se abre a propósito: PARAR 5 s al encender o «portal» en la consola.
  bool abrirPortal = pararAlArrancar() || portal::pedidoAlReiniciar();

  watchdog();
  control::begin(motivo);
  if (abrirPortal)
    portal::begin();
  else
    red::begin();
  consola::ayuda();
  Serial.print("> ");
}

void loop() {
  if (portal::activo())
    portal::loop();
  else
    red::loop();
  consola::loop();
  esp_task_wdt_reset();
  delay(2);
}
