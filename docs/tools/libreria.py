# -*- coding: utf-8 -*-
"""Revisa y corrige una SchLib de Altium (pines, parámetros, footprint) sin abrir Altium.

Uso:
    python docs/tools/libreria.py <SchLib>                       lista de piezas y avisos
    python docs/tools/libreria.py <SchLib> --pieza ATM90E26-YU-R detalle de una pieza
    python docs/tools/libreria.py <SchLib> --poner ATM90E26-YU-R "Manufacturer_Name=Microchip" ["Otro=valor" ...]
    python docs/tools/libreria.py <SchLib> --copiar CL21A106KAYNNNE CL21A475KAQNNNE "Value=4.7uF 25V" ...

--poner cambia (o agrega) parámetros. --copiar crea una pieza nueva a partir de otra con el mismo
encapsulado (mismo símbolo y footprint) y le pone los parámetros dados; Manufacturer_Part_Number,
Supplier PN y Comment toman el nombre nuevo si no se dan, y se borran los parámetros de SamacSys
que solo valen para la pieza original (Datasheet Link, Mouser, Arrow, Height).
Las dos opciones escriben el archivo (Altium CERRADO) y guardan antes una copia en docs/respaldos/.

Avisos que da la revisión: pines repetidos o sin pin 2 en piezas de 2 pines, parámetros obligatorios
vacíos, número de parte distinto del nombre, footprint que no está en la PcbLib de al lado y enlaces
de SamacSys (Datasheet Link, Mouser Part Number) que no corresponden a la pieza.
"""
import re
import sys
from collections import Counter
from pathlib import Path

import altium_ole as ao

OBLIGATORIOS = ["Manufacturer_Name", "Manufacturer_Part_Number", "Supplier", "Supplier PN", "Assembly", "Value"]
DE_SAMACSYS = ["Datasheet Link", "Height", "Mouser Part Number", "Mouser Price/Stock",
               "Arrow Part Number", "Arrow Price/Stock"]


def piezas(ruta):
    """{libref: {"stream": ..., "regs": [(tipo, cuerpo)]}} leyendo la cabecera de la SchLib."""
    import olefile
    o = olefile.OleFileIO(str(ruta))
    cab = ao.campos(o.openstream("FileHeader").read()[4:])
    n = int(ao.valor(cab, "CompCount", 0))
    nombres = [ao.valor(cab, f"LibRef{i}") for i in range(n)]
    # Los nombres largos o con caracteres raros se guardan con otro nombre (SectionKeys)
    claves = {}
    if o.exists("SectionKeys"):
        sk = ao.campos(o.openstream("SectionKeys").read()[4:])
        for i in range(int(ao.valor(sk, "KeyCount", 0))):
            claves[ao.valor(sk, f"LibRef{i}")] = ao.valor(sk, f"SectionKey{i}")
    out = {}
    for nom in nombres:
        st = f"{claves.get(nom, nom)}/Data"
        out[nom] = {"stream": st, "regs": ao.leer_registros(o.openstream(st).read())}
    o.close()
    return out


def footprints_pcblib(ruta_pcblib):
    import olefile
    if not Path(ruta_pcblib).exists():
        return None
    o = olefile.OleFileIO(str(ruta_pcblib))
    nombres = {e[0] for e in o.listdir() if len(e) > 1}
    if o.exists("SectionKeys"):
        sk = ao.campos(o.openstream("SectionKeys").read()[4:])
        for i in range(int(ao.valor(sk, "KeyCount", 0))):
            nombres.add(ao.valor(sk, f"LibRef{i}"))
    o.close()
    return nombres


def resumen(regs):
    comp = ao.campos(regs[0][1])
    params, pines, fps = {}, [], []
    for t, c in regs[1:]:
        if t == 1:
            pines.append(ao.pin_binario(c))
            continue
        f = ao.campos(c)
        rec = ao.valor(f, "RECORD")
        if rec == "41":
            params[ao.valor(f, "Name", "")] = ao.valor(f, "Text", "")
        elif rec == "45" and ao.valor(f, "ModelType") == "PCBLIB":
            fps.append(ao.valor(f, "ModelName"))
    return comp, params, pines, fps


def norm(s):
    return re.sub(r"[^A-Z0-9]", "", (s or "").upper())


