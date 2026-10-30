# -*- coding: utf-8 -*-
"""F9: pone en Altium los cambios de la BOM para JLCPCB (30 oct 2026, D20; Altium CERRADO).

Usa la maquinaria de bom_f7 con su propia lista de piezas nuevas:
- K1: AQY214EHAX (NA) en lugar de AQY-414EHAX (el AQY414EHAX está en 0 en JLC);
- 11 líneas genéricas pasan a piezas Basic de JLC (mismo valor y encapsulado).
Cada pieza nueva se crea en lib/SamacSys.SchLib copiando la que reemplaza (mismo símbolo y footprint), la vieja
se borra y las hojas apuntan a la nueva. Además, en todas las piezas quedan los cinco parámetros de la BOM
(Supplier y Assembly = JLCPCB). El PcbDoc no se toca: el Gerber del 23 oct sigue valiendo.

Uso: python docs/tools/bom_jlc_f9.py --probar <carpeta>   (trabaja en una copia)
     python docs/tools/bom_jlc_f9.py --todo               (en el proyecto, con respaldo)
"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bom_f7  # noqa: E402

# pieza nueva → (pieza que reemplaza, parámetros propios)
NUEVAS = {
    "AQY214EHAX": ("AQY-414EHAX", {"Value": "PhotoMOS NA",
                   "Description": "PhotoMOS 1 Form A (NO), 400 V 120 mA, reinforced insulation 5000 Vrms, SMD DIP-4"}),
    "0805W8F1001T5E": ("RC0805FR-071KL", {"Description": "Resistor 1 kOhm 1% 125 mW 0805"}),
    "0805W8F1002T5E": ("RC0805FR-0710KL", {"Description": "Resistor 10 kOhm 1% 125 mW 0805"}),
    "0805W8F1202T5E": ("RC0805FR-0712KL", {"Description": "Resistor 12 kOhm 1% 125 mW 0805"}),
    "0805W8F4701T5E": ("RC0805FR-074K7L", {"Description": "Resistor 4.7 kOhm 1% 125 mW 0805"}),
    "0805W8F5101T5E": ("RC0805FR-075K1L", {"Description": "Resistor 5.1 kOhm 1% 125 mW 0805"}),
    "0805W8F1000T5E": ("RC0805FR-07100RL", {"Description": "Resistor 100 Ohm 1% 125 mW 0805"}),
    "0805W8F3300T5E": ("RC0805FR-07330RL", {"Description": "Resistor 330 Ohm 1% 125 mW 0805"}),
    "0805W8F4702T5E": ("RC0805FR-0747KL", {"Description": "Resistor 47 kOhm 1% 125 mW 0805"}),
    "CC0805KRX7R9BB104": ("CL21B104KBCNNNC", {"Description": "Capacitor 100 nF 50 V X7R 10% 0805"}),
    "CL21B105KBFNNNE": ("CL21B105KAFNNNE", {"Value": "1uF 50V X7R", "Description": "Capacitor 1 uF 50 V X7R 10% 0805"}),
    "MMBT3904": ("MMBT3904LT1G", {"Description": "Transistor BJT NPN 40 V 200 mA, SOT-23"}),
}


if __name__ == "__main__":
    bom_f7.NUEVAS = NUEVAS
    a = sys.argv[1:]
    if "--probar" in a:
        destino = Path(a[a.index("--probar") + 1])
        (destino / "lib").mkdir(parents=True, exist_ok=True)
        for n in bom_f7.HOJAS:
            shutil.copy2(bom_f7.PROY / f"{n}.SchDoc", destino / f"{n}.SchDoc")
        for ext in ("SchLib", "PcbLib"):
            shutil.copy2(bom_f7.PROY / "lib" / f"SamacSys.{ext}", destino / "lib" / f"SamacSys.{ext}")
        bom_f7.main(destino, True)
    elif "--todo" in a:
        bom_f7.main(bom_f7.PROY, False)
    else:
        sys.exit(__doc__)
