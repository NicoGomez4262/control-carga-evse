# -*- coding: utf-8 -*-
"""Revisa EVSE_Monitor.PcbDoc sin abrir Altium: componentes y footprints, redes, clases, pares
diferenciales, reglas, stackup, contorno y pads (agujero y anillo) de una pieza.

Uso: python docs/tools/revisar_pcb.py [--pads J5] [--reglas] [--clases]

Formato: Components6, Nets6, Classes6, DifferentialPairs6 = registros uint32 + texto «|CLAVE=valor|»;
Pads6 = registros binarios como los de las PcbLib (pcblib.py): tipo 2 + 6 bloques; en el bloque de
geometría: capa [0], red uint16 [3], componente uint16 [7], x/y int32 [13]/[17], tamaño arriba
[21]/[25], agujero [45] (unidades de 1/10000 mil).
"""
import struct
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import altium_ole as ao  # noqa: E402
import pcblib  # noqa: E402

PCB = Path(r"C:/Nicolas/UNIVERSIDAD - 2026/Hardware en IoT/Control de Carga IoT/Control de Carga IoT/EVSE_Monitor.PcbDoc")
U = 0.0254 / 10000  # mm por unidad interna


def texto(stream):
    data = ao.leer_stream(PCB, stream)
    out, i = [], 0
    while i + 4 <= len(data):
        ln = struct.unpack_from("<I", data, i)[0]
        out.append(ao.campos(data[i + 4:i + 4 + ln]))
        i += 4 + ln
    return out


def reglas():
    data = ao.leer_stream(PCB, "Rules6/Data")
    out, i = [], 0
    while i < len(data):
        code = struct.unpack_from("<H", data, i)[0]
        ln = struct.unpack_from("<I", data, i + 2)[0]
        out.append((code, ao.campos(data[i + 6:i + 6 + ln])))
        i += 6 + ln
    return out


def pads():
    data = ao.leer_stream(PCB, "Pads6/Data")
    out, i = [], 0
    while i < len(data):
        t = data[i]
        i += 1
        bl, i = pcblib.bloques(data, i, 6)
        assert t == 2, t
        nombre = bl[0][1:1 + bl[0][0]].decode("latin-1")
        g = bl[4]
        capa = g[0]
        red = struct.unpack_from("<H", g, 3)[0]
        comp = struct.unpack_from("<H", g, 7)[0]
        x, y = struct.unpack_from("<ii", g, 13)
        sx, sy = struct.unpack_from("<ii", g, 21)
        hueco = struct.unpack_from("<i", g, 45)[0]
        out.append(dict(nombre=nombre, capa=capa, red=red, comp=comp, x=x * U, y=y * U, sx=sx * U, sy=sy * U,
                        hueco=hueco * U))
    return out


