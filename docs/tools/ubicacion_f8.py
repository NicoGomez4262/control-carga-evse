# -*- coding: utf-8 -*-
"""F8: ubicación de los 132 componentes de EVSE_Monitor.PcbDoc (placa de 130 × 100 mm, D18).

Uso:
    python docs/tools/ubicacion_f8.py               # revisa la ubicación de POS y dibuja docs/revisiones/F8_ubicacion.png
    python docs/tools/ubicacion_f8.py --pas         # además escribe docs/tools/reorganizar_f8.pas y .PrjScr

La ubicación se aplica en Altium con el script DelphiScript generado (File » Run Script… → ubicar_f8.pas →
UbicarF8): mueve el origen de cada footprint a (x, y) respecto del origen del usuario (esquina inferior
izquierda de la placa, puesto por reglas_f8.py) y le pone la rotación absoluta.

Revisión (con los pads y courtyards leídos del PcbDoc, en el marco propio del footprint):
- courtyards (capa mecánica 15 de SamacSys) que se cruzan (salvo F1/F1B y F2/F2B, anidados a propósito);
- pads de distinta red más cerca que la regla que les toca (red–resto 6,4; EVSE–resto 6,4; L1–L2 3,2;
  dentro de la red 0,5; EVSE_EN_A–B 1,5; resto 0,25 mm de margen para ubicar);
- pads SMD a menos de 5 mm de los bordes izquierdo o derecho (banda de la línea SMT);
- zonas: piezas de red con x ≤ 45 y y ≤ 75, isla EVSE en x ≤ 45 y y ≥ 80, SELV con x ≥ 51,7;
- agujeros M3 (NPTH Ø3,2) en las esquinas: cobre de red o EVSE a ≥ 8 mm del centro; courtyards fuera.
"""
import math
import struct
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import altium_ole as ao  # noqa: E402
import pcblib  # noqa: E402
import revisar_pcb as rv  # noqa: E402

RAIZ = Path(__file__).resolve().parents[2]
U = rv.U
X0 = Y0 = 25.4          # origen del usuario (1000 mil) en coordenadas absolutas del PcbDoc, mm
LARGO, ALTO = 130.0, 100.0
BARRERA = (45.0, 51.7)
HV_TOPE = 75.0          # cobre de red hasta aquí
ISLA_DESDE = 80.0
AGUJEROS = [(4, 4), (126, 4), (4, 96), (126, 96)]
R_AGUJERO = 1.6
FIDUCIALES = [(56.0, 40.0), (123.0, 34.75), (97.75, 74.5)]   # cobre Ø1 mm, máscara Ø2 mm, en el SELV
CAUTIN = {"K1": 2.0}    # se suelda a mano por arriba: courtyard libre alrededor (U1 es THT: se suelda por abajo)

# ---------------------------------------------------------------- clasificación de redes
L1 = {"AC_L1", "AC_L1_F", "HV_D1", "HV_D2"}
L2 = {"AC_L2", "AC_L2_F", "HV_INP", "HV_DCDC", "HV_LDO"}
HV = L1 | L2 | {"HV_D3"}
EVSE = {"EVSE_EN_A", "EVSE_EN_B"}

# piezas por zona (las que cruzan la barrera no se revisan por zona)
CRUZAN = {"PS1", "U2", "K1"}
EN_RED = {"J1", "F1", "F2", "F1B", "F2B", "RV1", "R2", "R3", "R4", "R5", "R6", "C9", "C10", "C11", "C12", "C16", "C17"}
EN_ISLA = {"J2"}
ANIDADOS = [{"F1", "F1B"}, {"F2", "F2B"}]
# pueden salirse del contorno (conectores y antena al borde)
SOBRESALEN = {"J1", "J2", "J3", "J4", "J5", "J6", "J7", "J8", "U4"}

