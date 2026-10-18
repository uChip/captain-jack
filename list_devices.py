"""List every device each home-automation vendor account knows about.

Read-only: only device-listing calls, never a control command. Prints one
table row per device (vendor, name, type, id, capabilities) so the result
can be checked against home-automation-device-list.csv and
docs/home-automation-allowlist.md.

Keys come from the environment (set in ~/.bashrc, never printed):
  GOVEE_API_KEY   - Govee Home app > Profile > Settings > Apply for API Key
  RACHIO_API_KEY  - Rachio app/web > Account Settings > Get API Key
  TUYA_ACCESS_ID, TUYA_ACCESS_SECRET - Tuya IoT Platform cloud project
                    Overview tab (Smart Life account linked to the project)
  TUYA_REGION     - optional data center: us (default), us-e, eu, eu-w, in, cn
A vendor whose key isn't set is skipped with a note.

    venv/bin/python list_devices.py [--csv FILE]
"""

import argparse
import csv
import hashlib
import hmac
import json
import os
import sys
import time
import urllib.error
import urllib.parse
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


TUYA_HOSTS = {"us": "openapi.tuyaus.com", "us-e": "openapi-ueaz.tuyaus.com",
              "eu": "openapi.tuyaeu.com", "eu-w": "openapi-weaz.tuyaeu.com",
              "in": "openapi.tuyain.com", "cn": "openapi.tuyacn.com"}

# Tuya category codes -> plain words (the ones a Smart Life house is
# likely to have; anything else prints as its raw code).
TUYA_CATEGORIES = {"kg": "switch", "tgkg": "dimmer", "tgq": "dimmer", "tdq": "breaker",
                   "dj": "light", "dd": "light strip", "fs": "fan",
                   "fskg": "fan switch", "cz": "outlet", "pc": "power strip",
                   "wk": "thermostat", "ggq": "irrigation"}


class TuyaCloud:
    """Minimal Tuya OpenAPI client: HMAC-SHA256 request signing, GET only."""

    def __init__(self, access_id, secret, region):
        self.access_id, self.secret = access_id, secret.encode()
        self.host = TUYA_HOSTS[region]
        self.token = ""
        self.token = self.get("/v1.0/token?grant_type=1")["access_token"]

    def get(self, path_and_query):
        t = str(int(time.time() * 1000))
        empty_body_sha = hashlib.sha256(b"").hexdigest()
        # Tuya signs the path with its query keys sorted.
        path, _, query = path_and_query.partition("?")
        if query:
            path += "?" + "&".join(sorted(query.split("&")))
        string_to_sign = f"GET\n{empty_body_sha}\n\n{path}"
        payload = self.access_id + self.token + t + string_to_sign
        sign = hmac.new(self.secret, payload.encode(),
                        hashlib.sha256).hexdigest().upper()
        hdr = {"client_id": self.access_id, "sign": sign, "t": t,
               "sign_method": "HMAC-SHA256"}
        if self.token:
            hdr["access_token"] = self.token
        data = get_json(f"https://{self.host}{path}", hdr)
        if not data.get("success"):
            # Tuya reports errors in a 200 body; code 28841002 means the
            # IoT Core trial has lapsed (renew under Cloud > My Services).
            raise ValueError(f"Tuya error {data.get('code')}: {data.get('msg')}")
        return data["result"]


def tuya_devices(_key):
    cloud = TuyaCloud(os.environ["TUYA_ACCESS_ID"],
                      os.environ["TUYA_ACCESS_SECRET"],
                      os.environ.get("TUYA_REGION", "us"))
    # Devices from every app account linked to the project, paged.
    devices, last_row_key = [], ""
    while True:
        q = "size=50" + (f"&last_row_key={urllib.parse.quote(last_row_key)}"
                         if last_row_key else "")
        page = cloud.get(f"/v1.0/iot-01/associated-users/devices?{q}")
        devices.extend(page.get("devices", []))
        if not page.get("has_more"):
            break
        last_row_key = page.get("last_row_key", "")
    for d in sorted(devices, key=lambda d: d.get("name", "")):
        try:
            funcs = cloud.get(f"/v1.0/devices/{d['id']}/functions")
            codes = " ".join(f["code"] for f in funcs.get("functions", []))
        except (urllib.error.URLError, ValueError) as e:
            codes = f"(functions unavailable: {e})"
        cat = d.get("category", "")
        yield {"vendor": "SmartLife", "name": d.get("name", ""),
               "type": TUYA_CATEGORIES.get(cat, cat),
               "model": d.get("product_name", ""), "id": d.get("id", ""),
               "details": f"online={d.get('online', '?')} {codes}"}


VENDORS = [("Govee", "GOVEE_API_KEY", govee_devices),
           ("Rachio", "RACHIO_API_KEY", rachio_devices),
           ("SmartLife", "TUYA_ACCESS_SECRET", tuya_devices)]

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
