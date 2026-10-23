# -*- coding: utf-8 -*-
"""F9: bloque de identificación en la serigrafía y textos libres al mínimo de PCBWay (Altium CERRADO).

PCBWay pide letras de al menos 0,8 mm de alto y 0,15 mm de trazo (capabilities, 22 oct 2026). Los textos libres
estaban en fuente de trazo de 0,508 mm (0,762 el de PELIGRO) con 0,127 mm de trazo.

- Bloque de identificación en Top Overlay, en el rincón libre del SELV de abajo a la derecha (x 104,6–123,2 mm,
  y 5,9–18,0 mm; debajo solo hay vías de costura tapadas): marco de 0,2 mm y, en TrueType Arial Bold (la fuente
  de trazo no tiene tildes), «EVSE MONITOR», «Rev 1.0 · 2026-10», una línea, «Nicolás Gómez» y «Hardware en IoT».
  El texto libre «EVSE MONITOR  REV 1.0  2026» del borde de abajo pasa a ser la primera línea del bloque.
- «ZONA DE RED 120-240 VAC», «HABILITACION EVSE (J2)» y «PELIGRO!! 240 VAC»: 1,0 mm de alto y 0,15 mm de trazo
  (mismo lugar y texto).

Formato de Texts6 (bloque 0, como lo lee el importador de Altium de KiCad): capa [0], componente [7], posición
[13] (esquina inferior izquierda) y otra vez en [244], alto [21], fuente de trazo [25], rotación [27], espejo [35],
trazo [36], comentario [40], designador [41], tipo de fuente [43] (0 trazo, 1 TrueType), negrita [44], cursiva
[45], nombre de la fuente [46] (UTF-16), índice en WideStrings6 [115], caja del texto [124] y [128], capa V7 [226].
El bloque 1 es el texto en ASCII (largo + caracteres); WideStrings6 lo repite en UTF-16 (índice, bytes, texto+\\0).

Uso: python docs/tools/serigrafia_f9.py            # muestra lo que haría y dibuja la vista previa
     python docs/tools/serigrafia_f9.py --escribir # respalda el PcbDoc en docs/respaldos/ y escribe
"""
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import altium_ole as ao  # noqa: E402
import aplicar_ruteo_f8 as ap  # noqa: E402
import revisar_pcb as rv  # noqa: E402

U, O = rv.U, 25.4
RAIZ = Path(__file__).resolve().parents[2]
TOP_OVERLAY, OVERLAY_V7 = 33, bytes.fromhex("06000301")
MARCO = (104.6, 5.9, 123.2, 18.0)
ANCHO_MARCO = 0.2
SEPARADOR_Y = 11.9
# texto, alto (mm), x, y (esquina inferior izquierda)
BLOQUE = [("EVSE MONITOR", 2.0, 105.4, 15.0),
          ("Rev 1.0 · 2026-10", 1.2, 105.4, 12.7),
          ("Nicolás Gómez", 1.6, 105.4, 9.2),
          ("Hardware en IoT", 1.2, 105.4, 6.8)]
SEGURIDAD = {"ZONA DE RED 120-240 VAC", "HABILITACION EVSE (J2)", "PELIGRO!! 240 VAC"}
ALTO_MIN, TRAZO_MIN = 1.0, 0.15


def u(mm):
    return int(round(mm / U))


def leer_ws(data):
    out, i = [], 0
    while i < len(data):
        idx, ln = struct.unpack_from("<II", data, i)
        out.append([idx, data[i + 8:i + 8 + ln].decode("utf-16-le").rstrip("\x00")])
        i += 8 + ln
    return out


def unir_ws(ents):
    return b"".join(struct.pack("<II", idx, 2 * (len(s) + 1)) + s.encode("utf-16-le") + b"\x00\x00" for idx, s in ents)


def ancho_aprox(txt, alto):
    """Ancho de Arial Bold (avances en em de la fuente) para la caja del texto."""
    try:
        from matplotlib.font_manager import FontProperties
        from matplotlib.textpath import TextPath
        p = TextPath((0, 0), txt, size=alto, prop=FontProperties(family="Arial", weight="bold"))
        return p.get_extents().width
    except Exception:
        return 0.62 * alto * len(txt)


