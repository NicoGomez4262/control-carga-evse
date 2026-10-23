# -*- coding: utf-8 -*-
"""F8: revisa los Gerber y taladros que generó Altium antes de mandarlos a PCBWay.

Lee los RS-274X (formato y unidades del encabezado; aperturas C, R y O; trazos, arcos G02/G03, flashes, regiones
G36/G37 y polaridad LPD/LPC) y los Excellon (INCH, LZ, 2:5; ranuras G85), los dibuja como los vería el visor de
PCBWay y los compara contra el PcbDoc:
- cada agujero del PcbDoc (vías y pads THT) tiene que estar en los taladros con el mismo diámetro, y viceversa;
- máscara: aberturas solo en pads (las vías van tapadas) y en los fiduciales;
- pasta: solo pads SMD, sin el contacto de BT1;
- cobre dentro del contorno y nada de cobre en la barrera (x = 45,6–51,2 mm, sin piezas que la crucen);
- contorno (Mechanical 1) cerrado de 130 × 100 mm con esquinas de R 4 mm (desde el 22 oct, `esquinas_f9.py`): el
  cobre tampoco puede pasar los arcos de las esquinas;
- el QR de la serigrafía de abajo (`marcas_f9.py`) se tiene que poder leer (con zxing-cpp).

Uso: python docs/tools/revisar_gerber_f8.py [carpeta]   (por defecto, Project Outputs del proyecto)
     Dibuja docs/revisiones/gerber/*.png
"""
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import revisar_ruteo_f8 as rr  # noqa: E402
import revisar_pcb as rv  # noqa: E402

RAIZ = Path(__file__).resolve().parents[2]
CARPETA = rv.PCB.parent / "Project Outputs for Control de Carga IoT"
SALIDA = RAIZ / "docs" / "revisiones" / "gerber"
NOMBRE = "EVSE_Monitor"
CAPAS = {"GTL": "Top Layer", "GBL": "Bottom Layer", "GTO": "Top Overlay", "GBO": "Bottom Overlay",
         "GTS": "Top Solder", "GBS": "Bottom Solder", "GTP": "Top Paste", "GBP": "Bottom Paste",
         "GM1": "Mechanical 1"}
MM = 25.4
R_ESQUINA = 4.0
CENTROS = [(R_ESQUINA, R_ESQUINA), (130 - R_ESQUINA, R_ESQUINA), (130 - R_ESQUINA, 100 - R_ESQUINA),
           (R_ESQUINA, 100 - R_ESQUINA)]


def fuera_de_esquina(x, y, r=0.0):
    """True si el punto (con radio r) pasa el arco de alguna esquina."""
    for cx, cy in CENTROS:
        sx, sy = (1 if cx > 65 else -1), (1 if cy > 50 else -1)
        if (x - cx) * sx > 0 and (y - cy) * sy > 0 and math.hypot(x - cx, y - cy) + r > R_ESQUINA + 0.01:
            return True
    return False


# ---------------------------------------------------------------- RS-274X
def leer_gerber(ruta):
    txt = ruta.read_text(encoding="latin-1")
    fmt = re.search(r"%FSLAX(\d)(\d)Y(\d)(\d)\*%", txt)
    dec = int(fmt.group(2))
    esc = MM if "%MOIN*%" in txt else 1.0
    ap = {}
    for m in re.finditer(r"%ADD(\d+)([CRO]),([\d.]+)(?:X([\d.]+))?(?:X([\d.]+))?\*%", txt):
        ap[int(m.group(1))] = (m.group(2), float(m.group(3)) * esc, float(m.group(4) or m.group(3)) * esc)
    prims = []          # (tipo, polaridad, datos)
    x = y = 0.0
    modo, actual, pol, region, contorno = "G01", None, "D", False, []
    cuerpo = re.sub(r"%[^%]*%", lambda m: m.group(0) if m.group(0).startswith(("%LP",)) else "", txt)
    for bloque in cuerpo.replace("\n", "").replace("\r", "").split("*"):
        b = bloque.strip().lstrip("%")          # «%LPC*%G36*»: el % de cierre queda pegado al bloque siguiente
        if not b or b.startswith("G04"):
            continue
        if b.startswith("LP"):
            pol = b[2]
            continue
        m = re.match(r"^G(\d+)", b)
        if m:
            g = int(m.group(1))
            if g in (1, 2, 3):
                modo = f"G0{g}"
            elif g == 36:
                region, contorno = True, []
            elif g == 37:
                if contorno:
                    prims.append(("region", pol, contorno))
                region, contorno = False, []
            b = b[m.end():]
            if not b:
                continue
        m = re.match(r"^D(\d+)$", b)
        if m and int(m.group(1)) >= 10:
            actual = int(m.group(1))
            continue
        m = re.match(r"^(?:X(-?\d+))?(?:Y(-?\d+))?(?:I(-?\d+))?(?:J(-?\d+))?D0?([123])$", b)
        if not m:
            continue
        nx = int(m.group(1)) / 10 ** dec * esc if m.group(1) else x
        ny = int(m.group(2)) / 10 ** dec * esc if m.group(2) else y
        i = int(m.group(3)) / 10 ** dec * esc if m.group(3) else 0.0
        j = int(m.group(4)) / 10 ** dec * esc if m.group(4) else 0.0
        d = int(m.group(5))
        if d == 1:
            pts = [(x, y), (nx, ny)] if modo == "G01" else arco(x, y, nx, ny, x + i, y + j, modo == "G02")
            if region:
                if not contorno:
                    contorno = [pts[0]]
                contorno += pts[1:]
            else:
                prims.append(("trazo", pol, (actual, pts)))
        elif d == 2:
            if region and contorno:
                prims.append(("region", pol, contorno))
                contorno = []
        elif d == 3:
            prims.append(("flash", pol, (actual, nx, ny)))
        x, y = nx, ny
    return ap, prims


