# -*- coding: utf-8 -*-
"""F9: esquinas redondeadas de la placa (radio 4 mm) en EVSE_Monitor.PcbDoc (Altium CERRADO).

El radio de 4 mm es concéntrico con los agujeros de montaje M1–M4 (Ø 3,2 mm a 4 mm de cada borde): alrededor de
cada agujero quedan 2,4 mm de material, lo mismo que hacia los bordes rectos. En las esquinas no hay más que esos
agujeros y el cobre de GND de las esquinas derechas.

Qué cambia (formato copiado de la placa de esquinas redondeadas del ejemplo de AD25 «Mini PC - WiFi»):
- `Board6`: 9 vértices en sentido antihorario. Un vértice de arco (KINDn=1) es el punto inicial, en el ángulo SAn,
  y el arco va en sentido antihorario hasta EAn, que es el vértice siguiente.
- `BoardRegions`: la región «Default Layer Stack Region» lleva el mismo contorno como polilínea (doubles en 1/10000
  mil), con 16 tramos por esquina; el largo del registro (bytes 1–4) se recalcula.
- Mechanical 1 (lo que sale en el Gerber GM1): las 4 pistas del borde se acortan 4 mm por punta y se agregan 4 arcos
  de 0,1 mm en Mechanical 1 (capa 57; la capa V7 de un arco va en los bytes 52–55, 01000201 como en las pistas).
- Polígonos de GND (Top y Bottom): el contorno se escribe antihorario con las esquinas derechas en arco de 3,5 mm
  (0,5 mm hacia adentro, como los bordes rectos). El cobre vertido queda viejo: en Altium hay que hacer
  Tools » Polygon Pours » Repour All antes del DRC y del OutJob.

- `--via` (después de lo anterior): la vía de costura de GND de (128,5; 2,0) quedaba a 0,4 mm del borde redondeado;
  se corre a 2,5 mm del centro de M2 hacia la esquina (127,77; 2,23): 1,1 mm al borde y 0,5 mm al agujero de M2.

Uso: python docs/tools/esquinas_f9.py            # muestra lo que haría
     python docs/tools/esquinas_f9.py --escribir # respalda el PcbDoc en docs/respaldos/ y escribe
     python docs/tools/esquinas_f9.py --via      # solo corre la vía de la esquina inferior derecha
"""
import math
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import altium_ole as ao  # noqa: E402
import aplicar_ruteo_f8 as ap  # noqa: E402
import revisar_pcb as rv  # noqa: E402

U, O = rv.U, 25.4
LARGO, ALTO = 130.0, 100.0
RADIO = 4.0
RADIO_POLI = 3.5
MECH1, MECH1_V7 = 57, bytes.fromhex("01000201")
VERT = ("KIND", "VX", "VY", "CX", "CY", "SA", "EA", "R")


def mil(mm, absoluto=True):
    v = (mm + O if absoluto else mm) / 0.0254
    return f"{v:.4f}".rstrip("0").rstrip(".") + "mil"


def ang(a):
    """Ángulo con el formato de Delphi de los archivos de Altium: « 2.70000000000000E+0002»."""
    if a == 0:
        return " 0.00000000000000E+0000"
    e = int(math.floor(math.log10(abs(a))))
    return f" {a / 10 ** e:.14f}E{'+' if e >= 0 else '-'}{abs(e):04d}"


def contorno(x1, y1, x2, y2, r, esquinas):
    """Vértices antihorarios desde la esquina inferior izquierda: (kind, x, y, centro, sa, ea). `esquinas` dice cuáles
    se redondean (BR, TR, TL, BL)."""
    v = []
    bl = "BL" in esquinas
    v.append((0, x1 + (r if bl else 0), y1, None, 0, 0))
    for nom, (px, py), (cx, cy), sa, (qx, qy) in (
            ("BR", (x2 - r, y1), (x2 - r, y1 + r), 270, (x2, y1 + r)),
            ("TR", (x2, y2 - r), (x2 - r, y2 - r), 0, (x2 - r, y2)),
            ("TL", (x1 + r, y2), (x1 + r, y2 - r), 90, (x1, y2 - r)),
            ("BL", (x1, y1 + r), (x1 + r, y1 + r), 180, (x1 + r, y1))):
        if nom in esquinas:
            v.append((1, px, py, (cx, cy), sa, sa + 90))
            if nom != "BL":
                v.append((0, qx, qy, None, 0, 0))
        else:
            esq = {"BR": (x2, y1), "TR": (x2, y2), "TL": (x1, y2), "BL": (x1, y1)}[nom]
            if nom != "BL":
                v.append((0, esq[0], esq[1], None, 0, 0))
    v.append(v[0])
    return v


