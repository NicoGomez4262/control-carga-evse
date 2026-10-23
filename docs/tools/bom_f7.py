# -*- coding: utf-8 -*-
"""F7: BOM con la regla de compras D16 (19 oct 2026, Altium CERRADO).

La lista LINEAS es la fuente única de la BOM: designadores, fabricante, MPN, proveedor, PN del
proveedor, montaje, precio (US$, cantidad 1) y nota. Con ella el script:

1. lib/SamacSys.SchLib: crea por copia las piezas que cambian de número de parte (mismo símbolo y
   footprint que la pieza que reemplazan), borra las reemplazadas, pone Manufacturer_Name,
   Manufacturer_Part_Number, Supplier, Supplier PN y Assembly en todas y quita los campos de Mouser,
   Arrow y RS (D16: Mouser ya no se usa). Una sola escritura, con respaldo.
2. Hojas 02–06: las piezas que cambian apuntan a la pieza nueva (LibReference, descripción, Comment y
   parámetros de la librería); en todos los componentes se ponen los cinco parámetros de la BOM por
   designador (SW2/SW3 y F1B/F2B quedan DNP) y se quitan los campos de Mouser, Arrow y RS.
3. --md escribe docs/BOM_F7.md (la tabla para leer). No toca Altium.
4. --hojas repite solo el paso 2 (la librería ya tiene las piezas nuevas): sirve cuando cambia una pieza que
   vive solo en la hoja (TP, J5). Guarda solo las hojas que cambian, con respaldo.

Uso: python docs/tools/bom_f7.py --md | --hojas | --probar <carpeta> | --todo (pasos 1 y 2 en el proyecto)
     --probar copia la librería y las hojas a <carpeta> y trabaja ahí (no toca el proyecto).
"""
import re
import shutil
import sys
from pathlib import Path

import altium_ole as ao
import libreria as L
from arreglos_hojas_f7 import comp, desig, texto
from hoja import Hoja
from ronda2_f4 import params_lib, sincronizar

PROY = Path("C:/Nicolas/UNIVERSIDAD - 2026/Hardware en IoT/Control de Carga IoT/Control de Carga IoT")
HOJAS = ["02_ALIMENTACION", "03_MEDICION", "04_MCU", "05_SENSORES", "06_ACTUACION"]
QUITAR = ["Mouser Part Number", "Mouser Price/Stock", "Arrow Part Number", "Arrow Price/Stock", "RS Price/Stock"]
TRM = 3174.67  # COP/USD, 19 oct 2026 (dolarhoy.co)

