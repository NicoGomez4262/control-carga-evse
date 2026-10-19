# -*- coding: utf-8 -*-
"""Genera los diagramas ASCII por fase y los inserta en los .md del proyecto.

Uso: python diagramas.py <archivo.md> [<archivo.md> ...]
Reemplaza marcadores <!--DIAG:ALL--> y <!--DIAG:F1--> ... <!--DIAG:F8--> (y bloques
ya generados entre <!--DIAG:Fx--> y <!--/DIAG-->) por el diagrama correspondiente.
"""
import re
import sys
from pathlib import Path

W = 54          # columna de la barrera izquierda
INNER = 10      # ancho interior de la barrera
P = 11          # ancho del prefijo de carril (marcador + nombre)

LABELS = {
    'BRK': 'Breaker del EVSE',
    'CT': 'F3 CT en L1',
    'EVSE': 'EVSE',
    'VEH': 'Vehículo',
    'PROT': 'F2 Protección',
    'RAIL': 'F2 Riel 12 V',
    'R78': 'F2 R-78CK + LC',
    'DRV': 'F6 Driver K1',
    'RSER': 'F3 Divisor',
    'ATM': 'F3 ATM90E26',
    'CTL': 'F3 Carga CT',
    'ESP': 'F4 ESP32-S3',
    'USB': 'F4 USB-C · USB-UART · auto-reset · LEDs',
    'SENS': 'F5 Sensores · RTC',
    'AUX': 'F2 Entrada banco 12 V',
}
STRAD = {'ACDC': ' AC-DC  ', 'RELAY': 'PhotoMOS', 'ISO': ' AMC3330'}

PCB = {'PROT', 'ACDC', 'RAIL', 'R78', 'AUX', 'RSER', 'ISO', 'ATM', 'CTL',
       'ESP', 'USB', 'SENS', 'RELAY', 'DRV'}
PHASES = {
    'ALL': set(),
    'F1': set(),
    'F2': {'PROT', 'ACDC', 'RAIL', 'R78', 'AUX'},
    'F3': {'RSER', 'ISO', 'ATM', 'CTL', 'CT'},
    'F4': {'ESP', 'USB'},
    'F5': {'SENS'},
    'F6': {'RELAY', 'DRV'},
    'F7': PCB | {'CT'},
    'F8': PCB,
}
BANNER = {
    'ALL': 'MAPA GENERAL · cada bloque indica la fase en que se diseña',
    'F1': '► ESTÁS AQUÍ: FASE 1 · 01_TOP.SchDoc — este diagrama completo ES la hoja TOP (un símbolo de hoja por cada F#)',
    'F2': '► ESTÁS AQUÍ: FASE 2 · 02_ALIMENTACION.SchDoc — se diseñan los bloques ▐marcados▌',
    'F3': '► ESTÁS AQUÍ: FASE 3 · 03_MEDICION.SchDoc — se diseñan los bloques ▐marcados▌',
    'F4': '► ESTÁS AQUÍ: FASE 4 · 04_MCU.SchDoc — se diseñan los bloques ▐marcados▌',
    'F5': '► ESTÁS AQUÍ: FASE 5 · 05_SENSORES.SchDoc — se diseñan los bloques ▐marcados▌',
    'F6': '► ESTÁS AQUÍ: FASE 6 · 06_ACTUACION.SchDoc — PhotoMOS K1 y salida J2 a los bornes de habilitación del EVSE ▐marcados▌',
    'F7': '► ESTÁS AQUÍ: FASE 7 · todas las hojas — revisión completa y BOM (todo ▐marcado▌)',
    'F8': '► ESTÁS AQUÍ: FASE 8 · EVSE_Monitor.PcbDoc — ubicación, ruteo y fabricación de toda la placa ▐marcada▌',
}
LANE_BLOCKS = {
    'ENERGÍA': {'PROT', 'ACDC', 'RAIL', 'R78'},
    'ACTUACIÓN': {'RELAY', 'DRV'},
    'MEDICIÓN V': {'RSER', 'ISO', 'ATM'},
    'MEDICIÓN I': {'CTL'},
    'CONTROL': {'ESP'},
    'INTERFAZ': {'USB'},
    'SENSORES': {'SENS'},
    'BANCO': {'AUX'},
}


def b(key, act):
    lab = LABELS[key]
    return ('▐' + lab + '▌') if key in act else ('[' + lab + ']')


def s(key, act):
    lab = STRAD[key]
    return ('▐' + lab + '▌') if key in act else (' ' + lab + ' ')


def fill(text, width, ch=' '):
    assert len(text) <= width, (text, len(text), width)
    return text + ch * (width - len(text))


def place(items, width=0):
    row = [' '] * width
    for pos, text in items:
        need = pos + len(text)
        if need > len(row):
            row += [' '] * (need - len(row))
        for i, ch in enumerate(text):
            row[pos + i] = ch
    return ''.join(row).rstrip()


def lane(name, act):
    mark = '►' if LANE_BLOCKS[name] & act else ' '
    return mark + fill(name, P - 1)


def bar(inner=' ' * INNER, left='┃', right='┃'):
    assert len(inner) == INNER, inner
    return left + inner + right


