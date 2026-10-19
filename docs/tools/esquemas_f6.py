# -*- coding: utf-8 -*-
"""Esquemas literales por bloque de la hoja 06_ACTUACION (F6). Escribe docs/esquemas/F6_*.svg.

Reusa las funciones de dibujo de esquemas.py y esquemas_f4.py (ic, led_v, ...) y agrega nmos (MOSFET de canal N,
pines como el AO3400A de SamacSys.SchLib: 1 G, 2 S, 3 D). K1 es el PhotoMOS AQY414EHAX (1 Form B = NC):
pines 1 y 2 = LED (ánodo, cátodo) y 3 y 4 = salida, según el datasheet de Panasonic (GU-E AQY41□EH).
Uso: python docs/tools/esquemas_f6.py   (desde la carpeta docs/esquemas)
"""
from pathlib import Path

exec(Path(__file__).with_name("esquemas_f4.py").read_text(encoding="utf-8").split("# ---------- F4_s1")[0])


def nmos(x, y, ref, mpn):
    """Gate en (x, y). Devuelve (gate, drain, source)."""
    cx = x + 34
    e(f'<circle cx="{cx}" cy="{y}" r="18" {W}/>')
    wire((x, y), (cx - 10, y))
    e(f'<line x1="{cx-10}" y1="{y-11}" x2="{cx-10}" y2="{y+11}" {WD}/>')
    for a, b in ((-13, -6), (-3, 3), (6, 13)):  # canal de enriquecimiento en 3 tramos
        e(f'<line x1="{cx-5}" y1="{y+a}" x2="{cx-5}" y2="{y+b}" {WD}/>')
    wire((cx - 5, y - 10), (cx + 6, y - 10), (cx + 6, y - 32))   # drain
    wire((cx - 5, y + 10), (cx + 6, y + 10), (cx + 6, y + 32))   # source
    wire((cx - 5, y), (cx + 6, y), (cx + 6, y + 10))             # sustrato al source
    e(f'<path d="M{cx-4} {y} L{cx+2} {y-4} L{cx+2} {y+4} Z" style="fill:var(--text-primary)"/>')
    t(x - 4, y - 10, "1 G", "ts", "end")
    t(cx + 11, y - 26, "3 D")
    t(cx + 11, y + 26, "2 S")
    t(cx + 24, y - 6, ref, "th")
    t(cx + 24, y + 10, mpn, "ts")
    return (x, y), (cx + 6, y - 32), (cx + 6, y + 32)


# ---------- F6_s1: entrada RELAY_EN y driver Q3 ----------
port(14, 150, "RELAY_EN", "right", 100)
wire((114, 150), (140, 150))
res_h(140, 150, "R39", "1 kΩ", "RC0805FR-071KL")
wire((200, 150), (330, 150)); dot(270, 150)
wire((270, 150), (270, 190)); res_v(270, 190, "R40", "10 kΩ", "RC0805FR-0710KL", "left"); gnd(270, 250)
g, d, s = nmos(330, 150, "Q3", "AO3400A")
wire(d, (d[0], 60)); net(d[0] + 6, 51, "RELAY_DRV")
gnd(*s)
t(20, 302, "R40 (gate a GND) apaga Q3 mientras la ESP32 arranca: el LED de K1 no recibe corriente y su salida queda", "ts")
t(20, 318, "cerrada (NC) → el EVSE puede cargar. RELAY_EN = 1 → VGS = 3,3 V · 10/11 = 3,0 V (AO3400A: ≤ 48 mΩ con 2,5 V).", "ts")
svg("F6_s1_driver", 332, "Puerto RELAY_EN de entrada, R39 de 1 kiloohm en serie hasta el gate de Q3 AO3400A, R40 de 10 kiloohm del gate a GND, source de Q3 a GND y drain a la red RELAY_DRV.")

# ---------- F6_s2: LED6 en serie con el LED de K1 (PhotoMOS NC) ----------
pwr(100, 60, "+VIN")
res_v(100, 60, "R41", "1 kΩ", "RC0805FR-071KL")
led_v(100, 120, "LED6", "amarillo", "KT-0805Y")
wire((100, 180), (100, 192), (290, 192))
zone(425, 120, 245, 170)
pos = ic(330, 170, 190, "K1", "AQY414EHAX · NC (1 Form B)",
         [("1", "LED +", ""), ("2", "LED −", "N:RELAY_DRV")],
         [("4", "salida", "N:EVSE_EN_A"), ("3", "salida", "N:EVSE_EN_B")], paso=40, stub=40)