# (designadores, fabricante, MPN, proveedor, PN del proveedor, montaje, US$ c/u, nota)
LINEAS = [
    # A · PCBWay turnkey, stock en LCSC
    ("BT1", "TE Connectivity", "BAT-HLD-001", "PCBWay", "LCSC C7501066", "PCBWay", 1.1381, ""),
    ("C1,C9,C11,C15,C17,C31", "KEMET", "C0805C102J5GACTU", "PCBWay", "LCSC C2167084", "PCBWay", 0.0294, ""),
    ("C2", "Panasonic", "EEE-FK1V101P", "PCBWay", "LCSC C128462", "PCBWay", 0.4394, ""),
    ("C3", "Panasonic", "EEE-FK1C101P", "PCBWay", "LCSC C128532", "PCBWay", 0.2762, ""),
    ("C4,C5,C33", "Samsung Electro-Mechanics", "CL21A226MAQNNNE", "PCBWay", "LCSC C45783", "PCBWay", 0.194, ""),
    ("C6", "Samsung Electro-Mechanics", "CL31B106KBHNNNE", "PCBWay", "LCSC C89632", "PCBWay", 0.2837, ""),
    ("C7,C8,C18,C21,C24,C37", "Samsung Electro-Mechanics", "CL21A106KAYNNNE", "PCBWay", "LCSC C15850", "PCBWay", 0.0874, ""),
    ("C10,C14,C30,C32", "Samsung Electro-Mechanics", "CL21B105KAFNNNE", "PCBWay", "LCSC C116352", "PCBWay", 0.0405, ""),
    ("C12,C13,C25,C28,C29,C34,C35,C36,C38,C39,C40", "Samsung Electro-Mechanics", "CL21B104KBCNNNC", "PCBWay",
     "LCSC C1711", "PCBWay", 0.0144, ""),
    ("C16", "Murata", "GRM31C5C1H104JA01L", "PCBWay", "LCSC C97946", "PCBWay", 0.3801,
     "cambio: el TDK C3216NP01H104J160AA está en 0"),
    ("C19,C22", "KEMET", "C0805C472J5GACTU", "PCBWay", "LCSC C2170898", "PCBWay", 0.0592, ""),
    ("C20,C23", "Murata", "GRM3195C1H333JA01D", "PCBWay", "LCSC C97930", "PCBWay", 0.1333,
     "cambio: el KEMET C1206C333J5GACTU no está en LCSC"),
    ("C26,C27", "KEMET", "C0805C120J5GACTU", "PCBWay", "LCSC C2168859", "PCBWay", 0.0188, ""),
    ("D1,D2", "Vishay", "SS34-E3/57T", "PCBWay", "LCSC C13354", "PCBWay", 0.2788, ""),
    ("D3", "Littelfuse", "SMBJ15A", "PCBWay", "LCSC C83846", "PCBWay", 0.1473, "la librería decía Vishay"),
    ("D4", "Littelfuse", "SMAJ5.0CA", "PCBWay", "LCSC C83324", "PCBWay", 0.1117, ""),
    ("D5,D6", "STMicroelectronics", "USBLC6-2SC6", "PCBWay", "LCSC C7519", "PCBWay", 0.1774, ""),
    ("F1,F2", "Schurter", "3403.0274.11", "PCBWay", "LCSC C6384960", "PCBWay", 2.572,
     "Please buy 2 extra pcs (4 total) and ship the 2 spares loose with the boards"),
    ("FB1", "Murata", "BLM21PG221SN1D", "PCBWay", "LCSC C85840", "PCBWay", 0.0345, ""),
    ("J1,J2", "Xinlaiya", "XY301V-A-5.0-2P", "PCBWay", "LCSC C557651", "PCBWay", 0.1141,
     "cambio: TB001-500-02BE sin stock; 300 V 15 A, pin de 1,0 mm, mismo footprint (THT)"),
    ("J3", "Same Sky", "SJ1-3515-SMT-TR", "PCBWay", "LCSC C22359767", "PCBWay", 1.8745, "antes Sigma"),
    ("J4", "Phoenix Contact", "1751251", "PCBWay", "LCSC C91152", "PCBWay", 1.3422, "antes Sigma (THT)"),
    ("J5", "Wurth Elektronik", "632723300011", "PCBWay", "LCSC C2830802", "PCBWay", 6.4413,
     "antes Mouser; DigiKey 732-9618-1-ND a US$ 4,37"),
    ("J6,J7", "Phoenix Contact", "1751248", "PCBWay", "LCSC C89122", "PCBWay", 0.9666, "antes Sigma (THT)"),
    ("J8", "Wurth Elektronik", "61300611121", "PCBWay", "LCSC C5444523", "PCBWay", 0.4703, "antes Sigma (THT)"),
    ("L1", "Murata", "LQH43NH120J03L", "PCBWay", "LCSC C3224514", "PCBWay", 0.2911,
     "cambio: RECOM RLS-126 sin stock en LCSC; 12 uH, 0,25 ohm, 420 mA, AEC-Q200"),
    ("L2", "Bourns", "SRR4028-2R2Y", "PCBWay", "LCSC C2041777", "PCBWay", 1.0728, ""),
    ("LED1,LED2,LED3,LED4", "Kingbright", "APT2012SGC", "PCBWay", "LCSC C5353439", "PCBWay", 0.125, ""),
    ("LED5", "Kingbright", "APT2012SURCK", "PCBWay", "LCSC C5875730", "PCBWay", 0.1254, ""),
    ("LED6", "Hubei KENTO Electronic", "KT-0805Y", "PCBWay", "LCSC C2296", "PCBWay", 0.0146, ""),
    ("PS1", "Mean Well", "IRM-20-12", "PCBWay", "LCSC C5278499", "PCBWay", 6.3695,
     "antes Sigma, 71.400 COP (THT)"),
    ("Q1,Q2", "onsemi", "MMBT3904LT1G", "PCBWay", "LCSC C81464", "PCBWay", 0.0164, ""),
    ("Q3", "Alpha & Omega Semiconductor", "AO3400A", "PCBWay", "LCSC C20917", "PCBWay", 0.0972, ""),
    ("R1,R8,R15,R17,R25,R26,R28,R29,R30,R31,R39,R41", "Yageo", "RC0805FR-071KL", "PCBWay", "LCSC C95781",
     "PCBWay", 0.0037, ""),
    ("R2,R3,R4,R5", "Panasonic", "ERJ-P08F1004V", "PCBWay", "LCSC C41369755", "PCBWay", 0.0319, ""),
    ("R6", "Panasonic", "ERA-6AEB103V", "PCBWay", "LCSC C191101", "PCBWay", 0.0918, ""),
    ("R7", "Yageo", "RC0805FR-0747KL", "PCBWay", "LCSC C126351", "PCBWay", 0.0075, ""),
    ("R9,R12", "Panasonic", "ERA-6AEB203V", "PCBWay", "LCSC C473304", "PCBWay", 0.1204, ""),
    ("R10,R14", "Panasonic", "ERA-6AEB133V", "PCBWay", "LCSC C445658", "PCBWay", 0.0833, ""),
    ("R11,R13", "Yageo", "RT0805BRD0710RL", "PCBWay", "LCSC C865142", "PCBWay", 0.1015,
     "cambio: ERA-6AHD100V en 0 en LCSC; 0,1 % y 25 ppm (mejor)"),
    ("R16,R18,R22,R27,R34,R40", "Yageo", "RC0805FR-0710KL", "PCBWay", "LCSC C84376", "PCBWay", 0.0053, ""),
    ("R19,R20", "Yageo", "RC0805FR-0712KL", "PCBWay", "LCSC C114556", "PCBWay", 0.0069, ""),
    ("R21,R32,R33,R35", "Yageo", "RC0805FR-074K7L", "PCBWay", "LCSC C60816", "PCBWay", 0.0072, ""),
    ("R23,R24", "Yageo", "RC0805FR-075K1L", "PCBWay", "LCSC C84375", "PCBWay", 0.0072, ""),
    ("R36", "Yageo", "RC0805FR-07100RL", "PCBWay", "LCSC C105577", "PCBWay", 0.0044, ""),
    ("R37", "Yageo", "RC1206FR-0768RL", "PCBWay", "LCSC C137238", "PCBWay", 0.0092, ""),
    ("R38", "Yageo", "RC0805FR-07330RL", "PCBWay", "LCSC C105878", "PCBWay", 0.006, ""),
    ("RV1", "Ruilon", "RL4032P471KJ", "PCBWay", "LCSC C2935514", "PCBWay", 0.2595,
     "cambio: TDK B72660M0301K072 sin stock en LCSC; 300 VAC, 2500 A, 30 J, mismos pads"),
    ("SW1", "XKB Connectivity", "TS-1187A-B-A-B", "PCBWay", "LCSC C318884", "PCBWay", 0.0206, ""),
    ("TP1,TP2,TP3,TP4,TP5,TP6", "ronghe", "RH-5016", "PCBWay", "LCSC C5199799", "PCBWay", 0.0926,
     "cambio (22 oct): el Keystone 5016 está en 0 en LCSC; el RH-5016 es el mismo plano (3,81 × 2,84 mm)"),
    ("U2", "Texas Instruments", "AMC3330DWER", "PCBWay", "LCSC C2999368", "PCBWay", 5.0242,
     "cambio de MPN: DWE (tubo) en 0; DWER es la misma pieza en carrete"),
    ("U3", "Microchip", "ATM90E26-YU-R", "PCBWay", "LCSC C616398", "PCBWay", 2.232, ""),
    ("U4", "Espressif Systems", "ESP32-S3-WROOM-1-N16R2", "PCBWay", "LCSC C2913205", "PCBWay", 5.2673, "antes Mouser"),
    ("U5", "WCH", "CH340C", "PCBWay", "LCSC C84681", "PCBWay", 0.5438, ""),
    ("U6", "Aosong", "AHT20", "PCBWay", "LCSC C2757850", "PCBWay", 0.7968, ""),
    ("U7", "Analog Devices", "DS3231SN#T&R", "PCBWay", "LCSC C9866", "PCBWay", 9.9329, ""),
    ("Y1", "ECS", "ECS-81.92-12-30Q-EN-TR", "PCBWay", "LCSC C2450755", "PCBWay", 1.7128, ""),
    # 23 oct: sin pedido de DigiKey (nadie más del curso pidió). PCBWay lo compra en DigiKey/Mouser y lo suelda
    ("K1", "Panasonic", "AQY414EHAX", "PCBWay", "DigiKey 255-6089-1-ND", "PCBWay", 3.29,
     "Not in LCSC stock: please buy from DigiKey 255-6089-1-ND or Mouser 769-AQY414EHAX. No substitutes"),
    # C · ya disponible, a mano
    ("U1", "RECOM Power", "R-78CK3.3-0.5", "Disponible", "-", "Manual", 0.0,
     "la del profesor; otra: DigiKey 945-R-78CK3.3-0.5-ND, US$ 3,57"),
    # D · no se monta
    ("F1B,F2B", "XC Electronics", "BLX-A", "Sigma", "BLX-A", "DNP", 0.0, "solo si se funde un UMT-H (LCSC C3131)"),
    ("SW2,SW3", "XKB Connectivity", "TS-1187A-B-A-B", "PCBWay", "LCSC C318884", "DNP", 0.0, "RESET y BOOT"),
]
# fuera de la PCB: (pieza, fabricante, referencia, proveedor, COP, por qué no DigiKey)
FUERA = [
    ("CT de J3", "YHDC", "SCT-013-000V", "Sigma", 35700, "Seeed 101990029 sin stock (llega el 18 de diciembre)"),
    ("Sonda de J4", "genérica", "SEN DS18B20 2M", "Sigma", 11900, "DFR0198 cuesta US$ 6,90"),
    ("Pila de BT1", "—", "CR2032", "Sigma", 3213, "11-CR2032-ND solo se envía por tierra"),
]