def campos_vertices(v, r):
    out = []
    for k, (kind, x, y, c, sa, ea) in enumerate(v):
        out += [(f"KIND{k}", str(kind)), (f"VX{k}", mil(x)), (f"VY{k}", mil(y)),
                (f"CX{k}", mil(c[0]) if c else "0mil"), (f"CY{k}", mil(c[1]) if c else "0mil"),
                (f"SA{k}", ang(sa) if c else ang(0)), (f"EA{k}", ang(ea) if c else ang(0)),
                (f"R{k}", mil(r, False) if c else "0mil")]
    return out


def reemplazar_vertices(f, nuevos):
    """Saca los campos KINDn…Rn y pone los nuevos en el mismo lugar."""
    es_vert = [n for n, (k, _) in enumerate(f) if any(k.startswith(p) and k[len(p):].isdigit() for p in VERT)]
    pos = es_vert[0]
    quedan = [kv for n, kv in enumerate(f) if n not in set(es_vert)]
    return quedan[:pos] + nuevos + quedan[pos:]


def polilinea(v, pasos=16):
    pts = []
    for kind, x, y, c, sa, ea in v[:-1]:
        pts.append((x, y))
        if kind == 1:
            r = math.dist((x, y), c)
            pts += [(c[0] + r * math.cos(math.radians(sa + (k + 0.5) * (ea - sa) / pasos)),
                     c[1] + r * math.sin(math.radians(sa + (k + 0.5) * (ea - sa) / pasos))) for k in range(pasos)]
            # el punto final del arco es el vértice siguiente
    return pts


def nuevo_board6(data, v):
    ln = struct.unpack_from("<I", data, 0)[0]
    assert ln + 4 == len(data), "Board6: el formato no es el esperado"
    f = ao.campos(data[4:])
    f = reemplazar_vertices(f, campos_vertices(v, RADIO))
    t = ao.cuerpo(f)
    return struct.pack("<I", len(t)) + t


def nuevo_boardregions(data, v):
    i = data.find(b"LAYERSTACKID=")
    j = data.find(b"\x00", i)
    n = struct.unpack_from("<I", data, j + 1)[0]
    assert data[0] == 0x0B and i > 0 and j + 5 + 16 * n == len(data), "BoardRegions: el formato no es el esperado"
    assert struct.unpack_from("<I", data, 1)[0] == len(data) - 5
    pts = polilinea(v)
    cola = struct.pack("<I", len(pts)) + b"".join(struct.pack("<dd", (x + O) / 0.0254 * 1e4, (y + O) / 0.0254 * 1e4)
                                                 for x, y in pts)
    nuevo = bytearray(data[:j + 1] + cola)
    struct.pack_into("<I", nuevo, 1, len(nuevo) - 5)
    return bytes(nuevo), len(pts)


def mech1(tr, ar):
    libres = [k for k, (t, bl) in enumerate(tr) if bl[0][0] == MECH1 and struct.unpack_from("<H", bl[0], 7)[0] == 0xFFFF]
    assert len(libres) == 4, f"Mechanical 1: esperaba 4 pistas del borde, hay {len(libres)}"
    for k in libres:
        g = bytearray(tr[k][1][0])
        x1, y1, x2, y2 = (v * U - O for v in struct.unpack_from("<iiii", g, 13))
        largo = math.dist((x1, y1), (x2, y2))
        assert largo > 50, "Mechanical 1: las pistas ya están acortadas"
        ux, uy = (x2 - x1) / largo, (y2 - y1) / largo
        struct.pack_into("<iiii", g, 13, ap.interno(x1 + RADIO * ux), ap.interno(y1 + RADIO * uy),
                         ap.interno(x2 - RADIO * ux), ap.interno(y2 - RADIO * uy))
        tr[k] = (4, [bytes(g)])
    ancho = struct.unpack_from("<i", tr[libres[0]][1][0], 29)[0]
    plantilla = next(bl[0] for t, bl in ar if struct.unpack_from("<H", bl[0], 7)[0] == 0xFFFF and bl[0][2] == 0)
    nuevos = []
    for (cx, cy), sa in (((LARGO - RADIO, RADIO), 270), ((LARGO - RADIO, ALTO - RADIO), 0),
                         ((RADIO, ALTO - RADIO), 90), ((RADIO, RADIO), 180)):
        g = bytearray(plantilla)
        g[0], g[2] = MECH1, 0
        struct.pack_into("<HH", g, 3, 0xFFFF, 0xFFFF)          # sin red ni polígono
        struct.pack_into("<H", g, 7, 0xFFFF)                    # sin componente
        struct.pack_into("<iii", g, 13, ap.interno(cx), ap.interno(cy), int(round(RADIO / U)))
        struct.pack_into("<dd", g, 25, float(sa), float(sa + 90))
        struct.pack_into("<i", g, 41, ancho)
        g[52:56] = MECH1_V7
        nuevos.append((1, [bytes(g)]))
    return libres, nuevos


