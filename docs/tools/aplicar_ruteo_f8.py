# -*- coding: utf-8 -*-
"""F8: escribe en EVSE_Monitor.PcbDoc lo que calcula rutear_f8.py (Altium CERRADO). Lo llama
`python docs/tools/rutear_f8.py --escribir`.

- Pistas y vías nuevas: se copian de un registro del mismo tipo que ya está en el archivo (una pista libre; una
  vía del mismo tamaño, porque la vía guarda el GUID de su plantilla de 0,3/0,6 o 0,4/0,8 en los bytes 259–274)
  y se cambian red, capa, coordenadas y ancho. Los cambios a mano reescriben su propio registro (no se borra
  ninguno: los índices de PrimitiveGuids no se corren).
- Anillos de keepout de los fiduciales: arcos de 360° en Top con el flag de keepout (byte 2 = 2, como los rellenos
  de la capa Keep-Out), así solo restringen Top; copiados de un arco libre.
- Polígonos de GND (Top y Bottom): registros de texto de Polygons6 con los campos de un polígono de los ejemplos
  de AD25 (SL1 Xilinx Spartan-IIE); quedan sin verter: en Altium, Tools » Polygon Pours » Repour All.
- Se vacían las conexiones guardadas (Altium las recalcula al abrir) y las violaciones guardadas
  (TClearanceViolation, TDiffPairsViolation), que apuntan a índices viejos; el DRC las vuelve a calcular.
"""
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import altium_ole as ao  # noqa: E402
import pcblib  # noqa: E402
import revisar_pcb as rv  # noqa: E402

U = rv.U
O = 25.4
TIPO_CONEXION = 0x807


def interno(mm):
    return int(round((mm + O) / U))


def mil(mm):
    return f"{(mm + O) / 0.0254:.4f}mil"


def registros(data, nb):
    out, i = [], 0
    while i < len(data):
        t = data[i]
        i += 1
        bl, i = pcblib.bloques(data, i, nb)
        out.append((t, bl))
    return out


def unir(regs):
    return b"".join(bytes([t]) + b"".join(struct.pack("<I", len(b)) + b for b in bl) for t, bl in regs)


# La capa está dos veces en una pista: el byte 0 (1 Top, 32 Bottom) y la «capa V7» de los bytes 41–44, que es la
# que Altium lee. Con solo el byte 0, Altium dejó en Top las pistas nuevas de Bottom (22 oct: 30 cortos).
CAPA_V7 = {1: bytes.fromhex("01000001"), 32: bytes.fromhex("ffff0001")}


def pista_bin(g, red_idx, capa, x1, y1, x2, y2, ancho=None):
    g = bytearray(g)
    g[0] = capa
    g[41:45] = CAPA_V7[capa]
    if red_idx is not None:
        struct.pack_into("<H", g, 3, red_idx)
    struct.pack_into("<iiii", g, 13, interno(x1), interno(y1), interno(x2), interno(y2))
    if ancho is not None:
        struct.pack_into("<i", g, 29, int(round(ancho / U)))
    return bytes(g)


def poligono_txt(nombre, capa, red_idx, contorno, indice):
    pts = list(contorno) + [contorno[0]]
    campos = [("SELECTION", "FALSE"), ("LAYER", capa), ("LOCKED", "FALSE"), ("POLYGONOUTLINE", "FALSE"),
              ("USERROUTED", "TRUE"), ("KEEPOUT", "FALSE"), ("UNIONINDEX", "0"), ("PRIMITIVELOCK", "TRUE"),
              ("POLYGONTYPE", "Polygon"), ("POUROVER", "TRUE"), ("REMOVEDEAD", "TRUE"), ("GRIDSIZE", "7.874mil"),
              ("TRACKWIDTH", "8.2677mil"), ("HATCHSTYLE", "Solid"), ("USEOCTAGONS", "FALSE"),
              ("MINPRIMLENGTH", "2.9921mil")]
    for k, (x, y) in enumerate(pts):
        campos += [(f"KIND{k}", "0"), (f"VX{k}", mil(x)), (f"VY{k}", mil(y)), (f"CX{k}", "0mil"), (f"CY{k}", "0mil"),
                   (f"SA{k}", " 0.00000000000000E+0000"), (f"EA{k}", " 0.00000000000000E+0000"), (f"R{k}", "0mil")]
    campos += [("SHELVED", "FALSE"), ("RESTORELAYER", "UNKNOWN"), ("RESTORENET", "GND"),
               ("REMOVEISLANDSBYAREA", "TRUE"), ("REMOVENECKS", "TRUE"), ("AREATHRESHOLD", "310000627729.000000"),
               ("ARCRESOLUTION", "0.5118mil"), ("NECKWIDTHTHRESHOLD", "5mil"), ("POUROVERSTYLE", "1"),
               ("NAME", ",".join(str(ord(c)) for c in nombre)), ("POURINDEX", str(indice)),
               ("IGNOREVIOLATIONS", "FALSE"), ("NET", str(red_idx))]
    t = ao.cuerpo(campos)
    return struct.pack("<I", len(t)) + t


