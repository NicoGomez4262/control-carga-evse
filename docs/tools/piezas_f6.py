# -*- coding: utf-8 -*-
"""Piezas de F6 en SamacSys.SchLib (Altium CERRADO). Copia de seguridad automática en docs/respaldos/.

1. AO3400A (Q3) copiado del MMBT3904LT1G: mismo SOT-23 y misma posición de pines (pad 1 B → G, 2 E → S,
   3 C → D, como el datasheet de AOS rev. 3.1). El dibujo del NPN se cambia por el de un MOSFET de canal N.
2. KT-0805Y (LED6, amarillo, LCSC C2296) copiado del APT2012SGC (0805, pad 1 = cátodo).
3. Parámetros de K1 (PhotoMOS AQY414EHAX, NC) cuando ya esté bajado de SamacSys (si no está, se salta).

Uso:  python docs/tools/piezas_f6.py ["C:/Users/nico/Documents/AltiumLL/SamacSys.SchLib"]
"""
import sys

import altium_ole as ao
import libreria as L
from piezas_f4 import pin_renombrado

RUTA = "C:/Users/nico/Documents/AltiumLL/SamacSys.SchLib"

COPIAS = [
    ("MMBT3904LT1G", "AO3400A", {
        "Manufacturer_Name": "Alpha & Omega Semiconductor", "Value": "NMOS 30V 5.7A", "Supplier": "PCBWay",
        "Supplier PN": "AO3400A", "Assembly": "PCBWay",
        "Description": "MOSFET N-channel 30V 5.7A, Rds(on) 48mR max at Vgs 2.5V, SOT-23",
        "Datasheet Link": "https://www.aosmd.com/res/datasheets/AO3400A.pdf"}),
    ("APT2012SGC", "KT-0805Y", {
        "Manufacturer_Name": "Hubei KENTO Elec", "Value": "amarillo", "Supplier": "PCBWay",
        "Supplier PN": "KT-0805Y", "Assembly": "PCBWay", "Description": "LED yellow 0805, 590 nm",
        "Datasheet Link": "https://www.lcsc.com/datasheet/C2296.pdf"}),
]

# pin: (nombre, tipo eléctrico 4 = pasivo)
PINES = {"AO3400A": {"1": ("G", 4), "2": ("S", 4), "3": ("D", 4)}}

# MOSFET de canal N dibujado en el mismo marco que el NPN (unidades de 10 mil): pines G (0,0) a la izquierda,
# D (40,30) arriba y S (40,-30) abajo; círculo con centro (35,0) como el del NPN.
LINEAS_MOSFET = [
    ((10, 0), (24, 0)),                                     # gate
    ((24, -10), (24, 10)),                                  # placa del gate
    ((28, 6), (28, 12)), ((28, -3), (28, 3)), ((28, -12), (28, -6)),  # canal de enriquecimiento (3 tramos)
    ((28, 9), (40, 9)), ((40, 9), (40, 20)),               # drain
    ((28, -9), (40, -9)), ((40, -9), (40, -20)),           # source
    ((28, 0), (40, 0)), ((40, 0), (40, -9)),               # sustrato unido al source
    ((29, 0), (33, 2)), ((33, 2), (33, -2)), ((33, -2), (29, 0)),  # flecha hacia el canal (canal N)
]

PONER = {
    # se completa después de bajarlo de SamacSys (nombre exacto de la pieza en la librería). K1 cambió del relé
    # Finder 34.51.7.012.5010 (no está en Mouser; con contactos dorados solo en TME, RS o Conrad) a este PhotoMOS.
    # J2 usa la TB001-500-02BE de J1 (ED1621 de Sigma), que ya tiene sus parámetros.
    # SamacSys la nombra «AQY-414EHAX»; el número de parte real de Panasonic va sin guion
    "AQY-414EHAX": {"Manufacturer_Name": "Panasonic", "Manufacturer_Part_Number": "AQY414EHAX",
                   "Value": "NC 400V 120mA", "Supplier": "Mouser",
                   "Supplier PN": "769-AQY414EHAX", "Assembly": "PCBWay", "Comment": "AQY414EHAX",
                   "Description": "PhotoMOS 1 Form B (NC), 400 V 120 mA, reinforced insulation 5000 Vrms, SMD DIP-4"},
}