# ---------------------------------------------------------------- ubicación: designador -> (x, y, rotación)
# (x, y) = origen del footprint en mm desde la esquina inferior izquierda de la placa.
# Reorganizada el 20 oct pensando en rutear a mano (ratsnest_f8.py: 227 → 140 cruces, 2019 → 1738 mm):
# piezas grandes a mano y pasivos con autoubicar_f8.py (pegados al pin que sirven), luego retoques a mano.
POS = {
    # --- zona de red (sin cambios)
    "PS1": (13.0, 7.0, 0), "J1": (5.5, 72.4, 90), "F2B": (17.25, 55.6, 270), "F2": (17.25, 55.6, 270),
    "F1B": (28.25, 55.6, 270), "F1": (28.25, 55.6, 270), "RV1": (22.75, 36.9, 180), "R2": (36.0, 45.0, 90),
    "R3": (36.0, 52.0, 90), "R4": (36.0, 59.0, 90), "R5": (36.0, 66.0, 90), "U2": (48.35, 64.0, 0),
    "C10": (39.7, 71.3, 0), "C11": (39.7, 73.4, 0), "C12": (43.4, 71.3, 0), "C17": (43.4, 73.4, 0),
    "C16": (41.05, 64.5, 90), "C9": (41.0, 60.4, 90), "R6": (41.0, 56.6, 90),
    # --- isla EVSE
    "J2": (5.5, 87.0, 90), "K1": (48.35, 85.73, 180),
    # --- driver de K1 (2 mm libres alrededor de K1 para el cautín)
    "LED6": (57.9, 81.6, 0), "R41": (61.6, 81.6, 0), "Q3": (58.0, 86.2, 180), "R40": (62.6, 83.75, 180),
    "R39": (62.6, 85.85, 180),
    # --- botón PARAR: J7 arriba a la izquierda, SW1 junto a la barrera, R31 junto al pin 9 de U4
    "J7": (61.0, 95.3, 180), "SW1": (55.6, 75.5, 90), "C36": (60.5, 74.0, 270), "R27": (63.5, 74.0, 0),
    "R31": (82.1, 78.4, 0),
    # --- salida de U2 (lado SELV) y cadena del AMC hacia VP/VN
    "C13": (56.0, 68.5, 0), "C14": (56.0, 63.25, 0), "C15": (56.0, 65.5, 0), "R7": (59.5, 67.5, 180),
    "C18": (56.0, 61.0, 0), "R9": (59.5, 61.0, 0), "C21": (53.0, 56.75, 270), "R12": (53.0, 53.25, 270),
    "R10": (60.25, 58.0, 270), "C19": (57.5, 58.75, 180), "R14": (54.25, 50.25, 0), "C22": (55.75, 52.5, 0),
    # --- ATM90E26: RST/AVDD arriba a la izquierda, VREF abajo, hueco para IP/IN en los pines 7 y 8, cristal a la derecha
    "U3": (72.0, 63.0, 0), "C29": (64.4, 67.6, 180), "C28": (64.4, 65.6, 180), "R16": (65.2, 70.3, 270),
    "C30": (64.4, 60.0, 180), "C31": (64.4, 58.1, 180), "C25": (69.2, 69.6, 0), "C24": (73.4, 69.6, 180),
    "FB1": (64.5, 63.0, 0), "C8": (61.25, 65.25, 180), "Y1": (82.5, 63.65, 180), "C26": (80.45, 59.3, 270),
    "C27": (84.55, 59.3, 270), "R18": (78.0, 68.25, 270), "R17": (75.25, 55.5, 270), "LED2": (75.25, 51.5, 90),
    # --- CT: J3 arriba, TVS, carga y filtro RC debajo; IP/IN bajan por la izquierda de U3
    "J3": (72.0, 95.5, 0), "D4": (72.0, 84.6, 180), "R11": (68.6, 80.6, 90), "R8": (70.6, 80.6, 270),
    "R15": (73.4, 80.6, 270), "R13": (75.4, 80.6, 270), "C20": (70.6, 76.6, 270), "C23": (73.4, 76.6, 270),
    # --- puntos de prueba en fila
    "TP5": (57.0, 46.0, 0), "TP4": (63.5, 46.0, 0), "TP6": (70.0, 46.0, 0),
    # --- ESP32-S3 (antena afuera) y alrededores: desacoples y EN arriba a la izquierda, LEDs en filas a la izquierda, I2C abajo
    "U4": (94.5, 93.5, 0), "C33": (80.9, 97.8, 270), "C34": (82.9, 97.8, 270), "C32": (82.2, 94.5, 0),
    "R22": (82.6, 91.6, 270), "LED3": (78.4, 85.6, 0), "R28": (82.1, 85.6, 0), "LED4": (78.4, 83.2, 0),
    "R29": (82.1, 83.2, 0), "LED5": (78.4, 80.8, 0), "R30": (82.1, 80.8, 0), "R32": (82.0, 88.0, 180),
    "R33": (89.0, 78.0, 180), "R21": (103.25, 77.25, 270),
    # --- USB-C, CH340C (rot 90) y auto-reset, a la derecha de U4
    "J5": (118.5, 95.35, 180), "D5": (118.5, 84.6, 270), "R23": (122.25, 87.25, 180), "R24": (115.5, 86.5, 90),
    "U5": (110.5, 80.5, 90), "C35": (106.25, 86.0, 270), "R25": (109.5, 75.5, 180), "R26": (100.25, 77.75, 180),
    "Q1": (109.5, 86.5, 270), "R20": (110.5, 90.5, 270), "Q2": (111.0, 94.75, 0), "R19": (107.0, 95.75, 0),
    "SW3": (105.5, 70.0, 0), "SW2": (116.0, 70.0, 0), "J8": (127.0, 75.5, 90),
    # --- RTC, pila y AHT20
    "BT1": (109.0, 47.0, 0), "U7": (87.5, 49.0, 0), "C39": (79.75, 51.25, 0), "R34": (79.5, 49.0, 0),
    "U6": (99.0, 62.5, 0), "R38": (94.5, 62.0, 0), "C37": (94.75, 64.25, 0), "C38": (95.25, 59.25, 90),
    # --- sonda DS18B20 (J4, borde derecho)
    "J4": (126.5, 60.0, 90), "D6": (119.75, 62.75, 270), "R36": (119.75, 59.25, 0), "R35": (116.0, 59.25, 180),
    "R37": (123.2, 74.2, 90), "C40": (116.75, 62.0, 270),
    # --- potencia SELV (salida de PS1 → 12 V → R-78CK → 3,3 V) y LED de encendido
    "D1": (68.5, 15.0, 180), "C2": (80.5, 8.0, 0), "D3": (80.5, 21.5, 0), "J6": (98.0, 5.0, 0),
    "D2": (93.0, 14.5, 0), "L1": (88.0, 22.5, 0), "C6": (94.5, 20.6, 90), "U1": (98.0, 26.0, 0),
    "C1": (100.0, 21.0, 180), "C7": (105.5, 21.0, 90), "L2": (110.25, 25.0, 0), "C3": (117.5, 26.0, 90),
    "C4": (110.5, 32.6, 90), "C5": (112.4, 32.6, 90), "LED1": (80.0, 40.0, 0), "R1": (80.0, 43.25, 90),
    "TP1": (66.0, 30.0, 0), "TP2": (73.0, 30.0, 0), "TP3": (80.0, 30.0, 0),
}


