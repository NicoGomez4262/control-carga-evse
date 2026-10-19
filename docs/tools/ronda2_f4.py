# -*- coding: utf-8 -*-
"""Segunda ronda de arreglos de F4 (Altium CERRADO), después del primer dibujo de 04_MCU.

Hallazgos que corrige:
- Los Blankets van en el stream «Additional» del .SchDoc (lo mostró la muestra dibujada en Altium el
  12 oct), no en «FileHeader». Se crean los 3 de 03_MEDICION ahí y sus Parameter Set en FileHeader.
- «Weight» de la cabecera = número de registros: Hoja.datos() ya lo actualiza (02 y 03 quedaron
  desfasados por los parámetros de los TP agregados el 11 oct).
- 04_MCU: se borra la muestra (Blanket + Parameter Set); LED_PARAR → BTN_PARAR; designadores según los
  esquemas F4; R21 de 47 kΩ → 4,7 kΩ; parámetros de U4, Q1, Q2 y J8 desde la librería; SW2/SW3 DNP;
  pulsadores: los pines B1 y C1 se intercambian de lugar (ver nota).
- SamacSys.SchLib: el TS-1187A-B-A-B queda con A1/B1 (COM, unidos por dentro) a la izquierda y C1/D1 (NO)
  a la derecha, para que cada lado del símbolo sea un solo terminal.

Nota de los pulsadores: en el símbolo de SamacSys A1 (COM_1) y C1 (NO_1) están a la izquierda y B1 (COM_2)
y D1 (NO_2) a la derecha. A1-B1 y C1-D1 están unidos dentro del pulsador, así que el cableado «izquierda a
GND, derecha a la red» dejaba la red en corto con GND (EN siempre en 0). Al intercambiar B1 y C1, ese mismo
cableado queda correcto: COM a GND y NO a la red.

Uso: python docs/tools/ronda2_f4.py "<carpeta del proyecto>" "<SamacSys.SchLib>" [--probar <carpeta>]
"""
import shutil
import sys
from pathlib import Path

import altium_ole as ao
import libreria as L
import pendientes_f3 as pf
from hoja import Hoja

DESIG = {"Z297": "J8", "Z327": "U5", "Z375": "C36", "Z406": "LED3", "Z443": "LED5", "Z474": "J7", "Z537": "C33",
         "Z564": "C34", "Z597": "R22", "Z621": "C32", "Z656": "SW3", "Z684": "SW2", "Z718": "R19", "Z736": "Q2",
         "Z768": "R20", "Z786": "Q1", "Z820": "R21", "Z863": "R26", "Z887": "R25", "Z914": "C35", "Z946": "R28",
         "Z970": "R29", "Z994": "R30", "Z1018": "LED4", "Z1062": "R27", "Z1087": "SW1", "Z1117": "R31"}


# ---------------------------------------------------------------- utilidades
def params_lib(ps, nombre):
    comp, params, _, _ = L.resumen(ps[nombre]["regs"])
    params = dict(params)
    params.pop("Comment", None)
    return params


def sincronizar(h, c, params, usados, borrar_resto=False):
    """Pone en el componente c (hoja) los parámetros de la librería; agrega los que falten."""
    hijos = h.hijos(c)
    p41 = {h.v(j, "Name"): j for j in hijos if h.v(j, "RECORD") == "41"}
    for n, v in params.items():
        if n in p41:
            h.poner(p41[n], Text=v if v else None)
    faltan = [(n, v) for n, v in params.items() if n not in p41 and v]
    ocultos = [j for j in hijos if h.v(j, "RECORD") == "41" and h.v(j, "IsHidden") == "T"]
    base = max(ocultos) if ocultos else max(hijos)
    pos = base + 1
    x, y = h.v(base, "Location.X") or "0", h.v(base, "Location.Y") or "0"
    for n, v in faltan:
        f = [("RECORD", "41"), ("OwnerIndex", str(c)), ("OwnerPartId", "-1"), ("Location.X", x), ("Location.Y", y),
             ("Color", "8388608"), ("FontID", "1"), ("IsHidden", "T"), ("Text", v), ("Name", n),
             ("UniqueID", ao.uid(usados))]
        h.insertar(pos, f)
        pos += 1
    if borrar_resto:
        for j in sorted([j for j in h.hijos(c) if h.v(j, "RECORD") == "41" and h.v(j, "Name") not in params
                         and h.v(j, "Name") != "Comment"], reverse=True):
            h.borrar(j)


def desig_de(h, c):
    return next((j for j in h.hijos(c) if h.v(j, "RECORD") == "34"), None)


