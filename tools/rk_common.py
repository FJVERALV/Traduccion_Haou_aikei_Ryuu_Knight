"""Datos y utilidades comunes para la traducción de Haou Taikei Ryuu Knight.

Mapa de la ROM inglesa (parche Game Translate v1.0, LoROM 2 MB, sin cabecera):

  0x0A0000-0x0B7FFF  Bancos $14-$16: guion de eventos (LZSS). En la versión inglesa
                     cada texto japonés se sustituyó por  FE 18 lo hi  = "mostrar mensaje N".
  0x11CC87           Banco $23 bloque 44 (LZSS): nombres por defecto de los 6 personajes.
  0x129F7C/0x12E279  Banco $25 bloques 4 y 21 (LZSS): mapa y gráficos (4bpp) del título.
  0x180000           Código nuevo del hack inglés.
  0x181000           Tabla de punteros de 3 bytes a los 1227 mensajes ($30:9000).
  0x184000           Anchos de la fuente 16x16 (menús y nombres pre-renderizados).
  0x184100           Anchos de la fuente 8x8.
  0x184200           Fuente 8x8 1bpp (carácter c en 0x184200 + c*8).
  0x188000           Ancho de cada celda/letra en los DIÁLOGOS (palabra por celda).
  0x184C00           Tabla de punteros de 16 bits (banco $30) a nombres de objetos/lugares.
  0x184E00           Cadenas de nombres (terminadas en FF).
  0x18C000           Fuente VWF 16x16 1bpp (carácter c en 0x18C000 + c*32) y, a partir de
                     la celda 0x100, menús pre-renderizados como gráficos.
  0x190000-0x1ADDFF  Texto de los mensajes en ASCII.
  0x1B0000           Listas de celdas (palabras de 16 bits, fin = byte FF) que forman el
                     nombre gráfico de cada objeto/lugar (163 listas, recorridas en orden).
  0x1BC000/0x1C4000  Más celdas pre-renderizadas (nombres, títulos de episodio, teclado).

Índice de celda (tile) -> ROM, según la rutina del hack en $30:80CF:
  a = índice - 0x300
  a <  0x200 -> 0x18C000 + a*32                       (banco $31)
  a <  0xE00 -> banco $37 + (a-0x200)//0x200, + 0xC000 + ((a-0x200)%0x200)*32
"""
import os
import sys
import zlib

# La ruta del proyecto contiene "ū": evita errores al imprimir en consolas cp1252.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROM_JP = os.path.join(ROOT, "Haou Taikei Ryuu Knight - Lord of Paladin (Japan) (Rev 1).sfc")
ROM_EN = os.path.join(ROOT, "Haou Taikei Ryuu Knight - Lord of Paladin (English v1.0).sfc")
PATCH_EN = os.path.join(ROOT, "Haou Taikei Ryuu Knight - Lord of Paladin (English) v1.0.bps")
CRC_JP = 0x2740560B
CRC_EN = 0x51EA61E1

MSG_TABLE = 0x181000
MSG_COUNT = 1227
WIDTHS = 0x184000                 # anchos fuente 16x16 (menús/nombres gráficos)
WIDTHS8 = 0x184100                # anchos de la fuente 8x8 (no la usan los diálogos)
DLG_WIDTHS = 0x188000             # ancho de cada celda en los DIÁLOGOS: 1 palabra por
                                  # celda (índice-0x300; las letras son celda = código)
FONT8 = 0x184200
NAME_PTRS = 0x184C00
NAME_DATA = 0x184E00
NAME_DATA_END = 0x188000
NAME_COUNT = 163
FONT16 = 0x18C000
TILELISTS = 0x1B0000
TILELISTS_END = 0x1B087F          # fin de las 163 listas originales
TILELIST_BANK_PATCH = (0xF376, 0xF382, 0xF620)   # bytes de banco ($36) que apuntan a las listas

# Zonas libres de la ROM inglesa usadas por el insertor
SCRIPT_REGIONS = [(0x190000, 0x1B0000), (0x1C8000, 0x1CC000), (0x1D0000, 0x1D4000),
                  (0x1D8000, 0x1DC000), (0x1E0000, 0x1E4000), (0x1F0000, 0x200000)]
NEW_CELL_FIRST = 0x900            # celdas nuevas para nombres: 0x900..0x10FF (0x1CC000..)
NEW_CELL_LAST = 0xAFF             # 0xB00-0xCFF quedan para los menús (menus.py)
NEW_TILELISTS = 0x1E8000          # banco $3D

