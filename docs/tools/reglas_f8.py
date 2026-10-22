# -*- coding: utf-8 -*-
"""F8: reglas de diseño y contorno de EVSE_Monitor.PcbDoc sin abrir Altium (Altium CERRADO).

Uso:
    python docs/tools/reglas_f8.py            # muestra lo que haría (no escribe)
    python docs/tools/reglas_f8.py --escribir # respalda el PcbDoc en docs/respaldos/ y escribe

Formato (leído del PcbDoc creado con AD 25.4.2):
- `Rules6/Data`: registros seguidos = código del tipo de regla (uint16) + largo (uint32) + texto
  «|CLAVE=valor|...» terminado en \\0. `Rules6/Header` = cantidad de registros (uint32).
  Códigos que se usan (los mismos de los ejemplos de Altium): Clearance 0, Width 2, RoutingVias 11,
  SolderMaskExpansion 13, PolygonConnect 20, ComponentClearance 24, HoleSize 42, DiffPairsRouting 51,
  HoleToHoleClearance 52, MinimumSolderMaskSliver 53, SilkToSolderMaskClearance 54,
  SilkToSilkClearance 55, BoardOutlineClearance 63; MinimumAnnularRing 19 (MINIMUMRING) y Creepage 65
  (CHECKDISTANCE, APPLYTOPOLYGONPOUR), leídos de las reglas que el usuario creó a mano el 19 oct.
  Volver a correrlo reemplaza todas las reglas de esos tipos (las demás, como las Supply Nets del
  esquemático, se dejan).
- `Board6/Data`: un registro de texto (uint32 + texto); el contorno son los vértices KINDn/VXn/VYn.
- `BoardRegions/Data`: la región «Default Layer Stack Region» repite el contorno como 4 vértices en
  doubles (unidades internas = 1/10000 mil) al final del registro.

Placa: 130 × 100 mm (D18: 2 capas, 1,6 mm, 1 oz, HASL sin plomo; 100 × 100 no alcanzaba), esquina
inferior izquierda en (1000 mil, 1000 mil) y el origen del usuario ahí, para que las coordenadas en mm
de la guía coincidan con las de Altium.
"""
import random
import string
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import altium_ole as ao  # noqa: E402

PCB = Path(r"C:/Nicolas/UNIVERSIDAD - 2026/Hardware en IoT/Control de Carga IoT/Control de Carga IoT/EVSE_Monitor.PcbDoc")

MIL = 1 / 0.0254
X0_MIL, Y0_MIL = 1000.0, 1000.0   # esquina inferior izquierda de la placa
LARGO_MM, ALTO_MM = 130.0, 100.0  # D18: 130 × 100 mm (el 20 oct; 100 × 100 no alcanzaba)


def mil(mm):
    v = f"{mm * MIL:.4f}".rstrip("0").rstrip(".")
    return f"{v}mil"


# ---------------------------------------------------------------- redes y alcances
L1 = ["AC_L1", "AC_L1_F", "HV_D1", "HV_D2"]
L2 = ["AC_L2", "AC_L2_F", "HV_INP", "HV_DCDC", "HV_LDO"]
RED = ["AC_L1", "AC_L2", "AC_L1_F", "AC_L2_F"]
V12 = ["+VIN", "VIN_ACDC", "VIN_BANCO"]
V33 = ["+3V3", "+3V3A"]
USB = ["USB_DP", "USB_DN"]


def redes(lista):
    return " Or ".join(f"InNet('{n}')" for n in lista)


def comps(lista):
    return " Or ".join(f"InComponent('{c}')" for c in lista)


HV = "InNetClass('HV_AC')"
EVSE = "InNetClass('EVSE_EXT')"

