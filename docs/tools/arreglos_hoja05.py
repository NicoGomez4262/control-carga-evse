# -*- coding: utf-8 -*-
"""Arreglos de 05_SENSORES después del primer dibujo (12 oct 2026, Altium CERRADO).

- Designadores según los esquemas F5 (R32–R38, C37–C40), ubicando cada pieza por su red.
- R32, R33, R35: RC0805FR-0747KL (47 kΩ) → RC0805FR-074K7L (4,7 kΩ), como R21 en F4.
- U6, U7, J4: parámetros de la librería (en la hoja quedaron los viejos: «Adafruit», «±1V iso amp»).
- U7: R34 estaba en serie con VCC (pin 2). Queda como pull-up de RTC_INT: el puerto RTC_INT se corre a la
  izquierda, R34 pin 2 baja al cable de INT (con unión) y el pin 2 recibe su propio +3V3.
- U7 pines 14, 15, 16: cable corto y net label RTC_VBAT, I2C_SDA, I2C_SCL.

Uso: python docs/tools/arreglos_hoja05.py ["<ruta>/05_SENSORES.SchDoc"]
"""
import sys

import altium_ole as ao
import libreria as L
from hoja import Hoja
from ronda2_f4 import desig_de, params_lib, sincronizar

HOJA = "C:/Nicolas/UNIVERSIDAD - 2026/Hardware en IoT/Control de Carga IoT/Control de Carga IoT/05_SENSORES.SchDoc"
LIB = "C:/Users/nico/Documents/AltiumLL/SamacSys.SchLib"

# (LibReference, ubicación del componente en mil, designador)
DESIG = [("RC0805FR-0747KL", (3700, 9200), "R33"), ("RC0805FR-0747KL", (4000, 8200), "R32"),
         ("RC0805FR-0747KL", (4000, 1400), "R35"), ("RC0805FR-0710KL", (2600, 5800), "R34"),
         ("RC0805FR-07100RL", (4700, 1400), "R36"), ("RC1206FR-0768RL", (3200, 3000), "R37"),
         ("RC0805FR-07330RL", (6100, 8900), "R38"), ("CL21A106KAYNNNE", (7300, 8400), "C37"),
         ("CL21B104KBCNNNC", (8500, 8400), "C38"), ("CL21B104KBCNNNC", (6500, 5300), "C39"),
         ("CL21B104KBCNNNC", (5000, 2400), "C40")]


def comp_en(h, lib, xy):
    c = [i for i in h.buscar(RECORD="1") if h.v(i, "LibReference") == lib and h.xy(i) == xy]
    if len(c) != 1:
        raise SystemExit(f"{lib} en {xy}: {len(c)} componentes")
    return c[0]


def nuevo_indice(h):
    h._idx = getattr(h, "_idx", h.max_index_in_sheet()) + 1
    return str(h._idx)


