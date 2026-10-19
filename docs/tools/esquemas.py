# -*- coding: utf-8 -*-
"""Genera los esquemas literales por bloque (SVG) que se muestran en el chat y se guardan en docs/esquemas/.

Uso: python docs/tools/esquemas.py  (escribe los .svg en la carpeta actual).
Para otra fase: copiar las funciones de dibujo (wire, res_h, res_v, cap_v, cap_h, gnd, pwr, port, net, zone)
y reemplazar las secciones «S1…S6» por los bloques de la hoja nueva. Revisar siempre el render antes de mostrarlo.
"""
import sys
sys.stdout.reconfigure(encoding="utf-8")
W = 'style="stroke:var(--text-primary);stroke-width:1.3;fill:none"'
WD = 'style="stroke:var(--text-primary);stroke-width:2.2;fill:none"'
out = []


def e(s):
    out.append(s)


def wire(*pts):
    d = " ".join(f"{'M' if i == 0 else 'L'}{x} {y}" for i, (x, y) in enumerate(pts))
    e(f'<path d="{d}" {W}/>')


def dot(x, y):
    e(f'<circle cx="{x}" cy="{y}" r="3" style="fill:var(--text-primary)"/>')


def t(x, y, s, cls="ts", anchor="start"):
    e(f'<text class="{cls}" x="{x}" y="{y}" text-anchor="{anchor}" dominant-baseline="central">{s}</text>')


def net(x, y, s, anchor="start"):
    e(f'<g class="c-blue"><text class="th" x="{x}" y="{y}" text-anchor="{anchor}" dominant-baseline="central">{s}</text></g>')


def labels(x, y, ref, val, mpn, anchor="start"):
    t(x, y, ref, "th", anchor)
    t(x, y + 15, val, "ts", anchor)
    t(x, y + 29, mpn, "ts", anchor)


def res_h(x, y, ref, val, mpn):  # de x a x+60
    wire((x, y), (x + 10, y))
    e(f'<rect x="{x+10}" y="{y-6}" width="40" height="12" rx="1" {W}/>')
    wire((x + 50, y), (x + 60, y))
    t(x + 30, y - 16, ref, "th", "middle")
    t(x + 30, y + 18, val, "ts", "middle")
    t(x + 30, y + 32, mpn, "ts", "middle")


def res_v(x, y, ref, val, mpn, side="right", ly=None):  # de y a y+60
    wire((x, y), (x, y + 10))
    e(f'<rect x="{x-6}" y="{y+10}" width="12" height="40" rx="1" {W}/>')
    wire((x, y + 50), (x, y + 60))
    ly = y + 15 if ly is None else ly
    if side == "right":
        labels(x + 12, ly, ref, val, mpn)
    else:
        labels(x - 12, ly, ref, val, mpn, "end")


def cap_v(x, y, ref, val, mpn, side="right"):  # de y a y+60
    wire((x, y), (x, y + 27))
    e(f'<line x1="{x-11}" y1="{y+27}" x2="{x+11}" y2="{y+27}" {WD}/>')
    e(f'<line x1="{x-11}" y1="{y+33}" x2="{x+11}" y2="{y+33}" {WD}/>')
    wire((x, y + 33), (x, y + 60))
    if side == "right":
        labels(x + 16, y + 15, ref, val, mpn)
    else:
        labels(x - 16, y + 15, ref, val, mpn, "end")


def cap_h(x, y, ref, val, mpn):  # de x a x+60
    wire((x, y), (x + 27, y))
    e(f'<line x1="{x+27}" y1="{y-11}" x2="{x+27}" y2="{y+11}" {WD}/>')
    e(f'<line x1="{x+33}" y1="{y-11}" x2="{x+33}" y2="{y+11}" {WD}/>')
    wire((x + 33, y), (x + 60, y))
    t(x + 30, y - 20, ref, "th", "middle")
    t(x + 30, y + 22, val, "ts", "middle")
    t(x + 30, y + 36, mpn, "ts", "middle")


def gnd(x, y):
    wire((x, y), (x, y + 6))
    e(f'<path d="M{x-9} {y+6} L{x+9} {y+6} M{x-5} {y+10} L{x+5} {y+10} M{x-2} {y+14} L{x+2} {y+14}" {W}/>')


