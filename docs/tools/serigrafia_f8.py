# -*- coding: utf-8 -*-
"""F8: serigrafía de EVSE_Monitor.PcbDoc a partir de la ubicación de ubicacion_f8.POS.

- Designadores: para cada componente se prueba el texto arriba, abajo, a la izquierda y a la derecha de su
  courtyard (y, si no hay lugar, más lejos o encima del cuerpo) y se elige el primero que no pisa pads,
  otros textos, courtyards ajenos ni el borde. Alto 0,8 mm (1,0 mm en piezas grandes), trazo 0,15 mm
  (mínimos de PCBWay: línea 0,15 mm, alto 0,8 mm), siempre horizontales.
- Textos y líneas fijas en Top Overlay: «PELIGRO 240 VAC» en el hueco red–isla, bordes de la barrera,
  «HABILITACION EVSE» junto a J2 y el nombre y la versión de la placa.

Uso: python docs/tools/serigrafia_f8.py   (dibuja docs/revisiones/F8_serigrafia.png; ubicacion_f8.py --pas
     escribe el script de Altium con estos datos)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ubicacion_f8 as u  # noqa: E402

RAIZ = Path(__file__).resolve().parents[2]
GROSOR = 0.15
ANCHO_CAR = 0.85     # ancho de un carácter de la fuente de trazo de Altium, en altos de letra (estimado)

# textos fijos: (texto, x, y, alto, grosor, rotación) — (x, y) = esquina inferior izquierda
TEXTOS = [
    ("PELIGRO 240 VAC", 13.0, 76.4, 2.0, 0.25, 0),
    ("HABILITACION EVSE (J2)", 12.5, 91.5, 1.2, 0.18, 0),
    ("ZONA DE RED 120-240 VAC", 12.5, 1.2, 1.2, 0.18, 0),
    ("BARRERA 6,4 mm", 49.3, 36.0, 1.0, 0.15, 90),
    ("EVSE MONITOR  REV 1.0  2026", 53.0, 1.0, 1.2, 0.18, 0),
]
# líneas fijas: (x1, y1, x2, y2, ancho) — bordes de la barrera, de arriba abajo
LINEAS = [(45.6, 0.6, 45.6, 99.4, 0.2), (51.2, 0.6, 51.2, 99.4, 0.2)]


def caja_texto(x, y, txt, alto):
    return (x, y, x + len(txt) * ANCHO_CAR * alto, y + alto)


def se_pisan(a, b, m=0.0):
    return a[0] < b[2] + m and b[0] < a[2] + m and a[1] < b[3] + m and b[1] < a[3] + m


def designadores(info, pos):
    pads = []
    for d, p in pos.items():
        for q in u.pads_en_placa(info[d], p):
            pads.append((q["X"] - q["SX"] / 2, q["Y"] - q["SY"] / 2, q["X"] + q["SX"] / 2, q["Y"] + q["SY"] / 2))
    for hx, hy in u.AGUJEROS:
        pads.append((hx - 2.2, hy - 2.2, hx + 2.2, hy + 2.2))
    for fx, fy in u.FIDUCIALES:
        pads.append((fx - 1.2, fy - 1.2, fx + 1.2, fy + 1.2))
    cajas = {d: u.caja_en_placa(info[d], p) for d, p in pos.items()}
    ocupado = [caja_texto(x, y, t, h) for t, x, y, h, _, r in TEXTOS if r == 0]
    for x1, y1, x2, y2, w in LINEAS:
        ocupado.append((min(x1, x2) - w / 2, min(y1, y2), max(x1, x2) + w / 2, max(y1, y2)))
    out = {}
    orden = sorted(pos, key=lambda d: (cajas[d][2] - cajas[d][0]) * (cajas[d][3] - cajas[d][1]))
    for d in orden:
        b = cajas[d]
        grande = (b[2] - b[0]) * (b[3] - b[1]) > 60
        alto = 1.0 if grande else 0.8
        w = len(d) * ANCHO_CAR * alto
        cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        candidatos = []
        for sep in (0.15, 0.6, 1.2):
            candidatos += [
                (cx - w / 2, b[3] + sep),              # arriba
                (cx - w / 2, b[1] - sep - alto),       # abajo
                (b[0] - sep - w, cy - alto / 2),       # izquierda
                (b[2] + sep, cy - alto / 2),           # derecha
            ]
        elegido = None
        for x, y in candidatos:
            t = caja_texto(x, y, d, alto)
            if t[0] < 0.4 or t[1] < 0.4 or t[2] > u.LARGO - 0.4 or t[3] > u.ALTO - 0.4:
                continue
            if any(se_pisan(t, p, 0.15) for p in pads):
                continue
            if any(se_pisan(t, o, 0.1) for o in ocupado):
                continue
            if any(se_pisan(t, cajas[e]) for e in pos if e != d):
                continue
            elegido = (x, y)
            break
        if elegido is None:   # sin lugar afuera: sobre el cuerpo, sin pisar pads
            for dx in (0.0, -0.3, 0.3):
                for dy in (0.0, -0.6, 0.6, -1.2, 1.2):
                    x, y = cx - w / 2 + dx, cy - alto / 2 + dy
                    t = caja_texto(x, y, d, alto)
                    if not any(se_pisan(t, p, 0.15) for p in pads) and not any(se_pisan(t, o, 0.1) for o in ocupado):
                        elegido = (x, y)
                        break
                if elegido:
                    break
        if elegido is None:
            elegido = (cx - w / 2, cy - alto / 2)
        out[d] = (round(elegido[0], 3), round(elegido[1], 3), alto)
        ocupado.append(caja_texto(elegido[0], elegido[1], d, alto))
    return out


def dibujar(info, pos, des, ruta):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fig, ax = plt.subplots(figsize=(19.5, 15))
    ax.add_patch(Rectangle((0, 0), u.LARGO, u.ALTO, fill=False, lw=1.2, color="black"))
    for d, p in pos.items():
        b = u.caja_en_placa(info[d], p)
        ax.add_patch(Rectangle((b[0], b[1]), b[2] - b[0], b[3] - b[1], fill=False, lw=0.4, color="#aaaaaa"))
        for q in u.pads_en_placa(info[d], p):
            ax.add_patch(Rectangle((q["X"] - q["SX"] / 2, q["Y"] - q["SY"] / 2), q["SX"], q["SY"], color="#c9a227", alpha=0.8, lw=0))
    for d, (x, y, h) in des.items():
        ax.text(x, y, d, fontsize=h * 4.3, ha="left", va="bottom", family="monospace", color="#111111")
    for t, x, y, h, g, r in TEXTOS:
        ax.text(x, y, t, fontsize=h * 4.3, rotation=r, ha="left", va="bottom", family="monospace", color="#b00020")
    for x1, y1, x2, y2, w in LINEAS:
        ax.plot([x1, x2], [y1, y2], color="#b00020", lw=0.8)
    ax.set_xlim(-3, u.LARGO + 3)
    ax.set_ylim(-3, u.ALTO + 8)
    ax.set_aspect("equal")
    fig.tight_layout()
    fig.savefig(ruta, dpi=120)


if __name__ == "__main__":
    info = u.leer()
    des = designadores(info, u.POS)
    encima = [d for d, (x, y, h) in des.items()
              if u.caja_en_placa(info[d], u.POS[d])[0] <= x <= u.caja_en_placa(info[d], u.POS[d])[2]
              and u.caja_en_placa(info[d], u.POS[d])[1] <= y <= u.caja_en_placa(info[d], u.POS[d])[3]]
    print(f"{len(des)} designadores; sobre el cuerpo (sin lugar afuera): {encima}")
    ruta = RAIZ / "docs" / "revisiones" / "F8_serigrafia.png"
    dibujar(info, u.POS, des, ruta)
    print("Dibujo:", ruta)