# ---------------------------------------------------------------- lectura del PcbDoc
def leer():
    comps = rv.texto("Components6/Data")
    nets = [ao.valor(n, "NAME") for n in rv.texto("Nets6/Data")]
    info = {}
    orden = []
    for c in comps:
        d = ao.valor(c, "SOURCEDESIGNATOR")
        x = float(ao.valor(c, "X").replace("mil", "")) * 0.0254
        y = float(ao.valor(c, "Y").replace("mil", "")) * 0.0254
        rot = float(ao.valor(c, "ROTATION"))
        info[d] = dict(des=d, fp=ao.valor(c, "PATTERN"), x=x, y=y, rot=rot, pads=[], caja=None)
        orden.append(d)

    def local(d, px, py):
        c = info[d]
        a = -math.radians(c["rot"])
        dx, dy = px - c["x"], py - c["y"]
        return dx * math.cos(a) - dy * math.sin(a), dx * math.sin(a) + dy * math.cos(a)

    data = ao.leer_stream(rv.PCB, "Pads6/Data")
    i = 0
    while i < len(data):
        i += 1
        bl, i = pcblib.bloques(data, i, 6)
        g = bl[4]
        nombre = bl[0][1:1 + bl[0][0]].decode("latin-1")
        red = struct.unpack_from("<H", g, 3)[0]
        comp = struct.unpack_from("<H", g, 7)[0]
        if comp == 0xFFFF:
            continue
        x, y = (v * U for v in struct.unpack_from("<ii", g, 13))
        sx, sy = (v * U for v in struct.unpack_from("<ii", g, 21))
        hueco = struct.unpack_from("<i", g, 45)[0] * U
        forma = g[49]
        prot = struct.unpack_from("<d", g, 52)[0]
        d = orden[comp]
        lx, ly = local(d, x, y)
        info[d]["pads"].append(dict(nombre=nombre, red=nets[red] if red != 0xFFFF else None, x=lx, y=ly,
                                    sx=sx, sy=sy, rot=(prot - info[d]["rot"]) % 360, smd=g[0] == 1,
                                    redondo=forma == 1 and abs(sx - sy) < 1e-3, hueco=hueco))
    # courtyard = caja de las pistas/arcos de la capa mecánica 15 (SamacSys); si no hay, la de los pads
    cajas = defaultdict(lambda: [1e9, 1e9, -1e9, -1e9])

    def sumar(d, pts):
        b = cajas[d]
        for px, py in pts:
            lx, ly = local(d, px, py)
            b[0], b[1], b[2], b[3] = min(b[0], lx), min(b[1], ly), max(b[2], lx), max(b[3], ly)

    for stream, tipo in (("Tracks6/Data", 4), ("Arcs6/Data", 1)):
        data = ao.leer_stream(rv.PCB, stream)
        i = 0
        while i < len(data):
            i += 1
            bl, i = pcblib.bloques(data, i, 1)
            g = bl[0]
            comp = struct.unpack_from("<H", g, 7)[0]
            if comp == 0xFFFF or g[0] != 71:   # 71 = Mechanical 15
                continue
            if tipo == 4:
                x1, y1, x2, y2 = (v * U for v in struct.unpack_from("<iiii", g, 13))
                sumar(orden[comp], [(x1, y1), (x2, y2)])
            else:
                cx, cy, r = (v * U for v in struct.unpack_from("<iii", g, 13))
                sumar(orden[comp], [(cx - r, cy - r), (cx + r, cy + r)])
    for d, c in info.items():
        if d in cajas:
            c["caja"] = cajas[d]
        else:
            xs = [p["x"] - max(p["sx"], p["sy"]) / 2 for p in c["pads"]] + [p["x"] + max(p["sx"], p["sy"]) / 2 for p in c["pads"]]
            ys = [p["y"] - max(p["sx"], p["sy"]) / 2 for p in c["pads"]] + [p["y"] + max(p["sx"], p["sy"]) / 2 for p in c["pads"]]
            c["caja"] = [min(xs) - 0.25, min(ys) - 0.25, max(xs) + 0.25, max(ys) + 0.25]
    return info