def pwr(x, y, s):  # puerto de alimentación hacia arriba
    wire((x, y), (x, y - 10))
    e(f'<line x1="{x-8}" y1="{y-10}" x2="{x+8}" y2="{y-10}" {WD}/>')
    net(x, y - 20, s, "middle")


def port(x, y, s, d="right", w=86):
    if d == "right":
        pts = f"{x},{y-9} {x+w-9},{y-9} {x+w},{y} {x+w-9},{y+9} {x},{y+9}"
    else:
        pts = f"{x},{y} {x+9},{y-9} {x+w},{y-9} {x+w},{y+9} {x+9},{y+9}"
    e(f'<g class="c-amber"><polygon points="{pts}" stroke-width="0.8"/><text class="ts" x="{x+w/2}" y="{y}" text-anchor="middle" dominant-baseline="central">{s}</text></g>')


def zone(x, y, w, h):
    e(f'<rect class="c-coral" x="{x}" y="{y}" width="{w}" height="{h}" rx="10" style="stroke:none"/>')


def pwr_h(x, y, s, side="left"):  # puerto de alimentación al final de un pin horizontal (barra vertical)
    d = -1 if side == "left" else 1
    wire((x, y), (x + d * 8, y))
    e(f'<line x1="{x+d*8}" y1="{y-8}" x2="{x+d*8}" y2="{y+8}" {WD}/>')
    net(x + d * 14, y, s, "end" if side == "left" else "start")


def noerc(x, y):  # cruz de No ERC en el extremo de un pin libre
    e(f'<path d="M{x-5} {y-5} L{x+5} {y+5} M{x+5} {y-5} L{x-5} {y+5}" stroke="#E24B4A" stroke-width="1.6" fill="none"/>')


def svg(name, h, desc):
    import re
    Ws = ' style="stroke:var(--text-primary);stroke-width:1.3;fill:none"'
    WDs = ' style="stroke:var(--text-primary);stroke-width:2.2;fill:none"'
    Ds = ' style="fill:var(--text-primary)"'
    zones=[x for x in out if 'c-coral' in x or 'class="box"' in x]
    w=[x.replace(Ws,'') for x in out if Ws in x]
    wd=[x.replace(WDs,'') for x in out if WDs in x]
    d=[x.replace(Ds,'') for x in out if Ds in x]
    rest=[x for x in out if x and x not in zones and Ws not in x and WDs not in x and Ds not in x]
    paths=' '.join(re.match(r'<path d="([^"]*)"/>',x).group(1) for x in w if x.startswith('<path'))
    others=''.join(x for x in w if not x.startswith('<path'))
    body = "".join(zones) + f'<g{Ws}><path d="{paths}"/>{others}</g><g{WDs}>{"".join(wd)}</g><g{Ds}>{"".join(d)}</g>' + "".join(rest)
    body = body.replace(' text-anchor="start"','').replace('.0"','"').replace(' dominant-baseline="central"',' dy=".35em"')

    out.clear()
    s = (f'<svg width="100%" viewBox="0 0 680 {h}" role="img"><title>{name}</title><desc>{desc}</desc>\n{body}\n</svg>')
    open(f"{name}.svg", "w", encoding="utf-8").write(s)
    print(name, len(s))


# ---------- S1: divisor ----------
zone(6, 22, 668, 228)
port(14, 80, "AC_L1_F")
wire((100, 80), (100, 80))
xs = [100, 200, 300, 400]
mpn = "ERJ-P08F1004V"
for i, x in enumerate(xs):
    res_h(x, 80, f"R{i+2}", "1 MΩ 1206", mpn)
for i, x in enumerate([160, 260, 360]):
    wire((x, 80), (x + 40, 80))
    net(x + 20, 66, f"HV_D{i+1}", "middle")
