# -*- coding: utf-8 -*-
"""Ubicador de pasivos para F8: con las piezas grandes fijas (ubicacion_f8.POS), pone cada pieza chica en la
posición y rotación libre que deja sus pads más cerca de los pads ya ubicados de sus mismas redes, sin chocar con
ningún courtyard, dentro de su zona y castigando los cruces nuevos de ratsnest.

Uso (desde otro script):
    import autoubicar_f8 as au
    pos = au.ubicar(info, fijas, orden, zona=..., radio=12)

- `fijas`: dict designador -> (x, y, rot) de lo que no se mueve.
- `orden`: lista de designadores a ubicar, en orden de prioridad (desacoples primero).
- GND no atrae (va al plano), pero las demás redes sí, con peso 1; las redes de potencia (+3V3, +3V3A, +VIN)
  con peso 0,6 (se rutean como tronco).
"""
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ubicacion_f8 as u  # noqa: E402
import ruteo_f8 as rr  # noqa: E402

PASO = 0.25           # mm de la grilla de ocupación
MARGEN = 0.15         # mm entre courtyards
PESO = {"+3V3": 0.6, "+3V3A": 0.8, "+VIN": 0.6}
NX, NY = int(u.LARGO / PASO), int(u.ALTO / PASO)


def _pad_es(info, pos, p, nombre):
    """¿El pad ubicado p = (x, y, des) es el pad 'DES.PIN'?"""
    des, pin = nombre.split(".")
    if p[2] != des:
        return False
    for q in u.pads_en_placa(info[des], pos[des]):
        if q["nombre"] == pin and abs(q["X"] - p[0]) < 1e-6 and abs(q["Y"] - p[1]) < 1e-6:
            return True
    return False


class Ocupacion:
    def __init__(self):
        self.g = np.zeros((NY, NX), dtype=np.int32)

    def _idx(self, b):
        x1 = max(0, int(math.floor((b[0] - MARGEN) / PASO)))
        y1 = max(0, int(math.floor((b[1] - MARGEN) / PASO)))
        x2 = min(NX, int(math.ceil((b[2] + MARGEN) / PASO)))
        y2 = min(NY, int(math.ceil((b[3] + MARGEN) / PASO)))
        return x1, y1, x2, y2

    def marcar(self, b):
        x1, y1, x2, y2 = self._idx(b)
        self.g[y1:y2, x1:x2] += 1
        self._suma = None

    def integral(self):
        s = np.zeros((NY + 1, NX + 1), dtype=np.int64)
        s[1:, 1:] = self.g.cumsum(0).cumsum(1)
        self._suma = s

    def libre(self, b):
        if b[0] < 0 or b[1] < 0 or b[2] > u.LARGO or b[3] > u.ALTO:
            return False
        x1 = int(math.floor(b[0] / PASO))
        y1 = int(math.floor(b[1] / PASO))
        x2 = int(math.ceil(b[2] / PASO))
        y2 = int(math.ceil(b[3] / PASO))
        s = self._suma
        return (s[y2, x2] - s[y1, x2] - s[y2, x1] + s[y1, x1]) == 0