def main():
    comps = texto("Components6/Data")
    nets = [ao.valor(n, "NAME") for n in texto("Nets6/Data")]
    print(f"Componentes: {len(comps)}  ·  redes: {len(nets)}")
    des = [ao.valor(c, "SOURCEDESIGNATOR") for c in comps]
    rep = [d for d, n in Counter(des).items() if n > 1]
    if rep:
        print("  designadores repetidos:", rep)
    fps = Counter(ao.valor(c, "PATTERN") for c in comps)
    print("  footprints distintos:", len(fps))
    fuera = []
    for c in comps:
        x = float(ao.valor(c, "X").replace("mil", "")) - 1000
        y = float(ao.valor(c, "Y").replace("mil", "")) - 1000
        if not (0 <= x <= 3937 and 0 <= y <= 3937):
            fuera.append(ao.valor(c, "SOURCEDESIGNATOR"))
    print(f"  fuera de la placa: {len(fuera)}")
    esperadas = ["AC_L1", "AC_L1_F", "AC_L2", "AC_L2_F", "HV_D1", "HV_D2", "HV_D3", "HV_INP", "HV_DCDC", "HV_LDO",
                 "EVSE_EN_A", "EVSE_EN_B", "USB_DP", "USB_DN", "+VIN", "VIN_ACDC", "VIN_BANCO", "+3V3", "+3V3A", "GND"]
    faltan = [n for n in esperadas if n not in nets]
    print("  redes de las reglas que no están:", faltan or "ninguna")
    print("  redes sin nombre propio (Net…):", sorted(n for n in nets if n.startswith("Net"))[:40])

    print("\nClases:")
    for c in texto("Classes6/Data"):
        miembros = [v for k, v in c if k.startswith("M") and k[1:].isdigit()]
        if ao.valor(c, "KIND") in ("0", None) or len(miembros) < 60:
            print(f"  [{ao.valor(c, 'KIND')}] {ao.valor(c, 'NAME')}: {len(miembros)} ->",
                  ", ".join(miembros[:24]) + (" …" if len(miembros) > 24 else ""))

    print("\nPares diferenciales:")
    for d in texto("DifferentialPairs6/Data"):
        print("  ", {k: v for k, v in d if k in ("NAME", "POSITIVENETNAME", "NEGATIVENETNAME", "POSITIVENET", "NEGATIVENET")} or d)

    if "--reglas" in sys.argv:
        print("\nReglas:")
        for code, f in reglas():
            extra = {k: v for k, v in f if k not in ("SELECTION", "LAYER", "LOCKED", "POLYGONOUTLINE", "USERROUTED",
                                                     "KEEPOUT", "UNIONINDEX", "NETSCOPE", "LAYERKIND", "ENABLED",
                                                     "COMMENT", "UNIQUEID", "DEFINEDBYLOGICALDOCUMENT", "NAME",
                                                     "RULEKIND", "PRIORITY", "SCOPE1EXPRESSION", "SCOPE2EXPRESSION")
                     and not k.startswith("MIDLAYER")}
            print(f"  {code:3} {ao.valor(f, 'RULEKIND'):24} {ao.valor(f, 'PRIORITY'):>2} {ao.valor(f, 'NAME'):24} "
                  f"{ao.valor(f, 'SCOPE1EXPRESSION')} | {ao.valor(f, 'SCOPE2EXPRESSION')} | {extra}")

    b = ao.campos(ao.leer_stream(PCB, "Board6/Data")[4:])
    print("\nStackup:")
    for k, v in b:
        if k.startswith("V9_STACK_LAYER") and (k.endswith("_NAME") or "COPTHICK" in k or "DIELHEIGHT" in k or "DIELCONST" in k):
            print(f"  {k} = {v}")
    print("Contorno:", [(ao.valor(b, f"VX{i}"), ao.valor(b, f"VY{i}")) for i in range(5)])

    if "--pads" in sys.argv:
        quien = sys.argv[sys.argv.index("--pads") + 1]
        idx = des.index(quien)
        ps = [p for p in pads() if p["comp"] == idx]
        cx = float(ao.valor(comps[idx], "X").replace("mil", "")) * 0.0254
        cy = float(ao.valor(comps[idx], "Y").replace("mil", "")) * 0.0254
        print(f"\nPads de {quien} ({ao.valor(comps[idx], 'PATTERN')}), relativos al origen de la pieza:")
        for p in sorted(ps, key=lambda p: (round(p["y"] - cy, 2), p["x"])):
            anillo = (min(p["sx"], p["sy"]) - p["hueco"]) / 2 if p["hueco"] else None
            print(f"  {p['nombre']:5} capa {p['capa']:3} x={p['x'] - cx:7.3f} y={p['y'] - cy:7.3f} "
                  f"{p['sx']:.3f} x {p['sy']:.3f}  agujero {p['hueco']:.3f}"
                  + (f"  anillo {anillo:.3f}" if anillo is not None else ""))


if __name__ == "__main__":
    main()
