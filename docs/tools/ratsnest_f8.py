# -*- coding: utf-8 -*-
"""Ratsnest de la ubicación de ubicacion_f8.POS: árbol de expansión mínima de los pads de cada red, largo total,
cruces entre conexiones de redes distintas (sin GND, que va al plano) y dibujo.

Uso: python docs/tools/ratsnest_f8.py [--png salida.png] [--top 25]

Sirve para ordenar la ubicación pensando en rutear a mano: menos cruces y conexiones más cortas.
"""
import math
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ubicacion_f8 as u  # noqa: E402

RAIZ = Path(__file__).resolve().parents[2]
SIN_CRUCES = {"GND"}           # va al plano: sus conexiones no cuentan como cruces


def pads_por_red(info, pos):
    redes = defaultdict(list)
    for d, p in pos.items():
        for q in u.pads_en_placa(info[d], p):
            if q["red"]:
                redes[q["red"]].append((q["X"], q["Y"], f"{d}.{q['nombre']}"))
    return redes


def mst(puntos):
    """Prim: aristas (i, j) del árbol mínimo."""
    n = len(puntos)
    if n < 2:
        return []
    dentro = [False] * n
    dist = [math.inf] * n
    padre = [-1] * n
    dist[0] = 0
    out = []
    for _ in range(n):
        k = min((i for i in range(n) if not dentro[i]), key=lambda i: dist[i])
        dentro[k] = True
        if padre[k] >= 0:
            out.append((padre[k], k))
        for i in range(n):
            if not dentro[i]:
                dd = math.hypot(puntos[i][0] - puntos[k][0], puntos[i][1] - puntos[k][1])
                if dd < dist[i]:
                    dist[i], padre[i] = dd, k
    return out


def conexiones(info, pos):
    out = []
    for red, pts in pads_por_red(info, pos).items():
        # pads del mismo componente y de la misma red unidos por dentro (p. ej. GND de U4): se cuentan una vez
        for i, j in mst(pts):
            a, b = pts[i], pts[j]
            if a[2].split(".")[0] == b[2].split(".")[0] and math.hypot(a[0] - b[0], a[1] - b[1]) < 3:
                continue
            out.append(dict(red=red, a=(a[0], a[1]), b=(b[0], b[1]), da=a[2], db=b[2],
                            L=math.hypot(a[0] - b[0], a[1] - b[1])))
    return out


def cruces(cons):
    import ruteo_f8 as r
    lst = [c for c in cons if c["red"] not in SIN_CRUCES]
    out = []
    for i, c in enumerate(lst):
        for d in lst[i + 1:]:
            if c["red"] == d["red"]:
                continue
            if c["a"] in (d["a"], d["b"]) or c["b"] in (d["a"], d["b"]):
                continue
            if r.se_cruzan(c["a"], c["b"], d["a"], d["b"]):
                out.append((c, d))
    return out


def resumen(info, pos, top=0):
    cons = conexiones(info, pos)
    cr = cruces(cons)
    L = sum(c["L"] for c in cons if c["red"] not in SIN_CRUCES)
    Lg = sum(c["L"] for c in cons if c["red"] in SIN_CRUCES)
    print(f"Conexiones: {len(cons)} · largo sin GND {L:.0f} mm · GND {Lg:.0f} mm · cruces {len(cr)}")
    if top:
        largos = sorted((c for c in cons if c["red"] not in SIN_CRUCES), key=lambda c: -c["L"])[:top]
        print("Más largas:")
        for c in largos:
            print(f"  {c['red']:12} {c['da']:>9} → {c['db']:<9} {c['L']:6.1f} mm")
        por = defaultdict(int)
        for c, d in cr:
            por[c["red"]] += 1
            por[d["red"]] += 1
        print("Redes con más cruces:", sorted(por.items(), key=lambda x: -x[1])[:top])
    return cons, cr


def dibujar(info, pos, cons, ruta):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle, Circle
    fig, ax = plt.subplots(figsize=(19.5, 15))
    ax.add_patch(Rectangle((0, 0), u.LARGO, u.ALTO, fill=False, lw=1.2, color="black"))
    ax.add_patch(Rectangle((u.BARRERA[0], 0), u.BARRERA[1] - u.BARRERA[0], u.ALTO, color="#cccccc", alpha=0.4))
    for d, p in pos.items():
        b = u.caja_en_placa(info[d], p)
        ax.add_patch(Rectangle((b[0], b[1]), b[2] - b[0], b[3] - b[1], fill=False, lw=0.5, color="#7f77dd"))
        for q in u.pads_en_placa(info[d], p):
            col = "#d85a30" if q["red"] in u.HV else "#993556" if q["red"] in u.EVSE else "#185fa5" if q["red"] == "GND" else "#3b6d11"
            ax.add_patch(Rectangle((q["X"] - q["SX"] / 2, q["Y"] - q["SY"] / 2), q["SX"], q["SY"], color=col, alpha=0.6, lw=0))
        ax.text((b[0] + b[2]) / 2, (b[1] + b[3]) / 2, d, ha="center", va="center", fontsize=5.5)
    for c in cons:
        if c["red"] == "GND":
            col, lw, al = "#185fa5", 0.4, 0.35
        elif c["red"] in u.HV or c["red"] in u.EVSE:
            col, lw, al = "#d85a30", 0.9, 0.9
        elif c["red"] in ("+3V3", "+3V3A", "+VIN"):
            col, lw, al = "#ba7517", 0.8, 0.9
        else:
            col, lw, al = "#222222", 0.6, 0.85
        ax.plot([c["a"][0], c["b"][0]], [c["a"][1], c["b"][1]], color=col, lw=lw, alpha=al)
    for hx, hy in u.AGUJEROS:
        ax.add_patch(Circle((hx, hy), u.R_AGUJERO, fill=False, color="black"))
    ax.set_xlim(-5, u.LARGO + 5)
    ax.set_ylim(-5, u.ALTO + 8)
    ax.set_aspect("equal")
    ax.set_xticks(range(0, int(u.LARGO) + 1, 10))
    ax.set_yticks(range(0, int(u.ALTO) + 1, 10))
    ax.grid(lw=0.2)
    fig.tight_layout()
    fig.savefig(ruta, dpi=110)


if __name__ == "__main__":
    info = u.leer()
    top = int(sys.argv[sys.argv.index("--top") + 1]) if "--top" in sys.argv else 25
    cons, cr = resumen(info, u.POS, top)
    ruta = Path(sys.argv[sys.argv.index("--png") + 1]) if "--png" in sys.argv else RAIZ / "docs" / "revisiones" / "F8_ratsnest.png"
    dibujar(info, u.POS, cons, ruta)
    print("Dibujo:", ruta)
