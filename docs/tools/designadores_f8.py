# -*- coding: utf-8 -*-
"""F8 (22 oct): mueve los designadores que quedaron encima de pads (Altium CERRADO).

El DRC del 22 oct dio 86 «Silk To Solder Mask» de texto sobre pad: al mover piezas durante el ruteo, 56
designadores quedaron sobre los pads de la pieza vecina (C10 sobre C11, R22 sobre U4…). Este script lee la
posición actual de piezas, pads, vías y designadores. Los que tocan un pad o salen de la placa se buscan
en otro lugar con el mismo criterio de serigrafia_f8.py: arriba, abajo, izquierda o derecha de su courtyard, sin
pisar pads, vías, otros textos ni courtyards ajenos; si no hay lugar, sobre su propio cuerpo. Los demás no se tocan
(el usuario movió algunos a mano). Escribe X/Y en el registro de Texts6 del designador (bytes 13 y 17).

Uso: python docs/tools/designadores_f8.py [--escribir]
"""
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import altium_ole as ao  # noqa: E402
import aplicar_ruteo_f8 as ap  # noqa: E402
import revisar_pcb as rv  # noqa: E402
import revisar_ruteo_f8 as rr  # noqa: E402
import serigrafia_f8 as sg  # noqa: E402
import ubicacion_f8 as u  # noqa: E402

U, O = rv.U, 25.4


def leer_designadores():
    comps = rv.texto("Components6/Data")
    orden = [ao.valor(c, "SOURCEDESIGNATOR") for c in comps]
    regs = ap.registros(ao.leer_stream(rv.PCB, "Texts6/Data"), 2)
    out = {}
    for n, (t, bl) in enumerate(regs):
        g = bl[0]
        comp = struct.unpack_from("<H", g, 7)[0]
        if comp == 0xFFFF or g[41] != 1:
            continue
        x, y = (v * U - O for v in struct.unpack_from("<ii", g, 13))
        h = struct.unpack_from("<i", g, 21)[0] * U
        rot = struct.unpack_from("<d", g, 27)[0]
        out[orden[comp]] = dict(n=n, x=x, y=y, h=h, rot=rot)
    return regs, out


def caja(d, t):
    if abs(t["rot"]) < 1 or abs(t["rot"] - 360) < 1:
        return sg.caja_texto(t["x"], t["y"], d, t["h"])
    w = len(d) * sg.ANCHO_CAR * t["h"]                     # rotado 90°: crece hacia arriba
    return (t["x"] - t["h"], t["y"], t["x"], t["y"] + w)


