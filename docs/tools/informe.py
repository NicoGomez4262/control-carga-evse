"""Genera el informe del proyecto (docs/informe/) en PDF.

Pasos:
  1. QR del video, del repositorio y del portafolio (qr_*.svg, con segno) y la foto de
     portada con la placa centrada (portada.jpg, desde docs/fotos/placa_1_arriba.jpg).
  2. informe.html -> EVSE_Monitor_Informe.pdf con Edge (o Chrome) sin interfaz.
  3. Revisa que salgan 5 páginas y, con --png DIR, guarda cada página como imagen
     (PyMuPDF) para revisarla.

Uso:
  python docs/tools/informe.py
  python docs/tools/informe.py --png <carpeta>
  python docs/tools/informe.py --pdf <otro.pdf>   (si el PDF está abierto en un visor)
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import segno

REPO = Path(__file__).resolve().parents[2]
CARPETA = REPO / "docs" / "informe"
HTML = CARPETA / "informe.html"
PDF = CARPETA / "EVSE_Monitor_Informe.pdf"

QR = {
    "qr_video.svg": "https://youtu.be/911OGRqqaCk",
    "qr_github.svg": "https://github.com/NicoGomez4262/control-carga-evse",
    "qr_portafolio.svg": "https://nicolasgomez.dev/#hw-evse",
}

NAVEGADORES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
]


def generar_qr() -> None:
    for nombre, url in QR.items():
        segno.make(url, error="m").save(
            str(CARPETA / nombre), kind="svg", scale=4, border=0, dark="#121b24", light=None, xmldecl=False
        )


def generar_portada() -> None:
    """Foto de portada: la placa girada como en Altium (J1/J2 a la izquierda) y centrada.

    Sale de docs/fotos/placa_1_arriba.jpg. Fuera del borde de la placa la mesa se oscurece hasta
    el color de la portada, así que la PCB queda sola sobre fondo oscuro, con un brillo verde suave
    detrás. El lienzo tiene la proporción del área de foto de la portada (816 × 592 px en el HTML).
    """
    import numpy as np
    from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

    noche = (14, 19, 23)
    foto = Image.open(REPO / "docs" / "fotos" / "placa_1_arriba.jpg").convert("RGB")
    foto = foto.rotate(90, expand=True)  # antihorario: lo de arriba queda a la izquierda
    placa = (32, 121, 942, 813)  # borde de la PCB en la foto girada
    centro = ((placa[0] + placa[2]) / 2, (placa[1] + placa[3]) / 2)

    # Fuera de la placa se apaga lo que parece mesa (gris claro, poco saturado); los conectores,
    # cables y la fuente, que sobresalen del borde, se quedan como están.
    dentro = Image.new("L", foto.size, 0)
    ImageDraw.Draw(dentro).rounded_rectangle(
        (placa[0] + 8, placa[1] + 8, placa[2] - 8, placa[3] - 8), radius=22, fill=255)
    dentro = np.asarray(dentro.filter(ImageFilter.GaussianBlur(3)), dtype=float) / 255
    hsv = np.asarray(foto.convert("HSV"), dtype=float)
    mesa = np.clip((hsv[..., 2] - 55) / 65, 0, 1) * np.clip((85 - hsv[..., 1]) / 45, 0, 1)
    t = Image.fromarray(np.uint8(255 * mesa * (1 - dentro))).filter(ImageFilter.GaussianBlur(2))
    apagada = ImageEnhance.Brightness(foto).enhance(0.1)
    foto = Image.composite(apagada, foto, t)
    dentro = Image.fromarray(np.uint8(255 * dentro))

    escala = 0.6  # la placa (700 px de alto girada) queda de 420 px en la portada
    lienzo = (round(816 / escala), round(592 / escala))
    destino = (lienzo[0] / 2, 262 / escala)  # centrada a lo ancho; su centro a 262 px de 592
    pos = (round(destino[0] - centro[0]), round(destino[1] - centro[1]))

    fondo = Image.new("RGB", lienzo, noche)
    brillo = Image.new("L", lienzo, 0)
    rx, ry = 620, 470
    ImageDraw.Draw(brillo).ellipse((destino[0] - rx, destino[1] - ry, destino[0] + rx, destino[1] + ry), fill=120)
    brillo = brillo.filter(ImageFilter.GaussianBlur(140))
    fondo = Image.composite(Image.new("RGB", lienzo, (24, 62, 46)), fondo, brillo)

    borde = 70
    mascara = Image.new("L", foto.size, 0)
    dib = ImageDraw.Draw(mascara)
    for i in range(borde):
        dib.rectangle((i, i, foto.width - 1 - i, foto.height - 1 - i), outline=round(255 * (i + 1) / borde))
    dib.rectangle((borde, borde, foto.width - 1 - borde, foto.height - 1 - borde), fill=255)
    mascara = Image.composite(Image.new("L", foto.size, 255), mascara, dentro)  # la placa nunca se desvanece
    fondo.paste(foto, pos, mascara)
    fondo.save(CARPETA / "portada.jpg", quality=90, optimize=True, progressive=True)


def navegador() -> str:
    for ruta in NAVEGADORES:
        if Path(ruta).exists():
            return ruta
    sys.exit("No encontré Edge ni Chrome.")


def imprimir(salida: Path) -> None:
    """Imprime a un archivo temporal y después lo pone en `salida`.

    Edge no avisa si no puede escribir el PDF (por ejemplo, si está abierto en un visor de Windows),
    así que se revisa aquí.
    """
    with tempfile.TemporaryDirectory() as tmp:
        nuevo = Path(tmp) / "informe.pdf"
        orden = [
            navegador(), "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
            f"--user-data-dir={Path(tmp) / 'perfil'}", "--no-pdf-header-footer", "--virtual-time-budget=20000",
            "--run-all-compositor-stages-before-draw", f"--print-to-pdf={nuevo}", HTML.as_uri(),
        ]
        subprocess.run(orden, check=True, capture_output=True, timeout=180)
        if not nuevo.exists() or nuevo.stat().st_size == 0:
            sys.exit("Edge no generó el PDF.")
        try:
            shutil.copyfile(nuevo, salida)
        except PermissionError:
            sys.exit(f"No pude escribir {salida}: ciérralo en el visor de PDF y vuelve a correr el script.")


def revisar(pdf: Path, png: Path | None) -> None:
    import pymupdf

    doc = pymupdf.open(pdf)
    fuentes = sorted({f[3] for p in doc for f in p.get_fonts()})
    print(f"{pdf.name}: {doc.page_count} páginas, {pdf.stat().st_size / 1e6:.2f} MB")
    print("Fuentes:", ", ".join(fuentes))
    if doc.page_count != 5:
        print("OJO: el informe debe tener 5 páginas.")
    if png:
        png.mkdir(parents=True, exist_ok=True)
        for i, pagina in enumerate(doc, 1):
            pagina.get_pixmap(dpi=110).save(png / f"informe_p{i}.png")
        print("Imágenes en", png)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--png", type=Path, help="carpeta donde guardar cada página como PNG")
    ap.add_argument("--pdf", type=Path, default=PDF, help=f"dónde escribir el PDF (por defecto {PDF.name})")
    args = ap.parse_args()
    generar_qr()
    generar_portada()
    imprimir(args.pdf)
    revisar(args.pdf, args.png)


if __name__ == "__main__":
    main()
