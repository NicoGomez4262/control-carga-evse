# -*- coding: utf-8 -*-
"""F9: arma la BOM y el CPL para el ensamble de JLCPCB (30 oct 2026, D20) y revisa el stock.

- BOM → docs/fabricacion/BOM_JLC.csv (Comment, Designator, Footprint, JLCPCB Part #), una fila por línea de
  bom_f7.LINEAS con Assembly = JLCPCB. Comment = MPN; Footprint = el del PcbDoc.
- CPL → docs/fabricacion/CPL_JLC.csv (Designator, Mid X, Mid Y, Layer, Rotation) con las posiciones de
  PickPlace_PCBWay.csv (OutJob del 23 oct: centro de pads, origen en la esquina inferior izquierda, igual que
  los Gerber). La rotación es la de Altium: se revisa en el visor de JLC (Component Placements).
- Revisa que la BOM y el CPL tengan los mismos designadores.
- --stock: consulta el stock de JLC (API de su buscador) para N placas y estima el costo de las piezas y el
  cargo de US$ 3,07 por referencia «extendida» del ensamble Economic.

Uso: python docs/tools/paquete_jlc_f9.py [--stock] [--placas 2]
"""
import csv
import json
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bom_f7  # noqa: E402

RAIZ = Path(__file__).resolve().parents[2]
FAB = RAIZ / "docs" / "fabricacion"
PP = FAB / "PickPlace_PCBWay.csv"
API = "https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList"
CARGO_EXT = 3.07  # US$ por referencia extendida, ensamble Economic (jlcpcb.com/help/article/pcb-assembly-price)


def lineas_jlc():
    return [ln for ln in bom_f7.LINEAS if ln[5] == "JLCPCB"]


def posiciones():
    with open(PP, encoding="utf-8") as fh:
        return {f["Designator"]: f for f in csv.DictReader(fh)}


def escribir():
    pos = posiciones()
    bom, cpl = [], []
    for ln in lineas_jlc():
        des = ln[0].split(",")
        falta = [d for d in des if d not in pos]
        if falta:
            raise SystemExit(f"{falta} no están en {PP.name}")
        huellas = {pos[d]["Footprint"] for d in des}
        if len(huellas) != 1:
            raise SystemExit(f"{ln[0]}: footprints distintos {huellas}")
        bom.append([ln[2], ",".join(des), huellas.pop(), ln[4].split()[-1]])
        for d in des:
            f = pos[d]
            capa = {"TopLayer": "Top", "BottomLayer": "Bottom"}[f["Layer"]]
            cpl.append([d, f"{float(f['Center-X(mm)']):.4f}mm", f"{float(f['Center-Y(mm)']):.4f}mm", capa,
                        f"{float(f['Rotation']):g}"])
    sobran = set(pos) - {c[0] for c in cpl}
    if sobran:
        raise SystemExit(f"en el Pick & Place pero no en la BOM de JLC: {sorted(sobran)}")
    with open(FAB / "BOM_JLC.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Comment", "Designator", "Footprint", "JLCPCB Part #"])
        w.writerows(bom)
    with open(FAB / "CPL_JLC.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        w.writerows(sorted(cpl, key=lambda c: c[0]))
    print(f"BOM_JLC.csv: {len(bom)} líneas · CPL_JLC.csv: {len(cpl)} piezas (iguales a la BOM)")


def buscar(codigo):
    req = urllib.request.Request(API, data=json.dumps({"keyword": codigo, "currentPage": 1, "pageSize": 10}).encode(),
                                 headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
    d = json.load(urllib.request.urlopen(req, timeout=30))
    lista = (d.get("data") or {}).get("componentPageInfo", {}).get("list") or []
    return next((c for c in lista if c["componentCode"] == codigo), None)


def precio(c, q):
    p = None
    for t in c.get("componentPrices") or []:
        if t["startNumber"] <= q:
            p = t["productPrice"]
    return p or 0.0


def stock(placas):
    total, ext, malos = 0.0, 0, []
    print(f"{'designadores':32} {'código':10} {'tipo':6} {'stock':>8} {'pide':>4} {'US$':>7}")
    for ln in lineas_jlc():
        codigo = ln[4].split()[-1]
        q = len(ln[0].split(",")) * placas
        c = buscar(codigo)
        time.sleep(0.3)
        if c is None:
            malos.append(f"{ln[0]}: {codigo} no está en JLC")
            continue
        tipo = "basic" if c["componentLibraryType"] == "base" else "ext"
        ext += tipo == "ext"
        sub = precio(c, q) * q
        total += sub
        if c["stockCount"] < q:
            malos.append(f"{ln[0]}: {codigo} con {c['stockCount']} en stock y se piden {q}")
        print(f"{ln[0][:32]:32} {codigo:10} {tipo:6} {c['stockCount']:>8} {q:>4} {sub:>7.2f}")
    print(f"\n{placas} placas: piezas ≈ US$ {total:.2f} (sin merma) · {ext} extendidas × {CARGO_EXT} = "
          f"US$ {ext * CARGO_EXT:.2f}")
    print("\n".join(malos) if malos else "todo en stock")


if __name__ == "__main__":
    a = sys.argv[1:]
    escribir()
    if "--stock" in a:
        stock(int(a[a.index("--placas") + 1]) if "--placas" in a else 2)