# piezas nuevas en la librería: nombre → (pieza que reemplaza, parámetros propios)
NUEVAS = {
    "GRM31C5C1H104JA01L": ("C3216NP01H104J160AA", {"Value": "100nF 50V C0G",
                           "Description": "Capacitor ceramico 100 nF 50 V C0G 5% 1206"}),
    "GRM3195C1H333JA01D": ("C1206C333J5GACTU", {"Value": "33nF 50V C0G",
                           "Description": "Capacitor ceramico 33 nF 50 V C0G 5% 1206"}),
    "RT0805BRD0710RL": ("ERA-6AHD100V", {"Value": "10R 0.1%",
                        "Description": "Resistencia de pelicula delgada 10 ohm 0.1% 25 ppm 0805"}),
    "XY301V-A-5.0-2P": ("TB001-500-02BE", {"Value": "2P 5.0mm 300V",
                        "Description": "Bornera de tornillo 2 polos, paso 5.0 mm, 300 V 15 A, 22-14 AWG"}),
    "LQH43NH120J03L": ("RLS-126", {"Value": "12uH",
                       "Description": "Inductor 12 uH 5% 420 mA 0.25 ohm 1812, AEC-Q200"}),
    "RL4032P471KJ": ("B72660M0301K072", {"Value": "300VAC",
                     "Description": "Varistor SMD 300 VAC, 470 V, 2500 A (8/20 us), 30 J, 4032"}),
    "AMC3330DWER": ("AMC3330DWE", {"Description": "Amplificador aislado +-1 V con DC/DC integrado, "
                                                  "aislamiento reforzado, SOIC-16 DWE (carrete)"}),
    "3403.0274.11": ("3403.0274.23", {"Description": "Fusible SMD UMT-H T1A 277 VAC, ruptura 1500 A (bolsa)"}),
}


