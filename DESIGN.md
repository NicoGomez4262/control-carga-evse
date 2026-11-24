# Design

Sistema visual de la app web del EVSE Monitor (`app/public/`), escrito a partir de lo construido el 24 nov 2026 (D32). Lo que dice el código manda sobre este archivo.

## Mundo

Un **tablero eléctrico del futuro**: la pantalla es el frente de un gabinete con módulos montados en un riel DIN. Cada módulo lleva un rótulo grabado con el designador de la placa (X0 circuito, P1 potencia, K1 permiso, E1 sesión, H1 anunciador, T1/T2 temperaturas, V1 red, E0 energía total). El estado se dice con luz: pilotos y anillos verdes, ámbar o rojos. Se evita el panel oscuro de tarjetas iguales con anillo de progreso y acento neón.

## Color

Estrategia contenida: neutros fríos y tres colores de estado que significan siempre lo mismo.

| Token | Día | Noche | Uso |
|---|---|---|---|
| `--fondo` | `#e4e8eb` | `#0e1317` | fondo del gabinete |
| `--modulo` → `--modulo-2` | `#fafbfc` → `#f1f4f6` | `#182129` → `#141c23` | policarbonato / vidrio antracita de cada módulo |
| `--placa`, `--vidrio` | `#e5eaee`, `#edf1f4` | `#222d36`, `#10171d` | rótulos y ventanas de lectura hundidas |
| `--costura`, `--riel-a/b` | `#cdd5db`, `#cfd6dc/#a9b3bc` | `#26323c`, `#2c3842/#1b232a` | bordes de 1 px y el riel |
| `--tinta`, `--tinta-2`, `--tinta-3` | `#121b24`, `#44515d`, `#64707c` | `#e6ecf1`, `#a9b5bf`, `#85919c` | texto |
| `--verde` | `#0e9f4e` (botón `#087f3d`) | `#34d27b` | permitida, cargando, en línea |
| `--ambar` | `#c98200` | `#f2b233` | espera, aviso, límite |
| `--rojo` | `#d0342a` | `#ff6656` | protección, falla, alarma grave |
| `--azul` | `#1f6fd1` | `#5b9bff` | foco y «esperando confirmación del equipo» |

El tema sigue al sistema; en Perfil se fija Día o Noche (`data-tema` en `<html>`, guardado en `localStorage`).

## Tipografía

**Barlow** (UI y lecturas, cifras tabulares) y **Barlow Semi Condensed** (rótulos en mayúsculas con 0,07–0,1 em de tracking), de la familia DIN: el mismo estándar que el riel. Lecturas: 3,6 rem (potencia), 2 rem, 1,35 rem; la unidad va a 0,48 em en `--tinta-3`.

## Piezas

- **Riel** (`.riel`): perfil metálico de 7 px con ranuras sobre cada fila; rejilla de 4 columnas en el celular y 12 desde 980 px. Cada módulo declara `--m` (celular) y `--d` (computador).
- **Módulo** (`.mod`): radio 16 px, costura de 1 px, brillo interior arriba, sombra suave con desplazamiento; pestaña de enganche al riel.
- **Rótulo** (`.rotulo`): placa hundida con el designador en negrita.
- **Piloto** (`.piloto`): lente de 12 px con reflejo; `respira` cuando hay energía fluyendo, `parpadea` (1 Hz) cuando falta reconocer.
- **Mímico** (`instrumentos.js → mimico`): diagrama unifilar RED → F1 → K1 → J2 → VE; la cuchilla de K1 gira al abrir o cerrar; los tramos con tensión se tiñen y el flujo corre con velocidad proporcional a la potencia.
- **Medidor de aguja** (`Medidor`): arco de 240°, escala en kW (4 u 8 según la red), aguja con resorte ligeramente subamortiguado, marca ámbar del pico de la sesión.
- **Selector K1** (`selector`): perilla de dos posiciones (−42° / +42°) con anillo de luz; mientras el equipo no confirma, un segmento azul gira; si falla, la perilla tiembla y vuelve.
- **Anunciador** (`.anunciador`): ventanas que se encienden en rojo (grave) o ámbar (aviso) y titilan sin reconocer.
- **Registro de rodillos** (`rodillos`): energía total con ruedas que ruedan; el decimal en rueda roja.
- **Mando** (`.mando`): barra inferior con cuatro posiciones y guía de luz verde arriba de la activa; columna lateral en el computador.

## Movimiento

Una secuencia de encendido por vista (módulos que se asientan con desenfoque que se aclara, pilotos que destellan en orden), View Transitions entre vistas, números que corren con salida exponencial, la aguja con resorte, el flujo del mímico y el giro del selector. `prefers-reduced-motion` apaga todo eso y deja los estados fijos (lo no reconocido se marca con borde).

## Superficies del navegador

Selección en verde translúcido, cursor de texto azul, foco con anillo azul de 2 px, barras de desplazamiento del color del riel, `accent-color` verde, cifras tabulares en todo.
