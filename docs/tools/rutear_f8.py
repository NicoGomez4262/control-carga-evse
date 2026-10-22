# -*- coding: utf-8 -*-
"""F8: termina el ruteo de EVSE_Monitor.PcbDoc respetando las reglas (Altium CERRADO).

1. Conexiones que faltan: ruteador A* en rejilla de 0,1 mm, dos capas, ángulos de 45°, que no pasa a menos
   de la distancia de cada regla (la misma tabla de revisar_ruteo_f8.regla) más medio ancho de pista; las vías
   cumplen la distancia en ambas capas y 0,4 mm entre agujeros. Bottom cuesta más en el lado SELV (es el
   plano de GND).
2. GND: una vía de 0,4/0,8 mm junto a cada pad SMD de GND, con una pista corta de 0,4 mm (los pads THT ya
   están en Bottom), y vías de costura cada ≈ 7,5 mm donde hay espacio.
3. Polígonos de GND en Top y Bottom sobre el lado SELV (x ≥ 52 mm); se vierten en Altium con Repour All.

Uso: python docs/tools/rutear_f8.py            # calcula, revisa y dibuja (no escribe)
     python docs/tools/rutear_f8.py --escribir # además respalda y escribe el PcbDoc (aplicar_ruteo_f8.py)
"""
import heapq
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import revisar_ruteo_f8 as rr  # noqa: E402

RAIZ = Path(__file__).resolve().parents[2]
PASO = 0.1
MARGEN = 0.03                  # holgura sobre cada regla por la discretización
TOP, BOT = rr.TOP, rr.BOT
SELV_X = 52.0                  # el plano y las vías de costura empiezan aquí (barrera hasta 51,4)
VIA_SENAL = (0.3, 0.6)
VIA_POT = (0.4, 0.8)
POTENCIA = {"AC_L1", "AC_L2", "AC_L1_F", "AC_L2_F", "+VIN", "VIN_ACDC", "VIN_BANCO", "+3V3", "+3V3A", "GND"}

# (red, ancho de pista) en el orden en que se rutean
FALTAN = [("NetLED6_2", 0.4), ("AMC_LDO", 0.4), ("HV_DCDC", 0.4), ("HV_LDO", 0.4), ("AC_L2_F", 0.5),
          ("VBUS", 0.25)]

# Cambios a mano sobre registros existentes (índice en Tracks6 / Vias6), sin borrar ninguno para no correr
# los índices: junto a U2 la vía de AMC_DIAG (pin 14) tapaba la salida de AMC_LDO (pin 13 → pin 16); la vía
# de AMC_DIAG pasa a la diagonal que va a R7 y AMC_LDO usa el lugar que deja libre.
MOD_PISTAS = {
    1574: dict(capa=BOT, x1=56.6, y1=66.489, x2=56.6, y2=63.9),
    1576: dict(capa=BOT, x1=56.6, y1=63.9, x2=54.991, y2=62.291),
    1577: dict(red="AMC_LDO", capa=TOP, x1=53.075, y1=64.635, x2=54.99, y2=64.635),
    2172: dict(x1=54.991, y1=48.768, x2=54.991, y2=62.291),
}
MOD_VIAS = {32: dict(x=56.6, y=66.489)}
NUEVAS_PISTAS = [
    # AMC_LDO: pin 13 → vía → Bottom → vía → la pista pin 16–C13
    dict(red="AMC_LDO", capa=BOT, x1=54.99, y1=64.635, x2=54.99, y2=67.35, ancho=0.4),
    dict(red="AMC_LDO", capa=TOP, x1=54.99, y1=67.35, x2=54.99, y2=68.445, ancho=0.4),
    # VBUS: A4 → B9 por Top; B4 → vía de D5 por Bottom, por debajo de la vía de USB_DN
    dict(red="VBUS", capa=TOP, x1=119.75, y1=89.42, x2=119.75, y2=90.40, ancho=0.25),
    dict(red="VBUS", capa=BOT, x1=117.3, y1=90.67, x2=117.3, y2=85.75, ancho=0.25),
    dict(red="VBUS", capa=BOT, x1=117.3, y1=85.75, x2=116.75, y2=85.2, ancho=0.25),
    dict(red="VBUS", capa=BOT, x1=116.75, y1=85.2, x2=116.75, y2=84.0, ancho=0.25),
    dict(red="VBUS", capa=BOT, x1=116.75, y1=84.0, x2=117.2, y2=83.55, ancho=0.25),
    dict(red="VBUS", capa=BOT, x1=117.2, y1=83.55, x2=118.0, y2=83.55, ancho=0.25),
    dict(red="VBUS", capa=BOT, x1=118.0, y1=83.55, x2=118.491, y2=84.041, ancho=0.25),
    dict(red="VBUS", capa=BOT, x1=118.491, y1=84.041, x2=118.491, y2=84.582, ancho=0.25),
]
NUEVAS_VIAS = [dict(red="AMC_LDO", x=54.99, y=64.635, hueco=0.3, dia=0.6),
               dict(red="AMC_LDO", x=54.99, y=67.35, hueco=0.3, dia=0.6)]