def cable(h, usados, p1, p2):
    f = [("RECORD", "27"), ("IndexInSheet", nuevo_indice(h)), ("OwnerPartId", "-1"), ("LineWidth", "1"),
         ("Color", "8388608"), ("UniqueID", ao.uid(usados)), ("LocationCount", "2")]
    for n, (x, y) in enumerate((p1, p2), 1):
        f += [(f"X{n}", str(int(x) // 10))] + ([(f"X{n}_Frac", str(round((x % 10) * 10000)))] if x % 10 else [])
        f += [(f"Y{n}", str(int(y) // 10))]
    return h.agregar(f)


def main(ruta):
    h = Hoja(ruta)
    ps = L.piezas(LIB)
    usados = h.uids()
    uid = {d: h.v(comp_en(h, lib, xy), "UniqueID") for lib, xy, d in DESIG}
    for r in ("U6", "U7", "J4"):
        uid[r] = h.v(next(i for i in h.buscar(RECORD="1") if h.v(desig_de(h, i), "Text") == r), "UniqueID")

    for d, u in uid.items():
        c = h.por_uid(u)
        if not d.startswith(("R", "C")):
            continue
        if h.v(desig_de(h, c), "Text") != d:
            h.poner(desig_de(h, c), Text=d)
            h._nota(c, f"designador {d}")
    for d in ("R32", "R33", "R35"):
        c = h.por_uid(uid[d])
        h.poner(c, LibReference="RC0805FR-074K7L", DesignItemId="RC0805FR-074K7L")
        sincronizar(h, h.por_uid(uid[d]), params_lib(ps, "RC0805FR-074K7L"), usados, borrar_resto=True)
        c = h.por_uid(uid[d])
        h.poner(next(j for j in h.hijos(c) if h.v(j, "Name") == "Comment"), Text="RC0805FR-074K7L")
        h._nota(c, f"{d}: RC0805FR-0747KL (47 kΩ) → RC0805FR-074K7L (4,7 kΩ)")
    for d, lib in (("U6", "AHT20"), ("U7", "DS3231SN"), ("J4", "1751251")):
        sincronizar(h, h.por_uid(uid[d]), params_lib(ps, lib), usados)
        c = h.por_uid(uid[d])
        com = next((j for j in h.hijos(c) if h.v(j, "Name") == "Comment"), None)
        if com is not None and h.v(com, "Text") in ("*", None):
            h.poner(com, Text=lib)
        h._nota(c, f"{d}: parámetros de la librería ({lib})")

    # --- U7: R34 como pull-up de RTC_INT y +3V3 propio en el pin 2
    port = h.buscar(RECORD="18", Name="RTC_INT")[0]
    if h.xy(port) != (3100.0, 5700.0):
        raise SystemExit("el puerto RTC_INT ya no está en (3100, 5700)")
    h.mover(port, 1500, 5700)
    ancho = int(h.v(port, "Width")) * 10 + int(h.v(port, "Width_Frac", 0) or 0) / 10000
    c647 = next(i for i in h.buscar(RECORD="27") if h.puntos(i) == [(3800.0, 5700.0), (3100 + ancho, 5700.0)])
    f = [(k, v) for k, v in h.r[c647] if k not in ("X2", "X2_Frac")]
    pos = next(n for n, (k, _) in enumerate(f) if k == "Y2")
    x2 = 1500 + ancho
    f[pos:pos] = [("X2", str(int(x2) // 10)), ("X2_Frac", str(round((x2 % 10) * 10000)))]
    h.r[c647] = f
    h._nota(port, f"puerto RTC_INT → (1500, 5700); cable de INT hasta {x2:.4f}")
    c648 = next(i for i in h.buscar(RECORD="27") if h.puntos(i) == [(3800.0, 5800.0), (3300.0, 5800.0)])
    h.borrar(c648)
    h._nota(c648, "borrado el cable R34 pin 2 → U7 pin 2 (VCC)")
    cable(h, usados, (3300, 5800), (3300, 5700))
    h.agregar([("RECORD", "29"), ("IndexInSheet", "-1"), ("OwnerPartId", "-1"), ("Location.X", "330"),
               ("Location.Y", "570"), ("Color", "128")])
    cable(h, usados, (3800, 5800), (3600, 5800))
    h.agregar([("RECORD", "17"), ("IndexInSheet", nuevo_indice(h)), ("OwnerPartId", "-1"), ("Style", "2"),
               ("ShowNetName", "T"), ("Location.X", "360"), ("Location.Y", "580"), ("Orientation", "1"),
               ("Color", "128"), ("FontID", "1"), ("Text", "+3V3"), ("UniqueID", ao.uid(usados))])
    h._nota(-1, "R34 pin 2 → cable de INT con unión en (3300, 5700); U7 pin 2 con +3V3 en (3600, 5800)")

    # --- U7 pines 16, 15, 14: cable corto y net label
    for y, nombre in ((5900, "I2C_SCL"), (5800, "I2C_SDA"), (5700, "RTC_VBAT")):
        cable(h, usados, (5400, y), (5800, y))
        h.agregar([("RECORD", "25"), ("IndexInSheet", nuevo_indice(h)), ("OwnerPartId", "-1"),
                   ("Location.X", "550"), ("Location.Y", str(y // 10)), ("Color", "128"), ("FontID", "1"),
                   ("Text", nombre), ("UniqueID", ao.uid(usados))])
        h._nota(-1, f"U7 pin en (5400, {y}): cable hasta 5800 y net label {nombre}")

    copia = h.guardar("antes_arreglos05")
    print(f"copia de seguridad: {copia}")
    for n in h.cambios:
        print(" ", n)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else HOJA)
