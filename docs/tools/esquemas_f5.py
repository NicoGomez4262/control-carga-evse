# -*- coding: utf-8 -*-
"""Esquemas literales por bloque de la hoja 05_SENSORES (F5). Escribe docs/esquemas/F5_*.svg.

Reusa las funciones de dibujo de esquemas.py y esquemas_f4.py (ic, conectar, ...) y agrega port2
(puerto bidireccional, con punta a los dos lados). Los números y nombres de pin son los de SamacSys.SchLib.
Uso: python docs/tools/esquemas_f5.py   (desde la carpeta docs/esquemas)
"""
from pathlib import Path

exec(Path(__file__).with_name("esquemas_f4.py").read_text(encoding="utf-8").split("# ---------- F4_s1")[0])


def port2(x, y, s, w=100):  # puerto bidireccional de x a x+w
    pts = f"{x},{y} {x+9},{y-9} {x+w-9},{y-9} {x+w},{y} {x+w-9},{y+9} {x+9},{y+9}"
    e(f'<g class="c-amber"><polygon points="{pts}" stroke-width="0.8"/><text class="ts" x="{x+w/2}" y="{y}" text-anchor="middle" dominant-baseline="central">{s}</text></g>')


# ---------- F5_s1: puertos del bus I²C y pull-ups (una sola pareja en todo el bus) ----------
port2(14, 110, "I2C_SCL")
wire((114, 110), (430, 110)); net(430, 101, "I2C_SCL", "end")
pwr(220, 40, "+3V3"); res_v(220, 40, "R33", "4,7 kΩ", "RC0805FR-074K7L")
wire((220, 100), (220, 110)); dot(220, 110)
port2(14, 190, "I2C_SDA")
wire((114, 190), (600, 190)); net(600, 181, "I2C_SDA", "end")
pwr(500, 120, "+3V3"); res_v(500, 120, "R32", "4,7 kΩ", "RC0805FR-074K7L")
wire((500, 180), (500, 190)); dot(500, 190)
t(20, 232, "La net label va también en el cable del puerto: en Altium un puerto y una net label del mismo", "ts")
t(20, 248, "nombre no se unen en la misma hoja (lección de F4). U6 y U7 se conectan con esas net labels.", "ts")
svg("F5_s1_i2c", 262, "Puerto I2C_SCL con su cable, net label I2C_SCL y R33 de 4,7 kiloohm a +3V3; puerto I2C_SDA con su cable, net label I2C_SDA y R32 de 4,7 kiloohm a +3V3.")

# ---------- F5_s2: U6 AHT20 con el filtro RC de VDD que pide el fabricante ----------
izq = [("1", "NC_1", "NC"), ("2", "VDD", "N:AHT_VDD"), ("3", "SCL", "N:I2C_SCL")]
der = [("6", "NC_2", "NC"), ("5", "GND", "GND"), ("4", "SDA", "N:I2C_SDA")]
ic(300, 50, 130, "U6", "AHT20 (0x38)", izq, der, paso=40, stub=40)
y0 = 280
t(20, y0 - 44, "Filtro de VDD (datasheet: R1 de 330–390 Ω y C1 de 10 µF), junto a U6", "ts")
pwr(40, y0, "+3V3"); wire((40, y0), (60, y0))
res_h(60, y0, "R38", "330 Ω", "RC0805FR-07330RL")
wire((120, y0), (470, y0)); net(470, y0 - 9, "AHT_VDD", "end")
dot(200, y0); dot(350, y0)
cap_v(200, y0, "C37", "10 µF X5R", "CL21A106KAYNNNE"); gnd(200, y0 + 60)
cap_v(350, y0, "C38", "100 nF X7R", "CL21B104KBCNNNC"); gnd(350, y0 + 60)
t(20, y0 + 104, "PCB (F8): sin pistas ni cobre debajo de U6 y, si cabe, una ranura de 1,5 mm alrededor para aislarlo del calor.", "ts")
svg("F5_s2_aht20", y0 + 118, "U6 AHT20: pin 2 VDD a la red AHT_VDD, pin 3 SCL a I2C_SCL, pin 4 SDA a I2C_SDA, pin 5 GND, pines 1 y 6 con No ERC. Filtro: +3V3, R38 de 330 ohm hasta AHT_VDD, con C37 de 10 microfaradios y C38 de 100 nanofaradios a GND.")

# ---------- F5_s3: U7 DS3231SN, pull-up de RTC_INT, desacople y BT1 ----------
izq = [("1", "32kHz", "NC"), ("2", "VCC", "PWR:+3V3"), ("3", "INT/SQW", ""), ("4", "RST", "NC"),
       ("5", "N.C.", "GND"), ("6", "N.C.", "GND"), ("7", "N.C.", "GND"), ("8", "N.C.", "GND")]
