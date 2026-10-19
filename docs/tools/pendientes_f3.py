# -*- coding: utf-8 -*-
"""Pendientes de F3 resueltos por script al inicio de F4 (Altium CERRADO).

A4  03_MEDICION: las 10 net labels +3V3/+3V3A pasan a puertos de alimentación (Bar), que son
    globales. Donde la etiqueta estaba en una esquina de un cable en forma de U, el cable queda
    recto desde el pin hasta el puerto. Para que los símbolos no se monten:
      - U3 pines 1, 3 y 5: puertos apuntando a la izquierda; los GND de los pines 2 y 6 se
        alargan hasta x = 10900 y apuntan a la izquierda.
      - U2 pin 12: el cable se alarga hasta x = 3600 y el puerto apunta arriba; el GND del pin 15
        pasa a x = 3400 apuntando a la derecha.
A6  02_ALIMENTACION: ClassName «HV-AC» → «HV_AC» en las 4 directivas.
A7  03_MEDICION: 3 Blankets (registro 225) con su Parameter Set (ClassName HV_AC / ANALOG) con la
    punta sobre el borde (coordenadas de NEXT_SESSION.md, A7).
A8  TP1–TP6: parámetros Manufacturer_Name, Manufacturer_Part_Number, Value, Supplier, Supplier PN
    y Assembly.

Uso:
    python docs/tools/pendientes_f3.py "<carpeta del proyecto>" [--probar]
--probar escribe copias en la carpeta de trabajo de Claude en vez de tocar las hojas.
"""
import shutil
import sys
from pathlib import Path

import altium_ole as ao
from hoja import Hoja

# ---------------------------------------------------------------- A4
# (UniqueID de la etiqueta, (x, y) del puerto, orientación 0=der 1=arriba 2=izq 3=abajo,
#  UniqueID del cable a rehacer o None, vértices nuevos del cable)
PUERTOS = [
    ("CMSXUGUO", (11500, 8400), 1, "cable riel C14", [(11500, 8400), (11500, 8100)]),
    ("UMZNRTYS", (1200, 3400), 1, "cable riel C24", [(1200, 3400), (1200, 3100), (2400, 3100)]),
    ("EPTMSARB", (3800, 2600), 1, "cable C28", [(3800, 2600), (3800, 2300)]),
    ("ACXAOPWK", (5000, 2900), 1, "cable R16", [(5000, 2900), (5000, 2700)]),
    ("DAWPNHIP", (9300, 1800), 1, "cable R18", [(9300, 1800), (9300, 1600)]),
    ("IJFPTEYK", (13700, 3700), 1, None, None),          # U3 pin 28
    ("WNQJHIZK", (11500, 3700), 2, None, None),          # U3 pin 1
    ("CQDCRWUC", (11500, 3500), 2, None, None),          # U3 pin 3
    ("QUFBJWST", (11500, 3300), 2, None, None),          # U3 pin 5 (+3V3A)
    ("YOIVLVFE", (3600, 8000), 1, "cable U2.12", [(3600, 8000), (2700, 8000)]),
]
# cables identificados por su primer vértice actual (mil)
CABLES = {
    "cable riel C14": (11300, 8400),
    "cable riel C24": (1100, 3400),
    "cable C28": (3800, 2600),
    "cable R16": (5000, 2900),
    "cable R18": (9300, 1800),
    "cable U2.12": (2900, 8000),
}
# GND que se mueven: UniqueID → ((x, y), orientación, cable (primer vértice), vértices nuevos)
GND = [
    ("SESLPMZO", (10900, 3600), 2, (12000, 3600), [(12000, 3600), (10900, 3600)]),   # U3 pin 2
    ("OCREVSQH", (10900, 3200), 2, (12000, 3200), [(12000, 3200), (10900, 3200)]),   # U3 pin 6
    ("MALTDXZT", (3400, 8300), 0, (2700, 8300), [(2700, 8300), (3400, 8300)]),       # U2 pin 15
]
UNION_SOBRANTE = (3800, 2300)   # punto de unión de C28 que queda entre cable y pin, sin T

# ---------------------------------------------------------------- A7
BLANKETS = [
    ("HV_AC", [(400, 10800), (9400, 10800), (9400, 6900), (3800, 6900), (3800, 8800), (1800, 8800),
               (1800, 7500), (400, 7500)], (1000, 10800), 255, 14474495),
    ("ANALOG", [(400, 6600), (5400, 6600), (5400, 6200), (3400, 6200), (3400, 5300), (5400, 5300),
                (5400, 4900), (400, 4900)], (400, 5700), 32768, 14483420),
    ("ANALOG", [(6100, 6200), (10700, 6200), (10700, 5800), (7600, 5800), (7600, 4800), (10700, 4800),
                (10700, 4300), (6100, 4300)], (6100, 5300), 32768, 14483420),
]

# ---------------------------------------------------------------- A8
PARAMS_TP = [("Manufacturer_Name", "Keystone"), ("Manufacturer_Part_Number", "5016"), ("Value", "TP"),
             ("Supplier", "PCBWay"), ("Supplier PN", "5016"), ("Assembly", "PCBWay")]


def cable_que_empieza(h, p):
    c = [i for i in h.buscar(RECORD="27") if h.puntos(i)[0] == p or h.puntos(i)[-1] == p]
    if len(c) != 1:
        raise SystemExit(f"esperaba un cable con extremo en {p} y hay {len(c)}")
    return c[0]


