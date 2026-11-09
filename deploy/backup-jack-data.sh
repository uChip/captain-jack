#!/bin/sh
# Daily snapshot of Jack's live data (docs/specification.md section 4.17,
# "Backups"). Run by captain-jack-backup.timer; safe to run by hand:
#     deploy/backup-jack-data.sh
#
# Copies memory.md and voiceprints/ from ~/jack-data (JACK_DATA overrides)
# into backups/<date>_<time>/ - only when something changed since the
# newest snapshot - and keeps the newest KEEP (default 30). jack.env (the
# API keys) is deliberately left out. Each snapshot is built in a temp dir
# and renamed into place, so a power cut never leaves a half-copied one.
# Jack's own saves are atomic renames, so copying while he runs is safe.
set -eu
DATA=${JACK_DATA:-$HOME/jack-data}
BACKUPS=$DATA/backups
KEEP=${KEEP:-30}
STAMP=${BACKUP_STAMP:-$(date +%Y-%m-%d_%H%M%S)}   # override is for tests

mkdir -p "$BACKUPS"
rm -rf "$BACKUPS"/.tmp-*                # leftovers from an interrupted run
TMP=$(mktemp -d "$BACKUPS/.tmp-XXXXXX")
trap 'rm -rf "$TMP"' EXIT

found=0
for item in memory.md voiceprints; do
    if [ -e "$DATA/$item" ]; then
        cp -a "$DATA/$item" "$TMP/"
        found=1
    fi
done
[ "$found" = 1 ] || { echo "backup: nothing to back up in $DATA"; exit 1; }

latest=$(ls -1 "$BACKUPS" | grep -v '^\.' | sort | tail -n 1 || true)
if [ -n "$latest" ] && diff -r -q "$TMP" "$BACKUPS/$latest" >/dev/null 2>&1; then
    echo "backup: unchanged since $latest - no new snapshot"
else
    chmod 700 "$TMP"
    mv "$TMP" "$BACKUPS/$STAMP"
    echo "backup: wrote $BACKUPS/$STAMP"
fi

# Prune: keep the newest $KEEP snapshots (names sort by date).
ls -1 "$BACKUPS" | grep -v '^\.' | sort | head -n "-$KEEP" | while read -r old; do
    rm -rf "${BACKUPS:?}/$old"
    echo "backup: pruned $old"
done
