# -*- coding: utf-8 -*-
"""F9: marcas de la serigrafía (Altium CERRADO), pedidas por el usuario el 22 oct 2026.

Top Overlay, zona de red, en la franja libre sobre «PELIGRO!! 240 VAC» (x 11–45, y 75–84 mm), una fila de símbolos:
- alta tensión, ISO 7010 W012 (triángulo con rayo), justo encima de «PELIGRO!!»;
- WEEE / RAEE, EN 50419 (contenedor tachado con barra): no se bota con la basura doméstica;
- sensible a descargas electrostáticas, ANSI/ESD S8.1 (triángulo con mano tachada).
No se ponen CE, FCC, UL ni RoHS: son declaraciones de conformidad que exigen ensayos y documentación.

Bottom Overlay, en la zona de red de atrás (libre de vías, pistas y pads; x 15–44, y 2–41 mm), una tarjeta con marco
redondeado: «Para más información», un QR estático a https://nicolasgomez.dev (en mayúsculas, modo alfanumérico:
versión 2, 25 × 25 módulos, corrección Q del 25 %; no depende de ningún servicio, así que no vence),
«Circuitos y diseños» y «nicolasgomez.dev». El QR va en positivo: la serigrafía blanca son los módulos claros y la
zona de silencio, y los oscuros son la máscara verde. Visto desde atrás se lee derecho (en coordenadas de la cara de
arriba va espejado), igual que los textos (espejo = 1; el ancla queda a la derecha vista desde arriba).

Además: «Made by: Nicopro3000...» (atrás) de 0,75 a 0,8 mm de alto, el mínimo de PCBWay.

Dibujo: pistas y arcos de 0,2–0,5 mm (mínimo de PCBWay 0,15 mm), rellenos (Fills6) para lo sólido y textos TrueType
Arial Bold (con el formato de serigrafia_f9.py). Alto de TrueType = alto de la celda (Arial: 1,117 em).

Uso: python docs/tools/marcas_f9.py            # dibuja las vistas previas (docs/revisiones/marcas_f9_*.png)
     python docs/tools/marcas_f9.py --escribir # respalda el PcbDoc en docs/respaldos/ y escribe
     python docs/tools/marcas_f9.py --reponer  # devuelve a su lugar los rellenos del QR que se movieron en Altium
                                               # (22 oct: uno de la zona de silencio quedó corrido 0,635 mm)
Los símbolos de arriba los reubicó el usuario en Altium el 22 oct (alta tensión y ESD en x 2,7–9,2, y 44,6–61,4;
RAEE en x 35,4–39,9, y 33–39,6); --escribir ya no se vuelve a correr.
"""
import math
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import altium_ole as ao  # noqa: E402
import aplicar_ruteo_f8 as ap  # noqa: E402
import revisar_pcb as rv  # noqa: E402
import serigrafia_f9 as sf  # noqa: E402

U, O = rv.U, 25.4
RAIZ = Path(__file__).resolve().parents[2]
TOP, BOT = 33, 34
V7 = {TOP: bytes.fromhex("06000301"), BOT: bytes.fromhex("07000301")}
EM = 1 / 1.117                      # Arial: la celda de TrueType mide 1,117 em (ascendente + descendente)
URL = "HTTPS://NICOLASGOMEZ.DEV"
MODULO = 0.75                       # mm por módulo del QR
SILENCIO = 3                        # módulos de zona de silencio (blancos) alrededor


