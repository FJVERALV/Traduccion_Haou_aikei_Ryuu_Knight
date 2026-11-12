"""Textos de la pantalla de título ("OPENING START" / "LOAD START").

Están en el banco $25: bloque 21 = tiles 4bpp (tile 0 del bloque = tile 0x80 en VRAM)
y bloque 4 = mapa de tiles (64 filas x 32). Ambos textos van en la fila 54 del mapa.

Estilo copiado del parche inglés: letras de 7 px de alto con degradado vertical
(colores 7 -> 1) y sombra de color 8 desplazada 1 px abajo a la derecha.
"""
from lzss import decompress, bank_table, compress

ROW = 54
PAL_BITS = 0x1000              # paleta 4, como el original
CENTERS = (72, 184)            # centro (px) de cada texto en el original
# 0xC0-0xCB y 0xD0-0xD4 eran los textos ingleses; 0xCC-0xCF son de "© BANDAI 1994"
FREE_TILES = list(range(0xC0, 0xCC)) + list(range(0xD0, 0xD5)) + list(range(0xE0, 0x100))

FONT = {
    "A": ["...####", "..##.##", "..##.##", ".##..##", ".##..##", "#######", "##...##"],
    "C": [".#####.", "##...##", "##.....", "##.....", "##.....", "##...##", ".#####."],
    "D": ["######.", "##...##", "##...##", "##...##", "##...##", "##...##", "######."],
    "E": ["######", "##....", "##....", "#####.", "##....", "##....", "######"],
    "G": [".#####.", "##...##", "##.....", "##..###", "##...##", "##...##", ".#####."],
    "I": ["##", "##", "##", "##", "##", "##", "##"],
    "L": ["##....", "##....", "##....", "##....", "##....", "##....", "######"],
    "M": ["##...##", "###.###", "#######", "##.#.##", "##...##", "##...##", "##...##"],
    "N": ["##...##", "###..##", "###..##", "##.#.##", "##..###", "##..###", "##...##"],
    "O": [".#####.", "##...##", "##...##", "##...##", "##...##", "##...##", ".#####."],
    "P": ["######.", "##...##", "##...##", "######.", "##.....", "##.....", "##....."],
    "R": ["######.", "##...##", "##...##", "######.", "##.##..", "##..##.", "##...##"],
    "S": [".#####.", "##...##", "##.....", ".#####.", ".....##", "##...##", ".#####."],
    "T": ["######", "..##..", "..##..", "..##..", "..##..", "..##..", "..##.."],
    "U": ["##...##", "##...##", "##...##", "##...##", "##...##", "##...##", ".#####."],
    "V": ["##...##", "##...##", "##...##", ".##.##.", ".##.##.", "..###..", "...#..."],
    "Z": ["#######", ".....##", "....##.", "...##..", "..##...", ".##....", "#######"],
    "B": ["######.", "##...##", "##...##", "######.", "##...##", "##...##", "######."],
    "J": ["....##", "....##", "....##", "....##", "....##", "##..##", ".####."],
}
SPACE = 5


def render(text):
    """Devuelve una matriz 8 x ancho de índices de color."""
    text = text.upper()
    for ch in text:
        if ch != " " and ch not in FONT:
            raise ValueError(f"titulo.txt: la letra '{ch}' no está en la fuente del título")
    width = sum(SPACE if c == " " else len(FONT[c][0]) + 1 for c in text) + 1
    pix = [[0] * width for _ in range(8)]
    x = 0
    for ch in text:
        if ch == " ":
            x += SPACE
            continue
        g = FONT[ch]
        for y, row in enumerate(g):
            for dx, c in enumerate(row):
                if c == "#":
                    if pix[y + 1][x + dx + 1] == 0:
                        pix[y + 1][x + dx + 1] = 8       # sombra
        for y, row in enumerate(g):
            for dx, c in enumerate(row):
                if c == "#":
                    pix[y][x + dx] = 7 - y               # degradado
        x += len(g[0]) + 1
    return pix


