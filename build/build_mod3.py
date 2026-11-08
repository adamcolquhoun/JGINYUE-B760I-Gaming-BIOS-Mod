"""Build JYB7IG13_mod3.bin from mod2:
 - Chinese (zh-chs) HII string packages in Setup, AMITSE, HddSmart, PauseKey -> inert zero-filled GUID packages (same size, no offsets move)
 - Setup IFR: language option SuppressIf -> always true (same length: TRUE TRUE AND)
 - Setup IFR + StdDefaults: Quiet Boot default 1 -> 0 (in place)
 - Boot logo PNG replaced (logo FV, outside the DXE volume)
python -I build_mod3.py mod2.bin new_logo.png out.bin"""
import sys, struct, lzma, hashlib, uuid, subprocess, os, zlib

src, logo_png, out = sys.argv[1:4]
img = bytearray(open(src, 'rb').read())
assert hashlib.sha256(img).hexdigest().startswith('918448e55f57352d'), 'input is not mod2'
LZ = os.environ.get('LZMA_EXE', 'lzma.exe')   # 7-Zip LZMA SDK encoder (bin/x64/lzma.exe)
TD = os.path.dirname(os.path.abspath(out))
GUID_LZMA = uuid.UUID('EE4E5898-3914-4259-9D6E-DC7BD79403CF').bytes_le

def sdk_lzma(raw, tag):
    rp = os.path.join(TD, tag + '.raw'); cp = os.path.join(TD, tag + '.lzma')
    open(rp, 'wb').write(raw)
    if os.path.exists(cp): os.remove(cp)
    subprocess.run([LZ, 'e', rp, cp], check=True, capture_output=True)
    c = open(cp, 'rb').read()
    assert c[0] == 0x5d and struct.unpack_from('<Q', c, 5)[0] == len(raw); print(f'  {tag}: lzma props {c[:5].hex()}')
    return c

def ffs_header(old_hdr, new_size):
    h = bytearray(old_hdr); h[0x14:0x17] = new_size.to_bytes(3, 'little')
    state = h[0x17]; h[0x10] = h[0x11] = h[0x17] = 0
    h[0x10] = (-sum(h)) & 0xFF
    assert h[0x13] & 0x40 == 0, 'file has data checksum attr'
    h[0x11] = 0xAA; h[0x17] = state
    return bytes(h)

def rebuild_lzma_file(FILE, fv_end, new_raw, tag):
    sec = FILE + 24
    ssize = int.from_bytes(img[sec:sec + 3], 'little')
    assert img[sec + 3] == 0x02 and img[sec + 4:sec + 20] == GUID_LZMA
    doff = struct.unpack_from('<H', img, sec + 20)[0]
    newc = sdk_lzma(new_raw, tag)
    section = bytearray(img[sec:sec + doff]); section[0:3] = (doff + len(newc)).to_bytes(3, 'little'); section += newc
    newfile = ffs_header(img[FILE:FILE + 24], 24 + len(section)) + bytes(section)
    assert FILE + len(newfile) <= fv_end
    img[FILE:fv_end] = newfile + b'\xff' * (fv_end - FILE - len(newfile))
    print(f'  {tag}: file {ssize + 24} -> {len(newfile)} bytes, free after {fv_end - FILE - len(newfile)}')

def get_lzma_raw(FILE):
    sec = FILE + 24; ssize = int.from_bytes(img[sec:sec + 3], 'little')
    doff = struct.unpack_from('<H', img, sec + 20)[0]
    return bytearray(lzma.decompress(bytes(img[sec + doff:sec + ssize]), format=lzma.FORMAT_ALONE))

def fv_end_of(fv):
    return fv + struct.unpack_from('<Q', img, fv + 0x20)[0]

FFS_GUID = {'108_Setup/1_PE32.efi': '899407D7-99FE-43D8-9A21-79EC328CAC21',
            '130_HddSmart/1_PE32.efi': 'D57C852E-809F-45CF-A377-D77BC0CB78EE',
            '136_PauseKey/1_PE32.efi': '0A845224-8675-4241-8AE9-4D94C93DEB90'}