wire((460, 80), (620, 80))
net(620, 66, "HV_INP", "end")
dot(480, 80)
wire((480, 80), (480, 120))
wire((450, 120), (530, 120))
dot(480, 120)
res_v(450, 120, "R6", "10 kΩ 0,1 %", "ERA-6AEB103V", "left")
cap_v(530, 120, "C9", "1 nF C0G", "C0805C102J5GAC-TU")
wire((450, 180), (450, 215))
wire((530, 180), (530, 215))
port(14, 215, "AC_L2_F")
wire((100, 215), (620, 215))
dot(450, 215)
dot(530, 215)
net(620, 232, "AC_L2_F", "end")
svg("s1_divisor", 260, "Divisor: AC_L1_F, R2 a R5 en serie con nodos HV_D1 a HV_D3 hasta HV_INP; R6 y C9 en paralelo de HV_INP a AC_L2_F.")

# ---------- S2: U2 ----------
zone(6, 22, 336, 300)
zone(6, 330, 668, 230)
bx, by, bw = 235, 40, 210
pins_l = [("1", "DCDC_OUT", "HV_DCDC"), ("2", "DCDC_HGND", "AC_L2_F"), ("3", "HLDO_IN", "HV_DCDC"), ("4", "NC", "AC_L2_F"),
          ("5", "HLDO_OUT", "HV_LDO"), ("6", "INP", "HV_INP"), ("7", "INN", "AC_L2_F"), ("8", "HGND", "AC_L2_F")]
pins_r = [("16", "DCDC_IN", "AMC_LDO"), ("15", "DCDC_GND", "GND"), ("14", "DIAG", "AMC_DIAG"), ("13", "LDO_OUT", "AMC_LDO"),
          ("12", "VDD", "PWR:+3V3"), ("11", "OUTP", "AMC_OUTP"), ("10", "OUTN", "AMC_OUTN"), ("9", "GND", "GND")]
e(f'<g class="box"><rect x="{bx}" y="{by}" width="{bw}" height="260" rx="4" stroke-width="0.8"/></g>')
t(bx + bw / 2, by + 12, "U2", "th", "middle")
t(bx + bw / 2, by + 248, "AMC3330DWE", "ts", "middle")
for i, (n, nm, nt) in enumerate(pins_l):
    y = by + 34 + i * 28
    wire((bx - 22, y), (bx, y))
    t(bx + 6, y, f"{n} {nm}")
    net(bx - 26, y - 1, nt, "end")
for i, (n, nm, nt) in enumerate(pins_r):
    y = by + 34 + i * 28
    wire((bx + bw, y), (bx + bw + 22, y))
    t(bx + bw - 6, y, f"{nm} {n}", "ts", "end")
    if nt == "GND":
        gnd(bx + bw + 22, y)
        e("")
    elif nt.startswith("PWR:"):
        pwr_h(bx + bw + 22, y, nt[4:], "right")
    else:
        net(bx + bw + 26, y - 1, nt)
# filas de condensadores lado red
def row(y0, netname, caps, rail):
    xs=[20+220*i for i in range(len(caps))]
    wire((14, y0), (xs[-1]+20, y0)); net(16, y0-12, netname)
    for x,(r,v,m) in zip(xs,caps):
        cap_v(x+10, y0, r, v, m); dot(x+10, y0)
        if rail: dot(x+10, y0+60)
        else: gnd(x+10, y0+60)
    if rail:
        wire((14, y0+60), (xs[-1]+20, y0+60)); net(xs[-1]+40, y0+60, rail)
row(362, "HV_DCDC", [("C10","1 µF X7R","CL21B105KAFNNNE"),("C11","1 nF C0G","C0805C102J5GAC-TU"),("C12","100 nF X7R","CL21B104KBCNNNC")], "AC_L2_F")
row(472, "HV_LDO", [("C16","100 nF C0G","C3216NP01H104J160AA"),("C17","1 nF C0G","C0805C102J5GAC-TU")], "AC_L2_F")
y1 = 600
wire((14, y1), (60, y1)); net(16, y1-12, "AMC_LDO")
cap_v(30, y1, "C13", "100 nF X7R", "CL21B104KBCNNNC"); gnd(30, y1+60)
pwr(170, y1, "+3V3")
wire((170, y1), (590, y1))
cap_v(170, y1, "C14", "1 µF X7R", "CL21B105KAFNNNE"); gnd(170, y1+60)
cap_v(300, y1, "C15", "1 nF C0G", "C0805C102J5GAC-TU"); gnd(300, y1+60); dot(300, y1)
res_v(590, y1, "R7", "47 kΩ", "RC0805FR-0747KL", "left")
wire((590, y1+60), (590, y1+90), (640, y1+90))
net(598, y1+78, "AMC_DIAG")
e(f'<circle cx="648" cy="{y1+90}" r="8" {W}/>')
t(640, y1+110, "TP5 · 5016", "ts", "end")
svg("s2_u2", 730, "AMC3330 U2 con net labels en cada pin; abajo, condensadores del lado red entre HV_DCDC/HV_LDO y AC_L2_F, y del lado SELV entre AMC_LDO o +3V3 y GND; R7 pull-up de DIAG con TP5.")