def _tile_bytes(pix, x0):
    out = bytearray(32)
    for y in range(8):
        p = [0, 0, 0, 0]
        for x in range(8):
            xx = x0 + x
            v = pix[y][xx] if 0 <= xx < len(pix[0]) else 0
            for i in range(4):
                p[i] |= ((v >> i) & 1) << (7 - x)
        out[y * 2], out[y * 2 + 1], out[16 + y * 2], out[16 + y * 2 + 1] = p
    return bytes(out)


# --- crédito (sustituye a "https://gametranslate.us", fila 58) ---------------------------
CREDIT_ROW = 58
CREDIT_COLS = range(17, 31)            # tiles 0x9D-0xAA del original
CREDIT_END_X = 30 * 8 + 2              # donde acababa la URL
DESC_TILES = (0xAB, 0xAC)              # tiles de la fila 59 (bajadas de p, g)
# Letra pequeña del copyright: filas 1-7 (mayúsculas), 3-7 (minúsculas), 8-9 bajadas
SMALL = {
    "T": ["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."],
    "F": ["####", "#...", "#...", "###.", "#...", "#...", "#..."],
    "V": ["#...#", "#...#", "#...#", ".#.#.", ".#.#.", "..#..", "..#.."],
    "E": ["####", "#...", "#...", "###.", "#...", "#...", "####"],
    "R": ["###.", "#..#", "#..#", "###.", "#.#.", "#..#", "#..#"],
    "A": [".##.", "#..#", "#..#", "####", "#..#", "#..#", "#..#"],
    "L": ["#...", "#...", "#...", "#...", "#...", "#...", "####"],
    "r": ["", "", "#.##", "##..", "#...", "#...", "#..."],
    "a": ["", "", ".##.", "...#", ".###", "#..#", ".###"],
    "d": ["...#", "...#", ".###", "#..#", "#..#", "#..#", ".###"],
    "u": ["", "", "#..#", "#..#", "#..#", "#..#", ".###"],
    "c": ["", "", ".###", "#...", "#...", "#...", ".###"],
    "i": ["#", "", "#", "#", "#", "#", "#"],
    "o": ["", "", ".##.", "#..#", "#..#", "#..#", ".##."],
    "p": ["", "", "###.", "#..#", "#..#", "#..#", "###.", "#...", "#..."],
}
SMALL_COLORS = [0, 15, 15, 15, 15, 14, 14, 13, 13, 12]      # por fila (y)


def render_small(text):
    width = sum(3 if c == " " else len(max(SMALL[c], key=len)) + 1 for c in text)
    pix = [[0] * width for _ in range(16)]
    x = 0
    for ch in text:
        if ch == " ":
            x += 3
            continue
        if ch not in SMALL:
            raise ValueError(f"titulo.txt: la letra '{ch}' no está en la letra del crédito")
        g = SMALL[ch]
        w = len(max(g, key=len))
        for y, row in enumerate(g):
            for dx, c in enumerate(row):
                if c == "#":
                    pix[y + 1][x + dx] = SMALL_COLORS[y + 1]
        x += w + 1
    return pix


def put_credit(tiles, tmap, text):
    pix = render_small(text)
    w = len(pix[0]) - 1
    start = CREDIT_END_X - w
    if start < CREDIT_COLS[0] * 8:
        raise SystemExit(f"titulo.txt: el crédito '{text}' es demasiado largo ({w} px)")
    nums = iter(range(0x9D, 0xAB))
    desc = iter(DESC_TILES)
    for col in CREDIT_COLS:
        for row, pool in ((CREDIT_ROW, nums), (CREDIT_ROW + 1, desc)):
            sub = pix[(row - CREDIT_ROW) * 8:(row - CREDIT_ROW) * 8 + 8]
            data = _tile_bytes(sub, col * 8 - start)
            k = (row * 32 + col) * 2
            old = tmap[k] | tmap[k + 1] << 8
            if row == CREDIT_ROW + 1 and old & 0x3FF not in DESC_TILES:
                old = 0
            if not any(data):
                if row == CREDIT_ROW or old:
                    tmap[k:k + 2] = bytes(2)
                continue
            n = next(pool, None)
            if n is None:
                raise SystemExit("titulo.txt: el crédito necesita demasiados tiles")
            tiles[(n - 0x80) * 32:(n - 0x80) * 32 + 32] = data
            tmap[k:k + 2] = (PAL_BITS | n).to_bytes(2, "little")
    for n in list(nums) + list(desc):          # tiles sobrantes, en blanco
        tiles[(n - 0x80) * 32:(n - 0x80) * 32 + 32] = bytes(32)


