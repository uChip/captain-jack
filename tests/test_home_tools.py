"""Re-runnable test for docs/tests.md: "Home-automation tools".

No network, no devices: a fake vendor link records what *would* have been
sent. Verifies home.py enforces docs/home-automation-allowlist.md in code,
and orchestrate.py's tool round trip:
  - the real inventory CSV loads only `Jack controls = yes` rows (ecobee,
    Office Outlet, the broken outdoor-plug Switch 1, and the disconnected
    Govee lights are absent), with unique names;
  - unknown devices, actions a device's Type doesn't allow, out-of-range
    or wrong-typed numbers, and over-cap irrigation are refused without
    any vendor call;
  - the fountain pump: off always goes straight through; on is held and
    Jack told to ask, and only goes through in the very next turn - a
    later turn, or a fresh first request, asks again; the rest of a
    group still switches meanwhile;
  - vendor failures come back as "failed" lines, never as success;
  - take_turn()/stream_turn() with home: run the tool, send the result
    back, speak text from both rounds (the lead-in before the tool call
    as soon as Haiku pauses for it), parse tags from the final part,
    keep a valid history, and roll it back on an API error mid-loop.

Run: venv/bin/python tests/test_home_tools.py
"""

import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parent.parent))

import anthropic  # noqa: E402

import home as home_mod  # noqa: E402
from home import Home, load_inventory  # noqa: E402
from orchestrate import MAX_TOOL_ROUNDS, stream_turn, take_turn  # noqa: E402

MEMORY_SRC = Path(__file__).parent.parent / "memory"


class FakeLink:
    def __init__(self, fail=()):
        self.calls = []
        self.fail = set(fail)

    def available(self, vendor):
        return vendor != "NoKey"

    def forget(self, vendor):
        pass

    def _do(self, action, d, *args):
        if d.name in self.fail:
            raise ValueError("device is offline")
        self.calls.append((action, d.name, *args))

    def set_power(self, d, on):
        self._do("power", d, on)

    def set_brightness(self, d, pct):
        self._do("brightness", d, pct)

    def set_color(self, d, rgb):
        self._do("color", d, rgb)

    def set_fan_speed(self, d, speed):
        self._do("fan", d, speed)

    def start_zone(self, d, minutes):
        self._do("zone", d, minutes)

    def stop_watering(self, d):
        self._do("stop", d)


def check_inventory():
    inv = load_inventory()
    names = {d.name for d in inv.values()}
    for gone in ("Office Outlet", "Cabinet Lights", "Living therm", "Casita",
                 "Bedrooms", "Bedroom"):
        assert gone not in names, gone
    assert not any(n.startswith("Switch 1") for n in names)
    assert not any(d.vendor == "Ecobee" for d in inv.values())
    # The Smart Life dimmer "Patio Lights" stays; the Govee one is excluded.
    assert inv["patio lights"].vendor == "SmartLife"
    pump = inv["courtyard fountain"]
    assert pump.type == "pump" and pump.guarded and pump.channel == "switch_3"
    assert inv["courtyard light one"].channel == "switch_2"
    assert {d.name for d in inv.values() if d.can("zone")} == {"Courtyard", "Back & Side Shrubs"}

    tools = {t["name"] for t in Home(inv, FakeLink()).tools()}
    assert tools == {"set_power", "set_brightness", "set_color", "set_fan_speed",
                     "water_zone", "stop_watering"}, tools

    # Duplicate names are an inventory bug, refused at load.
    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as fh:
        fh.write("Interface,Device Name,Subdevice,Type,Location,Needs guard rails,Jack controls\n"
                 "SmartLife,Lamp,,light,Den,,yes\nGovee,lamp,,light,Den,,yes\n")
    try:
        load_inventory(fh.name)
        raise AssertionError("duplicate name accepted")
    except ValueError:
        pass