# ---------------------------------------------------------------- geometría
def girar(x, y, rot):
    a = math.radians(rot)
    return x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)


def caja_en_placa(c, pos):
    x, y, rot = pos
    b = c["caja"]
    pts = [girar(px, py, rot) for px in (b[0], b[2]) for py in (b[1], b[3])]
    return [x + min(p[0] for p in pts), y + min(p[1] for p in pts), x + max(p[0] for p in pts), y + max(p[1] for p in pts)]


def pads_en_placa(c, pos):
    x, y, rot = pos
    out = []
    for p in c["pads"]:
        px, py = girar(p["x"], p["y"], rot)
        r = (p["rot"] + rot) % 180
        sx, sy = (p["sy"], p["sx"]) if abs(r - 90) < 1 else (p["sx"], p["sy"])
        out.append(dict(p, X=x + px, Y=y + py, SX=sx, SY=sy))
    return out


def dist_pads(a, b):
    if a["redondo"] and b["redondo"]:
        return math.hypot(a["X"] - b["X"], a["Y"] - b["Y"]) - a["SX"] / 2 - b["SX"] / 2
    dx = max(0.0, abs(a["X"] - b["X"]) - (a["SX"] + b["SX"]) / 2)
    dy = max(0.0, abs(a["Y"] - b["Y"]) - (a["SY"] + b["SY"]) / 2)
    return math.hypot(dx, dy)


def regla(na, nb):
    if na == nb and na is not None:
        return None
    ha, hb = na in HV, nb in HV
    ea, eb = na in EVSE, nb in EVSE
    if ha != hb or ea != eb:
        return 6.4, "red/EVSE-resto"
    if ea and eb:
        return 1.5, "EVSE_A-B"
    if ha and hb:
        if (na in L1 and nb in L2) or (na in L2 and nb in L1):
            return 3.2, "L1-L2"
        return 0.5, "red interna"
    return 0.25, "general"


