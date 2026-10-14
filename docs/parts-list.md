# Captain Jack Parts List

The exact make and model of every physical part in the bird. The
specification ([section 3](specification.md#3-hardware-architecture))
describes what each part does; this file records exactly which part is
installed, so a replacement or a comparison (e.g. a quieter servo) can
start from the real part. Update it whenever a part is swapped or added.

Entries marked *TBD* are for Chip to fill in.

## Compute and audio

| Part | Make / model | Qty | Source | Notes |
|---|---|---|---|---|
| Single-board computer | Raspberry Pi 5 Model B, Rev 1.1, 8GB RAM | 1 | *TBD* | Read from the board itself. Headless; see spec 3.1. |
| Pi storage | microSD, 128GB nominal (119GB usable) | 1 | *TBD* | Make/model *TBD*. |
| Pi power supply | *TBD* | 1 | *TBD* | |
| Pi cooling | *TBD* | | *TBD* | Active cooler / heatsink, if any. |
| Mic array / audio I/O | Seeed reSpeaker XVF3800 4-Mic Array (USB ID 2886:001a) | 1 | *TBD* | Seeed's 16kHz "standard" firmware (fixed S16_LE, 16kHz, 2ch). See spec 3.2. |
| Amplifier | *TBD* | 1 | *TBD* | Fed from the XVF3800's 3.5mm jack. Set to the lowest of its 4 strap-pin gain settings. See spec 3.3. |
| Speaker | *TBD* (40mm, 4Ω, 5W) | 1 | *TBD* | Make/model *TBD*. |
| Pi-to-XVF3800 cable | *TBD* | 1 | *TBD* | USB, kept short. |
| XVF3800-to-amp cable | *TBD* | 1 | *TBD* | 3.5mm, kept short. |

## Motion

| Part | Make / model | Qty | Source | Notes |
|---|---|---|---|---|
| Head servos (pitch, roll, yaw) | AGFRC B11DLS (metal-gear, digital; 9g class) | 3 | *TBD* | Plus 1 spare (used for the 2026-10-14 bench noise test). |
| Beak servo | *TBD* (2g class) | 1 | *TBD* | Driven with plain `Servo`, not `ServoEasing` (spec 4.14). |
| Servo power supply | *TBD* | 1 | *TBD* | On continuously; servos attached at sketch startup. |
| Pi-to-Arduino cable | *TBD* | 1 | *TBD* | USB serial. |

## Structure

| Part | Make / model | Qty | Source | Notes |
|---|---|---|---|---|
| Statue and perch | 3D-printed, filament *TBD* | 1 | Printed | See spec 3.6. |
| Electronics enclosure | 3D-printed, filament *TBD* | 1 | Printed | Rebuilt 2026-10-06. |
| Bird-to-base isolation mount | Not chosen yet | | | Temporarily a silicone mat. See spec 3.6 "Bird-to-base isolation mount". |
| Optional base ballast | Lead shot, 2 lb (~0.9 kg) | | On hand | Only if the base is reprinted. |

## To fill in

| Part | Make / model | Qty | Source | Notes |
|---|---|---|---|---|
| Servo controller | *TBD* (Arduino Uno clone) | 1 | *TBD* | USB-serial chip is a CH340 (USB ID 1a86:7523), which shows as `/dev/ttyUSB0`. See spec 3.4. |
