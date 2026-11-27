"""Genera el informe del proyecto (docs/informe/) en PDF.

Pasos:
  1. QR del video, del repositorio y del portafolio (qr_*.svg, con segno).
  2. informe.html -> EVSE_Monitor_Informe.pdf con Edge (o Chrome) sin interfaz.
  3. Revisa que salgan 5 páginas y, con --png DIR, guarda cada página como imagen
     (PyMuPDF) para revisarla.

Uso:
  python docs/tools/informe.py
  python docs/tools/informe.py --png <carpeta>
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


def navegador() -> str:
    for ruta in NAVEGADORES:
        if Path(ruta).exists():
            return ruta
    sys.exit("No encontré Edge ni Chrome.")


def imprimir() -> None:
    with tempfile.TemporaryDirectory() as perfil:
        orden = [
            navegador(), "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
            f"--user-data-dir={perfil}", "--no-pdf-header-footer", "--virtual-time-budget=20000",
            "--run-all-compositor-stages-before-draw", f"--print-to-pdf={PDF}", HTML.as_uri(),
        ]
        subprocess.run(orden, check=True, capture_output=True, timeout=180)


def revisar(png: Path | None) -> None:
    import pymupdf

    doc = pymupdf.open(PDF)
    fuentes = sorted({f[3] for p in doc for f in p.get_fonts()})
    print(f"{PDF.name}: {doc.page_count} páginas, {PDF.stat().st_size / 1e6:.2f} MB")
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
    args = ap.parse_args()
    generar_qr()
    imprimir()
    revisar(args.png)


if __name__ == "__main__":
    main()