# En la zona de red, la Bottom pasa por debajo del lado L1: el lado L2 no rutea por Top entre los pads de F1/F1B
PROHIBIDO_TOP_L2 = (24.0, 42.0, 32.5, 69.0)


# ---------------------------------------------------------------- distancias vectorizadas
def dist_puntos(X, Y, f):
    """Distancia (con signo: negativa adentro) de los puntos (X, Y) a la forma f de revisar_ruteo_f8."""
    if f.tipo == "pt":
        d = np.hypot(X - f.pts[0][0], Y - f.pts[0][1])
    elif f.tipo == "seg":
        d = _d_seg(X, Y, f.pts[0], f.pts[1])
    else:
        n = len(f.pts)
        d = np.full(X.shape, np.inf)
        dentro = np.ones(X.shape, bool)
        signo = None
        for i in range(n):
            a, b = f.pts[i], f.pts[(i + 1) % n]
            d = np.minimum(d, _d_seg(X, Y, a, b))
            o = (b[0] - a[0]) * (Y - a[1]) - (b[1] - a[1]) * (X - a[0])
            if signo is None:
                area = sum(f.pts[k][0] * f.pts[(k + 1) % n][1] - f.pts[(k + 1) % n][0] * f.pts[k][1] for k in range(n))
                signo = 1 if area > 0 else -1
            dentro &= o * signo >= 0
        d = np.where(dentro, -d, d)
    return d - f.r


