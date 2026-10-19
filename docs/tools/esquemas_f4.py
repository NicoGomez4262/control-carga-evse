# -*- coding: utf-8 -*-
"""Esquemas literales por bloque de la hoja 04_MCU (F4). Escribe docs/esquemas/F4_*.svg.

Reusa las funciones de dibujo de esquemas.py (wire, res_h, res_v, cap_v, gnd, pwr, pwr_h, port, net, noerc, svg)
y agrega: ic (símbolo rectangular con pines a los dos lados), npn, led_v, sw_v y header.
Los números y nombres de pin son los de los símbolos de SamacSys.SchLib.
Uso: python docs/tools/esquemas_f4.py   (desde la carpeta docs/esquemas)
"""
from pathlib import Path

_src = (Path(__file__).with_name("esquemas.py")).read_text(encoding="utf-8")
exec(_src.split("# ---------- S1")[0])  # solo las funciones de dibujo


def ic(x, y, w, ref, mpn, izq, der, paso=22, stub=22):
    """izq/der: [(num, nombre, conexión)]. Conexión: GND, PWR:+3V3, P:PUERTO, N:RED, NC o ''."""
    filas = max(len(izq), len(der))
    h = 30 + filas * paso
    e(f'<g class="box"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="4" stroke-width="0.8"/></g>')
    t(x + w / 2, y - 10, ref, "th", "middle")
    t(x + w / 2, y + h + 14, mpn, "ts", "middle")
    pos = {}
    for lado, pines in (("izq", izq), ("der", der)):
        for i, (n, nm, cx) in enumerate(pines):
            py = y + 22 + i * paso
            if lado == "izq":
                px = x - stub
                wire((px, py), (x, py))
                t(x + 5, py, f"{n} {nm}")
            else:
                px = x + w + stub
                wire((x + w, py), (px, py))
                t(x + w - 5, py, f"{nm} {n}", "ts", "end")
            pos[n] = (px, py)
            conectar(px, py, cx, lado)
    return pos


def conectar(px, py, cx, lado):
    izq = lado == "izq"
    if not cx:
        return
    if cx == "GND":
        gnd(px, py)
    elif cx == "NC":
        noerc(px, py)
    elif cx.startswith("PWR:"):
        pwr_h(px, py, cx[4:], "left" if izq else "right")
    elif cx.startswith("P:"):
        if izq:
            port(px - 100, py, cx[2:], "left", 100)
        else:
            port(px, py, cx[2:], "right", 100)
    elif cx.startswith("N:"):
        net(px - 4 if izq else px + 4, py - 9, cx[2:], "end" if izq else "start")


def npn(x, y, ref, mpn):
    """Base en (x, y). Devuelve (base, colector, emisor)."""
    cx = x + 34
    e(f'<circle cx="{cx}" cy="{y}" r="18" {W}/>')
    wire((x, y), (cx - 8, y))
    e(f'<line x1="{cx-8}" y1="{y-11}" x2="{cx-8}" y2="{y+11}" {WD}/>')
    wire((cx - 8, y - 5), (cx + 6, y - 16), (cx + 6, y - 32))
    wire((cx - 8, y + 5), (cx + 6, y + 16), (cx + 6, y + 32))
    e(f'<path d="M{cx+6} {y+16} L{cx-2} {y+15} L{cx+2} {y+9} Z" style="fill:var(--text-primary)"/>')
    t(cx + 22, y - 6, ref, "th")
    t(cx + 22, y + 10, mpn, "ts")
    return (x, y), (cx + 6, y - 32), (cx + 6, y + 32)


def led_v(x, y, ref, val, mpn):  # ánodo arriba en (x, y), cátodo abajo en (x, y+60)
    wire((x, y), (x, y + 20))
    e(f'<path d="M{x-9} {y+20} L{x+9} {y+20} L{x} {y+36} Z" {W}/>')
    e(f'<line x1="{x-9}" y1="{y+36}" x2="{x+9}" y2="{y+36}" {WD}/>')
    wire((x, y + 36), (x, y + 60))
    labels(x + 14, y + 18, ref, val, mpn)


