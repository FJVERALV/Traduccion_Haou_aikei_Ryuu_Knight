"""Textos de menú pre-renderizados (celdas 0x400-0x4F2 del parche inglés).

Hay dos tipos de referencias a esas celdas:

1. Elecciones dentro de los eventos (bancos $14-$16, LZSS). Formato:
       FF 0A  [W palabras de celda]  FE etiqueta  [W palabras]  FE etiqueta ... FF
   Cada opción ocupa W palabras (8 en tiendas, 3 en Sí/No), rellenas con 0000.
2. Tablas fijas sin comprimir (menú de sistema, configuración, teclado, avisos).
   Ahí cada texto debe ocupar exactamente el mismo número de celdas.

insertar.py redibuja cada texto en español con la fuente del juego, lo guarda en
celdas nuevas (0xB00-0xCFF, banco $3A) y reescribe todas las referencias.
"""
from rk_common import (render_vwf, split_cells, encode_message, glyph_left,
                       write_cell16, cell_offset, set_dlg_width)
from lzss import decompress, bank_table

MENU_CELL_FIRST = 0xB00
MENU_CELL_LAST = 0xCFF

# Estilos de dibujo (comprobados píxel a píxel contra el parche inglés):
#   "eleccion": x = 0, espaciado normal
#   "sistema":  primera columna con tinta en x = sangría, letra 1 px más junta
EVENT_STYLE = ("eleccion", 0)

CHOICE_SEQS = {
    (1024, 1025, 1026, 1027, 1028): "Of course!",
    (1029, 1030, 1031): "Alas...",
    (1032, 1033, 1034, 1035, 1036, 1037, 1038): "I won't give up!",
    (1039, 1040, 1041, 1042, 1043): "I give up...",
    (1044, 1045): "Yes",
    (1046, 1047): "No",
    (1048, 1049, 1050, 1051, 1052): "Buy items!",
    (1053, 1054, 1050, 1051, 1052): "Sell items!",
    (1055, 1056, 1057, 1058, 1059, 1060, 1061): "Leave the shop!",
    (1048, 1049, 1062, 1063, 1064): "Buy herbs!",
    (1053, 1054, 1062, 1063, 1064): "Sell herbs!",
    (1048, 1065, 1066, 1067, 1068): "Buy armor!",
    (1069, 1070, 1071, 1072, 1073, 1074, 1075): "Repair armor!",
    (1048, 1049, 1076, 1077, 1078, 1079): "Buy weapons!",
    (1080, 1081, 1082, 1083, 1084, 1085, 1086, 1087): "Temper weapons!",
    (1088, 1089, 1090, 1091, 1092, 1093, 1094, 1095): "Banbara Trouble",
    (1096, 1097, 1098, 1099, 1100, 1101, 1102): "Tavern waiter",
    (1103, 1104, 1105, 1106, 1107, 1108): "Delivery boy",
    (1109, 1110, 1111, 1112, 1113, 1114): "Powan Herb",
    (1115, 1116, 1117, 1118, 1119, 1120): "Soesoe Herb",
    (1121, 1122, 1123, 1124, 1125, 1126): "Tomioka Seed",
    (1127, 1128, 1129, 1130, 1131, 1132): "Go on ahead!",
    (1133, 1134, 1135, 1136, 1137, 1138, 1139, 1140): "Train some more",
    (1141, 1142, 1143, 1144, 1075): "Do herbs!",
    (1141, 1145, 1146, 1147, 1148, 1149): "Do it anyway!",
    (1150, 1151, 1152, 1126, 1153, 1154, 1155, 1156): "Changed my mind!",
    (1157, 1091, 1158, 1159, 1160): "Pirani Beer",
    (1157, 1091, 1158, 1161, 1162, 1163, 1164): "Pirani Cocktail",
    (1157, 1091, 1158, 1165, 1166): "Pirani Sake",
}