class Dibujo:
    """Primitivas en mm (coordenadas de la placa, vistas desde arriba)."""

    def __init__(self, capa):
        self.capa, self.lineas, self.arcos, self.rellenos, self.textos = capa, [], [], [], []

    def linea(self, x1, y1, x2, y2, w):
        self.lineas.append((x1, y1, x2, y2, w))

    def polilinea(self, pts, w, cerrada=False):
        pts = list(pts) + ([pts[0]] if cerrada else [])
        for a, b in zip(pts, pts[1:]):
            self.linea(*a, *b, w)

    def arco(self, cx, cy, r, sa, ea, w):
        self.arcos.append((cx, cy, r, sa, ea, w))

    def relleno(self, x1, y1, x2, y2):
        self.rellenos.append((min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)))

    def poligono_solido(self, pts, w=0.2):
        """Relleno con líneas horizontales de ancho w (paso 0,8 w), recortadas para que la tapa redonda quede adentro."""
        ys = [p[1] for p in pts]
        y = min(ys) + w / 2
        while y <= max(ys) - w / 2 + 1e-9:
            xs = []
            n = len(pts)
            for i in range(n):
                (xa, ya), (xb, yb) = pts[i], pts[(i + 1) % n]
                if (ya <= y < yb) or (yb <= y < ya):
                    xs.append(xa + (y - ya) * (xb - xa) / (yb - ya))
            xs.sort()
            for a, b in zip(xs[::2], xs[1::2]):
                if b - a > w:
                    self.linea(a + w / 2, y, b - w / 2, y, w)
                else:
                    self.linea((a + b) / 2, y, (a + b) / 2, y, max(0.15, b - a))
            y += 0.8 * w
        self.polilinea(pts, w, cerrada=True)

    def texto(self, txt, alto, x, y, centro=False):
        """TrueType Arial Bold; (x, y) es la esquina inferior izquierda tal como se lee (o el centro si centro=True).
        En la cara de abajo el texto va espejado y el ancla de Altium queda a la derecha vista desde arriba."""
        w = sf.ancho_aprox(txt, alto) * EM
        x0 = x - w / 2 if centro else x
        self.textos.append((txt, alto, x0, y, w))


def triangulo(d, x, y, lado, w):
    """Triángulo equilátero de advertencia con la base en y y el borde exterior en (x, y)–(x+lado, y)."""
    h = lado * math.sqrt(3) / 2
    a = w / 2
    pts = [(x + a * math.sqrt(3), y + a), (x + lado - a * math.sqrt(3), y + a), (x + lado / 2, y + h - 2 * a)]
    d.polilinea(pts, w, cerrada=True)
    return pts


def simbolo_alta_tension(d, x, y, lado=6.6):
    """ISO 7010 W012: triángulo y rayo con punta de flecha."""
    triangulo(d, x, y, lado, 0.55)
    s = lado / 6.6
    def p(px, py):
        return (x + px * s, y + py * s)
    # rayo sólido: tramo de arriba inclinado, escalón y tramo de abajo que termina en punta de flecha
    d.poligono_solido([p(3.00, 3.90), p(3.62, 3.90), p(3.38, 2.75), p(3.95, 2.75), p(2.95, 0.95), p(3.20, 2.20),
                       p(2.65, 2.20)], 0.18)


def simbolo_raee(d, x, y, alto=6.6):
    """EN 50419: contenedor con ruedas tachado y barra debajo (RAEE)."""
    s = alto / 6.6
    def p(px, py):
        return (x + px * s, y + py * s)
    w = 0.3 * s
    # cuerpo (trapecio) con dos nervios
    d.polilinea([p(1.05, 5.0), p(1.35, 1.75), p(3.85, 1.75), p(4.15, 5.0)], w)
    d.linea(*p(2.1, 4.55), *p(2.2, 2.2), 0.22 * s)
    d.linea(*p(3.1, 4.55), *p(3.0, 2.2), 0.22 * s)
    # tapa con manija y bisagra
    d.linea(*p(0.75, 5.25), *p(4.45, 5.25), 0.36 * s)
    d.polilinea([p(2.05, 5.4), p(2.15, 5.85), p(3.05, 5.85), p(3.15, 5.4)], 0.26 * s)
    # rueda
    d.arco(*p(3.7, 1.55), 0.42 * s, 0, 360, 0.26 * s)
    # tachado
    d.linea(*p(0.55, 6.1), *p(4.65, 1.15), 0.36 * s)
    d.linea(*p(4.65, 6.1), *p(0.55, 1.15), 0.36 * s)
    # barra sólida
    d.relleno(*p(0.55, 0.05), *p(4.65, 0.7))


