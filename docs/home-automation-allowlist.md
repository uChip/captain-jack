# Captain Jack — Home Automation Intent Allowlist

Per the brief: a deliberately bounded, explicit allowlist, written down before
any tool calls get wired up, so Captain Jack's capability set doesn't quietly
creep toward full-Jarvis scope over time. This defines *what Jack is allowed
to ask for* — the actual per-vendor API integration ("wiring the bridge") is
separate future work, tracked per category below.

Real device inventory (as of 2026-09-11): ecobee (thermostat), Govee Home
(smart lights), SmartLife/Tuya (light switches, fan switches, switched
outlets), Minoston (light switches, fan switches, switched outlets), Rachio
(irrigation), Reolink (security cameras). No smart locks currently installed.

Same enforcement pattern as the memory ruleset: Haiku proposes an intent from
this list; orchestration code validates it against the allowlist (including
any numeric bounds below) before ever calling a vendor API. Malformed or
out-of-range requests are rejected in code, not trusted from model output.

## Lights

- **Devices**: Govee Home smart lights; SmartLife/Tuya and Minoston light
  switches.
- **Allowed**: turn on, turn off, set brightness (dimmable fixtures only),
  set color (Govee color-capable fixtures only).
- **Not allowed**: adding/removing/renaming devices or groups, any
  network/firmware configuration.
- **Bridge status**: Govee has a public developer API (known). Tuya/SmartLife
  has a cloud API via the Tuya IoT Platform (known, needs a developer
  account). Minoston — unclear whether it exposes a direct API or requires a
  Z-Wave/Zigbee hub; genuinely don't know, flagging as an unbuilt
  bridge to research at implementation time rather than guessing.

## Fans (fan switches)

- **Devices**: SmartLife/Tuya and Minoston fan switches.
- **Allowed**: turn on, turn off, set speed (multi-speed switches only).
- **Bridge status**: same per-vendor status as Lights above.

## Switched outlets

- **Devices**: SmartLife/Tuya and Minoston smart outlets.
- **Allowed**: turn on, turn off — **only for outlets explicitly named/
  labeled as automation-safe** (e.g. "patio string lights"), not a blanket
  "any outlet" capability. An outlet can be powering anything — a space
  heater, an aquarium pump — so this category needs a real per-outlet
  allowlist maintained separately, not just "outlets in general are in
  scope."
- **Bridge status**: same per-vendor status as Lights above.

## Thermostat

- **Devices**: ecobee.
- **Allowed**: set target temperature, **clamped in code to a safe range**
  (e.g. 60-80°F — exact bounds TBD when implemented) regardless of what's
  requested; set mode (heat/cool/auto).
- **Bridge status**: ecobee has a well-documented public API (known).

## Irrigation

- **Devices**: Rachio.
- **Allowed**: start a zone for a bounded duration, **capped in code** (e.g.
  15-30 min per request, exact cap TBD) so a request can't run for hours;
  stop or skip a scheduled run.
- **Bridge status**: Rachio has a public API (known).

## Scenes

- **Devices**: any vendor's predefined scenes (Tuya/SmartLife scenes, Govee
  scenes, ecobee comfort settings).
- **Allowed**: activate an existing, already-configured scene by name.
- **Not allowed (for now)**: creating, editing, or deleting scenes/
  automations. Tracked as an open, deliberately deferred question in
  `parrot-project-brief.md` ("Automation/rules authoring") rather than a
  permanent no — vendor apps being clunky is itself a real argument for
  eventually letting Jack author simple vendor-executed rules on request.
- **Bridge status**: varies per platform; research alongside that platform's
  other intents at implementation time.

## Explicitly excluded from v1

- **Door locks**: no smart lock hardware exists in the house today, so
  there's nothing to control — not a judgment call, just no device. If a
  lock is added later, revisit with the same asymmetric caution raised
  during the memory-design pass: lock-only, no remote unlock, given Jack's
  no-voice-ID trust model means anyone overheard can issue a command.
- **Security cameras (Reolink)**: excluded for two independent reasons —
  Jack is audio-only and has no way to usefully surface camera footage even
  if he could reach it, and letting a voice command arm/disarm recording is
  the same risk shape as unlocking a door. A future *read-only* status check
  ("are the cameras online") would be a much smaller ask than control and
  should be evaluated separately from this allowlist, not bundled in.