def repack_bank(rom, bank, new_raw):
    """Recomprime todos los bloques del banco y los coloca seguidos (el compresor
    propio es óptimo y gana algo de espacio). new_raw: {índice: datos nuevos}."""
    table = bank_table(rom, bank)
    first = min(table)
    limit = max(decompress(rom, b)[1] for b in table)
    raws = [new_raw.get(i, decompress(rom, b)[0]) for i, b in enumerate(table)]
    pos = first
    out = bytearray()
    for i, raw in enumerate(raws):
        data = compress(raw)
        rom[bank * 0x8000 + 2 * i:bank * 0x8000 + 2 * i + 2] = (pos % 0x8000 | 0x8000).to_bytes(2, "little")
        out += data
        pos += len(data)
    if pos > limit:
        raise SystemExit(f"Banco {bank:02X}: no cabe ({pos - limit} bytes de más)")
    rom[first:pos] = out
    rom[pos:limit] = bytes([0xFF]) * (limit - pos)


# --- subtítulo del logo (ロード オブ パラディン) ------------------------------------------
# Banco $25, bloque 24: tiles 0-15 = mitad de arriba y 16-31 = mitad de abajo de una
# franja de 128 x 16 px. Letra de 11 px de alto (filas 3-13), trazo de 2 px, degradado
# vertical (color 16 - fila) y contorno de color 1, como el katakana original.
SUB_BLOCK = 24
SUB_W = 128
SUB_TOP = 3
SUB_FONT = {
    "S": [".####.", "##..##", "##....", "##....", "###...", ".####.", "...###", "....##", "....##", "##..##", ".####."],
    "E": ["######", "##....", "##....", "##....", "#####.", "##....", "##....", "##....", "##....", "##....", "######"],
    "N": ["##..##", "###.##", "###.##", "######", "##.###", "##.###", "##..##", "##..##", "##..##", "##..##", "##..##"],
    "O": [".####.", "##..##", "##..##", "##..##", "##..##", "##..##", "##..##", "##..##", "##..##", "##..##", ".####."],
    "R": ["#####.", "##..##", "##..##", "##..##", "#####.", "####..", "##.##.", "##.##.", "##..##", "##..##", "##..##"],
    "D": ["#####.", "##..##", "##..##", "##..##", "##..##", "##..##", "##..##", "##..##", "##..##", "##..##", "#####."],
    "P": ["#####.", "##..##", "##..##", "##..##", "##..##", "#####.", "##....", "##....", "##....", "##....", "##...."],
    "A": [".####.", "##..##", "##..##", "##..##", "######", "##..##", "##..##", "##..##", "##..##", "##..##", "##..##"],
    "L": ["##....", "##....", "##....", "##....", "##....", "##....", "##....", "##....", "##....", "##....", "######"],
    "I": ["##"] * 11,
    "T": ["######", "..##..", "..##..", "..##..", "..##..", "..##..", "..##..", "..##..", "..##..", "..##..", "..##.."],
    "C": [".####.", "##..##", "##....", "##....", "##....", "##....", "##....", "##....", "##....", "##..##", ".####."],
    "G": [".####.", "##..##", "##....", "##....", "##....", "##.###", "##..##", "##..##", "##..##", "##..##", ".####."],
    "U": ["##..##"] * 10 + [".####."],
    "Y": ["##..##", "##..##", "##..##", "##..##", ".####.", "..##..", "..##..", "..##..", "..##..", "..##..", "..##.."],
}
SUB_TILDE = [".##..#", "#..##."]          # para Ñ, en las filas 0-1
SUB_SPACE = 4