def arco(x1, y1, x2, y2, cx, cy, horario):
    a1, a2 = math.atan2(y1 - cy, x1 - cx), math.atan2(y2 - cy, x2 - cx)
    if horario:
        while a2 >= a1:
            a2 -= 2 * math.pi
    else:
        while a2 <= a1:
            a2 += 2 * math.pi
    if abs(x1 - x2) < 1e-9 and abs(y1 - y2) < 1e-9:
        a2 = a1 + (-2 * math.pi if horario else 2 * math.pi)
    r = math.hypot(x1 - cx, y1 - cy)
    n = max(4, int(abs(a2 - a1) / math.radians(5)))
    return [(cx + r * math.cos(a1 + (a2 - a1) * k / n), cy + r * math.sin(a1 + (a2 - a1) * k / n)) for k in range(n + 1)]


# ---------------------------------------------------------------- Excellon
def leer_taladro(ruta):
    txt = ruta.read_text(encoding="latin-1").splitlines()
    herr, holes = {}, []
    actual, x, y = None, 0.0, 0.0

    def num(s):
        neg = s.startswith("-")
        s = s.lstrip("-")
        v = int(s.ljust(7, "0")) / 1e5 * MM           # INCH, LZ, 2:5
        return -v if neg else v

    for l in txt:
        m = re.match(r"^T(\d+)F\d+S\d+C([\d.]+)", l)
        if m:
            herr[int(m.group(1))] = float(m.group(2)) * MM
            continue
        m = re.match(r"^T(\d+)$", l)
        if m:
            actual = int(m.group(1))
            continue
        m = re.match(r"^(?:X(-?\d+))?(?:Y(-?\d+))?(?:G85(?:X(-?\d+))?(?:Y(-?\d+))?)?$", l)
        if m and (m.group(1) or m.group(2)):
            x = num(m.group(1)) if m.group(1) else x
            y = num(m.group(2)) if m.group(2) else y
            if "G85" in l:
                x2 = num(m.group(3)) if m.group(3) else x
                y2 = num(m.group(4)) if m.group(4) else y
                holes.append(dict(d=herr[actual], x=x, y=y, x2=x2, y2=y2, ranura=True))
            else:
                holes.append(dict(d=herr[actual], x=x, y=y, ranura=False))
    return holes