# ---------------------------------------------------------------- revisión
def revisar(info, pos):
    prob = []
    faltan = [d for d in info if d not in pos]
    cajas = {d: caja_en_placa(info[d], pos[d]) for d in pos if d in info}
    pads = {d: pads_en_placa(info[d], pos[d]) for d in pos if d in info}
    ds = sorted(cajas)
    for i, a in enumerate(ds):
        A = cajas[a]
        for b in ds[i + 1:]:
            if {a, b} in ANIDADOS:
                continue
            B = cajas[b]
            if A[0] < B[2] - 1e-6 and B[0] < A[2] - 1e-6 and A[1] < B[3] - 1e-6 and B[1] < A[3] - 1e-6:
                ox = min(A[2], B[2]) - max(A[0], B[0])
                oy = min(A[3], B[3]) - max(A[1], B[1])
                prob.append(f"choque {a}-{b}: {ox:.2f} x {oy:.2f} mm")
    # pads entre componentes distintos
    todos = [(d, p) for d in ds for p in pads[d]]
    for i, (da, pa) in enumerate(todos):
        for db, pb in todos[i + 1:]:
            if da == db or {da, db} in ANIDADOS:
                continue
            r = regla(pa["red"], pb["red"])
            if r is None:
                continue
            if abs(pa["X"] - pb["X"]) > 12 or abs(pa["Y"] - pb["Y"]) > 12:
                continue
            dd = dist_pads(pa, pb)
            if dd < r[0] - 1e-6:
                prob.append(f"distancia {r[1]} {da}.{pa['nombre']}({pa['red']})-{db}.{pb['nombre']}({pb['red']}): "
                            f"{dd:.2f} < {r[0]}")
    for d, m in CAUTIN.items():
        A = cajas[d]
        for b in ds:
            if b == d:
                continue
            B = cajas[b]
            gx = max(B[0] - A[2], A[0] - B[2])
            gy = max(B[1] - A[3], A[1] - B[3])
            if max(gx, gy) < m - 1e-6:
                prob.append(f"cautín: {b} a {max(gx, gy):.2f} mm de {d} (pide {m})")
    for fx, fy in FIDUCIALES:
        for b in ds:
            B = cajas[b]
            cx, cy = min(max(fx, B[0]), B[2]), min(max(fy, B[1]), B[3])
            if math.hypot(fx - cx, fy - cy) < 1.5:
                prob.append(f"fiducial ({fx}, {fy}) a {math.hypot(fx - cx, fy - cy):.2f} mm de {b}")
    for d in ds:
        A = cajas[d]
        if d not in SOBRESALEN and (A[0] < -1e-6 or A[1] < -1e-6 or A[2] > LARGO + 1e-6 or A[3] > ALTO + 1e-6):
            prob.append(f"fuera de la placa {d}: {[round(v, 2) for v in A]}")
        for p in pads[d]:
            if p["smd"] and (p["X"] - p["SX"] / 2 < 5.0 or p["X"] + p["SX"] / 2 > LARGO - 5.0):
                prob.append(f"SMD a < 5 mm del borde de transporte: {d}.{p['nombre']}")
                break
        for hx, hy in AGUJEROS:
            cx = min(max(hx, A[0]), A[2])
            cy = min(max(hy, A[1]), A[3])
            if math.hypot(hx - cx, hy - cy) < R_AGUJERO + 0.3:
                prob.append(f"courtyard de {d} sobre el agujero ({hx}, {hy})")
            for p in pads[d]:
                lim = R_AGUJERO + (6.4 if (p["red"] in HV or p["red"] in EVSE) else 0.5)
                cx = min(max(hx, p["X"] - p["SX"] / 2), p["X"] + p["SX"] / 2)
                cy = min(max(hy, p["Y"] - p["SY"] / 2), p["Y"] + p["SY"] / 2)
                if math.hypot(hx - cx, hy - cy) < lim:
                    prob.append(f"pad {d}.{p['nombre']} a {math.hypot(hx - cx, hy - cy) - R_AGUJERO:.2f} mm del agujero ({hx}, {hy})")
        # zonas por cobre
        for p in pads[d]:
            x1, x2 = p["X"] - p["SX"] / 2, p["X"] + p["SX"] / 2
            y1, y2 = p["Y"] - p["SY"] / 2, p["Y"] + p["SY"] / 2
            if p["red"] in HV and not (x2 <= BARRERA[0] + 0.3 and y2 <= HV_TOPE):
                prob.append(f"cobre de red fuera de la zona: {d}.{p['nombre']} ({p['red']})")
            elif p["red"] in EVSE and not (x2 <= BARRERA[0] + 0.05 and y1 >= ISLA_DESDE):
                prob.append(f"cobre EVSE fuera de la isla: {d}.{p['nombre']}")
            elif p["red"] not in HV and p["red"] not in EVSE and d not in CRUZAN and x1 < BARRERA[1] - 1e-6:
                prob.append(f"cobre SELV en la barrera o la red: {d}.{p['nombre']} ({p['red']})")
    return faltan, prob


# ---------------------------------------------------------------- dibujo
def dibujar(info, pos, ruta):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle, Circle
    fig, ax = plt.subplots(figsize=(19.5, 15))
    ax.add_patch(Rectangle((0, 0), LARGO, ALTO, fill=False, lw=1.5, color="black"))
    ax.add_patch(Rectangle((0, 0), BARRERA[0], HV_TOPE, color="#f5c4b3", alpha=0.35))
    ax.add_patch(Rectangle((0, ISLA_DESDE), BARRERA[0], ALTO - ISLA_DESDE, color="#f0997b", alpha=0.30))
    ax.add_patch(Rectangle((BARRERA[0], 0), BARRERA[1] - BARRERA[0], ALTO, color="#cccccc", alpha=0.5, hatch="//"))
    ax.add_patch(Rectangle((BARRERA[1], 0), LARGO - BARRERA[1], ALTO, color="#9fe1cb", alpha=0.18))
    for x in (5, LARGO - 5):
        ax.axvline(x, color="gray", lw=0.6, ls=":")
    for hx, hy in AGUJEROS:
        ax.add_patch(Circle((hx, hy), R_AGUJERO, fill=False, color="black"))
    for fx, fy in FIDUCIALES:
        ax.add_patch(Circle((fx, fy), 1.0, fill=False, color="#ba7517"))
        ax.add_patch(Circle((fx, fy), 0.5, color="#ba7517"))
    for d, p in pos.items():
        if d not in info:
            continue
        b = caja_en_placa(info[d], p)
        ax.add_patch(Rectangle((b[0], b[1]), b[2] - b[0], b[3] - b[1], fill=False, lw=0.6,
                               color="#7f77dd" if d not in ("F1B", "F2B") else "#bbbbbb", ls="-" if d not in ("F1B", "F2B") else "--"))
        for q in pads_en_placa(info[d], p):
            col = "#d85a30" if q["red"] in HV else "#993556" if q["red"] in EVSE else "#185fa5" if q["red"] == "GND" else "#3b6d11"
            ax.add_patch(Rectangle((q["X"] - q["SX"] / 2, q["Y"] - q["SY"] / 2), q["SX"], q["SY"], color=col, alpha=0.75, lw=0))
        tam = 7 if (b[2] - b[0]) * (b[3] - b[1]) > 60 else 5
        ax.text((b[0] + b[2]) / 2, (b[1] + b[3]) / 2, d, ha="center", va="center", fontsize=tam)
    ax.set_xlim(-8, LARGO + 8)
    ax.set_ylim(-8, ALTO + 10)
    ax.set_aspect("equal")
    ax.set_xticks(range(0, int(LARGO) + 1, 10))
    ax.set_yticks(range(0, int(ALTO) + 1, 10))
    ax.grid(lw=0.2)
    fig.tight_layout()
    fig.savefig(ruta, dpi=110)