e(f'<line x1="425" y1="172" x2="425" y2="278" stroke="#E24B4A" stroke-width="1.4" stroke-dasharray="5 4"/>')
t(548, 136, "zona EVSE_EXT (externa)", "ts", "middle")
t(20, 318, "Corriente del LED: (11,6 − 2,0 − 1,25) V / 1 kΩ ≈ 8,4 mA. Datasheet: 5–10 mA recomendado; la salida se abre con", "ts")
t(20, 334, "≤ 3 mA a 25 °C (≈ 3,4 mA a 85 °C) → margen de 2,5×. LED6 encendido = salida abierta = carga parada.", "ts")
t(20, 350, "La línea roja es la barrera: los pines 3 y 4 (y todo lo que va a J2) quedan a ≥ 6,4 mm del lado SELV.", "ts")
svg("F6_s2_k1", 364, "+VIN pasa por R41 de 1 kiloohm y por LED6 KT-0805Y (ánodo arriba) hasta K1 pin 1, el ánodo del LED del PhotoMOS AQY414EHAX. K1 pin 2 va a la red RELAY_DRV. K1 pin 4 va a EVSE_EN_A y pin 3 a EVSE_EN_B, dentro de la zona EVSE_EXT.")

# ---------- F6_s3: J2 a los bornes de habilitación del EVSE ----------
zone(150, 40, 360, 150)
wire((220, 90), (330, 90)); net(226, 81, "EVSE_EN_A")
wire((220, 130), (330, 130)); net(226, 121, "EVSE_EN_B")
ic(370, 68, 70, "J2", "TB001-500-02BE · Sigma ED1621", [("1", "", ""), ("2", "", "")], [], paso=40, stub=40)
t(470, 90, "→ borne de habilitación A del EVSE", "ts")
t(470, 130, "→ borne de habilitación B", "ts")
t(160, 56, "zona EVSE_EXT")
t(20, 222, "Blanket sobre los cables de EVSE_EN_A y EVSE_EN_B con un Parameter Set de clase de red EVSE_EXT (como HV_AC).", "ts")
t(20, 238, "Reglas en F8: ≥ 6,4 mm de fuga y ≥ 5,5 mm en el aire hacia todo el SELV (incluido GND) y hacia HV_AC.", "ts")
t(20, 254, "Serigrafía de J2: «EVSE EN». Sin polaridad (salida AC/DC). Para un EVSE que pida NA se monta AQY214EHAX en K1.", "ts")
svg("F6_s3_j2", 268, "J2 de 2 polos (TB001-500-02BE, ED1621 de Sigma): pin 1 a la red EVSE_EN_A y pin 2 a EVSE_EN_B, dentro de la zona EVSE_EXT con su Blanket.")


def revisar(nombres, carpeta_png):
    """Render de los SVG a PNG con PyMuPDF (cambia variables y clases por colores fijos)."""
    import re
    import pymupdf
    reemplazos = [
        ("var(--text-primary)", "#222"),
        ('<g class="c-blue"><text class="th"', '<g><text class="th" fill="#185FA5"'),
        ('class="c-amber"><polygon', 'fill="#FAEEDA" stroke="#854F0B"><polygon'),
        ('<rect class="c-coral"', '<rect fill="#FAECE7"'),
        ('<g class="box">', '<g fill="#F1EFE8" stroke="#5F5E5A">'),
    ]
    for n in nombres:
        s = Path(f"{n}.svg").read_text(encoding="utf-8")
        for a, b in reemplazos:
            s = s.replace(a, b)
        s = re.sub(r'class="th"', 'font-size="14" font-weight="bold" font-family="Arial"', s)
        s = re.sub(r'class="ts"', 'font-size="12" fill="#444" font-family="Arial"', s)
        s = s.replace('<svg width="100%"', '<svg xmlns="http://www.w3.org/2000/svg" width="680" style="background:#fff"')
        doc = pymupdf.open(stream=s.encode("utf-8"), filetype="svg")
        doc[0].get_pixmap(dpi=110).save(str(Path(carpeta_png) / f"{n}.png"))


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        revisar(["F6_s1_driver", "F6_s2_k1", "F6_s3_j2"], sys.argv[1])