def simbolo_esd(d, x, y, lado=6.6):
    """ANSI/ESD S8.1: triángulo con una mano y una barra que la tacha."""
    triangulo(d, x, y, lado, 0.45)
    s = lado / 6.6
    k = 0.82                        # la mano se dibuja a 82 % para que quepa dentro del borde del triángulo
    def p(px, py):
        return (x + (3.35 + (px - 3.35) * k) * s, y + (0.9 + (py - 0.9) * k) * s)
    w = 0.24 * s
    # palma: muñeca, borde del meñique y pulgar abierto hacia la izquierda
    d.polilinea([p(2.65, 0.95), p(3.95, 0.95), p(4.05, 2.55)], w)
    d.polilinea([p(2.65, 0.95), p(2.6, 1.85), p(2.1, 2.45), p(1.95, 2.85)], w)
    # dedos (el del medio es el más largo), con la punta redonda de la pista
    for x0, y0, y1 in ((2.75, 2.05, 3.85), (3.17, 2.1, 4.2), (3.59, 2.1, 4.0), (4.0, 2.2, 3.55)):
        d.linea(*p(x0, y0), *p(x0, y1), 0.19)         # 0,19 mm: queda ~0,2 mm entre dedos (que no se unan)
    # barra que la tacha, de arriba a la izquierda hacia abajo a la derecha, sin tocar el borde
    d.linea(x + 2.45 * s, y + 2.85 * s, x + 4.6 * s, y + 1.1 * s, 0.38 * s)


def qr_modulos():
    import segno
    q = segno.make(URL, error="q", micro=False, boost_error=False)
    assert q.version == 2 and q.mode == "alphanumeric", (q.version, q.mode)
    return [list(fila) for fila in q.matrix]


def tarjeta_qr(d, xc, y_arriba):
    """Tarjeta de atrás; xc es el centro (vista desde arriba), y_arriba el borde superior del marco."""
    m = qr_modulos()
    n = len(m)
    lado = (n + 2 * SILENCIO) * MODULO
    margen, sep = 1.2, 1.0
    alto_t1, alto_t2, alto_t3 = 1.6, 1.5, 1.2
    y = y_arriba - margen - alto_t1
    d.texto("Para más información", alto_t1, xc, y, centro=True)
    y_qr_arriba = y - sep
    x0 = xc - lado / 2
    y0 = y_qr_arriba - lado
    # módulos claros y zona de silencio en blanco; en la cara de abajo el QR va espejado en x
    total = n + 2 * SILENCIO
    claro = [[True] * total for _ in range(total)]
    for r in range(n):
        for c in range(n):
            claro[r + SILENCIO][c + SILENCIO] = not m[r][c]
    for r in range(total):
        c = 0
        while c < total:
            if not claro[r][c]:
                c += 1
                continue
            c2 = c
            while c2 < total and claro[r][c2]:
                c2 += 1
            # columna c (vista desde atrás) → x espejado vista desde arriba
            xa = x0 + (total - c2) * MODULO
            xb = x0 + (total - c) * MODULO
            ya = y_qr_arriba - (r + 1) * MODULO
            d.relleno(xa, ya, xb, ya + MODULO)
            c = c2
    y = y0 - sep - alto_t2
    d.texto("Circuitos y diseños", alto_t2, xc, y, centro=True)
    y -= 0.6 + alto_t3
    d.texto("nicolasgomez.dev", alto_t3, xc, y, centro=True)
    y_abajo = y - margen
    ancho = max(lado, max(t[4] for t in d.textos)) + 2 * margen
    # marco redondeado
    r, w = 1.5, 0.2
    xa, xb, ya, yb = xc - ancho / 2, xc + ancho / 2, y_abajo, y_arriba
    d.linea(xa + r, ya, xb - r, ya, w)
    d.linea(xb, ya + r, xb, yb - r, w)
    d.linea(xb - r, yb, xa + r, yb, w)
    d.linea(xa, yb - r, xa, ya + r, w)
    for cx, cy, sa in ((xb - r, ya + r, 270), (xb - r, yb - r, 0), (xa + r, yb - r, 90), (xa + r, ya + r, 180)):
        d.arco(cx, cy, r, sa, sa + 90, w)
    return (xa, ya, xb, yb), (x0, y0, x0 + lado, y0 + lado)


