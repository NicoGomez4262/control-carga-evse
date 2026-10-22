# -*- coding: utf-8 -*-
"""F8: revisa el ruteo de EVSE_Monitor.PcbDoc sin abrir Altium (Altium CERRADO o guardado).

Lee el cobre (pads, pistas, arcos, vías, rellenos y keepouts) y hace un DRC propio con las mismas reglas
de reglas_f8.py:
- conexiones sin rutear (por red, uniendo el cobre que se toca en la misma capa; vías y pads THT en ambas),
- cortos (cobre de redes distintas que se toca) y distancias por regla (6,4 / 3,2 / 1,7 / 1,5 / 0,5 /
  0,145 / 0,2 mm), aparte las que vienen del propio footprint (pads de una misma pieza),
- cobre dentro de los keepouts de la barrera y del hueco red–isla, y distancia al borde (1,0 mm red, 0,3 resto),
- anchos de pista por red, vías (agujero, diámetro, anillo) y pistas colgando,
- las violaciones que Altium guardó (TClearanceViolation, TDiffPairsViolation) agrupadas por regla.

Formato (como lo lee KiCad, altium_parser_pcb): Tracks6 tipo 4 (capa [0], flags [1..2], red [3], polígono
[5], componente [7], x1 y1 x2 y2 [13..28], ancho [29]); Arcs6 tipo 1 (centro [13]/[17], radio [21],
ángulos double [25]/[33], ancho [41]); Vias6 tipo 3 (red [3], x y [13]/[17], diámetro [21], agujero [25]);
Fills6 tipo 6 (esquinas [13..28], rotación double [29]); Pads6 tipo 2 (6 bloques; geometría en el 5.º:
capa [0], red [3], componente [7], x y [13]/[17], tamaño [21]/[25], agujero [45], forma [49], rotación
double [52]; el 6.º, si está, trae formas alternativas [532] y radio de esquina en % [564]).
Capas: Top 1, Bottom 32, Keep-Out 56, Multi-Layer 74.

Uso: python docs/tools/revisar_ruteo_f8.py [--png]   (con --png dibuja docs/revisiones/F8_ruteo_revision.png)
"""
import math
import struct
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import altium_ole as ao  # noqa: E402
import pcblib  # noqa: E402
import revisar_pcb as rv  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RAIZ = Path(__file__).resolve().parents[2]
U = rv.U
O = 25.4                        # origen de la placa: (1000 mil, 1000 mil)
LARGO, ALTO = 130.0, 100.0
TOP, BOT, KEEPOUT, MULTI = 1, 32, 56, 74
TOL = 0.002

L1 = {"AC_L1", "AC_L1_F", "HV_D1", "HV_D2"}
L2 = {"AC_L2", "AC_L2_F", "HV_INP", "HV_DCDC", "HV_LDO"}


# ---------------------------------------------------------------- geometría
def d_pt_seg(p, a, b):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    t = 0.0 if L == 0 else max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L))
    return math.hypot(p[0] - ax - t * dx, p[1] - ay - t * dy)


