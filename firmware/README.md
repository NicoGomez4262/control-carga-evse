# Firmware del EVSE Monitor (ESP32-S3)

Dos proyectos de PlatformIO (Arduino-ESP32 2.0.17). Se abre cada carpeta por separado en VS Code.

| Carpeta | Para qué |
|---|---|
| [`prueba_placa/`](prueba_placa/) | Menú por consola para las pruebas S1–S6 de la placa (`docs/pruebas/PROTOCOLO_PRUEBAS.md`) |
| [`evse_monitor/`](evse_monitor/) | Firmware final: medición, protecciones, K1, búfer sin internet, conexión a la app y OTA |

Cómo compilar, subir y usar cada uno: [`docs/software/GUIA_INSTALACION.md`](../docs/software/GUIA_INSTALACION.md).
Cómo está hecho: [`docs/software/ARQUITECTURA.md`](../docs/software/ARQUITECTURA.md).

`evse_monitor/include/secrets.h` (opcional, fuera de git) se crea copiando `secrets.example.h`.
