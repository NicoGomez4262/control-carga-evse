# -*- coding: utf-8 -*-
"""Saca la lista de redes de un .SchDoc de Altium sin abrir Altium.

Uso:
    python docs/tools/lista_redes.py "<ruta>/02_ALIMENTACION.SchDoc" [-p]

-p  imprime también los parámetros de cada componente.
Necesita `pip install olefile`.

Lee el stream FileHeader (registros de texto «|CLAVE=valor|»). Conecta por geometría:
extremos de pines (ubicación + largo en la dirección del pin), vértices de cables,
uniones, etiquetas de red, puertos de alimentación y puertos (los dos extremos, con
WIDTH_FRAC). Un punto que cae sobre un tramo de cable se une a él (unión en T). Las redes
con el mismo nombre de etiqueta, puerto de alimentación o puerto se unen.
Marca como «¡SUELTO!» los pines que quedan solos en una red sin nombre (o «(No ERC)» si tienen la
marca de No ERC en la punta) y avisa de las redes con dos nombres y de las marcas No ERC puestas en
pines que sí están conectados.
"""
import sys
from collections import defaultdict

import olefile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DIRS = [(1, 0), (0, 1), (-1, 0), (0, -1)]  # derecha, arriba, izquierda, abajo


def registros(ruta):
    data = olefile.OleFileIO(ruta).openstream("FileHeader").read()
    i, out = 0, []
    while i + 4 <= len(data):
        ln = int.from_bytes(data[i:i + 2], "little")
        tipo = data[i + 3]
        cuerpo = data[i + 4:i + 4 + ln]
        i += 4 + ln
        rec = {}
        if tipo == 0:
            for kv in cuerpo.rstrip(b"\x00").decode("latin-1").split("|"):
                if "=" in kv:
                    k, v = kv.split("=", 1)
                    rec[k.upper()] = v
        out.append(rec)
    return out[1:]  # el primero es la cabecera; OWNERINDEX cuenta desde el siguiente


def mil(rec, clave):
    """Coordenada en mil (la unidad del archivo es 10 mil; _FRAC son 1/100000 de unidad)."""
    return int(rec.get(clave, 0) or 0) * 10 + int(rec.get(clave + "_FRAC", 0) or 0) / 10000.0