def _d_seg(X, Y, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = dx * dx + dy * dy
    if L == 0:
        return np.hypot(X - a[0], Y - a[1])
    t = np.clip(((X - a[0]) * dx + (Y - a[1]) * dy) / L, 0, 1)
    return np.hypot(X - a[0] - t * dx, Y - a[1] - t * dy)


class Rejilla:
    def __init__(self, x0, y0, x1, y1):
        self.x0, self.y0 = x0, y0
        self.nx = int(round((x1 - x0) / PASO)) + 1
        self.ny = int(round((y1 - y0) / PASO)) + 1
        self.X, self.Y = np.meshgrid(x0 + np.arange(self.nx) * PASO, y0 + np.arange(self.ny) * PASO, indexing="ij")

    def ventana(self, caja, m):
        i0 = max(0, int((caja[0] - m - self.x0) / PASO))
        i1 = min(self.nx, int((caja[2] + m - self.x0) / PASO) + 2)
        j0 = max(0, int((caja[1] - m - self.y0) / PASO))
        j1 = min(self.ny, int((caja[3] + m - self.y0) / PASO) + 2)
        return slice(i0, i1), slice(j0, j1)

    def xy(self, i, j):
        return self.x0 + i * PASO, self.y0 + j * PASO


def dist_obj_rejilla(rej, o, m, sl=None):
    si, sj = sl or rej.ventana(o["caja"], m)
    X, Y = rej.X[si, sj], rej.Y[si, sj]
    d = np.full(X.shape, np.inf)
    for f in o["formas"]:
        d = np.minimum(d, dist_puntos(X, Y, f))
    return (si, sj), d


# ---------------------------------------------------------------- mapas de bloqueo
def mapas(rej, objs, clases, red, media, rvia, hueco_via):
    """bloqueado[capa] para el eje de una pista de medio ancho `media`, y vía_no para una vía de radio rvia."""
    hv = clases["HV_AC"] | clases["EVSE_EXT"]
    sonda = dict(red=red, tipo="pista", comp=None)
    bloq = {TOP: np.zeros((rej.nx, rej.ny), bool), BOT: np.zeros((rej.nx, rej.ny), bool)}
    via_no = np.zeros((rej.nx, rej.ny), bool)
    for o in objs:
        if o["keepout"]:
            g = 0.2
        elif o["red"] == red:
            if o["tipo"] == "pad" and o["capas"] == {TOP}:     # nada de vías dentro de pads SMD
                (si, sj), d = dist_obj_rejilla(rej, o, rvia + 0.1)
                via_no[si, sj] |= d < rvia + 0.1
            if o.get("hueco", 0) > 0 or o["tipo"] == "via":
                pass
            else:
                continue
            g = None
        else:
            g, _ = rr.regla(sonda, o, clases)
        if g is not None:
            m = g + max(media, rvia) + MARGEN
            (si, sj), d = dist_obj_rejilla(rej, o, m)
            for c in (TOP, BOT):
                if c in o["capas"]:
                    bloq[c][si, sj] |= d < g + media + MARGEN
                    via_no[si, sj] |= d < g + rvia + MARGEN
        # agujero con agujero: 0,4 mm
        hueco = o.get("hueco", 0) if o["tipo"] in ("pad", "via") else 0
        if hueco > 0:
            cx, cy = o["x"], o["y"]
            si, sj = rej.ventana((cx, cy, cx, cy), hueco / 2 + hueco_via / 2 + 0.45)
            d = np.hypot(rej.X[si, sj] - cx, rej.Y[si, sj] - cy)
            via_no[si, sj] |= d < hueco / 2 + hueco_via / 2 + 0.4 + MARGEN
    # borde de la placa
    gb = 1.0 if red in hv else 0.3
    for c in (TOP, BOT):
        borde = np.minimum.reduce([rej.X, rr.LARGO - rej.X, rej.Y, rr.ALTO - rej.Y])
        bloq[c] |= borde < gb + media
    via_no |= np.minimum.reduce([rej.X, rr.LARGO - rej.X, rej.Y, rr.ALTO - rej.Y]) < gb + rvia
    via_no |= bloq[TOP] & False
    return bloq, via_no


# ---------------------------------------------------------------- A*
DIRS = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]