def escribir(nuevos, polis):
    import rutear_f8 as rt
    if ao.altium_abierto():
        sys.exit("Altium está abierto (X2.exe): guarda, ciérralo y vuelve a correr.")
    pcb = rv.PCB
    nets = [ao.valor(n, "NAME") for n in rv.texto("Nets6/Data")]
    idx = {n: i for i, n in enumerate(nets)}
    print("Respaldo:", ao.respaldo(pcb, "antes_ruteo_f8"))

    # pistas
    tr = registros(ao.leer_stream(pcb, "Tracks6/Data"), 1)
    plantilla = next(bl[0] for t, bl in tr if struct.unpack_from("<H", bl[0], 7)[0] == 0xFFFF and bl[0][0] in (1, 32)
                     and bl[0][33:] == bytes.fromhex("00000000000000000100000100000000"))
    for k, m in nuevos.get("mod_pistas", {}).items():
        t, bl = tr[k]
        g = bl[0]
        x1, y1, x2, y2 = (v * U - O for v in struct.unpack_from("<iiii", g, 13))
        g2 = pista_bin(g, idx[m["red"]] if "red" in m else None, m.get("capa", g[0]),
                       m.get("x1", x1), m.get("y1", y1), m.get("x2", x2), m.get("y2", y2))
        tr[k] = (t, [g2])
    for p in nuevos["pistas"]:
        tr.append((4, [pista_bin(plantilla, idx[p["red"]], p["capa"], p["x1"], p["y1"], p["x2"], p["y2"], p["ancho"])]))

    # vías
    vs = registros(ao.leer_stream(pcb, "Vias6/Data"), 1)
    por_dia = {}
    for t, bl in vs:
        por_dia.setdefault(round(struct.unpack_from("<i", bl[0], 21)[0] * U, 2), bl[0])
    for k, m in nuevos.get("mod_vias", {}).items():
        t, bl = vs[k]
        g = bytearray(bl[0])
        struct.pack_into("<ii", g, 13, interno(m["x"]), interno(m["y"]))
        vs[k] = (t, [bytes(g)])
    for v in nuevos["vias"]:
        g = bytearray(por_dia[round(v["dia"], 2)])
        struct.pack_into("<H", g, 3, idx[v["red"]])
        struct.pack_into("<ii", g, 13, interno(v["x"]), interno(v["y"]))
        vs.append((3, [bytes(g)]))

    # anillos de keepout
    ar = registros(ao.leer_stream(pcb, "Arcs6/Data"), 1)
    plantilla_arco = next(bl[0] for t, bl in ar if struct.unpack_from("<H", bl[0], 7)[0] == 0xFFFF)
    for a in nuevos.get("anillos", []):
        g = bytearray(plantilla_arco)
        g[0], g[2] = 1, 2                         # Top, con el flag de keepout
        struct.pack_into("<H", g, 3, 0xFFFF)
        struct.pack_into("<iii", g, 13, interno(a["x"]), interno(a["y"]), int(round(a["r"] / U)))
        struct.pack_into("<dd", g, 25, 0.0, 360.0)
        struct.pack_into("<i", g, 41, int(round(a["ancho"] / U)))
        ar.append((1, [bytes(g)]))

    # polígonos (polis=None: se dejan los que hay, ya vertidos por Altium)
    pol = None if polis is None else         b"".join(poligono_txt(p["nombre"], p["capa"], idx["GND"], p["contorno"], p["indice"]) for p in polis)

    # conexiones y violaciones guardadas
    guids = ao.leer_stream(pcb, "PrimitiveGuids/Data")
    regs_g = [guids[i:i + 24] for i in range(0, len(guids), 24)]
    regs_g = [r for r in regs_g if struct.unpack_from("<I", r, 0)[0] != TIPO_CONEXION]

    cambios = {
        "Tracks6/Data": unir(tr), "Tracks6/Header": struct.pack("<I", len(tr)),
        "Vias6/Data": unir(vs), "Vias6/Header": struct.pack("<I", len(vs)),
        "Arcs6/Data": unir(ar), "Arcs6/Header": struct.pack("<I", len(ar)),
        "Connections6/Data": b"", "Connections6/Header": struct.pack("<I", 0),
        "PrimitiveGuids/Data": b"".join(regs_g), "PrimitiveGuids/Header": struct.pack("<I", len(regs_g)),
    }
    if pol is not None:
        cambios.update({"Polygons6/Data": pol, "Polygons6/Header": struct.pack("<I", len(polis))})
    hay = set(ao.streams(pcb))       # Altium borra los streams de violaciones cuando no hay
    for s in ("TClearanceViolation", "TDiffPairsViolation", "TShortCircuitViolation"):
        if f"{s}/Data" in hay:
            cambios.update({f"{s}/Data": b"", f"{s}/Header": struct.pack("<I", 0)})
    ao.escribir_streams(pcb, cambios)
    print(f"Escrito: {len(tr)} pistas, {len(vs)} vías, {len(ar)} arcos, {len(polis or [])} polígonos nuevos; conexiones y "
          f"violaciones guardadas vaciadas.")
    del rt