def poligonos(data):
    regs, i = [], 0
    while i < len(data):
        n = struct.unpack_from("<I", data, i)[0]
        regs.append(ao.campos(data[i + 4:i + 4 + n]))
        i += 4 + n
    v = contorno(52.0, 0.5, 129.5, 99.5, RADIO_POLI, ("BR", "TR"))
    out = b""
    for f in regs:
        xs = [float(val[:-3]) * 0.0254 - O for k, val in f if k.startswith("VX") and k[2:].isdigit()]
        assert abs(min(xs) - 52.0) < 0.01 and abs(max(xs) - 129.5) < 0.01, "polígono: contorno inesperado"
        f = reemplazar_vertices(f, campos_vertices(v, RADIO_POLI))
        t = ao.cuerpo(f)
        out += struct.pack("<I", len(t)) + t
    return out, len(regs), v


def mover_via():
    pcb = rv.PCB
    vs = ap.registros(ao.leer_stream(pcb, "Vias6/Data"), 1)
    a = math.radians(-45)
    nueva = (LARGO - RADIO + 2.5 * math.cos(a), RADIO + 2.5 * math.sin(a))
    k = next(k for k, (t, bl) in enumerate(vs)
             if math.dist([v * U - O for v in struct.unpack_from("<ii", bl[0], 13)], (128.5, 2.0)) < 0.01)
    g = bytearray(vs[k][1][0])
    struct.pack_into("<ii", g, 13, ap.interno(nueva[0]), ap.interno(nueva[1]))
    vs[k] = (3, [bytes(g)])
    if ao.altium_abierto():
        sys.exit("Altium está abierto (X2.exe): guarda, ciérralo y vuelve a correr.")
    print("Respaldo:", ao.respaldo(pcb, "antes_via_esquina_f9"))
    ao.escribir_streams(pcb, {"Vias6/Data": ap.unir(vs)})
    print(f"Vía {k}: (128.5, 2.0) → ({nueva[0]:.3f}, {nueva[1]:.3f})")


def main():
    if "--via" in sys.argv:
        return mover_via()
    escribir = "--escribir" in sys.argv
    pcb = rv.PCB
    v = contorno(0.0, 0.0, LARGO, ALTO, RADIO, ("BR", "TR", "TL", "BL"))
    b6 = nuevo_board6(ao.leer_stream(pcb, "Board6/Data"), v)
    br, npts = nuevo_boardregions(ao.leer_stream(pcb, "BoardRegions/Data"), v)
    tr = ap.registros(ao.leer_stream(pcb, "Tracks6/Data"), 1)
    ar = ap.registros(ao.leer_stream(pcb, "Arcs6/Data"), 1)
    libres, arcos = mech1(tr, ar)
    pol, npol, vp = poligonos(ao.leer_stream(pcb, "Polygons6/Data"))
    print(f"Contorno: {LARGO:g} x {ALTO:g} mm con esquinas de R {RADIO:g} mm, {len(v)} vértices en Board6; "
          f"BoardRegions con {npts} puntos")
    for kind, x, y, c, sa, ea in v:
        print(f"   {'arco' if kind else 'recta'} ({x:g}, {y:g})" + (f" centro ({c[0]:g}, {c[1]:g}) {sa}°→{ea}°" if c else ""))
    print(f"Mechanical 1: {len(libres)} pistas acortadas {RADIO:g} mm por punta y {len(arcos)} arcos nuevos")
    print(f"Polígonos de GND: {npol}, esquinas derechas en arco de R {RADIO_POLI:g} mm ({len(vp)} vértices)")
    if not escribir:
        print("\n(prueba: no se escribió nada; usa --escribir)")
        return
    if ao.altium_abierto():
        sys.exit("Altium está abierto (X2.exe): guarda, ciérralo y vuelve a correr.")
    print("Respaldo:", ao.respaldo(pcb, "antes_esquinas_f9"))
    ar += arcos
    ao.escribir_streams(pcb, {"Board6/Data": b6, "BoardRegions/Data": br,
                              "Tracks6/Data": ap.unir(tr), "Tracks6/Header": struct.pack("<I", len(tr)),
                              "Arcs6/Data": ap.unir(ar), "Arcs6/Header": struct.pack("<I", len(ar)),
                              "Polygons6/Data": pol, "Polygons6/Header": struct.pack("<I", npol)})
    f = ao.campos(ao.leer_stream(pcb, "Board6/Data")[4:])
    print("Escrito y releído: KIND1 =", ao.valor(f, "KIND1"), "R1 =", ao.valor(f, "R1"), "VX8 =", ao.valor(f, "VX8"),
          "| arcos:", struct.unpack("<I", ao.leer_stream(pcb, "Arcs6/Header"))[0])
    print("En Altium: Tools » Polygon Pours » Repour All, DRC y OutJob.")


if __name__ == "__main__":
    main()