# ---------------------------------------------------------------- reglas (por tipo, en orden de prioridad)
# (nombre, alcance1, alcance2, campos propios, comentario)
REGLAS = {
    ("Clearance", 0, "DifferentNets"): [
        # «Not IsKeepOut»: los keepouts de la barrera y del hueco red-isla no son cobre; con ellos dentro del
        # alcance Altium marcaba en verde todo lo de red a menos de 6,4 mm de la barrera (22 oct)
        ("HV_SELV", HV, f"Not {HV} And Not IsKeepOut", {"GAP": 6.4}, "Red - resto (incluido GND): reforzado, 6,4 mm"),
        ("EVSE_resto", EVSE, f"Not {EVSE} And Not IsKeepOut", {"GAP": 6.4}, "J2 de potencial desconocido: 6,4 mm a todo"),
        ("L1_L2", redes(L1), redes(L2), {"GAP": 3.2}, "Funcional L1-L2 (hasta 373 Vpk)"),
        ("EVSE_pads_K1", "InNet('EVSE_EN_A') And InComponent('K1')", "InNet('EVSE_EN_B') And InComponent('K1')",
         {"GAP": 1.7}, "Pads 3 y 4 de K1 (1,79 mm)"),
        ("EVSE_A_B", "InNet('EVSE_EN_A')", "InNet('EVSE_EN_B')", {"GAP": 1.5}, "Salida de K1 (hasta 400 Vpk)"),
        ("HV_interna", HV, HV, {"GAP": 0.5}, "Dentro de la red (escalones de 93 Vpk; U2 0,62 mm)"),
        ("J5_pads", "InComponent('J5')", "InComponent('J5')", {"GAP": 0.145},
         "Patron de Wurth: pads de 0,65 mm a 0,8 mm (0,15 mm entre pads)"),
        ("Poligono_GND", "InPolygon", "All", {"GAP": 0.3}, "Poligonos de GND a 0,3 mm del resto"),
        ("Clearance", "All", "All", {"GAP": 0.2}, "General SELV (PCBWay 0,1 mm)"),
    ],
    ("Creepage", 65, "AnyNet"): [
        ("Creepage_HV", HV, f"Not {HV}", {"GAP": 6.4}, "Reforzado red - SELV"),
        ("Creepage_EVSE", EVSE, f"Not {EVSE}", {"GAP": 6.4}, "J2 de potencial desconocido"),
        ("Creepage_L1_L2", redes(L1), redes(L2), {"GAP": 3.2}, "Funcional L1-L2"),
    ],
    ("MinimumAnnularRing", 19, "AnyNet"): [
        ("Anillo_J5", "InComponent('J5')", "All", {"GAP": 0.12},
         "Wurth: agujero 0,4 / pad 0,65 (pin 0,28 x 0,25); pedir a PCBWay que no lo cambie"),
        ("Anillo", "All", "All", {"GAP": 0.15}, "PCBWay: anillo >= 0,15 mm"),
    ],
    ("Width", 2, "AnyNet"): [
        ("Ancho_USB", redes(USB), "All", {"MIN": 0.2, "PREF": 0.3, "MAX": 0.6}, "USB Full Speed: 0,3 mm para entrar a los pads de J5 (0,3 mm)"),
        ("Ancho_red", redes(RED), "All", {"MIN": 0.5, "PREF": 1.5, "MAX": 3.0}, "Troncos de red 1,5 mm; ramales a U2 y condensadores 0,5"),
        ("Ancho_HV", HV, "All", {"MIN": 0.3, "PREF": 0.4, "MAX": 3.0}, "Senales del lado de red"),
        ("Ancho_EVSE", EVSE, "All", {"MIN": 0.4, "PREF": 0.8, "MAX": 2.0}, "Salida de K1 <= 120 mA"),
        ("Ancho_12V", redes(V12), "All", {"MIN": 0.5, "PREF": 1.0, "MAX": 2.5}, "12 V hasta 1,67 A: troncos 1,0; ramal a R41 0,5"),
        ("Ancho_3V3", redes(V33), "All", {"MIN": 0.25, "PREF": 0.4, "MAX": 2.0}, "3,3 V <= 0,5 A (0,4 entra a los pads de U3)"),
        ("Ancho_GND", "InNet('GND')", "All", {"MIN": 0.25, "PREF": 0.3, "MAX": 3.0}, "GND: pistas finas, los poligonos lo refuerzan"),
        ("Width", "All", "All", {"MIN": 0.2, "PREF": 0.25, "MAX": 2.0}, "Senales"),
    ],
    ("RoutingVias", 11, "AnyNet"): [
        ("Vias_potencia", redes(RED + V12 + V33 + ["GND"]), "All",
         {"HOLE": (0.3, 0.4, 0.4), "DIAM": (0.6, 0.8, 0.8)}, "Potencia: 0,4 / 0,8 mm"),
        ("Vias", "All", "All", {"HOLE": (0.3, 0.3, 0.4), "DIAM": (0.6, 0.6, 0.8)}, "Senal: 0,3 / 0,6 mm (anillo 0,15)"),
    ],
    ("SolderMaskExpansion", 13, "AnyNet"): [
        # 22 oct: vías tapadas por las dos caras (las de costura y las de GND junto a pads salían como anillos dorados
        # y dejaban 82 puentes de máscara de menos de 0,1 mm entre pad y vía)
        ("Vias_tapadas", "IsVia", "All", {"EXPANSION": 0.0, "TAPADA": True}, "Vias tapadas con mascara en Top y Bottom"),
        ("SolderMaskExpansion", "All", "All", {"EXPANSION": 0.05}, "PCBWay: apertura >= 2 mil"),
    ],
    ("PolygonConnect", 20, "AnyNet"): [
        ("Polygon_vias", "IsVia", "All", {"STYLE": "Direct"}, "Vias directas al poligono"),
        ("PolygonConnect", "All", "All", {"STYLE": "Relief"}, "Pads con 4 rayos de 0,3 mm (se sueldan bien)"),
    ],
    ("ComponentClearance", 24, "AnyNet"): [
        ("Cautin_K1", "InComponent('K1')", "All", {"GAP": 2.0}, "K1 se suelda a mano por arriba: 2 mm libres (U1 es THT)"),
        ("F1B_anidado", "InComponent('F1B')", f"Not ({comps(['F1', 'F1B'])})", {"GAP": 0.25},
         "F1B (DNP) va sobre F1: solo se revisa contra el resto"),
        ("F2B_anidado", "InComponent('F2B')", f"Not ({comps(['F2', 'F2B'])})", {"GAP": 0.25},
         "F2B (DNP) va sobre F2: solo se revisa contra el resto"),
        ("ComponentClearance", f"Not ({comps(['F1B', 'F2B'])})", f"Not ({comps(['F1B', 'F2B'])})", {"GAP": 0.25},
         "Cuerpos SMD: 0,25 mm"),
    ],
    ("HoleSize", 42, "AnyNet"): [
        ("HoleSize", "All", "All", {"MIN": 0.3, "MAX": 6.0}, "PCBWay sin costo extra: 0,3-6,0 mm"),
    ],
    ("DiffPairsRouting", 51, "AnyNet"): [
        # 22 oct: 30 mm sin acoplar. El par de U5 a D5 quedó separado 23 mm; en USB Full Speed (12 Mb/s, flancos
        # >= 4 ns, largo crítico ~10 cm) eso no cambia nada, y el DRC ya no lo marca
        ("USB_90", "All", "All", {"W": (0.2, 0.5, 0.55), "GAP": (0.15, 0.15, 0.25), "UNCOUPLED": 30.0},
         "USB Full Speed: 0,50 / 0,15 / GND 0,15 -> 92,6 ohm; 30 mm sin acoplar (FS no es critico)"),
    ],
    ("HoleToHoleClearance", 52, "AnyNet"): [
        ("HoleToHoleClearance", "All", "All", {"GAP": 0.4}, "PCBWay: 0,41 mm entre agujeros de piezas"),
    ],
    ("MinimumSolderMaskSliver", 53, "AnyNet"): [
        ("Mascara_J5", "InComponent('J5')", "All", {"GAP": 0.0}, "Pads de J5 a 0,8 mm: apertura de mascara corrida"),
        ("MinimumSolderMaskSliver", "All", "All", {"GAP": 0.1}, "Puente de mascara verde >= 0,1 mm"),
    ],
    ("SilkToSolderMaskClearance", 54, "AnyNet"): [
        ("SilkToSolderMaskClearance", "All", "All", {"GAP": 0.05}, "PCBWay recorta la serigrafia sobre pads"),
    ],
    ("SilkToSilkClearance", 55, "AnyNet"): [
        ("SilkToSilkClearance", "All", "All", {"GAP": 0.0}, "Sin revision serigrafia-serigrafia"),
    ],
    ("BoardOutlineClearance", 63, "DifferentNets"): [
        ("Borde_HV", f"{HV} Or {EVSE}", "All", {"GAP": 1.0}, "Red y EVSE: 1 mm al borde"),
        ("BoardOutlineClearance", "All", "All", {"GAP": 0.3}, "PCBWay >= 0,25 mm"),
    ],
}

