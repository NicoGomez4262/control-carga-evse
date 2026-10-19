"""Copia el proyecto de Altium a la carpeta altium/ del repositorio y, si se pide, sube los cambios a GitHub.

El proyecto de Altium se sigue editando donde siempre (D12, fuera del repositorio). altium/ es un espejo de sus
fuentes: el .PrjPcb, las hojas, la PCB, el OutJob, la plantilla y las librerías. No copia History/,
Project Logs/, __Previews/ ni PDF (los PDF de revisión van en docs/revisiones/). Las rutas del .PrjPcb son
relativas, así que el espejo se abre tal cual en Altium.

Uso:
    python docs/tools/sincronizar_altium.py                 solo copia y dice qué cambió
    python docs/tools/sincronizar_altium.py --commit        copia, hace commit de todo el repo y push
    python docs/tools/sincronizar_altium.py --commit -m "F7: BOM con proveedores"

Con --commit entra todo lo que haya cambiado en el repositorio (altium/ y docs/), respetando .gitignore.
Si Altium está abierto, avisa: se copia lo último guardado, no lo que esté sin guardar.
"""
import argparse
import filecmp
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ORIGEN = Path("C:/Nicolas/UNIVERSIDAD - 2026/Hardware en IoT/Control de Carga IoT/Control de Carga IoT")
REPO = Path(__file__).resolve().parents[2]
DESTINO = REPO / "altium"

# Carpeta relativa al proyecto → extensiones que se copian de ella (sin entrar a subcarpetas).
FUENTES = {
    ".": {".PrjPcb", ".PrjPcbStructure", ".SchDoc", ".PcbDoc", ".OutJob"},
    "lib": {".SchLib", ".PcbLib", ".IntLib"},
    "templates": {".SchDoc", ".SchDot"},
}


def archivos(raiz: Path) -> set[Path]:
    """Rutas relativas de los archivos fuente bajo raiz, según FUENTES."""
    salida = set()
    for carpeta, extensiones in FUENTES.items():
        d = raiz / carpeta
        if not d.is_dir():
            continue
        for f in d.iterdir():
            if f.is_file() and f.suffix in extensiones and not f.name.startswith("~"):
                salida.add(f.relative_to(raiz))
    return salida


def altium_abierto() -> bool:
    try:
        r = subprocess.run(["tasklist", "/FI", "IMAGENAME eq X2.EXE"], capture_output=True, text=True, errors="replace")
        return "X2.EXE" in r.stdout
    except OSError:
        return False


def sincronizar() -> list[str]:
    if not ORIGEN.is_dir():
        sys.exit(f"No encuentro el proyecto de Altium en {ORIGEN}")
    origen, destino = archivos(ORIGEN), archivos(DESTINO)
    cambios = []
    for rel in sorted(origen):
        src, dst = ORIGEN / rel, DESTINO / rel
        if dst.exists() and filecmp.cmp(src, dst, shallow=False):
            continue
        cambios.append(("modificado" if dst.exists() else "nuevo") + f"  {rel.as_posix()}")
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    for rel in sorted(destino - origen):
        (DESTINO / rel).unlink()
        cambios.append(f"borrado     {rel.as_posix()}")
    return cambios


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True, errors="replace")


def subir(mensaje: str | None) -> None:
    git("add", "-A")
    if not git("diff", "--cached", "--name-only").stdout.strip():
        print("Nada que subir: el repositorio ya está al día.")
        return
    mensaje = mensaje or f"Sincroniza Altium y documentación ({date.today().isoformat()})"
    r = git("commit", "-m", mensaje)
    if r.returncode:
        sys.exit(r.stderr or r.stdout)
    print(r.stdout.strip().splitlines()[0])
    r = git("push")
    if r.returncode:
        sys.exit("El commit quedó local, pero el push falló:\n" + r.stderr)
    print("Subido a GitHub.")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--commit", action="store_true", help="hace commit de todo el repo y push")
    ap.add_argument("-m", "--mensaje", help="mensaje del commit (con --commit)")
    a = ap.parse_args()

    if altium_abierto():
        print("Ojo: Altium está abierto. Se copia lo último guardado; guarda todo antes si hay cambios pendientes.")
    cambios = sincronizar()
    print("\n".join(cambios) if cambios else "altium/ ya estaba igual al proyecto.")
    if a.commit:
        subir(a.mensaje)


if __name__ == "__main__":
    main()
