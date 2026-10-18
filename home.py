"""Jack's home-automation tools: the allowlist, enforced in code (spec 4.6).

Haiku proposes an action through a small fixed tool schema; this module
decides whether it's allowed and only then calls the vendor (vendors.py).
Same pattern as memory saving: model output is a request, never trusted
as-is.

What Jack may touch comes from Chip's inventory,
docs/home-automation-device-list.csv - only rows marked `Jack controls`
= yes. Its Type column is what a device *controls* (a light on an outlet
is a light), so "all the courtyard lights" is Type + Location. Rules from
docs/home-automation-allowlist.md enforced here:
  - only listed devices, only the actions their Type allows;
  - irrigation runs are capped at MAX_ZONE_MINUTES, enforced by the
    Rachio controller itself (a fixed run duration);
  - the fountain pump (Type "pump") can always be switched off, but only
    switched on in the turn right after Jack asked whether it has water
    in it - a dry pump burns out in minutes.

    venv/bin/python home.py     # print the inventory as Jack sees it
"""

import csv
import os
import re
import threading
import urllib.error
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

import vendors

INVENTORY_PATH = Path(__file__).parent / "docs" / "home-automation-device-list.csv"

# Longest single irrigation run Jack may start (allowlist: "e.g. 15-30 min,
# exact cap TBD"). Provisional - Chip to confirm.
MAX_ZONE_MINUTES = 15

NOTE_RE = re.compile(r"\s*<[^>]*>")  # "<disconnected>" etc. in the CSV

POWER_TYPES = {"light", "rope light", "dimmer", "fan", "outlet", "pump"}
DIM_TYPES = {"dimmer", "rope light"}
COLOR_TYPES = {"rope light"}
FAN_TYPES = {"fan"}
ZONE_TYPES = {"irrigation valve"}

VENDOR_KEYS = {"Govee": ("GOVEE_API_KEY",), "Rachio": ("RACHIO_API_KEY",),
               "SmartLife": ("TUYA_ACCESS_ID", "TUYA_ACCESS_SECRET")}

VENDOR_ERRORS = (urllib.error.URLError, OSError, ValueError, KeyError)


@dataclass
class Device:
    name: str         # what Jack and the household call it
    vendor: str       # Govee | SmartLife | Rachio (the CSV's Interface)
    vendor_name: str  # its name in the vendor's app (the CSV's Device Name)
    type: str
    location: str
    guarded: bool
    channel: str = ""  # which outlet of a multi-outlet plug
    ref: dict = field(default_factory=dict)  # vendor ids, filled on first use

    def can(self, action):
        return self.type in {"power": POWER_TYPES, "brightness": DIM_TYPES,
                             "color": COLOR_TYPES, "fan_speed": FAN_TYPES,
                             "zone": ZONE_TYPES}[action]


def load_inventory(path=INVENTORY_PATH):
    """Rows Jack controls, keyed by lowercase name. Raises on a duplicate
    name - two devices Jack can't tell apart is an inventory bug."""
    devices = {}
    with open(path, newline="") as fh:
        for row in csv.DictReader(fh):
            if row.get("Jack controls", "").strip().lower() != "yes":
                continue
            vendor_name = NOTE_RE.sub("", row["Device Name"]).strip()
            sub = NOTE_RE.sub("", row["Subdevice"]).strip()
            d = Device(name=sub or vendor_name, vendor=row["Interface"].strip(),
                       vendor_name=vendor_name, type=row["Type"].strip().lower(),
                       location=row["Location"].strip(),
                       guarded=row["Needs guard rails"].strip().lower() == "yes",
                       channel=row.get("Channel", "").strip())
            key = d.name.lower()
            if key in devices:
                raise ValueError(f"duplicate device name in inventory: {d.name!r}")
            devices[key] = d
    return devices