def avisos(nombre, regs, fps_lib, otros_mpn=()):
    comp, params, pines, fps = resumen(regs)
    out = []
    por_parte = Counter((p["parte"], p["modo"], p["designador"]) for p in pines)
    rep = sorted({d for (_, _, d), k in por_parte.items() if k > 1})
    if rep:
        out.append(f"pines repetidos: {', '.join(rep)}")
    desigs = {p["designador"] for p in pines}
    if int(ao.valor(comp, "AllPinCount", len(pines)) or 0) == 2 and desigs != {"1", "2"}:
        out.append(f"pieza de 2 pines con designadores {sorted(desigs)}")
    for f in OBLIGATORIOS:
        if not params.get(f):
            out.append(f"falta {f}")
    if not ao.valor(comp, "ComponentDescription"):
        out.append("falta Description")
    mpn = params.get("Manufacturer_Part_Number", "")
    if mpn and norm(mpn) != norm(nombre):
        out.append(f"MPN «{mpn}» distinto del nombre")
    if not fps:
        out.append("sin footprint")
    elif fps_lib is not None:
        for fp in fps:
            if fp not in fps_lib and fp[:31] not in fps_lib:  # el storage de la PcbLib se corta a 31
                out.append(f"footprint {fp} no está en la PcbLib")
    clave = norm(mpn or nombre)[:8]
    mouser = params.get("Mouser Part Number", "")
    if mouser and clave not in norm(mouser):
        out.append(f"Mouser Part Number «{mouser}» no corresponde")
    # enlaces copiados de otra pieza: nombran el número de parte de otra pieza de la librería
    propio = norm(mpn or nombre)
    for campo in ("Datasheet Link", "Mouser Price/Stock", "Arrow Part Number", "Arrow Price/Stock"):
        texto = norm(params.get(campo, ""))
        for otro in otros_mpn:
            if len(otro) >= 8 and otro != propio and otro in texto and propio not in texto:
                out.append(f"{campo} es de {otro}")
                break
    return out


def listar(ruta, solo=None):
    ps = piezas(ruta)
    fps_lib = footprints_pcblib(Path(ruta).with_suffix(".PcbLib"))
    otros = {norm(resumen(d["regs"])[1].get("Manufacturer_Part_Number") or n) for n, d in ps.items()}
    for nombre, d in ps.items():
        if solo and nombre != solo:
            continue
        comp, params, pines, fps = resumen(d["regs"])
        av = avisos(nombre, d["regs"], fps_lib, otros)
        print(f"{nombre:24s} {','.join(fps):22s} {params.get('Manufacturer_Name', '—'):14s} "
              f"{params.get('Value', '—'):22s} {params.get('Supplier', '—'):9s} {params.get('Assembly', '—'):8s}"
              + (f"  ← {'; '.join(av)}" if av else ""))
        if solo:
            print("  Description:", ao.valor(comp, "ComponentDescription"))
            for k, v in params.items():
                print(f"  {k} = {v}")
            for p in sorted(pines, key=lambda p: (p["parte"], p["designador"])):
                print(f"  pin {p['designador']:>4s} {p['nombre']:14s} parte {p['parte']} modo {p['modo']} "
                      f"x={p['x'] * 10} y={p['y'] * 10} mil rot={p['rotacion'] * 90}° largo={p['largo'] * 10}"
                      + (" OCULTO" if p["oculto"] else ""))


