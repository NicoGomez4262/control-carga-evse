# -*- coding: utf-8 -*-
"""Correcciones de parámetros de SamacSys.SchLib hechas al inicio de F4 (pendiente A2 y limpieza).

- A2: ATM90E26-YU-R decía Manufacturer_Name = «PCBWay».
- Piezas creadas copiando otra (pedido F3/F4): conservaban Datasheet Link, Mouser y Arrow de la pieza
  original. Se corrigen cuando el dato sale del mismo patrón que ya usaba SamacSys (KEMET specsheet,
  Mouser 603- de Yageo) y se dejan vacíos cuando no se conoce el correcto.

Uso (Altium CERRADO):  python docs/tools/corregir_libreria_f4.py "C:/Users/nico/Documents/AltiumLL/SamacSys.SchLib"
"""
import sys

import libreria as L

VACIO_DISTRIBUIDOR = {"Mouser Part Number": "", "Mouser Price/Stock": "", "Arrow Price/Stock": ""}


def kemet(pn):
    return {"Datasheet Link": f"https://www.kemet.com/specsheet/{pn}", "Arrow Part Number": pn, **VACIO_DISTRIBUIDOR}


def sin_datos(pn, **extra):
    return {"Datasheet Link": "", "Arrow Part Number": pn, **VACIO_DISTRIBUIDOR, **extra}


def yageo(pn):
    return {"Mouser Part Number": f"603-{pn}", "Mouser Price/Stock": "", "Arrow Part Number": pn,
            "Arrow Price/Stock": ""}


LOTE = {
    "ATM90E26-YU-R": {"Manufacturer_Name": "Microchip"},
    "C0805C120J5GACTU": kemet("C0805C120J5GACTU"),
    "C0805C472J5GACTU": kemet("C0805C472J5GACTU"),
    "C1206C333J5GACTU": kemet("C1206C333J5GACTU"),
    "CL21B104KBCNNNC": sin_datos("CL21B104KBCNNNC"),
    "CL21B105KAFNNNE": sin_datos("CL21B105KAFNNNE"),
    "C3216NP01H104J160AA": sin_datos("C3216NP01H104J160AA", Height="1.6mm"),
    "ERA-6AEB103V": sin_datos("ERA-6AEB103V"),
    "ERA-6AEB133V": sin_datos("ERA-6AEB133V"),
    "ERA-6AEB203V": sin_datos("ERA-6AEB203V"),
    "ERA-6AHD100V": sin_datos("ERA-6AHD100V"),
    "RC0805FR-0710KL": yageo("RC0805FR-0710KL"),
    "RC0805FR-0747KL": yageo("RC0805FR-0747KL"),
    "IRM-20-12": {"Datasheet Link": "https://www.meanwell.com/Upload/PDF/IRM-20/IRM-20-SPEC.PDF"},
}

if __name__ == "__main__":
    L.poner_lote(sys.argv[1], LOTE)
