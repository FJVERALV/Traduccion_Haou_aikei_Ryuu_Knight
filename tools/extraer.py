"""Extrae textos y gráficos de Haou Taikei Ryuu Knight (versión inglesa) para traducir.

Uso:
    python tools/extraer.py            # crea extraido/ y, si no existe, traduccion/
    python tools/extraer.py --forzar   # sobrescribe también traduccion/ (¡pierdes lo traducido!)

extraido/   = referencia en inglés, se regenera siempre.
traduccion/ = tu copia de trabajo; edítala y luego ejecuta tools/insertar.py
"""
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rk_common import *                       # noqa: E402,F401
from lzss import decompress, bank_table       # noqa: E402
import graficos                               # noqa: E402

OUT = os.path.join(ROOT, "extraido")
WORK = os.path.join(ROOT, "traduccion")

PRINTABLE = bytes(range(0x20, 0x7F))


# --- lectura de la ROM ---------------------------------------------------------------
def read_messages(rom):
    msgs = []
    for i in range(MSG_COUNT):
        e = MSG_TABLE + 3 * i
        p = lorom_to_file(rom[e + 2] << 16 | rom[e] | rom[e + 1] << 8)
        msgs.append(decode_message(rom, p)[0])
    return msgs


def read_name_strings(rom):
    out = []
    for i in range(NAME_COUNT):
        w = int.from_bytes(rom[NAME_PTRS + 2 * i:NAME_PTRS + 2 * i + 2], "little")
        fo = 0x180000 + w - 0x8000
        out.append(bytes(rom[fo:rom.index(0xFF, fo)]))
    return out


def read_tile_lists(rom, start=TILELISTS):
    p, lists = start, []
    for _ in range(NAME_COUNT):
        cur = []
        while rom[p] != 0xFF:
            cur.append(rom[p] | rom[p + 1] << 8)
            p += 2
        p += 1
        lists.append(cur)
    return lists


def spacing_for(idx):
    return -1 if 116 <= idx <= 127 else 0     # títulos de episodio: letra más junta


def ocr_name(rom, prefix: bytes, cells, spacing):
    """Recupera el texto completo de un nombre pre-renderizado (la tabla de texto
    lo corta a 15 letras) probando caracteres hasta que el render coincida."""
    target = [tuple(c) for c in cells]
    from rk_common import CANVAS
    trows = [0] * 16
    for k, c in enumerate(cells):
        for y in range(16):
            trows[y] |= c[y] << (CANVAS - 16 * (k + 1))

    def ok_prefix(t):
        rows, w = render_vwf(t, rom, spacing=spacing)
        if w > len(cells) * 16:
            return None
        sh = CANVAS - max(w, 0)
        if any((a >> sh) != (b >> sh) for a, b in zip(rows, trows)):
            return None
        return split_cells(rows, w)

    # sólo caracteres con ancho > 0 y glifo visible (más el espacio)
    cand = [c for c in PRINTABLE if rom[WIDTHS + c] > 0 and
            (c == 0x20 or any(read_cell16(rom, FONT16 + c * 32)))]
    stack = [prefix]
    seen = 0
    while stack and seen < 20000:
        t = stack.pop(); seen += 1
        mine = ok_prefix(t)
        if mine is None:
            continue
        if [tuple(c) for c in mine] == target:
            return t
        if len(t) > 60 or t.endswith(b"  "):
            continue
        for c in reversed(cand):
            stack.append(t + bytes([c]))
    return prefix


def read_default_names(rom):
    blk = bank_table(rom, 0x23)[44]
    data = decompress(rom, blk)[0]
    names = []
    for k in range(6):
        raw = data[k * 8:k * 8 + 8]
        names.append(raw.split(b"\xFF")[0].rstrip(b"\x00").decode("latin1"))
    return names


