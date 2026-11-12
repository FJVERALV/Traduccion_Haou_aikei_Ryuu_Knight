"""Compresión LZSS de Haou Taikei Ryuu Knight (rutina original en $00:B0F0 / $00:B170).

Formato de un bloque:
  word cabecera: bit15 = 1 si está comprimido; (cabecera & 0x7FFF) + 1 = tamaño descomprimido
  datos: byte de banderas (bit0 primero; 1 = literal, 0 = referencia)
         referencia = 2 bytes lo, hi:
             offset   = lo | (hi & 0x0F) << 8   (posición absoluta en búfer circular de 4 KB)
             longitud = (hi >> 4) * 2 + 3        (sólo longitudes impares 3..33)
  El búfer circular empieza en la posición 0; sus últimos bytes están a cero.

Cada banco comprimido empieza con una tabla de punteros de 16 bits ($8000..).
"""


def decompress(data: bytes, pos: int):
    """Devuelve (datos, offset_final, estaba_comprimido)."""
    hdr = int.from_bytes(data[pos:pos + 2], "little")
    size = (hdr & 0x7FFF) + 1
    p = pos + 2
    if not hdr & 0x8000:
        return bytes(data[p:p + size]), p + size, False
    buf = bytearray(0x1000)
    out = bytearray()
    r = 0
    while len(out) < size:
        flags = data[p]; p += 1
        for bit in range(8):
            if len(out) >= size:
                break
            if flags >> bit & 1:
                c = data[p]; p += 1
                out.append(c); buf[r] = c; r = (r + 1) & 0xFFF
            else:
                lo, hi = data[p], data[p + 1]; p += 2
                off = lo | (hi & 0x0F) << 8
                for k in range((hi >> 4) * 2 + 3):
                    c = buf[(off + k) & 0xFFF]
                    out.append(c); buf[r] = c; r = (r + 1) & 0xFFF
    return bytes(out[:size]), p, True


def _matches(raw):
    """Para cada posición: (longitud máxima, offset en búfer) de la mejor coincidencia."""
    size = len(raw)
    index = {}
    best = [(0, 0)] * size
    for i in range(size):
        maxlen = min(33, size - i)
        bl, bo = 0, 0
        if maxlen >= 3:
            key = raw[i:i + 3]
            for j in reversed(index.get(key, ())):
                if i - j >= 0x1000:
                    break
                l = 3
                while l < maxlen and raw[j + l] == raw[i + l]:
                    l += 1
                if l > bl:
                    bl, bo = l, j & 0xFFF
                    if l == maxlen:
                        break
            # rachas de ceros: se pueden copiar de la zona aún no escrita del búfer
            if raw[i] == 0 and i + 66 < 0x1000:
                z = 0
                while z < maxlen and raw[i + z] == 0:
                    z += 1
                if z > bl:
                    bl, bo = z, 0x1000 - 33
            if i + 3 <= size:
                index.setdefault(raw[i:i + 3], []).append(i)
        best[i] = (bl, bo)
    return best


def compress(raw: bytes) -> bytes:
    """Compresor compatible con análisis óptimo (ventana 4 KB, longitudes 3..33 impares)."""
    size = len(raw)
    if not 0 < size <= 0x8000:
        raise ValueError("tamaño fuera de rango")
    best = _matches(raw)
    # programación dinámica hacia atrás: coste en bits (literal 9, referencia 17)
    cost = [0] * (size + 1)
    choice = [1] * (size + 1)
    for i in range(size - 1, -1, -1):
        c, ch = 9 + cost[i + 1], 1
        bl = best[i][0]
        for L in range(3, bl + 1, 2):
            v = 17 + cost[i + L]
            if v < c:
                c, ch = v, L
        cost[i], choice[i] = c, ch
    out = bytearray((0x8000 | (size - 1)).to_bytes(2, "little"))
    i = 0
    while i < size:
        flag_pos = len(out); out.append(0); flags = 0
        for bit in range(8):
            if i >= size:
                break
            L = choice[i]
            if L == 1:
                flags |= 1 << bit
                out.append(raw[i])
            else:
                off = best[i][1]
                out += bytes([off & 0xFF, ((L - 3) // 2) << 4 | off >> 8])
            i += L
        out[flag_pos] = flags
    return bytes(out)


def bank_table(data: bytes, bank: int):
    """Lista de offsets de archivo de los bloques de un banco comprimido LoROM."""
    base = (bank & 0x7F) * 0x8000
    first = int.from_bytes(data[base:base + 2], "little")
    n = (first - 0x8000) // 2
    return [base + int.from_bytes(data[base + 2 * i:base + 2 * i + 2], "little") - 0x8000
            for i in range(n)]
