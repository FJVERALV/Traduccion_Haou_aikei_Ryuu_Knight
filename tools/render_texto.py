"""Dibuja un texto con la fuente del juego (para copiarlo en los PNG de menús).

Uso:
    python tools/render_texto.py "Guardar partida" guardar.png [--junto]

Genera un PNG en blanco y negro dividido en celdas de 16x16, igual que los menús
pre-renderizados de celdas_31_fuente_y_menus.png. --junto usa letra 1 px más junta.
Usa la fuente de traduccion/graficos si existe (con tus cambios y letras españolas).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PIL import Image                                  # noqa: E402
from rk_common import (ROOT, load_en_rom, encode_message, render_vwf,  # noqa: E402
                       split_cells, WIDTHS)
import graficos                                        # noqa: E402


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 2:
        raise SystemExit(__doc__)
    text, out = args
    rom = load_en_rom()
    g = os.path.join(ROOT, "traduccion", "graficos")
    if os.path.exists(os.path.join(g, "celdas_31_fuente_y_menus.png")):
        graficos.png_to_cells16(rom, 0x18C000, 512, os.path.join(g, "celdas_31_fuente_y_menus.png"))
        with open(os.path.join(g, "anchos_fuente.txt"), encoding="utf-8") as f:
            for line in f:
                if line.startswith("#") or not line.strip():
                    continue
                parts = [x.strip() for x in line.split("|")]
                rom[WIDTHS + int(parts[0], 16)] = int(parts[-1])
    else:
        graficos.make_spanish_glyphs16(rom)
    rows, w = render_vwf(encode_message(text), rom, spacing=-1 if "--junto" in sys.argv else 0)
    cells = split_cells(rows, w)
    img = Image.new("P", (16 * len(cells), 16), 0)
    img.putpalette(graficos.PAL_1BPP)
    px = img.load()
    for c, cell in enumerate(cells):
        for y, r in enumerate(cell):
            for x in range(16):
                if r >> (15 - x) & 1:
                    px[c * 16 + x, y] = 1
    img.save(out)
    print(f"{out}: {w} px, {len(cells)} celdas")


if __name__ == "__main__":
    main()
