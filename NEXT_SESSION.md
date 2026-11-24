# Siguiente sesión → Fase 10 (continuación): firmware final + app en la placa real

La **Fase 9 se cerró el 24 nov** (`docs/sesiones/F9_cerrada.md`). La placa 1 pasó todo lo que se puede probar sin red: H0–H6 y S1–S6, más el canal de corriente. **10H va por la mitad:** el firmware final 1.0.0 ya está en la placa 1 y arranca bien (D33). Falta publicar la app en Firebase, enlazar la placa, probarla desde el celular, S7 con red y calibración (incluido el CT con corriente real en un solo conductor) y S8 de punta a punta.

## Prompt para iniciar

```text
Seguimos con "Control de carga EVSE" (repo público github.com/NicoGomez4262/control-carga-evse).
Objetivo: unir el firmware final (firmware/evse_monitor) con la app de Firebase y probarlo desde el
celular con la placa 1 en el banco (tarea 10H, sin red eléctrica todavía).

Antes de nada, lee: CLAUDE.md; NEXT_SESSION.md; docs/software/GUIA_INSTALACION.md (partes B y C);
docs/software/ARQUITECTURA.md y PROTOCOLO_MENSAJES.md; docs/DECISIONES.md (D21–D32 y el cierre de la
Fase 9); docs/pruebas/PROTOCOLO_PRUEBAS.md (el registro del 24 nov, al final).

Lo probado en la placa 1 el 24 nov con firmware/prueba_placa:
- H0–H6 aprobadas. U1 soldado. CH340C en COM8. Alimentación: SOLO 12 V en J6 (+ al 6 = J6-1,
  − al 7 = J6-2), límite 0,20 A; nunca 3,3 V en TP3. El USB solo programa y da la consola.
- S1 (LED3–LED5, SW1, SW2/SW3, botón de panel en J7), S2 (AHT20 0x38, DS3231 0x68 con hora puesta,
  1 Hz), S3 (DS18B20), S4 (K1/J2), S5 (ATM90E26 por SPI) y S6 (WiFi: 60 s sin reinicio, pico de
  75 mA en la fuente) aprobadas.
- ATM90E26: WarnOut (IO21) e IRQ (IO14) son ACTIVOS EN ALTO. Al encender no marca CalErr con 8765H si
  no se ha escrito CS1; con una CS1 equivocada sí (SysStatus C000H). La CS1 de fábrica es 55CBH.
- Canal de corriente aprobado sin red (`s5 inyectar`: I2 de 0,008 a 2,985 A); con las ganancias de
  fábrica lee ≈ 1,8 veces la corriente real. Falta el CT con corriente real en UN SOLO conductor
  (un cable entero se anula). S7 (red y calibración) no se ha hecho: en el banco U = 0 e I = 0 y el
  medidor queda «sin calibrar»; es normal (la protección de red baja solo actúa calibrado).

Ya hecho (24 nov, D33): código de enlace, rutas y reglas cotejados entre la app y el firmware; CS1
antes de 8765H; tabla de particiones corregida; evse_monitor 1.0.0 subido a la placa 1 (flash borrada)
y arrancando sin errores. En el último arranque PARAR salió enclavado: [di si lo pulsaste].

Qué quiero, en este orden:
1. Estado de la app: [di si ya la publicaste en Firebase (guía B) y su dirección .web.app]; si no,
   guíame a publicarla (la CLI de Firebase tenía la sesión vencida: `npx firebase login --reauth`).
   Mi cuenta, `admins` y el equipo evse-01. El código de enlace lo copio yo: no va a git ni al chat.
2. Con la placa conectada (12 V en J6 y USB en COM8; pio en ~/.platformio/penv/Scripts/pio.exe;
   COM8 lo usa una sola sesión): yo escribo en la consola `wifi "RED" CLAVE`, `enlazar EVSE1.…` y
   `reiniciar`; Claude no escribe claves. La sonda está puesta (lee ≈ 25 °C): no hace falta
   `sonda 0`. Decido D28 (arranque de K1) en Ajustes.
3. Verificar desde el celular: LED3 fijo y «En línea»; datos en vivo (sonda y AHT20; U e I en 0);
   Detener/Permitir con Ω entre el 17 (J2-1) y el 18 (J2-2) → OL / 25–40 Ω y LED6; PARAR (SW1 o J7)
   abre K1 y se ve en la app; sonda sobre tmax (bajar tmax en Ajustes) abre K1; cortar el hotspot y
   comprobar que las protecciones siguen y que el historial se completa al volver; configuración
   empujada y confirmada; OTA 1.0.0 → 1.0.1. Mirar también la humedad del AHT20 (salió en 0 %).
4. Si consigo un cable dúplex: CT en un solo hilo con la estación de aire caliente enchufada; la
   corriente sale en `estado` y en la app (≈ 1,8 veces la real hasta calibrar).
5. Anotar cada resultado en el registro de PROTOCOLO_PRUEBAS.md (S8 parcial, sin red), registrar
   decisiones en DECISIONES.md, actualizar NEXT_SESSION.md y subir con
   `python docs/tools/sincronizar_altium.py --commit -m "..."` (sin coautor).

Reglas: COM8 lo usa una sola sesión a la vez. Nada de claves del WiFi, códigos de enlace ni tokens en
git ni en el chat. En cada prueba, dime qué conectar con los números del mapa y su pin de Altium.
```