def sw_v(x, y, ref, val, mpn, nota=""):  # de (x, y) a (x, y+60)
    wire((x, y), (x, y + 18))
    e(f'<circle cx="{x}" cy="{y+20}" r="2.5" {W}/><circle cx="{x}" cy="{y+40}" r="2.5" {W}/>')
    wire((x, y + 42), (x, y + 60))
    e(f'<path d="M{x+3} {y+22} L{x+14} {y+38} M{x+10} {y+28} L{x+18} {y+28}" {W}/>')
    labels(x + 22, y + 18, ref, val, mpn + nota)


# ---------- F4_s1: puente USB-UART ----------
izq = [("1", "GND", "GND"), ("2", "TXD", "N:CH_TXD"), ("3", "RXD", "N:CH_RXD"), ("4", "V3", "PWR:+3V3"),
       ("5", "UD+", "N:USB_DP"), ("6", "UD-", "N:USB_DN"), ("7", "NC", "NC"), ("8", "OUT#", "NC")]
der = [("16", "VCC", "PWR:+3V3"), ("15", "R232", "NC"), ("14", "RTS#", "N:RTS_N"), ("13", "DTR#", "N:DTR_N"),
       ("12", "DCD#", "NC"), ("11", "RI#", "NC"), ("10", "DSR#", "NC"), ("9", "CTS#", "NC")]
ic(265, 40, 150, "U5", "CH340C", izq, der, paso=30, stub=40)
y0 = 340
t(20, y0 - 34, "Serie del UART (cerca de U5)", "ts")
for k, (a1, r, b1) in enumerate([("CH_TXD", "R26", "UART_RX"), ("UART_TX", "R25", "CH_RXD")]):
    yy = y0 + k * 70
    wire((20, yy), (120, yy)); net(24, yy - 9, a1)
    res_h(120, yy, r, "1 kΩ", "RC0805FR-071KL")
    wire((180, yy), (280, yy)); net(276, yy - 9, b1, "end")
t(420, y0 - 34, "Desacople de VCC (pin 16)", "ts")
pwr(470, y0, "+3V3")
cap_v(470, y0, "C35", "100 nF X7R", "CL21B104KBCNNNC"); gnd(470, y0 + 60)
svg("F4_s1_ch340c", 450, "U5 CH340C con net labels: TXD a CH_TXD, RXD a CH_RXD, UD+ y UD- a USB_DP y USB_DN, DTR# y RTS# a DTR_N y RTS_N; V3 y VCC a +3V3; libres con No ERC. Abajo: R26 de CH_TXD a UART_RX, R25 de UART_TX a CH_RXD y C35 de +3V3 a GND.")

# ---------- F4_s2: auto-reset (circuito del profesor) ----------
net(40, 81, "DTR_N")
wire((40, 90), (120, 90))
res_h(120, 90, "R19", "12 kΩ", "RC0805FR-0712KL")
b, c, em = npn(180, 90, "Q2", "MMBT3904LT1G")
wire(c, (c[0], 40), (560, 40)); net(560, 31, "ESP_EN", "end")
wire(em, (em[0], 150)); net(em[0] + 6, 141, "RTS_N")
net(40, 231, "RTS_N")
wire((40, 240), (120, 240))
res_h(120, 240, "R20", "12 kΩ", "RC0805FR-0712KL")
b, c, em = npn(180, 240, "Q1", "MMBT3904LT1G")
wire(c, (c[0], 200), (480, 200)); dot(480, 200)
wire((480, 200), (560, 200)); net(560, 191, "ESP_IO0", "end")
wire(em, (em[0], 300)); net(em[0] + 6, 291, "DTR_N")
res_v(480, 140, "R21", "4,7 kΩ", "RC0805FR-074K7L", "left")
pwr(480, 140, "+3V3")
t(40, 330, "Q2: base por R19 desde DTR_N, emisor a RTS_N, colector a ESP_EN (EN). Q1: base por R20 desde RTS_N,", "ts")
t(40, 346, "emisor a DTR_N, colector a ESP_IO0 (IO0) con R21 a +3V3. Pines del MMBT3904: 1 B, 2 E, 3 C.", "ts")
svg("F4_s2_autoreset", 360, "Auto-reset: DTR_N por R19 a la base de Q2, emisor de Q2 a RTS_N y colector a ESP_EN; RTS_N por R20 a la base de Q1, emisor de Q1 a DTR_N y colector a ESP_IO0 con R21 de 4,7 kΩ a +3V3.")