def astar(rej, bloq, via_no, inicio, meta, costo_capa, costo_via, giro=0.25):
    """inicio/meta: dict capa -> máscara booleana. Devuelve [(capa, i, j), ...] o None."""
    libre = {c: ~bloq[c] | inicio[c] | meta[c] for c in (TOP, BOT)}
    mi = {c: np.argwhere(meta[c]) for c in (TOP, BOT)}
    todos = np.vstack([v for v in mi.values() if len(v)])
    gi0, gj0 = todos.min(0)
    gi1, gj1 = todos.max(0)

    def h(i, j):
        dx = max(gi0 - i, 0, i - gi1)
        dy = max(gj0 - j, 0, j - gj1)
        return (max(dx, dy) + (math.sqrt(2) - 1) * min(dx, dy)) * PASO

    heap, g, padre = [], {}, {}
    for c in (TOP, BOT):
        for i, j in np.argwhere(inicio[c]):
            s = (c, int(i), int(j), 8)
            g[s] = 0.0
            heapq.heappush(heap, (h(i, j), 0.0, s))
    via_ok = ~via_no
    while heap:
        f, gc, s = heapq.heappop(heap)
        if gc > g.get(s, 1e18) + 1e-9:
            continue
        c, i, j, d = s
        if meta[c][i, j] and not inicio[c][i, j]:
            camino = [s]
            while s in padre:
                s = padre[s]
                camino.append(s)
            return [(c, i, j) for c, i, j, _ in reversed(camino)]
        for k, (di, dj) in enumerate(DIRS):
            ni, nj = i + di, j + dj
            if not (0 <= ni < rej.nx and 0 <= nj < rej.ny) or not libre[c][ni, nj]:
                continue
            if di and dj and not (libre[c][i + di, j] or libre[c][i, j + dj]):
                continue
            paso = PASO * (math.sqrt(2) if di and dj else 1.0) * costo_capa[c]
            if d != 8 and d != k:
                dd = min((d - k) % 8, (k - d) % 8)
                if dd > 1:
                    continue            # solo giros de 45°
                paso += giro
            ns = (c, ni, nj, k)
            ng = gc + paso
            if ng < g.get(ns, 1e18):
                g[ns] = ng
                padre[ns] = s
                heapq.heappush(heap, (ng + h(ni, nj), ng, ns))
        if via_ok[i, j]:
            oc = BOT if c == TOP else TOP
            if libre[oc][i, j]:
                ns = (oc, i, j, 8)
                ng = gc + costo_via
                if ng < g.get(ns, 1e18):
                    g[ns] = ng
                    padre[ns] = s
                    heapq.heappush(heap, (ng + h(i, j), ng, ns))
    return None


def a_primitivas(rej, camino, red, ancho, via):
    """Camino de celdas -> pistas rectas (se juntan los tramos colineales) y vías en los cambios de capa."""
    pistas, vias = [], []
    tramo = [camino[0]]
    for p in camino[1:]:
        if p[0] != tramo[-1][0]:
            _cerrar(rej, tramo, red, ancho, pistas)
            vias.append(dict(red=red, x=rej.xy(p[1], p[2])[0], y=rej.xy(p[1], p[2])[1], hueco=via[0], dia=via[1]))
            tramo = [p]
        else:
            tramo.append(p)
    _cerrar(rej, tramo, red, ancho, pistas)
    return pistas, vias


def _cerrar(rej, tramo, red, ancho, pistas):
    if len(tramo) < 2:
        return
    pts = [tramo[0]]
    for k in range(1, len(tramo) - 1):
        a, b, c = pts[-1], tramo[k], tramo[k + 1]
        d1 = (np.sign(b[1] - a[1]), np.sign(b[2] - a[2]))
        d2 = (np.sign(c[1] - b[1]), np.sign(c[2] - b[2]))
        if d1 != d2:
            pts.append(b)
    pts.append(tramo[-1])
    for a, b in zip(pts, pts[1:]):
        x1, y1 = rej.xy(a[1], a[2])
        x2, y2 = rej.xy(b[1], b[2])
        pistas.append(dict(red=red, capa=a[0], x1=x1, y1=y1, x2=x2, y2=y2, ancho=ancho))


# ---------------------------------------------------------------- objetos nuevos
def obj_pista(p):
    f = rr.Forma("seg", [(p["x1"], p["y1"]), (p["x2"], p["y2"])], p["ancho"] / 2)
    return dict(tipo="pista", k=-1, red=p["red"], comp=None, capas={p["capa"]}, capa=p["capa"], ancho=p["ancho"],
                formas=[f], keepout=False, caja=f.caja, nuevo=True)


def obj_via(v):
    f = rr.Forma("pt", [(v["x"], v["y"])], v["dia"] / 2)
    return dict(tipo="via", k=-1, red=v["red"], comp=None, capas={TOP, BOT}, x=v["x"], y=v["y"], dia=v["dia"],
                hueco=v["hueco"], formas=[f], keepout=False, caja=f.caja, nuevo=True)


def mascara_objs(rej, lista):
    m = {TOP: np.zeros((rej.nx, rej.ny), bool), BOT: np.zeros((rej.nx, rej.ny), bool)}
    for o in lista:
        (si, sj), d = dist_obj_rejilla(rej, o, 0.0)
        for c in (TOP, BOT):
            if c in o["capas"]:
                m[c][si, sj] |= d <= -0.02
    return m