## Qué se hizo (24 nov, 10H primera parte)

- **Cotejo app ↔ firmware:** el código de enlace (`EVSE1.` + base64url de `{d,k,e,c}`) es igual en `app/public/fb.js` y `almacen.cpp`. Las 13 rutas que usa el equipo están permitidas por `database.rules.json`, y los campos de `estado` y de la configuración coinciden con la app.
- **Corregido (D33):** (1) `particiones.csv`. PlatformIO sube la app en 0x10000 y `boot_app0` en 0xE000, y la tabla ponía `app0` en 0x20000, así que el bootloader quedaba en bucle. Ahora la NVS de 64 KB va en 0x810000. (2) Un `sonda`/`tension` hecho sin conexión se mezcla con la configuración de la nube en vez de quedar con la misma versión. (3) Ya no salen avisos `[E]` de NVS vacía.
- Comentarios de S5-4 en el firmware final (WarnOut e IRQ activos en alto; CS1 antes de 8765H).
- **`evse_monitor` 1.0.0 en la placa 1** (flash borrada). Compila sin advertencias (1.079.381 bytes). En el arranque: hora del DS3231, sonda 25,4 °C, AHT20 28,3 °C con 0 %HR, ATM90E26 en 8765H sin CalErr, «sin calibrar», sin WiFi. En el último arranque PARAR salió enclavado; se suelta con 3 s de SW1/J7 o `soltar_parar`.
- La app **no está publicada** todavía: no hay `app/.firebaserc` y la sesión de la CLI de Firebase estaba vencida (401). Guía B, paso 5, ahora explica `login --reauth`.

## Qué se hizo (24 nov, cierre de la Fase 9)

- U1 soldado; H0 (lupa), H4, H5 y H6 aprobadas. SW2/SW3 (KFC-A04-02) soldados y el SW730RD cableado a J7.
- `firmware/prueba_placa` subido por Claude a COM8 y **S1–S6 aprobadas** (detalle en el registro del protocolo).
- S5-4: WarnOut e IRQ **activos en alto**; la prueba ahora escribe una CS1 equivocada (al encender, el chip no marca error sin ella).
- Canal de corriente probado sin red con `s5 inyectar` (IO0 → 1 kΩ → D4-2): I2 de 0,008 a 2,985 A.
- Firmware de pruebas corregido: CR + LF del monitor, comillas y red guardada en `s6 con` (`s6 olvidar`), ritmo de `s6 carga`, `s2 aht` de 20 s con la trama.
- Cierre de la Fase 9: PLAN_FASES, DECISIONES (con notas para la Rev 1.1) y etiqueta `rev1.0`.

## Dónde estamos

<!--DIAG:ALL-->
```text
MAPA GENERAL · cada bloque indica la fase en que se diseña

EXTERNO · instalación (fuera de la PCB)
  [Breaker del EVSE] ─┬─► [F3 CT en L1] ─► [EVSE] ─► [Vehículo]
                      │         │           ▲  │
                      └─► J1    └─► J3      │  └─ sonda DS18B20 ─► J4
                                            └─ J2 (bornes de habilitación)
════════════════════════════════════════════════════════════════════════════════════════════════════════════════
PCB        ZONA RED · 120–240 VAC                     ┃ BARRERA  ┃      ZONA SELV · 12 V y 3.3 V
                                                      ┃ ≥ 6.4 mm ┃
                                                      ┃          ┃
 ENERGÍA   J1 ─► [F2 Protección] ─┬───────────────────┨  AC-DC   ┠─► [F2 Riel 12 V] ─► [F2 R-78CK + LC] ─► 3V3
                                  │                   ┃   (F2)   ┃
 MEDICIÓN V                       └─► [F3 Divisor] ───┨  AMC3330 ┠─► V ─► [F3 ATM90E26] ═SPI═► ESP32-S3
                                                      ┃   (F3)   ┃              ▲ I
 MEDICIÓN I                                           ┃          ┃              └─◄ [F3 Carga CT] ◄─ J3
                                                      ┃          ┃
 ACTUACIÓN J2 ◄── contacto seco (aislado) ────────────┨ PhotoMOS ┠◄─ LED ─ [F6 Driver K1] ◄─ GPIO ─ ESP32-S3
                                                      ┃   (F6)   ┃
 CONTROL                                              ┃          ┃   [F4 ESP32-S3] ─ WiFi ─► router ─► internet ─► app
 INTERFAZ                                             ┃          ┃ J5 ─► [F4 USB-C · USB-UART · auto-reset · LEDs] ─► ESP32-S3
 SENSORES                                             ┃          ┃ J4 ─► [F5 Sensores · RTC] ─► ESP32-S3
 BANCO                                                ┃          ┃ J6 ─► [F2 Entrada banco 12 V] ─► D2 ─► +VIN
════════════════════════════════════════════════════════════════════════════════════════════════════════════════
[F# bloque] fase en que se diseña · ▐bloque▌ se diseña en ESTA fase · ► carril con trabajo en esta fase
┃ ┃ barrera de aislamiento · ┨ ┠ componente que cruza la barrera (AC-DC, AMC3330, PhotoMOS K1)
│ L1/L2 (L/N en 120 V) con fusibles · J1–J6 conectores · J1 con cable largo a la línea · J2 contacto seco aislado
```
<!--/DIAG-->

