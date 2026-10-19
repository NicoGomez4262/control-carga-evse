# -*- coding: utf-8 -*-
"""Edición de footprints de una PcbLib de Altium sin abrir Altium (Altium CERRADO).

Formato (el mismo que lee pcblib.py): el stream «<footprint>/Data» empieza con el nombre
(u32 largo + texto Pascal) y sigue con primitivas: 1 byte de tipo + N bloques (u32 largo + datos).
Tipos: 1 arco, 2 pad (6 bloques), 4 track, 5 texto, 6 fill, 11 región, 12 cuerpo 3D.

Pad, bloque 4 (geometría): capa @0, posición x/y @13, tamaño arriba/medio/abajo @21/@29/@37,
agujero @45, forma arriba/medio/abajo @49-51, rotación (double) @52.
Track, bloque 0: capa @0, inicio x/y @13, fin x/y @21, ancho @29.
Unidades internas: 1/10000 mil (pcblib.U mm por unidad).

    fp = leer_fp(ruta, "BATHLD001")          # {"nombre": ..., "prims": [(tipo, [bloques])]}
    poner_pad(fp, "1", x=-10.5, tam=(5.2, 1.8))
    datos = armar_fp(fp)                      # bytes del stream Data
"""
import random
import struct
import uuid

import olefile

import pcblib as P

TIPO = {1: "arco", 2: "pad", 3: "via", 4: "track", 5: "texto", 6: "fill", 11: "region", 12: "cuerpo"}
GUID_TIPO = {1: 1, 2: 2, 4: 4, 12: 90}   # tipo de primitiva → código en PrimitiveGuids (85 = el componente)


def u(mm):
    return int(round(mm / P.U))


def leer_fp(ruta, nombre):
    o = olefile.OleFileIO(str(ruta))
    try:
        data = o.openstream(f"{nombre}/Data").read()
        aux = {s: o.openstream(f"{nombre}/{s}").read() for s in
               ("Header", "Parameters", "WideStrings", "PrimitiveGuids/Header", "PrimitiveGuids/Data",
                "UniqueIDPrimitiveInformation/Header", "UniqueIDPrimitiveInformation/Data")
               if o.exists(f"{nombre}/{s}")}
    finally:
        o.close()
    ln = struct.unpack_from("<I", data, 0)[0]
    prims, i = [], 4 + ln
    while i < len(data):
        t = data[i]
        i += 1
        if t not in P.NBLOQ:
            raise ValueError(f"{nombre}: primitiva de tipo {t} desconocida en el byte {i - 1}")
        bl, i = P.bloques(data, i, P.NBLOQ[t])
        prims.append((t, [bytearray(b) for b in bl]))
    return {"nombre": data[4:4 + ln], "prims": prims, "aux": aux}


def armar_fp(fp, nombre=None):
    if nombre is not None:
        b = nombre.encode("latin-1")
        fp["nombre"] = bytes([len(b)]) + b
    out = bytearray(struct.pack("<I", len(fp["nombre"])) + fp["nombre"])
    for t, bl in fp["prims"]:
        out.append(t)
        for b in bl:
            out += struct.pack("<I", len(b)) + bytes(b)
    return bytes(out)


def nombre_pad(bl):
    return bl[0][1:1 + bl[0][0]].decode("latin-1")


def pads(fp):
    return {nombre_pad(bl): bl for t, bl in fp["prims"] if t == 2}


def poner_pad(fp, nombre, x=None, y=None, tam=None, agujero=None, forma=None, nuevo_nombre=None):
    """tam = (sx, sy) en mm, en el eje del pad antes de su rotación (igual para arriba, medio y abajo)."""
    bl = pads(fp)[nombre]
    g = bl[4]
    if x is not None:
        struct.pack_into("<i", g, 13, u(x))
    if y is not None:
        struct.pack_into("<i", g, 17, u(y))
    if tam is not None:
        for off in (21, 29, 37):
            struct.pack_into("<ii", g, off, u(tam[0]), u(tam[1]))
    if agujero is not None:
        struct.pack_into("<i", g, 45, u(agujero))
    if forma is not None:
        g[49] = g[50] = g[51] = forma
    if nuevo_nombre is not None:
        b = nuevo_nombre.encode("latin-1")
        bl[0] = bytearray(bytes([len(b)]) + b)


def track(plantilla, x1, y1, x2, y2, ancho=None):
    """Track nuevo copiando la capa y las banderas de otro track (bloques de la plantilla)."""
    g = bytearray(plantilla[0])
    struct.pack_into("<iiii", g, 13, u(x1), u(y1), u(x2), u(y2))
    if ancho is not None:
        struct.pack_into("<i", g, 29, u(ancho))
    return (4, [g])


def rectangulo(plantilla, x1, y1, x2, y2, ancho=None):
    return [track(plantilla, x1, y1, x2, y1, ancho), track(plantilla, x2, y1, x2, y2, ancho),
            track(plantilla, x2, y2, x1, y2, ancho), track(plantilla, x1, y2, x1, y1, ancho)]


def capa(bl_o_prim):
    t, bl = bl_o_prim
    return bl[4][0] if t == 2 else bl[0][0]