def rutear_red(objs, clases, red, ancho, nuevos):
    hv = clases["HV_AC"] | clases["EVSE_EXT"]
    via = VIA_POT if red in POTENCIA else VIA_SENAL
    for vuelta in range(12):
        grupos = [g for g in rr.conectividad(objs)[red].values() if any(o["tipo"] == "pad" for o in g)]
        if len(grupos) < 2:
            return True
        grupos.sort(key=len, reverse=True)
        arbol = grupos[0]
        resto = [o for g in grupos[1:] for o in g]
        cajas = [o["caja"] for g in grupos for o in g]
        caja = (max(0, min(c[0] for c in cajas) - 8), max(0, min(c[1] for c in cajas) - 8),
                min(rr.LARGO, max(c[2] for c in cajas) + 8), min(rr.ALTO, max(c[3] for c in cajas) + 8))
        rej = Rejilla(*caja)
        bloq, via_no = mapas(rej, objs, clases, red, ancho / 2, via[1] / 2, via[0])
        if red in rr.L2:
            x0, y0, x1, y1 = PROHIBIDO_TOP_L2
            bloq[TOP] |= (rej.X >= x0) & (rej.X <= x1) & (rej.Y >= y0) & (rej.Y <= y1)
        ini, meta = mascara_objs(rej, arbol), mascara_objs(rej, resto)
        selv = red not in hv
        costo = {TOP: 1.0, BOT: 3.0 if selv else 1.2}
        camino = astar(rej, bloq, via_no, ini, meta, costo, costo_via=4.0)
        if camino is None:
            print(f"  {red}: sin camino entre {len(grupos)} grupos")
            return False
        pistas, vias = a_primitivas(rej, camino, red, ancho, via)
        for p in pistas:
            o = obj_pista(p)
            objs.append(o)
            nuevos["pistas"].append(p)
        for v in vias:
            objs.append(obj_via(v))
            nuevos["vias"].append(v)
        print(f"  {red}: {len(pistas)} pistas, {len(vias)} vías")
    return False


# ---------------------------------------------------------------- GND
def vias_gnd(objs, clases, nuevos):
    """Una vía de GND junto a cada pad SMD de GND que no tenga ya una (pista de 0,4 mm hasta 3 mm)."""
    pads = [o for o in objs if o["tipo"] == "pad" and o["red"] == "GND" and o["capas"] == {TOP}]
    hechos = 0
    for p in sorted(pads, key=lambda o: (o["x"], o["y"])):
        caja = (max(0, p["x"] - 4), max(0, p["y"] - 4), min(rr.LARGO, p["x"] + 4), min(rr.ALTO, p["y"] + 4))
        rej = Rejilla(*caja)
        # ya conectado a una vía o pad THT de GND por cobre de Top
        grupo = None
        for g in rr.conectividad([o for o in objs if o["red"] == "GND"])["GND"].values():
            if p in g:
                grupo = g
                break
        if any(o["tipo"] == "via" or (o["tipo"] == "pad" and BOT in o["capas"]) for o in grupo):
            continue
        r_pad = max(p["sx"], p["sy"]) / 2
        if r_pad > 4:                                   # contacto de la pila: la ventana sigue al pad
            caja = (max(0, p["x"] - r_pad - 4), max(0, p["y"] - r_pad - 4),
                    min(rr.LARGO, p["x"] + r_pad + 4), min(rr.ALTO, p["y"] + r_pad + 4))
            rej = Rejilla(*caja)
        camino = None
        for via, ancho in ((VIA_POT, 0.4), (VIA_SENAL, 0.3)):     # si no cabe la de 0,4/0,8, la de 0,3/0,6
            bloq, via_no = mapas(rej, objs, clases, "GND", ancho / 2, via[1] / 2, via[0])
            ini = mascara_objs(rej, [p])
            (si, sj), d_pad = dist_obj_rejilla(rej, p, 0.0, (slice(0, rej.nx), slice(0, rej.ny)))
            meta = {TOP: ~via_no & ~bloq[TOP] & ~ini[TOP] & (d_pad <= 1.6), BOT: np.zeros_like(via_no)}
            if not meta[TOP].any():
                continue
            camino = astar(rej, bloq, via_no, ini, meta, {TOP: 1.0, BOT: 99.0}, costo_via=99.0, giro=0.1)
            if camino is not None:
                largo = sum(math.hypot(a[1] - b[1], a[2] - b[2]) for a, b in zip(camino, camino[1:])) * PASO
                if largo <= 2.5:            # una vía lejos (pista larga y con vueltas) no sirve: polígono
                    break
                camino = None
        if camino is None:
            print(f"  GND: sin lugar para la vía de {rr.nombre(p)} (queda para el polígono de Top)")
            continue
        pistas, _ = a_primitivas(rej, camino, "GND", ancho, via)
        fin = camino[-1]
        x, y = rej.xy(fin[1], fin[2])
        v = dict(red="GND", x=x, y=y, hueco=via[0], dia=via[1])
        for q in pistas:
            objs.append(obj_pista(q))
            nuevos["pistas"].append(q)
        objs.append(obj_via(v))
        nuevos["vias"].append(v)
        hechos += 1
    print(f"  GND: {hechos} vías junto a pads")


