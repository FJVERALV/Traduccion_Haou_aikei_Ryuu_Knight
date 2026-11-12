"""Genera el parche español completo desde la ROM japonesa.

Uso (desde la carpeta del proyecto):
    python tools/reconstruir.py

Necesita, en la carpeta del proyecto:
  - Haou Taikei Ryuu Knight - Lord of Paladin (Japan) (Rev 1).sfc   (CRC32 2740560B)
  - Haou Taikei Ryuu Knight - Lord of Paladin (English) v1.0.bps     (parche inglés de
    Game Translate) o, en su lugar, la ROM inglesa ya parcheada.

Pasos: extrae lo que falte de traduccion/ (texto inglés y gráficos, que no se
incluyen en el repositorio), aplica todos los lotes de traduccion/lotes/ y crea
salida/Haou Taikei Ryuu Knight (ES).sfc y .bps. Copia el parche a RyuuKnight_ES.bps.
"""
import glob
import os
import shutil
import subprocess
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)


def run(*args):
    r = subprocess.run([sys.executable, *args], cwd=TOOLS)
    if r.returncode:
        raise SystemExit(r.returncode)


def main():
    run("extraer.py")
    for lote in sorted(glob.glob(os.path.join(ROOT, "traduccion", "lotes", "lote_*.txt"))):
        run("aplicar_lote.py", lote)
    run("insertar.py")
    src = os.path.join(ROOT, "salida", "Haou Taikei Ryuu Knight (ES).bps")
    shutil.copy(src, os.path.join(ROOT, "RyuuKnight_ES.bps"))
    print("\nParche listo: RyuuKnight_ES.bps")


if __name__ == "__main__":
    main()
