#!/usr/bin/env python3
"""
One-off diagnostic, round 2: holds distance CONSTANT (the same 5-degree
pitch swing as id-idle-breathing) and varies DURATION instead, to test
whether step count scales with duration (pointing at a real but coarse
fixed-time update interval - e.g. ~220ms/tick instead of the documented
20ms) or stays fixed regardless of duration (pointing at something else
entirely, like a small fixed-size waypoint table). Round 1 (varying
distance at fixed 2000ms duration) got the same step count either way -
expected if the tick is time-based, since duration was held constant
there; not yet conclusive on its own.

Run: venv/bin/python diagnose_easing.py
"""
import time

import serial

PORT = "/dev/ttyUSB0"
BAUD = 115200
RESTING = {"p": 35, "r": 30, "y": 70}
DURATIONS_MS = [500, 1500, 3000, 6000]
PAUSE = 3.0


def send(ser, cmd, label):
    print(f"\n[{time.strftime('%H:%M:%S')}] {label}")
    print(f"  -> {cmd}")
    ser.write(cmd.encode())
    time.sleep(0.05)
    if ser.in_waiting:
        print(f"  [arduino] {ser.read(ser.in_waiting).decode(errors='replace').strip()}")


def main():
    ser = serial.Serial(PORT, BAUD, timeout=0.2)
    print(f"Opened {PORT}; waiting for board startup self-test...")
    time.sleep(3.5)
    if ser.in_waiting:
        ser.read(ser.in_waiting)

    r, y, p_rest, p_up = RESTING["r"], RESTING["y"], RESTING["p"], RESTING["p"] + 5

    send(ser, f"p{p_rest}r{r}y{y}t500s", "Reset to resting")
    time.sleep(0.6 + PAUSE)

    pass_num = 0
    try:
        while True:
            pass_num += 1
            print(f"\n########## PASS {pass_num} ##########")
            for d in DURATIONS_MS:
                print(f"\n=== 5-degree move (35 -> 40), duration {d}ms - count steps ===")
                send(ser, f"p{p_up}r{r}y{y}t{d}s", f"UP over {d}ms")
                time.sleep(d / 1000.0 + PAUSE)
                send(ser, f"p{p_rest}r{r}y{y}t{d}s", f"DOWN over {d}ms")
                time.sleep(d / 1000.0 + PAUSE)
    except KeyboardInterrupt:
        print("\nInterrupted.")
    finally:
        send(ser, f"p{p_rest}r{r}y{y}t500s", "Final reset to resting")
        time.sleep(0.6)
        ser.close()


if __name__ == "__main__":
    main()
