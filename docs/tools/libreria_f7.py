# -*- coding: utf-8 -*-
"""F7: librería propia del proyecto y arreglos de footprints (14 oct 2026, Altium CERRADO).

1. Copia SamacSys.SchLib/PcbLib de Documents/AltiumLL a lib/ del proyecto. La librería de AltiumLL
   (compartida con otros proyectos y con el Library Loader) no se toca.
2. PcbLib de lib/:
   - BATHLD001 (BT1): pads según el plano TE rev E1 (centros en ±10,5 mm, 1,8 × 5,2 mm; contacto
     negativo de Ø17,0 mm). SamacSys los tenía en ±11,45 mm (2,5 × 5,1) y Ø17,8.
   - Footprint nuevo BLX-A_5X20 para F1B/F2B: portafusible 5×20 XC Electronics BLX-A (LCSC C3131),
     2 pines planos de 1,5 × 0,35 mm a 22 ± 0,5 mm → agujero Ø1,9, pad Ø3,4; cuerpo 26,4 × 9,5 mm.
     El 01000056Z de SamacSys era un solo clip (pines a 4,6 mm): soldado, puenteaba el fusible.
3. SchLib de lib/: pieza nueva BLX-A (símbolo del 01000056Z, footprint BLX-A_5X20 y sus parámetros);
   se borran las piezas que el proyecto no usa (y el 01000056Z); los modelos de footprint apuntan a
   lib/SamacSys.PcbLib; se quitan los «Mouser Part Number» que SamacSys copió de otra pieza.
4. .PrjPcb: librerías en lib/, sin Job1.OutJob, Revision 1.0.

Uso: python docs/tools/libreria_f7.py [--probar <carpeta>]
     --probar copia las librerías y el .PrjPcb a <carpeta> y trabaja ahí (no toca el proyecto).
"""
import re
import shutil
import sys
from pathlib import Path

import altium_ole as ao
import libreria as L
import pcblib_editar as PE

PROY = Path("C:/Nicolas/UNIVERSIDAD - 2026/Hardware en IoT/Control de Carga IoT/Control de Carga IoT")
LL = Path("C:/Users/nico/Documents/AltiumLL")
HOJAS = ["02_ALIMENTACION", "03_MEDICION", "04_MCU", "05_SENSORES", "06_ACTUACION"]

BLX = "BLX-A"
BLX_FP = "BLX-A_5X20"
# SamacSys les puso el número de Mouser de otra pieza (libreria.py lo marca); se quitan
MOUSER_AJENO = ["ECS-81.92-12-30Q-EN-TR", "BLM21PG221SN1D", "SS34-E3_57T"]
BLX_PARAMS = {
    "Manufacturer_Name": "XC Electronics",
    "Manufacturer_Part_Number": "BLX-A",
    "Value": "5x20 6.3A 250V",
    "Supplier": "Sigma",
    "Supplier PN": "BLX-A",
    "Assembly": "DNP",
    "Description": "Portafusible 5x20 mm para PCB, 2 pines a 22 mm (XC Electronics BLX-A, LCSC C3131)",
}


def usados_en_hojas():
    out = set()
    for h in HOJAS:
        regs = [ao.campos(c) for _, c in ao.leer_registros(ao.leer_stream(PROY / f"{h}.SchDoc", "FileHeader"))]
        for r in regs[1:]:
            if ao.valor(r, "RECORD") == "1" and ao.valor(r, "SourceLibraryName") != "Altium Content Vault":
                out.add(ao.valor(r, "LibReference"))
    return out


# ---------------------------------------------------------------- PcbLib
def arreglar_pcblib(ruta, nueva_ruta_txt):
    cambios, nuevos, notas = {}, {}, []

    fp = PE.leer_fp(ruta, "BATHLD001")
    PE.poner_pad(fp, "1", x=-10.5, y=0, tam=(5.2, 1.8))
    PE.poner_pad(fp, "2", x=10.5, y=0, tam=(5.2, 1.8))
    PE.poner_pad(fp, "3", tam=(17.0, 17.0))
    cambios["BATHLD001/Data"] = PE.armar_fp(fp)
    notas.append("BATHLD001: pads 1 y 2 a ±10,5 mm de 1,8 × 5,2 mm; pad 3 de Ø17,0 mm (plano TE rev E1)")

    fp = PE.leer_fp(ruta, "01000056Z")
    plant = {}
    for t, bl in fp["prims"]:
        if t == 4:
            plant.setdefault(bl[0][0], bl)
    for n, x in (("1", -11.0), ("2", 11.0)):
        PE.poner_pad(fp, n, x=x, y=0, tam=(3.4, 3.4), agujero=1.9, forma=1)
    prims = [p for p in fp["prims"] if p[0] == 2]
    prims += PE.rectangulo(plant[69], -13.2, -4.75, 13.2, 4.75)      # cuerpo (mecánica)
    prims += PE.rectangulo(plant[71], -13.7, -5.25, 13.7, 5.25)      # courtyard
    prims += PE.rectangulo(plant[33], -13.4, -4.95, 13.4, 4.95)      # serigrafía
    fp["prims"] = prims
    desc = "Portafusible 5x20 BLX-A, pines a 22 mm"
    nuevos[BLX_FP] = {"Data": PE.armar_fp(fp, BLX_FP), **PE.aux_nuevo(fp, BLX_FP, desc)}
    notas.append(f"{BLX_FP}: footprint nuevo (2 pads THT Ø3,4/Ø1,9 a 22 mm, cuerpo 26,4 × 9,5 mm)")

    import olefile
    o = olefile.OleFileIO(str(ruta))
    libdata = o.openstream("Library/Data").read()
    toc = o.openstream("Library/ComponentParamsTOC/Data").read()
    o.close()
    cambios["Library/Data"], _ = PE.library_data_agregar(libdata, BLX_FP, archivo=nueva_ruta_txt)
    cambios["Library/ComponentParamsTOC/Data"] = PE.toc_agregar(toc, BLX_FP, 2, desc)
    PE.escribir(ruta, cambios, nuevos)
    return notas