def check_refusals():
    link = FakeLink()
    h = Home(load_inventory(), link)
    h.begin_turn()
    bad = [
        ("set_power", {"devices": ["Office Outlet"], "on": True}),       # excluded
        ("set_power", {"devices": ["Garage"], "on": True}),              # not a device
        ("set_power", {"devices": [], "on": True}),
        ("set_power", {"devices": ["Office Light"], "on": "yes"}),
        ("set_brightness", {"devices": ["Office Fan"], "percent": 50}),  # fan isn't dimmable
        ("set_brightness", {"devices": ["Kitchen Lights"], "percent": 0}),
        ("set_brightness", {"devices": ["Kitchen Lights"], "percent": 50.5}),
        ("set_brightness", {"devices": ["Kitchen Lights"], "percent": True}),
        ("set_color", {"devices": ["Kitchen Lights"], "red": 255, "green": 0, "blue": 0}),
        ("set_color", {"devices": ["Rope Light"], "red": 256, "green": 0, "blue": 0}),
        ("set_fan_speed", {"devices": ["Office Fan"], "speed": 5}),
        ("water_zone", {"zone": "Courtyard", "minutes": home_mod.MAX_ZONE_MINUTES + 1}),
        ("water_zone", {"zone": "Fountain", "minutes": 5}),              # unwired zone
        ("water_zone", {"zone": "Office Light", "minutes": 5}),
        ("open_garage", {}),
    ]
    for name, args in bad:
        text, err = h.run_tool(name, args)
        assert err, (name, args, text)
    assert link.calls == [], link.calls

    ok = [
        ("set_power", {"devices": ["office light", "Patio Fan"], "on": False}),
        ("set_brightness", {"devices": ["Kitchen Lights", "Rope Light"], "percent": 40}),
        ("set_color", {"devices": ["Office Strip Lights"], "red": 255, "green": 0, "blue": 0}),
        ("set_fan_speed", {"devices": ["Casita Fan"], "speed": 2}),
        ("water_zone", {"zone": "Back & Side Shrubs", "minutes": home_mod.MAX_ZONE_MINUTES}),
        ("stop_watering", {}),
    ]
    for name, args in ok:
        text, err = h.run_tool(name, args)
        assert not err and "failed" not in text, (name, text)
    assert ("power", "Office Light", False) in link.calls
    assert ("zone", "Back & Side Shrubs", home_mod.MAX_ZONE_MINUTES) in link.calls
    assert ("color", "Office Strip Lights", (255, 0, 0)) in link.calls


def check_pump():
    link = FakeLink()
    h = Home(load_inventory(), link)
    pump_on = {"devices": ["Courtyard Fountain", "Courtyard Light One"], "on": True}

    h.begin_turn()                                   # "turn on the fountain and its light"
    text, err = h.run_tool("set_power", pump_on)
    assert not err and "NOT switched on" in text and "Ask" in text, text
    assert link.calls == [("power", "Courtyard Light One", True)], link.calls

    h.begin_turn()                                   # "yes, it's full"
    text, err = h.run_tool("set_power", {"devices": ["Courtyard Fountain"], "on": True})
    assert not err and "Courtyard Fountain: on." in text, text
    assert link.calls[-1] == ("power", "Courtyard Fountain", True)

    # Confirmation is used up: a fresh request asks again.
    h.begin_turn()
    text, _ = h.run_tool("set_power", {"devices": ["Courtyard Fountain"], "on": True})
    assert "NOT switched on" in text
    # ...and a yes two turns later is too late - asks again.
    h.begin_turn()
    h.begin_turn()
    text, _ = h.run_tool("set_power", {"devices": ["Courtyard Fountain"], "on": True})
    assert "NOT switched on" in text
    n = len(link.calls)

    # Off never needs asking.
    h.begin_turn()
    text, err = h.run_tool("set_power", {"devices": ["Courtyard Fountain"], "on": False})
    assert not err and link.calls[n:] == [("power", "Courtyard Fountain", False)]


def check_failures():
    link = FakeLink(fail={"Office Light"})
    h = Home(load_inventory(), link)
    h.begin_turn()
    text, err = h.run_tool("set_power", {"devices": ["Office Light", "Office Fan"], "on": True})
    assert "Office Light: failed - device is offline." in text and "Office Fan: on." in text, text
    assert not err  # partly worked
    text, err = h.run_tool("set_power", {"devices": ["Office Light"], "on": True})
    assert err and "failed" in text

    inv = load_inventory()
    inv["office fan"].vendor = "NoKey"
    text, err = Home(inv, FakeLink()).run_tool("set_power", {"devices": ["Office Fan"], "on": True})
    assert err and "no NoKey key" in text, text


# --- orchestrate.py's tool round trip -------------------------------------

def text_block(t):
    return SimpleNamespace(type="text", text=t)


def tool_block(id_, name, inp):
    return SimpleNamespace(type="tool_use", id=id_, name=name, input=inp)


class FakeStream:
    def __init__(self, msg):
        self.msg = msg

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    @property
    def text_stream(self):
        for b in self.msg.content:
            if b.type == "text":
                yield from b.text  # one character at a time

    def get_final_message(self):
        return self.msg