# ---------- S3: acople ----------
for k, (yy, sfx, c, r1, r2, cf) in enumerate([(70, "P", "C18", "R9", "R10", "C19"), (210, "N", "C21", "R12", "R14", "C22")]):
    wire((20, yy), (110, yy))
    net(22, yy - 12, f"AMC_OUT{sfx}")
    cap_h(110, yy, c, "10 µF X5R", "CL21A106KAYNNNE")
    wire((170, yy), (230, yy))
    net(200, yy - 12, f"AMC_C{sfx}", "middle")
    res_h(230, yy, r1, "20 kΩ 0,1 %", "ERA-6AEB203V")
    wire((290, yy), (640, yy))
    dot(360, yy); dot(480, yy)
    net(640, yy - 12, f"ATM_V{sfx}", "end")
    res_v(360, yy, r2, "13 kΩ 0,1 %", "ERA-6AEB133V")
    gnd(360, yy + 60)
    cap_v(480, yy, cf, "4,7 nF C0G", "C0805C472J5GACTU")
    gnd(480, yy + 60)
svg("s3_acople", 300, "Acople AC: AMC_OUTP pasa por C18 a AMC_CP, R9 a ATM_VP, con R10 y C19 de ATM_VP a GND; igual en N con C21, R12, R14 y C22.")

# ---------- S4: CT ----------
e('<g class="box"><rect x="14" y="50" width="76" height="160" rx="4" stroke-width="0.8"/></g>')
t(52, 38, "J3", "th", "middle")
for y, s in [(70, "2 tip"), (100, "10 tip sw."), (130, "3 ring"), (160, "11 ring sw."), (190, "1 sleeve")]:
    t(84, y, s, "ts", "end")
wire((90, 70), (110, 70))
wire((90, 190), (110, 190))
for y in (100, 130, 160):
    wire((90, y), (100, y))
    noerc(100, y)
t(52, 228, "SJ1-3515-SMT-TR", "ts", "middle")
t(52, 242, "CT: SCT-013-000V", "ts", "middle")
wire((110, 70), (420, 70)); wire((110, 190), (420, 190))
net(200, 58, "CT_P", "middle"); net(200, 178, "CT_N", "middle")
dot(180, 70); dot(180, 190); dot(270, 70); dot(270, 190)
wire((180, 70), (180, 105))
e(f'<path d="M170 105 L190 105 L180 120 Z M170 135 L190 135 L180 120 Z" {W}/>')
e(f'<path d="M170 120 L190 120" {WD}/>')
wire((180, 135), (180, 190))
t(168, 112, "D4", "th", "end"); t(168, 127, "TVS bidir.", "ts", "end"); t(168, 141, "SMAJ5.0CA", "ts", "end")
res_v(270, 70, "R11", "10 Ω 0,5 %", "ERA-6AHD100V", ly=82)
res_v(270, 130, "R13", "10 Ω 0,5 %", "ERA-6AHD100V", ly=147)
dot(270, 130)
wire((270, 130), (240, 130)); gnd(240, 130)
res_h(420, 70, "R8", "1 kΩ", "RC0805FR-071KL")
res_h(420, 190, "R15", "1 kΩ", "RC0805FR-071KL")
wire((480, 70), (650, 70)); wire((480, 190), (650, 190))
dot(540, 70); dot(540, 190)
net(650, 58, "ATM_IP", "end"); net(650, 178, "ATM_IN", "end")
cap_v(540, 70, "C20", "33 nF C0G", "C1206C333J5GACTU")
gnd(540, 130)
cap_v(540, 190, "C23", "33 nF C0G", "C1206C333J5GACTU")
gnd(540, 250)
svg("s4_ct", 280, "Entrada del CT: J3 tip a CT_P y sleeve a CT_N, ring sin conexión; D4 entre CT_P y CT_N; R11 y R13 en serie con el punto medio a GND; R8 y R15 en serie hacia ATM_IP y ATM_IN con C20 y C23 a GND.")

