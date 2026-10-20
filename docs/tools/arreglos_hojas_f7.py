# -*- coding: utf-8 -*-
"""Arreglos de las hojas en F7 (14 oct 2026, Altium CERRADO). Se corre después de libreria_f7.py.

Todas las hojas:
- Bloque de título: Title de cada hoja; Address1 = curso, Address2–4 vacíos (mostraban «*»); el texto
  de la plantilla «PROPERTY OF ALTIUM LIMITED…» pasa a datos del proyecto; se quita el logo de Altium
  (tapaba el nombre del proyecto).
- Modelos de footprint: de Documents/AltiumLL/SamacSys.PcbLib a lib/SamacSys.PcbLib.
- Y1, FB1, D1 y D2: sin el «Mouser Part Number» que SamacSys copió de otra pieza.
01_TOP: nota de rieles (+3V3 ya no va a ACTUACION) y línea con las clases de red.
02_ALIMENTACION: F1B/F2B → BLX-A (footprint BLX-A_5X20 y parámetros de la librería).
03_MEDICION: las dos Blankets ANALOG se agrandan 100 mil (ATM_VN y CT_P quedaban en el borde).
04_MCU: clase de red USB (Blanket + Parameter Set sobre USB_DP/USB_DN junto a U5).
05/06: J4, U6 y K1 con SourceLibraryName = SamacSys.SchLib (estaban en «*»).
templates/EVSE_A3.SchDoc: el mismo texto de plantilla y sin logo (para hojas nuevas).

Uso: python docs/tools/arreglos_hojas_f7.py [--probar <carpeta> <SamacSys.SchLib de prueba>]
"""
import shutil
import sys
from pathlib import Path

import altium_ole as ao
import libreria as L
from hoja import Hoja
from ronda2_f4 import params_lib, sincronizar

PROY = Path("C:/Nicolas/UNIVERSIDAD - 2026/Hardware en IoT/Control de Carga IoT/Control de Carga IoT")
PCBLIB_TXT = str(PROY / "lib" / "SamacSys.PcbLib").replace("/", "\\")
HOJAS = ["01_TOP", "02_ALIMENTACION", "03_MEDICION", "04_MCU", "05_SENSORES", "06_ACTUACION"]

TITULOS = {
    "01_TOP": "Diagrama de bloques (hoja TOP)",
    "02_ALIMENTACION": "Alimentación: red, 12 V y 3,3 V",  # acortado en presentacion_f7.py
    "03_MEDICION": "Medición de tensión y corriente",
    "04_MCU": "ESP32-S3, USB y programación",
    "05_SENSORES": "Sensores, RTC y sonda 1-Wire",
    "06_ACTUACION": "Actuación: PhotoMOS K1 al EVSE",
}
DIRECCION = {"Address1": "Hardware en IoT · 2026", "Address2": " ", "Address3": " ", "Address4": " "}
PLANTILLA = {
    "THIS DOCUMENT AND THE DATA DISCLOSED HEREIN OR": "CONTROL DE CARGA EVSE · HARDWARE EN IOT 2026",
    "HEREWITH IS THE PROPERTY OF ALTIUM LIMITED AND MAY": "DISEÑO: NICOLÁS GÓMEZ RAMÍREZ",
    "BE FREELY DISTRIBUTED IN WHOLE. NO RIGHTS ARE": "ZONA DE RED 120–240 VAC CON AISLAMIENTO REFORZADO",
    "RESERVED OR EXPRESS OR IMPLIED WARANTEE GIVEN.": "USO ACADÉMICO, SIN GARANTÍA.",
}
NOTA_TOP = ("Rieles (puertos de alimentación globales, sin entradas de hoja):~1"
            "+VIN (12 V): ALIMENTACION → ACTUACION~1"
            "+3V3: ALIMENTACION → MEDICION, MCU, SENSORES~1"
            "+3V3A: ALIMENTACION → MEDICION   ·   GND: todas las hojas SELV~1"
            "AC_L1_F / AC_L2_F = red 120–240 VAC (clase HV_AC). En 120 V, AC_L2_F es el neutro.~1"
            "Clases de red: HV_AC (red), ANALOG (medición), EVSE_EXT (J2 al EVSE), USB (USB_DP/USB_DN).~1")