# (dirección, nº de celdas, texto inglés, estilo, sangría o posiciones de cada palabra)
FIXED = [
    (0x9174, 2, "Yes", "sistema", 0),
    (0x91F3, 4, ", please.", "eleccion", 0),
    (0xAB9A, 5, " obtained.", "eleccion", 0),
    (0xABAA, 5, " was lost.", "eleccion", 0),
    (0x1A8A4, 2, "OFF", "sistema", 0),
    (0x1A8AA, 2, "ON", "sistema", 0),
    (0x1B23E2, 14, "You can't carry any more items.", "eleccion", 0),
    (0x11F3B0, 3, "System", "sistema", 0),
    (0x11F3B8, 4, "Status", "sistema", 8),
    (0x11F3C2, 5, "World Map", "sistema", 8),
    (0x11F3CE, 3, "Config", "sistema", 0),
    (0x11F3D6, 2, "Save", "sistema", 0),
    (0x11F3DC, 2, "Load", "sistema", 0),
    (0x11F3E2, 2, "Exit", "sistema", 8),
    (0x11F3EC, 4, "Rename", "sistema", 8),
    (0x11F448, 2, "Load", "sistema", 0),
    (0x11F492, 2, "Save", "sistema", 0),
    (0x11F4DC, 3, "Summon", "sistema", 0),
    (0x11F4E2, 2, "ON", "sistema", 0),
    (0x11F4E8, 2, "OFF", "sistema", 0),
    (0x11F4EE, 2, "Diff.", "sistema", 0),
    (0x11F4F4, 9, "Easy / Norm / Hard / Assist", "sistema", [0, 32, 64, 96]),
    (0x11F516, 3, "Text", "sistema", 8),
    (0x11F51E, 9, "Slow / Mid / Fast / Sound", "sistema", [0, 32, 64, 104]),
    (0x11F532, 3, "Stereo", "sistema", 0),
    (0x11F53A, 2, "Mono", "sistema", 0),
    (0x11F552, 2, "ABC", "sistema", 0),
    (0x11F55A, 2, "abc", "sistema", 0),
    (0x11F562, 3, "Symbols", "sistema", 0),
    (0x11F572, 2, "Wpn.", "sistema", 0),
    (0x11F578, 2, "Arm.", "sistema", 0),
    (0x11F57E, 2, "Item", "sistema", 0),
    (0x11F584, 2, "Arm.", "sistema", 0),
]

# Zonas en las que se puede poner una palabra de una fila (desde su posición
# hasta la siguiente)
ROW_LIMIT_GAP = 0


def all_english():
    """Lista ordenada (sin repetir) de textos ingleses de menú."""
    seen = []
    for t in list(CHOICE_SEQS.values()) + [f[2] for f in FIXED]:
        if t not in seen:
            seen.append(t)
    return seen


# --- dibujo ----------------------------------------------------------------------------
def _render_word(rom, text, style, x):
    data = encode_message(text, "menus.txt")
    if style == "sistema":
        return render_vwf(data, rom, start_x=x - glyph_left(rom, data[0]) if data else x, spacing=-1)
    return render_vwf(data, rom, start_x=x, spacing=0)


def render_menu(rom, text, style, pos, ncells):
    """Devuelve (celdas, avisos). pos = sangría (int) o lista de posiciones."""
    warns = []
    if isinstance(pos, list):
        words = [w.strip() for w in text.split("/")]
        if len(words) != len(pos):
            raise ValueError(f"'{text}': hacen falta {len(pos)} partes separadas por /")
        rows = [0] * 16
        for k, (w, x) in enumerate(zip(words, pos)):
            r, _ = _render_word(rom, w, style, x)
            limit = pos[k + 1] - 1 if k + 1 < len(pos) else ncells * 16
            end = ink_right(r)
            if end > limit:
                warns.append(f"'{w}' es demasiado largo ({end - x} px, caben {limit - x})")
            rows = [a | b for a, b in zip(rows, r)]
        width = ncells * 16
    else:
        rows, width = _render_word(rom, text, style, pos)
    cells = split_cells(rows, width)
    if ncells is not None and len(cells) > ncells:
        # sobra sólo el espacio final de la última letra: se recorta sin aviso
        if ink_right(rows) > ncells * 16:
            warns.append(f"'{text}' mide {ink_right(rows)} px y caben {ncells * 16}")
        cells = cells[:ncells]
    return cells, warns