def lineas_por_designador():
    out = {}
    for ln in LINEAS:
        for d in ln[0].split(","):
            out[d] = ln
    return out


def cinco(ln):
    _, fab, mpn, sup, spn, asm, _, _ = ln
    return {"Manufacturer_Name": fab, "Manufacturer_Part_Number": mpn, "Supplier": sup,
            "Supplier PN": spn, "Assembly": asm}


# ---------------------------------------------------------------- librería
def piezas_de_hojas(carpeta):
    """{designador: LibReference} de las hojas 02–06."""
    out = {}
    for n in HOJAS:
        h = Hoja(str(carpeta / f"{n}.SchDoc"))
        for c in h.buscar(RECORD="1"):
            out[desig(h, c)] = h.v(c, "LibReference")
    return out


def plan_libreria(ps, lib_de):
    """{pieza: parámetros} para la librería después del cambio (pieza nueva si reemplaza a otra)."""
    reemplazo = {orig: nueva for nueva, (orig, _) in NUEVAS.items()}
    por_d = lineas_por_designador()
    plan = {}
    for d, lib in lib_de.items():
        lib = reemplazo.get(lib, lib)
        if lib not in ps and lib not in NUEVAS:
            continue  # pieza del Content Vault (J5, TP): solo en la hoja
        ln = por_d[d]
        if ln[5] == "DNP" and lib in plan:
            continue  # SW2/SW3 comparten pieza con SW1: la librería lleva el montaje de SW1
        plan[lib] = cinco(ln)
    return plan


