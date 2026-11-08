# JGINYUE B760I GAMING – modded BIOS (JYB7IG13)

A modified version of JGINYUE's own **JYB7IG13** BIOS for the **JGINYUE B760I GAMING** (mini-ITX, LGA1700).
It fixes the vendor's restart bug, sets better factory defaults, removes the Chinese language pack, replaces the boot-screen logo and adds a POST beep.

> [!WARNING]
> **For the JGINYUE B760I GAMING only.** Flashing it to any other board — including the B760M Snow Dream, which uses the same AMI template — will brick that board.
> The flash script checks the BIOS version and the flash descriptor and refuses to run on anything else.
> Flashing firmware always carries risk. This board has **no USB BIOS Flashback / crisis recovery**: if a flash fails, recovery needs an SPI programmer (e.g. CH341A + SOIC-8 clip) and the backup the script makes. You flash at your own risk.

## What's changed (summary)

| Area | Change |
|---|---|
| **Restart bug** | Restarting (from Windows *or* from BIOS setup) used to power the PC off instead of rebooting. Every reset path now does a full reset (`0x0E` to port `0xCF9`) instead of the `0x06` hard reset this board turns into a power-off. |
| **Factory defaults** | CSM **off** (pure UEFI), Re-Size BAR **on**, Package C-State Limit **Auto**, Quiet Boot **off**, 8254 clock gate set so the PC speaker works. |
| **Setup menu** | *Quiet Boot* and *System Language* options hidden (always off / always English). |
| **Language** | Chinese (zh-chs) setup string packages removed; English only. |
| **Boot screen** | The full-screen vendor logo never shows; the classic text POST screen is used, with the American Megatrends logo (white on black) in place of the small "ami" logo. |
| **POST beep** | One ~1 kHz, ~0.5 s beep through the motherboard speaker header on every boot – AMI's per-USB-device beeps are disabled. Error beep codes still sound. |
| **Untouched** | Intel ME region, CPU microcode, Secure Boot keys, flash descriptor, everything else. |

Full byte-level details: **[CHANGELOG.md](CHANGELOG.md)**. How to flash: **[INSTALL.md](INSTALL.md)**.

## Base BIOS and microcode

Built on JGINYUE's **JYB7IG13** BIOS, the vendor's **0x12F microcode** release. 0x12F is Intel's 2025 update for the 13th/14th-gen Raptor Lake Vmin-shift instability. The mod does **not** touch the microcode: every update below is byte-identical to the vendor image.

| CPUID | CPUs | Revision | Date |
|---|---|---|---|
| `B0671` | 13th/14th-gen Core (Raptor Lake-S, B0) | **`0x12F`** | 2025-03-17 |
| `B06F2`, `B06F5` | 13th/14th-gen Core (Raptor Lake-S, C0/H0 – Alder Lake die) | `0x20` | 2022-03-31 |
| `B0670` | Raptor Lake-S (early) | `0x0E` | 2022-02-20 |
| `90672`, `90675` | 12th-gen Core (Alder Lake-S) | `0x36`, `0x1E` | 2024-02-22, 2022-02-21 |
| `90670`, `90671`, `90674` | Alder Lake (pre-production) | `0x19`, `0x1C`, `0x217` | 2020–2021 |

## Files

| Path | What |
|---|---|
| `firmware/JYB7IG13_mod9.bin` | The modded 16 MiB full-chip image (descriptor + ME + BIOS). |
| `firmware/SHA256SUMS.txt` | `6044b57613a2066ed8dbf8a3d44a4b1c2a87fe46cc9bc310f9b06f9c612d1638` |
| `tools/flash_bios.cmd` | Safe flashing script (hash, board and descriptor checks, full backup, then flash). |
| `tools/update_me.cmd` | Optional Intel ME 16.1.42.2872 update (Intel files not included – see INSTALL.md). |
| `build/` | The Python scripts that produced each step, the beep stub source (`beep.s`) and the logo assets. Reference only – see [build/README.md](build/README.md). |

## Status

Every release from mod1 through mod9 has been flashed and booted on a real B760I GAMING. Confirmed working: restarts from Windows and from setup, the single 1 kHz boot beep (no other beeps), the logo, CSM off, ReBAR on and the hidden options.

## Not affiliated

Not affiliated with or endorsed by JGINYUE, AMI or Intel. The firmware remains the property of its respective owners; this repository only documents and distributes a modification of the vendor's publicly released BIOS for owners of this board. "American Megatrends" and the AMI logo are trademarks of AMI.
