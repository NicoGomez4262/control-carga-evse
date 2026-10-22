# -*- coding: utf-8 -*-
"""F8 (22 oct): conecta los pads de GND que el vertido de los polígonos dejó sueltos (Altium CERRADO).

Después del primer Repour All quedaron 7 pads de GND fuera del plano (revisar_ruteo_f8.gnd_con_planos):
- J5.B1 y dos patas del blindaje: pistas cortas por Top a los pads de GND vecinos (A12–B1–blindaje,
  blindaje–B12–A1), que ya tienen vía.
- U4.41 (centro de la grilla de 3 × 3 del ESP32-S3): pista a U4.45 y U4.49, que tienen vía.
- U2.15: AMC_LDO subía por Bottom hasta una vía justo delante del pin; esa vía pasa arriba de la pista
  U2.16–C13 y U2.15 sale por Top a una vía de GND propia.
- U3.2: a mano, a C25.2 (el ruteador no pasa por un pasillo de 0,73 mm con su margen de rejilla).
- C30.2: el ruteador de rutear_f8 busca el cobre de GND más cercano (o un lugar para una vía) por Top.

Uso: python docs/tools/terminar_gnd_f8.py [--escribir]
"""
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import revisar_ruteo_f8 as rr  # noqa: E402
import rutear_f8 as rt  # noqa: E402

TOP, BOT = rr.TOP, rr.BOT
PISTAS = [
    # J5: A12 → B1 → blindaje; blindaje → B12 → A1
    dict(red="GND", capa=TOP, x1=115.75, y1=89.42, x2=115.75, y2=90.40, ancho=0.25),
    dict(red="GND", capa=TOP, x1=115.7, y1=90.67, x2=116.5, y2=90.67, ancho=0.25),
    dict(red="GND", capa=TOP, x1=120.5, y1=90.67, x2=121.3, y2=90.67, ancho=0.25),
    dict(red="GND", capa=TOP, x1=121.25, y1=89.42, x2=121.25, y2=90.40, ancho=0.25),
    # U4: centro de la grilla de GND a sus vecinos de arriba y de abajo
    dict(red="GND", capa=TOP, x1=93.0, y1=91.04, x2=93.0, y2=89.64, ancho=0.4),
    dict(red="GND", capa=TOP, x1=93.0, y1=91.04, x2=93.0, y2=92.44, ancho=0.4),
    # U3.2: entre la esquina de U3.1 y la vía de ATM_RST hay 0,73 mm; una de 0,25 a 45° pasa a 0,24 mm de las dos
    # (punto medio (69,62; 66,75)) y sube a C25.2, que ya tiene vía
    dict(red="GND", capa=TOP, x1=69.0, y1=66.62, x2=69.49, y2=66.62, ancho=0.25),
    dict(red="GND", capa=TOP, x1=69.49, y1=66.62, x2=69.95, y2=67.08, ancho=0.25),
    dict(red="GND", capa=TOP, x1=69.95, y1=67.08, x2=69.95, y2=69.0, ancho=0.25),
    # U2.15 → vía de GND
    dict(red="GND", capa=TOP, x1=53.075, y1=67.175, x2=55.9, y2=67.175, ancho=0.4),
]
VIAS = [dict(red="GND", x=55.9, y=67.175, hueco=0.4, dia=0.8)]
# AMC_LDO: la vía de delante de U2.15 sube a y = 69,5 (encima de la pista U2.16–C13)
AMC_LDO_VIEJO = {("pista", (54.99, 64.635), (54.99, 67.35)): dict(x1=54.99, y1=64.635, x2=54.99, y2=69.5),
                 ("pista", (54.99, 67.35), (54.99, 68.445)): dict(x1=54.99, y1=69.5, x2=54.99, y2=68.445),
                 ("via", (54.99, 67.35)): dict(x=54.99, y=69.5)}
CON_RUTEADOR = ["C30.2"]


def buscar(objs, red, tipo, pts):
    for o in objs:
        if o["tipo"] != tipo or o["red"] != red:
            continue
        if tipo == "via":
            if abs(o["x"] - pts[0][0]) < 0.01 and abs(o["y"] - pts[0][1]) < 0.01:
                return o
        else:
            a, b = o["formas"][0].pts
            if all(abs(a[j] - pts[0][j]) < 0.01 and abs(b[j] - pts[1][j]) < 0.01 for j in (0, 1)) or \
               all(abs(b[j] - pts[0][j]) < 0.01 and abs(a[j] - pts[1][j]) < 0.01 for j in (0, 1)):
                return o
    raise SystemExit(f"No encontré {tipo} {red} {pts}")


