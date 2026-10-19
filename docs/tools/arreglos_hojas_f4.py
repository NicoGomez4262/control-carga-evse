# -*- coding: utf-8 -*-
"""Arreglos de hojas al inicio de F4, después del Update From Libraries (Altium CERRADO).

- TP1–TP6: el Update From Libraries (Full replacement) borró los 6 parámetros → se vuelven a poner.
- 03_MEDICION: había dos puertos MEAS_CS (U3 pin 24 y pull-up R18) → error «multiple Input ports».
  El del lado de R18 pasa a ser una net label MEAS_CS en la esquina del cable de R18.

Uso: python docs/tools/arreglos_hojas_f4.py "<carpeta del proyecto>"
"""
import sys
from pathlib import Path

from hoja import Hoja
import pendientes_f3 as pf

carpeta = Path(sys.argv[1])
h2 = Hoja(carpeta / "02_ALIMENTACION.SchDoc")
pf.a8(h2)
h3 = Hoja(carpeta / "03_MEDICION.SchDoc")
pf.a8(h3)
puertos = h3.buscar(RECORD="18", Name="MEAS_CS")
if len(puertos) == 2:
    i = max(puertos, key=lambda k: -h3.xy(k)[1])  # el de más abajo (R18)
    i = min(puertos, key=lambda k: h3.xy(k)[1])
    c = pf.cable_que_empieza(h3, (9400, 600))
    h3.trazo(c, [(9300, 600), (9300, 900)])
    uid, idx = h3.v(i, "UniqueID"), h3.v(i, "IndexInSheet")
    h3.r[i] = [("RECORD", "25"), ("IndexInSheet", idx), ("OwnerPartId", "-1"), ("Location.X", "930"),
               ("Location.Y", "60"), ("Color", "128"), ("FontID", "1"), ("Text", "MEAS_CS"), ("UniqueID", uid)]
    h3._nota(i, "puerto MEAS_CS de R18 → net label en (9300, 600); cable recortado")
for h in (h2, h3):
    print("==", h.ruta.name)
    for n in h.cambios:
        print("  ", n)
    print("   copia:", h.guardar("antes_arreglos_f4"))
