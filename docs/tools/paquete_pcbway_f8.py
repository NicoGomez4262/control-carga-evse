# -*- coding: utf-8 -*-
"""F8: arma el paquete para PCBWay con lo que genera el OutJob y lo revisa.

- Gerber + taladros → docs/fabricacion/EVSE_Monitor_Gerber.zip. Revisa que estén las 9 capas y los taladros
  (PTH y NPTH) y que no venga la capa Keep-Out.
- Pick & Place → docs/fabricacion/PickPlace_PCBWay.csv solo con lo que ensambla PCBWay (sin K1 y U1, que van a mano,
  ni F1B, F2B, SW2 y SW3, que no se montan), y la cantidad tiene que coincidir con la BOM. La columna Comment lleva
  el MPN de bom_f7.LINEAS, el mismo de la BOM (en la PCB TP1–TP6 dicen «5016» y la BOM, RH-5016).
- Plano de ensamble (PDF) y STEP: se copian.

Uso: python docs/tools/paquete_pcbway_f8.py
"""
import csv
import shutil
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bom_f7  # noqa: E402
import revisar_pcb as rv  # noqa: E402

RAIZ = Path(__file__).resolve().parents[2]
FAB = RAIZ / "docs" / "fabricacion"
# Altium dejó las salidas en la raíz de Project Outputs (no respetó la subcarpeta PCBWay del OutJob)
BASE = rv.PCB.parent / "Project Outputs for Control de Carga IoT"
NOMBRE = "EVSE_Monitor"
NO_ENSAMBLA = {"K1", "U1", "F1B", "F2B", "SW2", "SW3"}
GERBER = {".GTL": "Top Layer", ".GBL": "Bottom Layer", ".GTO": "Top Overlay", ".GBO": "Bottom Overlay",
          ".GTS": "Top Solder", ".GBS": "Bottom Solder", ".GTP": "Top Paste", ".GBP": "Bottom Paste",
          ".GM1": "Mechanical 1 (contorno)"}


def main():
    FAB.mkdir(parents=True, exist_ok=True)
    archivos = [p for p in BASE.iterdir() if p.is_file()]
    gerb = [p for p in archivos if (p.stem == NOMBRE and p.suffix.upper() in GERBER)
            or (p.stem.startswith(NOMBRE + "-") and p.suffix.upper() == ".TXT")]
    if not gerb:
        sys.exit(f"No hay salidas en {BASE}: genera el OutJob en Altium primero.")
    ext = {p.suffix.upper() for p in gerb}
    faltan = [f"{e} ({n})" for e, n in GERBER.items() if e not in ext]
    taladros = [p for p in gerb if p.suffix.upper() in (".TXT", ".DRL")]
    print("Gerber:", sorted(p.name for p in gerb))
    print("Faltan capas:", faltan or "ninguna", "| taladros:", [p.name for p in taladros])
    if any(p.suffix.upper() == ".GKO" for p in archivos):
        print("OJO: salió la capa Keep-Out (.GKO): no la mandes a PCBWay")
    with zipfile.ZipFile(FAB / "EVSE_Monitor_Gerber.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for p in gerb:
            if p.suffix.upper() != ".GKO":
                z.write(p, p.name)
    pp = next((p for p in archivos if p.suffix.lower() == ".csv" and "pick" in p.name.lower()), None)
    if pp:
        lineas = pp.read_text(encoding="latin-1").splitlines()
        i = next(k for k, l in enumerate(lineas) if l.strip('"').startswith("Designator"))
        filas = list(csv.reader(lineas[i:]))
        cab, datos = filas[0], [f for f in filas[1:] if f]
        quedan = [f for f in datos if f[0] not in NO_ENSAMBLA]
        mpn = {d: ln[2] for d, ln in bom_f7.lineas_por_designador().items()}
        for f in quedan:
            f[cab.index("Comment")] = mpn[f[0]]
        with open(FAB / "PickPlace_PCBWay.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(cab)
            w.writerows(quedan)
        capas = {f[cab.index("Layer")] for f in quedan} if "Layer" in cab else set()
        print(f"Pick & Place: {len(datos)} piezas, {len(quedan)} para PCBWay (capas {capas})")
    else:
        print("No encontré el Pick & Place (CSV)")
    for p in archivos:
        if p.suffix.lower() in (".step", ".stp") or (p.suffix.lower() == ".pdf" and p.stem.startswith("Ensamble")):
            shutil.copy2(p, FAB / p.name)
            print("Copiado:", p.name)
    print("Paquete en", FAB)


if __name__ == "__main__":
    main()