# ---------------------------------------------------------------- script de Altium
def _orden(d):
    return (d.rstrip("0123456789"), int("0" + "".join(ch for ch in d if ch.isdigit())))


def escribir_pas(info, ruta):
    """reorganizar_f8.pas: procedimiento ReorganizarF8 (borra lo libre, ubica, fiduciales, designadores, serigrafía).

    Los agujeros M3 y los fiduciales ya existen (AgujerosF8 del 20 oct): aquí solo se mueven los fiduciales."""
    import serigrafia_f8 as sg
    des = sg.designadores(info, POS)
    L = [
        "{ Generado por docs/tools/ubicacion_f8.py (F8, 20 oct 2026). Uso: con EVSE_Monitor.PcbDoc activo,",
        "  File > Run Script... > reorganizar_f8.pas > ReorganizarF8. Coordenadas en mm desde el origen del usuario",
        "  (esquina inferior izquierda de la placa).",
        "  1) borra pistas, vias y arcos libres de cobre (el prerruteo) y los textos/lineas libres de Top Overlay;",
        "  2) ubica los 132 componentes y mueve los fiduciales FID1-FID3;",
        "  3) designadores horizontales, 0,8 mm (1,0 mm en piezas grandes), trazo 0,15 mm;",
        "  4) serigrafia fija: PELIGRO 240 VAC, bordes de la barrera, nombre y version. }",
        "",
        "Var Board : IPCB_Board;",
        "    Faltan, FallosTexto : String;",
        "    Borrados : Integer;",
        "",
        "Procedure BorrarLibres;",
        "Var It : IPCB_BoardIterator;",
        "    Obj : IPCB_Primitive;",
        "    Lista : TInterfaceList;",
        "    i : Integer;",
        "Begin",
        "    Lista := TInterfaceList.Create;",
        "    It := Board.BoardIterator_Create;",
        "    It.AddFilter_ObjectSet(MkSet(eTrackObject, eViaObject, eArcObject, eTextObject));",
        "    It.AddFilter_LayerSet(MkSet(eTopLayer, eBottomLayer, eMultiLayer, eTopOverlay));",
        "    It.AddFilter_Method(eProcessAll);",
        "    Obj := It.FirstPCBObject;",
        "    While Obj <> Nil Do",
        "    Begin",
        "        If Not Obj.InComponent Then Lista.Add(Obj);",
        "        Obj := It.NextPCBObject;",
        "    End;",
        "    Board.BoardIterator_Destroy(It);",
        "    For i := 0 To Lista.Count - 1 Do",
        "    Begin",
        "        Obj := Lista.Items[i];",
        "        Board.RemovePCBObject(Obj);",
        "    End;",
        "    Borrados := Lista.Count;",
        "    Lista.Free;",
        "End;",
        "",
        "Procedure Ubica(Des : String; X, Y, Rot : Double);",
        "Var Comp : IPCB_Component;",
        "Begin",
        "    Comp := Board.GetPcbComponentByRefDes(Des);",
        "    If Comp = Nil Then",
        "    Begin",
        "        Faltan := Faltan + ' ' + Des;",
        "        Exit;",
        "    End;",
        "    PCBServer.SendMessageToRobots(Comp.I_ObjectAddress, c_Broadcast, PCBM_BeginModify, c_NoEventData);",
        "    Comp.Rotation := Rot;",
        "    Comp.MoveToXY(Board.XOrigin + MMsToCoord(X), Board.YOrigin + MMsToCoord(Y));",
        "    PCBServer.SendMessageToRobots(Comp.I_ObjectAddress, c_Broadcast, PCBM_EndModify, c_NoEventData);",
        "End;",
        "",
        "Procedure Fiducial(Nombre : String; X, Y : Double);",
        "Var It : IPCB_BoardIterator;",
        "    Pd : IPCB_Pad;",
        "    Hallado : IPCB_Pad;",
        "Begin",
        "    Hallado := Nil;",
        "    It := Board.BoardIterator_Create;",
        "    It.AddFilter_ObjectSet(MkSet(ePadObject));",
        "    It.AddFilter_LayerSet(AllLayers);",
        "    It.AddFilter_Method(eProcessAll);",
        "    Pd := It.FirstPCBObject;",
        "    While Pd <> Nil Do",
        "    Begin",
        "        If (Not Pd.InComponent) And (Pd.Name = Nombre) Then Hallado := Pd;",
        "        Pd := It.NextPCBObject;",
        "    End;",
        "    Board.BoardIterator_Destroy(It);",
        "    If Hallado = Nil Then",
        "    Begin",
        "        Faltan := Faltan + ' ' + Nombre;",
        "        Exit;",
        "    End;",
        "    PCBServer.SendMessageToRobots(Hallado.I_ObjectAddress, c_Broadcast, PCBM_BeginModify, c_NoEventData);",
        "    Hallado.X := Board.XOrigin + MMsToCoord(X);",
        "    Hallado.Y := Board.YOrigin + MMsToCoord(Y);",
        "    PCBServer.SendMessageToRobots(Hallado.I_ObjectAddress, c_Broadcast, PCBM_EndModify, c_NoEventData);",
        "End;",
        "",
        "Procedure Designador(Des : String; X, Y, Alto : Double);",
        "Var Comp : IPCB_Component;",
        "Begin",
        "    Comp := Board.GetPcbComponentByRefDes(Des);",
        "    If Comp = Nil Then Exit;",
        "    Try",
        "        Comp.NameOn := True;",
        "        Comp.ChangeNameAutoposition := eAutoPos_Manual;",
        "    Except",
        "    End;",
        "    Try",
        "        PCBServer.SendMessageToRobots(Comp.Name.I_ObjectAddress, c_Broadcast, PCBM_BeginModify, c_NoEventData);",
        "        Comp.Name.Size := MMsToCoord(Alto);",
        "        Comp.Name.Width := MMsToCoord(0.15);",
        "        Comp.Name.Rotation := 0;",
        "        Comp.Name.XLocation := Board.XOrigin + MMsToCoord(X);",
        "        Comp.Name.YLocation := Board.YOrigin + MMsToCoord(Y);",
        "        PCBServer.SendMessageToRobots(Comp.Name.I_ObjectAddress, c_Broadcast, PCBM_EndModify, c_NoEventData);",
        "    Except",
        "        FallosTexto := FallosTexto + ' ' + Des;",
        "    End;",
        "End;",
        "",
        "Procedure Texto(Txt : String; X, Y, Alto, Grosor, Rot : Double);",
        "Var Tx : IPCB_Text;",
        "Begin",
        "    Tx := PCBServer.PCBObjectFactory(eTextObject, eNoDimension, eCreate_Default);",
        "    Tx.XLocation := Board.XOrigin + MMsToCoord(X);",
        "    Tx.YLocation := Board.YOrigin + MMsToCoord(Y);",
        "    Tx.Layer := eTopOverlay;",
        "    Tx.Text := Txt;",
        "    Tx.Size := MMsToCoord(Alto);",
        "    Tx.Width := MMsToCoord(Grosor);",
        "    Tx.Rotation := Rot;",
        "    Board.AddPCBObject(Tx);",
        "    PCBServer.SendMessageToRobots(Board.I_ObjectAddress, c_Broadcast, PCBM_BoardRegisteration, Tx.I_ObjectAddress);",
        "End;",
        "",
        "Procedure Linea(X1, Y1, X2, Y2, Ancho : Double);",
        "Var Tr : IPCB_Track;",
        "Begin",
        "    Tr := PCBServer.PCBObjectFactory(eTrackObject, eNoDimension, eCreate_Default);",
        "    Tr.X1 := Board.XOrigin + MMsToCoord(X1);",
        "    Tr.Y1 := Board.YOrigin + MMsToCoord(Y1);",
        "    Tr.X2 := Board.XOrigin + MMsToCoord(X2);",
        "    Tr.Y2 := Board.YOrigin + MMsToCoord(Y2);",
        "    Tr.Width := MMsToCoord(Ancho);",
        "    Tr.Layer := eTopOverlay;",
        "    Board.AddPCBObject(Tr);",
        "    PCBServer.SendMessageToRobots(Board.I_ObjectAddress, c_Broadcast, PCBM_BoardRegisteration, Tr.I_ObjectAddress);",
        "End;",
        "",
        "Procedure ReorganizarF8;",
        "Begin",
        "    Board := PCBServer.GetCurrentPCBBoard;",
        "    If Board = Nil Then",
        "    Begin",
        "        ShowMessage('Abre EVSE_Monitor.PcbDoc (pestana activa) y vuelve a correr el script.');",
        "        Exit;",
        "    End;",
        "    Faltan := '';",
        "    FallosTexto := '';",
        "    PCBServer.PreProcess;",
        "    BorrarLibres;",
    ]
    for d in sorted(POS, key=_orden):
        x, y, r = POS[d]
        L.append(f"    Ubica('{d}', {x:.3f}, {y:.3f}, {r:.0f});")
    for k, (fx, fy) in enumerate(FIDUCIALES, 1):
        L.append(f"    Fiducial('FID{k}', {fx:.3f}, {fy:.3f});")
    for d in sorted(des, key=_orden):
        x, y, h = des[d]
        L.append(f"    Designador('{d}', {x:.3f}, {y:.3f}, {h:.2f});")
    for txt, x, y, h, g, r in sg.TEXTOS:
        L.append(f"    Texto('{txt}', {x:.3f}, {y:.3f}, {h:.2f}, {g:.2f}, {r});")
    for x1, y1, x2, y2, w in sg.LINEAS:
        L.append(f"    Linea({x1:.3f}, {y1:.3f}, {x2:.3f}, {y2:.3f}, {w:.2f});")
    L += [
        "    PCBServer.PostProcess;",
        "    Board.ViewManager_FullUpdate;",
        f"    ShowMessage('Listo: borrados ' + IntToStr(Borrados) + ' objetos libres; {len(POS)} componentes y "
        f"{len(FIDUCIALES)} fiduciales ubicados.'",
        "        + Chr(13) + 'No encontre:' + Faltan + Chr(13) + 'Designadores con error:' + FallosTexto",
        "        + Chr(13) + 'Guarda (Ctrl+S) y cierra Altium para refrescar las lineas de conexion.');",
        "End;",
        "",
    ]
    ruta.write_text("\n".join(L), encoding="latin-1")
    escribir_prjscr(ruta.with_suffix(".PrjScr"), [ruta.name])
    for viejo in ("ubicar_f8.pas", "ubicar_f8.PrjScr", "ruteo_f8.pas"):
        (ruta.parent / viejo).unlink(missing_ok=True)
    return des


