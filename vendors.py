"""Thin per-vendor HTTP clients for home automation: Govee, Rachio, Tuya.

Only the calls Jack needs - list devices, read a device's functions, send
a command. No validation here: everything that decides *whether* a
command may be sent lives in home.py (spec 4.6). Keys come from the
environment (~/.bashrc) and are never printed.

stdlib only (urllib), same as list_devices.py which uses this module.
"""

import hashlib
import hmac
import json
import time
import urllib.parse
import urllib.request
import uuid

TIMEOUT_S = 15


def _request(method, url, headers, body=None):
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers = {**headers, "Content-Type": "application/json"}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
        raw = resp.read()
    return json.loads(raw) if raw.strip() else {}


def get_json(url, headers):
    return _request("GET", url, headers)


# --- Govee (Platform API, openapi.api.govee.com) ---------------------------

GOVEE_BASE = "https://openapi.api.govee.com/router/api/v1"


def govee_devices(key):
    return get_json(f"{GOVEE_BASE}/user/devices", {"Govee-API-Key": key}).get("data", [])


def govee_control(key, sku, device, cap_type, instance, value):
    """One capability command, e.g. ("devices.capabilities.on_off",
    "powerSwitch", 1). Govee reports failure in the body, not the status."""
    body = {"requestId": str(uuid.uuid4()),
            "payload": {"sku": sku, "device": device,
                        "capability": {"type": cap_type, "instance": instance,
                                       "value": value}}}
    data = _request("POST", f"{GOVEE_BASE}/device/control",
                    {"Govee-API-Key": key}, body)
    if data.get("code") != 200:
        raise ValueError(f"Govee error {data.get('code')}: {data.get('msg')}")


# --- Rachio (api.rach.io/1/public) ------------------------------------------

RACHIO_BASE = "https://api.rach.io/1/public"


def rachio_person(key):
    """The account's person record, including devices[] and their zones[]."""
    hdr = {"Authorization": f"Bearer {key}"}
    person_id = get_json(f"{RACHIO_BASE}/person/info", hdr)["id"]
    return get_json(f"{RACHIO_BASE}/person/{person_id}", hdr)


def rachio_start_zone(key, zone_id, seconds):
    # The run duration is enforced by the controller itself - a device-side
    # guard rail (allowlist doc): it stops on time even if the Pi dies.
    _request("PUT", f"{RACHIO_BASE}/zone/start",
             {"Authorization": f"Bearer {key}"},
             {"id": zone_id, "duration": int(seconds)})


def rachio_stop(key, device_id):
    _request("PUT", f"{RACHIO_BASE}/device/stop_water",
             {"Authorization": f"Bearer {key}"}, {"id": device_id})


# --- Tuya / Smart Life (Tuya IoT Platform OpenAPI) ---------------------------

TUYA_HOSTS = {"us": "openapi.tuyaus.com", "us-e": "openapi-ueaz.tuyaus.com",
              "eu": "openapi.tuyaeu.com", "eu-w": "openapi-weaz.tuyaeu.com",
              "in": "openapi.tuyain.com", "cn": "openapi.tuyacn.com"}


class TuyaCloud:
    """Minimal Tuya OpenAPI client: HMAC-SHA256 request signing."""

    def __init__(self, access_id, secret, region="us"):
        self.access_id, self.secret = access_id, secret.encode()
        self.host = TUYA_HOSTS[region]
        self.token = ""
        self.token = self.get("/v1.0/token?grant_type=1")["access_token"]

    def get(self, path_and_query):
        return self._call("GET", path_and_query)

    def post(self, path, body):
        return self._call("POST", path, body)

    def _call(self, method, path_and_query, body=None):
        t = str(int(time.time() * 1000))
        body_bytes = json.dumps(body).encode() if body is not None else b""
        # Tuya signs the path with its query keys sorted.
        path, _, query = path_and_query.partition("?")
        if query:
            path += "?" + "&".join(sorted(query.split("&")))
        string_to_sign = f"{method}\n{hashlib.sha256(body_bytes).hexdigest()}\n\n{path}"
        payload = self.access_id + self.token + t + string_to_sign
        sign = hmac.new(self.secret, payload.encode(),
                        hashlib.sha256).hexdigest().upper()
        hdr = {"client_id": self.access_id, "sign": sign, "t": t,
               "sign_method": "HMAC-SHA256"}
        if self.token:
            hdr["access_token"] = self.token
        data = _request(method, f"https://{self.host}{path}", hdr, body)
        if not data.get("success"):
            # Tuya reports errors in a 200 body; code 28841002 means the
            # IoT Core trial has lapsed (renew under Cloud > My Services).
            raise ValueError(f"Tuya error {data.get('code')}: {data.get('msg')}")
        return data["result"]

    def devices(self):
        """Every device from every app account linked to the project."""
        devices, last_row_key = [], ""
        while True:
            q = "size=50" + (f"&last_row_key={urllib.parse.quote(last_row_key)}"
                             if last_row_key else "")
            page = self.get(f"/v1.0/iot-01/associated-users/devices?{q}")
            devices.extend(page.get("devices", []))
            if not page.get("has_more"):
                return devices
            last_row_key = page.get("last_row_key", "")

    def functions(self, device_id):
        """{code: {"type": ..., "values": {...}}} for the device's commands."""
        funcs = self.get(f"/v1.0/devices/{device_id}/functions").get("functions", [])
        return {f["code"]: {"type": f["type"], "values": json.loads(f["values"] or "{}")}
                for f in funcs}

    def command(self, device_id, commands):
        """commands: [(code, value), ...] sent as one request."""
        self.post(f"/v1.0/devices/{device_id}/commands",
                  {"commands": [{"code": c, "value": v} for c, v in commands]})