def lista_redes(ruta):
    recs = registros(ruta)
    comps = {i: r for i, r in enumerate(recs) if r.get("RECORD") == "1"}
    desig, params = {}, defaultdict(dict)
    for r in recs:
        if r.get("RECORD") == "34":
            desig[int(r["OWNERINDEX"])] = r.get("TEXT", "?")
        elif r.get("RECORD") == "41" and "OWNERINDEX" in r:
            params[int(r["OWNERINDEX"])][r.get("NAME", "")] = r.get("TEXT", "")

    pines = []
    for r in recs:
        if r.get("RECORD") != "2":
            continue
        dueño = int(r.get("OWNERINDEX", -1))
        c = comps.get(dueño)
        if c is None:
            continue
        if r.get("OWNERPARTID", "1") not in (c.get("CURRENTPARTID", "1"), "-1", "0"):
            continue
        if r.get("OWNERPARTDISPLAYMODE", "0") != c.get("DISPLAYMODE", "0"):
            continue
        largo = mil(r, "PINLENGTH")
        dx, dy = DIRS[int(r.get("PINCONGLOMERATE", 0)) & 3]
        x, y = mil(r, "LOCATION.X") + dx * largo, mil(r, "LOCATION.Y") + dy * largo
        nombre = r.get("NAME", "")
        num = r.get("DESIGNATOR", "?")
        pines.append((x, y, f"{desig.get(dueño, '?')}.{num}" + (f"({nombre})" if nombre and nombre != num else "")))

    cables = []
    for r in recs:
        if r.get("RECORD") == "27":
            n = int(r.get("LOCATIONCOUNT", 0))
            pts = [(mil(r, f"X{k}"), mil(r, f"Y{k}")) for k in range(1, n + 1)]
            cables += list(zip(pts, pts[1:]))
    uniones = [(mil(r, "LOCATION.X"), mil(r, "LOCATION.Y")) for r in recs if r.get("RECORD") == "29"]
    no_erc = {(round(mil(r, "LOCATION.X"), 1), round(mil(r, "LOCATION.Y"), 1)) for r in recs if r.get("RECORD") == "22"}

    etiquetas = []  # (x, y, tipo, texto)
    for r in recs:
        t = r.get("RECORD")
        x, y = mil(r, "LOCATION.X"), mil(r, "LOCATION.Y")
        if t == "25":
            etiquetas.append((x, y, "etiqueta", r.get("TEXT", "")))
        elif t == "17":
            etiquetas.append((x, y, "alim", r.get("TEXT", "")))
        elif t == "18":
            w = mil(r, "WIDTH")
            if int(r.get("STYLE", 0) or 0) >= 4:
                print(f"aviso: puerto vertical {r.get('NAME')} — revisar a mano")
                etiquetas.append((x, y, "puerto", r.get("NAME", "")))
            else:
                etiquetas.append((x, y, "puerto", r.get("NAME", "")))
                etiquetas.append((x + w, y, "puerto", r.get("NAME", "")))

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
    puntos |= {k(e[0], e[1]) for e in etiquetas} | {k(*u) for u in uniones}
    for p in puntos:
        for a, b in cables:
            if sobre(p, a, b):
                unir(p, k(*a))

    redes = defaultdict(lambda: {"pines": [], "nombres": set()})
    for x, y, txt in pines:
        redes[raiz(k(x, y))]["pines"].append(txt)
    for x, y, tipo, txt in etiquetas:
        redes[raiz(k(x, y))]["nombres"].add((tipo, txt))
    por_nombre = defaultdict(list)
    for r, n in redes.items():
        for _, txt in n["nombres"]:
            por_nombre[txt].append(r)
    for rs in por_nombre.values():
        for r in rs[1:]:
            unir(r, rs[0])
    final = defaultdict(lambda: {"pines": [], "nombres": set()})
    for r, n in redes.items():
        f = final[raiz(r)]
        f["pines"] += n["pines"]
        f["nombres"] |= n["nombres"]

    pines_no_erc = {txt for x, y, txt in pines if k(x, y) in no_erc}
    filas = []
    for n in final.values():
        nombres = sorted({txt for _, txt in n["nombres"]})
        tipos = {tipo for tipo, _ in n["nombres"]}
        filas.append((", ".join(nombres) or "(sin nombre)", sorted(n["pines"]), tipos, nombres))
    filas.sort()
    print(f"== {ruta}")
    for nombre, ps, tipos, nombres in filas:
        marca = ""
        if len(nombres) > 1:
            marca = "  ← ¡DOS NOMBRES!"
        if len(ps) == 1 and not nombres:
            marca = "  (No ERC)" if ps[0] in pines_no_erc else "  ← ¡SUELTO!"
        elif pines_no_erc & set(ps):
            marca += "  ← ¡No ERC en un pin conectado!"
        if not ps and "puerto" in tipos:
            marca = "  ← puerto sin conexión"
        print(f"{nombre}: {' '.join(ps)}{marca}")
    return comps, desig, params


if __name__ == "__main__":
    comps, desig, params = lista_redes(sys.argv[1])
    if "-p" in sys.argv:
        print("\nComponentes:")
        for i, c in sorted(comps.items(), key=lambda kv: desig.get(kv[0], "")):
            p = params.get(i, {})
            campos = ("Manufacturer_Name", "Manufacturer_Part_Number", "Value", "Supplier", "Supplier PN", "Assembly")
            print(f"  {desig.get(i, '?'):6s} {c.get('LIBREFERENCE', ''):22s} "
                  + " | ".join(f"{f}={p.get(f, '—')}" for f in campos))