def poner_params(regs, cambios, usados):
    """Cambia o agrega parámetros (RECORD=41) en la lista de registros de una pieza."""
    regs = list(regs)
    for nombre_p, val in cambios.items():
        if nombre_p.lower() == "description":
            comp = ao.poner(ao.campos(regs[0][1]), "ComponentDescription", val)
            regs[0] = (0, ao.cuerpo(comp))
            # SamacSys además trae un parámetro «Description»: se actualiza si existe
            for n, (t, c) in enumerate(regs):
                f = ao.campos(c) if t == 0 else []
                if ao.valor(f, "RECORD") == "41" and (ao.valor(f, "Name") or "").lower() == "description":
                    regs[n] = (0, ao.cuerpo(ao.poner(f, "Text", val, antes_de="Name")))
            continue
        hecho = False
        for n, (t, c) in enumerate(regs):
            if t == 0:
                f = ao.campos(c)
                if ao.valor(f, "RECORD") == "41" and ao.valor(f, "Name", "").lower() == nombre_p.lower():
                    f = ao.poner(f, "Text", val, antes_de="Name")
                    regs[n] = (0, ao.cuerpo(f))
                    hecho = True
        if not hecho:
            # se inserta después del último parámetro de la cabecera (antes de pines y dibujo)
            pos = 1
            for n, (t, c) in enumerate(regs[1:], 1):
                if t == 0 and ao.valor(ao.campos(c), "RECORD") == "41":
                    pos = n + 1
                else:
                    break
            nuevo = [("RECORD", "41"), ("OwnerPartId", "-1"), ("Color", "8388608"), ("FontID", "1"),
                     ("IsHidden", "T"), ("Text", val), ("Name", nombre_p), ("UniqueID", ao.uid(usados))]
            regs = insertar(regs, pos, (0, ao.cuerpo(nuevo)))
    return regs


def insertar(regs, pos, reg):
    """Inserta un registro y corrige los OwnerIndex que apuntan a registros corridos."""
    out = []
    for t, c in regs:
        if t == 0:
            f = ao.campos(c)
            oi = ao.valor(f, "OwnerIndex")
            if oi is not None and int(oi) >= pos:
                c = ao.cuerpo(ao.poner(f, "OwnerIndex", str(int(oi) + 1)))
        out.append((t, c))
    out.insert(pos, reg)
    return out


def quitar_params(regs, nombres):
    """Borra parámetros (RECORD=41) por nombre, corrigiendo los OwnerIndex."""
    regs = list(regs)
    n = 1
    while n < len(regs):
        t, c = regs[n]
        f = ao.campos(c) if t == 0 else []
        if t == 0 and ao.valor(f, "RECORD") == "41" and ao.valor(f, "Name", "") in nombres:
            del regs[n]
            for m, (t2, c2) in enumerate(regs):
                if t2 == 0:
                    f2 = ao.campos(c2)
                    oi = ao.valor(f2, "OwnerIndex")
                    if oi is not None and int(oi) > n:
                        regs[m] = (0, ao.cuerpo(ao.poner(f2, "OwnerIndex", str(int(oi) - 1))))
        else:
            n += 1
    return regs


def cambios_de(args):
    out = {}
    for a in args:
        k, v = a.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def usados_en(ps):
    u = set()
    for d in ps.values():
        for t, c in d["regs"]:
            if t == 0:
                v = ao.valor(ao.campos(c), "UniqueID")
                if v:
                    u.add(v)
    return u


def guardar_piezas(ruta, nuevas_streams, cabecera=None):
    if ao.altium_abierto():
        raise SystemExit("Altium está abierto: ciérralo antes de escribir la librería.")
    copia = ao.respaldo(ruta)
    print(f"copia de seguridad: {copia}")
    if cabecera is not None:
        nuevas_streams = dict(nuevas_streams, FileHeader=cabecera)
    ao.escribir_streams(ruta, nuevas_streams)


def poner(ruta, pieza, cambios):
    poner_lote(ruta, {pieza: cambios})


def poner_lote(ruta, lote):
    """lote = {pieza: {parámetro: valor}}; escribe todas las piezas de una vez (una sola copia)."""
    ps = piezas(ruta)
    faltan = [p for p in lote if p not in ps]
    if faltan:
        raise SystemExit(f"no están en {ruta}: {', '.join(faltan)}")
    usados = usados_en(ps)
    nuevos = {}
    for pieza, cambios in lote.items():
        nuevos[ps[pieza]["stream"]] = ao.unir_registros(poner_params(ps[pieza]["regs"], cambios, usados))
    guardar_piezas(ruta, nuevos)
    for pieza, cambios in lote.items():
        print(f"{pieza}: " + ", ".join(f"{k} = «{v}»" for k, v in cambios.items()))


