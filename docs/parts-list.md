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
| Amplifier | Stereo 2.1W Class D Audio Amplifier - TPA2012 | 1 | adafruit.com | **None working, 2026-11-18** - all three bought have failed: the original (5V from the Arduino) 2026-11-10, a replacement 2026-11-16, and the last spare 2026-11-18 (with all the protection parts below, no live plugging). Cause still unknown (log.md issue 26, 2026-11-18). Do not fit another into the current wiring until the cause is found. Was wired: fed from the XVF3800's 3.5mm jack, left channel only, right SD grounded. Left SD needs a pull-up (this board has none; a floating SD gives intermittent audio) - 1.2k to VDD on amp 3. Gain 12 dB (G0 high, G1 low), raised from the lowest for Kath. See spec 3.3. |
| Amp power supply | Buck converter module, make TBD | 1 | | Separate from the servo buck, fed from the 12V servo-controller supply. Trimmed to 4.8V before amp 3 was attached (amp 2: set to 4.5V, read 4.8V at the amp pins - the finicky trim pot or trimming unloaded, not drift, per Chip). Range check: TPA2012 2.5-5.5V, absolute max 6V). |
| Amp decoupling | 100uF electrolytic + 0.1uF ceramic | 1 each | on hand | Across the amp's VDD/GND, next to the pins (amp 2 had 0.22uF). |
| Amp VDD clamp | 5.6V zener (e.g. 1N4734A, 1W) | 1 | installed 2026-11-18 | Across amp VDD/GND, cathode to VDD, against supply overshoot. Not a 5V TVS (SMAJ5.0A etc.) - those don't conduct until ~6.4V and clamp near 9V. |
| Amp input series resistor | 560 ohm, 1/4W | 1 | installed 2026-11-18 | In the signal line at the amp input; limits fault current if the amp's ground floats during a live plug. Costs a little gain. |
| Amp proto board | Proto board | 1 | on hand | Carries the amp buck, amp, caps, and header; mounted in the 2026-11-16 enclosure bottom. |
| Amp header | 3-pin header + connector (12V, GND, signal) | 1 | on hand | Only mate or unmate with the amp's 12V unplugged - live plugging is the suspected cause of both amp failures. |
| Speaker |  40mm, 4Ω, 5W | 1 | adafruit.com | Product ID: 3968. |
| Pi-to-XVF3800 cable | USB A to Type C, 6in | 1 | Amazon | USB, kept short. |
| XVF3800-to-amp cable | single 22g wire | 1 | on hand | soldered to tip rung of 3.5mm connector, kept short; reaches the amp through the amp header's signal pin. Ground is shared through the header's GND. |

## Motion

| Part | Make / model | Qty | Source | Notes |
|---|---|---|---|---|
| Head servos (pitch, roll, yaw) | AGFRC B11DLS (metal-gear, digital; 9g class) | 3 | Amazon | Plus 1 spare (used for the 2026-10-14 bench noise test). |
| Beak servo | K-Power WK-P0025 (plastic gears) | 1 | | Replaced the GOTECK 2502MG (metal gears) 2026-11-07 for less noise. Powered through a series diode on its own supply line only (5.5V -> 4.9V), also for quieter running. Driven with plain `Servo`, not `ServoEasing` (spec 4.14). |
| Servo power supply | MP4560 DC-DC Buck Converter Module | 1 | Amazon | On continuously, driven from Arduino VIN pin (12v); servos attached at sketch startup. |
| Pi-to-Arduino cable | USB A to Micro USB, 6in | 1 | Amazon | USB serial. |
| Servo controller | SparkFun RedBoard Qwiic (Arduino Uno clone) | 1 | sparkfun.com | USB-serial chip is a CH340 (USB ID 1a86:7523), which shows as `/dev/ttyUSB0`. See spec 3.4. |
| Servo controller power supply | Generic 12v 1A wall wart | 1 | on hand | technically inadequate, should be 2A, but seems to be working fine, doesn't get hot. Also feeds the amp buck since 2026-11-16. |
| Servo controller proto board | Proto Shield Kit | 1 | Amazon | Used to mount buck converter and servo connector headers. 1 used from package of 9 |

## Structure

| Part | Make / model | Qty | Source | Notes |
|---|---|---|---|---|
| Statue and perch | 3D-printed, PLA filament, ~1.5kg | 1 | Printed | See spec 3.6. |
| Gimbal mechanism | 3D-printed, PLA filament, ~50g | 1 | Printed | Enables head pitch, roll, yaw |
| Electronics enclosure | 3D-printed, PLA filament, ~0.25kg | 1 | Printed | Rebuilt 2026-10-06. New bottom printed 2026-11-16 to hold the amp proto board. |
| Bird-to-base isolation mount | Sorbothane pads 1.5" x 0.25" (provisional on order) | 4 | Amazon | Temporarily a folded microfiber towel (a borrowed silicone mat was used for the 2026-10-14 tests). Pads due 2026-10-19. See spec 3.6 "Bird-to-base isolation mount". |
| Optional base ballast | Lead shot, 2 lb (~0.9 kg) | | On hand | Only if the base is reprinted. |