def ink_right_cells(cells):
    """Columna (exclusiva) donde acaba la tinta en una lista de celdas."""
    end = 0
    for k, c in enumerate(cells):
        cols = 0
        for r in c:
            cols |= r
        if cols:
            end = 16 * k + 16 - ((cols & -cols).bit_length() - 1)
    return end


def ink_right(rows):
    """Columna (exclusiva) donde acaba la tinta en un lienzo de render_vwf."""
    from rk_common import CANVAS
    allr = 0
    for r in rows:
        allr |= r
    if not allr:
        return 0
    return CANVAS - (allr & -allr).bit_length() + 1


# --- inserción ---------------------------------------------------------------------------
class CellAllocator:
    def __init__(self, rom):
        self.rom = rom
        self.ids = {}
        self.width = {}
        self.free = iter([x for x in range(MENU_CELL_FIRST, MENU_CELL_LAST + 1) if x & 0xFF != 0xFF])

    def get(self, cell, width=16):
        key = tuple(cell)
        if key not in self.ids:
            new = next(self.free, None)
            if new is None:
                raise SystemExit("No quedan celdas libres para los menús.")
            self.ids[key] = new
            self.width[new] = 0
            write_cell16(self.rom, cell_offset(new), cell)
        cid = self.ids[key]
        if width > self.width[cid]:
            self.width[cid] = width
            set_dlg_width(self.rom, cid, width)      # ancho en el motor de diálogo
        return cid


def iter_choices(d):
    """Localiza las elecciones de un bloque de eventos descomprimido.
    Devuelve [(offset_opción, W)]."""
    out = []
    for i in range(1, len(d) - 3):
        if d[i] == 0x0A and d[i - 1] == 0xFF and 0x400 <= (d[i + 1] | d[i + 2] << 8) <= 0x4F2:
            p = i + 1
            while d[p] != 0xFF:
                start = p
                while d[p] != 0xFE:
                    p += 2
                out.append((start, (p - start) // 2))
                p += 2
    return out


def insert_menus(rom, translations, write_block, warn):
    """translations: dict inglés -> español."""
    alloc = CellAllocator(rom)
    blank = alloc.get([0] * 16, 16)
    cache = {}

    def cells_for(eng, style, pos, ncells):
        key = (eng, style, str(pos), ncells)
        if key not in cache:
            es = translations.get(eng.strip()) or eng
            if eng.startswith(" ") and not es.startswith(" "):
                es = " " + es        # se añade detrás del nombre del objeto
            cells, w = render_menu(rom, es, style, pos, ncells)
            for m in w:
                warn(f"menus.txt: {m}")
            # en el inglés todas las celdas de menú tienen ancho 16 en el diálogo
            cache[key] = [alloc.get(c, 16) for c in cells]
        return cache[key]

    # 1. tablas fijas
    for addr, n, eng, style, pos in FIXED:
        ids = cells_for(eng, style, pos, n)
        ids = ids + [blank] * (n - len(ids))
        for k, x in enumerate(ids):
            rom[addr + 2 * k:addr + 2 * k + 2] = x.to_bytes(2, "little")

    # 2. elecciones de los eventos
    changed_blocks = 0
    for bank in (0x14, 0x15, 0x16):
        for k, off in enumerate(bank_table(rom, bank)):
            d = bytearray(decompress(rom, off)[0])
            orig = bytes(d)
            for start, W in iter_choices(d):
                words = [d[start + 2 * j] | d[start + 2 * j + 1] << 8 for j in range(W)]
                seq = tuple(w for w in words if w)
                eng = CHOICE_SEQS.get(seq)
                if eng is None:
                    warn(f"elección desconocida en {bank:02X}#{k}: {[hex(x) for x in seq]}")
                    continue
                ids = cells_for(eng, *EVENT_STYLE, W)
                ids = ids + [0] * (W - len(ids))
                for j, x in enumerate(ids):
                    d[start + 2 * j:start + 2 * j + 2] = x.to_bytes(2, "little")
            if bytes(d) != orig:
                write_block(rom, bank, k, bytes(d))
                changed_blocks += 1
    print(f"Menús: {len(alloc.ids)} celdas nuevas, {changed_blocks} bloques de eventos recomprimidos")