def vias_costura(objs, clases, nuevos, paso=7.5, holgura=0.8):
    """Vías de GND en una rejilla de `paso` mm sobre el SELV donde no hay cobre ajeno a menos de `holgura` mm."""
    rej = Rejilla(SELV_X, 0.0, rr.LARGO, rr.ALTO)
    _, via_no = mapas(rej, objs, clases, "GND", 0.2, VIA_POT[1] / 2 + holgura - 0.2, VIA_POT[0])
    # nada debajo de la antena ni pegado al borde
    lejos_borde = np.minimum.reduce([rej.X - SELV_X, rr.LARGO - rej.X, rej.Y, rr.ALTO - rej.Y]) >= 1.5
    ok = ~via_no & lejos_borde
    n = 0
    for x in np.arange(SELV_X + 1.5, rr.LARGO - 1.0, paso):
        for y in np.arange(2.0, rr.ALTO - 1.0, paso):
            i, j = int(round((x - SELV_X) / PASO)), int(round(y / PASO))
            mejor = None
            for r in range(0, 16):          # busca el lugar libre más cercano (hasta 1,5 mm)
                for di in range(-r, r + 1):
                    for dj in (-r, r) if abs(di) != r else range(-r, r + 1):
                        ii, jj = i + di, j + dj
                        if 0 <= ii < rej.nx and 0 <= jj < rej.ny and ok[ii, jj]:
                            mejor = (ii, jj)
                            break
                    if mejor:
                        break
                if mejor:
                    break
            if not mejor:
                continue
            vx, vy = rej.xy(*mejor)
            v = dict(red="GND", x=vx, y=vy, hueco=VIA_POT[0], dia=VIA_POT[1], costura=True)
            objs.append(obj_via(v))
            nuevos["vias"].append(v)
            n += 1
            # que la siguiente no quede encima
            d = np.hypot(rej.X - vx, rej.Y - vy)
            ok &= d >= 2.0
    print(f"  GND: {n} vías de costura")


# ---------------------------------------------------------------- polígonos
def poligonos():
    """Contorno de los dos polígonos de GND (mm, origen de la placa)."""
    x0, x1, y0, y1 = SELV_X, rr.LARGO - 0.5, 0.5, rr.ALTO - 0.5
    contorno = [(x0, y0), (x0, y1), (x1, y1), (x1, y0)]
    return [dict(capa="TOP", nombre="Top Layer-GND", contorno=contorno, indice=1),
            dict(capa="BOTTOM", nombre="Bottom Layer-GND", contorno=contorno, indice=2)]