def armar():
    top = Dibujo(TOP)
    # fila de símbolos sobre «PELIGRO!! 240 VAC» (el texto empieza en x 10,67, y 73,66)
    # tres símbolos de 7,2 mm de alto con 3,5 mm entre uno y otro (el contenedor ocupa x 0,55–4,65 de su caja de
    # 6,6); la franja libre llega a y 83,75 (debajo pasa la pista de J2 a K1)
    a = 7.2
    s = a / 6.6
    simbolo_alta_tension(top, 11.0, 76.0, a)
    simbolo_raee(top, 11.0 + a + 3.5 - 0.55 * s, 76.0, a)
    simbolo_esd(top, 11.0 + a + 3.5 + 4.1 * s + 3.5, 76.0, a)
    bot = Dibujo(BOT)
    caja, qr = tarjeta_qr(bot, 29.6, 39.5)
    return top, bot, caja, qr


# ---------------------------------------------------------------- vista previa
def vista_previa(top, bot, caja):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.font_manager import FontProperties
    from matplotlib.patches import PathPatch, Rectangle, Arc
    from matplotlib.textpath import TextPath
    from matplotlib.transforms import Affine2D

    def pintar(ax, d, espejo=False):
        for x1, y1, x2, y2, w in d.lineas:
            ax.plot([x1, x2], [y1, y2], color="white", lw=w * escala, solid_capstyle="round")
        for cx, cy, r, sa, ea, w in d.arcos:
            ax.add_patch(Arc((cx, cy), 2 * r, 2 * r, theta1=sa, theta2=ea, color="white", lw=w * escala))
        for x1, y1, x2, y2 in d.rellenos:
            ax.add_patch(Rectangle((x1, y1), x2 - x1, y2 - y1, fc="white", ec="none"))
        for txt, alto, x, y, w in d.textos:
            p = TextPath((0, 0.212 * alto * EM), txt, size=alto * EM, prop=FontProperties(family="Arial", weight="bold"))
            t = Affine2D().translate(x, y)
            if espejo:
                t = Affine2D().scale(-1, 1).translate(x + w, y)
            ax.add_patch(PathPatch(t.transform_path(p), fc="white", ec="none"))

    for nombre, d, lim, titulo, espejo in (
            ("top", top, (8, 46, 70, 90), "Cara de arriba, zona de red: alta tensión, RAEE y ESD sobre «PELIGRO!!»", False),
            ("bottom", bot, (12, 47, -1, 42), "Cara de atrás (vista desde atrás): tarjeta con el QR", True)):
        fig, ax = plt.subplots(figsize=(6.2, 6.2 * (lim[3] - lim[2]) / (lim[1] - lim[0])), dpi=220)
        global escala
        escala = fig.get_size_inches()[0] * 72 / (lim[1] - lim[0]) * 0.92
        ax.set_facecolor("#1f5a3a")
        if nombre == "top":
            ax.text(10.67, 73.66, "PELIGRO!! 240 VAC", color="white", fontsize=7.5, family="monospace", va="bottom")
            ax.add_patch(Rectangle((0.4, 79.4), 9.1, 10, fill=False, ec="white", lw=0.8))
            ax.text(5, 88, "J2", color="white", fontsize=6)
            ax.add_patch(Rectangle((0.4, 64.8), 9.1, 10, fill=False, ec="white", lw=0.8))
            ax.text(5, 73.5, "J1", color="white", fontsize=6)
            ax.plot([9.5, 45], [84.6, 84.6], color="#c8a43c", lw=0.8 * escala)
            ax.plot([45.6, 45.6], [60, 95], color="white", lw=0.2 * escala)
            ax.add_patch(Rectangle((32.4, 70.3), 1.9, 1.3, fc="#c8a43c"))
        pintar(ax, d, espejo)
        ax.set_xlim(lim[0], lim[1]) if not espejo else ax.set_xlim(lim[1], lim[0])
        ax.set_ylim(lim[2], lim[3])
        ax.set_aspect("equal")
        ax.set_title(titulo, fontsize=7)
        ax.tick_params(labelsize=5)
        fig.tight_layout()
        ruta = RAIZ / "docs" / "revisiones" / f"marcas_f9_{nombre}.png"
        fig.savefig(ruta)
        plt.close(fig)
        print("Vista previa:", ruta)