CAPAS_DP = ["TOPLAYER"] + [f"MIDLAYER{i}" for i in range(1, 31)] + ["BOTTOMLAYER"]


def campos_propios(kind, v):
    if kind in ("Clearance", "BoardOutlineClearance"):
        g = mil(v["GAP"])
        return [("GAP", g), ("GENERICCLEARANCE", g), ("IGNOREPADTOPADCLEARANCEINFOOTPRINT", "FALSE"), ("OBJECTCLEARANCES", "")]
    if kind == "Creepage":
        return [("CHECKDISTANCE", mil(v["GAP"])), ("APPLYTOPOLYGONPOUR", "TRUE")]
    if kind == "MinimumAnnularRing":
        return [("MINIMUMRING", mil(v["GAP"]))]
    if kind == "Width":
        return [("MAXLIMIT", mil(v["MAX"])), ("MINLIMIT", mil(v["MIN"])), ("PREFEREDWIDTH", mil(v["PREF"]))]
    if kind == "RoutingVias":
        hmin, hpref, hmax = v["HOLE"]
        dmin, dpref, dmax = v["DIAM"]
        return [("HOLEWIDTH", mil(hpref)), ("WIDTH", mil(dpref)), ("VIASTYLE", "Through Hole"),
                ("MINHOLEWIDTH", mil(hmin)), ("MINWIDTH", mil(dmin)), ("MAXHOLEWIDTH", mil(hmax)), ("MAXWIDTH", mil(dmax))]
    if kind == "SolderMaskExpansion":
        if v.get("TAPADA"):
            return [("EXPANSION", mil(v["EXPANSION"])), ("ISTENTINGTOP", "TRUE"), ("USESEPARATEEXPANSIONS", "FALSE"),
                    ("EXPANSIONBOTTOM", mil(v["EXPANSION"])), ("ISTENTINGBOTTOM", "TRUE")]
        return [("EXPANSION", mil(v["EXPANSION"])), ("ISTENTINGTOP", "FALSE")]
    if kind == "PolygonConnect":
        return [("CONNECTSTYLE", v["STYLE"]), ("RELIEFCONDUCTORWIDTH", mil(0.3)), ("RELIEFENTRIES", "4"),
                ("POLYGONRELIEFANGLE", "90 Angle"), ("AIRGAPWIDTH", mil(0.25))]
    if kind == "ComponentClearance":
        g = mil(v["GAP"])
        return [("GAP", g), ("COLLISIONCHECKMODE", "3"), ("VERTICALGAP", g), ("SHOWDISTANCES", "FALSE")]
    if kind == "HoleSize":
        return [("ABSOLUTEVALUES", "TRUE"), ("MAXLIMIT", mil(v["MAX"])), ("MINLIMIT", mil(v["MIN"])),
                ("MAXPERCENT", "80.000"), ("MINPERCENT", "20.000")]
    if kind == "DiffPairsRouting":
        gmin, gpref, gmax = v["GAP"]
        wmin, wpref, wmax = v["W"]
        out = [("MAXLIMIT", mil(gmax)), ("MINLIMIT", mil(gmin)), ("MOSTFREQGAP", mil(gpref))]
        for c in CAPAS_DP:
            out += [(f"{c}_MINWIDTH", mil(wmin)), (f"{c}_MAXWIDTH", mil(wmax)), (f"{c}_PREFWIDTH", mil(wpref))]
        return out + [("MAXUNCOUPLEDLENGTH", mil(v["UNCOUPLED"]))]
    if kind == "HoleToHoleClearance":
        return [("GAP", mil(v["GAP"])), ("ALLOWSTACKEDMICROVIAS", "TRUE")]
    if kind == "MinimumSolderMaskSliver":
        return [("MINSOLDERMASKWIDTH", mil(v["GAP"]))]
    if kind == "SilkToSolderMaskClearance":
        # FALSE = contra las aberturas de máscara (pads); con TRUE Altium marcaba serigrafía sobre pistas y polígonos
        # cubiertos por máscara (375 violaciones el 22 oct), que no es un problema
        return [("MINSILKSCREENTOMASKGAP", mil(v["GAP"])), ("CLEARANCETOEXPOSEDCOPPER", "FALSE")]
    if kind == "SilkToSilkClearance":
        return [("SILKTOSILKCLEARANCE", mil(v["GAP"]))]
    raise ValueError(kind)