def ubicar(info, fijas, orden, zona=None, radio=12.0, lam_cruce=4.0, verbose=False, solo=None, extra=None, cerca=None):
    """Devuelve dict con las posiciones de `orden` (y las fijas). `zona(d, caja) -> bool` restringe.

    `solo`: {designador: {redes}} = redes que atraen a esa pieza (p. ej. una serie junto a un solo extremo).
    `extra`: lista de rectángulos (x1, y1, x2, y2) prohibidos además de los courtyards (p. ej. cautín de K1)."""
    solo = solo or {}
    cerca = cerca or {}   # {designador: ['U4.2', ...]}: solo esos pads atraen (desacoples, pull-ups)
    pos = dict(fijas)
    occ = Ocupacion()
    for d, p in pos.items():
        occ.marcar(u.caja_en_placa(info[d], p))
    for hx, hy in u.AGUJEROS:
        occ.marcar((hx - u.R_AGUJERO - 0.3, hy - u.R_AGUJERO - 0.3, hx + u.R_AGUJERO + 0.3, hy + u.R_AGUJERO + 0.3))
    for fx, fy in u.FIDUCIALES:
        occ.marcar((fx - 1.4, fy - 1.4, fx + 1.4, fy + 1.4))
    for r in (extra or []):
        occ.marcar(r)
    occ.integral()

    def pads_red(pos_actual):
        out = {}
        for d, p in pos_actual.items():
            for q in u.pads_en_placa(info[d], p):
                if q["red"] and q["red"] != "GND":
                    out.setdefault(q["red"], []).append((q["X"], q["Y"], d))
        return out

    import ratsnest_f8 as rn
    for d in orden:
        objetivo = pads_red(pos)
        if d in cerca:
            quiero = set(cerca[d])
            objetivo = {r: [p for p in lst if f"{p[2]}" in {q.split('.')[0] for q in quiero} and
                            any(_pad_es(info, pos, p, q) for q in quiero)] for r, lst in objetivo.items()}
        c = info[d]
        redes = [q["red"] for q in c["pads"] if q["red"] and q["red"] != "GND" and (d not in solo or q["red"] in solo[d])]
        destinos = [(x, y) for r in redes for (x, y, dd) in objetivo.get(r, []) if dd != d]
        if destinos:
            cx = sum(p[0] for p in destinos) / len(destinos)
            cy = sum(p[1] for p in destinos) / len(destinos)
        else:
            cx, cy = 90.0, 50.0
        cons_exist = [k for k in rn.conexiones(info, pos) if k["red"] != "GND"]
        mejores = []
        paso = 0.25
        n = int(radio / paso)
        for rot in (0, 90, 180, 270):
            for i in range(-n, n + 1):
                x = round((cx + i * paso) / paso) * paso
                for j in range(-n, n + 1):
                    y = round((cy + j * paso) / paso) * paso
                    b = u.caja_en_placa(c, (x, y, rot))
                    if not occ.libre(b):
                        continue
                    if zona and not zona(d, b):
                        continue
                    pads = u.pads_en_placa(c, (x, y, rot))
                    if any(q["smd"] and (q["X"] - q["SX"] / 2 < 5.0 or q["X"] + q["SX"] / 2 > u.LARGO - 5.0) for q in pads):
                        continue
                    costo = 0.0
                    for q in pads:
                        if not q["red"] or q["red"] == "GND" or q["red"] not in redes:
                            continue
                        cand = [(px, py) for (px, py, dd) in objetivo.get(q["red"], []) if dd != d]
                        if cand:
                            costo += PESO.get(q["red"], 1.0) * min(math.hypot(q["X"] - px, q["Y"] - py) for px, py in cand)
                    mejores.append((costo, x, y, rot))
        if not mejores:
            print(f"  ¡sin lugar para {d}!")
            continue
        mejores.sort()
        # entre los 60 más cortos, castigar los cruces nuevos de ratsnest (solo se rehacen las redes de la pieza)
        todos = {}
        for dd, p in pos.items():
            for q in u.pads_en_placa(info[dd], p):
                if q["red"]:
                    todos.setdefault(q["red"], []).append((q["X"], q["Y"], dd))
        elegido = None
        for costo, x, y, rot in mejores[:60]:
            nuevas = []
            pads_c = u.pads_en_placa(c, (x, y, rot))
            for r in set(redes):
                pts = [p for p in todos.get(r, []) if p[2] != d] + [(q["X"], q["Y"], d) for q in pads_c if q["red"] == r]
                for i, j in rn.mst(pts):
                    if pts[i][2] == d or pts[j][2] == d:
                        nuevas.append(((pts[i][0], pts[i][1]), (pts[j][0], pts[j][1]), r))
            ncr = 0
            for a1, b1, r in nuevas:
                for e in cons_exist:
                    if e["red"] == r or e["a"] in (a1, b1) or e["b"] in (a1, b1):
                        continue
                    if rr.se_cruzan(a1, b1, e["a"], e["b"]):
                        ncr += 1
            total = costo + lam_cruce * ncr
            if elegido is None or total < elegido[0]:
                elegido = (total, x, y, rot, ncr, costo)
        _, x, y, rot, ncr, costo = elegido
        pos[d] = (x, y, rot)
        occ.marcar(u.caja_en_placa(c, pos[d]))
        occ.integral()
        if verbose:
            print(f"  {d:5} -> ({x:6.2f}, {y:6.2f}, {rot:3d})  largo {costo:5.1f}  cruces nuevos {ncr}")
    return pos
