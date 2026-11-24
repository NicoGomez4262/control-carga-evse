"""Genera src/ca_raiz.h con los certificados raíz que el ESP32 usa para verificar el TLS del servidor.

Firebase (Realtime Database e identitytoolkit.googleapis.com) usa Google Trust Services; Telegram
(api.telegram.org) usa GoDaddy; se deja ISRG (Let's Encrypt) por si se usa un dominio propio. Salen del
paquete `certifi` (lista de Mozilla), no de memoria. Cadenas revisadas con `openssl s_client` (24 nov 2026).

Uso:  python tools/generar_ca.py
"""
import pathlib
import re
import sys

import certifi

RAICES = [
    "GTS Root R1",
    "GTS Root R3",
    "GTS Root R4",
    "Go Daddy Root Certificate Authority - G2",
    "ISRG Root X1",
    "ISRG Root X2",
]

texto = pathlib.Path(certifi.where()).read_text(encoding="utf-8")
bloques = re.findall(r"# Issuer: (.*?)\n.*?(-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----)", texto, re.S)

elegidos = []
for nombre in RAICES:
    pem = next((p for emisor, p in bloques if f"CN={nombre}" in emisor), None)
    if pem is None:
        sys.exit(f"No está en certifi: {nombre}")
    elegidos.append((nombre, pem))

salida = pathlib.Path(__file__).resolve().parent.parent / "src" / "ca_raiz.h"
with salida.open("w", encoding="utf-8", newline="\n") as f:
    f.write("// Generado por tools/generar_ca.py desde certifi " + certifi.__version__ + ". No editar a mano.\n")
    f.write("// Raíces de Google Trust Services (Firebase), GoDaddy (Telegram) y Let's Encrypt (ISRG).\n")
    f.write("#pragma once\n\nstatic const char CA_RAIZ[] =\n")
    for nombre, pem in elegidos:
        f.write(f"    // {nombre}\n")
        for linea in pem.strip().splitlines():
            f.write(f'    "{linea}\\n"\n')
    f.write("    ;\n")
print(f"{salida}: {len(elegidos)} raíces")
