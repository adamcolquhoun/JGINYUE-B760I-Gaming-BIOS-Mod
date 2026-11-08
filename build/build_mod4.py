"""mod4 = mod3 + every CF9 'hard reset' (0x06) write changed to full reset (0x0E) + text-screen logo replaced.
python -I build_mod4.py mod3.bin logo.png out.bin workdir"""
import sys, struct, lzma, hashlib, uuid, subprocess, os, re

src, logo_png, out, TD = sys.argv[1:5]
img = bytearray(open(src, 'rb').read())
assert hashlib.sha256(img).hexdigest().startswith('9212f324acb20434'), 'input is not mod3'
LZ = os.environ.get('LZMA_EXE', 'lzma.exe')   # 7-Zip LZMA SDK encoder (bin/x64/lzma.exe)
GUID_LZMA = uuid.UUID('EE4E5898-3914-4259-9D6E-DC7BD79403CF').bytes_le
EX = os.environ['EXTRACTED_BIOS'] + '/'
FV1 = EX + 'FV01_0470000_8C8CE578/002_9E21FD93-9C72-4C15-8C4B-E77F1DB2D792/fv1/'

def sdk_lzma(raw, tag):
    rp = os.path.join(TD, tag + '.raw'); cp = os.path.join(TD, tag + '.lzma')
    open(rp, 'wb').write(raw)
    if os.path.exists(cp): os.remove(cp)
    subprocess.run([LZ, 'e', rp, cp], check=True, capture_output=True)
    c = open(cp, 'rb').read()
    assert c[0] == 0x5d and struct.unpack_from('<Q', c, 5)[0] == len(raw)
    return c

def ffs_header(old_hdr, new_size):
    h = bytearray(old_hdr); h[0x14:0x17] = new_size.to_bytes(3, 'little')
    state = h[0x17]; h[0x10] = h[0x11] = h[0x17] = 0
    h[0x10] = (-sum(h)) & 0xFF
    assert h[0x13] & 0x40 == 0
    h[0x11] = 0xAA; h[0x17] = state
    return bytes(h)

FILE = 0x4D10C0
fv_end = 0x470000 + struct.unpack_from('<Q', img, 0x470000 + 0x20)[0]
sec = FILE + 24; ssize = int.from_bytes(img[sec:sec + 3], 'little')
assert img[sec + 3] == 0x02 and img[sec + 4:sec + 20] == GUID_LZMA
doff = struct.unpack_from('<H', img, sec + 20)[0]
raw = bytearray(lzma.decompress(bytes(img[sec + doff:sec + ssize]), format=lzma.FORMAT_ALONE))

def ffs_attr_of(buf, pos):
    """attributes of the FFS file whose header precedes pos (walk back to an 8-aligned header whose size covers pos)."""
    for o in range((pos & ~7), max(0, pos - 0x200000), -8):
        sz = int.from_bytes(buf[o + 0x14:o + 0x17], 'little'); t = buf[o + 0x12]
        if o + sz > pos and 0x01 <= t <= 0x0F and buf[o + 0x17] in (0xF8, 0xF0) and 24 < sz < 0x400000:
            h = bytearray(buf[o:o + 24]); h[0x11] = 0; h[0x17] = 0
            if sum(h) & 0xFF == 0: return o, buf[o + 0x13]
    raise SystemExit(f'no FFS header found for {pos:#x}')

# ---- DXE / SMM reset writes: mov edx,0CF9h ; mov al,6 ; out dx,al  ->  mov al,0Eh
SITES = [('160_ResetSystemRuntimeDxe/1_PE32.efi', [0xb19]), ('217_SbRunSmm/1_PE32.efi', [0x1f95]),
         ('156_CardCheckDxe/1_PE32.efi', [0x611, 0x6c3]), ('230_PlatformInitAdvancedSmm/1_PE32.efi', [0xf7f]),
         ('241_UsbRtSmm/1_PE32.efi', [0x1a222])]
for rel, offs in SITES:
    cand = [p for p in os.listdir(FV1 + rel.split('/')[0]) if p.endswith('.efi')]
    pe = open(FV1 + rel.split('/')[0] + '/' + cand[0], 'rb').read()
    assert raw.count(pe) == 1, rel
    b = raw.index(pe)
    for o in offs:
        a = b + o
        assert raw[a:a + 2] == b'\xb0\x06', (rel, hex(o), raw[a:a + 2].hex())
        # either 'mov edx,0CF9h' right before, or (warm path) 'out' before and a jmp to the shared 'mov edx,0CF9h; out' tail after
        assert raw[a - 5:a] == b'\xba\xf9\x0c\x00\x00' or (raw[a - 1] == 0xee and raw[a + 2] == 0xeb), (rel, hex(o))
        raw[a + 1] = 0x0E
        fo, fat = ffs_attr_of(raw, a); assert fat & 0x40 == 0, rel
    print(f'  {rel}: {len(offs)} reset write(s) 0x06 -> 0x0E')

