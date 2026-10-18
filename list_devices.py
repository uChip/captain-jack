"""List every device each home-automation vendor account knows about.

Read-only: only device-listing calls, never a control command. Prints one
table row per device (vendor, name, type, id, capabilities) so the result
can be checked against home-automation-device-list.csv and
docs/home-automation-allowlist.md.

Keys come from the environment (set in ~/.bashrc, never printed):
  GOVEE_API_KEY   - Govee Home app > Profile > Settings > Apply for API Key
  RACHIO_API_KEY  - Rachio app/web > Account Settings > Get API Key
A vendor whose key isn't set is skipped with a note.

    venv/bin/python list_devices.py [--csv FILE]
"""

import argparse
import csv
import json
import os
import sys
import urllib.error
import urllib.request

TIMEOUT_S = 15


def get_json(url, headers):
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
        return json.load(resp)


def govee_devices(key):
    # Govee's current "Platform API" (the older developer-api.govee.com v1
    # is deprecated). Capabilities list what each device can be told to do.
    data = get_json("https://openapi.api.govee.com/router/api/v1/user/devices",
                    {"Govee-API-Key": key})
    for d in data.get("data", []):
        caps = sorted({c.get("instance", "?") for c in d.get("capabilities", [])})
        yield {"vendor": "Govee", "name": d.get("deviceName", ""),
               "type": d.get("type", "").rsplit(".", 1)[-1],
               "model": d.get("sku", ""), "id": d.get("device", ""),
               "details": " ".join(caps)}


def rachio_devices(key):
    hdr = {"Authorization": f"Bearer {key}"}
    person_id = get_json("https://api.rach.io/1/public/person/info", hdr)["id"]
    person = get_json(f"https://api.rach.io/1/public/person/{person_id}", hdr)
    for d in person.get("devices", []):
        yield {"vendor": "Rachio", "name": d.get("name", ""),
               "type": "controller", "model": d.get("model", ""),
               "id": d.get("id", ""),
               "details": f"status={d.get('status', '?')} "
                          f"on={d.get('on', '?')}"}
        for z in sorted(d.get("zones", []), key=lambda z: z.get("zoneNumber", 0)):
            yield {"vendor": "Rachio",
                   "name": z.get("name", ""), "type": "zone",
                   "model": f"zone {z.get('zoneNumber', '?')}",
                   "id": z.get("id", ""),
                   "details": f"enabled={z.get('enabled', '?')}"}


VENDORS = [("Govee", "GOVEE_API_KEY", govee_devices),
           ("Rachio", "RACHIO_API_KEY", rachio_devices)]

FIELDS = ["vendor", "name", "type", "model", "id", "details"]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--csv", help="also write the table to this CSV file")
    args = ap.parse_args()

    rows = []
    for vendor, env, fn in VENDORS:
        key = os.environ.get(env)
        if not key:
            print(f"[{vendor}] skipped: {env} not set", file=sys.stderr)
            continue
        try:
            found = list(fn(key))
        except urllib.error.HTTPError as e:
            print(f"[{vendor}] HTTP {e.code} {e.reason}", file=sys.stderr)
            continue
        except (urllib.error.URLError, OSError, ValueError, KeyError) as e:
            print(f"[{vendor}] failed: {e}", file=sys.stderr)
            continue
        print(f"[{vendor}] {len(found)} device(s)", file=sys.stderr)
        rows.extend(found)

    widths = {f: max([len(f)] + [len(str(r[f])) for r in rows]) for f in FIELDS}
    print("  ".join(f.ljust(widths[f]) for f in FIELDS))
    for r in rows:
        print("  ".join(str(r[f]).ljust(widths[f]) for f in FIELDS))

    if args.csv:
        with open(args.csv, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=FIELDS)
            w.writeheader()
            w.writerows(rows)


if __name__ == "__main__":
    main()