def regs_copia(ps, origen, nueva, cambios, usados):
    """Registros de una pieza nueva con el símbolo y el footprint de `origen` (como libreria.copiar)."""
    regs = L.quitar_params(ps[origen]["regs"], L.DE_SAMACSYS + QUITAR)
    comp_ = ao.campos(regs[0][1])
    for k in ("LibReference", "DesignItemId"):
        comp_ = ao.poner(comp_, k, nueva)
    regs[0] = (0, ao.cuerpo(comp_))
    regs = L.poner_params(regs, dict({"Comment": nueva}, **cambios), usados)
    for n, (t, c) in enumerate(regs):
        if t == 0:
            f = ao.campos(c)
            if ao.valor(f, "UniqueID"):
                regs[n] = (0, ao.cuerpo(ao.poner(f, "UniqueID", ao.uid(usados))))
    return regs


def reescribir_libreria(ruta, lib_de, probar):
    import pythoncom
    from win32com import storagecon as sc

    ps = L.piezas(ruta)
    plan = plan_libreria(ps, lib_de)
    usados = L.usados_en(ps)
    borrar = [orig for orig, _ in NUEVAS.values()]
    datos = {}
    for nom in ps:
        if nom in borrar:
            continue
        regs = L.quitar_params(ps[nom]["regs"], QUITAR)
        if nom in plan:
            regs = L.poner_params(regs, plan[nom], usados)
        datos[nom] = regs
    for nueva, (orig, propios) in NUEVAS.items():
        datos[nueva] = regs_copia(ps, orig, nueva, dict(plan[nueva], **propios), usados)

    fh = ao.leer_stream(ruta, "FileHeader")
    tipo, cab_c = ao.leer_registros(fh)[0]
    cab = ao.campos(cab_c)
    n = int(ao.valor(cab, "CompCount"))
    info = {ao.valor(cab, f"LibRef{i}"): (ao.valor(cab, f"CompDescr{i}", ""), ao.valor(cab, f"PartCount{i}", "1"))
            for i in range(n)}
    for nueva, (orig, propios) in NUEVAS.items():
        info[nueva] = (propios["Description"], info[orig][1])
    base = [kv for kv in cab if not re.match(r"(LibRef|CompDescr|PartCount)\d+$", kv[0])]
    pos = next(k for k, (c, _) in enumerate(base) if c == "CompCount")
    lista = []
    for i, nom in enumerate(datos):
        d, pc = info[nom]
        lista += [(f"LibRef{i}", nom), (f"CompDescr{i}", d), (f"PartCount{i}", pc)]
    cab = base[:pos + 1] + lista + base[pos + 1:]
    cab = ao.poner(cab, "CompCount", str(len(datos)))
    cab = ao.poner(cab, "Weight", str(sum(len(r) for r in datos.values())))
    nueva_cab = ao.unir_registros([(tipo, ao.cuerpo(cab))]) + fh[4 + len(cab_c):]

    if ao.altium_abierto():
        raise SystemExit("Altium está abierto: ciérralo antes de correr el script.")
    print(f"== {Path(ruta).name} (respaldo: {'—' if probar else ao.respaldo(ruta, 'antes_bom_f7')})")
    rw = sc.STGM_READWRITE | sc.STGM_SHARE_EXCLUSIVE
    raiz = pythoncom.StgOpenStorage(str(ruta), None, rw | sc.STGM_TRANSACTED, None, 0)
    for nom in borrar:
        raiz.DestroyElement(ps[nom]["stream"].split("/")[0])
    for nom, regs in datos.items():
        data = ao.unir_registros(regs)
        if nom in NUEVAS:
            sub = raiz.CreateStorage(nom, rw | sc.STGM_CREATE, 0, 0)
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
    for nueva, (orig, _) in NUEVAS.items():
        print(f"   pieza nueva {nueva} (copia de {orig}, que se borra)")
    print(f"   {len(plan)} piezas con Manufacturer_Name, MPN, Supplier, Supplier PN y Assembly de la BOM; "
          f"sin campos de Mouser/Arrow/RS; quedan {len(datos)} piezas")


