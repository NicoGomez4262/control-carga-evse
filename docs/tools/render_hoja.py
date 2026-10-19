# -*- coding: utf-8 -*-
"""Dibuja un .SchDoc de Altium (o una zona) como SVG/PNG, sin abrir Altium.

Uso:
    python docs/tools/render_hoja.py "<ruta>.SchDoc" salida.png [x0 y0 x1 y1] [--escala 0.12]
Coordenadas en mil, como la barra de estado de Altium. Sin zona, dibuja la hoja completa.
Sirve para revisar cambios hechos por script o el avance de una hoja antes de exportar el PDF.
Es una aproximación (símbolos de puertos y textos simplificados), no un reemplazo del PDF.
"""
import math
import sys
from pathlib import Path

import altium_ole as ao

DIRS = [(1, 0), (0, 1), (-1, 0), (0, -1)]


def rgb(c, defecto="#000080"):
    if c is None:
        return defecto
    c = int(c)
    return f"#{c & 0xFF:02x}{(c >> 8) & 0xFF:02x}{(c >> 16) & 0xFF:02x}"


def mil(f, k):
    return int(ao.valor(f, k, 0) or 0) * 10 + int(ao.valor(f, k + "_Frac", 0) or 0) / 10000.0


def esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class Lienzo:
    def __init__(self, x0, y0, x1, y1, escala):
        self.x0, self.y0, self.x1, self.y1, self.s = x0, y0, x1, y1, escala
        self.out = []

    def p(self, x, y):
        return round((x - self.x0) * self.s, 2), round((self.y1 - y) * self.s, 2)

    def linea(self, pts, color, ancho=10, dash=None, cerrar=False, relleno="none", opac=1):
        d = " ".join(f"{'M' if i == 0 else 'L'}{a} {b}" for i, (a, b) in enumerate(self.p(*q) for q in pts))
        if cerrar:
            d += " Z"
        extra = f' stroke-dasharray="{dash}"' if dash else ""
        self.out.append(f'<path d="{d}" fill="{relleno}" fill-opacity="{opac}" stroke="{color}" '
                        f'stroke-width="{max(ancho * self.s, 0.6):.2f}"{extra}/>')

    def circulo(self, x, y, r, color, relleno=None, ancho=8):
        a, b = self.p(x, y)
        self.out.append(f'<circle cx="{a}" cy="{b}" r="{max(r * self.s, 0.8):.2f}" fill="{relleno or "none"}" '
                        f'stroke="{color}" stroke-width="{max(ancho * self.s, 0.5):.2f}"/>')

    def texto(self, x, y, s, color, alto=80, rot=0, anchor="start", base="auto"):
        a, b = self.p(x, y)
        tr = f' transform="rotate({-90 * rot} {a} {b})"' if rot else ""
        self.out.append(f'<text x="{a}" y="{b}" fill="{color}" font-family="Times New Roman, serif" '
                        f'font-size="{alto * self.s:.2f}" text-anchor="{anchor}" dominant-baseline="{base}"{tr}>'
                        f'{esc(s)}</text>')

    def svg(self):
        w, h = (self.x1 - self.x0) * self.s, (self.y1 - self.y0) * self.s
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.0f}" height="{h:.0f}" '
                f'viewBox="0 0 {w:.1f} {h:.1f}"><rect width="100%" height="100%" fill="#fffdf8"/>'
                + "".join(self.out) + "</svg>")


def puerto_alim(L, x, y, ori, estilo, texto, color):
    dx, dy = DIRS[ori]
    px, py = -dy, dx  # perpendicular
    tallo = 100 if estilo in (0, 1, 2, 3) else 100
    L.linea([(x, y), (x + dx * tallo, y + dy * tallo)], color)
    ex, ey = x + dx * tallo, y + dy * tallo
    if estilo == 2:  # barra
        L.linea([(ex - px * 50, ey - py * 50), (ex + px * 50, ey + py * 50)], color, 14)
        fin = 20
    elif estilo == 0:  # círculo
        L.circulo(ex + dx * 20, ey + dy * 20, 20, color)
        fin = 50
    elif estilo == 1:  # flecha
        L.linea([(ex - px * 30, ey - py * 30), (ex + dx * 40, ey + dy * 40), (ex + px * 30, ey + py * 30)], color)
        fin = 50
    elif estilo in (4, 5, 6):  # tierras
        for k, w in enumerate((50, 33, 16)):
            cx, cy = ex + dx * 30 * k, ey + dy * 30 * k
            L.linea([(cx - px * w, cy - py * w), (cx + px * w, cy + py * w)], color, 12)
        fin = 100
    else:
        L.linea([(ex - px * 50, ey - py * 50), (ex + px * 50, ey + py * 50)], color)
        fin = 20
    tx, ty = ex + dx * (fin + 20), ey + dy * (fin + 20)
    if ori == 1:
        L.texto(tx, ty, texto, color, anchor="middle", base="auto")
    elif ori == 3:
        L.texto(tx, ty, texto, color, anchor="middle", base="hanging")
    elif ori == 0:
        L.texto(tx, ty, texto, color, anchor="start", base="middle")
    else:
        L.texto(tx, ty, texto, color, anchor="end", base="middle")


