# -*- coding: utf-8 -*-
"""Lectura y escritura de archivos de Altium (.SchLib, .SchDoc) sin abrir Altium.

Los archivos de Altium son «compound files» de OLE. Cada stream es una lista de registros:
3 bytes de largo + 1 byte de tipo (0 = texto «|CLAVE=valor|...», 1 = binario, como los pines
de las SchLib) + el cuerpo. Aquí se leen con olefile y se escriben con el almacenamiento
estructurado de Windows (pywin32), que admite streams de cualquier tamaño.

Altium tiene que estar CERRADO al escribir. Antes de escribir, `respaldo()` copia el archivo
a docs/respaldos/ con fecha y hora.
"""
import random
import shutil
import string
import sys
from datetime import datetime
from pathlib import Path

import olefile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RESPALDOS = Path(__file__).resolve().parents[1] / "respaldos"


# ---------------------------------------------------------------- registros
def leer_registros(data):
    """[(tipo, cuerpo)] de un stream."""
    i, out = 0, []
    while i + 4 <= len(data):
        ln = int.from_bytes(data[i:i + 3], "little")
        out.append((data[i + 3], bytes(data[i + 4:i + 4 + ln])))
        i += 4 + ln
    return out


def unir_registros(regs):
    return b"".join(len(c).to_bytes(3, "little") + bytes([t]) + c for t, c in regs)


def campos(cuerpo):
    """Registro de texto → lista ordenada [(clave, valor)] (conserva mayúsculas y orden)."""
    out = []
    for kv in cuerpo.rstrip(b"\x00").decode("latin-1").split("|"):
        if "=" in kv:
            k, v = kv.split("=", 1)
            out.append((k, v))
    return out


def cuerpo(lista):
    return ("|" + "|".join(f"{k}={v}" for k, v in lista)).encode("latin-1") + b"\x00"


def valor(lista, clave, defecto=None):
    for k, v in lista:
        if k.upper() == clave.upper():
            return v
    return defecto


def poner(lista, clave, val, antes_de=None):
    """Cambia (o agrega) clave=val. Si no existe, la mete antes de `antes_de` o al final.

    Si el texto viejo tenía caracteres no ASCII, Altium guardó además una copia «%UTF8%clave» y es la
    que lee primero: se borra para que no reponga el valor viejo (pasó con el Value del DS3231SN)."""
    if not clave.upper().startswith("%UTF8%"):
        lista[:] = [(k, v) for k, v in lista if k.upper() != "%UTF8%" + clave.upper()]
    for n, (k, _) in enumerate(lista):
        if k.upper() == clave.upper():
            lista[n] = (k, val)
            return lista
    pos = len(lista)
    if antes_de:
        for n, (k, _) in enumerate(lista):
            if k.upper() == antes_de.upper():
                pos = n
                break
    lista.insert(pos, (clave, val))
    return lista


def quitar(lista, clave):
    return [(k, v) for k, v in lista if k.upper() != clave.upper()]


def uid(usados=None):
    """UniqueID nuevo de 8 letras mayúsculas, como los de Altium."""
    usados = usados or set()
    while True:
        u = "".join(random.choice(string.ascii_uppercase) for _ in range(8))
        if u not in usados:
            usados.add(u)
            return u


# ---------------------------------------------------------------- pines binarios (SchLib)
def _pstr(b, i):
    n = b[i]
    return b[i + 1:i + 1 + n].decode("latin-1"), i + 1 + n


def pin_binario(c):
    """Pin binario de una SchLib → dict (posición en unidades de 10 mil)."""
    p = {"parte": int.from_bytes(c[5:7], "little", signed=True), "modo": c[7]}
    p["descripcion"], i = _pstr(c, 12)
    p["tipo_formal"], p["electrico"], p["conglomerado"] = c[i], c[i + 1], c[i + 2]
    i += 3
    p["largo"] = int.from_bytes(c[i:i + 2], "little", signed=True)
    p["x"] = int.from_bytes(c[i + 2:i + 4], "little", signed=True)
    p["y"] = int.from_bytes(c[i + 4:i + 6], "little", signed=True)
    i += 10  # color (4 bytes)
    p["nombre"], i = _pstr(c, i)
    p["designador"], i = _pstr(c, i)
    p["rotacion"] = p["conglomerado"] & 3
    p["oculto"] = bool(p["conglomerado"] & 0x04)
    return p


# ---------------------------------------------------------------- archivos
def leer_stream(ruta, stream):
    o = olefile.OleFileIO(str(ruta))
    try:
        return o.openstream(stream).read()
    finally:
        o.close()


def streams(ruta):
    o = olefile.OleFileIO(str(ruta))
    try:
        return ["/".join(e) for e in o.listdir()]
    finally:
        o.close()


def respaldo(ruta, etiqueta=""):
    RESPALDOS.mkdir(parents=True, exist_ok=True)
    ruta = Path(ruta)
    sello = datetime.now().strftime("%Y%m%d_%H%M%S")
    destino = RESPALDOS / f"{ruta.stem}_{sello}{('_' + etiqueta) if etiqueta else ''}{ruta.suffix}"
    n = 1
    while destino.exists():  # no pisar una copia hecha en el mismo segundo
        n += 1
        destino = destino.with_name(f"{ruta.stem}_{sello}_{n}{ruta.suffix}")
    shutil.copy2(ruta, destino)
    return destino


def escribir_streams(ruta, cambios):
    """cambios = {"ruta/del/stream": bytes}. Usa el almacenamiento estructurado de Windows."""
    import pythoncom
    from win32com import storagecon as sc

    modo = sc.STGM_READWRITE | sc.STGM_SHARE_EXCLUSIVE | sc.STGM_TRANSACTED
    raiz = pythoncom.StgOpenStorage(str(ruta), None, modo, None, 0)
    for nombre, data in cambios.items():
        partes = nombre.split("/")
        pila = [raiz]
        for sub in partes[:-1]:
            pila.append(pila[-1].OpenStorage(sub, None, modo, None, 0))
        st = pila[-1].OpenStream(partes[-1], None, sc.STGM_READWRITE | sc.STGM_SHARE_EXCLUSIVE, 0)
        st.SetSize(len(data))
        st.Seek(0, 0)
        st.Write(data)
        st.Commit(0)
        del st
        for s in reversed(pila[1:]):
            s.Commit(0)
        # soltar todas las referencias: si queda una (la variable del bucle), el mismo storage no se
        # puede volver a abrir para el siguiente stream (Access Denied)
        s = None
        del pila
    raiz.Commit(0)
    del raiz


def altium_abierto():
    import subprocess
    salida = subprocess.run(["tasklist", "/FI", "IMAGENAME eq X2.exe"], capture_output=True, text=True).stdout
    return "X2.exe" in salida
