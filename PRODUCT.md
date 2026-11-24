# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

- **Dueño del equipo (principal):** quien carga su vehículo eléctrico en casa o en un parqueadero, con el EVSE Monitor instalado junto al cargador. Abre la app casi siempre desde el celular: para ver si está cargando, cuánta energía y plata lleva la sesión, y para permitir o detener la carga a distancia.
- **Administrador:** quien hizo el proyecto (curso Hardware en IoT). Da de alta equipos, calibra el medidor, actualiza el firmware y da permisos. Confirmado (24 nov 2026): la usan quien administra y las personas que invite.
- **Solo lectura:** alguien que solo mira (por ejemplo, el profesor del curso o un familiar).

## Product Purpose

Una placa propia (ESP32-S3 + ATM90E26) mide tensión, corriente, potencia, energía y temperatura durante la carga de un vehículo eléctrico, y habilita o detiene la carga con un relé en los bornes de habilitación del EVSE. La app web muestra eso en vivo, guarda el historial con costos y manda las órdenes. Éxito: desde el celular se ve la medición real y se permite o detiene la carga con confirmación del equipo; las protecciones actúan aunque no haya internet.

## Positioning

No es un cargador ni la app de un fabricante: es un monitor independiente que se pone al lado de cualquier EVSE, mide la red de verdad (120 V L–N o 240 V L1–L2) y decide localmente por temperatura y fallas. La app es la ventana a ese hardware, no el lugar donde se decide la seguridad.

## Operating Context

- Se usa en Colombia (español, pesos colombianos, hora UTC−5), en el garaje o desde fuera de casa.
- Momentos típicos: enchufar el carro y mirar que arranque; revisar a mitad de la carga; recibir una alarma (sobretemperatura, PARAR) y entender qué pasó; mirar el mes en energía y plata.
- Estados del equipo: en línea / sin conexión; carga permitida o detenida y por qué (falla, temperatura, PARAR, tensión baja, límite, horario, app, arranque); alarmas sin reconocer; OTA en curso.
- Backend: Firebase (Authentication + Realtime Database + Hosting) en el plan gratis. Los datos llegan en tiempo real.

## Capabilities and Constraints

- Panel en vivo: V, I, P, FP, Hz, energía de la sesión y total, costo, duración, temperaturas de sonda y placa, humedad, K1, motivo, alarmas.
- Órdenes con confirmación del equipo: permitir, detener, reconocer alarmas, soltar PARAR, reiniciar; calibración solo para el administrador.
- Configuración: tensión nominal, tarifa, límites por sesión (kWh, minutos, pesos), horario semanal, temperaturas de corte, política de arranque de K1, Telegram.
- Historial: gráficas de potencia, tensión y temperatura (24 h, 7 d, 30 d), sesiones con costo, eventos y alarmas, CSV.
- Administración: equipos (alta, código de enlace, borrado), usuarios y permisos, firmware OTA.
- HTML, CSS y JS sin framework ni paso de compilación (D24). Sin dependencias salvo el SDK web de Firebase.
- El repositorio es público: nada de credenciales en el código.

## Brand Commitments

Nombre: **EVSE Monitor**. Proyecto del curso Hardware en IoT; enlazado desde el portafolio nicolasgomez.dev. Textos en español con trato de tú.

## Evidence on Hand

- Hardware real: placa Rev 1.0 ensamblada por JLCPCB (render en `docs/img/render_3d.webp`, layout en `docs/img/layout_2d.webp`).
- No hay mediciones reales todavía: los datos de la app salen del simulador (`tools/simulador`) hasta que la placa esté calibrada (S7). No inventar cifras de ahorro, usuarios ni clientes.

## Product Principles

1. El estado de la carga se entiende en un vistazo: si está cargando, si no, y por qué.
2. Ninguna orden se da por hecha hasta que el equipo la confirma.
3. La seguridad vive en el equipo; la app informa y pide, nunca promete lo que no controla.
4. Funciona igual de bien con una mano en el celular que en el computador.

## Accessibility & Inclusion

Contraste legible a pleno sol en un garaje y de noche; respetar `prefers-reduced-motion`; objetivos táctiles grandes.