def diagram(phase):
    act = PHASES[phase]
    out = [BANNER[phase], '']

    # Circuito externo
    out.append('EXTERNO · instalación (fuera de la PCB)')
    brk, ct, evse, veh = (b(k, act) for k in ('BRK', 'CT', 'EVSE', 'VEH'))
    l1 = '  ' + brk + ' ─┬─► ' + ct + ' ─► ' + evse + ' ─► ' + veh
    p_tap = l1.index('┬')
    p_ct = l1.index(ct) + len(ct) // 2
    p_en = l1.index(evse) + 1
    p_probe = l1.index(evse) + len(evse) - 2
    out.append(l1)
    out.append(place([(p_tap, '│'), (p_ct, '│'), (p_en, '▲'), (p_probe, '│')]))
    out.append(place([(p_tap, '└─► J1'), (p_ct, '└─► J3'), (p_en, '│'),
                      (p_probe, '└─ sonda DS18B20 ─► J4')]))
    out.append(place([(p_en, '└─ J2 (bornes de habilitación)')]))
    out.append('═' * 112)

    # Encabezado de la PCB
    out.append(fill('PCB        ZONA RED · 120–240 VAC', W) + bar(' BARRERA  ') + '      ZONA SELV · 12 V y 3.3 V')
    out.append(fill('', W) + bar(' ≥ 6.4 mm '))
    out.append(fill('', W) + bar())

    # ENERGÍA
    e = lane('ENERGÍA', act) + 'J1 ─► ' + b('PROT', act) + ' ─┬'
    p_bus = len(e) - 1
    out.append(fill(e, W, '─') + bar(s('ACDC', act), '┨', '┠') + '─► ' + b('RAIL', act) + ' ─► ' + b('R78', act) + ' ─► 3V3')
    out.append(fill(place([(p_bus, '│')]), W) + bar('   (F2)   '))
    # MEDICIÓN V
    v = fill(lane('MEDICIÓN V', act), p_bus) + '└─► ' + b('RSER', act) + ' ─'
    right_v = '─► V ─► ' + b('ATM', act) + ' ═SPI═► ESP32-S3'
    out.append(fill(v, W, '─') + bar(s('ISO', act), '┨', '┠') + right_v)
    p_atm = W + INNER + 2 + len('─► V ─► ') + len(b('ATM', act)) // 2
    out.append(place([(0, fill('', W) + bar('   (F3)   ')), (p_atm, '▲ I')]))
    # MEDICIÓN I
    i = fill(fill(lane('MEDICIÓN I', act), W) + bar(), p_atm) + '└─◄ ' + b('CTL', act) + ' ◄─ J3'
    out.append(i)
    out.append(fill('', W) + bar())
    # ACTUACIÓN
    a = lane('ACTUACIÓN', act) + 'J2 ◄── contacto seco (aislado) '
    out.append(fill(a, W, '─') + bar(s('RELAY', act), '┨', '┠') + '◄─ LED ─ ' + b('DRV', act) + ' ◄─ GPIO ─ ESP32-S3')
    out.append(fill('', W) + bar('   (F6)   '))
    # CONTROL e interfaz
    out.append(fill(lane('CONTROL', act), W) + bar() + '   ' + b('ESP', act) + ' ─ WiFi ─► router ─► internet ─► app')
    out.append(fill(lane('INTERFAZ', act), W) + bar() + ' J5 ─► ' + b('USB', act) + ' ─► ESP32-S3')
    out.append(fill(lane('SENSORES', act), W) + bar() + ' J4 ─► ' + b('SENS', act) + ' ─► ESP32-S3')
    out.append(fill(lane('BANCO', act), W) + bar() + ' J6 ─► ' + b('AUX', act) + ' ─► D2 ─► +VIN')
    out.append('═' * 112)
    out.append('[F# bloque] fase en que se diseña · ▐bloque▌ se diseña en ESTA fase · ► carril con trabajo en esta fase')
    out.append('┃ ┃ barrera de aislamiento · ┨ ┠ componente que cruza la barrera (AC-DC, AMC3330, PhotoMOS K1)')
    out.append('│ L1/L2 (L/N en 120 V) con fusibles · J1–J6 conectores · J1 con cable largo a la línea · J2 contacto seco aislado')
    return '\n'.join(out)


def render(md_text):
    def repl(m):
        key = m.group(1)
        return '<!--DIAG:' + key + '-->\n```text\n' + diagram(key) + '\n```\n<!--/DIAG-->'
    pattern = re.compile(r'<!--DIAG:(ALL|F[1-8])-->(?:\n```text\n.*?\n```\n<!--/DIAG-->)?', re.S)
    return pattern.sub(repl, md_text)


if __name__ == '__main__':
    if len(sys.argv) == 1:
        sys.stdout.reconfigure(encoding='utf-8')
        for k in ('ALL', 'F2'):
            print(diagram(k))
            print()
    for name in sys.argv[1:]:
        path = Path(name)
        path.write_text(render(path.read_text(encoding='utf-8')), encoding='utf-8')
        print('ok', name)
