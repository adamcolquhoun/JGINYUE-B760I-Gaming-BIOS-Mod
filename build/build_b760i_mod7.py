"""B760I mod7 = mod6 + Quiet Boot option hidden in place (quietboot.py: IFR SuppressIf TRUE before the CheckBox,
no referenced opcode moves; AMITSESetupData record conditional -4).
python -I build_b760i_mod7.py <mod6.bin> <out.bin> <workdir>"""
import sys, os, struct, lzma, hashlib, uuid, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import quietboot
src, out, wd = sys.argv[1:4]
os.makedirs(wd, exist_ok=True)
img = bytearray(open(src, 'rb').read())
assert hashlib.sha256(img).hexdigest() == '6051c4080aa4d0a831448dab7424c2285dc8ace7a576f71993929faa5d62b0b7', 'input is not mod6'
GUID_LZMA = uuid.UUID('EE4E5898-3914-4259-9D6E-DC7BD79403CF').bytes_le

FV = 0x470000; FILE = 0x4D10C0
fv_end = FV + struct.unpack_from('<Q', img, FV + 0x20)[0]
sec = FILE + 24; ss = int.from_bytes(img[sec:sec + 3], 'little'); doff = struct.unpack_from('<H', img, sec + 20)[0]
assert img[sec + 3] == 0x02 and img[sec + 4:sec + 20] == GUID_LZMA
raw = bytearray(lzma.decompress(bytes(img[sec + doff:sec + ss]), format=lzma.FORMAT_ALONE))
quietboot.hide_quiet_boot(raw, wd)

c = quietboot._sdk(bytes(raw), wd, 'dxe7')
section = bytearray(img[sec:sec + doff]); section[0:3] = (doff + len(c)).to_bytes(3, 'little'); section += c
newfile = quietboot._hdr(img[FILE:FILE + 24], 24 + len(section)) + bytes(section)
old_end = FILE + 24 + ss
assert all(b == 0xFF for b in img[(old_end + 7) & ~7:fv_end]) and FILE + len(newfile) <= fv_end
img[FILE:fv_end] = newfile + b'\xff' * (fv_end - FILE - len(newfile))
print(f'  DXE file {ss + 24} -> {len(newfile)}, free after {fv_end - FILE - len(newfile)}')
open(out, 'wb').write(img)
open(os.path.join(wd, 'dxe7_expected.raw'), 'wb').write(raw)
print('sha256', hashlib.sha256(img).hexdigest())
