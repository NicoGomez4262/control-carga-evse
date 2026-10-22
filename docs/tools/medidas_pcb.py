# -*- coding: utf-8 -*-
"""Medidas de cada componente de EVSE_Monitor.PcbDoc (Altium CERRADO o guardado), sin abrir Altium.

Para cada componente da la caja que ocupan sus pads, su serigrafía (Top Overlay) y su courtyard
(capas mecánicas), en el marco propio del footprint (sin la rotación actual), relativa al origen del
footprint. Sirve para planear la ubicación y generar el script de Altium que mueve las piezas.

Uso: python docs/tools/medidas_pcb.py [--json salida.json]

Tracks6: tipo 4 + bloque (capa [0], red uint16 [3], componente uint16 [7], x1 y1 x2 y2 int32 [13..28],
ancho int32 [29]). Arcs6: tipo 1 + bloque (capa [0], componente [7], centro [13]/[17], radio [21],
ángulo inicial/final double [25]/[33], ancho [41]). Unidades internas = 1/10000 mil.
"""
import json
import math
import struct
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import altium_ole as ao  # noqa: E402
import pcblib  # noqa: E402
import revisar_pcb as rv  # noqa: E402

U = rv.U
TOP_OVERLAY = 33


def primitivas(stream, tipo, nbloques=1):
    data = ao.leer_stream(rv.PCB, stream)
    out, i = [], 0
    while i < len(data):
        t = data[i]
        i += 1
        bl, i = pcblib.bloques(data, i, nbloques)
        assert t == tipo, (stream, t)
        out.append(bl[0])
    return out


def medidas():
    comps = rv.texto("Components6/Data")
    info = []
    for c in comps:
        x = float(ao.valor(c, "X").replace("mil", "")) * 0.0254
        y = float(ao.valor(c, "Y").replace("mil", "")) * 0.0254
        rot = float(ao.valor(c, "ROTATION"))
        info.append(dict(des=ao.valor(c, "SOURCEDESIGNATOR"), fp=ao.valor(c, "PATTERN"), x=x, y=y, rot=rot,
                         cajas=defaultdict(lambda: [1e9, 1e9, -1e9, -1e9])))

    def local(ci, px, py):
        c = info[ci]
        a = -math.radians(c["rot"])
        dx, dy = px - c["x"], py - c["y"]
        return dx * math.cos(a) - dy * math.sin(a), dx * math.sin(a) + dy * math.cos(a)

    def sumar(ci, capa, pts):
        b = info[ci]["cajas"][capa]
        for px, py in pts:
            lx, ly = local(ci, px, py)
            b[0], b[1], b[2], b[3] = min(b[0], lx), min(b[1], ly), max(b[2], lx), max(b[3], ly)

    for p in rv.pads():
        if p["comp"] == 0xFFFF:
            continue
        hx, hy = p["sx"] / 2, p["sy"] / 2
        r = max(hx, hy)  # sin la rotación del pad: caja conservadora
        sumar(p["comp"], "pads", [(p["x"] - r, p["y"] - r), (p["x"] + r, p["y"] + r)])
    for g in primitivas("Tracks6/Data", 4):
        comp = struct.unpack_from("<H", g, 7)[0]
        if comp == 0xFFFF:
            continue
        x1, y1, x2, y2 = (v * U for v in struct.unpack_from("<iiii", g, 13))
        capa = "silk" if g[0] == TOP_OVERLAY else ("mec%d" % (g[0] - 56) if g[0] >= 57 else "c%d" % g[0])
        sumar(comp, capa, [(x1, y1), (x2, y2)])
    for g in primitivas("Arcs6/Data", 1):
        comp = struct.unpack_from("<H", g, 7)[0]
        if comp == 0xFFFF:
            continue
        cx, cy, r = (v * U for v in struct.unpack_from("<iii", g, 13))
        capa = "silk" if g[0] == TOP_OVERLAY else ("mec%d" % (g[0] - 56) if g[0] >= 57 else "c%d" % g[0])
        sumar(comp, capa, [(cx - r, cy - r), (cx + r, cy + r)])
    for c in info:
        c["cajas"] = {k: [round(v, 2) for v in b] for k, b in c["cajas"].items()}
    return info


if __name__ == "__main__":
    info = medidas()
    capas = sorted({k for c in info for k in c["cajas"]})
    print("capas con primitivas:", capas)
    vistos = set()
    for c in sorted(info, key=lambda c: c["fp"]):
        if c["fp"] in vistos:
            continue
        vistos.add(c["fp"])
        cj = c["cajas"]
        todo = [min(b[0] for b in cj.values()), min(b[1] for b in cj.values()),
                max(b[2] for b in cj.values()), max(b[3] for b in cj.values())]
        print(f"{c['fp'][:34]:34} ej. {c['des']:5} rot {c['rot']:5.0f}  total {todo}  "
              + "  ".join(f"{k}={v}" for k, v in sorted(cj.items()) if k != "silk"))
    if "--json" in sys.argv:
        Path(sys.argv[sys.argv.index("--json") + 1]).write_text(json.dumps(info, indent=1), encoding="utf-8")
