"""Conversión entre gráficos de la ROM y PNG editables, y glifos españoles."""
from PIL import Image

from rk_common import read_cell16, write_cell16, SPANISH, FONT16, WIDTHS, FONT8

PAL_1BPP = [0, 0, 0, 255, 255, 255]


# --- celdas 16x16 1bpp ---------------------------------------------------------------
def cells16_to_png(rom, off, count, path, cols=32):
    rows_n = (count + cols - 1) // cols
    img = Image.new("P", (cols * 16, rows_n * 16), 0)
    img.putpalette(PAL_1BPP)
    px = img.load()
    for k in range(count):
        rows = read_cell16(rom, off + k * 32)
        ox, oy = (k % cols) * 16, (k // cols) * 16
        for y, r in enumerate(rows):
            for x in range(16):
                if r >> (15 - x) & 1:
                    px[ox + x, oy + y] = 1
    img.save(path)


def png_to_cells16(rom, off, count, path, cols=32):
    img = Image.open(path).convert("L")
    px = img.load()
    for k in range(count):
        ox, oy = (k % cols) * 16, (k // cols) * 16
        rows = []
        for y in range(16):
            r = 0
            for x in range(16):
                if px[ox + x, oy + y] >= 128:
                    r |= 1 << (15 - x)
            rows.append(r)
        write_cell16(rom, off + k * 32, rows)


# --- fuente 8x8 1bpp (caracteres 0x20-0x7F) -----------------------------------------------
def font8_to_png(rom, path):
    img = Image.new("P", (16 * 8, 6 * 8), 0)
    img.putpalette(PAL_1BPP)
    px = img.load()
    for k in range(96):
        o = FONT8 + (0x20 + k) * 8
        for y in range(8):
            for x in range(8):
                if rom[o + y] >> (7 - x) & 1:
                    px[(k % 16) * 8 + x, (k // 16) * 8 + y] = 1
    img.save(path)


def png_to_font8(rom, path):
    px = Image.open(path).convert("L").load()
    for k in range(96):
        o = FONT8 + (0x20 + k) * 8
        for y in range(8):
            b = 0
            for x in range(8):
                if px[(k % 16) * 8 + x, (k // 16) * 8 + y] >= 128:
                    b |= 0x80 >> x
            rom[o + y] = b


# --- tiles 4bpp SNES ------------------------------------------------------------------------
GRAY16 = sum(([v * 17, v * 17, v * 17] for v in range(16)), [])


def tiles4_to_png(data, path, cols=16):
    n = len(data) // 32
    img = Image.new("P", (cols * 8, ((n + cols - 1) // cols) * 8), 0)
    img.putpalette(GRAY16)
    px = img.load()
    for t in range(n):
        for y in range(8):
            p = [data[t * 32 + y * 2], data[t * 32 + y * 2 + 1],
                 data[t * 32 + 16 + y * 2], data[t * 32 + 16 + y * 2 + 1]]
            for x in range(8):
                v = sum(((p[i] >> (7 - x)) & 1) << i for i in range(4))
                px[(t % cols) * 8 + x, (t // cols) * 8 + y] = v
    img.save(path)


def png_to_tiles4(path, n, cols=16):
    img = Image.open(path)
    if img.mode != "P":
        raise ValueError(f"{path} debe ser PNG indexado (16 colores)")
    px = img.load()
    out = bytearray(n * 32)
    for t in range(n):
        for y in range(8):
            p = [0, 0, 0, 0]
            for x in range(8):
                v = px[(t % cols) * 8 + x, (t // cols) * 8 + y] & 15
                for i in range(4):
                    p[i] |= ((v >> i) & 1) << (7 - x)
            out[t * 32 + y * 2], out[t * 32 + y * 2 + 1] = p[0], p[1]
            out[t * 32 + 16 + y * 2], out[t * 32 + 16 + y * 2 + 1] = p[2], p[3]
    return bytes(out)


# --- generación de glifos españoles ----------------------------------------------------------
def _bbox(rows):
    cols = 0
    for r in rows:
        cols |= r
    xs = [x for x in range(16) if cols >> (15 - x) & 1]
    ys = [y for y, r in enumerate(rows) if r]
    return xs[0], xs[-1], ys[0], ys[-1]


def _set(rows, x, y):
    if 0 <= x < 16 and 0 <= y < 16:
        rows[y] |= 1 << (15 - x)


def _acute(rows, cx, y0):
    for dx, dy in ((1, 0), (2, 0), (0, 1), (1, 1)):
        _set(rows, cx + dx, y0 + dy)


def _tilde(rows, x0, x1, y0):
    w = x1 - x0 + 1
    pts = [(0, 1), (1, 0), (2, 0), (3, 1), (4, 1), (5, 0)]
    off = x0 + max(0, (w - 7) // 2)
    for dx, dy in pts:
        _set(rows, off + dx, y0 + dy)
        _set(rows, off + dx + 1, y0 + dy)


def _diaeresis(rows, x0, x1, y0):
    for x in (x0, x1 - 1):
        _set(rows, x, y0); _set(rows, x + 1, y0)


def _flip(rows, x0, x1, y0, y1):
    """Gira 180° la caja (x0..x1, y0..y1) del glifo (para ¿ y ¡)."""
    out = list(rows)
    for y in range(y0, y1 + 1):
        out[y] = 0
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            if rows[y] >> (15 - x) & 1:
                _set(out, x0 + x1 - x, y0 + y1 - y)
    return out


def make_spanish_glyphs16(rom):
    """Dibuja los glifos españoles en los huecos libres de la fuente 16x16."""
    widths = rom[WIDTHS:WIDTHS + 0x100]
    base = {"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ü": "u", "ñ": "n",
            "Á": "A", "É": "E", "Í": "I", "Ó": "O", "Ñ": "N", "¿": "?", "¡": "!"}
    for ch, b in base.items():
        src = read_cell16(rom, FONT16 + ord(b) * 32)
        rows = list(src)
        x0, x1, y0, y1 = _bbox(rows)
        cx = (x0 + x1) // 2
        if ch in "¿¡":
            rows = _flip(rows, x0, x1, y0, min(15, y1 + 2))   # baja bajo la línea
        elif ch == "í":
            rows[y0] = 0                      # quita el punto de la i
            _acute(rows, x0, y0 - 1)
        elif ch.islower():
            if ch == "ñ":
                _tilde(rows, x0, x1, y0 - 3)
            elif ch == "ü":
                _diaeresis(rows, x0, x1, y0 - 2)
            else:
                _acute(rows, cx - 1, y0 - 3)
        else:                                 # mayúsculas: acento encima (filas 1-2)
            if ch == "Ñ":
                _tilde(rows, x0, x1, y0 - 3)
            else:
                _acute(rows, cx - 1, y0 - 3)
        code = SPANISH[ch]
        write_cell16(rom, FONT16 + code * 32, rows)
        rom[WIDTHS + code] = widths[ord(b)]


BASE_ES = {"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ü": "u", "ñ": "n",
           "Á": "A", "É": "E", "Í": "I", "Ó": "O", "Ñ": "N", "¿": "?", "¡": "!"}


def make_spanish_glyphs8(rom):
    """Glifos españoles para la fuente 8x8 de los DIÁLOGOS (0x184200).

    Minúsculas: altura x en filas 3-7 -> el acento va en las filas 1-2.
    Mayúsculas: filas 1-7 -> el acento va en la fila 0.
    """
    for ch, b in BASE_ES.items():
        src = list(rom[FONT8 + ord(b) * 8:FONT8 + ord(b) * 8 + 8])
        cols = 0
        for r in src:
            cols |= r
        xs = [x for x in range(8) if cols >> (7 - x) & 1]
        x0, x1 = xs[0], xs[-1]
        cx = (x0 + x1) // 2
        bit = lambda x: (0x80 >> x) if 0 <= x < 8 else 0          # noqa: E731
        rows = list(src)
        if ch in "¿¡":
            # giro de 180° dentro de la caja del glifo
            rows = [0] * 8
            for y in range(8):
                for x in range(x0, x1 + 1):
                    if src[y] & bit(x):
                        rows[7 - y] |= bit(x0 + x1 - x)
            if ch == "¡":
                # que no parezca una "i": punto arriba y palo hasta abajo
                rows = [rows[1], 0] + [rows[3]] * 6
        elif ch == "ñ":
            rows[1] = bit(x0 + 1) | bit(x0 + 2) | bit(x0 + 4)
            rows[2] = bit(x0) | bit(x0 + 3)
        elif ch == "ü":
            rows[1] = bit(x0) | bit(x0 + 1) | bit(x1 - 1) | bit(x1)
        elif ch == "í":
            rows[0] = 0
            rows[1] = bit(x0 + 1) | bit(x0 + 2)
            rows[2] = bit(x0)
        elif ch.islower():
            rows[1] = bit(cx + 1) | bit(cx + 2)
            rows[2] = bit(cx) | bit(cx + 1)
        else:
            # mayúsculas (filas 1-7): se quita una fila repetida para dejar
            # un hueco entre el acento y la letra
            body = src[1:]
            for k in range(1, len(body)):
                if body[k] == body[k - 1]:
                    del body[k]
                    break
            else:
                del body[len(body) // 2]
            rows = [0, 0] + body
            if ch == "Ñ":
                rows[0] = bit(x0 + 1) | bit(x0 + 2) | bit(x0 + 4) | bit(x0 + 5)
            else:
                rows[0] = bit(cx + 1) | bit(cx + 2)
        rom[FONT8 + SPANISH[ch] * 8:FONT8 + SPANISH[ch] * 8 + 8] = bytes(rows)
    set_spanish_widths8(rom)


def set_spanish_widths8(rom):
    """Anchos de la fuente de diálogos (tabla $30:C100 = 0x184100) para las letras
    españolas: los mismos que su letra base."""
    from rk_common import WIDTHS8
    for ch, b in BASE_ES.items():
        rom[WIDTHS8 + SPANISH[ch]] = rom[WIDTHS8 + ord(b)]
