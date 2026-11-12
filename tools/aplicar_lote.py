"""Aplica un lote de traducciones a traduccion/dialogos.txt y comprueba los anchos.

Uso:
    python tools/aplicar_lote.py lote.txt [--comprobar]

Formato del lote (igual que dialogos.txt, sin comentarios):
    @0005
    Texto traducido
    segunda línea{fin}

    @0006
    ...
Cada mensaje termina en la línea anterior al siguiente @NNNN; se quita una sola
línea en blanco final (la separadora). Con --comprobar sólo valida, no escribe.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rk_common import (ROOT, encode_message, load_en_rom, WIDTHS, NAME_PX,  # noqa: E402
                       SPANISH_REV, set_dlg_width, dlg_widths)
from insertar import parse_dialogos, MAX_LINE_PX                            # noqa: E402
import graficos                                                             # noqa: E402



def widths_with_names(data, w):
    """Como line_widths, pero estimando los nombres en NAME_PX."""
    res, cur, i = [], 0, 0
    while i < len(data):
        b = data[i]
        if b == 0xFE:
            s = data[i + 1]
            if s == 0x00:
                cur += NAME_PX; i += 3; continue
            if s in (0x09, 0x08):
                res.append(cur); cur = 0
            i += 2
            continue
        cur += w[b]; i += 1
    res.append(cur)
    return res


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    only_check = "--comprobar" in sys.argv
    lote = parse_dialogos(args[0])
    rom = load_en_rom()
    graficos.make_spanish_glyphs16(rom)
    for c in SPANISH_REV:
        set_dlg_width(rom, c, rom[WIDTHS + c])
    w = dlg_widths(rom)
    problems = 0
    for i, t in sorted(lote.items()):
        data = encode_message(t, f"@{i:04d}")
        if "Ú" in t or "Ü" in t:
            problems += 1
            print(f"@{i:04d}: usa Ú/Ü, que no existen en la fuente (saldría U)")
        for k, px in enumerate(widths_with_names(data, w)):
            if px > MAX_LINE_PX:
                problems += 1
                parts = re.split(r"\n|\{ventana\}", t)
                print(f"@{i:04d}: {px} px > {MAX_LINE_PX}: {parts[k] if k < len(parts) else ''}")
    if only_check:
        print(f"{len(lote)} mensajes, {problems} líneas demasiado largas")
        return

    path = os.path.join(ROOT, "traduccion", "dialogos.txt")
    out, cur, skipping = [], None, False
    with open(path, encoding="utf-8") as f:
        lines = f.read().split("\n")
    for line in lines:
        if line.startswith("@"):
            cur = int(line[1:])
            out.append(line)
            skipping = cur in lote
            if skipping:
                # conserva los comentarios ingleses que siguen, luego el texto nuevo
                pass
            continue
        if skipping:
            if line.startswith("#"):
                out.append(line)
                continue
            if lote.get(cur) is not None:
                out.append(lote[cur])
                out.append("")
                lote[cur] = None
            continue
        out.append(line)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out))
    print(f"Aplicados {sum(1 for v in lote.values() if v is None)} mensajes; "
          f"{problems} líneas demasiado largas")


if __name__ == "__main__":
    main()
