# -*- coding: utf-8 -*-
"""Mapa de puntos de medición de la Fase 9 (pruebas de la placa), dibujado desde EVSE_Monitor.PcbDoc.

Dibuja la placa vista desde arriba (pads, serigrafía, barrera) y marca con un número cada punto que usa
docs/pruebas/PROTOCOLO_PRUEBAS.md. Amarillo: lado SELV; naranja: lado de red (solo con J1 sin cables).

Uso: python docs/tools/mapa_puntos_f9.py docs/pruebas/mapa_puntos.png
"""
import sys, struct, math
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from PIL import Image, ImageDraw, ImageFont
import altium_ole as ao, revisar_pcb as rv, medidas_pcb as m

S, M = 10, 50                      # px/mm, margen
LEYENDA = 400
W, H = int(130 * S + 2 * M), int(100 * S + 2 * M + 40 + LEYENDA)
def P(x, y): return (M + x * S, M + (100 - y) * S)

comps = rv.texto("Components6/Data")
des = [ao.valor(c, "SOURCEDESIGNATOR") for c in comps]
cen = {}
rot = [float(ao.valor(c, "ROTATION")) for c in comps]
for c in comps:
    cen[ao.valor(c, "SOURCEDESIGNATOR")] = (float(ao.valor(c, "X").replace("mil", "")) * 0.0254 - 25.4,
                                           float(ao.valor(c, "Y").replace("mil", "")) * 0.0254 - 25.4)
pads = rv.pads()
nets = [ao.valor(n, "NAME") for n in rv.texto("Nets6/Data")]
padpos, padnet = {}, {}
for p in pads:
    if p["comp"] != 0xFFFF:
        padpos[(des[p["comp"]], p["nombre"])] = (p["x"] - 25.4, p["y"] - 25.4)
        padnet[(des[p["comp"]], p["nombre"])] = nets[p["red"]] if p["red"] < len(nets) else ""

im = Image.new("RGB", (W, H), "white")
d = ImageDraw.Draw(im)
f9 = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 11)
fb = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 13)
ft = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 16)

d.rounded_rectangle([P(0, 100), P(130, 0)], radius=40, fill=(18, 60, 140))
# zonas
d.rectangle([P(45, 100), P(51.7, 0)], fill=(40, 40, 40))
d.text(P(1.5, 99), "ZONA DE RED / ISLA EVSE", font=fb, fill=(255, 170, 150))
d.text(P(53, 99), "ZONA SELV", font=fb, fill=(170, 255, 210))
# pads
for p in pads:
    x, y = p["x"] - 25.4, p["y"] - 25.4
    hx, hy = p["sx"] / 2, p["sy"] / 2
    if p["comp"] != 0xFFFF and round(rot[p["comp"]]) % 180 == 90:
        hx, hy = hy, hx
    if p["comp"] != 0xFFFF and des[p["comp"]] in ("BT1",) and p["nombre"] == "3":
        continue
    if p["hueco"] > 0:
        d.ellipse([P(x - hx, y + hy), P(x + hx, y - hy)], fill=(200, 200, 200))
        d.ellipse([P(x - p["hueco"] / 2, y + p["hueco"] / 2), P(x + p["hueco"] / 2, y - p["hueco"] / 2)], fill=(18, 60, 140))
    else:
        # pad rotado: usar la caja con la rotación del componente si es 90/270
        d.rectangle([P(x - hx, y + hy), P(x + hx, y - hy)], fill=(200, 200, 200))
# serigrafía
for g in m.primitivas("Tracks6/Data", 4):
    if g[0] != 33: continue
    x1, y1, x2, y2 = (v * rv.U - 25.4 for v in struct.unpack_from("<iiii", g, 13))
    d.line([P(x1, y1), P(x2, y2)], fill=(235, 235, 235), width=1)

# designadores de referencia
ref = ["U1","U2","U3","U4","U5","U6","U7","PS1","J1","J2","J3","J4","J5","J6","J7","J8","K1","Q3","F1","F2","RV1",
       "R2","R3","R4","R5","R6","C2","C3","C10","C16","C18","C19","C21","C22","C29","C30","C38","R41","D1","D2","D3",
       "D4","D5","D6","BT1","LED1","LED2","LED3","LED4","LED5","LED6","Y1","SW1","L1","L2","TP1","TP2","TP3","TP4","TP5","TP6","R37"]
for r in ref:
    x, y = cen[r]
    tx, ty = P(x, y)
    w = d.textlength(r, font=f9)
    LOFF = {"J1": (4.6, -2.5), "J2": (4.6, -2.5), "J6": (1.75, -3.4), "U1": (2.5, 4.3), "J4": (0, 9.6),
            "J8": (0, 15.2), "R5": (-2.9, 0), "U4": (0, 0.8)}
    if r in LOFF:
        off = (LOFF[r][0] * S, -LOFF[r][1] * S)
    else:
        off = (0, -26) if r.startswith("TP") else (0, 0)
    d.rectangle([tx - w / 2 - 2 + off[0], ty - 7 + off[1], tx + w / 2 + 2 + off[0], ty + 7 + off[1]], fill=(255, 255, 255))
    d.text((tx - w / 2 + off[0], ty - 7 + off[1]), r, font=f9, fill=(0, 0, 0))

