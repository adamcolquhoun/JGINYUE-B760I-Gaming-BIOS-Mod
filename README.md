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
| **POST beep** | One ~2 kHz, ~0.5 s beep through the motherboard speaker header on every boot. |
| **Untouched** | Intel ME region, CPU microcode, Secure Boot keys, flash descriptor, everything else. |

Full byte-level details: **[CHANGELOG.md](CHANGELOG.md)**. How to flash: **[INSTALL.md](INSTALL.md)**.

## Files

| Path | What |
|---|---|
| `firmware/JYB7IG13_mod8.bin` | The modded 16 MiB full-chip image (descriptor + ME + BIOS). |
| `firmware/SHA256SUMS.txt` | `60dd920842c96d7d1d46fe33d3f375767f7cec560d682efea3f13d57b1cab9ed` |
| `tools/flash_bios.cmd` | Safe flashing script (hash, board and descriptor checks, full backup, then flash). |
| `tools/update_me.cmd` | Optional Intel ME 16.1.42.2872 update (Intel files not included – see INSTALL.md). |
| `build/` | The Python scripts that produced each step, the beep stub source (`beep.s`) and the logo assets. Reference only – see [build/README.md](build/README.md). |

## Status

Every step from mod1 through mod7 has been flashed and used daily on a real B760I GAMING. Restarts from Windows and from setup, the beep, the logo, CSM off, ReBAR on and the hidden options are all confirmed working.
mod8 only differs from mod7 in the default value of the hidden System Language option (English instead of Chinese). See CHANGELOG.md.

## Not affiliated

Not affiliated with or endorsed by JGINYUE, AMI or Intel. The firmware remains the property of its respective owners; this repository only documents and distributes a modification of the vendor's publicly released BIOS for owners of this board. "American Megatrends" and the AMI logo are trademarks of AMI.