def main():
    info = u.leer()
    pos = {d: (c["x"] - O, c["y"] - O, c["rot"]) for d, c in info.items()}
    objs, _ = rr.cargar()
    # pads: nunca (máscara abierta). Vías: van tapadas (regla Vias_tapadas), así que encima de una se puede, pero se
    # prefiere no hacerlo
    pads = [o["caja"] for o in objs if o["tipo"] == "pad" and not o.get("virtual")]
    vias = [o["caja"] for o in objs if o["tipo"] == "via"]
    cajas = {d: u.caja_en_placa(info[d], p) for d, p in pos.items()}
    regs, des = leer_designadores()
    malos = []
    for d, t in des.items():
        b = caja(d, t)
        fuera = b[0] < 0.3 or b[1] < 0.3 or b[2] > u.LARGO - 0.3 or b[3] > u.ALTO - 0.3
        if fuera or any(sg.se_pisan(b, p, 0.1) for p in pads):
            malos.append(d)
    print(f"Designadores: {len(des)}; sobre pads o fuera de la placa: {len(malos)}")
    ocupado = [caja(d, t) for d, t in des.items() if d not in malos]
    ocupado += [sg.caja_texto(x, y, txt, h) for txt, x, y, h, _, r in sg.TEXTOS if r == 0]
    nuevos, sin_lugar = {}, []
    for d in sorted(malos, key=lambda d: (cajas[d][2] - cajas[d][0]) * (cajas[d][3] - cajas[d][1])):
        b = cajas[d]
        alto = des[d]["h"]
        w = len(d) * sg.ANCHO_CAR * alto
        cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        cand = []
        for sep in (0.15, 0.5, 1.0, 1.6):
            cand += [(cx - w / 2, b[3] + sep), (cx - w / 2, b[1] - sep - alto),
                     (b[0] - sep - w, cy - alto / 2), (b[2] + sep, cy - alto / 2)]
        elegido = None
        # 1) sin pisar vías ni courtyards ajenos; 2) encima de courtyards ajenos; 3) también encima de vías tapadas
        for nivel in (1, 2, 3):
            obst = pads + (vias if nivel < 3 else [])
            for x, y in cand:
                t = sg.caja_texto(x, y, d, alto)
                if t[0] < 0.4 or t[1] < 0.4 or t[2] > u.LARGO - 0.4 or t[3] > u.ALTO - 0.4:
                    continue
                if any(sg.se_pisan(t, p, 0.12) for p in obst) or any(sg.se_pisan(t, o, 0.1) for o in ocupado):
                    continue
                if nivel == 1 and any(sg.se_pisan(t, cajas[e]) for e in pos if e != d):
                    continue
                elegido = (x, y)
                break
            if elegido:
                break
        if elegido is None:                       # sobre su propio cuerpo, entre sus pads
            for dx in (0.0, -0.3, 0.3, -0.6, 0.6):
                for dy in (0.0, -0.4, 0.4, -0.8, 0.8):
                    x, y = cx - w / 2 + dx, cy - alto / 2 + dy
                    t = sg.caja_texto(x, y, d, alto)
                    if not any(sg.se_pisan(t, p, 0.1) for p in pads) and not any(sg.se_pisan(t, o, 0.1) for o in ocupado):
                        elegido = (x, y)
                        break
                if elegido:
                    break
        rot = 0.0
        if elegido is None:                       # vertical (90°) al lado del courtyard, encima de vías si hace falta
            for sep in (0.15, 0.5, 1.0):
                for x, y in ((b[0] - sep, cy - w / 2), (b[2] + sep + alto, cy - w / 2)):
                    t = caja(d, dict(x=x, y=y, h=alto, rot=90.0))
                    if t[0] < 0.4 or t[1] < 0.4 or t[2] > u.LARGO - 0.4 or t[3] > u.ALTO - 0.4:
                        continue
                    if any(sg.se_pisan(t, q, 0.12) for q in pads) or any(sg.se_pisan(t, o, 0.1) for o in ocupado):
                        continue
                    elegido, rot = (x, y), 90.0
                    break
                if elegido:
                    break
        if elegido is None:
            sin_lugar.append(d)
            continue
        nuevos[d] = (elegido[0], elegido[1], rot)
        ocupado.append(caja(d, dict(x=elegido[0], y=elegido[1], h=alto, rot=rot)))
    print(f"Reubicados: {len(nuevos)}; sin lugar libre (se dejan): {sin_lugar}")
    for d, (x, y, r) in sorted(nuevos.items()):
        print(f"  {d:5} ({des[d]['x']:.2f}, {des[d]['y']:.2f}) -> ({x:.2f}, {y:.2f})" + (" vertical" if r else ""))
    if "--escribir" not in sys.argv:
        print("(prueba: usa --escribir)")
        return
    if ao.altium_abierto():
        sys.exit("Altium está abierto (X2.exe): guarda, ciérralo y vuelve a correr.")
    print("Respaldo:", ao.respaldo(rv.PCB, "antes_designadores_f8"))
    for d, (x, y, r) in nuevos.items():
        t, bl = regs[des[d]["n"]]
        g = bytearray(bl[0])
        struct.pack_into("<ii", g, 13, ap.interno(x), ap.interno(y))
        struct.pack_into("<d", g, 27, r)
        regs[des[d]["n"]] = (t, [bytes(g), bl[1]])
    ao.escribir_streams(rv.PCB, {"Texts6/Data": ap.unir(regs)})
    print("Escrito.")


if __name__ == "__main__":
    main()
