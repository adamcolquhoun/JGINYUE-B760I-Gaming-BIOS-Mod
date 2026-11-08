# Changelog – JGINYUE B760I GAMING modded BIOS

Base image: JGINYUE **JYB7IG13** `BIOS.rom` (16 MiB full chip), SHA-256 `b04d9453812f3aca516f28f628672ae4bde5671558ab7971ffbd6542928180bd`.
Current release: **mod8** – `firmware/JYB7IG13_mod8.bin`, SHA-256 `60dd920842c96d7d1d46fe33d3f375767f7cec560d682efea3f13d57b1cab9ed`.

Offsets below are flash (image) offsets unless noted as *DXE+…* (offset inside the decompressed main DXE firmware volume, which is LZMA-compressed in FFS file `9E21FD93-9C72-4C15-8C4B-E77F1DB2D792` at flash `0x4D10C0`) or *module+…* (offset inside that PE/TE module).

---

## Complete list of alterations (mod8 vs. vendor JYB7IG13)

Changed flash areas: `0x400000–0x401FFF` (factory defaults), `0x471000–0x474FFF` (full-screen logo volume), `0x4D1000–0x80DFFF` (main DXE volume), `0xDF8000`, `0xF50000`, `0xF6B000` (one 4 KB block each, PEI code).
**Not changed:** flash descriptor (`0x0–0xFFF`), Intel ME region (`0x1000–0x3D8FFF`, ME 16.1.25.1917 as shipped), CPU microcode, Secure Boot keys (PK/KEK/db/dbx), SMBIOS data, the rest of the BIOS region.

### 1. Restart / reset fix

**Problem:** on this board a *hard reset* (writing `0x06` to the Reset Control Register, I/O port `0xCF9`) powers the system **off** instead of restarting it. Windows restarts (via the ACPI FADT reset register) and *Save Changes and Reset* in BIOS setup both used that value, so "Restart" left the PC switched off.

**Fix:** every `0x06` write to `0xCF9` became `0x0E` (full reset: SYS_RST + RST_CPU + FULL_RST), which this board handles correctly.

| # | Where | Location | Original → New |
|---|---|---|---|
| 1 | ACPI FADT `RESET_VALUE` (built by the ACPI DXE driver; `RESET_REG` = I/O `0xCF9`) | DXE, store `mov byte [rax+80h], 06h` | `06` → `0E` |
| 2 | ResetSystemRuntimeDxe – warm-reset path | module+`0xB19` (`mov al,06h`) | `06` → `0E` |
| 3 | SbRunSmm (SMM) | module+`0x1F95` | `06` → `0E` |
| 4 | CardCheckDxe | module+`0x611` | `06` → `0E` |
| 5 | CardCheckDxe | module+`0x6C3` | `06` → `0E` |
| 6 | PlatformInitAdvancedSmm (SMM) | module+`0xF7F` | `06` → `0E` |
| 7 | UsbRtSmm (SMM) | module+`0x1A222` | `06` → `0E` |
| 8 | ResetSystemPei (FV05, execute-in-place) – warm-reset path | flash `0xDF82EA` (pattern `b0 06 eb ba 55 8b ec`) | `06` → `0E` |
| 9 | ResetSystemPei (FV07 copy) – warm-reset path | flash `0xF505C2` | `06` → `0E` |
| 10 | PeiCore – `mov al,1; out 0CF9h,al; add al,5; out 0CF9h,al` | flash `0xF6BC7B` | `add al,05h` → `add al,0Dh` (writes `0x0E`) |

Deliberately left unchanged: one further CF9 write in PEI module `1BA0062E…` (FV07). The tested build already restarts correctly without changing it.

### 2. Factory defaults (StdDefaults NVRAM store)

These are the values used after a flash, CMOS clear or *Load Optimized Defaults*. Your own saved settings override them.

| Setting | Variable + offset | Flash offset | Vendor → Mod |
|---|---|---|---|
| Re-Size BAR Support | `Setup`+`0xC8C` | `0x400D44` | `0` Disabled → `1` **Enabled** |
| CSM Support | `Setup`+`0xCB7` | `0x400D6F` | `1` Enabled → `0` **Disabled** |
| Quiet Boot (full-screen logo) | `AMITSESetup`+`0x50` | `0x400E14` | `1` Enabled → `0` **Disabled** |
| Package C State Limit | `CpuSetup`+`0x4B` | `0x400E74` | `0` → `0xFF` **Auto** |
| Enable 8254 Clock Gate | `PchSetup`+`0x6BE` | `0x401E5D` | `1` Enabled → `2` **Enabled In Runtime and S3 Resume** |

The last one keeps the legacy 8254 timer clocked during POST so the PC speaker can sound (with the vendor default the speaker stays silent). The timer is still gated once the OS runs, so Modern Standby is unaffected.

### 3. Setup menu (IFR in the Setup driver + AMITSESetupData)

All edits are **in place and the same length**. AMI's setup browser uses a prebuilt index (`AMITSESetupData`, FFS `FE612B72-203C-47B1-8560-A66D946EB371`, itself LZMA-compressed inside the DXE volume) that stores the exact position of every setup control, so no referenced IFR opcode may move. After the edits, all 11,516 references were checked and still land on the same opcodes as before.