# ---------------------------------------------------------------- streams auxiliares de un footprint nuevo
def _texto(txt):
    b = txt.encode("latin-1") + b"\x00"
    return struct.pack("<I", len(b)) + b


def aux_nuevo(fp, nombre, descripcion="", usados=None):
    """Header, Parameters, WideStrings, PrimitiveGuids y UniqueIDPrimitiveInformation para `fp`."""
    usados = usados if usados is not None else set()
    prims = fp["prims"]
    guids = [struct.pack("<II", 85, 0) + uuid.uuid4().bytes_le]
    for k, (t, _) in enumerate(prims):
        guids.append(struct.pack("<II", GUID_TIPO.get(t, t), k) + uuid.uuid4().bytes_le)
    uids = b""
    n_pads = 0
    for k, (t, _) in enumerate(prims):
        if t == 2:
            while True:
                uid = "".join(random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ") for _ in range(8))
                if uid not in usados:
                    usados.add(uid)
                    break
            uids += _texto(f"|PRIMITIVEINDEX={k}|PRIMITIVEOBJECTID=Pad|UNIQUEID={uid}")
            n_pads += 1
    return {
        "Header": struct.pack("<I", len(prims)),
        "Parameters": _texto(f"|PATTERN={nombre}|HEIGHT=0mil|DESCRIPTION={descripcion}|ITEMGUID=|REVISIONGUID="),
        "WideStrings": fp["aux"].get("WideStrings", struct.pack("<I", 1) + b"\x00"),
        "PrimitiveGuids/Header": struct.pack("<I", len(guids)),
        "PrimitiveGuids/Data": b"".join(guids),
        "UniqueIDPrimitiveInformation/Header": struct.pack("<I", n_pads),
        "UniqueIDPrimitiveInformation/Data": uids,
    }


# ---------------------------------------------------------------- lista de footprints de la librería
def library_data_agregar(data, nombre, archivo=None):
    """Library/Data: propiedades + u32 cantidad + [u32 largo + Pascal] por footprint."""
    ln = struct.unpack_from("<I", data, 0)[0]
    props = data[4:4 + ln]
    if archivo is not None:
        txt = props.rstrip(b"\x00").decode("latin-1")
        partes = txt.split("|")
        partes = [f"FILENAME={archivo}" if p.upper().startswith("FILENAME=") else p for p in partes]
        props = "|".join(partes).encode("latin-1") + b"\x00"
    k = 4 + ln
    n = struct.unpack_from("<I", data, k)[0]
    lista = data[k + 4:]
    nombres, j = [], 0
    for _ in range(n):
        sl = struct.unpack_from("<I", lista, j)[0]
        s = lista[j + 4:j + 4 + sl]
        nombres.append(s[1:1 + s[0]].decode("latin-1"))
        j += 4 + sl
    if j != len(lista):
        raise ValueError("Library/Data tiene datos después de la lista de footprints")
    if nombre is not None:
        if nombre in nombres:
            raise ValueError(f"{nombre} ya está en la librería")
        b = nombre.encode("latin-1")
        lista += struct.pack("<I", len(b) + 1) + bytes([len(b)]) + b
        n += 1
    return struct.pack("<I", len(props)) + props + struct.pack("<I", n) + lista, nombres


def toc_agregar(data, nombre, pads, descripcion=""):
    txt = data[4:].rstrip(b"\x00")
    txt += f"Name={nombre}|Pad Count={pads}|Height=0|Description={descripcion}\r\n".encode("latin-1") + b"\x00"
    return struct.pack("<I", len(txt)) + txt


# ---------------------------------------------------------------- escritura (almacenamiento de Windows)
def escribir(ruta, cambios, nuevos=None):
    """cambios = {"FP/Data": bytes, ...} en streams que ya existen; nuevos = {"FP": {"Data": bytes,
    "PrimitiveGuids/Data": bytes, ...}} crea el storage del footprint con sus streams."""
    import pythoncom
    from win32com import storagecon as sc

    rw = sc.STGM_READWRITE | sc.STGM_SHARE_EXCLUSIVE
    raiz = pythoncom.StgOpenStorage(str(ruta), None, rw | sc.STGM_TRANSACTED, None, 0)
    for nombre, streams in (nuevos or {}).items():
        sub = raiz.CreateStorage(nombre, rw | sc.STGM_CREATE, 0, 0)
        subs = {}
        for s, data in streams.items():
            partes = s.split("/")
            st_padre = sub
            if len(partes) == 2:
                if partes[0] not in subs:
                    subs[partes[0]] = sub.CreateStorage(partes[0], rw | sc.STGM_CREATE, 0, 0)
                st_padre = subs[partes[0]]
            st = st_padre.CreateStream(partes[-1], rw | sc.STGM_CREATE, 0, 0)
            st.Write(data)
            st.Commit(0)
            del st
        for s in subs.values():
            s.Commit(0)
        del subs
        sub.Commit(0)
        del sub
    raiz.Commit(0)
    del raiz
    if cambios:
        import altium_ole as ao
        ao.escribir_streams(ruta, cambios)