# Caracteres especiales del texto --------------------------------------------------
# Códigos 0x80-0x89: marcadores del motor (0x82 rodea el nombre del que habla, etc.)
# Huecos sin glifo en la fuente inglesa que reutilizamos para el español:
SPANISH = {
    "á": 0x7B, "é": 0x7C, "í": 0x7D, "ó": 0x7F, "ú": 0x5E, "ü": 0x5F, "ñ": 0x60,
    "Á": 0x23, "É": 0x24, "Í": 0x3D, "Ó": 0x40, "Ñ": 0x5C, "¿": 0x3C, "¡": 0x3E,
}
SPANISH_REV = {v: k for k, v in SPANISH.items()}
# Sustituciones automáticas al codificar (caracteres que no existen en la fuente)
FALLBACK = {"Ú": "U", "Ü": "U", "“": '"', "”": '"', "‘": "'", "’": "'", "—": "-", "…": "..."}

FE_TAGS = {0x07: "{espera}", 0x08: "{ventana}", 0xFF: "{fin}"}
FE_TAGS_REV = {v: k for k, v in FE_TAGS.items()}


def lorom_to_file(addr24: int) -> int:
    return ((addr24 >> 16) & 0x7F) * 0x8000 + (addr24 & 0x7FFF)


def file_to_lorom(off: int) -> int:
    return ((off // 0x8000) | 0x80) << 16 | (off % 0x8000) | 0x8000


def cell_offset(idx: int) -> int:
    a = idx - 0x300
    if 0 <= a < 0x200:
        return FONT16 + a * 32
    if 0x200 <= a < 0xE00:
        a -= 0x200
        bank = 0x37 + a // 0x200
        return bank * 0x8000 + 0x4000 + (a % 0x200) * 32
    raise ValueError(f"índice de celda fuera de rango: {idx:#x}")


# ---------------------------------------------------------------------------------
def load_en_rom() -> bytearray:
    """ROM inglesa: la del directorio o, si falta, la genera desde la japonesa + BPS."""
    if os.path.exists(ROM_EN):
        data = open(ROM_EN, "rb").read()
        if zlib.crc32(data) == CRC_EN:
            return bytearray(data)
        print("Aviso: la ROM inglesa no tiene el CRC esperado; se regenera desde el parche.")
    from bps import apply_bps
    jp = open(ROM_JP, "rb").read()
    if zlib.crc32(jp) != CRC_JP:
        raise SystemExit("La ROM japonesa no es la Rev 1 sin cabecera (CRC32 2740560B).")
    return bytearray(apply_bps(jp, open(PATCH_EN, "rb").read()))


# --- Texto de mensajes -------------------------------------------------------------
def decode_message(rom, pos):
    """Decodifica un mensaje desde pos hasta FF (o FE FF). Devuelve (texto, fin)."""
    out = []
    while True:
        b = rom[pos]
        if b == 0xFF:
            return "".join(out), pos + 1
        if b == 0xFE:
            s = rom[pos + 1]
            if s == 0x09:
                out.append("\n"); pos += 2
            elif s == 0x00:
                out.append("{nombre:%02X}" % rom[pos + 2]); pos += 3
            elif s in FE_TAGS:
                out.append(FE_TAGS[s]); pos += 2
                if s == 0xFF:
                    return "".join(out), pos
            else:
                out.append("{FE:%02X}" % s); pos += 2
            continue
        if b in SPANISH_REV:
            out.append(SPANISH_REV[b])
        elif 0x20 <= b < 0x7F and b not in (0x7B, 0x7D):
            out.append(chr(b))
        else:
            out.append("{%02X}" % b)
        pos += 1


def encode_message(text: str, where: str = "") -> bytes:
    """Codifica el texto de un mensaje (sin el FF final, salvo si acaba en {fin})."""
    out = bytearray()
    i = 0
    while i < len(text):
        c = text[i]
        if c == "{":
            j = text.find("}", i)
            if j < 0:
                raise ValueError(f"{where}: falta '}}' en: {text[i:i+20]!r}")
            tag = text[i:j + 1]
            body = tag[1:-1]
            if tag in FE_TAGS_REV:
                out += bytes([0xFE, FE_TAGS_REV[tag]])
            elif body.lower().startswith("nombre:"):
                out += bytes([0xFE, 0x00, int(body[7:], 16)])
            elif body.upper().startswith("FE:"):
                out += bytes([0xFE, int(body[3:], 16)])
            elif len(body) == 2:
                out.append(int(body, 16))
            else:
                raise ValueError(f"{where}: etiqueta desconocida {tag}")
            i = j + 1
            continue
        if c == "\n":
            out += b"\xFE\x09"
        elif c in SPANISH:
            out.append(SPANISH[c])
        elif c in FALLBACK:
            out += encode_message(FALLBACK[c])
        elif 0x20 <= ord(c) < 0x7F:
            out.append(ord(c))
        else:
            raise ValueError(f"{where}: carácter no soportado {c!r}")
        i += 1
    return bytes(out)


NAME_PX = 40      # ancho estimado de {nombre:NN} en los diálogos (~5 letras)


def dlg_word(width: int) -> int:
    """Codifica un ancho (1-16) como lo espera el motor de diálogo ($01:8DC8)."""
    if width <= 0:
        return 0
    v = 1 << (16 - min(width, 16))
    return (v & 0xFF) << 8 | v >> 8


def dlg_width_of(word: int) -> int:
    v = (word & 0xFF) << 8 | word >> 8
    n = 16
    while n:
        bit = v & 1
        v >>= 1
        if bit:
            break
        n -= 1
    return n


def set_dlg_width(rom, cell_index: int, width: int):
    """cell_index: código de letra (0-0xFF) o índice de celda >= 0x300."""
    a = cell_index - 0x300 if cell_index >= 0x300 else cell_index
    off = DLG_WIDTHS + 2 * a
    if off + 2 > 0x189C00:
        raise ValueError(f"celda {cell_index:#x} fuera de la tabla de anchos")
    rom[off:off + 2] = dlg_word(width).to_bytes(2, "little")


def dlg_widths(rom):
    """Anchos de las letras 0-0xFF tal como los usa el diálogo."""
    return [dlg_width_of(int.from_bytes(rom[DLG_WIDTHS + 2 * c:DLG_WIDTHS + 2 * c + 2], "little"))
            for c in range(256)]


def line_widths(encoded: bytes, widths) -> list:
    """Anchos en píxeles de cada línea de un mensaje codificado."""
    res, cur, i = [], 0, 0
    while i < len(encoded):
        b = encoded[i]
        if b == 0xFE:
            s = encoded[i + 1]
            if s == 0x00:
                cur += NAME_PX; i += 3; continue    # nombre de personaje (estimado)
            if s in (0x09, 0x08):
                res.append(cur); cur = 0
            i += 2
            continue
        cur += widths[b]
        i += 1
    res.append(cur)
    return res


# --- Fuentes / gráficos 1bpp --------------------------------------------------------
def read_cell16(rom, off):
    return [rom[off + 2 * y] << 8 | rom[off + 2 * y + 1] for y in range(16)]


def write_cell16(rom, off, rows):
    for y, r in enumerate(rows):
        rom[off + 2 * y] = r >> 8 & 0xFF
        rom[off + 2 * y + 1] = r & 0xFF


CANVAS = 1024   # ancho del lienzo de render en bits


def glyph_left(rom, b: int) -> int:
    """Primera columna con tinta del glifo b (0 si está vacío)."""
    cols = 0
    for r in read_cell16(rom, FONT16 + b * 32):
        cols |= r
    for x in range(16):
        if cols >> (15 - x) & 1:
            return x
    return 0


def render_vwf(text_bytes: bytes, rom, start_x=None, spacing=0) -> list:
    """Renderiza bytes con la fuente VWF. Devuelve (filas, ancho_px).

    Como en el parche inglés, el texto pre-renderizado empieza en la primera
    columna con tinta del primer carácter."""
    widths = rom[WIDTHS:WIDTHS + 0x100]
    rows = [0] * 16
    x = start_x if start_x is not None else (-glyph_left(rom, text_bytes[0]) if text_bytes else 0)
    mask = (1 << CANVAS) - 1
    for b in text_bytes:
        g = read_cell16(rom, FONT16 + b * 32)
        for y in range(16):
            rows[y] |= (g[y] << (CANVAS - 16 - x)) & mask
        x += widths[b] + spacing
    return rows, x - spacing


def split_cells(rows, width_px):
    """Corta el lienzo de render_vwf en celdas de 16 px."""
    n = max(1, (width_px + 15) // 16)
    cells = []
    for c in range(n):
        shift = CANVAS - 16 * (c + 1)
        cells.append([(r >> shift) & 0xFFFF for r in rows])
    return cells


# --- Cabecera SNES -------------------------------------------------------------------
def fix_checksum(rom: bytearray):
    rom[0x7FDC:0x7FE0] = b"\xFF\xFF\x00\x00"
    s = sum(rom) & 0xFFFF
    rom[0x7FDC:0x7FDE] = (s ^ 0xFFFF).to_bytes(2, "little")
    rom[0x7FDE:0x7FE0] = s.to_bytes(2, "little")
