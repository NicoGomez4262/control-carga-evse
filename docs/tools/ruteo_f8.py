# -*- coding: utf-8 -*-
"""F8: prerruteo de los troncos de EVSE_Monitor.PcbDoc (red, isla EVSE, 12 V, R-78CK) y keepouts.

Uso:
    python docs/tools/ruteo_f8.py          # revisa el prerruteo y dibuja docs/revisiones/F8_prerruteo.png
    python docs/tools/ruteo_f8.py --pas    # además escribe docs/tools/ruteo_f8.pas (en ubicar_f8.PrjScr)

El resto (U2 lado HV, divisor a U2, señales, USB, GND) lo rutea el autorouter de Altium (Situs) con
estas pistas bloqueadas, y después se ponen los polígonos de GND.

Revisión, con la ubicación de ubicacion_f8.POS y los pads leídos del PcbDoc:
- cada pista contra los pads, vías y pistas de otra red en su misma capa (los pads THT y las vías están en
  las dos) con la distancia de ubicacion_f8.regla(): red–resto 6,4; EVSE–resto 6,4; L1–L2 3,2; red
  interna 0,5; EVSE_A–B 1,5; resto 0,25 mm. Los agujeros M3 y los fiduciales cuentan como pads sin red;
- que cada extremo de pista caiga en un pad, una vía u otra pista de su misma red;
- pistas de red dentro de la zona de red y fuera de los keepouts.
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ubicacion_f8 as u  # noqa: E402

RAIZ = Path(__file__).resolve().parents[2]
T, B = 1, 2   # capas: Top, Bottom

# ---------------------------------------------------------------- prerruteo: (red, capa, ancho mm, [(x, y), ...])
PISTAS = [
    # --- red: J1 → fusibles (entrada arriba) → RV1 → PS1
    ("AC_L1", T, 1.5, [(5.5, 72.4), (28.25, 72.4), (28.25, 62.48)]),
    ("AC_L2", T, 1.5, [(5.5, 67.4), (17.25, 67.4), (17.25, 62.48)]),
    ("AC_L1_F", T, 1.5, [(28.25, 48.72), (28.25, 44.6), (27.4, 36.9), (24.0, 27.8), (13.0, 27.8)]),
    ("AC_L1_F", T, 1.0, [(28.25, 44.6), (36.0, 43.27)]),
    ("AC_L2_F", T, 1.5, [(17.25, 48.72), (17.25, 44.6), (18.1, 36.9), (8.0, 36.9), (8.0, 12.0), (13.0, 12.0), (13.0, 7.0)]),
    # AC_L2_F (HGND de U2) por abajo, por debajo del divisor, hasta una vía junto al pin 8 de U2
    ("AC_L2_F", B, 1.0, [(17.25, 44.6), (21.0, 38.9), (39.5, 38.9), (39.5, 56.6), (43.6, 58.0)]),
    ("AC_L2_F", T, 0.5, [(43.6, 58.0), (43.63, 59.56), (43.63, 60.83)]),
    ("AC_L2_F", T, 0.5, [(43.6, 58.0), (41.0, 57.55)]),
    # --- divisor R2–R5 (pads vecinos)
    ("HV_D1", T, 0.5, [(36.0, 46.73), (36.0, 50.27)]),
    ("HV_D2", T, 0.5, [(36.0, 53.73), (36.0, 57.27)]),
    ("HV_D3", T, 0.5, [(36.0, 60.73), (36.0, 64.27)]),
    # --- isla EVSE: J2 → K1 (salida)
    ("EVSE_EN_B", T, 0.8, [(5.5, 87.0), (44.05, 87.0)]),
    ("EVSE_EN_A", T, 0.8, [(5.5, 82.0), (40.0, 82.0), (42.5, 84.46), (44.05, 84.46)]),
    # --- 12 V: PS1 → D1 → +VIN (C2, D3, TP2, L1, D2) ← D2 ← J6
    ("VIN_ACDC", T, 1.0, [(58.0, 15.0), (65.0, 15.0)]),
    ("+VIN", T, 1.0, [(72.0, 15.0), (76.95, 15.0), (76.95, 8.0)]),
    ("+VIN", T, 1.0, [(76.95, 15.0), (85.0, 15.0), (89.5, 14.5)]),
    ("+VIN", T, 1.0, [(85.0, 15.0), (86.6, 22.5)]),
    ("+VIN", T, 1.0, [(76.95, 15.0), (78.3, 21.5), (73.0, 30.0)]),
    ("VIN_BANCO", T, 1.0, [(98.0, 5.0), (98.0, 10.0), (96.5, 14.5)]),
    # --- R-78CK: entrada (L1 → C6, C1, U1.1) y salida (U1.3 → C1, C7, L2)
    ("NetC1_2", T, 0.6, [(89.4, 22.5), (92.0, 19.21), (97.6, 19.21), (98.0, 19.6), (98.0, 26.0)]),
    ("NetC1_2", T, 0.6, [(98.0, 21.0), (99.2, 21.0)]),
    ("NetC1_1", T, 0.6, [(103.08, 26.0), (103.08, 23.25), (110.25, 23.25)]),
    ("NetC1_1", T, 0.6, [(103.08, 23.25), (103.08, 21.0), (100.8, 21.0)]),
    ("NetC1_1", T, 0.6, [(103.08, 21.0), (105.5, 20.17)]),
    # --- +3V3 a la salida de L2 (C3, C4, C5)
    ("+3V3", T, 0.8, [(110.25, 26.75), (114.5, 26.75), (117.5, 23.5)]),
    ("+3V3", T, 0.6, [(110.25, 26.75), (110.5, 31.78), (112.4, 31.78)]),
]
VIAS = [("AC_L2_F", 43.6, 58.0, 0.8, 0.4)]
# keepouts (capa Keep-Out): barrera y hueco red–isla
KEEPOUTS = [(45.4, 0.0, 51.4, 100.0), (0.0, 74.6, 45.4, 80.6)]


# ---------------------------------------------------------------- geometría
def d_punto_seg(p, a, b):
    ax, ay = a
    bx, by = b
    px, py = p
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    t = 0.0 if L == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def se_cruzan(a, b, c, d):
    def o(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    return (o(a, b, c) * o(a, b, d) < 0) and (o(c, d, a) * o(c, d, b) < 0)


def d_seg_seg(a, b, c, d):
    if se_cruzan(a, b, c, d):
        return 0.0
    return min(d_punto_seg(a, c, d), d_punto_seg(b, c, d), d_punto_seg(c, a, b), d_punto_seg(d, a, b))


def d_seg_rect(a, b, r):
    x1, y1, x2, y2 = r
    if x1 <= a[0] <= x2 and y1 <= a[1] <= y2:
        return 0.0
    esq = [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]
    return min(d_seg_seg(a, b, esq[i], esq[(i + 1) % 4]) for i in range(4))


def segmentos():
    out = []
    for i, (red, capa, w, pts) in enumerate(PISTAS):
        for a, b in zip(pts, pts[1:]):
            out.append(dict(red=red, capa=capa, w=w, a=a, b=b, pista=i))
    return out


def pads_todos(info):
    out = []
    for d, pos in u.POS.items():
        for p in u.pads_en_placa(info[d], pos):
            capas = {T} if p["smd"] else {T, B}
            out.append(dict(des=f"{d}.{p['nombre']}", red=p["red"], capas=capas, redondo=p["redondo"],
                            x=p["X"], y=p["Y"], sx=p["SX"], sy=p["SY"]))
    for i, (hx, hy) in enumerate(u.AGUJEROS, 1):
        out.append(dict(des=f"M{i}", red=None, capas={T, B}, redondo=True, x=hx, y=hy, sx=2 * u.R_AGUJERO, sy=2 * u.R_AGUJERO))
    for i, (fx, fy) in enumerate(u.FIDUCIALES, 1):
        out.append(dict(des=f"FID{i}", red=None, capas={T}, redondo=True, x=fx, y=fy, sx=1.0, sy=1.0))
    return out


def d_seg_pad(s, p):
    if p["redondo"]:
        return d_punto_seg((p["x"], p["y"]), s["a"], s["b"]) - p["sx"] / 2
    r = (p["x"] - p["sx"] / 2, p["y"] - p["sy"] / 2, p["x"] + p["sx"] / 2, p["y"] + p["sy"] / 2)
    return d_seg_rect(s["a"], s["b"], r)


def en_pad(pt, p):
    if p["redondo"]:
        return math.hypot(pt[0] - p["x"], pt[1] - p["y"]) <= p["sx"] / 2 + 1e-6
    return abs(pt[0] - p["x"]) <= p["sx"] / 2 + 1e-6 and abs(pt[1] - p["y"]) <= p["sy"] / 2 + 1e-6


# ---------------------------------------------------------------- revisión
def revisar(info):
    prob = []
    segs = segmentos()
    pads = pads_todos(info)
    vias = [dict(red=r, x=x, y=y, d=dd, capas={T, B}) for r, x, y, dd, _ in VIAS]
    for s in segs:
        for p in pads:
            if s["capa"] not in p["capas"]:
                continue
            r = u.regla(s["red"], p["red"])
            if r is None:
                continue
            if min(abs(s["a"][0] - p["x"]), abs(s["b"][0] - p["x"])) > 25 and min(abs(s["a"][1] - p["y"]), abs(s["b"][1] - p["y"])) > 25:
                continue
            dd = d_seg_pad(s, p) - s["w"] / 2
            if dd < r[0] - 1e-6:
                prob.append(f"{r[1]}: pista {s['red']} {s['a']}-{s['b']} a {dd:.2f} mm de {p['des']} ({p['red']}), pide {r[0]}")
        for v in vias:
            r = u.regla(s["red"], v["red"])
            if r is None:
                continue
            dd = d_punto_seg((v["x"], v["y"]), s["a"], s["b"]) - v["d"] / 2 - s["w"] / 2
            if dd < r[0] - 1e-6:
                prob.append(f"{r[1]}: pista {s['red']} a {dd:.2f} mm de la vía {v['red']}")
        for k in KEEPOUTS:
            if d_seg_rect(s["a"], s["b"], k) - s["w"] / 2 < 0.2:
                prob.append(f"pista {s['red']} {s['a']}-{s['b']} dentro o junto al keepout {k}")
    for i, s in enumerate(segs):
        for t in segs[i + 1:]:
            if s["capa"] != t["capa"] or s["red"] == t["red"]:
                continue
            r = u.regla(s["red"], t["red"])
            dd = d_seg_seg(s["a"], s["b"], t["a"], t["b"]) - (s["w"] + t["w"]) / 2
            if dd < r[0] - 1e-6:
                prob.append(f"{r[1]}: pistas {s['red']} y {t['red']} a {dd:.2f} mm, pide {r[0]}")
    for v in vias:
        for p in pads:
            r = u.regla(v["red"], p["red"])
            if r is None:
                continue
            q = dict(a=(v["x"], v["y"]), b=(v["x"], v["y"]))
            dd = d_seg_pad(q, p) - v["d"] / 2
            if dd < r[0] - 1e-6:
                prob.append(f"{r[1]}: vía {v['red']} a {dd:.2f} mm de {p['des']} ({p['red']})")
    # conectividad de extremos
    for red, capa, w, pts in PISTAS:
        for pt in (pts[0], pts[-1]):
            ok = any(p["red"] == red and capa in p["capas"] and en_pad(pt, p) for p in pads)
            ok = ok or any(v["red"] == red and math.hypot(pt[0] - v["x"], pt[1] - v["y"]) < 1e-3 for v in vias)
            ok = ok or any(s["red"] == red and s["capa"] == capa and d_punto_seg(pt, s["a"], s["b"]) < 1e-3
                           and not (s["a"] in (pts[0], pts[-1]) and s["b"] in pts) for s in segs if s["pista"] != PISTAS.index((red, capa, w, pts)))
            if not ok:
                prob.append(f"extremo suelto: {red} en {pt} (capa {'Top' if capa == T else 'Bottom'})")
    # zonas
    for s in segs:
        hv = s["red"] in u.HV
        for x, y in (s["a"], s["b"]):
            if hv and (x > u.BARRERA[0] or y > u.HV_TOPE):
                prob.append(f"pista de red fuera de su zona: {s['red']} en ({x}, {y})")
    return prob


# ---------------------------------------------------------------- dibujo
def dibujar(info, ruta):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle, Circle
    u.dibujar(info, u.POS, ruta)
    img = plt.imread(str(ruta))
    fig, ax = plt.subplots(figsize=(19.5, 15))
    ax.add_patch(Rectangle((0, 0), u.LARGO, u.ALTO, fill=False, lw=1.2, color="black"))
    for k in KEEPOUTS:
        ax.add_patch(Rectangle((k[0], k[1]), k[2] - k[0], k[3] - k[1], color="#e24b4a", alpha=0.12, hatch="xx"))
    for d, pos in u.POS.items():
        for q in u.pads_en_placa(info[d], pos):
            col = "#d85a30" if q["red"] in u.HV else "#993556" if q["red"] in u.EVSE else "#185fa5" if q["red"] == "GND" else "#3b6d11"
            ax.add_patch(Rectangle((q["X"] - q["SX"] / 2, q["Y"] - q["SY"] / 2), q["SX"], q["SY"], color=col, alpha=0.55, lw=0))
        b = u.caja_en_placa(info[d], pos)
        ax.text((b[0] + b[2]) / 2, (b[1] + b[3]) / 2, d, ha="center", va="center", fontsize=5, color="#444")
    for s in segmentos():
        col = "#c0392b" if s["capa"] == T else "#2e6fd6"
        ax.plot([s["a"][0], s["b"][0]], [s["a"][1], s["b"][1]], color=col, lw=s["w"] * 3.2, alpha=0.8, solid_capstyle="round")
    for r, x, y, dd, h in VIAS:
        ax.add_patch(Circle((x, y), dd / 2, color="#ba7517"))
    for hx, hy in u.AGUJEROS:
        ax.add_patch(Circle((hx, hy), u.R_AGUJERO, fill=False, color="black"))
    ax.set_xlim(-5, u.LARGO + 5)
    ax.set_ylim(-5, u.ALTO + 8)
    ax.set_aspect("equal")
    ax.grid(lw=0.2)
    ax.set_xticks(range(0, int(u.LARGO) + 1, 10))
    ax.set_yticks(range(0, int(u.ALTO) + 1, 10))
    fig.tight_layout()
    fig.savefig(ruta, dpi=110)
    del img


# ---------------------------------------------------------------- script de Altium
def escribir_pas(ruta):
    L = [
        "{ Generado por docs/tools/ruteo_f8.py: prerruteo de los troncos (red, isla EVSE, 12 V, R-78CK) y keepouts.",
        "  Uso: con EVSE_Monitor.PcbDoc activo, File > Run Script... > ruteo_f8.pas > PrerruteoF8.",
        "  Coordenadas en mm desde el origen del usuario. }",
        "",
        "Var BoardR : IPCB_Board;",
        "    SinRed : String;",
        "",
        "Function Red(Nombre : String) : IPCB_Net;",
        "Var It : IPCB_BoardIterator;",
        "    N : IPCB_Net;",
        "Begin",
        "    Result := Nil;",
        "    It := BoardR.BoardIterator_Create;",
        "    It.AddFilter_ObjectSet(MkSet(eNetObject));",
        "    It.AddFilter_LayerSet(AllLayers);",
        "    It.AddFilter_Method(eProcessAll);",
        "    N := It.FirstPCBObject;",
        "    While (N <> Nil) And (Result = Nil) Do",
        "    Begin",
        "        If N.Name = Nombre Then Result := N;",
        "        N := It.NextPCBObject;",
        "    End;",
        "    BoardR.BoardIterator_Destroy(It);",
        "End;",
        "",
        "Procedure Pista(Nombre : String; Capa : Integer; X1, Y1, X2, Y2, Ancho : Double);",
        "Var Tr : IPCB_Track;",
        "    N : IPCB_Net;",
        "Begin",
        "    Tr := PCBServer.PCBObjectFactory(eTrackObject, eNoDimension, eCreate_Default);",
        "    Tr.X1 := BoardR.XOrigin + MMsToCoord(X1);",
        "    Tr.Y1 := BoardR.YOrigin + MMsToCoord(Y1);",
        "    Tr.X2 := BoardR.XOrigin + MMsToCoord(X2);",
        "    Tr.Y2 := BoardR.YOrigin + MMsToCoord(Y2);",
        "    Tr.Width := MMsToCoord(Ancho);",
        "    If Capa = 1 Then Tr.Layer := eTopLayer Else Tr.Layer := eBottomLayer;",
        "    N := Red(Nombre);",
        "    If N <> Nil Then Tr.Net := N Else SinRed := SinRed + ' ' + Nombre;",
        "    BoardR.AddPCBObject(Tr);",
        "    PCBServer.SendMessageToRobots(BoardR.I_ObjectAddress, c_Broadcast, PCBM_BoardRegisteration, Tr.I_ObjectAddress);",
        "End;",
        "",
        "Procedure NuevaVia(Nombre : String; X, Y, Diam, Hueco : Double);",
        "Var Vi : IPCB_Via;",
        "    N : IPCB_Net;",
        "Begin",
        "    Vi := PCBServer.PCBObjectFactory(eViaObject, eNoDimension, eCreate_Default);",
        "    Vi.X := BoardR.XOrigin + MMsToCoord(X);",
        "    Vi.Y := BoardR.YOrigin + MMsToCoord(Y);",
        "    Vi.Size := MMsToCoord(Diam);",
        "    Vi.HoleSize := MMsToCoord(Hueco);",
        "    Vi.LowLayer := eBottomLayer;",
        "    Vi.HighLayer := eTopLayer;",
        "    N := Red(Nombre);",
        "    If N <> Nil Then Vi.Net := N Else SinRed := SinRed + ' ' + Nombre;",
        "    BoardR.AddPCBObject(Vi);",
        "    PCBServer.SendMessageToRobots(BoardR.I_ObjectAddress, c_Broadcast, PCBM_BoardRegisteration, Vi.I_ObjectAddress);",
        "End;",
        "",
        "Procedure Keepout(X1, Y1, X2, Y2 : Double);",
        "Var Fi : IPCB_Fill;",
        "Begin",
        "    Fi := PCBServer.PCBObjectFactory(eFillObject, eNoDimension, eCreate_Default);",
        "    Fi.X1Location := BoardR.XOrigin + MMsToCoord(X1);",
        "    Fi.Y1Location := BoardR.YOrigin + MMsToCoord(Y1);",
        "    Fi.X2Location := BoardR.XOrigin + MMsToCoord(X2);",
        "    Fi.Y2Location := BoardR.YOrigin + MMsToCoord(Y2);",
        "    Fi.Rotation := 0;",
        "    Fi.Layer := eKeepOutLayer;",
        "    BoardR.AddPCBObject(Fi);",
        "    PCBServer.SendMessageToRobots(BoardR.I_ObjectAddress, c_Broadcast, PCBM_BoardRegisteration, Fi.I_ObjectAddress);",
        "End;",
        "",
        "Procedure PrerruteoF8;",
        "Begin",
        "    BoardR := PCBServer.GetCurrentPCBBoard;",
        "    If BoardR = Nil Then",
        "    Begin",
        "        ShowMessage('Abre EVSE_Monitor.PcbDoc y vuelve a correr el script.');",
        "        Exit;",
        "    End;",
        "    SinRed := '';",
        "    PCBServer.PreProcess;",
    ]
    for k in KEEPOUTS:
        L.append(f"    Keepout({k[0]:.3f}, {k[1]:.3f}, {k[2]:.3f}, {k[3]:.3f});")
    n = 0
    for red, capa, w, pts in PISTAS:
        for a, b in zip(pts, pts[1:]):
            L.append(f"    Pista('{red}', {capa}, {a[0]:.3f}, {a[1]:.3f}, {b[0]:.3f}, {b[1]:.3f}, {w:.2f});")
            n += 1
    for red, x, y, dd, h in VIAS:
        L.append(f"    NuevaVia('{red}', {x:.3f}, {y:.3f}, {dd:.2f}, {h:.2f});")
    L += [
        "    PCBServer.PostProcess;",
        "    BoardR.ViewManager_FullUpdate;",
        f"    If SinRed = '' Then ShowMessage('Listo: {n} tramos, {len(VIAS)} via(s) y {len(KEEPOUTS)} keepouts.')",
        "    Else ShowMessage('Listo, pero no encontre las redes:' + SinRed);",
        "End;",
        "",
    ]
    ruta.write_text("\n".join(L), encoding="latin-1")
    return n


def main():
    info = u.leer()
    prob = revisar(info)
    print(f"Prerruteo: {len(PISTAS)} pistas, {len(segmentos())} tramos, {len(VIAS)} vías, {len(KEEPOUTS)} keepouts")
    print(f"Problemas: {len(prob)}")
    for p in prob:
        print("  -", p)
    salida = RAIZ / "docs" / "revisiones" / "F8_prerruteo.png"
    dibujar(info, salida)
    print("Dibujo:", salida)
    if "--pas" in sys.argv:
        n = escribir_pas(Path(__file__).with_name("ruteo_f8.pas"))
        u.escribir_prjscr(Path(__file__).with_name("ubicar_f8.PrjScr"))
        print(f"Script de Altium: docs/tools/ruteo_f8.pas ({n} tramos), agregado a ubicar_f8.PrjScr")


if __name__ == "__main__":
    main()