# ---------------------------------------------------------------- hojas
def arreglar_hoja(h, ps):
    reemplazo = {orig: nueva for nueva, (orig, _) in NUEVAS.items()}
    por_d = lineas_por_designador()
    usados = h.uids()
    for uid in [h.v(c, "UniqueID") for c in h.buscar(RECORD="1")]:
        c = h.por_uid(uid)
        d = desig(h, c)
        ln = por_d.get(d)
        if ln is None:
            raise SystemExit(f"{d} no está en la BOM")
        vieja = h.v(c, "LibReference")
        if vieja in reemplazo:
            nueva = reemplazo[vieja]
            h.poner(c, LibReference=nueva, DesignItemId=nueva)
            texto(h, c, "ComponentDescription", ao.valor(L.resumen(ps[nueva]["regs"])[0], "ComponentDescription"))
            sincronizar(h, c, params_lib(ps, nueva), usados, borrar_resto=True)
            c = h.por_uid(uid)
            com = next(j for j in h.hijos(c) if h.v(j, "Name") == "Comment")
            h.poner(com, Text=nueva)
            h._nota(c, f"{d}: {vieja} → {nueva}")
        for j in sorted([j for j in h.hijos(c) if h.v(j, "RECORD") == "41" and h.v(j, "Name") in QUITAR],
                        reverse=True):
            h.borrar(j)
        c = h.por_uid(uid)
        antes = {h.v(j, "Name"): h.v(j, "Text") for j in h.hijos(c) if h.v(j, "RECORD") == "41"}
        sincronizar(h, c, cinco(ln), usados)
        cambio = [f"{k}: «{antes.get(k, '')}» → «{v}»" for k, v in cinco(ln).items() if antes.get(k) != v]
        if cambio:
            h._nota(c, f"{d}: " + "; ".join(cambio))


