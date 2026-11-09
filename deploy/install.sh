#!/bin/sh
# Install (or update) the boot service. Run from the repo:
#     sudo deploy/install.sh            # install + enable (starts at next boot)
#     sudo deploy/install.sh --now      # ...and start it now
# Needs ~/jack-live (with its venv) and ~/jack-data/jack.env first - see
# docs/specification.md section 4.17.
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
for f in /home/chips/jack-live/venv/bin/python /home/chips/jack-data/jack.env; do
    [ -e "$f" ] || { echo "missing $f - set it up first"; exit 1; }
done
install -m 644 "$HERE/captain-jack.service" /etc/systemd/system/captain-jack.service
install -d /etc/systemd/journald.conf.d
install -m 644 "$HERE/journald-captain-jack.conf" /etc/systemd/journald.conf.d/50-captain-jack.conf
systemctl restart systemd-journald
systemctl daemon-reload
if [ "$1" = "--now" ]; then
    systemctl enable --now captain-jack
else
    systemctl enable captain-jack
fi
systemctl --no-pager status captain-jack | head -5 || true