class VendorLink:
    """The real vendor calls, with ids looked up lazily on first use (so
    starting Jack never waits on, or fails because of, a vendor's cloud).
    Tests substitute a fake with the same methods."""

    def __init__(self, env=os.environ):
        self.env = env
        self._lock = threading.Lock()
        self._tuya = None
        self._tuya_ids = None   # vendor name (lowercase) -> device id
        self._tuya_funcs = {}   # device id -> functions()
        self._govee = None      # vendor name (lowercase) -> device dict
        self._rachio = None     # (controller id, {zone name lowercase: zone id})

    def available(self, vendor):
        return all(self.env.get(k) for k in VENDOR_KEYS.get(vendor, ("-",)))

    # -- lookups ---------------------------------------------------------

    def _tuya_device(self, d):
        with self._lock:
            if self._tuya is None:
                self._tuya = vendors.TuyaCloud(self.env["TUYA_ACCESS_ID"],
                                               self.env["TUYA_ACCESS_SECRET"],
                                               self.env.get("TUYA_REGION", "us"))
            if self._tuya_ids is None:
                self._tuya_ids = {x["name"].strip().lower(): x["id"]
                                  for x in self._tuya.devices()}
            dev_id = self._tuya_ids.get(d.vendor_name.lower())
            if dev_id is None:
                raise ValueError(f"Smart Life has no device named {d.vendor_name!r}")
            if dev_id not in self._tuya_funcs:
                self._tuya_funcs[dev_id] = self._tuya.functions(dev_id)
            return dev_id, self._tuya_funcs[dev_id]

    def _govee_device(self, d):
        with self._lock:
            if self._govee is None:
                self._govee = {x["deviceName"].strip().lower(): x
                               for x in vendors.govee_devices(self.env["GOVEE_API_KEY"])}
        g = self._govee.get(d.vendor_name.lower())
        if g is None:
            raise ValueError(f"Govee has no device named {d.vendor_name!r}")
        return g

    def _rachio_zone(self, d):
        with self._lock:
            if self._rachio is None:
                person = vendors.rachio_person(self.env["RACHIO_API_KEY"])
                ctrl = next(c for c in person["devices"]
                            if c["name"].strip().lower() == d.vendor_name.lower())
                self._rachio = (ctrl["id"], {z["name"].strip().lower(): z["id"]
                                             for z in ctrl["zones"]})
        zone_id = self._rachio[1].get(d.name.lower())
        if zone_id is None:
            raise ValueError(f"Rachio has no zone named {d.name!r}")
        return self._rachio[0], zone_id

    def forget(self, vendor):
        """Drop cached ids after a failure, so the next try looks again."""
        with self._lock:
            if vendor == "SmartLife":
                self._tuya, self._tuya_ids, self._tuya_funcs = None, None, {}
            elif vendor == "Govee":
                self._govee = None
            elif vendor == "Rachio":
                self._rachio = None

    # -- actions ---------------------------------------------------------

    def set_power(self, d, on):
        if d.vendor == "SmartLife":
            dev_id, funcs = self._tuya_device(d)
            code = d.channel or next((c for c in ("switch_led", "switch_fan", "switch_1")
                                      if c in funcs), None)
            if code not in funcs:
                raise ValueError(f"no power switch found on {d.vendor_name!r}")
            self._tuya.command(dev_id, [(code, bool(on))])
        elif d.vendor == "Govee":
            g = self._govee_device(d)
            if d.channel:   # one outlet of a multi-outlet plug
                cap = ("devices.capabilities.toggle", d.channel)
            elif any(c["instance"].startswith("socketToggle") for c in g["capabilities"]):
                raise ValueError(f"which outlet of {d.vendor_name!r} isn't mapped yet")
            else:
                cap = ("devices.capabilities.on_off", "powerSwitch")
            vendors.govee_control(self.env["GOVEE_API_KEY"], g["sku"], g["device"],
                                  *cap, 1 if on else 0)
        else:
            raise ValueError(f"can't switch {d.vendor} devices")

    def set_brightness(self, d, percent):
        if d.vendor == "SmartLife":
            dev_id, funcs = self._tuya_device(d)
            rng = funcs["bright_value"]["values"]
            lo, hi = rng.get("min", 10), rng.get("max", 1000)
            value = round(lo + (hi - lo) * (percent - 1) / 99)
            self._tuya.command(dev_id, [("switch_led", True), ("bright_value", value)])
        else:
            g = self._govee_device(d)
            vendors.govee_control(self.env["GOVEE_API_KEY"], g["sku"], g["device"],
                                  "devices.capabilities.range", "brightness", percent)

    def set_color(self, d, rgb):
        g = self._govee_device(d)
        r, gr, b = rgb
        vendors.govee_control(self.env["GOVEE_API_KEY"], g["sku"], g["device"],
                              "devices.capabilities.color_setting", "colorRgb",
                              (r << 16) | (gr << 8) | b)

    def set_fan_speed(self, d, speed):
        dev_id, funcs = self._tuya_device(d)
        levels = funcs["fan_speed_enum"]["values"]["range"]
        if not 1 <= speed <= len(levels):
            raise ValueError(f"{d.name} has speeds 1-{len(levels)}")
        self._tuya.command(dev_id, [("switch_fan", True),
                                    ("fan_speed_enum", levels[speed - 1])])

    def start_zone(self, d, minutes):
        _, zone_id = self._rachio_zone(d)
        vendors.rachio_start_zone(self.env["RACHIO_API_KEY"], zone_id, minutes * 60)

    def stop_watering(self, d):
        ctrl_id, _ = self._rachio_zone(d)
        vendors.rachio_stop(self.env["RACHIO_API_KEY"], ctrl_id)


