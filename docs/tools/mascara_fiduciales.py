# -*- coding: utf-8 -*-
"""Pone la máscara de soldadura manual de los fiduciales FID1–FID3 de EVSE_Monitor.PcbDoc (Altium CERRADO).

Uso: python docs/tools/mascara_fiduciales.py [--escribir] [--mm 0.5]

Pads6: cada pad = tipo 2 + 6 bloques (uint32 largo + datos). En el bloque 5 (geometría), como lo lee el
importador de Altium de KiCad: expansión manual de pasta int32 [86], de máscara int32 [90], modo de pasta
[101] y de máscara [102] (1 = según regla, 2 = manual). Unidades internas = 1/10000 mil.
"""
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import altium_ole as ao  # noqa: E402
import revisar_pcb as rv  # noqa: E402

NOMBRES = {"FID1", "FID2", "FID3"}


def main():
    escribir = "--escribir" in sys.argv
    mm = float(sys.argv[sys.argv.index("--mm") + 1]) if "--mm" in sys.argv else 0.5
    valor = round(mm / 0.0254 * 10000)
    data = bytearray(ao.leer_stream(rv.PCB, "Pads6/Data"))
    i, hechos = 0, []
    while i < len(data):
        assert data[i] == 2
        i += 1
        bloques = []
        for _ in range(6):
            ln = struct.unpack_from("<I", data, i)[0]
            bloques.append((i + 4, ln))
            i += 4 + ln
        ini, ln = bloques[0]
        nombre = bytes(data[ini + 1:ini + 1 + data[ini]]).decode("latin-1")
        g, lg = bloques[4]
        comp = struct.unpack_from("<H", data, g + 7)[0]
        if nombre in NOMBRES and comp == 0xFFFF and lg > 102:
            antes = (struct.unpack_from("<i", data, g + 90)[0], data[g + 102])
            struct.pack_into("<i", data, g + 90, valor)
            data[g + 102] = 2
            hechos.append((nombre, antes))
    print(f"Fiduciales: {[(n, f'{a[0] * 0.0254 / 10000:.3f} mm, modo {a[1]}') for n, a in hechos]} -> {mm} mm manual")
    if len(hechos) != len(NOMBRES):
        sys.exit("No encontré los 3 fiduciales (¿corriste AgujerosF8?).")
    if not escribir:
        print("(prueba: usa --escribir)")
        return
    if ao.altium_abierto():
        sys.exit("Altium está abierto (X2.exe): ciérralo antes de escribir.")
    print("Respaldo:", ao.respaldo(rv.PCB, "antes_mascara_fiduciales"))
    ao.escribir_streams(rv.PCB, {"Pads6/Data": bytes(data)})
    print("Escrito.")


if __name__ == "__main__":
    main()