# ---------------------------------------------------------------- Rules6
def leer_reglas(data):
    out, i = [], 0
    while i < len(data):
        code = struct.unpack_from("<H", data, i)[0]
        ln = struct.unpack_from("<I", data, i + 2)[0]
        out.append((code, data[i + 6:i + 6 + ln]))
        i += 6 + ln
    return out


def unir_reglas(regs):
    return b"".join(struct.pack("<HI", c, len(t)) + t for c, t in regs)


def uid(usados):
    while True:
        u = "".join(random.choice(string.ascii_uppercase) for _ in range(8))
        if u not in usados:
            usados.add(u)
            return u


def registro(kind, netscope, nombre, s1, s2, prioridad, propios, comentario, usados):
    base = [("SELECTION", "FALSE"), ("LAYER", "UNKNOWN"), ("LOCKED", "FALSE"), ("POLYGONOUTLINE", "FALSE"),
            ("USERROUTED", "TRUE"), ("KEEPOUT", "FALSE"), ("UNIONINDEX", "0"), ("RULEKIND", kind),
            ("NETSCOPE", netscope), ("LAYERKIND", "SameLayer"), ("SCOPE1EXPRESSION", s1), ("SCOPE2EXPRESSION", s2),
            ("NAME", nombre), ("ENABLED", "TRUE"), ("PRIORITY", str(prioridad)), ("COMMENT", comentario),
            ("UNIQUEID", uid(usados)), ("DEFINEDBYLOGICALDOCUMENT", "FALSE")]
    for k, v in base + propios:
        assert "|" not in v and "=" not in k, (k, v)
    return ao.cuerpo(base + propios)


