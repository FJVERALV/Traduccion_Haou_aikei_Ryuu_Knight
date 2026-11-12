"""Genera la ROM traducida a partir de la carpeta traduccion/.

Uso:
    python tools/insertar.py

Salida:
    salida/Haou Taikei Ryuu Knight (ES).sfc
    salida/Haou Taikei Ryuu Knight (ES).bps   (parche sobre la ROM japonesa Rev 1)

Base: la ROM inglesa (o la japonesa + parche inglés). Se reemplazan los diálogos,
nombres, nombres de personajes, fuente y gráficos con lo que haya en traduccion/.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rk_common import *                         # noqa: E402,F401
from lzss import decompress, compress, bank_table   # noqa: E402
from bps import create_bps                      # noqa: E402
import graficos                                 # noqa: E402
import menus                                    # noqa: E402
import titulo                                   # noqa: E402

WORK = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(ROOT, "traduccion")
OUTDIR = os.path.join(ROOT, "salida")
OUT_ROM = os.path.join(OUTDIR, "Haou Taikei Ryuu Knight (ES).sfc")
OUT_BPS = os.path.join(OUTDIR, "Haou Taikei Ryuu Knight (ES).bps")
MAX_LINE_PX = 236     # ancho máximo de línea de diálogo (el inglés llega justo a 236)
MAX_NAME_TABLE = 15

warnings = []


def warn(msg):
    warnings.append(msg)


# --- lectura de archivos de traducción --------------------------------------------------
def parse_dialogos(path):
    msgs = {}
    cur, lines = None, []

    def flush():
        if cur is None:
            return
        body = list(lines)
        if body and body[-1] == "":
            body.pop()                       # línea en blanco separadora
        msgs[cur] = "\n".join(body)

    with open(path, encoding="utf-8") as f:
        for n, raw in enumerate(f, 1):
            line = raw.rstrip("\r\n")
            if line.startswith("#"):
                continue
            if line.startswith("@"):
                flush()
                try:
                    cur = int(line[1:].strip())
                except ValueError:
                    raise SystemExit(f"dialogos.txt:{n}: cabecera inválida {line!r}")
                if cur in msgs:
                    raise SystemExit(f"dialogos.txt:{n}: mensaje @{cur:04d} repetido")
                lines = []
            elif cur is not None:
                lines.append(line)
    flush()
    return msgs


def parse_table(path, ncols_min=3):
    rows = {}
    with open(path, encoding="utf-8") as f:
        for n, raw in enumerate(f, 1):
            line = raw.rstrip("\r\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) < ncols_min:
                raise SystemExit(f"{os.path.basename(path)}:{n}: faltan columnas")
            rows[int(parts[0])] = parts
    return rows


# --- inserción ---------------------------------------------------------------------------
class Space:
    """Reparte datos en regiones libres sin cruzar límites de banco LoROM."""

    def __init__(self, regions):
        self.chunks = []
        for a, b in regions:
            while a < b:
                end = min(b, (a // 0x8000 + 1) * 0x8000)
                self.chunks.append([a, end])
                a = end

    def alloc(self, size):
        for c in self.chunks:
            if c[1] - c[0] >= size:
                p = c[0]
                c[0] += size
                return p
        raise SystemExit("¡No queda espacio libre en la ROM para el texto!")

    def free(self):
        return sum(b - a for a, b in self.chunks)


def insert_graphics(rom):
    gdir = os.path.join(WORK, "graficos")
    p = lambda n: os.path.join(gdir, n)     # noqa: E731
    if os.path.exists(p("celdas_31_fuente_y_menus.png")):
        graficos.png_to_cells16(rom, 0x18C000, 512, p("celdas_31_fuente_y_menus.png"))
    if os.path.exists(p("celdas_37_nombres.png")):
        graficos.png_to_cells16(rom, 0x1BC000, 512, p("celdas_37_nombres.png"))
    if os.path.exists(p("celdas_38_titulos_teclado.png")):
        graficos.png_to_cells16(rom, 0x1C4000, 512, p("celdas_38_titulos_teclado.png"))
    if os.path.exists(p("fuente8x8.png")):
        graficos.png_to_font8(rom, p("fuente8x8.png"))
    graficos.set_spanish_widths8(rom)
    if os.path.exists(p("anchos_fuente.txt")):
        with open(p("anchos_fuente.txt"), encoding="utf-8") as f:
            for line in f:
                if line.startswith("#") or not line.strip():
                    continue
                parts = [x.strip() for x in line.split("|")]
                rom[WIDTHS + int(parts[0], 16)] = int(parts[-1])
    # anchos que usa el DIÁLOGO para las letras españolas (tabla 0x188000)
    for c in SPANISH_REV:
        set_dlg_width(rom, c, rom[WIDTHS + c])
    if os.path.exists(p("titulo_4bpp.png")):
        blocks = bank_table(rom, 0x25)
        orig = decompress(rom, blocks[21])[0]
        new = graficos.png_to_tiles4(p("titulo_4bpp.png"), len(orig) // 32)
        if new != orig:
            write_block(rom, 0x25, 21, new)


def write_block(rom, bank, idx, raw):
    """Recomprime un bloque LZSS. Lo escribe en su sitio si cabe; si no, lo mueve al
    espacio libre (FF) del final del banco y actualiza su puntero."""
    blocks = bank_table(rom, bank)
    start = blocks[idx]
    bank_end = (bank + 1) * 0x8000
    nxt = min([b for b in blocks if b > start] + [bank_end])
    data = compress(raw)
    if len(data) > nxt - start:
        used_end = max(decompress(rom, b)[1] for b in blocks)
        if used_end + len(data) > bank_end or any(x != 0xFF for x in rom[used_end:used_end + len(data)]):
            raise SystemExit(f"El bloque {bank:02X}#{idx} comprimido ocupa {len(data)} bytes "
                             f"y no cabe en el banco.")
        start = used_end
        tbl = bank * 0x8000 + 2 * idx
        rom[tbl:tbl + 2] = (start % 0x8000 | 0x8000).to_bytes(2, "little")
    rom[start:start + len(data)] = data


def insert_dialogos(rom, base_msgs):
    path = os.path.join(WORK, "dialogos.txt")
    msgs = parse_dialogos(path)
    widths = dlg_widths(rom)
    missing = [i for i in range(MSG_COUNT) if i not in msgs]
    extra = [i for i in msgs if not 0 <= i < MSG_COUNT]
    if extra:
        raise SystemExit(f"dialogos.txt: números de mensaje fuera de rango: {extra[:10]}")
    if missing:
        warn(f"{len(missing)} mensajes no están en dialogos.txt; se deja el inglés "
             f"(p. ej. {missing[:5]})")
    encoded = []
    for i in range(MSG_COUNT):
        text = msgs.get(i, base_msgs[i])
        try:
            data = encode_message(text, f"@{i:04d}")
        except ValueError as e:
            raise SystemExit(f"dialogos.txt: {e}")
        for k, w in enumerate(line_widths(data, widths)):
            if w > MAX_LINE_PX:
                line = text.split("\n")[k] if k < len(text.split("\n")) else "?"
                warn(f"@{i:04d} línea {k + 1} demasiado larga ({w} px > {MAX_LINE_PX}): {line}")
        if not data.endswith(b"\xFE\xFF"):
            data += b"\xFF"
        encoded.append(data)

    # limpiar zona antigua y repartir
    for a, b in SCRIPT_REGIONS:
        rom[a:b] = b"\xFF" * (b - a)
    space = Space(SCRIPT_REGIONS)
    placed = {}
    for i, data in enumerate(encoded):
        if data not in placed:
            placed[data] = space.alloc(len(data))
            rom[placed[data]:placed[data] + len(data)] = data
        p = placed[data]
        e = MSG_TABLE + 3 * i
        rom[e] = p & 0xFF
        rom[e + 1] = (p % 0x8000 | 0x8000) >> 8
        rom[e + 2] = p // 0x8000
    used = sum(len(d) for d in placed)
    print(f"Diálogos: {len(encoded)} mensajes, {used} bytes, quedan {space.free()} libres")


def insert_nombres(rom):
    rows = parse_table(os.path.join(WORK, "nombres.txt"))
    # listas originales (para las entradas vacías)
    p, orig_lists = TILELISTS, []
    for _ in range(NAME_COUNT):
        cur = []
        while rom[p] != 0xFF:
            cur.append(rom[p] | rom[p + 1] << 8)
            p += 2
        p += 1
        orig_lists.append(cur)

    cell_ids = {}
    cell_w = {}
    # primero las celdas que ya usaban los nombres ingleses (0x4F3-0x7F8, probadas en
    # el juego), luego 0x880-0x8FF (resto libre del banco $38) y por último
    # bancos nuevos $39-$3C (0x900-0x10FF)
    free_ids = iter([x for x in list(range(0x4F3, 0x7F9)) + list(range(0x880, 0x900)) + list(range(NEW_CELL_FIRST, NEW_CELL_LAST + 1))
                     if x & 0xFF != 0xFF])   # el byte FF marca fin de lista
    lists = []
    strings = []
    for i in range(NAME_COUNT):
        r = rows.get(i)
        if r is None or r[2] == "(vacío)" or (orig_lists[i] and orig_lists[i][0] < 0x300):
            lists.append(orig_lists[i])
            strings.append(b"")
            continue
        text = r[2]
        data = encode_message(text, f"nombres.txt {i:03d}")
        if any(b >= 0x80 for b in data):
            raise SystemExit(f"nombres.txt {i:03d}: sólo se permite texto normal")
        short = encode_message(r[3], f"nombres.txt {i:03d}") if len(r) > 3 and r[3] else data
        if len(short) > MAX_NAME_TABLE:
            if len(r) > 3 and r[3]:
                warn(f"nombres.txt {i:03d}: el texto corto tiene más de {MAX_NAME_TABLE} letras")
            short = short[:MAX_NAME_TABLE]
        strings.append(short)
        spacing = -1 if 116 <= i <= 127 else 0
        canvas, w = render_vwf(data, rom, spacing=spacing)
        cells = split_cells(canvas, w)
        if len(cells) > 15:
            warn(f"nombres.txt {i:03d}: '{text}' ocupa {len(cells)} celdas (inglés máx. 15); "
                 f"puede no caber en pantalla")
        lst = []
        for k, c in enumerate(cells):
            key = tuple(c)
            if key not in cell_ids:
                new_id = next(free_ids, None)
                if new_id is None:
                    raise SystemExit("No quedan celdas libres para los nombres.")
                cell_ids[key] = new_id
                write_cell16(rom, cell_offset(new_id), c)
                cell_w[new_id] = 0
            cw = 16 if k < len(cells) - 1 else max(1, min(16, w - 16 * k))
            cell_w[cell_ids[key]] = max(cell_w[cell_ids[key]], cw)
            lst.append(cell_ids[key])
        lists.append(lst)

    for cid, cw in cell_w.items():
        set_dlg_width(rom, cid, cw)

    # listas de celdas: en su sitio si caben; si no, al banco $3D redirigiendo el código
    out = bytearray()
    for lst in lists:
        for x in lst:
            out += x.to_bytes(2, "little")
        out.append(0xFF)
    for a in TILELIST_BANK_PATCH:
        if rom[a] != 0x36:
            raise SystemExit(f"Byte inesperado en {a:#x}: {rom[a]:#x}")
    if len(out) <= TILELISTS_END - TILELISTS:
        rom[TILELISTS:TILELISTS_END] = out + b"\xFF" * (TILELISTS_END - TILELISTS - len(out))
        where = "en su sitio"
    else:
        rom[NEW_TILELISTS:NEW_TILELISTS + len(out)] = out
        for a in TILELIST_BANK_PATCH:
            rom[a] = NEW_TILELISTS // 0x8000
        where = "movidas al banco $3D"
    print(f"Listas de celdas: {len(out)} bytes, {where}")

    # tabla de texto de nombres (banco $30)
    rom[NAME_DATA:NAME_DATA_END] = b"\xFF" * (NAME_DATA_END - NAME_DATA)
    p = NAME_DATA
    for i, s in enumerate(strings):
        if p + len(s) + 1 > NAME_DATA_END:
            raise SystemExit("La tabla de texto de nombres no cabe.")
        rom[p:p + len(s)] = s
        rom[p + len(s)] = 0xFF
        rom[NAME_PTRS + 2 * i:NAME_PTRS + 2 * i + 2] = (p - 0x180000 + 0x8000).to_bytes(2, "little")
        p += len(s) + 1
    print(f"Nombres: {len(lists)} listas, {len(cell_ids)} celdas gráficas nuevas")


def insert_personajes(rom):
    rows = parse_table(os.path.join(WORK, "personajes.txt"))
    blk = bank_table(rom, 0x23)[44]
    data = bytearray(decompress(rom, blk)[0])
    changed = False
    for k in range(6):
        r = rows.get(k + 1)
        if not r:
            continue
        name = encode_message(r[2], f"personajes.txt {k + 1}")
        if len(name) > 8 or any(not (0x20 <= b < 0x7F) for b in name):
            raise SystemExit(f"personajes.txt {k + 1}: máx. 8 letras sin acentos")
        slot = name + b"\x00" * (7 - len(name)) + b"\xFF" if len(name) < 8 else name
        if data[k * 8:k * 8 + 8] != slot:
            data[k * 8:k * 8 + 8] = slot
            changed = True
    if changed:
        write_block(rom, 0x23, 44, bytes(data))
    print("Personajes:", "actualizados" if changed else "sin cambios")


def main():
    if not os.path.isdir(WORK):
        raise SystemExit("No existe traduccion/. Ejecuta antes: python tools/extraer.py")
    rom = load_en_rom()
    from extraer import read_messages
    base_msgs = read_messages(rom)

    insert_graphics(rom)
    insert_dialogos(rom, base_msgs)
    insert_nombres(rom)
    insert_personajes(rom)
    menus_path = os.path.join(WORK, "menus.txt")
    if os.path.exists(menus_path):
        tr = {r[1]: r[2] for r in parse_table(menus_path).values()}
        menus.insert_menus(rom, tr, write_block, warn)
    titulo_path = os.path.join(WORK, "titulo.txt")
    if os.path.exists(titulo_path):
        with open(titulo_path, encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip() and not l.startswith("#")]
        titulo.apply(rom, lines[0], lines[1], write_block, lines[2] if len(lines) > 2 else None,
                     lines[3] if len(lines) > 3 else None)
    fix_checksum(rom)

    os.makedirs(OUTDIR, exist_ok=True)
    open(OUT_ROM, "wb").write(rom)
    jp = open(ROM_JP, "rb").read()
    open(OUT_BPS, "wb").write(create_bps(jp, bytes(rom)))
    print(f"\nROM: {OUT_ROM}\nParche (sobre la japonesa Rev 1): {OUT_BPS}")
    if warnings:
        print(f"\n{len(warnings)} avisos:")
        for w in warnings[:200]:
            print("  -", w)
        if len(warnings) > 200:
            print(f"  ... y {len(warnings) - 200} más")


if __name__ == "__main__":
    main()