# ---------- F4_s3: módulo ESP32-S3 ----------
izq = [("1", "GND_1", "GND"), ("2", "3V3", "PWR:+3V3"), ("3", "EN", "N:ESP_EN"), ("4", "IO4", "P:OW_DATA"),
       ("5", "IO5", "P:RELAY_EN"), ("6", "IO6", "N:LED_WIFI"), ("7", "IO7", "N:LED_CARGA"), ("8", "IO15", "N:LED_FALLA"),
       ("9", "IO16", "N:BTN_PARAR"), ("10", "IO17", "P:MEAS_ZX"), ("11", "IO18", "P:RTC_INT"), ("12", "IO8", "P:I2C_SDA"),
       ("13", "IO19", "NC"), ("14", "IO20", "NC"), ("15", "IO3", "NC"), ("16", "IO46", "NC"), ("17", "IO9", "P:I2C_SCL"),
       ("18", "IO10", "P:MEAS_CS"), ("19", "IO11", "P:MEAS_MOSI"), ("20", "IO12", "P:MEAS_SCK"), ("21", "IO13", "P:MEAS_MISO"),
       ("22", "IO14", "P:MEAS_IRQ"), ("23", "IO21", "P:MEAS_WARN"), ("24", "IO47", "NC"), ("25", "IO48", "NC")]
der = [("26", "IO45", "NC"), ("27", "IO0", "N:ESP_IO0"), ("28", "IO35", "NC"), ("29", "IO36", "NC"), ("30", "IO37", "NC"),
       ("31", "IO38", "NC"), ("32", "IO39", "NC"), ("33", "IO40", "NC"), ("34", "IO41", "NC"), ("35", "IO42", "NC"),
       ("36", "RXD0", "N:UART_RX"), ("37", "TXD0", "N:UART_TX"), ("38", "IO2", "NC"), ("39", "IO1", "NC")] + \
      [(str(n), f"GND_{n - 38}", "GND") for n in range(40, 50)]
ic(250, 40, 170, "U4", "ESP32-S3-WROOM-1-N16R2", izq, der, paso=27, stub=24)
svg("F4_s3_esp32", 770, "U4 ESP32-S3-WROOM-1-N16R2 con lo que va en cada uno de sus 49 pines: puertos hacia las otras hojas, net labels locales, +3V3, GND y No ERC en los pines libres.")

# ---------- F4_s4: alimentación y arranque del módulo ----------
t(20, 30, "+3V3 junto al pin 2", "ts")
pwr(60, 80, "+3V3")
wire((60, 80), (220, 80))
cap_v(60, 80, "C33", "22 µF X5R", "CL21A226MAQNNNE"); gnd(60, 140)
cap_v(220, 80, "C34", "100 nF X7R", "CL21B104KBCNNNC"); gnd(220, 140); dot(220, 80)
t(400, 30, "EN (pin 3) e IO0 (pin 27)", "ts")
pwr(470, 80, "+3V3")
res_v(470, 80, "R22", "10 kΩ", "RC0805FR-0710KL", "left")
wire((470, 140), (470, 160), (660, 160)); dot(470, 160); dot(540, 160)
net(660, 151, "ESP_EN", "end")
cap_v(470, 160, "C32", "1 µF X7R", "CL21B105KAFNNNE", "left"); gnd(470, 220)
sw_v(540, 160, "SW2", "RESET · DNP", "TS-1187A-B-A-B"); gnd(540, 220)
net(540, 271, "ESP_IO0")
wire((540, 280), (540, 300)); dot(540, 280)
sw_v(540, 300, "SW3", "BOOT · DNP", "TS-1187A-B-A-B"); gnd(540, 360)
t(20, 300, "SW2 y SW3: pines A1/B1 (COM) a la red, C1/D1 (NO) a GND.", "ts")
t(20, 316, "Parámetro Assembly = DNP en los dos.", "ts")
svg("F4_s4_arranque", 400, "Desacople del módulo: C33 22 µF y C34 100 nF de +3V3 a GND. EN: R22 10 kΩ a +3V3, C32 1 µF a GND y SW2 RESET (DNP) a GND. IO0: SW3 BOOT (DNP) a GND.")