def intercambiar_pines_hoja(h, c, a="B1", b="C1"):
    pins = {h.v(j, "Designator"): j for j in h.hijos(c) if h.v(j, "RECORD") == "2"}
    ja, jb = pins[a], pins[b]
    claves = ["Location.X", "Location.X_Frac", "Location.Y", "Location.Y_Frac", "PinConglomerate"]
    va = {k: h.v(ja, k) for k in claves}
    vb = {k: h.v(jb, k) for k in claves}
    for j, nuevos in ((ja, vb), (jb, va)):
        f = h.r[j]
        for k, v in nuevos.items():
            f = ao.quitar(f, k) if v is None else ao.poner(f, k, v, antes_de="Name")
        h.r[j] = f


def intercambiar_pines_lib(regs, a="B1", b="C1"):
    """Intercambia posición y orientación de dos pines binarios de una SchLib."""
    regs = list(regs)
    idx = {}
    for n, (t, c) in enumerate(regs):
        if t == 1:
            idx[ao.pin_binario(c)["designador"]] = n

    def campos_pos(c):
        i = 12 + 1 + c[12]
        return i + 2, c[i + 2], c[i + 5:i + 9]  # offset del conglomerado, conglomerado, x+y

    na, nb = idx[a], idx[b]
    ca, cb = bytearray(regs[na][1]), bytearray(regs[nb][1])
    ia, ga, pa = campos_pos(ca)
    ib, gb, pb = campos_pos(cb)
    ca[ia] = (ca[ia] & ~3) | (gb & 3)
    cb[ib] = (cb[ib] & ~3) | (ga & 3)
    ca[ia + 3:ia + 7], cb[ib + 3:ib + 7] = pb, pa
    regs[na], regs[nb] = (1, bytes(ca)), (1, bytes(cb))
    return regs