def nuevas_reglas(data):
    regs = leer_reglas(data)
    assert unir_reglas(regs) == data, "Rules6: el formato no es el esperado"
    usados = {ao.valor(ao.campos(t), "UNIQUEID") for _, t in regs}
    codigos = {code for (_, code, _) in REGLAS}
    quedan = [(c, t) for c, t in regs if c not in codigos]
    quitadas = [ao.valor(ao.campos(t), "NAME") for c, t in regs if c in codigos]
    nuevas = []
    for (kind, code, netscope), lista in REGLAS.items():
        for prio, (nombre, s1, s2, v, com) in enumerate(lista, 1):
            nuevas.append((code, registro(kind, netscope, nombre, s1, s2, prio, campos_propios(kind, v), com, usados)))
    return quedan + nuevas, quitadas, nuevas


# ---------------------------------------------------------------- contorno
def vertices_mil():
    x1, y1 = X0_MIL, Y0_MIL
    x2, y2 = X0_MIL + LARGO_MM * MIL, Y0_MIL + ALTO_MM * MIL
    return [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]


def nuevo_board6(data):
    ln = struct.unpack_from("<I", data, 0)[0]
    assert ln + 4 == len(data), "Board6: el formato no es el esperado"
    f = ao.campos(data[4:])
    vs = vertices_mil() + [vertices_mil()[0]]
    for i in range(5):
        assert ao.valor(f, f"VX{i}") is not None and ao.valor(f, f"KIND{i}") == "0"
        f = ao.poner(f, f"VX{i}", f"{vs[i][0]:.4f}mil".replace(".0000mil", "mil"))
        f = ao.poner(f, f"VY{i}", f"{vs[i][1]:.4f}mil".replace(".0000mil", "mil"))
    assert ao.valor(f, "VX5") is None, "Board6: el contorno tiene más de 5 vértices"
    f = ao.poner(f, "ORIGINX", f"{X0_MIL:g}mil")
    f = ao.poner(f, "ORIGINY", f"{Y0_MIL:g}mil")
    t = ao.cuerpo(f)
    return struct.pack("<I", len(t)) + t