def unir_con_ruteador(objs, clases, nuevos, nombre):
    p = next(o for o in objs if o["tipo"] == "pad" and rr.nombre(o) == nombre)
    caja = (max(0, p["x"] - 6), max(0, p["y"] - 6), min(rr.LARGO, p["x"] + 6), min(rr.ALTO, p["y"] + 6))
    rej = rt.Rejilla(*caja)
    otros = [o for o in objs if o["red"] == "GND" and o is not p and not o["keepout"]]
    # U3.2 sale entre la esquina de U3.1 y la vía de ATM_RST: el pasillo es de 0,72 mm y solo entra una de 0,25
    for via, ancho in ((rt.VIA_POT, 0.4), (rt.VIA_SENAL, 0.3), (rt.VIA_SENAL, 0.25)):
        bloq, via_no = rt.mapas(rej, objs, clases, "GND", ancho / 2, via[1] / 2, via[0])
        ini = rt.mascara_objs(rej, [p])
        cobre = rt.mascara_objs(rej, otros)
        meta = {TOP: (cobre[TOP] | (~via_no & ~bloq[TOP])) & ~ini[TOP], BOT: np.zeros_like(via_no)}
        camino = rt.astar(rej, bloq, via_no, ini, meta, {TOP: 1.0, BOT: 99.0}, costo_via=99.0, giro=0.1)
        if camino is None:
            continue
        pistas, _ = rt.a_primitivas(rej, camino, "GND", ancho, via)
        fin = camino[-1]
        x, y = rej.xy(fin[1], fin[2])
        for q in pistas:
            objs.append(rt.obj_pista(q))
            nuevos["pistas"].append(q)
        if not cobre[TOP][fin[1], fin[2]]:            # terminó en un lugar libre: vía al plano de Bottom
            v = dict(red="GND", x=x, y=y, hueco=via[0], dia=via[1])
            objs.append(rt.obj_via(v))
            nuevos["vias"].append(v)
        largo = sum(math.hypot(q["x2"] - q["x1"], q["y2"] - q["y1"]) for q in pistas)
        print(f"  {nombre}: {len(pistas)} pistas ({largo:.1f} mm)" + ("" if cobre[TOP][fin[1], fin[2]] else " y una vía"))
        return
    print(f"  {nombre}: sin camino")


def main():
    objs, clases = rr.cargar()
    nuevos = {"pistas": [], "vias": [], "anillos": [], "mod_pistas": {}, "mod_vias": {}}
    for (tipo, *pts), m in AMC_LDO_VIEJO.items():
        o = buscar(objs, "AMC_LDO", tipo, pts)
        if tipo == "via":
            o.update(m)
            f = rr.Forma("pt", [(o["x"], o["y"])], o["dia"] / 2)
            nuevos["mod_vias"][o["k"]] = m
        else:
            f = rr.Forma("seg", [(m["x1"], m["y1"]), (m["x2"], m["y2"])], o["ancho"] / 2)
            nuevos["mod_pistas"][o["k"]] = dict(m, capa=o["capa"])
        o["formas"], o["caja"], o["nuevo"] = [f], f.caja, True
    for p in PISTAS:
        objs.append(rt.obj_pista(p))
        nuevos["pistas"].append(p)
    for v in VIAS:
        objs.append(rt.obj_via(v))
        nuevos["vias"].append(v)
    for nombre in CON_RUTEADOR:
        unir_con_ruteador(objs, clases, nuevos, nombre)
    malos = rt.revisar_nuevos(objs, clases)
    print(f"Nuevos: {len(nuevos['pistas'])} pistas, {len(nuevos['vias'])} vías; problemas: {len(malos)}")
    for m in malos:
        print("  ", m)
    if "--escribir" in sys.argv:
        if malos:
            sys.exit("Hay problemas: no se escribe.")
        import aplicar_ruteo_f8
        aplicar_ruteo_f8.escribir(nuevos, None)


if __name__ == "__main__":
    main()