def main(carpeta, probar):
    if ao.altium_abierto():
        raise SystemExit("Altium está abierto: ciérralo antes de correr el script.")
    lib = carpeta / "lib" / "SamacSys.SchLib"
    lib_de = piezas_de_hojas(carpeta)
    falta = set(lib_de) - set(lineas_por_designador())
    sobra = set(lineas_por_designador()) - set(lib_de)
    if falta or sobra:
        raise SystemExit(f"la BOM no coincide con las hojas: faltan {sorted(falta)}, sobran {sorted(sobra)}")
    reescribir_libreria(lib, lib_de, probar)
    ps = L.piezas(lib)
    for nombre in HOJAS:
        h = Hoja(str(carpeta / f"{nombre}.SchDoc"))
        arreglar_hoja(h, ps)
        copia = h.guardar("antes_bom_f7") if not probar else (
            ao.escribir_streams(h.ruta, {"FileHeader": h.datos()}) or "—")
        print(f"== {nombre} (respaldo: {copia})")
        for x in h.cambios:
            print("  ", x)


def solo_hojas(carpeta):
    if ao.altium_abierto():
        raise SystemExit("Altium está abierto: ciérralo antes de correr el script.")
    ps = L.piezas(carpeta / "lib" / "SamacSys.SchLib")
    for nombre in HOJAS:
        h = Hoja(str(carpeta / f"{nombre}.SchDoc"))
        arreglar_hoja(h, ps)
        if not h.cambios:
            print(f"== {nombre}: sin cambios")
            continue
        print(f"== {nombre} (respaldo: {h.guardar('antes_bom_hojas')})")
        for x in h.cambios:
            print("  ", x)


# ---------------------------------------------------------------- docs/BOM_F7.md
def grupo(ln):
    if ln[5] == "DNP":
        return "D"
    if ln[3] == "Disponible":
        return "C"
    if ln[3] == "DigiKey":
        return "B"
    return "A"


def usd(x, n=2):
    """Número con coma decimal y punto de miles (formato de Colombia)."""
    return f"{x:,.{n}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def cop(x):
    return f"{x:,.0f}".replace(",", ".")