MOUSER_AJENO = ["ECS-81.92-12-30Q-EN-TR", "BLM21PG221SN1D", "SS34-E3_57T"]
# 03: (vértices viejos → nuevos) en mil
BLANKETS_03 = [
    ([(400, 6700), (5700, 6700), (5700, 6200), (3400, 6200), (3400, 5300), (5400, 5300), (5400, 4900), (400, 4900)],
     [(400, 6700), (5700, 6700), (5700, 6200), (3400, 6200), (3400, 5300), (5400, 5300), (5400, 4800), (400, 4800)]),
    ([(6100, 6300), (11000, 6300), (11000, 5800), (7600, 5800), (7600, 4800), (11000, 4800), (11000, 4300), (6100, 4300)],
     [(6100, 6400), (11000, 6400), (11000, 5800), (7600, 5800), (7600, 4800), (11000, 4800), (11000, 4300), (6100, 4300)]),
]
USB_BLANKET = [(2450, 5350), (2950, 5350), (2950, 5550), (2450, 5550)]
USB_DIRECTIVA = (2450, 5350)   # esquina inferior izquierda, banderín hacia abajo (arriba está el +3V3 de V3)


def texto(h, i, clave, valor):
    """Texto con su copia %UTF8% cuando tiene caracteres fuera de ASCII (Altium lee primero la copia)."""
    h.poner(i, **{clave: valor.encode("cp1252", "replace").decode("latin-1")})
    if any(ord(ch) > 127 for ch in valor):
        h.poner(i, **{"%UTF8%" + clave: valor.encode("utf-8").decode("latin-1")})


def comp(h, desig):
    for i in h.buscar(RECORD="1"):
        if any(h.v(j, "RECORD") == "34" and h.v(j, "Text") == desig for j in h.hijos(i)):
            return i
    raise SystemExit(f"{desig} no está en la hoja")


def desig(h, c):
    return next((h.v(j, "Text") for j in h.hijos(c) if h.v(j, "RECORD") == "34"), "?")


def plantilla(h):
    for i in h.buscar(RECORD="4"):
        t = h.v(i, "Text")
        if t in PLANTILLA:
            texto(h, i, "Text", PLANTILLA[t])
            h._nota(i, f"plantilla: «{t}» → «{PLANTILLA[t]}»")
    for i in sorted(h.buscar(RECORD="30"), reverse=True):
        if "Altium Logo" in (h.v(i, "FileName") or ""):
            h.borrar(i)
            h._nota(i, "logo de Altium borrado")


def comun(h, nombre):
    plantilla(h)
    for i in h.buscar(RECORD="41"):
        if h.v(i, "OwnerIndex") is not None:
            continue
        n = h.v(i, "Name")
        if n == "Title":
            texto(h, i, "Text", TITULOS[nombre])
            h._nota(i, f"Title = «{TITULOS[nombre]}»")
        elif n in DIRECCION:
            texto(h, i, "Text", DIRECCION[n])
    for i in h.buscar(RECORD="45"):
        if "AltiumLL" in (h.v(i, "ModelDatafile0") or ""):
            h.poner(i, ModelDatafile0=PCBLIB_TXT)
    n_mod = sum(1 for i in h.buscar(RECORD="45") if h.v(i, "ModelDatafile0") == PCBLIB_TXT)
    if n_mod:
        h._nota(0, f"{n_mod} modelos de footprint → lib\\SamacSys.PcbLib")
    borrar = []
    for c in h.buscar(RECORD="1"):
        if h.v(c, "LibReference") in MOUSER_AJENO:
            for j in h.hijos(c):
                if h.v(j, "Name") in ("Mouser Part Number", "Mouser Price/Stock"):
                    borrar.append(j)
            h._nota(c, f"{desig(h, c)}: sin el Mouser Part Number de otra pieza")
    for j in sorted(borrar, reverse=True):
        h.borrar(j)