escala = 1.0


# ---------------------------------------------------------------- escritura
def escribir(top, bot):
    pcb = rv.PCB
    tr = ap.registros(ao.leer_stream(pcb, "Tracks6/Data"), 1)
    ar = ap.registros(ao.leer_stream(pcb, "Arcs6/Data"), 1)
    fl = ap.registros(ao.leer_stream(pcb, "Fills6/Data"), 1)
    tx = ap.registros(ao.leer_stream(pcb, "Texts6/Data"), 2)
    ws = sf.leer_ws(ao.leer_stream(pcb, "WideStrings6/Data"))
    t_pista = next(bl[0] for t, bl in tr if bl[0][0] == 57 and struct.unpack_from("<H", bl[0], 7)[0] == 0xFFFF)
    t_arco = next(bl[0] for t, bl in ar if bl[0][0] == 57)
    t_relleno = fl[0][1][0]
    v7_rel = t_relleno.find(bytes.fromhex("0d000301"))
    assert v7_rel > 0, "Fills6: no encontré la capa V7"
    texto_ws = {idx: s for idx, s in ws}
    # plantilla de texto TrueType: la primera línea del bloque de identificación
    k_tt = next(k for k, (t, bl) in enumerate(tx) if bl[0][0] == TOP and bl[0][43] == 1)
    g_tt, b_tt = tx[k_tt][1]
    nuevo_idx = max(texto_ws) + 1
    for d in (top, bot):
        for x1, y1, x2, y2, w in d.lineas:
            g = bytearray(t_pista)
            g[0], g[2] = d.capa, 0
            g[41:45] = V7[d.capa]
            struct.pack_into("<iiii", g, 13, ap.interno(x1), ap.interno(y1), ap.interno(x2), ap.interno(y2))
            struct.pack_into("<i", g, 29, sf.u(w))
            tr.append((4, [bytes(g)]))
        for cx, cy, r, sa, ea, w in d.arcos:
            g = bytearray(t_arco)
            g[0], g[2] = d.capa, 0
            struct.pack_into("<iii", g, 13, ap.interno(cx), ap.interno(cy), sf.u(r))
            struct.pack_into("<dd", g, 25, float(sa), float(ea))
            struct.pack_into("<i", g, 41, sf.u(w))
            g[52:56] = V7[d.capa]
            ar.append((1, [bytes(g)]))
        for x1, y1, x2, y2 in d.rellenos:
            g = bytearray(t_relleno)
            g[0], g[2] = d.capa, 0
            struct.pack_into("<iiii", g, 13, ap.interno(x1), ap.interno(y1), ap.interno(x2), ap.interno(y2))
            struct.pack_into("<d", g, 29, 0.0)
            g[v7_rel:v7_rel + 4] = V7[d.capa]
            fl.append((6, [bytes(g)]))
        for txt, alto, x, y, w in d.textos:
            reg = sf.texto_truetype(g_tt, b_tt, txt, alto, x + (w if d.capa == BOT else 0), y, nuevo_idx)
            g = bytearray(reg[0])
            g[0] = d.capa
            g[35] = 1 if d.capa == BOT else 0
            g[226:230] = V7[d.capa]
            tx.append((5, [bytes(g), reg[1]]))
            texto_ws[nuevo_idx] = txt
            nuevo_idx += 1
    # «Made by: …» de atrás al mínimo de PCBWay
    for k, (t, bl) in enumerate(tx):
        g = bl[0]
        if g[0] == BOT and texto_ws.get(struct.unpack_from("<I", g, 115)[0], "").startswith("Made by"):
            h = struct.unpack_from("<i", g, 21)[0] * U
            if h < 0.8:
                g = bytearray(g)
                struct.pack_into("<i", g, 21, sf.u(0.8))
                tx[k] = (5, [bytes(g), bl[1]])
                print(f"«Made by…»: alto {h:.2f} → 0.80 mm")
    if ao.altium_abierto():
        sys.exit("Altium está abierto (X2.exe): guarda, ciérralo y vuelve a correr.")
    print("Respaldo:", ao.respaldo(pcb, "antes_marcas_f9"))
    ws = sorted(texto_ws.items())
    ao.escribir_streams(pcb, {
        "Tracks6/Data": ap.unir(tr), "Tracks6/Header": struct.pack("<I", len(tr)),
        "Arcs6/Data": ap.unir(ar), "Arcs6/Header": struct.pack("<I", len(ar)),
        "Fills6/Data": ap.unir(fl), "Fills6/Header": struct.pack("<I", len(fl)),
        "Texts6/Data": ap.unir(tx), "Texts6/Header": struct.pack("<I", len(tx)),
        "WideStrings6/Data": sf.unir_ws(ws), "WideStrings6/Header": struct.pack("<I", len(ws))})
    print(f"Escrito: {len(tr)} pistas, {len(ar)} arcos, {len(fl)} rellenos, {len(tx)} textos, {len(ws)} cadenas")