def dibujar(ruta, zona=None, escala=None):
    regs = ao.leer_registros(ao.leer_stream(ruta, "FileHeader"))
    r = [ao.campos(c) for _, c in regs[1:]]
    hoja = next((f for f in r if ao.valor(f, "RECORD") == "31"), [])
    tam = {int(k[4:]): int(v) for k, v in hoja if k.startswith("Size") and k[4:].isdigit()}
    W = int(ao.valor(hoja, "CustomX", 1653) or 1653) * 10
    H = int(ao.valor(hoja, "CustomY", 1169) or 1169) * 10
    x0, y0, x1, y1 = zona or (0, 0, W, H)
    escala = escala or (1600 / (x1 - x0))
    L = Lienzo(x0, y0, x1, y1, escala)
    comps = {i: f for i, f in enumerate(r) if ao.valor(f, "RECORD") == "1"}

    def visible(f):
        oi = ao.valor(f, "OwnerIndex")
        if oi is None or int(oi) not in comps:
            return True
        c = comps[int(oi)]
        parte = ao.valor(f, "OwnerPartId", "-1")
        if parte not in ("-1", "0", ao.valor(c, "CurrentPartId", "1")):
            return False
        return ao.valor(f, "OwnerPartDisplayMode", "0") == ao.valor(c, "DisplayMode", "0")

    def alto(f):
        return tam.get(int(ao.valor(f, "FontID", 1) or 1), 10) * 8

    for i, f in enumerate(r):
        rec = ao.valor(f, "RECORD")
        if not visible(f) or ao.valor(f, "OwnerIndex") == "1":  # plantilla y bloque de título fuera
            continue
        col = rgb(ao.valor(f, "Color"))
        if rec == "225":
            n = int(ao.valor(f, "LocationCount", 0))
            pts = [(mil(f, f"X{k}"), mil(f, f"Y{k}")) for k in range(1, n + 1)]
            L.linea(pts, col, 10, dash="6 4", cerrar=True, relleno=rgb(ao.valor(f, "AreaColor"), "#eeeeee"), opac=0.35)
    for i, f in enumerate(r):
        rec = ao.valor(f, "RECORD")
        if not visible(f) or ao.valor(f, "OwnerIndex") == "1":
            continue
        col = rgb(ao.valor(f, "Color"))
        if rec == "27":
            n = int(ao.valor(f, "LocationCount", 0))
            L.linea([(mil(f, f"X{k}"), mil(f, f"Y{k}")) for k in range(1, n + 1)], col, 10)
        elif rec in ("6", "7"):
            n = int(ao.valor(f, "LocationCount", 0))
            pts = [(mil(f, f"X{k}"), mil(f, f"Y{k}")) for k in range(1, n + 1)]
            relleno = rgb(ao.valor(f, "AreaColor")) if rec == "7" and ao.valor(f, "IsSolid") == "T" else "none"
            L.linea(pts, col, 8, cerrar=(rec == "7"), relleno=relleno)
        elif rec == "13":
            L.linea([(mil(f, "Location.X"), mil(f, "Location.Y")), (mil(f, "Corner.X"), mil(f, "Corner.Y"))], col, 8)
        elif rec in ("14", "10"):
            ax, ay, bx, by = mil(f, "Location.X"), mil(f, "Location.Y"), mil(f, "Corner.X"), mil(f, "Corner.Y")
            relleno = rgb(ao.valor(f, "AreaColor")) if ao.valor(f, "IsSolid") == "T" else "none"
            L.linea([(ax, ay), (bx, ay), (bx, by), (ax, by)], col, 8, cerrar=True, relleno=relleno)
        elif rec in ("12", "11", "8"):
            cx, cy, rad = mil(f, "Location.X"), mil(f, "Location.Y"), mil(f, "Radius")
            a0 = float(ao.valor(f, "StartAngle", 0) or 0)
            a1 = float(ao.valor(f, "EndAngle", 360) or 360)
            if rec == "8" or (a1 - a0) % 360 == 0:
                L.circulo(cx, cy, rad, col, rgb(ao.valor(f, "AreaColor")) if ao.valor(f, "IsSolid") == "T" else None)
            else:
                if a1 < a0:
                    a1 += 360
                pts = [(cx + rad * math.cos(math.radians(a)), cy + rad * math.sin(math.radians(a)))
                       for a in [a0 + (a1 - a0) * k / 16 for k in range(17)]]
                L.linea(pts, col, 8)
        elif rec == "2":
            x, y, lg = mil(f, "Location.X"), mil(f, "Location.Y"), mil(f, "PinLength")
            cg = int(ao.valor(f, "PinConglomerate", 0) or 0)
            dx, dy = DIRS[cg & 3]
            if cg & 0x04:  # oculto
                continue
            L.linea([(x, y), (x + dx * lg, y + dy * lg)], "#000000", 8)
            if cg & 0x10:  # número visible
                mx, my = x + dx * lg / 2, y + dy * lg / 2
                L.texto(mx - dy * 0, my + (8 if dx else 0), ao.valor(f, "Designator", ""), "#000000", 60,
                        rot=1 if dy else 0, anchor="middle", base="auto")
            if cg & 0x08 and ao.valor(f, "Name", "") != ao.valor(f, "Designator", ""):  # nombre visible
                nombre = (ao.valor(f, "Name", "") or "").replace("\\", "")
                L.texto(x - dx * 30, y - dy * 30, nombre, "#000000", 60, rot=1 if dy else 0,
                        anchor="end" if dx > 0 or dy > 0 else "start", base="middle")
        elif rec == "29":
            L.circulo(mil(f, "Location.X"), mil(f, "Location.Y"), 20, col, col)
        elif rec == "25":
            L.texto(mil(f, "Location.X"), mil(f, "Location.Y") + 10, ao.valor(f, "Text", ""), col, alto(f),
                    rot=int(ao.valor(f, "Orientation", 0) or 0))
        elif rec == "17":
            puerto_alim(L, mil(f, "Location.X"), mil(f, "Location.Y"), int(ao.valor(f, "Orientation", 0) or 0),
                        int(ao.valor(f, "Style", 0) or 0), ao.valor(f, "Text", ""), col)
        elif rec == "18":
            x, y, w = mil(f, "Location.X"), mil(f, "Location.Y"), mil(f, "Width")
            h = (mil(f, "Height") or 100) / 2
            st = int(ao.valor(f, "Style", 0) or 0)
            izq = st in (1, 3)
            der = st in (2, 3)
            pts = [(x + (h if izq else 0), y + h), (x + w - (h if der else 0), y + h), (x + w, y) if der else (x + w, y + h),
                   (x + w - (h if der else 0), y - h) if der else (x + w, y - h), (x + (h if izq else 0), y - h),
                   (x, y) if izq else (x, y - h)]
            if not der:
                pts = [(x + (h if izq else 0), y + h), (x + w, y + h), (x + w, y - h), (x + (h if izq else 0), y - h)] + ([(x, y)] if izq else [(x, y - h), (x, y + h)])
            L.linea(pts, col, 8, cerrar=True, relleno=rgb(ao.valor(f, "AreaColor"), "#ffff99"))
            L.texto(x + w / 2, y, ao.valor(f, "Name", ""), rgb(ao.valor(f, "TextColor"), "#800000"), 70,
                    anchor="middle", base="middle")
        elif rec == "22":
            x, y = mil(f, "Location.X"), mil(f, "Location.Y")
            L.linea([(x - 25, y - 25), (x + 25, y + 25)], "#ff0000", 8)
            L.linea([(x - 25, y + 25), (x + 25, y - 25)], "#ff0000", 8)
        elif rec == "43":
            x, y = mil(f, "Location.X"), mil(f, "Location.Y")
            L.linea([(x, y), (x, y + 80), (x + 90, y + 80), (x + 90, y + 140), (x, y + 140), (x, y + 80)], "#ff0000", 8)
            hijo = next((g for g in r if ao.valor(g, "OwnerIndex") == str(i)), None)
            if hijo:
                L.texto(x + 110, y + 100, ao.valor(hijo, "Text", ""), "#ff0000", 70)
        elif rec in ("34", "41", "4"):
            if ao.valor(f, "IsHidden") == "T" or rec == "41" and ao.valor(f, "OwnerIndex") is None:
                continue
            if rec == "41" and ao.valor(f, "Name") not in ("Comment", "Value"):
                continue
            L.texto(mil(f, "Location.X"), mil(f, "Location.Y"), ao.valor(f, "Text", ""), col, alto(f),
                    rot=int(ao.valor(f, "Orientation", 0) or 0))
    return L.svg()


def guardar(svg, salida):
    salida = Path(salida)
    if salida.suffix.lower() == ".svg":
        salida.write_text(svg, encoding="utf-8")
        return
    import pymupdf
    tmp = salida.with_suffix(".svg")
    tmp.write_text(svg, encoding="utf-8")
    doc = pymupdf.open(str(tmp))
    doc[0].get_pixmap(dpi=96).save(str(salida))
    tmp.unlink()


if __name__ == "__main__":
    a = sys.argv[1:]
    escala = None
    if "--escala" in a:
        k = a.index("--escala")
        escala = float(a[k + 1])
        del a[k:k + 2]
    zona = tuple(map(float, a[2:6])) if len(a) >= 6 else None
    guardar(dibujar(a[0], zona, escala), a[1])
    print("listo:", a[1])