# ---- text-screen logo (AMITSE loads FFS 63819805...): 378x100 24bpp BMP, same size
G = uuid.UUID('63819805-67BB-46EF-AA8D-1524A19A01E4').bytes_le
fo = raw.index(G); assert fo % 8 == 0 and raw.count(G) == 1
bmp_off = fo + 24 + 4
assert raw[fo + 24 + 3] == 0x19 and raw[bmp_off:bmp_off + 2] == b'BM'
bsize, _, pix, _, w, h, _, bpp = struct.unpack_from('<IIIIiiHH', raw, bmp_off + 2)
assert (w, h, bpp, pix) == (378, 100, 24, 54) and bsize == 113654

import zlib
def png_rgb(d):
    o = 8; ch = []
    while o < len(d):
        l = struct.unpack('>I', d[o:o + 4])[0]; ch.append((d[o + 4:o + 8], d[o + 8:o + 8 + l])); o += 12 + l
    w, h, bd, ct, _, _, il = struct.unpack('>IIBBBBB', dict(ch)[b'IHDR']); assert bd == 8 and il == 0 and ct in (2, 3, 6)
    bp = {2: 3, 3: 1, 6: 4}[ct]; pal = dict(ch).get(b'PLTE'); z = zlib.decompress(b''.join(c for t, c in ch if t == b'IDAT'))
    st = w * bp; prev = bytearray(st); px = []; p = 0
    for _ in range(h):
        f = z[p]; ln = bytearray(z[p + 1:p + 1 + st]); p += 1 + st
        for i in range(st):
            a = ln[i - bp] if i >= bp else 0; b = prev[i]; c = prev[i - bp] if i >= bp else 0
            if f == 1: ln[i] = (ln[i] + a) & 255
            elif f == 2: ln[i] = (ln[i] + b) & 255
            elif f == 3: ln[i] = (ln[i] + ((a + b) >> 1)) & 255
            elif f == 4:
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                ln[i] = (ln[i] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        prev = ln
        row = []
        for x in range(w):
            if ct == 3: k = ln[x]; row.append(tuple(pal[3 * k:3 * k + 3]))
            elif ct == 2: row.append(tuple(ln[3 * x:3 * x + 3]))
            else:
                r, g, bb, al = ln[4 * x:4 * x + 4]
                row.append(tuple((v * al + 255 * (255 - al)) // 255 for v in (r, g, bb)))
        px.append(row)
    return w, h, px

sw, sh, spx = png_rgb(open(logo_png, 'rb').read())
N = 4  # 4x4 supersampling for a clean downscale
stride = (w * 3 + 3) & ~3
newbmp = bytearray(raw[bmp_off:bmp_off + 54])
rows = []
for y in range(h):
    line = bytearray()
    for x in range(w):
        acc = [0, 0, 0]
        for j in range(N):
            sy = min(sh - 1, int((y + (j + 0.5) / N) * sh / h))
            for i in range(N):
                sx = min(sw - 1, int((x + (i + 0.5) / N) * sw / w))
                for k in range(3): acc[k] += spx[sy][sx][k]
        r, g, b = (round(v / (N * N)) for v in acc)
        line += bytes((b, g, r))
    line += b'\0' * (stride - len(line)); rows.append(line)
for line in reversed(rows): newbmp += line          # BMP is bottom-up
assert len(newbmp) == bsize
raw[bmp_off:bmp_off + bsize] = newbmp
open(os.path.join(TD, 'textscreen_logo.bmp'), 'wb').write(newbmp)
print(f'  text-screen logo: {sw}x{sh} -> {w}x{h} 24bpp BMP (same size, {bsize} bytes)')

# ---- recompress DXE volume
newc = sdk_lzma(bytes(raw), 'dxe4')
section = bytearray(img[sec:sec + doff]); section[0:3] = (doff + len(newc)).to_bytes(3, 'little'); section += newc
newfile = ffs_header(img[FILE:FILE + 24], 24 + len(section)) + bytes(section)
assert FILE + len(newfile) <= fv_end
img[FILE:fv_end] = newfile + b'\xff' * (fv_end - FILE - len(newfile))
print(f'  DXE file {ssize + 24} -> {len(newfile)}, free after {fv_end - FILE - len(newfile)}')

# ---- PEI (uncompressed, execute-in-place TE images): ResetSystemPei x2 warm path, PeiCore
for a, exp, new, what in ((0xdf82e9, 'b006ebba558bec', 0x0E, 'ResetSystemPei (FV05) warm reset'),
                          (0xf505c1, 'b006ebba558bec', 0x0E, 'ResetSystemPei (FV07) warm reset'),
                          (0xf6bc72, 'b001eebaf90c00000405ee', None, 'PeiCore CF9 write (1+5)')):
    assert img[a:a + len(exp) // 2] == bytes.fromhex(exp), what
    if new is None: img[a + 9] = 0x0D        # add al,5 -> add al,0Dh  => 1+0x0D = 0x0E
    else: img[a + 1] = new
    fo, fat = ffs_attr_of(img, a); assert fat & 0x40 == 0, what
    print(f'  {what}: 0x06 -> 0x0E')

open(out, 'wb').write(img)
open(os.path.join(TD, 'dxe4_expected.raw'), 'wb').write(raw)
print('sha256', hashlib.sha256(img).hexdigest())
