# -*- coding: utf-8 -*-
"""Arreglos de presentación después del PDF de F7 (19 oct 2026, Altium CERRADO). Solo texto.

- 02, 04 y 06: el Title se salía del bloque de título (caben ≈ 31 caracteres, como
  «Medición de tensión y corriente»); se acorta.
- 01_TOP: la nota de rieles tenía 7 líneas y el cuadro solo mostraba 6; se alarga 400 mil hacia abajo.

Uso: python docs/tools/presentacion_f7.py
"""
from pathlib import Path

import altium_ole as ao
from arreglos_hojas_f7 import texto
from hoja import Hoja

PROY = Path("C:/Nicolas/UNIVERSIDAD - 2026/Hardware en IoT/Control de Carga IoT/Control de Carga IoT")
TITULOS = {
    "02_ALIMENTACION": "Alimentación: red, 12 V y 3,3 V",
    "04_MCU": "ESP32-S3, USB y programación",
    "06_ACTUACION": "Actuación: PhotoMOS K1 al EVSE",
}
NOTA_BAJA_MIL = 400


def main():
    if ao.altium_abierto():
        raise SystemExit("Altium está abierto: ciérralo antes de correr el script.")
    for nombre, titulo in TITULOS.items():
        h = Hoja(str(PROY / f"{nombre}.SchDoc"))
        for i in h.buscar(RECORD="41"):
            if h.v(i, "OwnerIndex") is None and h.v(i, "Name") == "Title":
                viejo = h.v(i, "%UTF8%Text") or h.v(i, "Text")
                texto(h, i, "Text", titulo)
                h._nota(i, f"Title «{viejo.encode('latin-1').decode('utf-8', 'replace')}» → «{titulo}»")
        print(f"== {nombre} (respaldo: {h.guardar('antes_titulo')})")
        for x in h.cambios:
            print("  ", x)
    h = Hoja(str(PROY / "01_TOP.SchDoc"))
    for i in h.buscar(RECORD="28"):
        if "Rieles" in (h.v(i, "%UTF8%Text") or h.v(i, "Text") or ""):
            y = h.mil(h.r[i], "Location.Y")
            nuevo = int(round(y / 10.0)) * 10 - NOTA_BAJA_MIL
            h.r[i] = ao.quitar(h.r[i], "Location.Y_Frac")
            h.poner(i, Location_Y=str(nuevo // 10))
            h._nota(i, f"nota de rieles: borde inferior {y:.0f} → {nuevo} mil")
    print(f"== 01_TOP (respaldo: {h.guardar('antes_nota')})")
    for x in h.cambios:
        print("  ", x)


if __name__ == "__main__":
    main()