def linea(p1, p2, uid):
    f = [("RECORD", "13"), ("OwnerPartId", "1")]
    for k, v in (("Location.X", p1[0]), ("Location.Y", p1[1]), ("Corner.X", p2[0]), ("Corner.Y", p2[1])):
        if v:  # Altium no escribe las coordenadas en cero
            f.append((k, str(v)))
    f += [("LineWidth", "1"), ("Color", "16711680"), ("UniqueID", uid)]
    return f


def dibujo_mosfet(regs, usados):
    """Cambia las líneas (13) del NPN por las del MOSFET; deja el círculo (12). Corrige OwnerIndex e IndexInSheet."""
    graf = [n for n, (t, c) in enumerate(regs) if t == 0 and ao.valor(ao.campos(c), "RECORD") == "13"]
    if not graf:
        raise SystemExit("AO3400A: no hay líneas que cambiar")
    ini, fin = graf[0], graf[-1] + 1
    if fin - ini != len(graf):
        raise SystemExit("AO3400A: las líneas del dibujo no están juntas")
    nuevas = [(0, ao.cuerpo(linea(a, b, ao.uid(usados)))) for a, b in LINEAS_MOSFET]
    out = regs[:ini] + nuevas + regs[fin:]
    corr = len(nuevas) - (fin - ini)
    for n, (t, c) in enumerate(out):
        if t != 0:
            continue
        f = ao.campos(c)
        oi = ao.valor(f, "OwnerIndex")
        if oi is not None and int(oi) >= fin:
            f = ao.poner(f, "OwnerIndex", str(int(oi) + corr))
        idx = ao.valor(f, "IndexInSheet")
        if n >= ini and (idx is None or int(idx) >= 0) and ao.valor(f, "RECORD") in ("13", "12", "41"):
            # índice = posición - 1, como en el resto de la pieza (los -1 de Designator y Comment no cambian)
            f = ao.poner(f, "IndexInSheet", str(n - 1), antes_de="OwnerPartId")
        out[n] = (0, ao.cuerpo(f))
    return out


def ajustar_ao3400a(ruta):
    ps = L.piezas(ruta)
    regs = list(ps["AO3400A"]["regs"])
    lineas = [ao.campos(c) for t, c in regs if t == 0 and ao.valor(ao.campos(c), "RECORD") == "13"]
    if len(lineas) == len(LINEAS_MOSFET):
        print("AO3400A: el dibujo de MOSFET ya estaba")
        return
    for n, (t, c) in enumerate(regs):
        if t == 1:
            nombre, el = PINES["AO3400A"][ao.pin_binario(c)["designador"]]
            regs[n] = (1, pin_renombrado(c, nombre, el))
    regs = dibujo_mosfet(regs, L.usados_en(ps))
    comp = ao.poner(ao.campos(regs[0][1]), "ComponentDescription", COPIAS[0][2]["Description"])
    regs[0] = (0, ao.cuerpo(comp))
    L.guardar_piezas(ruta, {ps["AO3400A"]["stream"]: ao.unir_registros(regs)})
    print(f"AO3400A: pines G/S/D y dibujo de MOSFET de canal N ({len(LINEAS_MOSFET)} líneas)")


if __name__ == "__main__":
    ruta = sys.argv[1] if len(sys.argv) > 1 else RUTA
    existentes = L.piezas(ruta)
    for origen, nueva, params in COPIAS:
        if nueva in existentes:
            print(f"{nueva}: ya existe, no se copia")
            continue
        L.copiar(ruta, origen, nueva, params)
    ajustar_ao3400a(ruta)
    existentes = L.piezas(ruta)
    lote = {p: c for p, c in PONER.items() if p in existentes}
    for p in PONER:
        if p not in existentes:
            print(f"{p}: todavía no está en la librería (bajarlo de SamacSys); se salta")
    if lote:
        L.poner_lote(ruta, lote)