# ---------- S5: U3 ----------
bx, by, bw = 255, 30, 170
pl = [("1", "MMD1", "PWR:+3V3"), ("2", "DGND", "GND"), ("3", "DVDD", "PWR:+3V3"), ("4", "Reset", "ATM_RST"), ("5", "AVDD", "PWR:+3V3A"),
      ("6", "AGND", "GND"), ("7", "I2P", "ATM_IP"), ("8", "I2N", "ATM_IN"), ("9", "Resv_low", "GND"), ("10", "I1P", "GND"),
      ("11", "I1N", "GND"), ("12", "USEL", "GND"), ("13", "Vref", "ATM_VREF"), ("14", "AGND", "GND")]
pr = [("28", "MMD0", "PWR:+3V3"), ("27", "SDI", "P:MEAS_MOSI"), ("26", "SDO", "P:MEAS_MISO"), ("25", "SCLK", "P:MEAS_SCK"),
      ("24", "CS", "P:MEAS_CS"), ("23", "OSCO", "XTAL_O"), ("22", "OSCI", "XTAL_I"), ("21", "ZX", "P:MEAS_ZX"),
      ("20", "IRQ", "P:MEAS_IRQ"), ("19", "CF2", "ATM_CF2"), ("18", "CF1", "ATM_CF1"), ("17", "WarnOut", "P:MEAS_WARN"),
      ("16", "VP", "ATM_VP"), ("15", "VN", "ATM_VN")]
e(f'<g class="box"><rect x="{bx}" y="{by}" width="{bw}" height="{50+14*28}" rx="4" stroke-width="0.8"/></g>')
t(bx + bw / 2, by + 12, "U3", "th", "middle")
t(bx + bw / 2, by + 50 + 14 * 28 - 12, "ATM90E26-YU-R", "ts", "middle")
for i, (n, nm, nt) in enumerate(pl):
    y = by + 34 + i * 28
    wire((bx - 22, y), (bx, y))
    t(bx + 6, y, f"{n} {nm}")
    if nt == "GND":
        gnd(bx - 22, y)
    elif nt.startswith("PWR:"):
        pwr_h(bx - 22, y, nt[4:], "left")
    else:
        net(bx - 26, y - 1, nt, "end")
for i, (n, nm, nt) in enumerate(pr):
    y = by + 34 + i * 28
    wire((bx + bw, y), (bx + bw + 22, y))
    t(bx + bw - 6, y, f"{nm} {n}", "ts", "end")
    if nt.startswith("P:"):
        port(bx + bw + 22, y, nt[2:], "right", 100)
    elif nt.startswith("PWR:"):
        pwr_h(bx + bw + 22, y, nt[4:], "right")
    else:
        net(bx + bw + 26, y - 1, nt)
svg("s5_u3", 490, "ATM90E26 U3 con net labels y puertos MEAS en cada pin.")

# ---------- S6: soporte U3 ----------
def caps_cell(cx, cy, title, pw, caps, is_pwr=True):
    t(cx, cy-42, title, "ts")
    if is_pwr: pwr(cx+20, cy, pw)
    else: net(cx+20, cy-12, pw)
    xs=[cx+20+150*i for i in range(len(caps))]
    wire((cx+20, cy), (xs[-1], cy))
    for x,(r,v,m) in zip(xs,caps):
        cap_v(x, cy, r, v, m); gnd(x, cy+60); dot(x, cy)