# ---------------------------------------------------------------- SchLib
def modelo_a(regs, pcblib_txt, nombre_fp=None):
    out = []
    for t, c in regs:
        if t == 0:
            f = ao.campos(c)
            if ao.valor(f, "RECORD") == "45" and ao.valor(f, "ModelType") == "PCBLIB":
                if nombre_fp:
                    f = ao.poner(f, "ModelName", nombre_fp)
                    f = ao.poner(f, "ModelDatafileEntity0", nombre_fp)
                if ao.valor(f, "ModelDatafile0"):
                    f = ao.poner(f, "ModelDatafile0", pcblib_txt)
                c = ao.cuerpo(f)
        out.append((t, c))
    return out


def pieza_blx(ps, pcblib_txt):
    usados = L.usados_en(ps)
    regs = L.quitar_params(ps["01000056Z"]["regs"], L.DE_SAMACSYS)
    comp = ao.campos(regs[0][1])
    for k in ("LibReference", "DesignItemId"):
        comp = ao.poner(comp, k, BLX)
    regs[0] = (0, ao.cuerpo(comp))
    regs = L.poner_params(regs, dict(BLX_PARAMS, Comment=BLX), usados)
    regs = modelo_a(regs, pcblib_txt, BLX_FP)
    out = []
    for t, c in regs:
        if t == 0:
            f = ao.campos(c)
            if ao.valor(f, "RECORD") == "34":
                f = ao.poner(f, "Text", "F?")
            if ao.valor(f, "UniqueID"):
                f = ao.poner(f, "UniqueID", ao.uid(usados))
            c = ao.cuerpo(f)
        out.append((t, c))
    return out


def arreglar_schlib(ruta, pcblib_txt, usados_hojas):
    import pythoncom
    from win32com import storagecon as sc

    ps = L.piezas(ruta)
    faltan = usados_hojas - set(ps)
    if faltan:
        raise SystemExit(f"piezas de las hojas que no están en la librería: {faltan}")
    usados_hojas = usados_hojas - {"01000056Z"}          # F1B/F2B pasan a BLX-A (arreglos_hojas_f7.py)
    quedan = [n for n in ps if n in usados_hojas]
    borrar = [n for n in ps if n not in usados_hojas]
    datos = {n: modelo_a(ps[n]["regs"], pcblib_txt) for n in quedan}
    for n in MOUSER_AJENO:
        datos[n] = L.quitar_params(datos[n], ["Mouser Part Number", "Mouser Price/Stock"])
    datos[BLX] = pieza_blx(ps, pcblib_txt)

    fh = ao.leer_stream(ruta, "FileHeader")
    tipo, cab_c = ao.leer_registros(fh)[0]
    cab = ao.campos(cab_c)
    n = int(ao.valor(cab, "CompCount"))
    info = {ao.valor(cab, f"LibRef{i}"): (ao.valor(cab, f"CompDescr{i}", ""), ao.valor(cab, f"PartCount{i}", "1"))
            for i in range(n)}
    info[BLX] = (BLX_PARAMS["Description"], info["01000056Z"][1])
    base = [kv for kv in cab if not re.match(r"(LibRef|CompDescr|PartCount)\d+$", kv[0])]
    pos = next(k for k, (c, _) in enumerate(base) if c == "CompCount")
    lista = []
    for i, nom in enumerate(quedan + [BLX]):
        d, pc = info[nom]
        lista += [(f"LibRef{i}", nom), (f"CompDescr{i}", d), (f"PartCount{i}", pc)]
    cab = base[:pos + 1] + lista + base[pos + 1:]
    cab = ao.poner(cab, "CompCount", str(len(quedan) + 1))
    cab = ao.poner(cab, "Weight", str(sum(len(r) for r in datos.values())))
    nueva_cab = ao.unir_registros([(tipo, ao.cuerpo(cab))]) + fh[4 + len(cab_c):]

    rw = sc.STGM_READWRITE | sc.STGM_SHARE_EXCLUSIVE
    raiz = pythoncom.StgOpenStorage(str(ruta), None, rw | sc.STGM_TRANSACTED, None, 0)
    for nom in borrar:
        raiz.DestroyElement(ps[nom]["stream"].split("/")[0])
    for nom, regs in datos.items():
        data = ao.unir_registros(regs)
        if nom == BLX:
            sub = raiz.CreateStorage(BLX, rw | sc.STGM_CREATE, 0, 0)
            st = sub.CreateStream("Data", rw | sc.STGM_CREATE, 0, 0)
        else:
            sub = raiz.OpenStorage(ps[nom]["stream"].split("/")[0], None, rw, None, 0)
            st = sub.OpenStream("Data", None, rw, 0)
            st.SetSize(len(data))
            st.Seek(0, 0)
        st.Write(data)
        st.Commit(0)
        del st
        sub.Commit(0)
        del sub
    st = raiz.OpenStream("FileHeader", None, rw, 0)
    st.SetSize(len(nueva_cab))
    st.Seek(0, 0)
    st.Write(nueva_cab)
    st.Commit(0)
    del st
    raiz.Commit(0)
    del raiz
    return quedan, borrar


