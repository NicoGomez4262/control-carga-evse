# -*- coding: utf-8 -*-
"""F8 (22 oct): corrige las pistas de Bottom que aplicar_ruteo_f8.py escribió solo con el byte 0 de la capa.

Altium lee la «capa V7» (bytes 41–44 de la pista: 01000001 = Top, ffff0001 = Bottom), así que al abrir y guardar
dejó en Top las pistas nuevas que iban por Bottom (30 cortos). Este script vuelve a calcular lo que escribió
rutear_f8.py sobre el respaldo de antes de escribir, busca esas pistas por red y coordenadas en el PcbDoc actual
y les pone Bottom en los dos campos. Además repone el par diferencial USB_D (el ECO de F1B lo borró porque no está
en el esquemático) y vacía las conexiones y violaciones guardadas.

Uso: python docs/tools/corregir_capas_f8.py [--escribir]      (Altium CERRADO)
"""
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import altium_ole as ao  # noqa: E402
import aplicar_ruteo_f8 as ap  # noqa: E402
import revisar_pcb as rv  # noqa: E402

RAIZ = Path(__file__).resolve().parents[2]
ANTES = RAIZ / "docs" / "respaldos" / "EVSE_Monitor_20261022_143525_antes_ruteo_f8.PcbDoc"


def clave(red, x1, y1, x2, y2):
    a, b = (x1, y1), (x2, y2)
    return (red, min(a, b), max(a, b))


def esta(k, claves, tol=0.01):
    """Misma red y mismos extremos (en cualquier orden) con tolerancia: el redondeo a 0,01 mm partía 64,635."""
    for c in claves:
        if c[0] == k[0] and all(abs(c[i][j] - k[i][j]) < tol for i in (1, 2) for j in (0, 1)):
            return True
    return False


def bottom_previstas():
    import revisar_ruteo_f8 as rr
    import rutear_f8 as rt
    actual = rv.PCB
    rv.PCB = ANTES
    try:
        objs, clases = rr.cargar()
        nuevos = rt.calcular(objs, clases)
    finally:
        rv.PCB = actual
    claves = {clave(p["red"], p["x1"], p["y1"], p["x2"], p["y2"]) for p in nuevos["pistas"] if p["capa"] == rt.BOT}
    for k, m in rt.MOD_PISTAS.items():
        if m.get("capa") == rt.BOT:
            red = "AMC_DIAG"
            claves.add(clave(m.get("red", red), m["x1"], m["y1"], m["x2"], m["y2"]))
    return claves


def main():
    claves = bottom_previstas()
    print(f"Pistas que tienen que ir por Bottom: {len(claves)}")
    pcb = rv.PCB
    nets = [ao.valor(n, "NAME") for n in rv.texto("Nets6/Data")]
    tr = ap.registros(ao.leer_stream(pcb, "Tracks6/Data"), 1)
    cambiadas, ya = 0, 0
    for n, (t, bl) in enumerate(tr):
        g = bl[0]
        if struct.unpack_from("<H", g, 7)[0] != 0xFFFF or g[0] not in (1, 32):
            continue
        red_i = struct.unpack_from("<H", g, 3)[0]
        red = nets[red_i] if red_i != 0xFFFF else None
        x1, y1, x2, y2 = (v * ap.U - ap.O for v in struct.unpack_from("<iiii", g, 13))
        if not esta(clave(red, x1, y1, x2, y2), claves):
            continue
        if g[0] == 32 and g[41:45] == ap.CAPA_V7[32]:
            ya += 1
            continue
        g = bytearray(g)
        g[0] = 32
        g[41:45] = ap.CAPA_V7[32]
        tr[n] = (t, [bytes(g)])
        cambiadas += 1
    print(f"A Bottom: {cambiadas}; ya estaban: {ya}; no encontradas: {len(claves) - cambiadas - ya}")
    par = ao.leer_stream(ANTES, "DifferentialPairs6/Data")
    print("Par USB_D del respaldo:", par[4:120])
    if "--escribir" not in sys.argv:
        print("(prueba: usa --escribir)")
        return
    if ao.altium_abierto():
        sys.exit("Altium está abierto (X2.exe): guarda, ciérralo y vuelve a correr.")
    if cambiadas + ya != len(claves):
        sys.exit("No se encontraron todas las pistas: no se escribe.")
    print("Respaldo:", ao.respaldo(pcb, "antes_corregir_capas"))
    guids = ao.leer_stream(pcb, "PrimitiveGuids/Data")
    regs_g = [guids[i:i + 24] for i in range(0, len(guids), 24)]
    regs_g = [r for r in regs_g if struct.unpack_from("<I", r, 0)[0] != ap.TIPO_CONEXION]
    cambios = {
        "Tracks6/Data": ap.unir(tr),
        "DifferentialPairs6/Data": par, "DifferentialPairs6/Header": struct.pack("<I", 1),
        "Connections6/Data": b"", "Connections6/Header": struct.pack("<I", 0),
        "PrimitiveGuids/Data": b"".join(regs_g), "PrimitiveGuids/Header": struct.pack("<I", len(regs_g)),
    }
    streams = set(ao.streams(pcb))
    for s in ("TClearanceViolation", "TDiffPairsViolation", "TShortCircuitViolation"):
        if f"{s}/Data" in streams:
            cambios[f"{s}/Data"] = b""
            cambios[f"{s}/Header"] = struct.pack("<I", 0)
    ao.escribir_streams(pcb, cambios)
    print("Escrito.")


if __name__ == "__main__":
    main()