class FakeClient:
    """Plays back a scripted list of messages; raises at index fail_at."""

    def __init__(self, script, fail_at=None):
        self.script = list(script)
        self.fail_at = fail_at
        self.requests = []
        self.messages = SimpleNamespace(create=self._create, stream=self._stream)

    def _next(self, kw):
        self.requests.append({**kw, "messages": list(kw["messages"])})
        if self.fail_at == len(self.requests) - 1:
            raise anthropic.APIConnectionError(request=None)
        return self.script.pop(0)

    def _create(self, **kw):
        return self._next(kw)

    def _stream(self, **kw):
        return FakeStream(self._next(kw))


def scripted():
    return [
        SimpleNamespace(stop_reason="tool_use", content=[
            text_block("Aye, lighting her up!"),
            tool_block("t1", "set_power", {"devices": ["Office Light"], "on": True})]),
        SimpleNamespace(stop_reason="end_turn", content=[
            text_block("The office be bright as a lighthouse now, Captain.\nMODE: NONE\nMEMORY: NONE")]),
    ]


def scratch_memory():
    d = Path(tempfile.mkdtemp(prefix="jack-mem-"))
    for name in ("identity.md", "memory.md"):
        (d / name).write_text((MEMORY_SRC / name).read_text())
    return d


def check_tool_turn():
    mem = scratch_memory()
    for streaming in (False, True):
        link = FakeLink()
        h = Home(load_inventory(), link)
        client = FakeClient(scripted())
        history, spoken, events = [], [], []

        def on_sentence(s):
            spoken.append(s)
            events.append(("spoke", s))

        orig = h.run_tool

        def run_tool(name, args):
            events.append(("tool", name))
            return orig(name, args)
        h.run_tool = run_tool

        if streaming:
            turn = stream_turn(client, history, "Light up the office", on_sentence, mem, home=h)
            # The lead-in was spoken before the tool ran, not after.
            assert events[0] == ("spoke", "Aye, lighting her up!"), events
            assert events[1] == ("tool", "set_power"), events
            assert spoken == ["Aye, lighting her up!",
                              "The office be bright as a lighthouse now, Captain."], spoken
        else:
            turn = take_turn(client, history, "Light up the office", mem, home=h)
        assert link.calls == [("power", "Office Light", True)]
        assert turn.mode is None and turn.saved is None
        assert "lighthouse" in turn.spoken and "MODE" not in turn.spoken, turn.spoken
        # history: user, assistant(tool_use), user(tool_result), assistant
        roles = [m["role"] for m in history]
        assert roles == ["user", "assistant", "user", "assistant"], roles
        result = history[2]["content"][0]
        assert result["tool_use_id"] == "t1" and result["content"] == "Office Light: on."
        assert result["is_error"] is False
        # Tools and the device list were offered on every call.
        for req in client.requests:
            assert {t["name"] for t in req["tools"]} >= {"set_power"}
            assert "Devices you control" in req["system"]
        assert len(client.requests) == 2

    # API error on the second call: history rolled back to before the turn.
    h = Home(load_inventory(), FakeLink())
    history = [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "Ahoy"}]
    client = FakeClient(scripted(), fail_at=1)
    try:
        stream_turn(client, history, "Light up the office", lambda s: None, mem, home=h)
        raise AssertionError("expected an API error")
    except anthropic.APIError:
        pass
    assert history == [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "Ahoy"}]

    # A model that never stops calling tools is cut off after MAX_TOOL_ROUNDS.
    loop = [SimpleNamespace(stop_reason="tool_use", content=[
        tool_block(f"t{i}", "set_power", {"devices": ["Office Light"], "on": True})])
        for i in range(MAX_TOOL_ROUNDS + 2)]
    client = FakeClient(loop)
    take_turn(client, [], "flicker", mem, home=Home(load_inventory(), FakeLink()))
    assert len(client.requests) == MAX_TOOL_ROUNDS


if __name__ == "__main__":
    check_inventory()
    check_refusals()
    check_pump()
    check_failures()
    check_tool_turn()
    print("PASS: inventory loads only allowed devices; refusals never reach a vendor; "
          "the pump needs a yes in the very next turn; failures reported as failures; "
          "the tool round trip speaks both rounds, keeps history valid, rolls back on "
          "an API error, and stops after MAX_TOOL_ROUNDS")
