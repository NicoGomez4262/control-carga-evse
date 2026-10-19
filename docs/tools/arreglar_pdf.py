"""Corrige los PDF de Altium que salen recortados cuando Windows no está al 100 % de escala.

Con la escala de Windows al 125 %, Altium escribe la página al 80 % del tamaño real
(952 × 674 pt en vez de A3 = 1191 × 842 pt) pero dibuja el contenido completo, así que
se corta a la derecha y abajo. El dibujo sigue dentro del archivo: basta agrandar la
MediaBox de cada página hasta que lo contenga, manteniendo la esquina superior izquierda.

Uso:
    python docs/tools/arreglar_pdf.py docs/revisiones/F2_ALIMENTACION.pdf
    python docs/tools/arreglar_pdf.py --nuevo docs/revisiones/PROYECTO_F3.pdf
Sobrescribe el archivo (guarda una copia *_original.pdf la primera vez). Si *_original.pdf ya
existe, rehace el arreglo desde esa copia. Cuando el PDF se vuelve a exportar desde Altium con el
mismo nombre, se usa --nuevo: la exportación nueva reemplaza la copia *_original.pdf.
"""
import shutil
import sys
from pathlib import Path

import pymupdf

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def arreglar(ruta: Path, nuevo: bool = False) -> None:
    respaldo = ruta.with_name(ruta.stem + "_original.pdf")
    if nuevo or not respaldo.exists():
        shutil.copy2(ruta, respaldo)
    doc = pymupdf.open(respaldo)
    for pagina in doc:
        w, h = pagina.rect.width, pagina.rect.height
        xs, ys = [], []
        for d in pagina.get_drawings():
            xs += [d["rect"].x0, d["rect"].x1]
            ys += [d["rect"].y0, d["rect"].y1]
        for b in pagina.get_text("dict")["blocks"]:
            xs += [b["bbox"][0], b["bbox"][2]]
            ys += [b["bbox"][1], b["bbox"][3]]
        if not xs:
            continue
        # margen simétrico: el dibujo de Altium va centrado en la hoja real
        nuevo_w = max(w, max(xs) + max(0.0, min(xs)))
        nuevo_h = max(h, max(ys) + max(0.0, min(ys)))
        if nuevo_w <= w + 1 and nuevo_h <= h + 1:
            continue
        # coordenadas PDF (origen abajo a la izquierda): se conserva el borde superior
        caja = f"[0 {h - nuevo_h:.2f} {nuevo_w:.2f} {h:.2f}]"
        doc.xref_set_key(pagina.xref, "MediaBox", caja)
        doc.xref_set_key(pagina.xref, "CropBox", caja)
        print(f"página {pagina.number + 1}: {w:.0f} × {h:.0f} pt → {nuevo_w:.0f} × {nuevo_h:.0f} pt")
    doc.save(ruta, garbage=3, deflate=True)
    print(f"listo: {ruta} (original en {respaldo.name})")


if __name__ == "__main__":
    nuevo = "--nuevo" in sys.argv[1:]
    for arg in sys.argv[1:]:
        if arg != "--nuevo":
            arreglar(Path(arg), nuevo)
