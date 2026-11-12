"""Aplicador de parches BPS (formato beat) en Python puro."""
import sys, zlib

def _num(d, p):
    data, shift = 0, 1
    while True:
        x = d[p]; p += 1
        data += (x & 0x7f) * shift
        if x & 0x80:
            return data, p
        shift <<= 7
        data += shift

def apply_bps(src: bytes, patch: bytes) -> bytes:
    if patch[:4] != b"BPS1":
        raise ValueError("No es un parche BPS")
    p = 4
    ssize, p = _num(patch, p)
    tsize, p = _num(patch, p)
    msize, p = _num(patch, p)
    p += msize
    if len(src) != ssize:
        raise ValueError(f"Tamaño de ROM origen {len(src)} != {ssize}")
    if zlib.crc32(src) != int.from_bytes(patch[-12:-8], "little"):
        raise ValueError("CRC32 de la ROM origen no coincide")
    out = bytearray(tsize)
    o = sr = tr = 0
    end = len(patch) - 12
    while p < end:
        n, p = _num(patch, p)
        cmd, length = n & 3, (n >> 2) + 1
        if cmd == 0:
            out[o:o+length] = src[o:o+length]; o += length
        elif cmd == 1:
            out[o:o+length] = patch[p:p+length]; p += length; o += length
        else:
            v, p = _num(patch, p)
            off = (-1 if v & 1 else 1) * (v >> 1)
            if cmd == 2:
                sr += off
                out[o:o+length] = src[sr:sr+length]; sr += length; o += length
            else:
                tr += off
                for _ in range(length):
                    out[o] = out[tr]; o += 1; tr += 1
    if zlib.crc32(out) != int.from_bytes(patch[-8:-4], "little"):
        raise ValueError("CRC32 del resultado no coincide")
    return bytes(out)



def _enc(n: int) -> bytes:
    out = bytearray()
    while True:
        x = n & 0x7F
        n >>= 7
        if n == 0:
            out.append(0x80 | x)
            return bytes(out)
        out.append(x)
        n -= 1


def create_bps(src: bytes, dst: bytes) -> bytes:
    """Crea un parche BPS sencillo (SourceRead + TargetRead)."""
    out = bytearray(b"BPS1") + _enc(len(src)) + _enc(len(dst)) + _enc(0)
    i, n = 0, len(dst)
    while i < n:
        j = i
        while j < n and j < len(src) and src[j] == dst[j]:
            j += 1
        if j - i >= 4 or (j == n and j > i):
            out += _enc(((j - i - 1) << 2) | 0)
            i = j
            continue
        # TargetRead hasta la próxima coincidencia de >= 4 bytes
        j = i
        while j < n:
            if j + 4 <= min(n, len(src)) and src[j:j + 4] == dst[j:j + 4]:
                break
            j += 1
        out += _enc(((j - i - 1) << 2) | 1) + dst[i:j]
        i = j
    out += zlib.crc32(src).to_bytes(4, "little") + zlib.crc32(dst).to_bytes(4, "little")
    out += zlib.crc32(out).to_bytes(4, "little")
    return bytes(out)


if __name__ == "__main__":
    # python bps.py rom_origen parche.bps rom_destino
    s, pt, dst = sys.argv[1:4]
    open(dst, "wb").write(apply_bps(open(s, "rb").read(), open(pt, "rb").read()))
    print("OK ->", dst)