# ---------------------------------------------------------------- revisión de lo nuevo
def revisar_nuevos(objs, clases):
    nuevos = [o for o in objs if o.get("nuevo")]
    malos = []
    for o in nuevos:
        for q in objs:
            if q is o or q["keepout"] and False:
                continue
            if q["red"] == o["red"] and q["red"] is not None and not q["keepout"]:
                continue
            if not (o["capas"] & q["capas"]) or (o["keepout"] and q["keepout"]):
                continue
            c1, c2 = o["caja"], q["caja"]
            if c1[0] > c2[2] + 6.5 or c2[0] > c1[2] + 6.5 or c1[1] > c2[3] + 6.5 or c2[1] > c1[3] + 6.5:
                continue
            g = 0.2 if (q["keepout"] or o["keepout"]) else rr.regla(o, q, clases)[0]
            d = rr.dist_obj(o, q)
            if d < g - 0.001:
                malos.append((rr.nombre(o), o["red"], rr.nombre(q), q["red"], round(d, 3), g))
    # agujero con agujero
    huecos = [o for o in objs if o["tipo"] in ("pad", "via") and o.get("hueco", 0) > 0]
    for o in nuevos:
        if o["tipo"] != "via":
            continue
        for q in huecos:
            if q is o:
                continue
            d = math.hypot(o["x"] - q["x"], o["y"] - q["y"]) - o["hueco"] / 2 - q["hueco"] / 2
            if d < 0.4 - 0.001:
                malos.append((rr.nombre(o), "agujero", rr.nombre(q), q["red"], round(d, 3), 0.4))
    return malos


def dibujar(objs, ruta, polis):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon, Rectangle
    fig, ax = plt.subplots(figsize=(19.5, 15))
    ax.add_patch(Rectangle((0, 0), rr.LARGO, rr.ALTO, fill=False, lw=1.2, color="black"))
    for pz in polis:
        ax.add_patch(Polygon(pz["contorno"], closed=True, fill=False, ls="--", color="#1a7f37", lw=1.2))
    for o in objs:
        if o["keepout"] or not (o["capas"] & {TOP, BOT}):
            continue
        nuevo = o.get("nuevo")
        col = ("#ff00ff" if nuevo else "#c0392b") if o["capas"] == {TOP} else \
              (("#00a0ff" if nuevo else "#2e5cb8") if o["capas"] == {BOT} else ("#00c853" if nuevo else "#b8860b"))
        for f in o["formas"]:
            if f.tipo == "seg":
                ax.plot([f.pts[0][0], f.pts[1][0]], [f.pts[0][1], f.pts[1][1]], color=col,
                        lw=max(0.5, f.r * 2 * 7.2), solid_capstyle="round", alpha=0.85)
            elif f.tipo == "pt":
                ax.add_patch(plt.Circle(f.pts[0], f.r, color=col, alpha=0.9))
            else:
                ax.add_patch(Polygon(f.pts, closed=True, color=col, alpha=0.5, lw=0))
    ax.set_xlim(-2, rr.LARGO + 2)
    ax.set_ylim(-2, rr.ALTO + 2)
    ax.set_aspect("equal")
    fig.tight_layout()
    fig.savefig(ruta, dpi=110)


def aplicar_cambios(objs, nuevos):
    """Cambios a mano: modifica los objetos existentes (se escriben en su mismo registro) y agrega los nuevos."""
    por_k = {(o["tipo"], o["k"]): o for o in objs if o["k"] >= 0}
    for k, m in MOD_PISTAS.items():
        o = por_k[("pista", k)]
        o.update({c: v for c, v in m.items() if c in ("red", "capa")})
        o["capas"] = {o["capa"]}
        f = rr.Forma("seg", [(m["x1"], m["y1"]), (m["x2"], m["y2"])], o["ancho"] / 2)
        o["formas"], o["caja"], o["nuevo"] = [f], f.caja, True
    for k, m in MOD_VIAS.items():
        o = por_k[("via", k)]
        o.update(m)
        f = rr.Forma("pt", [(o["x"], o["y"])], o["dia"] / 2)
        o["formas"], o["caja"], o["nuevo"] = [f], f.caja, True
    for p in NUEVAS_PISTAS:
        objs.append(obj_pista(p))
        nuevos["pistas"].append(p)
    for v in NUEVAS_VIAS:
        objs.append(obj_via(v))
        nuevos["vias"].append(v)
    nuevos["mod_pistas"], nuevos["mod_vias"] = MOD_PISTAS, MOD_VIAS