# ---------- F4_s5: LEDs, PARAR y J8 ----------
for i, (nt, r, led, val, mpn) in enumerate([("LED_WIFI", "R28", "LED3", "verde WiFi", "APT2012SGC"),
                                            ("LED_CARGA", "R29", "LED4", "verde carga", "APT2012SGC"),
                                            ("LED_FALLA", "R30", "LED5", "rojo falla", "APT2012SURCK")]):
    x = 40 + i * 150
    net(x, 31, nt)
    wire((x, 40), (x, 50))
    res_v(x, 50, r, "1 kΩ", "RC0805FR-071KL")
    led_v(x, 110, led, val, mpn)
    gnd(x, 170)
t(20, 222, "Botón PARAR", "ts")
pwr(80, 270, "+3V3")
res_v(80, 270, "R27", "10 kΩ", "RC0805FR-0710KL")
wire((80, 330), (80, 350), (520, 350)); dot(80, 350); dot(200, 350); dot(310, 350)
net(84, 341, "PARAR_IN")
sw_v(200, 350, "SW1", "PARAR", "TS-1187A-B-A-B"); gnd(200, 410)
cap_v(310, 350, "C36", "100 nF X7R", "CL21B104KBCNNNC"); gnd(310, 410)
res_h(520, 350, "R31", "1 kΩ", "RC0805FR-071KL")
wire((580, 350), (660, 350)); net(660, 341, "BTN_PARAR", "end")
e('<g class="box"><rect x="40" y="480" width="60" height="150" rx="4" stroke-width="0.8"/></g>')
t(70, 470, "J8", "th", "middle"); t(70, 646, "61300611121 · 1×6", "ts", "middle")
for k, cx in enumerate(["PWR:+3V3", "N:UART_TX", "N:UART_RX", "N:ESP_EN", "N:ESP_IO0", "GND"]):
    yy = 500 + k * 22
    t(92, yy, str(k + 1), "ts", "end")
    wire((100, yy), (140, yy))
    conectar(140, yy, cx, "der")
e('<g class="box"><rect x="330" y="480" width="60" height="70" rx="4" stroke-width="0.8"/></g>')
t(360, 470, "J7", "th", "middle"); t(360, 566, "borne 2P 3,5 mm (1751248)", "ts", "middle")
t(382, 500, "1", "ts", "end"); t(382, 530, "2", "ts", "end")
wire((390, 500), (440, 500)); net(444, 491, "PARAR_IN")
wire((390, 530), (440, 530)); gnd(440, 530)
t(330, 596, "Botón de panel SW730RD (Sigma) cableado a J7.", "ts")
svg("F4_s5_leds_parar_j8", 670, "LED3, LED4 y LED5 con R28 a R30 de 1 kΩ desde LED_WIFI, LED_CARGA y LED_FALLA a GND. PARAR: R27 10 kΩ de +3V3 a PARAR_IN, SW1 a GND, C36 100 nF a GND y R31 1 kΩ hacia BTN_PARAR. J8: 3V3, UART_TX, UART_RX, ESP_EN, ESP_IO0, GND. J7: PARAR_IN y GND.")

# ---------- F4_s6: USB-C (J5 Würth 632723300011), CC y ESD ----------
der = [("A4 B4 A9 B9", "VBUS", "N:VBUS"), ("A6 B6", "D+", "N:USB_DP"), ("A7 B7", "D−", "N:USB_DN"),
       ("A5", "CC1", "N:CC1"), ("B5", "CC2", "N:CC2"), ("A1 B1 A12 B12", "GND", "GND"), ("S1–S4", "carcasa", "GND"),
       ("A2 A3 B2 B3", "TX SS", "NC"), ("A10 A11 B10 B11", "RX SS", "NC"), ("A8 B8", "SBU", "NC")]
