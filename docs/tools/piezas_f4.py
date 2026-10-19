# -*- coding: utf-8 -*-
"""Piezas de F4 en SamacSys.SchLib (Altium CERRADO).

1. Completa Supplier, Supplier PN, Assembly, Value y Comment de las piezas bajadas de SamacSys.
2. Crea el CH340C copiando el SN74HC595DR (mismo SOIC-16 de 3,9 mm y paso de 1,27 mm) y le pone
   los nombres y tipos eléctricos de sus 16 pines según el datasheet de WCH (V3C, tabla 4).

Uso:  python docs/tools/piezas_f4.py "C:/Users/nico/Documents/AltiumLL/SamacSys.SchLib"
"""
import sys

import altium_ole as ao
import libreria as L

LOTE = {
    "ESP32-S3-WROOM-1-N16R2": {"Value": "N16R2 16MB/2MB", "Supplier": "Mouser", "Supplier PN": "356-ESP32S3WRM1N16R2",
                               "Assembly": "PCBWay", "Comment": "ESP32-S3-WROOM-1-N16R2"},
    "USBLC6-2SC6": {"Value": "ESD USB", "Supplier": "PCBWay", "Supplier PN": "USBLC6-2SC6", "Assembly": "PCBWay",
                    "Comment": "USBLC6-2SC6"},
    "MMBT3904LT1G": {"Value": "NPN 40V 0.2A", "Supplier": "PCBWay", "Supplier PN": "MMBT3904LT1G", "Assembly": "PCBWay",
                     "Comment": "MMBT3904LT1G"},
    "TS-1187A-B-A-B": {"Value": "pulsador 5.1mm", "Supplier": "PCBWay", "Supplier PN": "TS-1187A-B-A-B",
                       "Assembly": "PCBWay", "Comment": "TS-1187A-B-A-B",
                       "Description": "Tact switch 5.1 x 5.1 x 1.5 mm, 160 gf, 50 mA 12 VDC"},
    "61300611121": {"Value": "1x6 2.54mm", "Supplier": "Sigma", "Supplier PN": "REGLETA 40 X 1", "Assembly": "Manual",
                    "Comment": "61300611121"},
}

# pin: (nombre, tipo eléctrico)  0 entrada, 1 E/S, 2 salida, 4 pasivo, 7 alimentación
CH340C = {"1": ("GND", 7), "2": ("TXD", 2), "3": ("RXD", 0), "4": ("V3", 7), "5": ("UD+", 1), "6": ("UD-", 1),
          "7": ("NC", 4), "8": ("O\\U\\T\\", 2), "9": ("C\\T\\S\\", 0), "10": ("D\\S\\R\\", 0), "11": ("R\\I\\", 0),
          "12": ("D\\C\\D\\", 0), "13": ("D\\T\\R\\", 2), "14": ("R\\T\\S\\", 2), "15": ("R232", 0), "16": ("VCC", 7)}
PARAMS_CH340C = {"Manufacturer_Name": "WCH", "Value": "USB-UART", "Supplier": "PCBWay", "Supplier PN": "CH340C",
                 "Assembly": "PCBWay", "Description": "USB to UART bridge, DTR/RTS, internal clock, SOP-16",
                 "Datasheet Link": "https://www.wch-ic.com/downloads/CH340DS1_PDF.html", "Height": "1.75mm"}


def pin_renombrado(c, nombre, electrico):
    """Reescribe nombre y tipo eléctrico de un pin binario de SchLib (el resto queda igual)."""
    i = 12 + 1 + c[12]                       # después de la descripción
    out = bytearray(c[:i])
    out += bytes([c[i], electrico, c[i + 2]])  # tipo formal, eléctrico, conglomerado
    j = i + 3 + 10                            # largo, x, y, color
    out += c[i + 3:j]
    n_viejo = c[j]
    nb = nombre.encode("latin-1")
    out += bytes([len(nb)]) + nb
    out += c[j + 1 + n_viejo:]                # designador, swap, parte, valor por defecto
    return bytes(out)


def crear_ch340c(ruta):
    ps = L.piezas(ruta)
    if "CH340C" not in ps:
        L.copiar(ruta, "SN74HC595DR", "CH340C", PARAMS_CH340C)
        ps = L.piezas(ruta)
    regs = list(ps["CH340C"]["regs"])
    for n, (t, c) in enumerate(regs):
        if t == 1:
            d = ao.pin_binario(c)["designador"]
            nombre, el = CH340C[d]
            regs[n] = (1, pin_renombrado(c, nombre, el))
        elif t == 0:
            f = ao.campos(c)
            if ao.valor(f, "RECORD") == "1":
                f = ao.poner(f, "ComponentDescription", "USB to UART bridge")
                regs[n] = (0, ao.cuerpo(f))
    L.guardar_piezas(ruta, {ps["CH340C"]["stream"]: ao.unir_registros(regs)})
    print("CH340C: 16 pines renombrados")


if __name__ == "__main__":
    ruta = sys.argv[1]
    L.poner_lote(ruta, LOTE)
    crear_ch340c(ruta)