def texto_truetype(g, b1, txt, alto, x, y, ws_idx):
    g = bytearray(g)
    g[0] = TOP_OVERLAY
    struct.pack_into("<ii", g, 13, ap.interno(x), ap.interno(y))
    struct.pack_into("<ii", g, 244, ap.interno(x), ap.interno(y))
    struct.pack_into("<i", g, 21, u(alto))
    struct.pack_into("<d", g, 27, 0.0)
    g[35], g[40], g[41], g[43], g[44], g[45] = 0, 0, 0, 1, 1, 0
    g[46:110] = "Arial".encode("utf-16-le").ljust(64, b"\x00")
    struct.pack_into("<I", g, 115, ws_idx)
    struct.pack_into("<ii", g, 124, u(ancho_aprox(txt, alto)), u(alto))
    g[226:230] = OVERLAY_V7
    a = txt.encode("cp1252")
    return [bytes(g), bytes([len(a)]) + a + b1[1 + b1[0]:]]


def linea(plantilla, x1, y1, x2, y2):
    g = bytearray(plantilla)
    g[0] = TOP_OVERLAY
    g[41:45] = OVERLAY_V7
    struct.pack_into("<HH", g, 3, 0xFFFF, 0xFFFF)
    struct.pack_into("<H", g, 7, 0xFFFF)
    struct.pack_into("<iiii", g, 13, ap.interno(x1), ap.interno(y1), ap.interno(x2), ap.interno(y2))
    struct.pack_into("<i", g, 29, u(ANCHO_MARCO))
    return (4, [bytes(g)])


def calcular():
    pcb = rv.PCB
    tx = ap.registros(ao.leer_stream(pcb, "Texts6/Data"), 2)
    ws = leer_ws(ao.leer_stream(pcb, "WideStrings6/Data"))
    texto_ws = {idx: s for idx, s in ws}
    libres = {texto_ws[struct.unpack_from("<I", bl[0], 115)[0]]: k for k, (t, bl) in enumerate(tx)
              if struct.unpack_from("<H", bl[0], 7)[0] == 0xFFFF and bl[0][0] == TOP_OVERLAY}
    assert "EVSE MONITOR  REV 1.0  2026" in libres, "el texto del borde de abajo ya se cambió"
    cambios = []
    # textos de seguridad al mínimo de PCBWay
    for s in SEGURIDAD:
        k = libres[s]
        g = bytearray(tx[k][1][0])
        antes = (struct.unpack_from("<i", g, 21)[0] * U, struct.unpack_from("<i", g, 36)[0] * U)
        struct.pack_into("<i", g, 21, u(max(ALTO_MIN, antes[0])))
        struct.pack_into("<i", g, 36, u(max(TRAZO_MIN, antes[1])))
        tx[k] = (5, [bytes(g), tx[k][1][1]])
        cambios.append(f"«{s}»: {antes[0]:.3f}/{antes[1]:.3f} → {ALTO_MIN}/{TRAZO_MIN} mm")
    # bloque: el texto del borde pasa a ser la primera línea; las otras son nuevas
    k0 = libres["EVSE MONITOR  REV 1.0  2026"]
    g0, b0 = tx[k0][1]
    idx0 = struct.unpack_from("<I", g0, 115)[0]
    nuevo_idx = max(i for i, _ in ws) + 1
    for n, (s, alto, x, y) in enumerate(BLOQUE):
        idx = idx0 if n == 0 else nuevo_idx + n - 1
        reg = texto_truetype(g0, b0, s, alto, x, y, idx)
        if n == 0:
            tx[k0] = (5, reg)
            texto_ws[idx0] = s
        else:
            tx.append((5, reg))
            texto_ws[idx] = s
        cambios.append(f"«{s}»: TrueType Arial Bold {alto} mm en ({x}, {y})" + (" (era el texto del borde)" if n == 0 else ""))
    ws = sorted(texto_ws.items())
    tr = ap.registros(ao.leer_stream(pcb, "Tracks6/Data"), 1)
    plantilla = next(bl[0] for t, bl in tr if bl[0][0] == 57 and struct.unpack_from("<H", bl[0], 7)[0] == 0xFFFF)
    x1, y1, x2, y2 = MARCO
    nuevas = [linea(plantilla, *s) for s in ((x1, y1, x2, y1), (x2, y1, x2, y2), (x2, y2, x1, y2), (x1, y2, x1, y1),
                                            (x1 + 0.6, SEPARADOR_Y, x2 - 0.6, SEPARADOR_Y))]
    cambios.append(f"marco {x2 - x1:.1f} × {y2 - y1:.1f} mm y línea separadora, {ANCHO_MARCO} mm")
    return tx, ws, tr + nuevas, cambios