def escribir_prjscr(ruta, docs):
    """Proyecto de script (*.PrjScr) con los .pas dados.

    Altium (AD 25) solo corre scripts que están en un proyecto de script: File » Run Script… » Browse pide
    un *.PrjScr. Mismo formato que el proyecto del Library Loader (Documents/AltiumLL/AltiumLL.PrjScr)."""
    prj = ["[Design]", "Version=1.0", "HierarchyMode=0", "OpenOutputs=1", "ArchiveProject=0", "TimestampOutput=0",
           "SeparateFolders=0", "OutputPath=", "LogFolderPath=", "",
           "[Preferences]", "PrefsVaultGUID=", "PrefsRevisionGUID=", ""]
    for k, n in enumerate(docs, 1):
        prj += [f"[Document{k}]", f"DocumentPath={n}", "AnnotationEnabled=1", "AnnotateStartValue=1",
                "AnnotationIndexControlEnabled=0", "AnnotateSuffix=", "AnnotateScope=All", "AnnotateOrder=-1",
                "DoLibraryUpdate=1", "DoDatabaseUpdate=1", "ClassGenCCAutoEnabled=1", "ClassGenCCAutoRoomEnabled=1",
                "ClassGenNCAutoScope=None", "DItemRevisionGUID=", "GenerateClassCluster=0", "DocumentUniqueId=", ""]
    ruta.write_text("\r\n".join(prj), encoding="latin-1")


def main():
    info = leer()
    faltan, prob = revisar(info, POS)
    print(f"Ubicados: {len([d for d in POS if d in info])} de {len(info)}; faltan {len(faltan)}")
    if faltan:
        print("  ", " ".join(sorted(faltan)))
    print(f"Problemas: {len(prob)}")
    for p in prob:
        print("  -", p)
    salida = RAIZ / "docs" / "revisiones" / "F8_ubicacion.png"
    dibujar(info, POS, salida)
    print("Dibujo:", salida)
    if "--pas" in sys.argv:
        des = escribir_pas(info, Path(__file__).with_name("reorganizar_f8.pas"))
        print(f"Script de Altium: docs/tools/reorganizar_f8.PrjScr con reorganizar_f8.pas ({len(des)} designadores)")


if __name__ == "__main__":
    main()