def reponer():
    """Rellenos de atrás que no están donde se escribieron: se busca el esperado de la misma fila y tamaño que falta."""
    _, bot, _, _ = armar()
    pcb = rv.PCB
    fl = ap.registros(ao.leer_stream(pcb, "Fills6/Data"), 1)
    def caja(g):
        x1, y1, x2, y2 = (v * U - O for v in struct.unpack_from("<iiii", g, 13))
        return (min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))
    hay = [(k, caja(bl[0])) for k, (t, bl) in enumerate(fl) if bl[0][0] == BOT]
    igual = lambda a, b: all(abs(u - v) < 0.002 for u, v in zip(a, b))
    faltan = [e for e in bot.rellenos if not any(igual(e, c) for _, c in hay)]
    sobran = [(k, c) for k, c in hay if not any(igual(e, c) for e in bot.rellenos)]
    cambios = []
    for k, c in sobran:
        e = next((e for e in faltan if abs(e[1] - c[1]) < 0.002 and abs((e[2] - e[0]) - (c[2] - c[0])) < 0.002), None)
        if e is None:
            continue
        g = bytearray(fl[k][1][0])
        struct.pack_into("<iiii", g, 13, ap.interno(e[0]), ap.interno(e[1]), ap.interno(e[2]), ap.interno(e[3]))
        fl[k] = (6, [bytes(g)])
        faltan.remove(e)
        cambios.append(f"relleno {k}: x {c[0]:.3f}–{c[2]:.3f} → {e[0]:.3f}–{e[2]:.3f} (y {c[1]:.3f})")
    print("\n".join(cambios) or "Todos los rellenos del QR están en su lugar")
    if not cambios:
        return
    if ao.altium_abierto():
        sys.exit("Altium está abierto (X2.exe): guarda, ciérralo y vuelve a correr.")
    print("Respaldo:", ao.respaldo(pcb, "antes_reponer_qr_f9"))
    ao.escribir_streams(pcb, {"Fills6/Data": ap.unir(fl)})


def main():
    if "--reponer" in sys.argv:
        return reponer()
    top, bot, caja, qr = armar()
    for nombre, d in (("arriba", top), ("atrás", bot)):
        print(f"{nombre}: {len(d.lineas)} pistas, {len(d.arcos)} arcos, {len(d.rellenos)} rellenos, {len(d.textos)} textos")
    print(f"tarjeta del QR: x {caja[0]:.2f}–{caja[2]:.2f}, y {caja[1]:.2f}–{caja[3]:.2f}; QR con zona de silencio "
          f"{qr[2] - qr[0]:.2f} mm (módulo {MODULO} mm)")
    vista_previa(top, bot, caja)
    if "--escribir" in sys.argv:
        escribir(top, bot)
    else:
        print("\n(prueba: no se escribió nada; usa --escribir)")


if __name__ == "__main__":
    main()