def _devices_prop(names, what):
    return {"type": "array", "minItems": 1, "description": what,
            "items": {"type": "string", "enum": names}}


class Home:
    """The allowlist in code: tool schema for Haiku, validation, guard
    rails, then the vendor call. One instance per conversation process;
    begin_turn() is called once per user turn (the pump confirmation is
    counted in turns)."""

    def __init__(self, inventory=None, link=None, log=None):
        self.devices = inventory if inventory is not None else load_inventory()
        self.link = link or VendorLink()
        self.log = log or (lambda line: None)
        self.turn = 0
        self._pump_asked = {}  # device name -> turn Jack asked about water

    def begin_turn(self):
        self.turn += 1

    def _names(self, action):
        return sorted(d.name for d in self.devices.values() if d.can(action))

    # -- what Haiku sees ---------------------------------------------------

    def prompt_section(self):
        lines = ["", "---", "", "## Devices you control", "",
                 "Use your tools to act on these - only these. Each line is "
                 "name (what it controls, where). To act on a group, like "
                 "\"all the courtyard lights\", list every matching device in "
                 "one call. Only say something's done once the tool result "
                 "says so; if it failed, say so plainly.", ""]
        for d in sorted(self.devices.values(), key=lambda d: (d.location, d.name)):
            lines.append(f"- {d.name} ({d.type}, {d.location})")
        return "\n".join(lines) + "\n"

    def tools(self):
        tools = []
        if names := self._names("power"):
            tools.append({
                "name": "set_power",
                "description": "Switch devices on or off. Turning on the fountain "
                               "pump needs a yes from the person first - the tool will "
                               "say when to ask.",
                "input_schema": {"type": "object", "properties": {
                    "devices": _devices_prop(names, "Devices to switch."),
                    "on": {"type": "boolean"}},
                    "required": ["devices", "on"]}})
        if names := self._names("brightness"):
            tools.append({
                "name": "set_brightness",
                "description": "Set dimmable lights' brightness (also turns them on).",
                "input_schema": {"type": "object", "properties": {
                    "devices": _devices_prop(names, "Lights to dim or brighten."),
                    "percent": {"type": "integer", "minimum": 1, "maximum": 100}},
                    "required": ["devices", "percent"]}})
        if names := self._names("color"):
            tools.append({
                "name": "set_color",
                "description": "Set color-capable lights to an RGB color.",
                "input_schema": {"type": "object", "properties": {
                    "devices": _devices_prop(names, "Lights to color."),
                    "red": {"type": "integer", "minimum": 0, "maximum": 255},
                    "green": {"type": "integer", "minimum": 0, "maximum": 255},
                    "blue": {"type": "integer", "minimum": 0, "maximum": 255}},
                    "required": ["devices", "red", "green", "blue"]}})
        if names := self._names("fan_speed"):
            tools.append({
                "name": "set_fan_speed",
                "description": "Set ceiling fans' speed, 1 (slowest) to 4 (fastest); "
                               "also turns them on.",
                "input_schema": {"type": "object", "properties": {
                    "devices": _devices_prop(names, "Fans."),
                    "speed": {"type": "integer", "minimum": 1, "maximum": 4}},
                    "required": ["devices", "speed"]}})
        if names := self._names("zone"):
            tools.append({
                "name": "water_zone",
                "description": f"Run one irrigation zone for a set time, at most "
                               f"{MAX_ZONE_MINUTES} minutes. It stops by itself.",
                "input_schema": {"type": "object", "properties": {
                    "zone": {"type": "string", "enum": names},
                    "minutes": {"type": "integer", "minimum": 1,
                                "maximum": MAX_ZONE_MINUTES}},
                    "required": ["zone", "minutes"]}})
            tools.append({
                "name": "stop_watering",
                "description": "Stop any irrigation that's running now.",
                "input_schema": {"type": "object", "properties": {}}})
        return tools

    # -- running a tool call -------------------------------------------------

    def run_tool(self, name, args):
        """Validate and carry out one tool call. Returns (text, is_error):
        text is the tool_result Haiku sees, one line per device."""
        try:
            handler = getattr(self, f"_tool_{name}")
        except AttributeError:
            return f"Unknown tool {name!r}.", True
        try:
            text, is_error = handler(args if isinstance(args, dict) else {})
        except _Refused as e:
            text, is_error = str(e), True
        self.log(f"  [home] {name} {args} -> " + text.replace("\n", "; "))
        return text, is_error

    def _pick(self, names, action):
        if not isinstance(names, list) or not names:
            raise _Refused("No devices named.")
        picked = []
        for n in names:
            d = self.devices.get(str(n).strip().lower())
            if d is None:
                raise _Refused(f"{n!r} isn't a device you control.")
            if not d.can(action):
                raise _Refused(f"{d.name} can't do that.")
            picked.append(d)
        return picked

    def _int(self, args, key, lo, hi):
        v = args.get(key)
        if not isinstance(v, int) or isinstance(v, bool) or not lo <= v <= hi:
            raise _Refused(f"{key} must be a whole number from {lo} to {hi}.")
        return v

    def _each(self, devices, fn, done_word):
        """Run fn(device) for each device in parallel; one result line each."""
        def one(d):
            if not self.link.available(d.vendor):
                return f"{d.name}: failed - no {d.vendor} key set up."
            try:
                fn(d)
                return f"{d.name}: {done_word}."
            except VENDOR_ERRORS as e:
                self.link.forget(d.vendor)
                return f"{d.name}: failed - {e}."
        with ThreadPoolExecutor(max_workers=8) as pool:
            lines = list(pool.map(one, devices))
        failed = all(": failed" in line for line in lines)
        return "\n".join(lines), failed

    def _tool_set_power(self, args):
        devices = self._pick(args.get("devices"), "power")
        on = args.get("on")
        if not isinstance(on, bool):
            raise _Refused("on must be true or false.")
        held = []
        if on:
            for d in [d for d in devices if d.type == "pump"]:
                if self._pump_asked.pop(d.name, None) == self.turn - 1:
                    continue  # asked last turn, and Haiku heard a yes
                self._pump_asked[d.name] = self.turn
                devices.remove(d)
                held.append(f"{d.name}: NOT switched on. Ask whether the fountain has "
                            f"water in it. Only if their very next reply is yes, "
                            f"call set_power for it again.")
        text, failed = self._each(devices, lambda d: self.link.set_power(d, on),
                                  "on" if on else "off") if devices else ("", False)
        return "\n".join(x for x in [text, *held] if x), failed and not held

    def _tool_set_brightness(self, args):
        devices = self._pick(args.get("devices"), "brightness")
        pct = self._int(args, "percent", 1, 100)
        return self._each(devices, lambda d: self.link.set_brightness(d, pct),
                          f"brightness {pct}%")

    def _tool_set_color(self, args):
        devices = self._pick(args.get("devices"), "color")
        rgb = tuple(self._int(args, c, 0, 255) for c in ("red", "green", "blue"))
        return self._each(devices, lambda d: self.link.set_color(d, rgb), "color set")

    def _tool_set_fan_speed(self, args):
        devices = self._pick(args.get("devices"), "fan_speed")
        speed = self._int(args, "speed", 1, 4)
        return self._each(devices, lambda d: self.link.set_fan_speed(d, speed),
                          f"speed {speed}")

    def _tool_water_zone(self, args):
        [zone] = self._pick([args.get("zone")], "zone")
        minutes = self._int(args, "minutes", 1, MAX_ZONE_MINUTES)
        return self._each([zone], lambda d: self.link.start_zone(d, minutes),
                          f"watering for {minutes} minutes")

    def _tool_stop_watering(self, args):
        zones = [d for d in self.devices.values() if d.can("zone")]
        if not zones:
            raise _Refused("No irrigation to stop.")
        return self._each(zones[:1], self.link.stop_watering, "watering stopped")


class _Refused(Exception):
    """A tool call the allowlist rejects - reported to Haiku, never sent."""


if __name__ == "__main__":
    home = Home()
    print(home.prompt_section())
    for t in home.tools():
        print(t["name"], "-", t["description"])