def nuevo_boardregions(data):
    # registro: cabecera binaria + texto «...|LAYERSTACKID={...}» terminado en \0 + cantidad de vértices
    # (uint32) + vértices (x, y en doubles, 1/10000 mil). Solo se acepta una región de 4 vértices al final.
    i = data.find(b"LAYERSTACKID=")
    j = data.find(b"\x00", i)
    n = struct.unpack_from("<I", data, j + 1)[0]
    if i < 0 or n != 4 or j + 5 + 16 * n != len(data):
        return None
    nuevo = b"".join(struct.pack("<dd", x * 1e4, y * 1e4) for x, y in vertices_mil())
    return data[:j + 5] + nuevo


def main():
    escribir = "--escribir" in sys.argv
    if escribir and ao.altium_abierto():
        sys.exit("Altium está abierto (X2.exe): ciérralo antes de escribir.")
    rules = ao.leer_stream(PCB, "Rules6/Data")
    regs, quitadas, nuevas = nuevas_reglas(rules)
    print(f"Rules6: {len(leer_reglas(rules))} reglas -> {len(regs)}")
    print("  se reemplazan:", ", ".join(quitadas))
    for code, t in nuevas:
        f = ao.campos(t)
        print(f"  + {ao.valor(f, 'RULEKIND'):26} {ao.valor(f, 'PRIORITY'):>2} {ao.valor(f, 'NAME'):26} "
              f"{ao.valor(f, 'SCOPE1EXPRESSION')}  <->  {ao.valor(f, 'SCOPE2EXPRESSION')}")
    b6 = nuevo_board6(ao.leer_stream(PCB, "Board6/Data"))
    br = nuevo_boardregions(ao.leer_stream(PCB, "BoardRegions/Data"))
    print(f"Contorno: {LARGO_MM:g} x {ALTO_MM:g} mm desde (1000 mil, 1000 mil); origen en la esquina inferior izquierda")
    print("  BoardRegions:", "se actualiza" if br else "NO se encontró el contorno por defecto (no se toca)")
    if not escribir:
        print("\n(prueba: no se escribió nada; usa --escribir)")
        return
    copia = ao.respaldo(PCB, "antes_reglas_f8")
    print("Respaldo:", copia)
    cambios = {"Rules6/Data": unir_reglas(regs), "Rules6/Header": struct.pack("<I", len(regs)), "Board6/Data": b6}
    if br:
        cambios["BoardRegions/Data"] = br
    ao.escribir_streams(PCB, cambios)
    # verificación
    vuelta = leer_reglas(ao.leer_stream(PCB, "Rules6/Data"))
    assert len(vuelta) == len(regs) == struct.unpack("<I", ao.leer_stream(PCB, "Rules6/Header"))[0]
    f = ao.campos(ao.leer_stream(PCB, "Board6/Data")[4:])
    print("Escrito y releído:", len(vuelta), "reglas; VX2 =", ao.valor(f, "VX2"), "VY2 =", ao.valor(f, "VY2"))


if __name__ == "__main__":
    main()