```text
SOFTWARE (Fase 10) · ► ESTÁS AQUÍ: integración con la placa (10H)

[Placa: S1–S6 ✓ · canal I ✓] ─► [ESP32-S3: firmware final 1.0.0 ✓ ▐enlazar▌] ═TLS═► [Firebase ✓] ─► [App web ▐publicar▌] ─► celular
          ▲ ▐S7 red + cal · S8▌             │ protecciones locales ✓                       ▲                                  │
          └─────────────────────────────────┴─ NVS + búfer 7 MB + DS3231 ✓                 └────────── órdenes ◄─────────────────┘
```

## Tareas de la Fase 10 (software)

- [x] 10A · Arquitectura (D21–D32; Firebase desde el 24 nov). **Falta tu decisión de D28** (arranque de K1).
- [x] 10B · Firmware de pruebas (`firmware/prueba_placa`), corrido en la placa 1: S1–S6 aprobadas (24 nov).
- [x] 10C · Protocolo de mensajes.
- [x] 10D · Firmware final (`firmware/evse_monitor`).
- [x] 10E · Simulador del equipo.
- [x] 10F · Servidor y base de datos.
- [x] 10G · Aplicación web.
- [ ] 10H · Integración con la placa:
  - [x] S1–S6 con `firmware/prueba_placa`, U1 + H4 y el canal de corriente sin red (24 nov).
  - [ ] Publicar la app en Firebase (guía, parte B); tu cuenta, `admins` y el equipo `evse-01`.
  - [ ] Opcional: dominio `evse.nicolasgomez.dev` y bot de Telegram.
  - [x] Cotejar el enlace, las rutas y las reglas; borrar la flash y subir `firmware/evse_monitor` 1.0.0 (24 nov, D33).
  - [ ] `wifi` + `enlazar CÓDIGO`; LED3 fijo y «En línea» en la app.
  - [ ] Desde el celular, sin red: Detener/Permitir con J2 medido, PARAR, sonda caliente, sin internet, configuración, OTA 1.0.0 → 1.0.1.
  - [ ] CT con corriente real en un solo conductor (cable dúplex separado o separador de línea).
  - [ ] S7: con transformador de aislamiento, repetir H1-5 y H1-6 apagada; calibración con `cal_auto` y verificación con otra carga (error < 1–2 %).
  - [ ] S8: de punta a punta con red; protecciones sin internet; historial completo al volver la red.
  - [ ] Al cerrar la fase: agregar el bloque de software al artifact de referencia (CLAUDE.md, paso 5).
- [x] 10I · Documentación.

## Ten a mano

- La placa 1, la fuente de banco (12 V, 0,2 A en J6), el Keysight 34461A, el cable USB-C de datos y cables dupont.
- La sonda DS18B20 y el CT. Un cable dúplex (paralelo) o un separador de línea para el CT.
- El celular con el hotspot y tu cuenta de Google para Firebase. El nombre y la clave del WiFi no van en el repo.
- Para S7: transformador de aislamiento, regleta con interruptor, carga resistiva de 1–1,5 kW y pinza amperimétrica.

## Pendientes fuera de esta fase

- Rev 1.1 de la PCB: gabinete, punto de prueba para el canal de corriente y lo demás de las notas en `docs/DECISIONES.md` (Fase 9).
- Fotos de las dos caras de la placa 1 para `docs/pruebas/fotos/` (opcional).