def hoja_01(h):
    for i in h.buscar(RECORD="28"):
        if (h.v(i, "Text") or "").startswith("Rieles"):
            texto(h, i, "Text", NOTA_TOP)
            h._nota(i, "nota de rieles: +3V3 sin ACTUACION; línea de clases de red")


def hoja_02(h, lib_sch):
    ps = L.piezas(lib_sch)
    pl = params_lib(ps, "BLX-A")
    desc = ao.valor(L.resumen(ps["BLX-A"]["regs"])[0], "ComponentDescription")
    usados = h.uids()
    for d in ("F1B", "F2B"):
        uid = h.v(comp(h, d), "UniqueID")
        c = h.por_uid(uid)
        h.poner(c, LibReference="BLX-A", DesignItemId="BLX-A")
        texto(h, c, "ComponentDescription", desc)
        sincronizar(h, c, pl, usados, borrar_resto=True)
        c = h.por_uid(uid)
        com = next(j for j in h.hijos(c) if h.v(j, "Name") == "Comment")
        h.poner(com, Text="BLX-A")
        for lst in h.hijos(c):
            if h.v(lst, "RECORD") == "44":
                for m in h.hijos(lst):
                    if h.v(m, "RECORD") == "45":
                        h.poner(m, ModelName="BLX-A_5X20", ModelDatafileEntity0="BLX-A_5X20",
                                ModelDatafile0=PCBLIB_TXT)
        h._nota(c, f"{d}: 01000056Z → BLX-A (footprint BLX-A_5X20, XC Electronics, Sigma BLX-A, DNP)")