caps_cell(10, 70, "DVDD (pin 3)", "+3V3", [("C24","10 µF X5R","CL21A106KAYNNNE"),("C25","100 nF X7R","CL21B104KBCNNNC")])
caps_cell(370, 70, "AVDD (pin 5)", "+3V3A", [("C28","100 nF X7R","CL21B104KBCNNNC")])
caps_cell(10, 230, "Vref (pin 13)", "ATM_VREF", [("C30","1 µF X7R","CL21B105KAFNNNE"),("C31","1 nF C0G","C0805C102J5GAC-TU")], False)
t(370, 188, "Reset (pin 4)", "ts")
pwr(390, 230, "+3V3")
res_v(390, 230, "R16", "10 kΩ", "RC0805FR-0710KL")
wire((390, 290), (390, 300), (500, 300)); dot(500, 300)
net(510, 288, "ATM_RST")
cap_v(500, 300, "C29", "100 nF X7R", "CL21B104KBCNNNC"); gnd(500, 360)
# cristal
cy=430
t(10, cy-40, "Cristal (pines 22 y 23)", "ts")
net(16, cy-12, "XTAL_I"); net(600, cy-12, "XTAL_O", "end")
wire((14, cy), (244, cy))
e(f'<rect x="255" y="{cy-10}" width="30" height="20" rx="2" {W}/>')
e(f'<path d="M248 {cy-9} L248 {cy+9} M292 {cy-9} L292 {cy+9}" {WD}/>')
wire((244, cy), (248, cy)); wire((292, cy), (600, cy))
t(270, cy-22, "Y1", "th", "middle")
t(270, cy+24, "8,192 MHz", "ts", "middle")
t(270, cy+38, "ECS-81.92-12-30Q-EN-TR", "ts", "middle")
dot(150, cy); dot(430, cy)
cap_v(150, cy, "C26", "12 pF C0G", "C0805C120J5GACTU", "left"); gnd(150, cy+60)
cap_v(430, cy, "C27", "12 pF C0G", "C0805C120J5GACTU"); gnd(430, cy+60)
# CF1, CF2, CS
cy=580
t(10, cy-40, "CF1 y CF2 (pines 18 y 19)", "ts")
net(16, cy-12, "ATM_CF1")
wire((14, cy), (80, cy))
res_h(80, cy, "R17", "1 kΩ", "RC0805FR-071KL")
wire((140, cy), (190, cy), (190, cy+20))
e(f'<path d="M180 {cy+20} L200 {cy+20} L190 {cy+36} Z" {W}/>')
e(f'<path d="M180 {cy+36} L200 {cy+36}" {WD}/>')
wire((190, cy+36), (190, cy+50)); gnd(190, cy+50)
t(206, cy+22, "LED2", "th"); t(206, cy+37, "verde · APT2012SGC", "ts")
net(16, cy+85, "ATM_CF2")
wire((14, cy+97), (90, cy+97))
e(f'<circle cx="98" cy="{cy+97}" r="8" {W}/>')
t(112, cy+97, "TP6 · 5016", "ts")
t(370, cy-40, "Pull-up de CS (pin 24)", "ts")
pwr(390, cy, "+3V3")
res_v(390, cy, "R18", "10 kΩ", "RC0805FR-0710KL")
wire((390, cy+60), (390, cy+75), (450, cy+75))
port(450, cy+75, "MEAS_CS", "right", 90)
svg("s6_soporte", 710, "Circuitos de soporte de U3: desacople de DVDD, AVDD y Vref, reset con R16 y C29, cristal Y1 con C26 y C27, LED2 con R17 en CF1, TP6 en CF2 y pull-up R18 de MEAS_CS.")

# ---------- C1: corrección de J3 (misma orientación que en la hoja: tip arriba, sleeve abajo) ----------
zone(6, 10, 668, 46)
wire((20, 36), (400, 36))
net(24, 24, "AC_L2_F")
t(410, 36, "riel de C16/C17 (red)", "ts")
e('<g class="box"><rect x="40" y="110" width="180" height="170" rx="4" stroke-width="0.8"/></g>')
t(130, 185, "J3", "th", "middle")
t(130, 203, "SJ1-3515-SMT-TR", "ts", "middle")
for x, s in [(130, "2 tip"), (190, "10 t.sw")]:
    wire((x, 110), (x, 86))
    t(x, 124, s, "ts", "middle")
for x, s in [(70, "3 ring"), (130, "11 r.sw"), (190, "1 sleeve")]:
    wire((x, 280), (x, 304))
    t(x, 266, s, "ts", "middle")