der = [("16", "SCL", "N:I2C_SCL"), ("15", "SDA", "N:I2C_SDA"), ("14", "VBAT", "N:RTC_VBAT"), ("13", "GND", "GND"),
       ("12", "N.C.", "GND"), ("11", "N.C.", "GND"), ("10", "N.C.", "GND"), ("9", "N.C.", "GND")]
ic(250, 50, 180, "U7", "DS3231SN", izq, der, paso=30, stub=40)
port(14, 132, "RTC_INT", "left", 90)
wire((104, 132), (210, 132)); dot(150, 132)
pwr(150, 72, "+3V3"); res_v(150, 72, "R34", "10 kΩ", "RC0805FR-0710KL", "left", ly=80)
y0 = 400
t(20, y0 - 50, "Desacople de VCC (pin 2), pegado al pin", "ts")
pwr(60, y0, "+3V3"); cap_v(60, y0, "C39", "100 nF X7R", "CL21B104KBCNNNC"); gnd(60, y0 + 60)
ic(480, y0 - 50, 100, "BT1", "BAT-HLD-001 · CR2032", [("1", "+", "N:RTC_VBAT"), ("3", "−", "GND"), ("2", "+", "N:RTC_VBAT")], [],
   paso=40, stub=40)
t(20, y0 + 130, "Pines 5–12 (N.C.) a GND: el datasheet lo exige. 1 y 4 libres con No ERC. VBAT sin condensador.", "ts")
svg("F5_s3_ds3231", y0 + 144, "U7 DS3231SN: pin 1 y 4 con No ERC, pin 2 VCC a +3V3, pin 3 INT/SQW al puerto RTC_INT con R34 de 10 kiloohm a +3V3, pines 5 a 12 a GND, 13 GND, 14 VBAT a RTC_VBAT, 15 SDA a I2C_SDA, 16 SCL a I2C_SCL. C39 de 100 nanofaradios de +3V3 a GND. BT1: pines 1 y 2 (+) a RTC_VBAT y pin 3 (−) a GND.")

# ---------- F5_s4: J4 sonda DS18B20, 1-Wire, ESD y protección del 3V3 ----------
pwr(40, 50, "+3V3"); wire((40, 50), (70, 50))
res_h(70, 50, "R37", "68 Ω 1206", "RC1206FR-0768RL")
wire((130, 50), (540, 50), (540, 200), (570, 200)); net(160, 41, "J4_3V3")
dot(360, 50); cap_v(360, 50, "C40", "100 nF X7R", "CL21B104KBCNNNC"); gnd(360, 110)
port2(14, 230, "OW_DATA")
wire((114, 230), (200, 230)); dot(150, 230)
pwr(150, 170, "+3V3"); res_v(150, 170, "R35", "4,7 kΩ", "RC0805FR-074K7L", "left")
res_h(200, 230, "R36", "100 Ω", "RC0805FR-07100RL")
wire((260, 230), (320, 230)); net(268, 221, "OW_J4")
izq = [("1", "I/O1_1", ""), ("2", "GND", "GND"), ("3", "I/O2_1", "NC")]
der = [("6", "I/O1_2", ""), ("5", "VBUS", "N:J4_3V3"), ("4", "I/O2_2", "NC")]
ic(350, 208, 120, "D6", "USBLC6-2SC6", izq, der, paso=30, stub=30)
wire((500, 230), (570, 230)); net(506, 221, "OW_J4")
ic(600, 178, 60, "J4", "1751251", [("1", "3V3", ""), ("2", "DATA", ""), ("3", "GND", "GND")], [], paso=30, stub=30)
t(20, 372, "OW_J4 va en los dos lados de D6: los pines 1 y 6 son la misma línea por dentro, pero en Altium son pines distintos.", "ts")
t(20, 388, "Serigrafía de J4: 3V3 · DQ · GND (rojo, amarillo, negro en la sonda de Sigma; verificar al comprar).", "ts")
svg("F5_s4_j4", 402, "J4 de la sonda: +3V3 por R37 de 68 ohm a la red J4_3V3, con C40 de 100 nanofaradios a GND, hasta J4 pin 1. Puerto OW_DATA con R35 de 4,7 kiloohm a +3V3, R36 de 100 ohm hasta OW_J4, que entra por D6 pin 1 y sale por D6 pin 6 hasta J4 pin 2. D6 pin 5 VBUS a J4_3V3, pin 2 a GND, pines 3 y 4 con No ERC. J4 pin 3 a GND.")
