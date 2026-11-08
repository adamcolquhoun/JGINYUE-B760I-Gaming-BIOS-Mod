"""B760I mod5 = mod4 + boot beep (CapsuleRuntimeDxe entry stub) + StdDefaults 8254 clock gate 1 -> 2.
python -I build_b760i_mod5.py <mod4.bin> <out.bin> <workdir>"""
import sys, os, struct, lzma, hashlib, uuid, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import beepinject

src, out, wd = sys.argv[1:4]
os.makedirs(wd, exist_ok=True)
img = bytearray(open(src, 'rb').read())
print('input sha256', hashlib.sha256(img).hexdigest())
LZ = os.environ.get('LZMA_EXE', 'lzma.exe')   # 7-Zip LZMA SDK encoder (bin/x64/lzma.exe)
GUID_LZMA = uuid.UUID('EE4E5898-3914-4259-9D6E-DC7BD79403CF').bytes_le
PE = os.environ['EXTRACTED_BIOS'] + '/FV01_0470000_8C8CE578/002_9E21FD93-9C72-4C15-8C4B-E77F1DB2D792/fv1/157_CapsuleRuntimeDxe/1_PE32.efi'

beepinject.set_8254_default(img, 2)

FV = 0x470000; FILE = 0x4D10C0
fv_end = FV + struct.unpack_from('<Q', img, FV + 0x20)[0]
sec = FILE + 24; ss = int.from_bytes(img[sec:sec + 3], 'little'); doff = struct.unpack_from('<H', img, sec + 20)[0]
assert img[sec + 3] == 0x02 and img[sec + 4:sec + 20] == GUID_LZMA
raw = bytearray(lzma.decompress(bytes(img[sec + doff:sec + ss]), format=lzma.FORMAT_ALONE))
orig = bytes(raw)
beepinject.inject_beep(raw, PE)
ndiff = sum(1 for i in range(len(raw)) if raw[i] != orig[i]); print(f'  DXE bytes changed: {ndiff}')

rp = os.path.join(wd, 'dxe5.raw'); cp = os.path.join(wd, 'dxe5.lzma')
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
assert all(b == 0xFF for b in img[(old_end + 7) & ~7:fv_end])
assert FILE + len(newfile) <= fv_end
img[FILE:fv_end] = newfile + b'\xff' * (fv_end - FILE - len(newfile))
print(f'  DXE file {ss + 24} -> {len(newfile)}, free after {fv_end - FILE - len(newfile)}')
open(out, 'wb').write(img)
open(os.path.join(wd, 'dxe5_expected.raw'), 'wb').write(raw)
print('sha256', hashlib.sha256(img).hexdigest())