# ---------------------------------------------------------------- .PrjPcb
def arreglar_prjpcb(ruta):
    crudo = Path(ruta).read_bytes()
    bom = crudo.startswith(b"\xef\xbb\xbf")
    txt = crudo.decode("utf-8-sig")
    lineas = txt.splitlines(keepends=True)
    out, saltar, notas = [], False, []
    for ln in lineas:
        s = ln.strip()
        if s.startswith("[") and s.endswith("]"):
            saltar = False
        if s.startswith("DocumentPath=") and s.endswith("Job1.OutJob"):
            # quita la sección completa [DocumentN] (ya se agregó su encabezado a out)
            while out and not out[-1].strip().startswith("[Document"):
                out.pop()
            out.pop()
            saltar = True
            notas.append("se quitó Job1.OutJob del proyecto")
            continue
        if saltar:
            continue
        m = re.match(r"DocumentPath=.*\\AltiumLL\\(SamacSys\.(SchLib|PcbLib))\s*$", s)
        if m:
            ln = ln.replace(s, f"DocumentPath=lib\\{m.group(1)}")
            notas.append(f"{m.group(1)} → lib\\{m.group(1)}")
        out.append(ln)
    txt = "".join(out)
    # Revision 1.0 (parámetro del proyecto)
    txt2 = re.sub(r"(\[Parameter\d+\]\r?\nName=Revision\r?\nValue=)[^\r\n]*", r"\g<1>1.0", txt)
    if txt2 != txt:
        notas.append("Revision = 1.0")
    # numeración continua de [DocumentN]
    k = 0

    def renum(m):
        nonlocal k
        k += 1
        return f"[Document{k}]"
    txt2 = re.sub(r"\[Document\d+\]", renum, txt2)
    Path(ruta).write_bytes((b"\xef\xbb\xbf" if bom else b"") + txt2.encode("utf-8"))
    return notas


def main(probar=None):
    if ao.altium_abierto():
        raise SystemExit("Altium está abierto: ciérralo antes de correr el script.")
    destino = Path(probar) if probar else PROY / "lib"
    prj = PROY / "Control de Carga IoT.PrjPcb"
    if probar:
        destino.mkdir(parents=True, exist_ok=True)
        shutil.copy2(prj, destino / prj.name)
        prj = destino / prj.name
    sch, pcb = destino / "SamacSys.SchLib", destino / "SamacSys.PcbLib"
    for f in (sch, pcb):
        if f.exists() and not probar:
            print(f"respaldo de la copia anterior: {ao.respaldo(f, 'antes_f7')}")
    if not probar:
        print(f"respaldo: {ao.respaldo(prj, 'antes_f7')}")
    shutil.copy2(LL / "SamacSys.SchLib", sch)
    shutil.copy2(LL / "SamacSys.PcbLib", pcb)
    print(f"copiadas a {destino}: SamacSys.SchLib y SamacSys.PcbLib")

    pcblib_txt = str(PROY / "lib" / "SamacSys.PcbLib").replace("/", "\\")
    for n in arreglar_pcblib(pcb, pcblib_txt):
        print("  PcbLib:", n)
    quedan, borradas = arreglar_schlib(sch, pcblib_txt, usados_en_hojas())
    print(f"  SchLib: {len(quedan)} piezas del proyecto + {BLX} nueva; modelos → {pcblib_txt}")
    print(f"  SchLib: {len(borradas)} piezas sin uso borradas: {', '.join(sorted(borradas))}")
    for n in arreglar_prjpcb(prj):
        print("  PrjPcb:", n)


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[a.index("--probar") + 1] if "--probar" in a else None)
