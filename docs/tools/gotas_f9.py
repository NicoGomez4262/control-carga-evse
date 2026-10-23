# -*- coding: utf-8 -*-
"""F9: qué uniones de pista con pad o vía no tienen gota (teardrop) en EVSE_Monitor.PcbDoc (solo lee).

Las gotas de Altium (Tools » Teardrops) se guardan como regiones sueltas (ShapeBasedRegions6 sin polígono, índice
de polígono 0xFFFF) en la capa y la red de la pista. Para cada punta de pista que cae dentro de un pad o una vía de
su red se busca el punto donde la pista sale del cobre del pad y 0,15 mm más afuera: si ninguna región suelta de la
misma capa y red contiene ese punto, la unión no tiene gota. No se cuentan las pistas tan anchas como el pad (ahí
Altium no pone gota).

Uso: python docs/tools/gotas_f9.py [ruta.PcbDoc]
"""
import math
import struct
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import revisar_pcb as rv  # noqa: E402
import revisar_ruteo_f8 as rr  # noqa: E402


def dentro(o, p):
    return min(rr.distancia(rr.Forma("pt", [p], 0.0), f) for f in o["formas"]) <= 1e-6


def uniones_sin_gota():
    from matplotlib.path import Path as Ruta
    objs, _ = rr.cargar()
    nets = [n for n in (dict(c).get("NAME") for c in rv.texto("Nets6/Data"))]
    gotas = defaultdict(list)
    for bl in rr._prims("ShapeBasedRegions6/Data", 11, 1):
        g = bl[0]
        if struct.unpack_from("<H", g, 5)[0] != 0xFFFF:
            continue
        red = struct.unpack_from("<H", g, 3)[0]
        i = 18 + 4 + struct.unpack_from("<I", g, 18)[0]
        n = struct.unpack_from("<I", g, i)[0]
        cont = [((struct.unpack_from("<i", g, i + 4 + 37 * k + 1)[0]) * rr.U - rr.O,
                 (struct.unpack_from("<i", g, i + 4 + 37 * k + 5)[0]) * rr.U - rr.O) for k in range(n + 1)]
        gotas[(g[0], nets[red] if red != 0xFFFF else None)].append(Ruta(cont))
    destinos = [o for o in objs if o["tipo"] in ("pad", "via") and o["red"] and not o.get("virtual")]
    faltan, con = [], 0
    for o in objs:
        if o["tipo"] != "pista" or not o["red"] or o["keepout"] or o["capa"] not in (1, 32):
            continue
        a, b = o["formas"][0].pts
        largo = math.dist(a, b)
        if largo < 1e-6:
            continue
        for e, otro in ((a, b), (b, a)):
            u = ((otro[0] - e[0]) / largo, (otro[1] - e[1]) / largo)
            for d in destinos:
                if d["red"] != o["red"] or o["capa"] not in d["capas"]:
                    continue
                if not (d["caja"][0] - 0.01 <= e[0] <= d["caja"][2] + 0.01 and d["caja"][1] - 0.01 <= e[1] <= d["caja"][3] + 0.01):
                    continue
                if not dentro(d, e):
                    continue
                menor = min(d["sx"], d["sy"]) if d["tipo"] == "pad" else d["dia"]
                if o["ancho"] >= menor - 0.05:
                    continue
                s = 0.0
                while s < largo and dentro(d, (e[0] + u[0] * s, e[1] + u[1] * s)):
                    s += 0.02
                s += 0.15
                if s >= largo:
                    continue
                p = (e[0] + u[0] * s, e[1] + u[1] * s)
                if any(r.contains_point(p) for r in gotas[(o["capa"], o["red"])]):
                    con += 1
                else:
                    faltan.append((rr.nombre(d), o["red"], "Top" if o["capa"] == 1 else "Bottom", round(o["ancho"], 3),
                                   (round(e[0], 2), round(e[1], 2))))
    return con, faltan


def main():
    if len(sys.argv) > 1:
        rv.PCB = Path(sys.argv[1])
    con, faltan = uniones_sin_gota()
    print(f"Uniones pista–pad/vía con gota: {con}; sin gota: {len(faltan)}")
    for f in sorted(faltan):
        print("  ", f)


if __name__ == "__main__":
    main()
