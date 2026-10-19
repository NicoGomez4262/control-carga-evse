# -*- coding: utf-8 -*-
"""Mapa de la hoja con los Blankets propuestos (SVG estilo widget)."""
import sys

sys.path.insert(0, r"C:/Users/nico/Control de carga - Carro/docs/tools")
import lista_redes as L  # noqa: E402

ruta, salida = sys.argv[1], sys.argv[2]
X0, X1, Y0, Y1 = 0, 11200, 4000, 11200
S = 640 / (X1 - X0)


def px(x, y):
    return round(20 + (x - X0) * S, 1), round(20 + (Y1 - y) * S, 1)


recs = L.registros(ruta)
comps = {i: r for i, r in enumerate(recs) if r.get("RECORD") == "1"}
zonas = {
    "HV_AC": ("c-coral", [(400, 7500), (1800, 7500), (1800, 8800), (3800, 8800), (3800, 6900), (9400, 6900), (9400, 10800), (400, 10800)]),
    "ANALOG A": ("c-teal", [(400, 6600), (5400, 6600), (5400, 6200), (3400, 6200), (3400, 5300), (5400, 5300), (5400, 4900), (400, 4900)]),
    "ANALOG B": ("c-teal", [(6100, 6200), (10700, 6200), (10700, 5800), (7600, 5800), (7600, 4800), (10700, 4800), (10700, 4300), (6100, 4300)]),
}
out = []
for nombre, (clase, pts) in zonas.items():
    p = " ".join(f"{a},{b}" for a, b in (px(*q) for q in pts))
    out.append(f'<g class="{clase}"><polygon points="{p}" style="fill-opacity:0.55;stroke-width:1;stroke-dasharray:5 3"/></g>')
cab, pins = [], []
for r in recs:
    t = r.get("RECORD")
    if t == "27":
        n = int(r.get("LOCATIONCOUNT", 0))
        pts = [px(L.mil(r, f"X{k}"), L.mil(r, f"Y{k}")) for k in range(1, n + 1)]
        if all(X0 <= L.mil(r, f"X{k}") <= X1 and Y0 <= L.mil(r, f"Y{k}") <= Y1 for k in range(1, n + 1)):
            cab.append("M" + " L".join(f"{a} {b}" for a, b in pts))
    elif t == "2":
        c = comps.get(int(r.get("OWNERINDEX", -1)))
        if c is None:
            continue
        largo = L.mil(r, "PINLENGTH")
        dx, dy = L.DIRS[int(r.get("PINCONGLOMERATE", 0)) & 3]
        x0, y0 = L.mil(r, "LOCATION.X"), L.mil(r, "LOCATION.Y")
        if X0 <= x0 <= X1 and Y0 <= y0 <= Y1:
            a, b = px(x0, y0)
            c2, d2 = px(x0 + dx * largo, y0 + dy * largo)
            pins.append(f"M{a} {b} L{c2} {d2}")
out.append(f'<path d="{" ".join(cab)}" fill="none" style="stroke:var(--text-secondary);stroke-width:0.8"/>')
out.append(f'<path d="{" ".join(pins)}" fill="none" style="stroke:var(--text-primary);stroke-width:1.6"/>')
etiquetas = [
    ("HV_AC", 4100, 9800, "c-coral"), ("ANALOG A", 600, 5750, "c-teal"), ("ANALOG B", 8200, 4100, "c-teal"),
    ("U2", 1500, 9000, None), ("divisor R2–R5", 5000, 11000, None), ("C10–C14", 5500, 9050, None),
    ("J3", 5650, 5800, None), ("U2 lado SELV", 2050, 7200, None),
]
for txt, x, y, clase in etiquetas:
    a, b = px(x, y)
    if clase:
        out.append(f'<g class="{clase}"><text class="th" x="{a}" y="{b}" dy=".35em">{txt}</text></g>')
    else:
        out.append(f'<text class="ts" x="{a}" y="{b}" dy=".35em">{txt}</text>')
alto = round(20 + (Y1 - Y0) * S + 20)
svg = (f'<svg width="100%" viewBox="0 0 680 {alto}" role="img"><title>c3_clases</title>'
       '<desc>Mapa de 03_MEDICION con tres Blankets: HV_AC (coral) sobre el lado de red de U2, el divisor y C9 a C14; '
       'ANALOG A (verde azulado) sobre las dos filas del acople; ANALOG B sobre los dos rieles del CT. '
       'Las zonas dejan por fuera los símbolos de GND y los rieles de +3V3.</desc>\n' + "".join(out) + "\n</svg>")
open(salida, "w", encoding="utf-8").write(svg)
print(salida, len(svg), alto)