def anillos_fiduciales(objs, nuevos):
    """Anillo de keepout de Top alrededor de cada fiducial (arco en Top con el flag de keepout: solo restringe Top):
    el polígono no entra a la abertura de máscara (Ø 2 mm) y la cámara de PCBWay ve el fiducial limpio. Interior a
    1,0 mm del centro, exterior hasta 2,0 mm o hasta 0,25 mm del cobre de Top más cercano."""
    for f in [o for o in objs if o["tipo"] == "pad" and o["red"] is None and o["nombre"].startswith("FID")]:
        punto = dict(formas=[rr.Forma("pt", [(f["x"], f["y"])], 0.0)])
        cerca = min(rr.dist_obj(punto, o) for o in objs
                    if o is not f and not o["keepout"] and TOP in o["capas"]
                    and o["caja"][0] < f["x"] + 6 and o["caja"][2] > f["x"] - 6
                    and o["caja"][1] < f["y"] + 6 and o["caja"][3] > f["y"] - 6)
        interior, exterior = 1.0, min(2.0, cerca - 0.25)
        if exterior - interior < 0.2:
            print(f"  {f['nombre']}: sin lugar para el anillo (cobre a {cerca:.2f} mm)")
            continue
        r, w = (interior + exterior) / 2, exterior - interior
        n = 36
        pts = [(f["x"] + r * math.cos(2 * math.pi * i / n), f["y"] + r * math.sin(2 * math.pi * i / n)) for i in range(n + 1)]
        formas = [rr.Forma("seg", [pts[i], pts[i + 1]], w / 2) for i in range(n)]
        cs = [g.caja for g in formas]
        objs.append(dict(tipo="arco", k=-1, red=None, comp=None, capas={TOP}, capa=TOP, ancho=w,
                         formas=formas, keepout=True, nuevo=True,
                         caja=(min(c[0] for c in cs), min(c[1] for c in cs), max(c[2] for c in cs), max(c[3] for c in cs))))
        nuevos["anillos"].append(dict(x=f["x"], y=f["y"], r=r, ancho=w))
        print(f"  {f['nombre']}: anillo de keepout de {interior:.1f} a {exterior:.2f} mm")


def calcular(objs, clases):
    nuevos = {"pistas": [], "vias": [], "anillos": []}
    aplicar_cambios(objs, nuevos)
    print("Conexiones que faltan:")
    for red, ancho in FALTAN:
        rutear_red(objs, clases, red, ancho, nuevos)
    print("Fiduciales:")
    anillos_fiduciales(objs, nuevos)
    print("GND:")
    vias_gnd(objs, clases, nuevos)
    vias_costura(objs, clases, nuevos)
    return nuevos


def main():
    objs, clases = rr.cargar()
    nuevos = calcular(objs, clases)
    malos = revisar_nuevos(objs, clases)
    print(f"\nNuevos: {len(nuevos['pistas'])} pistas, {len(nuevos['vias'])} vías; problemas: {len(malos)}")
    for m in malos[:30]:
        print("  ", m)
    pend = {r: len([g for g in gs.values() if any(o['tipo'] == 'pad' for o in g)])
            for r, gs in rr.conectividad(objs).items()}
    print("Redes con más de un grupo (sin GND):", {r: n for r, n in pend.items() if n > 1 and r != "GND"})
    ruta = RAIZ / "docs" / "revisiones" / "F8_ruteo_completado.png"
    dibujar(objs, ruta, poligonos())
    print("Dibujo:", ruta)
    if "--escribir" in sys.argv:
        if malos:
            sys.exit("Hay problemas: no se escribe.")
        import aplicar_ruteo_f8
        aplicar_ruteo_f8.escribir(nuevos, poligonos())


if __name__ == "__main__":
    main()
