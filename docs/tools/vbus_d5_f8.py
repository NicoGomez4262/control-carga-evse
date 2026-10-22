# -*- coding: utf-8 -*-
"""F8 (22 oct): libera la vía de GND de D5 (pin 2) que el camino de VBUS de B4 dejó encerrada (Altium CERRADO).

El DRC dio «Un-Routed Net GND» y «Net Antennae» en la vía de D5.2 (118,3; 86,95). En Bottom, el camino de VBUS
que bajaba de J5.B4 por x = 117,3 hasta la vía de D5.5, junto con USB_DN y USB_DP, cerraba un bolsillo alrededor
de esa vía, y el plano no entraba. Ahora VBUS baja de J5.A9 por Top (x = 116,55, a la izquierda de USB_DN y de D5)
y pasa a Bottom con una vía en (116,55; 84,75), debajo de la vía de USB_DN; por Bottom solo queda el tramo corto
hasta la vía de D5.5. Las 3 pistas del camino viejo se reescriben en su mismo registro (de Bottom a Top).

Uso: python docs/tools/vbus_d5_f8.py [--escribir]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import revisar_ruteo_f8 as rr  # noqa: E402
import rutear_f8 as rt  # noqa: E402
import terminar_gnd_f8 as tg  # noqa: E402

TOP, BOT = rr.TOP, rr.BOT
REESCRIBIR = {
    ((117.3, 90.67), (117.3, 85.75)): dict(capa=TOP, x1=116.55, y1=87.85, x2=116.55, y2=84.75),
    ((117.3, 85.75), (116.75, 85.2)): dict(capa=TOP, x1=117.25, y1=88.55, x2=116.55, y2=87.85),
    ((116.75, 85.2), (116.75, 84.0)): dict(capa=TOP, x1=117.25, y1=89.0, x2=117.25, y2=88.55),
}
PISTAS = [dict(red="VBUS", capa=BOT, x1=116.55, y1=84.75, x2=116.55, y2=84.2, ancho=0.25),
          dict(red="VBUS", capa=BOT, x1=116.55, y1=84.2, x2=116.75, y2=84.0, ancho=0.25)]
VIAS = [dict(red="VBUS", x=116.55, y=84.75, hueco=0.3, dia=0.6)]


def main():
    objs, clases = rr.cargar()
    nuevos = {"pistas": [], "vias": [], "anillos": [], "mod_pistas": {}, "mod_vias": {}}
    for pts, m in REESCRIBIR.items():
        o = tg.buscar(objs, "VBUS", "pista", pts)
        f = rr.Forma("seg", [(m["x1"], m["y1"]), (m["x2"], m["y2"])], o["ancho"] / 2)
        o.update(capa=m["capa"], capas={m["capa"]}, formas=[f], caja=f.caja, nuevo=True)
        nuevos["mod_pistas"][o["k"]] = m
    for p in PISTAS:
        objs.append(rt.obj_pista(p))
        nuevos["pistas"].append(p)
    for v in VIAS:
        objs.append(rt.obj_via(v))
        nuevos["vias"].append(v)
    malos = rt.revisar_nuevos(objs, clases)
    grupos = [g for g in rr.conectividad(objs)["VBUS"].values() if any(o["tipo"] == "pad" for o in g)]
    print(f"Problemas: {len(malos)}; grupos de VBUS: {len(grupos)}")
    for m in malos:
        print("  ", m)
    if "--escribir" in sys.argv:
        if malos or len(grupos) != 1:
            sys.exit("No se escribe.")
        import aplicar_ruteo_f8
        aplicar_ruteo_f8.escribir(nuevos, None)


if __name__ == "__main__":
    main()