# --- escritura -----------------------------------------------------------------------
HEADER_DIALOGOS = """\
# ====================================================================================
#  Haou Taikei Ryuu Knight - DIÁLOGOS (1227 mensajes)
# ------------------------------------------------------------------------------------
#  - Cada mensaje empieza con una línea  @NNNN  (no la cambies ni borres mensajes).
#  - Las líneas que empiezan por # son comentarios (el texto inglés de referencia).
#  - Escribe la traducción debajo; cada salto de línea = salto de línea en el juego.
#  - Ancho máximo aproximado por línea: 236 píxeles (~33 letras). insertar.py avisa.
#  - Puedes usar: á é í ó ú ü ñ Á É Í Ó Ñ ¿ ¡
#  - Etiquetas (mantenlas):
#      {espera}      esperar a que el jugador pulse un botón
#      {ventana}     limpiar la ventana y seguir
#      {fin}         fin del diálogo
#      {nombre:NN}   nombre del personaje NN (01 = protagonista...)
#      {82}Nombre{82}   nombre del que habla
#      {88}...{89}, {84}...{85}, {86}...{87}  marcas de resaltado/comillas
#      {80}          guion largo
#  - Deja una línea en blanco antes de cada @NNNN.
# ====================================================================================

"""

HEADER_NOMBRES = """\
# ====================================================================================
#  NOMBRES de objetos, magias, títulos de episodio y lugares
# ------------------------------------------------------------------------------------
#  Formato:  NNN | inglés (referencia, no se usa) | TRADUCCIÓN
#  Sólo edita la tercera columna. En los menús se dibujan como gráficos generados
#  con la fuente del juego, así que pueden ser algo más largos que en inglés.
#  Los títulos de episodio (116-127) se dibujan con letra más junta.
#  Opcional: una cuarta columna  | texto corto  para la tabla de texto interna
#  (máx. 15 letras; si no la pones se recorta la traducción).
# ====================================================================================

"""

HEADER_PERSONAJES = """\
# Nombres por defecto de los personajes (máx. 8 letras, sin acentos: la pantalla
# de cambio de nombre sólo tiene letras inglesas).
# Formato:  N | inglés | TRADUCCIÓN

"""


def write_dialogos(path, msgs, with_translation):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(HEADER_DIALOGOS)
        for i, t in enumerate(msgs):
            f.write(f"@{i:04d}\n")
            for line in t.split("\n"):
                f.write(f"# {line}\n")
            if with_translation:
                f.write(t + "\n")
            f.write("\n")


HEADER_MENUS = """# ====================================================================================
#  MENÚS y opciones (Sí/No, tiendas, menú de sistema, configuración...)
# ------------------------------------------------------------------------------------
#  Formato:  NN | inglés | TRADUCCIÓN
#  Se dibujan como gráficos en un espacio fijo: insertar.py avisa si no caben.
#  - Opciones de tienda/eventos: hasta 128 px (Sí/No: 48 px).
#  - Menú de sistema y configuración: el mismo nº de celdas que el inglés.
#  - Las filas con " / " (dificultad, velocidad del texto) llevan una palabra
#    en cada hueco de 32 px: mantén el mismo número de partes.
# ====================================================================================

"""


def write_menus(path):
    from menus import all_english
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(HEADER_MENUS)
        for i, t in enumerate(all_english()):
            f.write(f"{i:02d} | {t} | {t}\n")


def write_nombres(path, names_full):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(HEADER_NOMBRES)
        for i, n in enumerate(names_full):
            if n is None:
                f.write(f"{i:03d} | (vacío) | (vacío)\n")
            else:
                f.write(f"{i:03d} | {n} | {n}\n")