def md(ruta):
    tit = {"A": "A · PCBWay turnkey (stock en LCSC; K1 lo compra PCBWay en DigiKey o Mouser): llega soldado",
           "B": "B · DigiKey (carrito del curso), se suelda a mano: PCBWay no lo tiene (vacío desde el 23 oct)",
           "C": "C · Ya disponible, se suelda a mano",
           "D": "D · No se monta (DNP)"}
    o = ["# BOM de la Fase 7 (regla de compras D16)", "",
         "Generada con `python docs/tools/bom_f7.py --md` (la lista `LINEAS` de ese script es la fuente única; "
         "los mismos datos quedan en los parámetros `Manufacturer_Name`, `Manufacturer_Part_Number`, `Supplier`, "
         "`Supplier PN` y `Assembly` de la librería y las hojas).", "",
         "- **Stock revisado el 19 oct 2026** en LCSC (API de JLCPCB/LCSC), DigiKey y Sigma. Precio en US$ por pieza "
         "a cantidad 1 (LCSC o DigiKey); PCBWay cotiza el suyo al hacer el pedido.",
         "- **Una placa ensamblada** (decisión del usuario): U1 es el R-78CK del profesor y se suelda a mano. "
         "Lo demás llega soldado. **23 oct:** no hay pedido de DigiKey; K1 (en 0 en LCSC) lo compra PCBWay en "
         "DigiKey o Mouser dentro del turnkey, y F1/F2 llevan 2 fusibles de repuesto sueltos.",
         f"- TRM del día: {usd(TRM)} COP/USD ([dolarhoy.co](https://www.dolarhoy.co/2026-10-19)).",
         "- PCBWay compra por número de parte, primero en proveedores locales y si no en DigiKey, Mouser o Arrow "
         "([componentes](https://www.pcbway.com/pcb_prototype/Electronic_Components.html)).", ""]
    tot = {}
    for g in "ABCD":
        if not any(grupo(ln) == g for ln in LINEAS):
            continue  # B quedó vacío el 23 oct
        o += [f"## {tit[g]}", "",
              "| Designadores | Cant. | Fabricante | MPN | Proveedor | PN proveedor | Montaje | US$ c/u | US$ línea | Nota |",
              "|---|---|---|---|---|---|---|---|---|---|"]
        for ln in LINEAS:
            if grupo(ln) != g:
                continue
            d, fab, mpn, sup, spn, asm, p, nota = ln
            q = len(d.split(","))
            tot[g] = tot.get(g, 0) + q * p
            o.append(f"| {d.replace(',', ', ')} | {q} | {fab} | `{mpn}` | {sup} | {spn} | {asm} | "
                     f"{usd(p, 4)} | {usd(q * p)} | {nota} |")
        o += ["", f"**Subtotal {g}: US$ {usd(tot.get(g, 0))} por placa**", ""]
    o += ["## E · Fuera de la PCB (Sigma: DigiKey no las tiene o no las envía)", "",
          "| Pieza | Fabricante | Referencia | Proveedor | COP | DigiKey |", "|---|---|---|---|---|---|"]
    for pieza, fab, ref, sup, pesos, nota in FUERA:
        o.append(f"| {pieza} | {fab} | `{ref}` | {sup} | {cop(pesos)} | {nota} |")
    sc_ = sum(x[4] for x in FUERA)
    n_pz = sum(len(ln[0].split(",")) for ln in LINEAS if ln[5] != "DNP")
    o += ["", f"**Subtotal E: {cop(sc_)} COP ≈ US$ {usd(sc_ / TRM)}**", "",
          "## Resumen", "",
          f"{len(LINEAS)} líneas, {n_pz} piezas montadas por placa.", "",
          "| Grupo | US$ | COP |", "|---|---|---|",
          f"| A · PCBWay (LCSC; K1 en DigiKey/Mouser) | {usd(tot.get('A', 0))} | {cop(tot.get('A', 0) * TRM)} |",
          f"| B · DigiKey, carrito del curso | {usd(tot.get('B', 0))} | {cop(tot.get('B', 0) * TRM)} |",
          f"| E · Sigma, fuera de la PCB | {usd(sc_ / TRM)} | {cop(sc_)} |",
          f"| **Total en componentes** | **{usd(tot.get('A', 0) + tot.get('B', 0) + sc_ / TRM)}** | "
          f"**{cop((tot.get('A', 0) + tot.get('B', 0)) * TRM + sc_)}** |", "",
          "Sin la PCB, el costo de ensamble de PCBWay (SMD y THT), el envío ni los impuestos: eso va en el "
          "carrito de compras de F8.",
          "",
          "Stock justo en LCSC (sobra para una placa): APT2012SGC 62 u., Y1 70, SRR4028 66, BAT-HLD-001 55, "
          "3403.0274.11 89 (23 oct; con los 2 de repuesto se piden 4)."]
    Path(ruta).write_text("\n".join(o) + "\n", encoding="utf-8")
    print(f"escrito {ruta}: A US$ {tot.get('A', 0):.2f}, B US$ {tot.get('B', 0):.2f}, E {sc_} COP")


if __name__ == "__main__":
    a = sys.argv[1:]
    if "--md" in a:
        md(Path(__file__).resolve().parents[1] / "BOM_F7.md")
    elif "--hojas" in a:
        solo_hojas(PROY)
    elif "--probar" in a:
        destino = Path(a[a.index("--probar") + 1])
        (destino / "lib").mkdir(parents=True, exist_ok=True)
        for n in HOJAS:
            shutil.copy2(PROY / f"{n}.SchDoc", destino / f"{n}.SchDoc")
        for ext in ("SchLib", "PcbLib"):
            shutil.copy2(PROY / "lib" / f"SamacSys.{ext}", destino / "lib" / f"SamacSys.{ext}")
        main(destino, True)
    elif "--todo" in a:
        # 22 oct: ya no sirve (las piezas reemplazadas se borraron de la librería; falla antes de escribir)
        main(PROY, False)
    else:
        sys.exit(__doc__)