ic(40, 40, 210, "J5", "Würth 632723300011 (USB-C)", [], der, paso=30, stub=30)
t(40, 412, "Cada fila agrupa pines que en Altium son separados:", "ts")
t(40, 428, "los cuatro VBUS juntos, los dos D+, los dos D−, todos los GND y la carcasa.", "ts")
t(40, 444, "TX/RX SuperSpeed y SBU llevan No ERC (es un puerto USB 2.0).", "ts")
# R23, R24
for k, (cc, r) in enumerate((("CC1", "R23"), ("CC2", "R24"))):
    x = 380 + k * 160
    net(x, 31, cc)
    wire((x, 40), (x, 50))
    res_v(x, 50, r, "5,1 kΩ", "RC0805FR-075K1L")
    gnd(x, 110)
# D5
izq = [("1", "I/O1_1", "N:USB_DP"), ("2", "GND", "GND"), ("3", "I/O2_1", "N:USB_DN")]
der = [("6", "I/O1_2", "N:USB_DP"), ("5", "VBUS", "N:VBUS"), ("4", "I/O2_2", "N:USB_DN")]
ic(430, 200, 110, "D5", "USBLC6-2SC6", izq, der, paso=30, stub=30)
svg("F4_s6_usb", 470, "J5 USB-C Würth 632723300011: VBUS (A4 B4 A9 B9) a VBUS, D+ (A6 B6) a USB_DP, D− (A7 B7) a USB_DN, CC1 y CC2 a R23 y R24 de 5,1 kΩ a GND, GND y carcasa a GND, pares SuperSpeed y SBU con No ERC. D5 USBLC6-2SC6: pines 1 y 6 a USB_DP, 3 y 4 a USB_DN, 5 a VBUS, 2 a GND.")

# ---------- F4_s7: J5 con el símbolo real de Altium (Content Vault) ----------
izq = [("A4", "VBUS", "N:VBUS"), ("A9", "VBUS", "N:VBUS"), ("B9", "VBUS", "N:VBUS"), ("B4", "VBUS", "N:VBUS"),
       ("A5", "CC", "N:CC1"), ("B5", "VCONN", "N:CC2"), ("A8", "SBU1", "NC"), ("B8", "SBU2", "NC"),
       ("A1", "GND", "GND"), ("A12", "GND", "GND"), ("B1", "GND", "GND"), ("B12", "GND", "GND"), ("Shell", "Shield", "GND")]
der = [("A6", "Dp1", "N:USB_DP"), ("A7", "Dn1", "N:USB_DN"), ("B6", "Dp2", "N:USB_DP"), ("B7", "Dn2", "N:USB_DN"),
       ("A2", "SSTXp1", "NC"), ("A3", "SSTXn1", "NC"), ("B2", "SSTXp2", "NC"), ("B3", "SSTXn2", "NC"),
       ("B11", "SSRXp1", "NC"), ("B10", "SSRXn1", "NC"), ("A11", "SSRXp2", "NC"), ("A10", "SSRXn2", "NC")]
ic(150, 40, 150, "J5", "632723300011 (Würth)", izq, der, paso=26, stub=26)
t(20, 450, "B5 dice VCONN pero en el receptáculo es CC2: lleva su propia R de 5,1 kΩ.", "ts")
for k, (cc, r) in enumerate((("CC1", "R23"), ("CC2", "R24"))):
    x = 440 + k * 120
    net(x, 31, cc); wire((x, 40), (x, 50))
    res_v(x, 50, r, "5,1 kΩ", "RC0805FR-075K1L"); gnd(x, 110)
izq = [("1", "I/O1_1", "N:USB_DP"), ("2", "GND", "GND"), ("3", "I/O2_1", "N:USB_DN")]
der = [("6", "I/O1_2", "N:USB_DP"), ("5", "VBUS", "N:VBUS"), ("4", "I/O2_2", "N:USB_DN")]
ic(450, 230, 130, "D5", "USBLC6-2SC6", izq, der, paso=30, stub=22)
svg("F4_s7_usb_altium", 470, "J5 con el símbolo de Altium: A4 A9 B9 B4 a VBUS, A5 a CC1, B5 (VCONN) a CC2, A1 A12 B1 B12 y Shell a GND, SBU con No ERC; a la derecha Dp1 y Dp2 a USB_DP, Dn1 y Dn2 a USB_DN, pares SuperSpeed con No ERC. R23 y R24 de CC1 y CC2 a GND. D5: 1 y 6 a USB_DP, 3 y 4 a USB_DN, 5 a VBUS, 2 a GND.")
