# Build scripts (reference)

These are the scripts that produced each release step, kept so every change can be audited. They are **not** a one-click build: each script checks the SHA-256 of its *input* (the previous step's image), and mod1/mod2 were done by hand (5 default bytes and one FADT byte; see CHANGELOG.md).

| Script | Input → output |
|---|---|
| `build_mod3.py` | mod2 → mod3 (zh-chs packages, System Language hidden, Quiet Boot default, full-screen logo) |
| `build_mod4.py` | mod3 → mod4 (CF9 reset sites, text-screen logo) |
| `build_b760i_mod5.py` | mod4 → mod5 (POST beep, 8254 clock-gate default) – uses `beepinject.py`, `beep.bin` |
| `build_b760i_mod6.py` | mod5 → mod6 (black-background text-screen logo `assets/text_screen_logo.bmp`) |
| `build_b760i_mod7.py` | mod6 → mod7 (Quiet Boot hidden in place) – uses `quietboot.py` |
| `build_b760i_mod8.py` | mod7 → mod8 (System Language defaults → English) |

Requirements: Python 3.10+, the 7-Zip **LZMA SDK** `lzma.exe` encoder (`set LZMA_EXE=…\lzma_sdk\bin\x64\lzma.exe`), and for mod3–mod5 an extraction of the vendor image (UEFITool/UEFIExtract-style folder tree) in `EXTRACTED_BIOS`.

`beep.s` is the source of `beep.bin` (GNU as, Intel syntax): `as beep.s -o beep.o && objcopy -O binary beep.o beep.bin`.