def main():
    force = "--forzar" in sys.argv
    rom = load_en_rom()
    os.makedirs(OUT, exist_ok=True)

    # 1. Diálogos
    msgs = read_messages(rom)
    write_dialogos(os.path.join(OUT, "dialogos_en.txt"), msgs, False)
    print(f"Diálogos: {len(msgs)} mensajes")

    # 2. Nombres (texto completo recuperado de los gráficos)
    strings = read_name_strings(rom)
    lists = read_tile_lists(rom)
    full = []
    for i, (s, l) in enumerate(zip(strings, lists)):
        if not l or l[0] < 0x300:
            full.append(None)
            continue
        cells = [read_cell16(rom, cell_offset(x)) for x in l]
        t = ocr_name(rom, s, cells, spacing_for(i))
        full.append(t.decode("latin1"))
    write_nombres(os.path.join(OUT, "nombres_en.txt"), full)
    print(f"Nombres: {sum(1 for x in full if x)} (+{full.count(None)} vacíos)")

    # 3. Nombres de personajes
    chars = read_default_names(rom)
    with open(os.path.join(OUT, "personajes_en.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write(HEADER_PERSONAJES)
        for k, n in enumerate(chars):
            f.write(f"{k + 1} | {n} | {n}\n")
    print("Personajes:", ", ".join(chars))

    # 4. Gráficos (en una copia con los glifos españoles ya añadidos)
    g = bytearray(rom)
    graficos.make_spanish_glyphs16(g)
    graficos.make_spanish_glyphs8(g)
    gdir = os.path.join(OUT, "graficos")
    os.makedirs(gdir, exist_ok=True)
    graficos.cells16_to_png(g, 0x18C000, 512, os.path.join(gdir, "celdas_31_fuente_y_menus.png"))
    graficos.cells16_to_png(g, 0x1BC000, 512, os.path.join(gdir, "celdas_37_nombres.png"))
    graficos.cells16_to_png(g, 0x1C4000, 512, os.path.join(gdir, "celdas_38_titulos_teclado.png"))
    graficos.font8_to_png(g, os.path.join(gdir, "fuente8x8.png"))
    with open(os.path.join(gdir, "anchos_fuente.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write("# Ancho en píxeles de cada carácter de la fuente VWF 16x16\n")
        f.write("# código | carácter | ancho\n")
        for c in range(0x20, 0x90):
            ch = SPANISH_REV.get(c) or (chr(c) if c < 0x7F else f"{{{c:02X}}}")
            f.write(f"{c:02X} | {ch} | {g[WIDTHS + c]}\n")
    t21 = decompress(rom, bank_table(rom, 0x25)[21])[0]
    graficos.tiles4_to_png(t21, os.path.join(gdir, "titulo_4bpp.png"))
    print("Gráficos exportados en", gdir)

    # 5. Binarios de referencia
    bdir = os.path.join(OUT, "bin")
    os.makedirs(bdir, exist_ok=True)
    open(os.path.join(bdir, "titulo_mapa_b25_04.bin"), "wb").write(
        decompress(rom, bank_table(rom, 0x25)[4])[0])
    open(os.path.join(bdir, "titulo_tiles_b25_21.bin"), "wb").write(t21)

    write_menus(os.path.join(OUT, "menus_en.txt"))

    # 6. Copia de trabajo
    if os.path.exists(WORK) and not force:
        if not os.path.exists(os.path.join(WORK, "menus.txt")):
            shutil.copy(os.path.join(OUT, "menus_en.txt"), os.path.join(WORK, "menus.txt"))
            print("Añadido traduccion/menus.txt")
        # En el repositorio no se incluyen ni el texto inglés ni los gráficos del juego:
        # se generan aquí desde la ROM del usuario.
        if not os.path.exists(os.path.join(WORK, "dialogos.txt")):
            write_dialogos(os.path.join(WORK, "dialogos.txt"), msgs, True)
            print("Añadido traduccion/dialogos.txt (en inglés; se traduce con los lotes)")
        if not os.path.exists(os.path.join(WORK, "graficos")):
            shutil.copytree(gdir, os.path.join(WORK, "graficos"))
            print("Añadido traduccion/graficos")
        print(f"\n'{WORK}' ya existe: no se toca (usa --forzar para regenerarla).")
        return
    if os.path.exists(WORK):
        shutil.rmtree(WORK)
    os.makedirs(WORK)
    write_dialogos(os.path.join(WORK, "dialogos.txt"), msgs, True)
    write_nombres(os.path.join(WORK, "nombres.txt"), full)
    shutil.copy(os.path.join(OUT, "personajes_en.txt"), os.path.join(WORK, "personajes.txt"))
    shutil.copy(os.path.join(OUT, "menus_en.txt"), os.path.join(WORK, "menus.txt"))
    shutil.copytree(gdir, os.path.join(WORK, "graficos"))
    print(f"Copia de trabajo creada en '{WORK}'.")


if __name__ == "__main__":
    main()
