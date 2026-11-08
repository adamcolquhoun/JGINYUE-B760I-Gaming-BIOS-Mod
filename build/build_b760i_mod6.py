"""B760I mod6 = mod5 with the text-screen logo (FFS 63819805, 378x100 24bpp BMP) replaced by the black-background
version (white text, red triangle) used in the Snow Dream kit. Same size, in place.
python -I build_b760i_mod6.py <mod5.bin> <post_logo.bmp> <out.bin> <workdir>"""
import sys, os, struct, lzma, hashlib, uuid, subprocess
src, bmp_path, out, wd = sys.argv[1:5]
os.makedirs(wd, exist_ok=True)
img = bytearray(open(src, 'rb').read())
assert hashlib.sha256(img).hexdigest() == '692df85e6025980cf78d6c11598ae3e5def1e3187864354ea8a58ce534800d61', 'input is not mod5'
LZ = os.environ.get('LZMA_EXE', 'lzma.exe')   # 7-Zip LZMA SDK encoder (bin/x64/lzma.exe)
GUID_LZMA = uuid.UUID('EE4E5898-3914-4259-9D6E-DC7BD79403CF').bytes_le
new_bmp = open(bmp_path, 'rb').read()

FV = 0x470000; FILE = 0x4D10C0
fv_end = FV + struct.unpack_from('<Q', img, FV + 0x20)[0]
sec = FILE + 24; ss = int.from_bytes(img[sec:sec + 3], 'little'); doff = struct.unpack_from('<H', img, sec + 20)[0]
assert img[sec + 3] == 0x02 and img[sec + 4:sec + 20] == GUID_LZMA
raw = bytearray(lzma.decompress(bytes(img[sec + doff:sec + ss]), format=lzma.FORMAT_ALONE))

G = uuid.UUID('63819805-67BB-46EF-AA8D-1524A19A01E4').bytes_le
assert raw.count(G) == 1
fo = raw.index(G); assert fo % 8 == 0 and raw[fo + 0x12] == 0x02 and not raw[fo + 0x13] & 0x40
s = fo + 24
assert raw[s + 3] == 0x19 and int.from_bytes(raw[s:s + 3], 'little') == 4 + len(new_bmp)
assert raw[s + 4:s + 4 + 54] == new_bmp[:54], 'BMP header differs'
raw[s + 4:s + 4 + len(new_bmp)] = new_bmp
print(f'  text-screen logo replaced @ {s + 4:#x} ({len(new_bmp)} bytes)')

rp = os.path.join(wd, 'dxe6.raw'); cp = os.path.join(wd, 'dxe6.lzma')
open(rp, 'wb').write(raw)
if os.path.exists(cp): os.remove(cp)
subprocess.run([LZ, 'e', rp, cp, '-d24'], check=True, capture_output=True)
c = open(cp, 'rb').read()
assert c[:5] == bytes.fromhex('5d00000001') and struct.unpack_from('<Q', c, 5)[0] == len(raw)
section = bytearray(img[sec:sec + doff]); section[0:3] = (doff + len(c)).to_bytes(3, 'little'); section += c
h = bytearray(img[FILE:FILE + 24]); h[0x14:0x17] = (24 + len(section)).to_bytes(3, 'little')
assert not h[0x13] & 0x40
state = h[0x17]; h[0x10] = h[0x11] = h[0x17] = 0; h[0x10] = (-sum(h)) & 0xFF; h[0x11] = 0xAA; h[0x17] = state
newfile = bytes(h) + bytes(section)
old_end = FILE + 24 + ss
assert all(b == 0xFF for b in img[(old_end + 7) & ~7:fv_end]) and FILE + len(newfile) <= fv_end
img[FILE:fv_end] = newfile + b'\xff' * (fv_end - FILE - len(newfile))
print(f'  DXE file {ss + 24} -> {len(newfile)}, free after {fv_end - FILE - len(newfile)}')
open(out, 'wb').write(img)
open(os.path.join(wd, 'dxe6_expected.raw'), 'wb').write(raw)
print('sha256', hashlib.sha256(img).hexdigest())