def render_subtitle(text):
    text = text.upper()
    glyphs = []
    for ch in text:
        if ch == " ":
            glyphs.append(None)
        elif ch == "Ñ":
            glyphs.append((SUB_FONT["N"], True))
        elif ch in SUB_FONT:
            glyphs.append((SUB_FONT[ch], False))
        else:
            raise ValueError(f"titulo.txt: la letra '{ch}' no está en la letra del subtítulo")
    width = sum(SUB_SPACE if g is None else len(g[0][0]) + 1 for g in glyphs) + 1
    if width > SUB_W:
        raise SystemExit(f"titulo.txt: el subtítulo '{text}' mide {width} px y caben {SUB_W}")
    ink = [[False] * SUB_W for _ in range(16)]
    x = (SUB_W - width) // 2 + 1
    for g in glyphs:
        if g is None:
            x += SUB_SPACE
            continue
        rows, tilde = g
        for y, row in enumerate(rows):
            for dx, c in enumerate(row):
                if c == "#":
                    ink[SUB_TOP + y][x + dx] = True
        if tilde:
            for y, row in enumerate(SUB_TILDE):
                for dx, c in enumerate(row):
                    if c == "#":
                        ink[y][x + dx] = True
        x += len(rows[0]) + 1
    pix = [[0] * SUB_W for _ in range(16)]
    for y in range(16):
        for xx in range(SUB_W):
            if ink[y][xx]:
                pix[y][xx] = max(2, min(15, 16 - y))
            elif any(0 <= y + dy < 16 and 0 <= xx + dx < SUB_W and ink[y + dy][xx + dx]
                     for dy in (-1, 0, 1) for dx in (-1, 0, 1)):
                pix[y][xx] = 1                    # contorno
    return pix


def put_subtitle(rom, text):
    data = bytearray(decompress(rom, bank_table(rom, 0x25)[SUB_BLOCK])[0])
    pix = render_subtitle(text)
    for half in range(2):
        rows = pix[half * 8:half * 8 + 8]
        for t in range(16):
            n = half * 16 + t
            data[n * 32:n * 32 + 32] = _tile_bytes(rows, t * 8)
    return bytes(data)


def apply(rom, left, right, write_block, credit=None, subtitle=None):
    tiles = bytearray(decompress(rom, bank_table(rom, 0x25)[21])[0])
    tmap = bytearray(decompress(rom, bank_table(rom, 0x25)[4])[0])
    row = [0] * 32
    free = iter(FREE_TILES)
    used_cols = set()
    for text, center in zip((left, right), CENTERS):
        pix = render(text)
        w = len(pix[0])
        start = center - w // 2
        c0, c1 = start // 8, (start + w + 7) // 8
        if c0 < 0 or c1 > 32 or used_cols & set(range(c0, c1)):
            raise SystemExit(f"titulo.txt: '{text}' es demasiado largo ({w} px)")
        used_cols |= set(range(c0, c1))
        # se dibuja en un lienzo de pantalla para alinear con la rejilla de tiles
        for col in range(c0, c1):
            data = _tile_bytes(pix, col * 8 - start)
            if not any(data):
                continue
            n = next(free, None)
            if n is None:
                raise SystemExit("titulo.txt: no quedan tiles libres")
            tiles[(n - 0x80) * 32:(n - 0x80) * 32 + 32] = data
            row[col] = PAL_BITS | n
    for col in range(32):
        k = (ROW * 32 + col) * 2
        tmap[k:k + 2] = row[col].to_bytes(2, "little")
    if credit:
        put_credit(tiles, tmap, credit)
    blocks = {21: bytes(tiles), 4: bytes(tmap)}
    if subtitle:
        blocks[SUB_BLOCK] = put_subtitle(rom, subtitle)
    repack_bank(rom, 0x25, blocks)
    print(f"Título: '{left}' / '{right}'" + (f" / crédito '{credit}'" if credit else "")
          + (f" / subtítulo '{subtitle}'" if subtitle else ""))
