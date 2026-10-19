# -*- coding: utf-8 -*-
"""Qué redes cubre cada Blanket de un .SchDoc (o un polígono de prueba).

Regla de Altium: un Blanket cubre una red si una net label o un puerto de alimentación de esa
red queda debajo, o si un extremo de alguno de sus cables queda dentro del polígono.

Uso:
    python docs/tools/cobertura_blanket.py "<ruta>/03_MEDICION.SchDoc"
        → lista los Blankets que haya en la hoja (registros con vértices de tipo ≥ 200) y sus redes.
    python docs/tools/cobertura_blanket.py "<ruta>.SchDoc" "x1,y1;x2,y2;x3,y3;..."
        → prueba un polígono (coordenadas en mil, como la barra de estado de Altium).
Avisa cuando un punto cae justo sobre el borde (caso dudoso: conviene mover el vértice 100 mil).
"""
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import lista_redes as L  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def geometria(ruta):
    recs = L.registros(ruta)
    comps = {i: r for i, r in enumerate(recs) if r.get("RECORD") == "1"}
    desig = {int(r["OWNERINDEX"]): r.get("TEXT", "?") for r in recs if r.get("RECORD") == "34"}
    pines = []
    for r in recs:
        if r.get("RECORD") != "2":
            continue
        d = int(r.get("OWNERINDEX", -1))
        c = comps.get(d)
        if c is None or r.get("OWNERPARTID", "1") not in (c.get("CURRENTPARTID", "1"), "-1", "0"):
            continue
        if r.get("OWNERPARTDISPLAYMODE", "0") != c.get("DISPLAYMODE", "0"):
            continue
        largo = L.mil(r, "PINLENGTH")
        dx, dy = L.DIRS[int(r.get("PINCONGLOMERATE", 0)) & 3]
        pines.append((L.mil(r, "LOCATION.X") + dx * largo, L.mil(r, "LOCATION.Y") + dy * largo,
                      f"{desig.get(d, '?')}.{r.get('DESIGNATOR', '?')}"))
    polis = []
    for r in recs:
        if r.get("RECORD") == "27":
            n = int(r.get("LOCATIONCOUNT", 0))
            polis.append([(L.mil(r, f"X{k}"), L.mil(r, f"Y{k}")) for k in range(1, n + 1)])
    cables = [s for p in polis for s in zip(p, p[1:])]
    uniones = [(L.mil(r, "LOCATION.X"), L.mil(r, "LOCATION.Y")) for r in recs if r.get("RECORD") == "29"]
    ids = []
    for r in recs:
        t = r.get("RECORD")
        x, y = L.mil(r, "LOCATION.X"), L.mil(r, "LOCATION.Y")
        if t in ("25", "17"):
            ids.append((x, y, r.get("TEXT", "")))
        elif t == "18":
            ids.append((x, y, r.get("NAME", "")))
            if int(r.get("STYLE", 0) or 0) < 4:
                ids.append((x + L.mil(r, "WIDTH"), y, r.get("NAME", "")))
    padre = {}

    def raiz(a):
        padre.setdefault(a, a)
        while padre[a] != a:
            padre[a] = padre[padre[a]]
            a = padre[a]
        return a

    def unir(a, b):
        ra, rb = raiz(a), raiz(b)
        if ra != rb:
            padre[ra] = rb

    def k(x, y):
        return (round(x, 1), round(y, 1))

    def sobre(p, a, b):
        (px, py), (ax, ay), (bx, by) = p, a, b
        if abs((bx - ax) * (py - ay) - (by - ay) * (px - ax)) > 0.5:
            return False
        return min(ax, bx) - 0.1 <= px <= max(ax, bx) + 0.1 and min(ay, by) - 0.1 <= py <= max(ay, by) + 0.1

    for a, b in cables:
        unir(k(*a), k(*b))
    puntos = {k(*a) for c in cables for a in c} | {k(p[0], p[1]) for p in pines}
    puntos |= {k(e[0], e[1]) for e in ids} | {k(*u) for u in uniones}
    for p in puntos:
        for a, b in cables:
            if sobre(p, a, b):
                unir(p, k(*a))
    nombre = defaultdict(set)
    for x, y, t in ids:
        nombre[raiz(k(x, y))].add(t)
    por = defaultdict(list)
    for r, ns in list(nombre.items()):
        for n in ns:
            por[n].append(r)
    for rs in por.values():
        for r in rs[1:]:
            unir(r, rs[0])
    fin = defaultdict(set)
    for r, ns in nombre.items():
        fin[raiz(r)] |= ns
    pinred = defaultdict(list)
    for x, y, t in pines:
        pinred[raiz(k(x, y))].append(t)

    def nom(p):
        rr = raiz(k(*p))
        return ", ".join(sorted(fin.get(rr, []))) or ("sin nombre: " + " ".join(sorted(pinred.get(rr, []))))

    extremos = [(p[0], nom(p[0])) for p in polis] + [(p[-1], nom(p[-1])) for p in polis]
    idents = [((x, y), nom((x, y))) for x, y, _ in ids]
    blankets = []
    # Altium guarda los Blankets en el stream «Additional» (FileHeader se revisa por compatibilidad)
    import altium_ole as ao
    try:
        extra = [{k.upper(): v for k, v in ao.campos(c)} for _, c in ao.leer_registros(ao.leer_stream(ruta, "Additional"))[1:]]
    except Exception:
        extra = []
    for r in recs + extra:
        if int(r.get("RECORD", 0) or 0) >= 200 and "LOCATIONCOUNT" in r:
            n = int(r.get("LOCATIONCOUNT", 0))
            blankets.append((r.get("RECORD"), [(L.mil(r, f"X{k}"), L.mil(r, f"Y{k}")) for k in range(1, n + 1)]))
    return extremos, idents, blankets


def dentro(p, poly):
    x, y = p
    c = False
    for i in range(len(poly)):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % len(poly)]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            c = not c
    return c


def en_borde(p, poly):
    x, y = p
    for i in range(len(poly)):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % len(poly)]
        if (abs((x2 - x1) * (y - y1) - (y2 - y1) * (x - x1)) < 0.5
                and min(x1, x2) - 0.1 <= x <= max(x1, x2) + 0.1 and min(y1, y2) - 0.1 <= y <= max(y1, y2) + 0.1):
            return True
    return False


def informe(nombre, poly, extremos, idents):
    redes, borde = defaultdict(set), []
    for lista, tipo in ((idents, "identificador"), (extremos, "extremo de cable")):
        for p, n in lista:
            if en_borde(p, poly):
                borde.append((p, n, tipo))
            elif dentro(p, poly):
                redes[n].add(tipo)
    print(f"{nombre}: {poly}")
    for n in sorted(redes):
        print(f"    {n}   ({', '.join(sorted(redes[n]))})")
    for p, n, tipo in borde:
        print(f"    ¡EN EL BORDE! {p} {n} ({tipo})")


if __name__ == "__main__":
    extremos, idents, blankets = geometria(sys.argv[1])
    if len(sys.argv) > 2:
        for i, s in enumerate(sys.argv[2:], 1):
            poly = [tuple(map(float, v.split(","))) for v in s.split(";")]
            informe(f"Polígono {i}", poly, extremos, idents)
    else:
        if not blankets:
            print("La hoja no tiene Blankets.")
        for i, (tipo, poly) in enumerate(blankets, 1):
            informe(f"Blanket {i} (RECORD={tipo})", poly, extremos, idents)