def ffs_of(buf, rel, off):
    g = uuid.UUID(FFS_GUID[rel]).bytes_le
    i = buf.find(g)
    while i >= 0:
        sz = int.from_bytes(buf[i + 0x14:i + 0x17], 'little')
        if i % 8 == 0 and i < off < i + sz: return i, buf[i + 0x13]
        i = buf.find(g, i + 1)
    raise SystemExit(f'no FFS for {rel}')

# ---------------- DXE volume ----------------
DXE_FILE = 0x4D10C0
raw = get_lzma_raw(DXE_FILE)
EX = os.environ['EXTRACTED_BIOS'] + '/FV01_0470000_8C8CE578/002_9E21FD93-9C72-4C15-8C4B-E77F1DB2D792/fv1/'
MODS = {'108_Setup/1_PE32.efi': (0x640bd, 0x1c40c), 
        '130_HddSmart/1_PE32.efi': (0x46d4, 0x4a), '136_PauseKey/1_PE32.efi': (0x15b4, 0x47)}
INERT_GUID = uuid.UUID('6b1c3a52-0d3e-4f1e-9a6b-6e6f7a685f00').bytes_le
pe_base = {}
for rel, (po, plen) in MODS.items():
    pe = open(EX + rel, 'rb').read()
    # the extracted PE comes from the original IG13 DXE; these modules are unchanged in mod2 (only ACPI differs)
    assert raw.count(pe) == 1, rel
    b = raw.index(pe); pe_base[rel] = b
    o = b + po
    assert int.from_bytes(raw[o:o + 3], 'little') == plen and raw[o + 3] == 0x04
    hs = struct.unpack_from('<I', raw, o + 4)[0]
    assert raw[o + 46:raw.index(b'\0', o + 46)] == b'zh-chs', rel
    # next package must follow directly (en-US)
    assert raw[o + plen + 3] == 0x04
    raw[o:o + plen] = plen.to_bytes(3, 'little') + b'\x01' + INERT_GUID + b'\0' * (plen - 20)
    fo, fattr = ffs_of(raw, rel, o); assert fattr & 0x40 == 0, f'{rel} FFS has data checksum'
    print(f'  {rel}: zh-chs package ({plen} bytes) -> inert GUID package')

S = pe_base['108_Setup/1_PE32.efi']
# language option: SuppressIf { EqIdVal Q0x1239 == 0xFFFF } -> SuppressIf { TRUE TRUE AND }
o = S + 0x2f6db
assert raw[o:o + 12] == bytes.fromhex('0a82 1206 3912 ffff 0594 0b00'.replace(' ', ''))
assert struct.unpack_from('<H', raw, o + 8 + 6)[0] == 0x0008  # OneOf QuestionId 8 = System Language
raw[o + 2:o + 8] = bytes.fromhex('4602 4602 1502'.replace(' ', ''))
print('  System Language option: suppressed')
# Quiet Boot defaults (CheckBox Q=0x10fa, VarStore AMITSESetup off 0x50) 1 -> 0
o = S + 0x62281
assert raw[o:o + 14] == bytes.fromhex('068e2a002b00fa1013f050000000')
assert raw[o + 14:o + 28] == bytes.fromhex('5b06000000015b0601000001')+b'\x29\x02'
raw[o + 19] = 0; raw[o + 25] = 0
print('  Quiet Boot IFR defaults: 0')
rebuild_lzma_file(DXE_FILE, fv_end_of(0x470000), bytes(raw), 'dxe3')

# ---------------- StdDefaults: AMITSESetup.QuietBoot ----------------
q = 0x400e14
assert img[0x400dad:0x400db1] == b'NVAR' and img[0x400db8:0x400dc4] == b'AMITSESetup\0' and img[q] == 1
img[q] = 0
print('  StdDefaults AMITSESetup+0x50 (Quiet Boot): 1 -> 0')