# ---------------------------------------------------------------- dibujo
def dibujar(capas_prims, ruta, colores, titulo, lim=(-4, 134, -4, 112), dpi_mm=12):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, FancyBboxPatch, Polygon, Rectangle
    x0, x1, y0, y1 = lim
    fig = plt.figure(figsize=((x1 - x0) * dpi_mm / 100, (y1 - y0) * dpi_mm / 100), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_aspect("equal")
    ax.axis("off")
    fondo = colores.get("fondo", "white")
    fig.patch.set_facecolor(fondo)
    pt_por_mm = dpi_mm * 72 / 100
    z = 0
    for (ap, prims), color in zip(capas_prims, colores["capas"]):
        for tipo, pol, dat in prims:
            z += 1
            c = color if pol == "D" else fondo
            if tipo == "flash":
                a, x, y = dat
                f, w, h = ap[a]
                if f == "C":
                    ax.add_patch(Circle((x, y), w / 2, color=c, lw=0, zorder=z))
                elif f == "R":
                    ax.add_patch(Rectangle((x - w / 2, y - h / 2), w, h, color=c, lw=0, zorder=z))
                else:
                    r = min(w, h) / 2
                    ax.add_patch(FancyBboxPatch((x - w / 2 + r, y - h / 2 + r), w - 2 * r, h - 2 * r,
                                                boxstyle=f"round,pad={r}", color=c, lw=0, zorder=z))
            elif tipo == "trazo":
                a, pts = dat
                w = ap[a][1] if a in ap else 0.1
                xs, ys = zip(*pts)
                ax.plot(xs, ys, color=c, lw=max(w * pt_por_mm, 0.3), solid_capstyle="round",
                        solid_joinstyle="round", zorder=z)
            else:
                ax.add_patch(Polygon(dat, closed=True, color=c, lw=0, zorder=z))
    for extra in colores.get("extra", []):
        extra(ax, z + 1)
    ax.text(x0 + 1, y1 - 3, titulo, fontsize=14, color=colores.get("texto", "black"))
    fig.savefig(ruta, facecolor=fondo)
    plt.close(fig)


# ---------------------------------------------------------------- comparación
def main():
    carpeta = Path(sys.argv[1]) if len(sys.argv) > 1 else CARPETA
    SALIDA.mkdir(parents=True, exist_ok=True)
    g = {}
    for ext, nombre in CAPAS.items():
        ruta = carpeta / f"{NOMBRE}.{ext}"
        if not ruta.exists():
            print(f"FALTA {ruta.name} ({nombre})")
            continue
        g[ext] = leer_gerber(ruta)
        n = Counter(t for t, _, _ in g[ext][1])
        print(f"{ext} {nombre:15} aperturas {len(g[ext][0]):3}  {dict(n)}")
    print("Capa Keep-Out (.GKO) en la carpeta:", (carpeta / f"{NOMBRE}.GKO").exists())

    # contorno
    ap, prims = g["GM1"]
    pts = [p for t, _, d in prims if t == "trazo" for p in d[1]]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    print(f"Contorno: x {min(xs):.3f}–{max(xs):.3f}  y {min(ys):.3f}–{max(ys):.3f} mm, {len(prims)} trazos")
    en_esquina = [p for p in pts if any(abs(p[0] - cx) < R_ESQUINA and abs(p[1] - cy) < R_ESQUINA and
                                        abs(math.hypot(p[0] - cx, p[1] - cy) - R_ESQUINA) < 0.02 for cx, cy in CENTROS)]
    print(f"Contorno: {len(en_esquina)} puntos sobre los arcos de R {R_ESQUINA:g} mm de las esquinas")

    # taladros
    holes = []
    for f in carpeta.glob(f"{NOMBRE}-*.TXT"):
        hs = leer_taladro(f)
        for h in hs:
            h["archivo"] = f.stem.split("-", 1)[1]
        holes += hs
    objs, _ = rr.cargar()
    agujeros = [o for o in objs if o["tipo"] in ("via", "pad") and o.get("hueco", 0) > 0 and not o.get("virtual")]
    sin_par, usados = [], set()
    for o in agujeros:
        cand = [k for k, h in enumerate(holes) if k not in usados and
                (abs(h["x"] - o["x"]) < 0.02 and abs(h["y"] - o["y"]) < 0.02 if not h["ranura"] else
                 abs((h["x"] + h["x2"]) / 2 - o["x"]) < 0.05 and abs((h["y"] + h["y2"]) / 2 - o["y"]) < 0.05)]
        if not cand:
            sin_par.append((rr.nombre(o), round(o["x"], 3), round(o["y"], 3), round(o["hueco"], 3)))
            continue
        k = cand[0]
        usados.add(k)
        if abs(holes[k]["d"] - o["hueco"]) > 0.02:
            sin_par.append((rr.nombre(o), "diámetro", round(holes[k]["d"], 3), "vs", round(o["hueco"], 3)))
    sobran = [h for k, h in enumerate(holes) if k not in usados]
    print(f"Taladros: {len(holes)} ({Counter(h['archivo'] for h in holes)}); en el PcbDoc: {len(agujeros)}; "
          f"sin pareja en los taladros: {sin_par}; taladros sin agujero en el PcbDoc: {sobran}")

    # máscara y pasta
    def flashes(ext):
        ap, prims = g[ext]
        return [(ap[d[0]], d[1], d[2]) for t, p, d in prims if t == "flash" and p == "D"]

    vias = [o for o in objs if o["tipo"] == "via"]
    for ext in ("GTS", "GBS"):
        fl = flashes(ext)
        en_via = [f for f in fl if any(abs(f[1] - v["x"]) < 0.01 and abs(f[2] - v["y"]) < 0.01 for v in vias)]
        print(f"{ext}: {len(fl)} aberturas (flash), {sum(1 for t, *_ in g[ext][1] if t == 'region')} regiones; "
              f"sobre vías: {len(en_via)}")
    pads_top = [o for o in objs if o["tipo"] == "pad" and 1 in o["capas"] and not o.get("virtual")]
    pads_bot = [o for o in objs if o["tipo"] == "pad" and 32 in o["capas"] and not o.get("virtual")]
    print(f"Pads en Top: {len(pads_top)} (SMD {sum(1 for o in pads_top if o['capas'] == {1})}); en Bottom (THT): {len(pads_bot)}")
    gtp = flashes("GTP")
    grande = [f for f in gtp if max(f[0][1], f[0][2]) > 10]
    bt1 = next(o for o in objs if o["tipo"] == "pad" and o["comp"] == "BT1" and o["nombre"] == "3")
    sobre_bt1 = [f for f in gtp if math.hypot(f[1] - bt1["x"], f[2] - bt1["y"]) < 8.5]
    print(f"GTP: {len(gtp)} aberturas de pasta (+{sum(1 for t, *_ in g['GTP'][1] if t == 'region')} regiones); "
          f"aberturas > 10 mm: {len(grande)}; sobre el contacto de BT1: {len(sobre_bt1)}; GBP: {len(g['GBP'][1])} primitivas")

    # cobre: dentro del contorno y nada en la barrera
    for ext in ("GTL", "GBL"):
        ap, prims = g[ext]
        fuera, barrera = 0, []
        for t, p, d in prims:
            if p != "D":
                continue
            if t == "flash":
                f, w, h = ap[d[0]]
                caja = (d[1] - w / 2, d[2] - h / 2, d[1] + w / 2, d[2] + h / 2)
            elif t == "trazo":
                w = ap[d[0]][1] / 2
                xs, ys = [q[0] for q in d[1]], [q[1] for q in d[1]]
                caja = (min(xs) - w, min(ys) - w, max(xs) + w, max(ys) + w)
            else:
                xs, ys = [q[0] for q in d], [q[1] for q in d]
                caja = (min(xs), min(ys), max(xs), max(ys))
            if t == "flash":
                puntos, rad = [(caja[0], caja[1]), (caja[2], caja[1]), (caja[2], caja[3]), (caja[0], caja[3])], 0.0
            else:
                puntos, rad = (d[1], w) if t == "trazo" else (d, 0.0)
            if (caja[0] < -0.01 or caja[1] < -0.01 or caja[2] > 130.01 or caja[3] > 100.01
                    or any(fuera_de_esquina(x, y, rad) for x, y in puntos)):
                fuera += 1
            if caja[0] < 51.2 and caja[2] > 45.6:
                barrera.append((t, [round(v, 2) for v in caja]))
        print(f"{ext}: cobre fuera del contorno: {fuera}; dentro de la barrera (x 45,6–51,2): {len(barrera)} {barrera[:6]}")

    # dibujos
    taladro_extra = [lambda ax, z: [ax.add_patch(__import__("matplotlib").patches.Circle(
        (h["x"], h["y"]), h["d"] / 2, color="black", lw=0, zorder=z)) for h in holes if not h["ranura"]]]
    verde, cobre, blanco = "#2f6b2f", "#c8a43c", "#f5f5f5"
    dibujar([g["GM1"], g["GTL"], g["GTO"]], SALIDA / "top_cobre_serigrafia.png",
            dict(fondo="#163a16", capas=["#9bd19b", cobre, blanco], extra=taladro_extra, texto="white"),
            "TOP: cobre (dorado) + serigrafía (blanco) + taladros")
    dibujar([g["GM1"], g["GBL"], g["GBO"]], SALIDA / "bottom_cobre.png",
            dict(fondo="#163a16", capas=["#9bd19b", cobre, blanco], extra=taladro_extra, texto="white"),
            "BOTTOM (vista desde arriba): cobre + taladros")
    dibujar([g["GM1"], g["GTS"]], SALIDA / "top_mascara.png", dict(capas=["#999999", "#d04040"]),
            "TOP SOLDER: aberturas de máscara (rojo)")
    dibujar([g["GM1"], g["GTP"]], SALIDA / "top_pasta.png", dict(capas=["#999999", "#404040"]),
            "TOP PASTE: stencil (gris)")
    for ext in ("GTL", "GBL", "GTO", "GBO"):
        dibujar([g["GM1"], g[ext]], SALIDA / f"{ext}.png", dict(capas=["#999999", "#202020"]), f"{ext} — {CAPAS[ext]}")
    print("Dibujos en", SALIDA)
    # QR de atrás (marcas_f9.py): se lee del dibujo de la serigrafía de abajo (vista desde arriba, espejado; zxing
    # también lee los espejados). Con dpi_mm = 12 el módulo de 0,75 mm mide 9 píxeles.
    try:
        import zxingcpp
        from PIL import Image
        img = Image.open(SALIDA / "bottom_cobre.png").convert("L")
        print("QR en la serigrafía de abajo (GBO):", [(str(r.format), r.text) for r in zxingcpp.read_barcodes(img)]
              or "no se pudo leer")
    except ImportError:
        print("QR: sin zxing-cpp para leerlo (pip install zxing-cpp)")


if __name__ == "__main__":
    main()