def vista_previa(ruta):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.font_manager import FontProperties
    from matplotlib.patches import Circle, Rectangle
    from matplotlib.textpath import TextPath
    from matplotlib.patches import PathPatch
    fig, ax = plt.subplots(figsize=(6, 4.2), dpi=200)
    ax.set_facecolor("#1f5a3a")
    x1, y1, x2, y2 = MARCO
    ax.add_patch(Rectangle((x1, y1), x2 - x1, y2 - y1, fill=False, ec="white", lw=ANCHO_MARCO * 7))
    ax.plot([x1 + 0.6, x2 - 0.6], [SEPARADOR_Y] * 2, color="white", lw=ANCHO_MARCO * 7)
    for s, alto, x, y in BLOQUE:
        p = TextPath((x, y + 0.2 * alto), s, size=alto, prop=FontProperties(family="Arial", weight="bold"))
        ax.add_patch(PathPatch(p, fc="white", ec="none"))
    for vx in (106, 113.5, 121):
        for vy in (9.5, 17):
            ax.add_patch(Circle((vx, vy), 0.4, fc="#2d7a4f", ec="none", zorder=0))
    ax.add_patch(Circle((126, 4), 1.6, fc="black"))
    ax.add_patch(Rectangle((96, 1.4), 7.5, 7.3, fill=False, ec="white", lw=0.7))
    ax.text(99.7, 5, "J6", color="white", ha="center", va="center", fontsize=7)
    ax.add_patch(Rectangle((104.77, 19.68), 1.46, 2.64, fc="#c8a43c"))
    ax.plot([126, 130], [0, 0], color="#9bd19b", lw=1)
    t = __import__("numpy").linspace(-90, 0, 30)
    ax.plot(126 + 4 * __import__("numpy").cos(__import__("numpy").radians(t)),
            4 + 4 * __import__("numpy").sin(__import__("numpy").radians(t)), color="#9bd19b", lw=1)
    ax.plot([130, 130], [4, 22], color="#9bd19b", lw=1)
    ax.set_xlim(94, 131)
    ax.set_ylim(-1, 23)
    ax.set_aspect("equal")
    ax.set_title("Bloque de identificación (Top Overlay), esquina inferior derecha", fontsize=8)
    ax.tick_params(labelsize=6)
    fig.tight_layout()
    fig.savefig(ruta)
    plt.close(fig)


def main():
    tx, ws, tr, cambios = calcular()
    for c in cambios:
        print("  ", c)
    prev = RAIZ / "docs" / "revisiones" / "bloque_serigrafia_f9.png"
    vista_previa(prev)
    print("Vista previa:", prev)
    for s, alto, x, y in BLOQUE:
        print(f"   {s!r}: ancho ≈ {ancho_aprox(s, alto):.1f} mm (hasta x = {x + ancho_aprox(s, alto):.1f}; el marco "
              f"termina en {MARCO[2]})")
    if "--escribir" not in sys.argv:
        print("\n(prueba: no se escribió nada; usa --escribir)")
        return
    if ao.altium_abierto():
        sys.exit("Altium está abierto (X2.exe): guarda, ciérralo y vuelve a correr.")
    pcb = rv.PCB
    print("Respaldo:", ao.respaldo(pcb, "antes_serigrafia_f9"))
    ao.escribir_streams(pcb, {"Texts6/Data": ap.unir(tx), "Texts6/Header": struct.pack("<I", len(tx)),
                              "WideStrings6/Data": unir_ws(ws), "WideStrings6/Header": struct.pack("<I", len(ws)),
                              "Tracks6/Data": ap.unir(tr), "Tracks6/Header": struct.pack("<I", len(tr))})
    vuelta = leer_ws(ao.leer_stream(pcb, "WideStrings6/Data"))
    print(f"Escrito: {len(tx)} textos, {len(vuelta)} cadenas (últimas: {[s for _, s in vuelta[-3:]]}), {len(tr)} pistas")


if __name__ == "__main__":
    main()