# ---------------- Logo ----------------
def png_chunks(d):
    assert d[:8] == b'\x89PNG\r\n\x1a\n'; o = 8
    while o < len(d):
        l = struct.unpack('>I', d[o:o + 4])[0]; yield d[o + 4:o + 8], d[o + 8:o + 8 + l]; o += 12 + l

def png_to_rgba(d):
    ch = list(png_chunks(d)); ihdr = dict(ch)[b'IHDR']
    w, h, bd, ct, cm, fm, il = struct.unpack('>IIBBBBB', ihdr)
    assert bd == 8 and il == 0 and ct in (2, 3, 6)
    bpp = {2: 3, 3: 1, 6: 4}[ct]
    pal = dict(ch).get(b'PLTE'); trns = dict(ch).get(b'tRNS', b'')
    z = zlib.decompress(b''.join(c for t, c in ch if t == b'IDAT'))
    stride = w * bpp; prev = bytearray(stride); rows = []; p = 0
    for _ in range(h):
        f = z[p]; line = bytearray(z[p + 1:p + 1 + stride]); p += 1 + stride
        for i in range(stride):
            a = line[i - bpp] if i >= bpp else 0; b = prev[i]; c = prev[i - bpp] if i >= bpp else 0
            if f == 1: line[i] = (line[i] + a) & 255
            elif f == 2: line[i] = (line[i] + b) & 255
            elif f == 3: line[i] = (line[i] + ((a + b) >> 1)) & 255
            elif f == 4:
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                line[i] = (line[i] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        rows.append(line); prev = line
    out = bytearray()
    for line in rows:
        out.append(0)
        for x in range(w):
            if ct == 3:
                k = line[x]; r, g, bb = pal[3 * k:3 * k + 3]; al = trns[k] if k < len(trns) else 255
            elif ct == 2: r, g, bb = line[3 * x:3 * x + 3]; al = 255
            else: r, g, bb, al = line[4 * x:4 * x + 4]
            # composite onto white so nothing turns transparent on the black boot screen
            r = (r * al + 255 * (255 - al)) // 255; g = (g * al + 255 * (255 - al)) // 255; bb = (bb * al + 255 * (255 - al)) // 255
            out += bytes((r, g, bb, 255))
    def chunk(t, c): return struct.pack('>I', len(c)) + t + c + struct.pack('>I', zlib.crc32(t + c) & 0xffffffff)
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0)) +
            chunk(b'IDAT', zlib.compress(bytes(out), 9)) + chunk(b'IEND', b'')), (w, h)

newpng, (w, h) = png_to_rgba(open(logo_png, 'rb').read())
open(os.path.join(TD, 'new_logo_rgba.png'), 'wb').write(newpng)
LOGO_FILE = 0x471138; LOGO_FV = 0x4710c0
assert img[LOGO_FILE:LOGO_FILE + 16] == uuid.UUID('7BB28B99-61BB-11D5-9A5D-0090273FC14D').bytes_le
lraw = get_lzma_raw(LOGO_FILE)
assert lraw[3] == 0x19 and lraw[4:8] == b'\x89PNG'
l0 = int.from_bytes(lraw[0:3], 'little'); ui = lraw[(l0 + 3) & ~3:]
assert ui[3] == 0x15 and bytes(ui[4:22]).decode('utf-16le').rstrip('\0') == 'Logo.bmp'
sec = (4 + len(newpng)).to_bytes(3, 'little') + b'\x19' + newpng
sec += b'\0' * (-len(sec) % 4)
rebuild_lzma_file(LOGO_FILE, fv_end_of(LOGO_FV), sec + bytes(ui), 'logo3')
print(f'  logo: {w}x{h} RGBA PNG, {len(newpng)} bytes')

open(out, 'wb').write(img)
print('sha256', hashlib.sha256(img).hexdigest())