def a4(h):
    for uid, (x, y), ori, cable, pts in PUERTOS:
        i = h.por_uid(uid)
        texto = h.v(i, "Text")
        if h.v(i, "RECORD") != "25":
            raise SystemExit(f"{uid} ya no es una net label")
        if cable:
            c = cable_que_empieza(h, CABLES[cable])
            h.trazo(c, pts)
            h._nota(c, f"{cable}: {pts}")
        f = [("RECORD", "17"), ("IndexInSheet", h.v(i, "IndexInSheet")), ("OwnerPartId", "-1"),
             ("Style", "2"), ("ShowNetName", "T"), ("Location.X", str(x // 10)), ("Location.Y", str(y // 10))]
        if ori:
            f.append(("Orientation", str(ori)))
        f += [("Color", "128"), ("FontID", "1"), ("Text", texto), ("UniqueID", uid)]
        h.r[i] = f
        h._nota(i, f"net label {texto} → puerto de alimentación en ({x}, {y}) orientación {ori * 90}°")
    for uid, (x, y), ori, inicio, pts in GND:
        i = h.por_uid(uid)
        c = cable_que_empieza(h, inicio)
        h.trazo(c, pts)
        h.mover(i, x, y)
        h.poner(i, Orientation=ori if ori else None)
        h._nota(i, f"GND → ({x}, {y}) orientación {ori * 90}°; cable {pts}")
    for j in h.buscar(RECORD="29"):
        if h.xy(j) == UNION_SOBRANTE:
            h.borrar(j)
            h._nota(j, f"unión sobrante en {UNION_SOBRANTE} borrada")
            break


def a7(h):
    usados = h.uids()
    n = h.max_index_in_sheet()
    for clase, pts, (fx, fy), color, relleno in BLANKETS:
        n += 1
        b = [("RECORD", "225"), ("IndexInSheet", str(n)), ("OwnerPartId", "-1"), ("LineWidth", "1"),
             ("LineStyle", "1"), ("IsSolid", "T"), ("Transparent", "T"), ("Color", str(color)),
             ("AreaColor", str(relleno)), ("LocationCount", str(len(pts)))]
        for k, (x, y) in enumerate(pts, 1):
            b += [(f"X{k}", str(x // 10)), (f"Y{k}", str(y // 10))]
        b.append(("UniqueID", ao.uid(usados)))
        ib = h.agregar(b)
        n += 1
        d = [("RECORD", "43"), ("IndexInSheet", str(n)), ("OwnerPartId", "-1"), ("Location.X", str(fx // 10)),
             ("Location.Y", str(fy // 10)), ("Color", "255"), ("Name", "Parameter Set"), ("UniqueID", ao.uid(usados))]
        idir = h.agregar(d)
        p = [("RECORD", "41"), ("OwnerIndex", str(idir)), ("OwnerPartId", "-1"), ("Location.X", str(fx // 10)),
             ("Location.Y", str(fy // 10 - 16)), ("Color", "8388608"), ("FontID", "1"), ("IsHidden", "T"),
             ("Text", clase), ("Name", "ClassName"), ("UniqueID", ao.uid(usados))]
        h.agregar(p)
        h._nota(ib, f"Blanket {clase} {pts}; Parameter Set en ({fx}, {fy})")


def a6(h):
    for i in h.buscar(RECORD="41", Name="ClassName", Text="HV-AC"):
        h.poner(i, Text="HV_AC")
        h._nota(i, "ClassName HV-AC → HV_AC")


def a8(h):
    usados = h.uids()
    # de atrás hacia adelante: lo que se inserta no corre los índices de los TP anteriores
    for c in sorted(h.buscar(RECORD="1", LibReference="KEYSTONE-5016"), reverse=True):
        hijos = h.hijos(c)
        nombres = {h.v(j, "Name"): j for j in hijos if h.v(j, "RECORD") == "41"}
        desig = next(h.v(j, "Text") for j in hijos if h.v(j, "RECORD") == "34")
        # después del último parámetro oculto (antes del designador)
        params = [j for j in hijos if h.v(j, "RECORD") == "41" and h.v(j, "IsHidden") == "T"]
        pos = max(params) + 1
        idx = int(h.v(max(params), "IndexInSheet"))
        x, y = h.v(max(params), "Location.X"), h.v(max(params), "Location.Y")
        for nombre, val in PARAMS_TP:
            if nombre in nombres:
                h.poner(nombres[nombre], Text=val)
                continue
            idx += 1
            f = [("RECORD", "41"), ("OwnerIndex", str(c)), ("IndexInSheet", str(idx)), ("OwnerPartId", "-1"),
                 ("Location.X", x), ("Location.Y", y), ("Color", "8388608"), ("FontID", "1"), ("IsHidden", "T"),
                 ("Text", val), ("Name", nombre), ("UniqueID", ao.uid(usados))]
            h.insertar(pos, f)
            pos += 1
        h._nota(c, f"{desig}: " + ", ".join(f"{k}={v}" for k, v in PARAMS_TP))


def main(carpeta, probar):
    carpeta = Path(carpeta)
    s02, s03 = carpeta / "02_ALIMENTACION.SchDoc", carpeta / "03_MEDICION.SchDoc"
    if probar:
        tmp = Path(probar)
        tmp.mkdir(parents=True, exist_ok=True)
        s02 = Path(shutil.copy2(s02, tmp / s02.name))
        s03 = Path(shutil.copy2(s03, tmp / s03.name))
    h2 = Hoja(s02)
    a6(h2)
    a8(h2)
    h3 = Hoja(s03)
    a4(h3)
    a7(h3)
    a8(h3)
    for h in (h2, h3):
        print(f"== {h.ruta.name}")
        for c in h.cambios:
            print("  ", c)
        if probar:
            ao.escribir_streams(h.ruta, {"FileHeader": h.datos()})
        else:
            print("   copia:", h.guardar("antes_pendientes_f3"))


if __name__ == "__main__":
    a = sys.argv[1:]
    probar = a[a.index("--probar") + 1] if "--probar" in a else None
    main(a[0], probar)
