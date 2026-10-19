# -*- coding: utf-8 -*-
"""Repara los condensadores de SamacSys.SchLib que quedaron con dos pines «1» y sin pin «2».

El 9 oct, al borrar los pines repetidos, quedaron dos pines «1» en el mismo sitio en
C0805C102J5GAC-TU, C0805C120J5GACTU, C0805C472J5GACTU, CL21B104KBCNNNC y CL21B105KAFNNNE.
Este script convierte el segundo pin «1» de cada uno en el pin «2» de un condensador SamacSys
sano (CL21A106KAYNNNE): base en X = 300 mil, mirando a la derecha, nombre y número «2».
El registro tiene el mismo tamaño, así que el archivo se edita en su sitio.

Uso (con Altium CERRADO):
    python docs/tools/reparar_pin2_condensadores.py "C:/Users/nico/Documents/AltiumLL/SamacSys.SchLib"
Guarda antes una copia SamacSys_antes_reparar.SchLib junto al archivo. Con --probar no escribe nada.
"""
import shutil
import sys
from pathlib import Path

import olefile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PIEZAS = ["C0805C102J5GAC-TU", "C0805C120J5GACTU", "C0805C472J5GACTU", "CL21B104KBCNNNC", "CL21B105KAFNNNE"]
SANA = "CL21A106KAYNNNE"


def pines(data):
    """Devuelve [(inicio_del_cuerpo, cuerpo)] de los pines binarios del stream Data."""
    i, out = 0, []
    while i + 4 <= len(data):
        ln = int.from_bytes(data[i:i + 2], "little")
        if data[i + 3] == 1:
            out.append((i + 4, data[i + 4:i + 4 + ln]))
        i += 4 + ln
    return out


def pin2_de_referencia(o):
    for _, cuerpo in pines(o.openstream(f"{SANA}/Data").read()):
        if b"\x012\x012" in cuerpo:  # nombre «2» y designador «2»
            return cuerpo
    raise SystemExit(f"No encontré el pin 2 de {SANA}")


def reparar(ruta, probar):
    if not probar:
        respaldo = Path(ruta).with_name("SamacSys_antes_reparar.SchLib")
        if not respaldo.exists():
            shutil.copy2(ruta, respaldo)
            print(f"copia de seguridad: {respaldo}")
    o = olefile.OleFileIO(ruta, write_mode=not probar)
    ref = pin2_de_referencia(o)
    for pieza in PIEZAS:
        data = bytearray(o.openstream(f"{pieza}/Data").read())
        ps = pines(data)
        unos = [(ini, c) for ini, c in ps if b"\x011\x011" in c]
        doses = [c for _, c in ps if b"\x012\x012" in c]
        if doses:
            print(f"{pieza}: ya tiene pin 2, no se toca")
            continue
        if len(unos) != 2 or len(unos[1][1]) != len(ref):
            print(f"{pieza}: forma inesperada ({len(unos)} pines «1»), no se toca")
            continue
        ini, _ = unos[1]
        data[ini:ini + len(ref)] = ref
        print(f"{pieza}: segundo pin «1» → pin «2» {'(prueba)' if probar else ''}")
        if not probar:
            o.write_stream(f"{pieza}/Data", bytes(data))
    o.close()


if __name__ == "__main__":
    reparar(sys.argv[1], "--probar" in sys.argv[2:])