def poner_poligono(f, pts):
    f = [(k, v) for k, v in f if not (k[:1] in "XY" and k[1:].split("_")[0].isdigit())]
    pos = next(n for n, (k, _) in enumerate(f) if k == "LocationCount")
    f[pos] = ("LocationCount", str(len(pts)))
    nuevos = []
    for n, (x, y) in enumerate(pts, 1):
        nuevos += [(f"X{n}", str(x // 10)), (f"Y{n}", str(y // 10))]
    f = f[:pos + 1] + nuevos + f[pos + 1:]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    for k, v in (("Location.X", min(xs)), ("Location.Y", min(ys)), ("Corner.X", max(xs)), ("Corner.Y", max(ys))):
        f = ao.quitar(f, k + "_Frac")
        f = ao.poner(f, k, str(v // 10))
    return f


def hoja_03(h):
    h.leer_adicional()
    hechos = 0
    for k, f in enumerate(h.ad):
        if ao.valor(f, "RECORD") != "225":
            continue
        n = int(ao.valor(f, "LocationCount", 0))
        pts = [(Hoja.mil(f, f"X{j}"), Hoja.mil(f, f"Y{j}")) for j in range(1, n + 1)]
        for viejo, nuevo in BLANKETS_03:
            if pts == [(float(x), float(y)) for x, y in viejo]:
                h.ad[k] = poner_poligono(f, nuevo)
                hechos += 1
                h._nota(k, f"Blanket ANALOG {viejo[0]}… agrandada 100 mil")
    if hechos != 2:
        raise SystemExit(f"03: se esperaban 2 Blankets ANALOG y se encontraron {hechos}")


def hoja_04(h):
    h.leer_adicional()
    usados = h.uids() | {ao.valor(f, "UniqueID") for f in h.ad}
    n = max(h.max_index_in_sheet(), *[int(ao.valor(f, "IndexInSheet", 0) or 0) for f in h.ad] or [0]) + 1
    pts = USB_BLANKET
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    b = [("RECORD", "225"), ("IndexInSheet", str(n)), ("OwnerPartId", "-1"),
         ("Location.X", str(min(xs) // 10)), ("Location.Y", str(min(ys) // 10)),
         ("Corner.X", str(max(xs) // 10)), ("Corner.Y", str(max(ys) // 10)),
         ("Color", "33023"), ("AreaColor", "16777215"), ("LineStyle", "1"), ("LocationCount", str(len(pts)))]
    for k, (x, y) in enumerate(pts, 1):
        b += [(f"X{k}", str(x // 10)), (f"Y{k}", str(y // 10))]
    b += [("LineStyleExt", "1"), ("UniqueID", ao.uid(usados))]
    h.ad.append(b)
    fx, fy = USB_DIRECTIVA
    d = [("RECORD", "43"), ("IndexInSheet", str(n + 1)), ("OwnerPartId", "-1"), ("Location.X", str(fx // 10)),
         ("Location.Y", str(fy // 10)), ("Color", "255"), ("Orientation", "3"), ("Name", "Parameter Set"),
         ("UniqueID", ao.uid(usados))]
    idir = h.agregar(d)
    h.agregar([("RECORD", "41"), ("OwnerIndex", str(idir)), ("OwnerPartId", "-1"),
               ("Location.X", str(fx // 10 + 5)), ("Location.Y", str(fy // 10 - 12)), ("Color", "8388608"),
               ("FontID", "1"), ("IsHidden", "T"), ("Text", "USB"), ("Name", "ClassName"),
               ("UniqueID", ao.uid(usados))])
    h._nota(idir, f"clase USB: Blanket {pts[0]}–{pts[2]} y Parameter Set en {USB_DIRECTIVA}")


def libreria_origen(h, desigs):
    for d in desigs:
        c = comp(h, d)
        if h.v(c, "SourceLibraryName") != "SamacSys.SchLib":
            h.poner(c, SourceLibraryName="SamacSys.SchLib")
            h._nota(c, f"{d}: SourceLibraryName «*» → SamacSys.SchLib")


def main(carpeta, lib_sch, probar):
    if ao.altium_abierto():
        raise SystemExit("Altium está abierto: ciérralo antes de correr el script.")
    for nombre in HOJAS:
        h = Hoja(str(carpeta / f"{nombre}.SchDoc"))
        comun(h, nombre)
        if nombre == "01_TOP":
            hoja_01(h)
        elif nombre == "02_ALIMENTACION":
            hoja_02(h, lib_sch)
        elif nombre == "03_MEDICION":
            hoja_03(h)
        elif nombre == "04_MCU":
            hoja_04(h)
        elif nombre == "05_SENSORES":
            libreria_origen(h, ["J4", "U6"])
        elif nombre == "06_ACTUACION":
            libreria_origen(h, ["K1"])
        copia = h.guardar("antes_f7") if not probar else (ao.escribir_streams(h.ruta, dict(
            {"FileHeader": h.datos()}, **({"Additional": h.datos_adicional()} if hasattr(h, "ad") else {}))) or "—")
        print(f"== {nombre} (respaldo: {copia})")
        for x in h.cambios:
            print("  ", x)
    t = Hoja(str(carpeta / "templates" / "EVSE_A3.SchDoc"))
    plantilla(t)
    copia = t.guardar("antes_f7") if not probar else ao.escribir_streams(t.ruta, {"FileHeader": t.datos()})
    print(f"== templates/EVSE_A3.SchDoc (respaldo: {copia})")
    for x in t.cambios:
        print("  ", x)


if __name__ == "__main__":
    a = sys.argv[1:]
    if "--probar" in a:
        destino = Path(a[a.index("--probar") + 1])
        (destino / "templates").mkdir(parents=True, exist_ok=True)
        for n in HOJAS:
            shutil.copy2(PROY / f"{n}.SchDoc", destino / f"{n}.SchDoc")
        shutil.copy2(PROY / "templates" / "EVSE_A3.SchDoc", destino / "templates" / "EVSE_A3.SchDoc")
        main(destino, a[a.index("--probar") + 2], True)
    else:
        main(PROY, str(PROY / "lib" / "SamacSys.SchLib"), False)