- **System Language hidden.** Its `SuppressIf { EqIdVal Q0x1239 == 0xFFFF }` became `SuppressIf { TRUE TRUE AND }` (same 6 bytes). Both of its defaults (standard + manufacturing) changed from `0` (zh-chs) to `1` (en-US) (mod8).
- **Quiet Boot hidden** (CheckBox question `0x10FA`, VarStore `AMITSESetup`+`0x50`, page *Boot*):
  - before: `[NumLock Default0][NumLock Default1][End]` `CheckBox` `[Default0=1][Default1=1][End]`
  - after: `[NumLock Default0 (padded to 8 bytes)][End][SuppressIf][TRUE]` `CheckBox` `[Default0=0 (padded to 10 bytes)][End][End]`
  - The CheckBox stays at the same offset. NumLock keeps its standard default; only its redundant manufacturing default was dropped to make room.
  - In AMITSESetupData the Quiet Boot control record's condition pointer was set to the new `SuppressIf` (`+0x28 = -4`, `+0x2C = 0xFFFFFFFF`), the same encoding the vendor uses for its own always-hidden options. 8 bytes changed.
- **Quiet Boot IFR defaults** `1` → `0`, matching the StdDefaults change.

### 4. Chinese language pack removed

The zh-chs HII string packages are replaced by inert, same-size GUID packages (zero-filled), so no other data moves:

| Module | Package size |
|---|---|
| Setup | 115,724 bytes (`0x1C40C`) |
| HddSmart | 74 bytes |
| PauseKey | 71 bytes |

Setup is English-only. The language list entry and AMITSE's own small zh-chs pack are left as they are; the System Language option is hidden (see §3).

### 5. Logos

- **Text POST screen logo** (FFS `63819805-67BB-46EF-AA8D-1524A19A01E4`, freeform, drawn by AMITSE): the 378×100 24-bit BMP "ami" logo was replaced by the **American Megatrends** logo, white text on black (`build/assets/text_screen_logo.bmp`, SHA-256 `6ebba7de…7046062`). Same size (113,654 bytes), in place.
- **Full-screen boot logo** (FFS `7BB28B99-61BB-11D5-9A5D-0090273FC14D`, own LZMA volume at `0x4710C0`): replaced with an AMI PNG in mod3. Because Quiet Boot is now always off this logo is **never displayed**; listed for completeness.

### 6. POST beep

A 103-byte routine (`build/beep.s`) was placed in unused space at the end of the `.text` section of **CapsuleRuntimeDxe** (RVA `0x1C70`, raw zero padding). The module's entry point was redirected to it (`AddressOfEntryPoint 0x1124 → 0x1C70`, `.text VirtualSize 0xC6F → 0xCD7`). It:

1. reads the CPU base frequency from `CPUID 0x16` (falls back to 2500 MHz);
2. programs 8254 counter 2 for a square wave with divisor `0x254` (≈ 2,002 Hz) and sets bits 0–1 of port `0x61` (speaker on);
3. waits ≈ 0.5 s using the TSC;
4. switches the speaker off and jumps to the original entry point.

It makes no calls and writes no memory except the stack. It needs a speaker on the SPEAKER header and the 8254 clock-gate default from §2.

### 7. Recompression

The main DXE volume and AMITSESetupData were recompressed with the 7-Zip **LZMA SDK** encoder (`lzma.exe e -d24`: no end marker, 16 MiB dictionary, props `5D 00 00 00 01`) – the format EDK2's `LzmaDecompress` expects. Every stream was checked by decoding it with the SDK's reference decoder (`LZMA_FINISH_END`), and the output matched the intended data byte for byte. FFS header checksums were recalculated. When AMITSESetupData got smaller, a standard FFS pad file fills the gap so the next file keeps its position. A full re-extraction of the image gives all 514 modules with no errors.

---

## Release history

All builds 2026-11. Each step was built from the previous image; scripts are in `build/`.

| Release | Changes | Tested on hardware |
|---|---|---|
| **mod8** | System Language defaults zh-chs → en-US (2 bytes, DXE+`0x3B98E0` / `0x3B98E7`). Matters only after *Load Defaults* on a fresh flash. | ✅ |
| **mod7** | Quiet Boot option hidden in place + AMITSESetupData record (§3). | ✅ |
| **mod6** | Text-screen logo: black background instead of white. | ✅ |
| **mod5** | POST beep (§6); 8254 clock-gate default → 2. | ✅ |
| **mod4** | All remaining CF9 `0x06` writes → `0x0E` (§1 rows 2–10) – fixes *Save Changes and Reset* in setup powering off; text-screen logo replaced. | ✅ (via mod5) |
| **mod3** | zh-chs packages removed (§4); System Language hidden; Quiet Boot default 0; full-screen logo replaced. | ✅ |
| **mod2** | FADT `RESET_VALUE` `0x06` → `0x0E` – fixes Windows *Restart* powering the PC off. | ✅ |
| **mod1** | Factory defaults: CSM off, Re-Size BAR on, Package C-State Auto. | ✅ |
