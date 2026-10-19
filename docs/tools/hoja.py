# -*- coding: utf-8 -*-
"""Edición de un .SchDoc de Altium registro por registro (Altium CERRADO).

Los registros se numeran como en Altium (OwnerIndex): 0 es el primero después de la cabecera.
Las coordenadas que reciben y devuelven estas funciones están en mil; el archivo guarda
unidades de 10 mil (Location.X=111 → 1110 mil).

    h = Hoja(ruta)
    i = h.buscar(RECORD="25", Text="+3V3")          # índices de registros
    h.mover(i[0], 1200, 3400)                      # Location en mil
    h.insertar(pos, [("RECORD", "41"), ...])        # corrige los OwnerIndex corridos
    h.guardar()                                    # copia en docs/respaldos/ y escribe
"""
import altium_ole as ao


class Hoja:
    def __init__(self, ruta):
        self.ruta = ruta
        regs = ao.leer_registros(ao.leer_stream(ruta, "FileHeader"))
        self.cabecera = regs[0]
        self.r = [ao.campos(c) for _, c in regs[1:]]
        self.cambios = []

    # ------------------------------------------------------------ consulta
    def v(self, i, clave, defecto=None):
        return ao.valor(self.r[i], clave, defecto)

    def buscar(self, **cond):
        out = []
        for i, f in enumerate(self.r):
            if all(ao.valor(f, k.replace("_", "."), None) == val for k, val in cond.items()):
                out.append(i)
        return out

    def por_uid(self, uid):
        i = self.buscar(UniqueID=uid)
        if len(i) != 1:
            raise SystemExit(f"UniqueID {uid}: {len(i)} registros")
        return i[0]

    def hijos(self, i):
        return [j for j, f in enumerate(self.r) if ao.valor(f, "OwnerIndex") == str(i)]

    def uids(self):
        return {ao.valor(f, "UniqueID") for f in self.r if ao.valor(f, "UniqueID")}

    def max_index_in_sheet(self):
        vals = [int(ao.valor(f, "IndexInSheet")) for f in self.r
                if ao.valor(f, "OwnerIndex") is None and (ao.valor(f, "IndexInSheet") or "").lstrip("-").isdigit()]
        return max(vals or [0])

    @staticmethod
    def mil(f, clave):
        return int(ao.valor(f, clave, 0) or 0) * 10 + int(ao.valor(f, clave + "_Frac", 0) or 0) / 10000.0

    def xy(self, i):
        return self.mil(self.r[i], "Location.X"), self.mil(self.r[i], "Location.Y")

    def puntos(self, i):
        n = int(self.v(i, "LocationCount", 0))
        return [(self.mil(self.r[i], f"X{k}"), self.mil(self.r[i], f"Y{k}")) for k in range(1, n + 1)]

    # ------------------------------------------------------------ cambios
    def _nota(self, i, texto):
        self.cambios.append(f"[{i}] {texto}")

    @staticmethod
    def _u(mil):
        if mil % 10:
            raise ValueError(f"{mil} mil no cae en la rejilla de 10 mil")
        return str(int(mil // 10))

    def poner(self, i, **kv):
        f = self.r[i]
        for k, val in kv.items():
            k = k.replace("_", ".")
            if val is None:
                f = ao.quitar(f, k)
            else:
                f = ao.poner(f, k, str(val), antes_de="UniqueID")
        self.r[i] = f

    def mover(self, i, x, y):
        f = ao.quitar(ao.quitar(self.r[i], "Location.X_Frac"), "Location.Y_Frac")
        f = ao.poner(f, "Location.X", self._u(x), antes_de="UniqueID")
        f = ao.poner(f, "Location.Y", self._u(y), antes_de="UniqueID")
        self.r[i] = f

    def trazo(self, i, pts):
        """Reemplaza los vértices de un cable (o polígono) por `pts` en mil."""
        f = [(k, v) for k, v in self.r[i]
             if not (k[:1] in "XY" and k[1:].split("_")[0].isdigit())]
        pos = next(n for n, (k, _) in enumerate(f) if k == "LocationCount")
        f[pos] = ("LocationCount", str(len(pts)))
        nuevos = []
        for n, (x, y) in enumerate(pts, 1):
            nuevos += [(f"X{n}", self._u(x)), (f"Y{n}", self._u(y))]
        self.r[i] = f[:pos + 1] + nuevos + f[pos + 1:]

    def insertar(self, pos, f):
        for j, g in enumerate(self.r):
            oi = ao.valor(g, "OwnerIndex")
            if oi is not None and int(oi) >= pos:
                self.r[j] = ao.poner(g, "OwnerIndex", str(int(oi) + 1))
        self.r.insert(pos, f)
        return pos

    def agregar(self, f):
        self.r.append(f)
        return len(self.r) - 1

    def borrar(self, i):
        if self.hijos(i):
            raise SystemExit(f"[{i}] tiene registros hijos; no se borra")
        del self.r[i]
        for j, g in enumerate(self.r):
            oi = ao.valor(g, "OwnerIndex")
            if oi is not None and int(oi) > i:
                self.r[j] = ao.poner(g, "OwnerIndex", str(int(oi) - 1))

    def datos(self):
        """FileHeader con «Weight» = número de registros (Altium lo usa para leer el archivo)."""
        cab = ao.poner(ao.campos(self.cabecera[1]), "Weight", str(len(self.r)), antes_de="MinorVersion")
        return ao.unir_registros([(self.cabecera[0], ao.cuerpo(cab))] + [(0, ao.cuerpo(f)) for f in self.r])

    # ------------------------------------------------------------ stream Additional (Blankets)
    def leer_adicional(self):
        regs = ao.leer_registros(ao.leer_stream(self.ruta, "Additional"))
        self.ad_cab = regs[0]
        self.ad = [ao.campos(c) for _, c in regs[1:]]
        return self.ad

    def datos_adicional(self):
        cab = ao.poner(ao.campos(self.ad_cab[1]), "Weight", str(len(self.ad)))
        return ao.unir_registros([(self.ad_cab[0], ao.cuerpo(cab))] + [(0, ao.cuerpo(f)) for f in self.ad])

    def guardar(self, etiqueta=""):
        if ao.altium_abierto():
            raise SystemExit("Altium está abierto: ciérralo antes de escribir la hoja.")
        copia = ao.respaldo(self.ruta, etiqueta)
        cambios = {"FileHeader": self.datos()}
        if hasattr(self, "ad"):
            cambios["Additional"] = self.datos_adicional()
        ao.escribir_streams(self.ruta, cambios)
        return copia
