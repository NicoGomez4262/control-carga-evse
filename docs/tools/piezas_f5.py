# -*- coding: utf-8 -*-
"""Piezas de F5 en SamacSys.SchLib (Altium CERRADO). Copia de seguridad automática en docs/respaldos/.

1. Copias del mismo encapsulado (solo cambian los parámetros):
   RC0805FR-07100RL y RC0805FR-07330RL (desde RC0805FR-0710KL), RC1206FR-0768RL (desde ERJ-P08F1004V).
2. ICs del mismo encapsulado con los pines renombrados (como el CH340C de F4):
   FM24CL64B-GTR desde LM334SMX_NOPB (SOIC-8 de 3,9 mm, paso 1,27; pinout del datasheet de Infineon, rev. *K)
   DS3231SN desde AMC3330DWE (SOIC-16 de 7,5 mm / MS-013, paso 1,27; pines del datasheet 19-5170 rev. 10).
3. Parámetros del portapila BAT-HLD-001 (ya estaba en la librería).

Uso:  python docs/tools/piezas_f5.py ["C:/Users/nico/Documents/AltiumLL/SamacSys.SchLib"]
"""
import sys

import altium_ole as ao
import libreria as L
from piezas_f4 import pin_renombrado

RUTA = "C:/Users/nico/Documents/AltiumLL/SamacSys.SchLib"
RES = {"Manufacturer_Name": "YAGEO", "Supplier": "PCBWay", "Assembly": "PCBWay", "Description": "Resistor"}

COPIAS = [
    ("RC0805FR-0710KL", "RC0805FR-07100RL", dict(RES, Value="100R")),
    ("RC0805FR-0710KL", "RC0805FR-07330RL", dict(RES, Value="330R")),
    ("ERJ-P08F1004V", "RC1206FR-0768RL", dict(RES, Value="68R 1206")),
    ("LM334SMX_NOPB", "FM24CL64B-GTR", {
        "Manufacturer_Name": "Infineon", "Value": "FRAM 8KB I2C", "Supplier": "PCBWay", "Assembly": "PCBWay",
        "Description": "64-Kbit (8K x 8) I2C F-RAM, 1 MHz, SOIC-8",
        "Datasheet Link": "https://www.lcsc.com/datasheet/C9829.pdf", "Height": "1.75mm"}),
    ("AMC3330DWE", "DS3231SN", {
        "Manufacturer_Name": "Analog Devices", "Manufacturer_Part_Number": "DS3231SN#",
        "Value": "RTC TCXO 2ppm", "Supplier": "PCBWay", "Supplier PN": "DS3231SN#T&R", "Assembly": "PCBWay",
        "Description": "I2C RTC with integrated TCXO and crystal, VBAT, SO-16W",
        "Datasheet Link": "https://www.analog.com/media/en/technical-documentation/data-sheets/DS3231.pdf",
        "Height": "2.65mm"}),
]

# pin: (nombre, tipo eléctrico)  0 entrada, 1 E/S, 3 colector abierto, 4 pasivo, 7 alimentación
PINES = {
    "FM24CL64B-GTR": {"1": ("A0", 0), "2": ("A1", 0), "3": ("A2", 0), "4": ("VSS", 7),
                      "5": ("SDA", 1), "6": ("SCL", 0), "7": ("WP", 0), "8": ("VDD", 7)},
    "DS3231SN": dict({"1": ("32kHz", 3), "2": ("VCC", 7), "3": ("I\\N\\T\\/SQW", 3), "4": ("R\\S\\T\\", 3),
                      "13": ("GND", 7), "14": ("VBAT", 7), "15": ("SDA", 1), "16": ("SCL", 0)},
                     **{str(n): ("N.C.", 4) for n in range(5, 13)}),  # 5–12: el datasheet pide unirlos a GND
}

PONER = {
    "BAT-HLD-001": {"Value": "CR2032", "Supplier": "PCBWay", "Supplier PN": "BAT-HLD-001", "Assembly": "PCBWay",
                    "Description": "Battery holder CR2032, SMD"},
    # bajadas de SamacSys el 12 oct: el AHT20 venía rotulado «Adafruit» (breakout) pero símbolo y footprint son del
    # chip DFN-6 de 3 x 3 mm (pads en ±1,0 mm, paso 1,0; pines 1 NC, 2 VDD, 3 SCL, 4 SDA, 5 GND, 6 NC)
    "AHT20": {"Manufacturer_Name": "Aosong", "Value": "T/HR I2C 0x38", "Supplier": "PCBWay", "Supplier PN": "AHT20",
              "Assembly": "PCBWay", "Comment": "AHT20",
              "Description": "Temperature and humidity sensor, I2C 0x38, DFN-6 3x3 mm",
              "Datasheet Link": "https://www.lcsc.com/datasheet/C2757850.pdf"},
    "1751251": {"Value": "3P 3.5mm", "Supplier": "Sigma", "Supplier PN": "BORNE 3.5MM 3P V", "Assembly": "Manual",
                "Comment": "1751251"},
}


def renombrar_pines(ruta, pieza, tabla):
    ps = L.piezas(ruta)
    regs = list(ps[pieza]["regs"])
    hechos = 0
    for n, (t, c) in enumerate(regs):
        if t == 1:
            d = ao.pin_binario(c)["designador"]
            nombre, el = tabla[d]
            regs[n] = (1, pin_renombrado(c, nombre, el))
            hechos += 1
    if hechos != len(tabla):
        raise SystemExit(f"{pieza}: {hechos} pines en el símbolo y {len(tabla)} en la tabla")
    if regs == list(ps[pieza]["regs"]):
        print(f"{pieza}: los pines ya estaban renombrados")
        return
    L.guardar_piezas(ruta, {ps[pieza]["stream"]: ao.unir_registros(regs)})
    print(f"{pieza}: {hechos} pines renombrados")


if __name__ == "__main__":
    ruta = sys.argv[1] if len(sys.argv) > 1 else RUTA
    existentes = L.piezas(ruta)
    for origen, nueva, params in COPIAS:
        if nueva in existentes:
            print(f"{nueva}: ya existe, no se copia")
            continue
        L.copiar(ruta, origen, nueva, params)
    for pieza, tabla in PINES.items():
        renombrar_pines(ruta, pieza, tabla)
    L.poner_lote(ruta, PONER)