def copiar(ruta, origen, nueva, cambios):
    """Pieza nueva con el símbolo y footprint de `origen`. Necesita crear un storage: se hace con
    el almacenamiento de Windows y se agrega la pieza a la cabecera (FileHeader)."""
    import pythoncom
    from win32com import storagecon as sc

    ps = piezas(ruta)
    if origen not in ps:
        raise SystemExit(f"{origen} no está en {ruta}")
    if nueva in ps:
        raise SystemExit(f"{nueva} ya existe; usa --poner")
    if len(nueva) > 31 or re.search(r"[/\\:*?\"<>|]", nueva):
        raise SystemExit("nombre largo o con caracteres raros: créala en Altium")
    regs = quitar_params(ps[origen]["regs"], DE_SAMACSYS)
    comp = ao.campos(regs[0][1])
    for k in ("LibReference", "DesignItemId"):
        comp = ao.poner(comp, k, nueva)
    comp = ao.poner(comp, "UniqueID", ao.uid(usados_en(ps)))
    regs[0] = (0, ao.cuerpo(comp))
    base = {"Manufacturer_Part_Number": nueva, "Supplier PN": nueva, "Comment": nueva}
    base.update(cambios)
    regs = poner_params(regs, base, usados_en(ps))
    # UniqueID nuevos para todos los registros
    usados = usados_en(ps)
    for n, (t, c) in enumerate(regs):
        if t == 0:
            f = ao.campos(c)
            if ao.valor(f, "UniqueID"):
                regs[n] = (0, ao.cuerpo(ao.poner(f, "UniqueID", ao.uid(usados))))
    # cabecera: CompCount, LibRefN, CompDescrN, PartCountN
    data = ao.leer_stream(ruta, "FileHeader")
    tipo, cab_c = ao.leer_registros(data)[0]
    cab = ao.campos(cab_c)
    n = int(ao.valor(cab, "CompCount"))
    i_or = next(i for i in range(n) if ao.valor(cab, f"LibRef{i}") == origen)
    pos_fin = max(k for k, (c, _) in enumerate(cab) if re.match(r"(LibRef|CompDescr|PartCount)\d+$", c)) + 1
    nuevos = [(f"LibRef{n}", nueva),
              (f"CompDescr{n}", cambios.get("Description", ao.valor(cab, f"CompDescr{i_or}", ""))),
              (f"PartCount{n}", ao.valor(cab, f"PartCount{i_or}", "1"))]
    cab = cab[:pos_fin] + nuevos + cab[pos_fin:]
    cab = ao.poner(cab, "CompCount", str(n + 1))
    resto = data[4 + len(cab_c):]
    nueva_cab = ao.unir_registros([(tipo, ao.cuerpo(cab))]) + resto

    if ao.altium_abierto():
        raise SystemExit("Altium está abierto: ciérralo antes de escribir la librería.")
    print(f"copia de seguridad: {ao.respaldo(ruta)}")
    modo = sc.STGM_READWRITE | sc.STGM_SHARE_EXCLUSIVE | sc.STGM_TRANSACTED
    raiz = pythoncom.StgOpenStorage(str(ruta), None, modo, None, 0)
    sub = raiz.CreateStorage(nueva, sc.STGM_READWRITE | sc.STGM_SHARE_EXCLUSIVE | sc.STGM_CREATE, 0, 0)
    st = sub.CreateStream("Data", sc.STGM_READWRITE | sc.STGM_SHARE_EXCLUSIVE | sc.STGM_CREATE, 0, 0)
    st.Write(ao.unir_registros(regs))
    st.Commit(0)
    del st
    sub.Commit(0)
    del sub
    fh = raiz.OpenStream("FileHeader", None, sc.STGM_READWRITE | sc.STGM_SHARE_EXCLUSIVE, 0)
    fh.SetSize(len(nueva_cab))
    fh.Seek(0, 0)
    fh.Write(nueva_cab)
    fh.Commit(0)
    del fh
    raiz.Commit(0)
    del raiz
    print(f"{nueva}: copiada de {origen} · " + ", ".join(f"{k} = {v}" for k, v in base.items()))


if __name__ == "__main__":
    a = sys.argv[1:]
    ruta = a[0]
    if "--poner" in a:
        i = a.index("--poner")
        poner(ruta, a[i + 1], cambios_de(a[i + 2:]))
    elif "--copiar" in a:
        i = a.index("--copiar")
        copiar(ruta, a[i + 1], a[i + 2], cambios_de(a[i + 3:]))
    else:
        listar(ruta, a[a.index("--pieza") + 1] if "--pieza" in a else None)