# ---------------------------------------------------------------- hoja 03: Blankets
def blankets_03(h):
    h.leer_adicional()
    usados = h.uids() | {ao.valor(f, "UniqueID") for f in h.ad}
    n = max(h.max_index_in_sheet(), *[int(ao.valor(f, "IndexInSheet", 0) or 0) for f in h.ad] or [0])
    for clase, pts, (fx, fy), color, _ in pf.BLANKETS:
        n += 1
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        b = [("RECORD", "225"), ("IndexInSheet", str(n)), ("OwnerPartId", "-1"),
             ("Location.X", str(min(xs) // 10)), ("Location.Y", str(min(ys) // 10)),
             ("Corner.X", str(max(xs) // 10)), ("Corner.Y", str(max(ys) // 10)),
             ("Color", str(color)), ("AreaColor", "16777215"), ("LineStyle", "1"), ("LocationCount", str(len(pts)))]
        for k, (x, y) in enumerate(pts, 1):
            b += [(f"X{k}", str(x // 10)), (f"Y{k}", str(y // 10))]
        b += [("LineStyleExt", "1"), ("UniqueID", ao.uid(usados))]
        h.ad.append(b)
        n += 1
        d = [("RECORD", "43"), ("IndexInSheet", str(n)), ("OwnerPartId", "-1"), ("Location.X", str(fx // 10)),
             ("Location.Y", str(fy // 10)), ("Color", "255"), ("Orientation", "1"), ("Name", "Parameter Set"),
             ("UniqueID", ao.uid(usados))]
        idir = h.agregar(d)
        h.agregar([("RECORD", "41"), ("OwnerIndex", str(idir)), ("OwnerPartId", "-1"),
                   ("Location.X", str(fx // 10 - 3)), ("Location.Y", str(fy // 10 + 4)), ("Color", "8388608"),
                   ("FontID", "1"), ("IsHidden", "T"), ("Text", clase), ("Name", "ClassName"),
                   ("UniqueID", ao.uid(usados))])
        h._nota(idir, f"Blanket {clase} (stream Additional) y Parameter Set en ({fx}, {fy})")


# ---------------------------------------------------------------- hoja 04
def hoja_04(h, ps):
    usados = h.uids()
    h.leer_adicional()
    if any(ao.valor(f, "RECORD") == "225" for f in h.ad):
        h.ad = [f for f in h.ad if ao.valor(f, "RECORD") != "225"]
        h._nota(-1, "muestra de Blanket borrada (Additional)")
    for i in sorted(h.buscar(RECORD="43"), reverse=True):
        for j in sorted(h.hijos(i), reverse=True):
            h.borrar(j)
        h.borrar(i)
        h._nota(i, "muestra de Parameter Set borrada")
    for i in h.buscar(RECORD="25", Text="LED_PARAR"):
        h.poner(i, Text="BTN_PARAR")
        h._nota(i, "net label LED_PARAR → BTN_PARAR (pin 9 de U4)")
    # designadores: los índices Z se calcularon antes de borrar la muestra → se ubican por UniqueID
    ref = {}
    for i in h.buscar(RECORD="1"):
        ref[h.v(i, "UniqueID")] = i
    # tabla Z (índice original) → UniqueID, calculada con la hoja sin tocar
    for uidc, nuevo in UID_A_DESIG.items():
        c = ref[uidc]
        d = desig_de(h, c)
        if h.v(d, "Text") != nuevo:
            h.poner(d, Text=nuevo)
    h._nota(-1, "designadores: " + ", ".join(sorted(UID_A_DESIG.values())))
    uid_ref = {h.v(desig_de(h, c), "Text"): h.v(c, "UniqueID") for c in h.buscar(RECORD="1")}

    class _Ref(dict):  # los índices cambian al insertar o borrar: se buscan por UniqueID cada vez
        def __getitem__(self, k):
            return h.por_uid(uid_ref[k])
    por_ref = _Ref()
    # R21 47k → 4,7k
    c = por_ref["R21"]
    if h.v(c, "LibReference") != "RC0805FR-074K7L":
        h.poner(c, LibReference="RC0805FR-074K7L", DesignItemId="RC0805FR-074K7L")
        sincronizar(h, c, params_lib(ps, "RC0805FR-074K7L"), usados, borrar_resto=True)
        com = next(j for j in h.hijos(c) if h.v(j, "Name") == "Comment")
        h.poner(com, Text="RC0805FR-074K7L")
        h._nota(c, "R21: RC0805FR-0747KL (47 kΩ) → RC0805FR-074K7L (4,7 kΩ)")
    for r, lib in (("U4", "ESP32-S3-WROOM-1-N16R2"), ("Q1", "MMBT3904LT1G"), ("Q2", "MMBT3904LT1G"),
                   ("J8", "61300611121")):
        c = por_ref[r]
        sincronizar(h, c, params_lib(ps, lib), usados)
        com = next((j for j in h.hijos(c) if h.v(j, "Name") == "Comment"), None)
        if com is not None and h.v(com, "Text") in ("*", None):
            h.poner(com, Text=lib)
        h._nota(c, f"{r}: parámetros de la librería")
    for r in ("SW1", "SW2", "SW3"):
        c = por_ref[r]
        intercambiar_pines_hoja(h, c)
        if r != "SW1":
            sincronizar(h, c, {"Assembly": "DNP"}, usados)
        h._nota(c, f"{r}: pines B1 y C1 intercambiados" + (", Assembly = DNP" if r != "SW1" else ""))


UID_A_DESIG = {}


def main(carpeta, lib, probar):
    carpeta = Path(carpeta)
    hojas = {n: carpeta / f"{n}.SchDoc" for n in ("02_ALIMENTACION", "03_MEDICION", "04_MCU")}
    if probar:
        tmp = Path(probar)
        tmp.mkdir(parents=True, exist_ok=True)
        hojas = {n: Path(shutil.copy2(p, tmp / p.name)) for n, p in hojas.items()}
        lib = shutil.copy2(lib, tmp / "SamacSys.SchLib")
    h4 = Hoja(hojas["04_MCU"])
    for i in h4.buscar(RECORD="1"):
        z = f"Z{i}"
        if z in DESIG:
            UID_A_DESIG[h4.v(i, "UniqueID")] = DESIG[z]
    ps = L.piezas(lib)
    hoja_04(h4, ps)
    h2 = Hoja(hojas["02_ALIMENTACION"])
    h3 = Hoja(hojas["03_MEDICION"])
    blankets_03(h3)
    for h in (h2, h3, h4):
        print("==", h.ruta.name)
        for n in h.cambios:
            print("  ", n)
        if probar:
            cambios = {"FileHeader": h.datos()}
            if hasattr(h, "ad"):
                cambios["Additional"] = h.datos_adicional()
            ao.escribir_streams(h.ruta, cambios)
        else:
            print("   copia:", h.guardar("antes_ronda2_f4"))
    # librería: pulsador
    ps = L.piezas(lib)
    regs = intercambiar_pines_lib(ps["TS-1187A-B-A-B"]["regs"])
    if probar:
        ao.escribir_streams(lib, {ps["TS-1187A-B-A-B"]["stream"]: ao.unir_registros(regs)})
    else:
        L.guardar_piezas(lib, {ps["TS-1187A-B-A-B"]["stream"]: ao.unir_registros(regs)})
    print("SamacSys.SchLib: TS-1187A-B-A-B con A1/B1 a la izquierda y C1/D1 a la derecha")


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0], a[1], a[a.index("--probar") + 1] if "--probar" in a else None)
