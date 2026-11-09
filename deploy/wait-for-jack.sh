#!/bin/sh
# ExecStartPre for captain-jack.service: wait for Jack's hardware, then give
# the clock a short chance to sync before he picks his boot state by time
# of day. Never waits for the internet itself - Jack runs without it.
SERIAL=/dev/serial/by-id/usb-1a86_USB_Serial-if00-port0
DEVICE_WAIT_S=60
CLOCK_WAIT_S=45

i=0
until [ -e "$SERIAL" ] && grep -q "XVF3800" /proc/asound/cards; do
    i=$((i + 1))
    if [ "$i" -ge "$DEVICE_WAIT_S" ]; then
        [ -e "$SERIAL" ] || echo "wait-for-jack: no Arduino at $SERIAL"
        grep -q "XVF3800" /proc/asound/cards || echo "wait-for-jack: no XVF3800 sound card"
        exit 1
    fi
    sleep 1
done
echo "wait-for-jack: Arduino and XVF3800 present after ${i}s"

i=0
until [ "$(timedatectl show -p NTPSynchronized --value)" = "yes" ]; do
    i=$((i + 1))
    if [ "$i" -ge "$CLOCK_WAIT_S" ]; then
        echo "wait-for-jack: clock not synced after ${CLOCK_WAIT_S}s - starting anyway (boots Asleep)"
        exit 0
    fi
    sleep 1
done
echo "wait-for-jack: clock synced after ${i}s"
