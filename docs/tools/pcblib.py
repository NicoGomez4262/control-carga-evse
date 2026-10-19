# -*- coding: utf-8 -*-
"""Lee los pads de un footprint de una PcbLib de Altium (nombre, posición, tamaño, agujero) sin abrir Altium.

Uso: python docs/tools/pcblib.py <PcbLib> [footprint]
Unidades internas de Altium: 1/10000 mil. Se imprimen en mm.
"""
import struct
import sys

import olefile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
U = 0.0254 / 10000  # mm por unidad interna


def bloques(d, i, n):
    out = []
    for _ in range(n):
        ln = struct.unpack_from("<I", d, i)[0]
        out.append(d[i + 4:i + 4 + ln])
        i += 4 + ln
    return out, i


NBLOQ = {1: 1, 2: 6, 3: 1, 4: 1, 5: 2, 6: 1, 11: 1, 12: 1}


def pads(data):
    i = 0
    ln = struct.unpack_from("<I", data, 0)[0]
    i = 4 + ln
    out = []
    while i < len(data):
        t = data[i]
        i += 1
        if t not in NBLOQ:
            break
        bl, i = bloques(data, i, NBLOQ[t])
        if t == 2:
            nombre = bl[0][1:1 + bl[0][0]].decode("latin-1")
            g = bl[4]
            capa = g[0]
            x, y = struct.unpack_from("<ii", g, 13)
            sx, sy = struct.unpack_from("<ii", g, 21)
            hueco = struct.unpack_from("<i", g, 45)[0]
            forma = g[49]
            rot = struct.unpack_from("<d", g, 52)[0]
            out.append((nombre, capa, x * U, y * U, sx * U, sy * U, hueco * U, forma, rot))
    return out


def footprints(ruta):
    o = olefile.OleFileIO(str(ruta))
    return o, sorted({e[0] for e in o.listdir() if len(e) > 1 and o.exists(f"{e[0]}/Data")} - {"Library", "FileVersionInfo"})


if __name__ == "__main__":
    o, fps = footprints(sys.argv[1])
    for fp in fps:
        if len(sys.argv) > 2 and fp != sys.argv[2]:
            continue
        ps = pads(o.openstream(f"{fp}/Data").read())
        print(f"== {fp}: {len(ps)} pads (capa 1 = top, 74 = multicapa)")
        for n, capa, x, y, sx, sy, h, forma, rot in sorted(ps, key=lambda p: (p[0][:1], len(p[0]), p[0])):
            print(f"  {n:6s} capa {capa:3d}  x={x:7.3f} y={y:7.3f}  {sx:5.2f} x {sy:5.2f} mm"
                  + (f"  agujero {h:4.2f}" if h else "") + (f"  rot {rot:.0f}" if rot else ""))