PUNTOS = [
 (1, "TP1", "1", "s"), (2, "TP2", "1", "s"), (3, "TP3", "1", "s"), (4, "TP4", "1", "s"), (5, "TP5", "1", "s"),
 (6, "J6", "1", "s"), (7, "J6", "2", "s"), (8, "U1", "1", "s"), (9, "U1", "2", "s"), (10, "U1", "3", "s"),
 (11, "J1", "1", "h"), (12, "J1", "2", "h"), (13, "F1", "1", "h"), (14, "F1", "2", "h"), (15, "F2", "1", "h"),
 (16, "F2", "2", "h"), (17, "J2", "1", "h"), (18, "J2", "2", "h"), (19, "D4", "2", "s"), (20, "D4", "1", "s"),
 (21, "C10", "1", "h"), (22, "C10", "2", "h"), (23, "C16", "1", "h"), (24, "C18", "1", "s"), (25, "C21", "1", "s"),
 (26, "C19", "1", "s"), (27, "C22", "1", "s"), (28, "C30", "1", "s"), (29, "C29", "1", "s"), (30, "C38", "2", "s"),
 (31, "J4", "1", "s"), (32, "D5", "5", "s"), (33, "R41", "1", "s"), (34, "R41", "2", "s"), (35, "BT1", "1", "s"),
 (36, "J8", "1", "s"), (37, "J8", "4", "s"), (38, "J8", "5", "s"), (39, "J8", "6", "s"),
]
# desplazamiento del rótulo para no tapar (dx, dy en mm)
OFF = {1: (0, -3.3), 2: (0, -3.3), 3: (0, -3.3), 4: (0, 3.2), 5: (0, 3.2), 6: (-3, 2.6), 7: (3, 2.6),
       8: (-1.2, -3), 9: (0, -3.2), 10: (1.2, -3), 11: (-2.8, 0), 12: (-2.8, 0), 13: (3.6, 0), 14: (3.6, 0),
       15: (-3.6, 0), 16: (-3.6, 0), 17: (-2.8, 0), 18: (-2.8, 0), 19: (-2.4, 2.6), 20: (2.4, 2.6),
       21: (-3, -1.5), 22: (-3, 1.5), 23: (-3, -1.5), 24: (-3.2, 0.6), 25: (-3.2, 1.2), 26: (3.3, 0.2),
       27: (-3.2, -1.2), 28: (2.8, -2.4), 29: (2.8, 2.4), 30: (-3, 2.4), 31: (-3.4, -1.2), 32: (-3, -2.4),
       33: (-2.5, -2.8), 34: (2.5, -2.8), 35: (3.2, -1.5),
       36: (2.4, 0), 37: (2.4, 0), 38: (2.4, 0), 39: (2.4, 0)}
for n, c, pad, tipo in PUNTOS:
    x, y = padpos[(c, pad)]
    px, py = P(x, y)
    dx, dy = OFF.get(n, (0, 3))
    lx, ly = P(x + dx, y + dy)
    col = (255, 120, 60) if tipo == "h" else (255, 215, 0)
    d.line([px, py, lx, ly], fill=col, width=2)
    d.ellipse([px - 3, py - 3, px + 3, py + 3], fill=col)
    r = 12
    d.ellipse([lx - r, ly - r, lx + r, ly + r], fill=col, outline=(0, 0, 0))
    t = str(n)
    w = d.textlength(t, font=fb)
    d.text((lx - w / 2, ly - 8), t, font=fb, fill=(0, 0, 0))
# números de pin de J8 y J4
for k in range(1, 7):
    x, y = padpos[("J8", str(k))]
    tx, ty = P(x - 2.6, y)
    d.text((tx - 4, ty - 7), str(k), font=fb, fill=(255, 255, 255))
for k in range(1, 4):
    x, y = padpos[("J4", str(k))]
    tx, ty = P(x - 2.4, y)
    d.text((tx - 4, ty - 7), str(k), font=fb, fill=(255, 255, 255))
Y0 = M + 100 * S + 8
d.text((M, Y0), "Vista desde arriba (cara de los componentes). Amarillo: SELV. Naranja: lado de red (solo con J1 SIN cables).",
       font=ft, fill=(0, 0, 0))
d.text((M, Y0 + 22), "J8 de abajo hacia arriba: 1 3V3 · 2 TX · 3 RX · 4 EN · 5 IO0 · 6 GND.   J4: 1 3V3 sonda · 2 DATOS · 3 GND.",
       font=ft, fill=(0, 0, 0))
# leyenda: número -> pin de Altium (Designador-pin) y red
NOMBRE = {("U1", "1"): "+Vin del R-78CK", ("U1", "3"): "+Vout del R-78CK", ("R41", "1"): "ánodo de LED6"}
d.text((M, Y0 + 58), "Número del mapa  →  pin en Altium (Designador-pin)  ·  red", font=ft, fill=(0, 0, 0))
filas = 13
for i, (n, c, pad, tipo) in enumerate(PUNTOS):
    col, fila = divmod(i, filas)
    x0, y0 = M + col * 440, Y0 + 92 + fila * 24
    cc = (255, 120, 60) if tipo == "h" else (255, 215, 0)
    d.ellipse([x0, y0, x0 + 22, y0 + 22], fill=cc, outline=(0, 0, 0))
    t = str(n)
    w = d.textlength(t, font=fb)
    d.text((x0 + 11 - w / 2, y0 + 3), t, font=fb, fill=(0, 0, 0))
    red = NOMBRE.get((c, pad), padnet.get((c, pad), ""))
    d.text((x0 + 32, y0 + 2), f"{c}-{pad}", font=ft, fill=(0, 0, 0))
    d.text((x0 + 110, y0 + 2), red, font=ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 15), fill=(60, 60, 60))
im.save(sys.argv[1])
print("ok", im.size)
