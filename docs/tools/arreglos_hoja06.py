# -*- coding: utf-8 -*-
"""Arreglos de 06_ACTUACION después del primer dibujo (12 oct 2026, Altium CERRADO).

- Borra las piezas sobrantes que quedaron sueltas: el relé 34.51.7.012.5010, la bornera TB001-500-03BE
  (diseño anterior a K1 = PhotoMOS) y un segundo AQY-414EHAX sin conectar.
- Designadores según los esquemas F6: Q3, R39 (gate), R40 (pull-down), R41 (LED), LED6, K1, J2.
- K1: parámetros de la librería (Mouser 769-AQY414EHAX, NC 400V 120mA) y Comment «AQY414EHAX».
- Clase de red EVSE_EXT: dos Blankets (salida de K1 y J2) con su Parameter Set, en el stream «Additional».

Uso: python docs/tools/arreglos_hoja06.py ["<ruta>/06_ACTUACION.SchDoc"]
"""
import sys

import altium_ole as ao
import libreria as L
from hoja import Hoja
from ronda2_f4 import desig_de, params_lib, sincronizar

HOJA = "C:/Nicolas/UNIVERSIDAD - 2026/Hardware en IoT/Control de Carga IoT/Control de Carga IoT/06_ACTUACION.SchDoc"
LIB = "C:/Users/nico/Documents/AltiumLL/SamacSys.SchLib"

BORRAR = [("34.51.7.012.5010", (4100, 9700)), ("TB001-500-03BE", (6800, 9100)), ("AQY-414EHAX", (10100, 8500))]
DESIG = [("AO3400A", (5400, 7500), "Q3"), ("RC0805FR-071KL", (3000, 7500), "R39"),
         ("RC0805FR-0710KL", (4400, 6800), "R40"), ("RC0805FR-071KL", (2800, 5600), "R41"),
         ("KT-0805Y", (3900, 5600), "LED6"), ("AQY-414EHAX", (4900, 5600), "K1"), ("TB001-500-02BE", (10200, 7500), "J2")]
# (clase, polígono en mil, Parameter Set en el borde, color del borde BGR)
BLANKETS = [("EVSE_EXT", [(5700, 5400), (6600, 5400), (6600, 5800), (5700, 5800)], (5700, 5800), 33023),
            ("EVSE_EXT", [(9300, 7300), (10300, 7300), (10300, 7700), (9300, 7700)], (9300, 7700), 33023)]


def comp_en(h, lib, xy):
    c = [i for i in h.buscar(RECORD="1") if h.v(i, "LibReference") == lib and h.xy(i) == xy]
    if len(c) != 1:
        raise SystemExit(f"{lib} en {xy}: {len(c)} componentes")
    return c[0]


def descendientes(h, i):
    out = []
    for j in h.hijos(i):
        out += [j] + descendientes(h, j)
    return out


def main(ruta):
    h = Hoja(ruta)
    ps = L.piezas(LIB)
    usados = h.uids()
    uid = {d: h.v(comp_en(h, lib, xy), "UniqueID") for lib, xy, d in DESIG}

    for lib, xy in BORRAR:
        c = comp_en(h, lib, xy)
        for j in sorted([c] + descendientes(h, c), reverse=True):
            h.borrar(j)
        h._nota(c, f"borrado {lib} suelto en {xy}")

    for d, u in uid.items():
        c = h.por_uid(u)
        h.poner(desig_de(h, c), Text=d)
        h._nota(c, f"designador {d}")

    sincronizar(h, h.por_uid(uid["K1"]), params_lib(ps, "AQY-414EHAX"), usados)
    c = h.por_uid(uid["K1"])
    com = next(j for j in h.hijos(c) if h.v(j, "Name") == "Comment")
    h.poner(com, Text="AQY414EHAX")
    h.poner(c, ComponentDescription=ao.valor(L.resumen(ps["AQY-414EHAX"]["regs"])[0], "ComponentDescription"))
    h._nota(c, "K1: parámetros de la librería (AQY-414EHAX) y Comment AQY414EHAX")

    h.leer_adicional()
    n = max(h.max_index_in_sheet(), *[int(ao.valor(f, "IndexInSheet", 0) or 0) for f in h.ad] or [0])
    for clase, pts, (fx, fy), color in BLANKETS:
        n += 1
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        b = [("RECORD", "225"), ("IndexInSheet", str(n)), ("OwnerPartId", "-1"),
             ("Location.X", str(min(xs) // 10)), ("Location.Y", str(min(ys) // 10)),
             ("Corner.X", str(max(xs) // 10)), ("Corner.Y", str(max(ys) // 10)),
             ("Color", str(color)), ("AreaColor", "16777215"), ("LineStyle", "1"), ("LocationCount", str(len(pts)))]
        for k, (x, y) in enumerate(pts, 1):
            b += [(f"X{k}", str(x // 10)), (f"Y{k}", str(y // 10))]
        b += [("LineStyleExt", "1"), ("UniqueID", ao.uid(usados))]
        h.ad.append(b)
        n += 1
        d = [("RECORD", "43"), ("IndexInSheet", str(n)), ("OwnerPartId", "-1"), ("Location.X", str(fx // 10)),
             ("Location.Y", str(fy // 10)), ("Color", "255"), ("Orientation", "1"), ("Name", "Parameter Set"),
             ("UniqueID", ao.uid(usados))]
        idir = h.agregar(d)
        h.agregar([("RECORD", "41"), ("OwnerIndex", str(idir)), ("OwnerPartId", "-1"),
                   ("Location.X", str(fx // 10 - 3)), ("Location.Y", str(fy // 10 + 4)), ("Color", "8388608"),
                   ("FontID", "1"), ("IsHidden", "T"), ("Text", clase), ("Name", "ClassName"),
                   ("UniqueID", ao.uid(usados))])
        h._nota(idir, f"Blanket {clase} {pts[0]}–{pts[2]} y Parameter Set en ({fx}, {fy})")

    copia = h.guardar("antes_arreglos06")
    print(f"copia de seguridad: {copia}")
    for x in h.cambios:
        print(" ", x)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else HOJA)
