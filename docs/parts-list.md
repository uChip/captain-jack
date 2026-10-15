# Captain Jack Parts List

The exact make and model of every physical part in the bird. The
specification ([section 3](specification.md#3-hardware-architecture))
describes what each part does; this file records exactly which part is
installed, so a replacement or a comparison (e.g. a quieter servo) can
start from the real part. Update it whenever a part is swapped or added.

## Compute and audio

| Part | Make / model | Qty | Source | Notes |
|---|---|---|---|---|
| Single-board computer | Raspberry Pi 5 Model B, Rev 1.1, 8GB RAM | 1 | Amazon | Read from the board itself. Headless; see spec 3.1. |
| Pi storage | microSD, 128GB nominal (119GB usable) | 1 | Amazon | Make/model SanDisk Extreme. |
| Pi power supply | RasTech 5.1vdc 5A wall wart | 1 | Amazon | USB-C connector | 
| Pi power cabling | USB-C 90 Degree Angle Adapter | 1 | Amazon | Helps with cable routing |
| Pi cooling | GeeekPi Aluminum Heatsink Case | 1 | Amazon | Passive cooler / heatsink |
| Mic array / audio I/O | Seeed reSpeaker XVF3800 4-Mic Array (USB ID 2886:001a) | 1 | Amazon | Seeed's 16kHz "standard" firmware (fixed S16_LE, 16kHz, 2ch). See spec 3.2. |
| Amplifier | Stereo 2.1W Class D Audio Amplifier - TPA2012 | 1 | adafruit.com | Fed from the XVF3800's 3.5mm jack. 5v power fed from Arduino. Set to the lowest of its 4 strap-pin gain settings. See spec 3.3. |
| Speaker |  40mm, 4Ω, 5W | 1 | adafruit.com | Product ID: 3968. |
| Pi-to-XVF3800 cable | USB A to Type C, 6in | 1 | Amazon | USB, kept short. |
| XVF3800-to-amp cable | single 22g wire | 1 | on hand | soldered to tip rung of 3.5mm connector, kept short. |

## Motion

| Part | Make / model | Qty | Source | Notes |
|---|---|---|---|---|
| Head servos (pitch, roll, yaw) | AGFRC B11DLS (metal-gear, digital; 9g class) | 3 | Amazon | Plus 1 spare (used for the 2026-10-14 bench noise test). |
| Beak servo | GOTECK 2502MG (2g class) | 1 | Amazon | Driven with plain `Servo`, not `ServoEasing` (spec 4.14). |
| Servo power supply | MP4560 DC-DC Buck Converter Module | 1 | Amazon | On continuously, driven from Arduino VIN pin (12v); servos attached at sketch startup. |
| Pi-to-Arduino cable | USB A to Micro USB, 6in | 1 | Amazon | USB serial. |
| Servo controller | SparkFun RedBoard Qwiic (Arduino Uno clone) | 1 | sparkfun.com | USB-serial chip is a CH340 (USB ID 1a86:7523), which shows as `/dev/ttyUSB0`. See spec 3.4. |
| Servo controller power supply | Generic 12v 1A wall wart | 1 | on hand | technically inadequate, should be 2A, but seems to be working fine, doesn't get hot |
| Servo controller proto board | Proto Shield Kit | 1 | Amazon | Used to mount buck converter and servo connector headers. 1 used from package of 9 |

## Structure

| Part | Make / model | Qty | Source | Notes |
|---|---|---|---|---|
| Statue and perch | 3D-printed, PLA filament, ~1.5kg | 1 | Printed | See spec 3.6. |
| Gimbal mechanism | 3D-printed, PLA filament, ~50g | 1 | Printed | Enables head pitch, roll, yaw |
| Electronics enclosure | 3D-printed, PLA filament, ~0.25kg | 1 | Printed | Rebuilt 2026-10-06. |
| Bird-to-base isolation mount | Sorbothane pads 1.5" x 0.25" (provisional on order) | 4 | Amazon | Temporarily a folded microfiber towel (a borrowed silicone mat was used for the 2026-10-14 tests). Pads due 2026-10-19. See spec 3.6 "Bird-to-base isolation mount". |
| Optional base ballast | Lead shot, 2 lb (~0.9 kg) | | On hand | Only if the base is reprinted. |
