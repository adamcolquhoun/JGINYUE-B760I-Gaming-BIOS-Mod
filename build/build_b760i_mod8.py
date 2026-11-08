"""B760I mod8 = mod7 + hidden System Language option defaults 0 (zh-chs) -> 1 (en-US), same as the Snow Dream kit.
Two DefaultStore values inside the OneOf, same size, nothing moves.
python -I build_b760i_mod8.py <mod7.bin> <out.bin> <workdir>"""
import sys, os, struct, lzma, hashlib, uuid, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import quietboot
src, out, wd = sys.argv[1:4]
os.makedirs(wd, exist_ok=True)
img = bytearray(open(src, 'rb').read())
assert hashlib.sha256(img).hexdigest() == 'c066626b7f27863cf5cb9396890ec0921e3e5e6702b75673284ad56b862076d1', 'input is not mod7'
GUID_LZMA = uuid.UUID('EE4E5898-3914-4259-9D6E-DC7BD79403CF').bytes_le

FV = 0x470000; FILE = 0x4D10C0
fv_end = FV + struct.unpack_from('<Q', img, FV + 0x20)[0]
sec = FILE + 24; ss = int.from_bytes(img[sec:sec + 3], 'little'); doff = struct.unpack_from('<H', img, sec + 20)[0]
assert img[sec + 3] == 0x02 and img[sec + 4:sec + 20] == GUID_LZMA
raw = bytearray(lzma.decompress(bytes(img[sec + doff:sec + ss]), format=lzma.FORMAT_ALONE))

hits = [m.start() for m in re.finditer(rb'\x0a\x82\x46\x02\x46\x02\x15\x02\x05\x94', raw)]
assert len(hits) == 1, hits
oneof = hits[0] + 8; L = raw[oneof + 1] & 0x7F
assert struct.unpack_from('<H', raw, oneof + 6)[0] == 0x0008          # System Language question
p = oneof + L; seen = 0
while raw[p] != 0x29:
    op, ln = raw[p], raw[p + 1] & 0x7F
    if op == 0x5B:
        did, ty = struct.unpack_from('<HB', raw, p + 2); assert ty == 1 and ln == 7
        assert raw[p + 5:p + 7] == b'\x00\x00'
        raw[p + 5:p + 7] = b'\x01\x00'; seen += 1
        print(f'  System Language default id={did}: 0 (zh-chs) -> 1 (en-US) @ {p:#x}')
    p += ln
assert seen == 2

c = quietboot._sdk(bytes(raw), wd, 'dxe8')
section = bytearray(img[sec:sec + doff]); section[0:3] = (doff + len(c)).to_bytes(3, 'little'); section += c
newfile = quietboot._hdr(img[FILE:FILE + 24], 24 + len(section)) + bytes(section)
old_end = FILE + 24 + ss
assert all(b == 0xFF for b in img[(old_end + 7) & ~7:fv_end]) and FILE + len(newfile) <= fv_end
img[FILE:fv_end] = newfile + b'\xff' * (fv_end - FILE - len(newfile))
print(f'  DXE file {ss + 24} -> {len(newfile)}, free after {fv_end - FILE - len(newfile)}')
open(out, 'wb').write(img)
open(os.path.join(wd, 'dxe8_expected.raw'), 'wb').write(raw)
print('sha256', hashlib.sha256(img).hexdigest())