noerc(190, 86); noerc(70, 304); noerc(130, 304)
wire((130, 86), (130, 70), (300, 70), (300, 150), (590, 150))
wire((190, 304), (190, 330), (590, 330))
net(330, 138, "CT_P"); net(330, 318, "CT_N")
dot(380, 150); dot(380, 330); dot(520, 150); dot(520, 330)
wire((380, 150), (380, 215))
e(f'<path d="M370 215 L390 215 L380 230 Z M370 245 L390 245 L380 230 Z" {W}/>')
e(f'<path d="M370 230 L390 230" {WD}/>')
wire((380, 245), (380, 330))
t(394, 222, "D4", "th"); t(394, 237, "TVS bidir.", "ts"); t(394, 251, "SMAJ5.0CA", "ts")
res_v(520, 150, "R11", "10 Ω 0,5 %", "ERA-6AHD100V")
wire((520, 210), (520, 270))
dot(520, 240)
wire((520, 240), (560, 240)); gnd(560, 240)
res_v(520, 270, "R13", "10 Ω 0,5 %", "ERA-6AHD100V")
t(596, 150, "a R8", "ts"); t(596, 330, "a R15", "ts")
svg("c1_j3", 350, "Corrección de J3 con su orientación en la hoja: tip (pin 2) sale hacia arriba, gira a la derecha y baja al riel CT_P; sleeve (pin 1) baja al riel CT_N; ring (3), tip switch (10) y ring switch (11) con No ERC; D4 entre CT_P y CT_N; R11 y R13 con punto medio a GND. Arriba, el riel AC_L2_F de la zona de red, que el cable de tip no debe tocar.")

# ---------- C4: net label +3V3 (hoy) frente a puerto de alimentación (debe ser) ----------
e('<g class="c-red"><text class="th" x="20" y="22" dy=".35em">Hoy: net label (solo existe en esta hoja)</text></g>')
e('<g class="c-teal"><text class="th" x="360" y="22" dy=".35em">Debe ser: puerto de alimentación</text></g>')
for x0, buena in ((20, False), (360, True)):
    bx = x0 + 200
    e(f'<g class="box"><rect x="{bx}" y="50" width="96" height="100" rx="4" stroke-width="0.8"/></g>')
    t(bx + 48, 140, "U3", "th", "middle")
    for y, s in ((70, "1 MMD1"), (110, "3 DVDD")):
        wire((bx - 60, y), (bx, y))
        t(bx + 6, y, s)
        if buena:
            pwr_h(bx - 60, y, "+3V3", "left")
        else:
            net(bx - 56, y - 12, "+3V3")
    cx = x0 + 60
    if buena:
        pwr(cx, 200, "+3V3")
    else:
        wire((cx, 200), (cx, 180))
        net(cx + 4, 168, "+3V3")
    res_v(cx, 200, "R16", "10 kΩ", "RC0805FR-0710KL")
svg("c4_puerto_alim", 280, "A la izquierda, como está hoy: el nombre +3V3 es una net label azul sobre el cable de los pines 1 y 3 de U3 y sobre R16. A la derecha, como debe quedar: en el mismo extremo de cable, un puerto de alimentación con barra llamado +3V3.")

# ---------- C5: dónde van HV_D1, HV_D2 y HV_D3 (resistencias pegadas pin con pin) ----------
zone(6, 22, 668, 150)
port(14, 110, "AC_L1_F")
for i, x in enumerate([100, 230, 360, 490]):
    res_h(x, 110, f"R{i+2}", "1 MΩ 1206", "ERJ-P08F1004V")
for i, x in enumerate([160, 290, 420]):
    wire((x, 110), (x + 70, 110))
for i, x in enumerate([195, 325, 455]):
    e(f'<circle cx="{x}" cy="110" r="5" stroke="#E24B4A" stroke-width="1.6" fill="none"/>')
    net(x, 66, f"HV_D{i+1}", "middle")
    e(f'<path d="M{x} 76 L{x} 102" stroke="#E24B4A" stroke-width="1" stroke-dasharray="3 2" fill="none"/>')
wire((550, 110), (660, 110))
net(660, 96, "HV_INP", "end")
svg("c5_divisor_etiquetas", 190, "Divisor R2 a R5 en serie desde AC_L1_F hasta HV_INP. Los círculos rojos marcan los tres puntos donde se tocan dos resistencias; ahí se pone la net label HV_D1, HV_D2 y HV_D3, de izquierda a derecha.")
