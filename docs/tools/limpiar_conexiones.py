# -*- coding: utf-8 -*-
"""Borra las líneas de conexión (ratsnest) guardadas en EVSE_Monitor.PcbDoc para que Altium las recalcule al abrir.

Uso: python docs/tools/limpiar_conexiones.py [--escribir]      (Altium CERRADO)

Por qué: al mover componentes con un script de Altium (ubicar/reorganizar_f8.pas), el analizador de redes no
recalculó las conexiones y Altium las guardó apuntando a las posiciones viejas (20 oct: 385 de 558 extremos
fuera de la placa). Las conexiones son datos derivados de las redes y los pads:
- `Connections6/Data`: registros uint32 largo + 43 bytes (capa, red uint16 [3], x1 y1 x2 y2 int32 [13..28]);
  `Connections6/Header` = cantidad.
- `PrimitiveGuids/Data`: registros de 24 bytes (uint32 tipo, uint32 índice, GUID de 16 bytes); el tipo 0x807
  son las conexiones (tantos como registros de Connections6). `PrimitiveGuids/Header` = cantidad.
Se vacía Connections6 y se quitan los GUID de tipo 0x807; lo demás queda igual.
"""
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import altium_ole as ao  # noqa: E402
import revisar_pcb as rv  # noqa: E402

TIPO_CONEXION = 0x807


def main():
    con = ao.leer_stream(rv.PCB, "Connections6/Data")
    n_con = struct.unpack("<I", ao.leer_stream(rv.PCB, "Connections6/Header"))[0]
    guids = ao.leer_stream(rv.PCB, "PrimitiveGuids/Data")
    n_g = struct.unpack("<I", ao.leer_stream(rv.PCB, "PrimitiveGuids/Header"))[0]
    assert len(guids) == 24 * n_g, "PrimitiveGuids: formato inesperado"
    regs = [guids[i:i + 24] for i in range(0, len(guids), 24)]
    quedan = [r for r in regs if struct.unpack_from("<I", r, 0)[0] != TIPO_CONEXION]
    quitados = len(regs) - len(quedan)
    print(f"Conexiones guardadas: {n_con} ({len(con)} bytes); GUID de conexiones: {quitados} de {n_g}")
    if quitados != n_con:
        sys.exit("La cantidad de GUID 0x807 no coincide con las conexiones: no se toca nada.")
    if "--escribir" not in sys.argv:
        print("(prueba: usa --escribir)")
        return
    if ao.altium_abierto():
        sys.exit("Altium está abierto (X2.exe): guarda, ciérralo y vuelve a correr.")
    print("Respaldo:", ao.respaldo(rv.PCB, "antes_limpiar_conexiones"))
    ao.escribir_streams(rv.PCB, {
        "Connections6/Data": b"",
        "Connections6/Header": struct.pack("<I", 0),
        "PrimitiveGuids/Data": b"".join(quedan),
        "PrimitiveGuids/Header": struct.pack("<I", len(quedan)),
    })
    print("Listo: conexiones vacías; Altium las recalcula al abrir (si no aparecen: N » Show Connections » All).")


if __name__ == "__main__":
    main()