def _orient(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def se_cruzan(a, b, c, d):
    o1, o2, o3, o4 = _orient(a, b, c), _orient(a, b, d), _orient(c, d, a), _orient(c, d, b)
    return (o1 > 0) != (o2 > 0) and (o3 > 0) != (o4 > 0) and o1 * o2 < 0 and o3 * o4 < 0


def d_seg_seg(a, b, c, d):
    if se_cruzan(a, b, c, d):
        return 0.0
    return min(d_pt_seg(a, c, d), d_pt_seg(b, c, d), d_pt_seg(c, a, b), d_pt_seg(d, a, b))


def dentro(p, poly):
    s = None
    n = len(poly)
    for i in range(n):
        o = _orient(poly[i], poly[(i + 1) % n], p)
        if abs(o) < 1e-12:
            continue
        if s is None:
            s = o > 0
        elif (o > 0) != s:
            return False
    return True


class Forma:
    """Núcleo (punto, segmento o polígono convexo) + radio: círculo, pista, rectángulo, rect. redondeado."""

    def __init__(self, tipo, pts, r):
        self.tipo, self.pts, self.r = tipo, pts, r
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        self.caja = (min(xs) - r, min(ys) - r, max(xs) + r, max(ys) + r)

    def aristas(self):
        if self.tipo == "poly":
            n = len(self.pts)
            return [(self.pts[i], self.pts[(i + 1) % n]) for i in range(n)]
        if self.tipo == "seg":
            return [(self.pts[0], self.pts[1])]
        return [(self.pts[0], self.pts[0])]


def distancia(f, g):
    if f.tipo == "poly" and dentro(g.pts[0], f.pts):
        d = 0.0
    elif g.tipo == "poly" and dentro(f.pts[0], g.pts):
        d = 0.0
    else:
        d = min(d_seg_seg(a, b, c, e) for a, b in f.aristas() for c, e in g.aristas())
    return d - f.r - g.r


def rect(cx, cy, sx, sy, rot, r=0.0):
    a = math.radians(rot)
    ca, sa = math.cos(a), math.sin(a)
    hx, hy = sx / 2 - r, sy / 2 - r
    pts = [(cx + x * ca - y * sa, cy + x * sa + y * ca) for x, y in ((-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy))]
    return Forma("poly", pts, r)


# ---------------------------------------------------------------- lectura
def _prims(stream, tipo, nb):
    data = ao.leer_stream(rv.PCB, stream)
    out, i = [], 0
    while i < len(data):
        t = data[i]
        i += 1
        bl, i = pcblib.bloques(data, i, nb)
        assert t == tipo, (stream, t)
        out.append(bl)
    return out


def _capas(capa):
    # la capa Keep-Out restringe Top y Bottom; un keepout en una capa de señal (flag), solo esa capa
    return {TOP, BOT} if capa in (MULTI, KEEPOUT) else {capa}


def cargar():
    comps = rv.texto("Components6/Data")
    orden = [ao.valor(c, "SOURCEDESIGNATOR") for c in comps]
    nets = [ao.valor(n, "NAME") for n in rv.texto("Nets6/Data")]
    clases = {ao.valor(c, "NAME"): {v for k, v in c if k.startswith("M") and k[1:].isdigit()}
              for c in rv.texto("Classes6/Data") if ao.valor(c, "KIND") == "0"}

    def red(g):
        n = struct.unpack_from("<H", g, 3)[0]
        return None if n == 0xFFFF else nets[n]

    def comp(g):
        c = struct.unpack_from("<H", g, 7)[0]
        return None if c == 0xFFFF else orden[c]

    objs = []
    # pads
    for k, bl in enumerate(_prims("Pads6/Data", 2, 6)):
        g = bl[4]
        nombre = bl[0][1:1 + bl[0][0]].decode("latin-1")
        x, y = (v * U - O for v in struct.unpack_from("<ii", g, 13))
        sx, sy = (v * U for v in struct.unpack_from("<ii", g, 21))
        hueco = struct.unpack_from("<i", g, 45)[0] * U
        forma = g[49]
        rot = struct.unpack_from("<d", g, 52)[0]
        cr = 0.0
        ext = bl[5]
        if len(ext) >= 596 and ext[532] == 9:
            cr = ext[564] / 100 * min(sx, sy) / 2
        if forma == 1 and abs(sx - sy) < 1e-3:
            f = Forma("pt", [(x, y)], sx / 2)
        elif forma == 1:
            L, W = max(sx, sy), min(sx, sy)
            a = math.radians(rot + (0 if sx >= sy else 90))
            h = (L - W) / 2
            f = Forma("seg", [(x - h * math.cos(a), y - h * math.sin(a)), (x + h * math.cos(a), y + h * math.sin(a))], W / 2)
        else:
            f = rect(x, y, sx, sy, rot, cr)
        objs.append(dict(tipo="pad", k=k, nombre=nombre, red=red(g), comp=comp(g), capas=_capas(g[0]),
                         formas=[f], x=x, y=y, sx=sx, sy=sy, hueco=hueco, keepout=False))
    # pistas
    for k, bl in enumerate(_prims("Tracks6/Data", 4, 1)):
        g = bl[0]
        if comp(g) is not None:
            continue
        x1, y1, x2, y2 = (v * U - O for v in struct.unpack_from("<iiii", g, 13))
        w = struct.unpack_from("<i", g, 29)[0] * U
        objs.append(dict(tipo="pista", k=k, red=red(g), comp=None, capas=_capas(g[0]), capa=g[0], ancho=w,
                         formas=[Forma("seg", [(x1, y1), (x2, y2)], w / 2)], keepout=g[2] == 2 or g[0] == KEEPOUT))
    # arcos
    for k, bl in enumerate(_prims("Arcs6/Data", 1, 1)):
        g = bl[0]
        if comp(g) is not None:
            continue
        cx, cy = (v * U - O for v in struct.unpack_from("<ii", g, 13))
        r = struct.unpack_from("<i", g, 21)[0] * U
        a1, a2 = struct.unpack_from("<dd", g, 25)
        w = struct.unpack_from("<i", g, 41)[0] * U
        if a2 < a1:
            a2 += 360
        n = max(2, int((a2 - a1) / 10) + 1)
        pts = [(cx + r * math.cos(math.radians(a1 + (a2 - a1) * i / n)), cy + r * math.sin(math.radians(a1 + (a2 - a1) * i / n)))
               for i in range(n + 1)]
        objs.append(dict(tipo="arco", k=k, red=red(g), comp=None, capas=_capas(g[0]), capa=g[0], ancho=w,
                         formas=[Forma("seg", [pts[i], pts[i + 1]], w / 2) for i in range(n)],
                         keepout=g[2] == 2 or g[0] == KEEPOUT))
    # vías
    for k, bl in enumerate(_prims("Vias6/Data", 3, 1)):
        g = bl[0]
        x, y = (v * U - O for v in struct.unpack_from("<ii", g, 13))
        dia = struct.unpack_from("<i", g, 21)[0] * U
        hueco = struct.unpack_from("<i", g, 25)[0] * U
        objs.append(dict(tipo="via", k=k, red=red(g), comp=None, capas={TOP, BOT}, x=x, y=y, dia=dia, hueco=hueco,
                         formas=[Forma("pt", [(x, y)], dia / 2)], keepout=False))
    # rellenos
    for k, bl in enumerate(_prims("Fills6/Data", 6, 1)):
        g = bl[0]
        if comp(g) is not None:
            continue
        x1, y1, x2, y2 = (v * U - O for v in struct.unpack_from("<iiii", g, 13))
        rot = struct.unpack_from("<d", g, 29)[0]
        f = rect((x1 + x2) / 2, (y1 + y2) / 2, abs(x2 - x1), abs(y2 - y1), rot)
        objs.append(dict(tipo="relleno", k=k, red=red(g), comp=None, capas=_capas(g[0]), capa=g[0],
                         formas=[f], keepout=g[2] == 2 or g[0] == KEEPOUT))
    # F1B (portafusible DNP sobre F1) se borró de la PCB el 22 oct: se revisa como si estuviera, con los pads
    # de F2B corridos 11,0 mm (F1 - F2), hasta que vuelva con Update PCB
    if "F1B" not in orden:
        for o in [o for o in objs if o["tipo"] == "pad" and o["comp"] == "F2B"]:
            q = dict(o, comp="F1B", red="AC_L1" if o["nombre"] == "1" else "AC_L1_F", x=o["x"] + 11.0, virtual=True,
                     formas=[Forma(f.tipo, [(p[0] + 11.0, p[1]) for p in f.pts], f.r) for f in o["formas"]])
            objs.append(q)
    for o in objs:
        cs = [f.caja for f in o["formas"]]
        o["caja"] = (min(c[0] for c in cs), min(c[1] for c in cs), max(c[2] for c in cs), max(c[3] for c in cs))
    return objs, clases


def regiones():
    """Cobre vertido de los polígonos (ShapeBasedRegions6, como lo lee KiCad): capa [0], red [3], polígono [5],
    huecos uint16 [14]; después el texto de propiedades (uint32 + texto), los vértices del contorno (uint32 n, y
    n+1 vértices de 37 bytes: redondo u8, x y int32, centro x y int32, radio int32, ángulos double) y cada hueco
    (uint32 n + n pares de doubles en unidades internas)."""
    nets = [ao.valor(n, "NAME") for n in rv.texto("Nets6/Data")]
    # el cobre vertido no guarda la red: es la de su polígono (índice en Polygons6)
    red_poli = [nets[int(ao.valor(p, "NET"))] for p in rv.texto("Polygons6/Data")]
    out = []
    for bl in _prims("ShapeBasedRegions6/Data", 11, 1):
        g = bl[0]
        capa, red, poli = g[0], struct.unpack_from("<H", g, 3)[0], struct.unpack_from("<H", g, 5)[0]
        nhuecos = struct.unpack_from("<H", g, 14)[0]
        i = 18
        ln = struct.unpack_from("<I", g, i)[0]
        i += 4 + ln
        n = struct.unpack_from("<I", g, i)[0]
        i += 4
        contorno = []
        for _ in range(n + 1):
            x, y = struct.unpack_from("<ii", g, i + 1)
            contorno.append((x * U - O, y * U - O))
            i += 37
        huecos = []
        for _ in range(nhuecos):
            m = struct.unpack_from("<I", g, i)[0]
            i += 4
            huecos.append([(struct.unpack_from("<d", g, i + 16 * k)[0] * U - O,
                            struct.unpack_from("<d", g, i + 16 * k + 8)[0] * U - O) for k in range(m)])
            i += 16 * m
        red = nets[red] if red != 0xFFFF else (red_poli[poli] if poli < len(red_poli) else None)
        out.append(dict(capa=capa, red=red, poligono=poli,
                        contorno=contorno, huecos=huecos))
    return out


def gnd_con_planos(objs):
    """Grupos de pads de GND contando el cobre vertido (los rayos de relieve ya están entre las pistas)."""
    from matplotlib.path import Path as Ruta
    regs = [r for r in regiones() if r["red"] == "GND"]
    gnd = [o for o in objs if o["red"] == "GND" and not o["keepout"]]
    padre = list(range(len(gnd) + len(regs)))

    def raiz(i):
        while padre[i] != i:
            padre[i] = padre[padre[i]]
            i = padre[i]
        return i

    for i, j in vecinos(gnd, TOL):
        if (gnd[i]["capas"] & gnd[j]["capas"]) and dist_obj(gnd[i], gnd[j]) <= TOL:
            padre[raiz(i)] = raiz(j)
    for k, r in enumerate(regs):
        ruta = Ruta(r["contorno"])
        huecos = [Ruta(h) for h in r["huecos"] if len(h) > 2]
        for i, o in enumerate(gnd):
            if r["capa"] not in o["capas"]:
                continue
            if o["tipo"] in ("pista", "arco"):
                pts = [o["formas"][0].pts[0], o["formas"][-1].pts[-1]]
            elif o["tipo"] == "via":
                pts = [(o["x"], o["y"])]
            else:
                pts = [p for f in o["formas"] for p in f.pts] + [(o["x"], o["y"])]
            for p in pts:
                if ruta.contains_point(p) and not any(h.contains_point(p) for h in huecos):
                    padre[raiz(i)] = raiz(len(gnd) + k)
                    break
    grupos = defaultdict(list)
    for i, o in enumerate(gnd):
        grupos[raiz(i)].append(o)
    con_pads = [g for g in grupos.values() if any(o["tipo"] == "pad" for o in g)]
    con_pads.sort(key=len, reverse=True)
    sueltas = [o for g in grupos.values() if not any(q["tipo"] == "pad" for q in g) for o in g if o["tipo"] == "via"]
    return regs, con_pads, sueltas


def dist_obj(a, b):
    return min(distancia(f, g) for f in a["formas"] for g in b["formas"])


def vecinos(objs, margen):
    """Pares (i, j) cuyas cajas están a menos de `margen` (rejilla de 4 mm)."""
    paso = 4.0
    celdas = defaultdict(list)
    for i, o in enumerate(objs):
        x0, y0, x1, y1 = o["caja"]
        for cx in range(int(math.floor(x0 / paso)), int(math.floor(x1 / paso)) + 1):
            for cy in range(int(math.floor(y0 / paso)), int(math.floor(y1 / paso)) + 1):
                celdas[(cx, cy)].append(i)
    vistos = set()
    alcance = int(math.ceil(margen / paso))
    for (cx, cy), lista in celdas.items():
        cerca = []
        for dx in range(-alcance, alcance + 1):
            for dy in range(-alcance, alcance + 1):
                cerca += celdas.get((cx + dx, cy + dy), [])
        for i in lista:
            a = objs[i]["caja"]
            for j in cerca:
                if j <= i or (i, j) in vistos:
                    continue
                b = objs[j]["caja"]
                if a[0] - margen > b[2] or b[0] - margen > a[2] or a[1] - margen > b[3] or b[1] - margen > a[3]:
                    continue
                vistos.add((i, j))
                yield i, j


# ---------------------------------------------------------------- reglas
def regla(a, b, clases):
    """Distancia exigida entre dos objetos de redes distintas (mismo orden de prioridad que reglas_f8.py)."""
    hv, ev = clases.get("HV_AC", set()), clases.get("EVSE_EXT", set())
    na, nb = a["red"], b["red"]
    if (na in hv) != (nb in hv):
        return 6.4, "HV_SELV"
    if (na in ev) != (nb in ev):
        return 6.4, "EVSE_resto"
    if (na in L1 and nb in L2) or (na in L2 and nb in L1):
        return 3.2, "L1_L2"
    if {na, nb} == {"EVSE_EN_A", "EVSE_EN_B"}:
        if a["tipo"] == "pad" and b["tipo"] == "pad" and a["comp"] == b["comp"] == "K1":
            return 1.7, "EVSE_pads_K1"
        return 1.5, "EVSE_A_B"
    if na in hv and nb in hv:
        return 0.5, "HV_interna"
    if a["tipo"] == "pad" and b["tipo"] == "pad" and a["comp"] == b["comp"] == "J5":
        return 0.145, "J5_pads"
    return 0.2, "Clearance"


def nombre(o):
    if o["tipo"] == "pad":
        return f"{o['comp'] or ''}.{o['nombre']}" if o["comp"] else f"pad {o['nombre']}"
    if o["tipo"] == "via":
        return f"vía ({o['x']:.2f}, {o['y']:.2f})"
    f = o["formas"][0].pts
    return f"{o['tipo']} ({f[0][0]:.2f}, {f[0][1]:.2f})"


def lugar(a, b):
    ca, cb = a["caja"], b["caja"]
    return ((max(ca[0], cb[0]) + min(ca[2], cb[2])) / 2, (max(ca[1], cb[1]) + min(ca[3], cb[3])) / 2)


# ---------------------------------------------------------------- revisión
def conectividad(objs):
    padre = list(range(len(objs)))

    def raiz(i):
        while padre[i] != i:
            padre[i] = padre[padre[i]]
            i = padre[i]
        return i

    cobre = [i for i, o in enumerate(objs) if not o["keepout"] and o["red"] is not None]
    sub = [objs[i] for i in cobre]
    for i, j in vecinos(sub, TOL):
        a, b = sub[i], sub[j]
        if a["red"] != b["red"] or not (a["capas"] & b["capas"]):
            continue
        if dist_obj(a, b) <= TOL:
            padre[raiz(cobre[i])] = raiz(cobre[j])
    grupos = defaultdict(lambda: defaultdict(list))
    for i in cobre:
        o = objs[i]
        grupos[o["red"]][raiz(i)].append(o)
    return grupos


def revisar(objs, clases):
    res = defaultdict(list)
    cobre = [o for o in objs if not o["keepout"] and (o["capas"] & {TOP, BOT})]
    keep = [o for o in objs if o["keepout"]]
    # conexiones
    for red, gs in sorted(conectividad(objs).items()):
        con_pads = [g for g in gs.values() if any(o["tipo"] == "pad" for o in g)]
        sin_pads = [g for g in gs.values() if not any(o["tipo"] == "pad" for o in g)]
        if len(con_pads) > 1:
            res["sin_rutear"].append((red, [sorted(nombre(o) for o in g if o["tipo"] == "pad") for g in con_pads]))
        for g in sin_pads:
            res["cobre_suelto"].append((red, [nombre(o) for o in g][:4], len(g)))
    # distancias entre redes distintas
    for i, j in vecinos(cobre, 6.5):
        a, b = cobre[i], cobre[j]
        if not (a["capas"] & b["capas"]):
            continue
        if a["red"] == b["red"] and a["red"] is not None:
            continue
        if a["red"] is None and b["red"] is None:
            continue
        g, nr = regla(a, b, clases)
        d = dist_obj(a, b)
        if d < g - 0.001:
            misma = a["tipo"] == b["tipo"] == "pad" and a["comp"] == b["comp"] and a["comp"]
            clave = "corto" if d <= TOL else ("footprint" if misma else "distancia")
            res[clave].append((nr, g, round(d, 3), nombre(a), a["red"], nombre(b), b["red"], lugar(a, b)))
    # keepouts
    for k in keep:
        for o in cobre:
            if not (o["capas"] & k["capas"]):
                continue
            if o["caja"][0] > k["caja"][2] + 6.5 or k["caja"][0] > o["caja"][2] + 6.5 \
                    or o["caja"][1] > k["caja"][3] + 6.5 or k["caja"][1] > o["caja"][3] + 6.5:
                continue
            d = dist_obj(o, k)
            if d < 0.0:
                res["en_keepout"].append((nombre(o), o["red"], round(d, 3)))
            elif d < 0.2:       # HV_SELV y EVSE_resto excluyen los keepouts (Not IsKeepOut): rige la general
                res["cerca_keepout"].append(("Clearance", 0.2, round(d, 3), nombre(o), o["red"]))
    # borde
    hv = clases.get("HV_AC", set()) | clases.get("EVSE_EXT", set())
    for o in cobre:
        x0, y0, x1, y1 = o["caja"]
        d = min(x0, LARGO - x1, y0, ALTO - y1)
        g = 1.0 if o["red"] in hv else 0.3
        if d < g:
            res["borde"].append((nombre(o), o["red"], round(d, 2), g))
    # pistas colgando
    for o in cobre:
        if o["tipo"] != "pista":
            continue
        for p in o["formas"][0].pts:
            punto = dict(formas=[Forma("pt", [p], 0.0)])
            toca = any(q is not o and q["red"] == o["red"] and (q["capas"] & o["capas"])
                       and q["caja"][0] - 0.1 <= p[0] <= q["caja"][2] + 0.1 and q["caja"][1] - 0.1 <= p[1] <= q["caja"][3] + 0.1
                       and dist_obj(punto, q) <= TOL for q in cobre)
            if not toca:
                res["colgando"].append((o["red"], round(p[0], 2), round(p[1], 2), round(o["ancho"], 2)))
    return res


def anchos(objs):
    por_red = defaultdict(Counter)
    for o in objs:
        if o["tipo"] in ("pista", "arco") and not o["keepout"] and o["red"]:
            por_red[o["red"]][(round(o["ancho"], 3), "T" if o["capa"] == TOP else "B")] += 1
    return por_red


def vias(objs):
    out = defaultdict(Counter)
    for o in objs:
        if o["tipo"] == "via":
            out[o["red"]][(round(o["hueco"], 3), round(o["dia"], 3))] += 1
    return out


def violaciones_altium():
    reglas = [(c, ao.valor(f, "NAME")) for c, f in rv.reglas()]
    out = {}
    for stream in ("TClearanceViolation/Data", "TDiffPairsViolation/Data"):
        try:
            regs = rv.texto(stream)
        except Exception:
            continue
        cnt = Counter()
        for r in regs:
            i = int(ao.valor(r, "RULEINDEX"))
            cnt[(reglas[i][1] if i < len(reglas) else i, ao.valor(r, "PRIM1ID"), ao.valor(r, "PRIM2ID"))] += 1
        out[stream.split("/")[0]] = cnt
    return out


def dibujar(objs, res, ruta):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon, Rectangle
    fig, ax = plt.subplots(figsize=(19.5, 15))
    ax.add_patch(Rectangle((0, 0), LARGO, ALTO, fill=False, lw=1.2, color="black"))
    for o in objs:
        if o["keepout"]:
            for f in o["formas"]:
                if f.tipo == "poly":
                    ax.add_patch(Polygon(f.pts, closed=True, color="#d9a6ff", alpha=0.35, lw=0))
            continue
        if not (o["capas"] & {TOP, BOT}):
            continue
        col = "#c0392b" if o["capas"] == {TOP} else ("#2e5cb8" if o["capas"] == {BOT} else "#b8860b")
        for f in o["formas"]:
            if f.tipo == "seg":
                ax.plot([f.pts[0][0], f.pts[1][0]], [f.pts[0][1], f.pts[1][1]], color=col, lw=max(0.4, f.r * 2 * 7.2),
                        solid_capstyle="round", alpha=0.8)
            elif f.tipo == "pt":
                ax.add_patch(plt.Circle(f.pts[0], f.r, color=col, alpha=0.8))
            else:
                ax.add_patch(Polygon(f.pts, closed=True, color=col, alpha=0.6, lw=f.r * 14))
    for clave, color in (("distancia", "#00b050"), ("corto", "#ff00ff")):
        for v in res.get(clave, []):
            x, y = v[-1]
            ax.add_patch(plt.Circle((x, y), 1.2, fill=False, color=color, lw=2))
    for red, grupos in res.get("sin_rutear", []):
        pass
    ax.set_xlim(-3, LARGO + 3)
    ax.set_ylim(-3, ALTO + 3)
    ax.set_aspect("equal")
    fig.tight_layout()
    fig.savefig(ruta, dpi=110)


def main():
    objs, clases = cargar()
    print(f"Objetos: {Counter(o['tipo'] for o in objs)}; keepouts: {sum(o['keepout'] for o in objs)}")
    print("\n== Violaciones guardadas por Altium (regla, objeto 1, objeto 2): cantidad")
    for s, cnt in violaciones_altium().items():
        for k, v in cnt.most_common():
            print(f"  {s}: {k}: {v}")
    res = revisar(objs, clases)
    print("\n== Sin rutear (grupos de pads de la misma red que no se tocan)")
    for red, gs in res["sin_rutear"]:
        print(f"  {red}: {len(gs)} grupos -> " + " | ".join(", ".join(g[:6]) + (" …" if len(g) > 6 else "") for g in gs))
    print("\n== Cobre suelto (sin pads):", res["cobre_suelto"][:20])
    for clave in ("corto", "distancia", "footprint"):
        print(f"\n== {clave}: {len(res[clave])}")
        for v in sorted(res[clave])[:80]:
            print("  ", v)
    print(f"\n== Cobre dentro de keepouts: {len(res['en_keepout'])}")
    for v in res["en_keepout"][:40]:
        print("  ", v)
    print(f"== A menos de 0,2 mm de un keepout: {len(res['cerca_keepout'])}")
    for v in res["cerca_keepout"][:20]:
        print("  ", v)
    print(f"\n== Borde: {res['borde'][:30]}")
    print(f"\n== Pistas colgando: {len(res['colgando'])}")
    for v in res["colgando"][:40]:
        print("  ", v)
    print("\n== Anchos por red (ancho, capa): cantidad")
    for red, c in sorted(anchos(objs).items()):
        print(f"  {red:12} " + "  ".join(f"{w:g}{l}×{n}" for (w, l), n in sorted(c.items())))
    print("\n== Vías por red (agujero, diámetro): cantidad")
    for red, c in sorted(vias(objs).items(), key=lambda t: str(t[0])):
        print(f"  {str(red):12} " + "  ".join(f"{h:g}/{d:g}×{n}" for (h, d), n in sorted(c.items())))
    if "--png" in sys.argv:
        ruta = RAIZ / "docs" / "revisiones" / "F8_ruteo_revision.png"
        dibujar(objs, res, ruta)
        print("\nDibujo:", ruta)


if __name__ == "__main__":
    main()
