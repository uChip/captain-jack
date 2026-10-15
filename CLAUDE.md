# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project state

This Claude Code session runs directly on the bird's own Raspberry Pi 5
(headless, accessed via SSH from Chip's desktop) — not a separate dev
machine. Hardware-facing checks (USB devices, serial ports, audio devices)
can be run directly from a session in this repo; there's no "deploy to the
Pi" step to account for.

Early implementation. `orchestrate.py` is Captain Jack's text-only
conversation loop: loads `memory/identity.md` + `memory/memory.md` as the
system prompt, calls the Claude API (Haiku), and parses/validates/saves the
model's proposed `MEMORY:` line per `docs/captain-jack-memory-design.md`.
`coordinator.py` runs the voice loop (spec section 4.16) and the full
Off Watch/On Watch/Asleep state machine (spec 4.11): press Enter to
wake Jack, speak, and he answers aloud (`tts.py`, kokoro-pi, voice
`am_santa`); typing `sleep` then Enter stands in for "Goodnight, Jack".
It builds on `playback.py`, `capture.py`, `listener.py`, `stt.py`, and
(via `--port`/`--dry-run`) `serial_link.py` + `motion.py` for beak-sync
and ambient/excursion gestures — omitted by default so the no-hardware
test suite stays hardware-free. The Pi<->Arduino serial link's command
syntax is locked down and implemented
(`arduino/ServoControl/ServoControl.ino`, see
`docs/specification.md` section 4.13); the Arduino drives all four servos
(head pitch/roll/yaw + beak) correctly from real commands. The reSpeaker
XVF3800 is USB-connected to the Pi with the bird's speaker (40mm, 4Ω,
5W) wired to its output through an external amp, and physical
construction is complete (2026-10-06): the electronics enclosure was
rebuilt and the Pi, Arduino, servo power supply, XVF3800, amp, and
speaker are all mounted inside it. Playback is confirmed clean at full
digital scale — the clipping problem is resolved, see
`docs/specification.md` Open Issues issue 26.
No home-automation tool calling yet
either — the intent allowlist (next-step below) isn't wired into a tool
schema.

**This file and `docs/specification.md` describe current state and
project definition only.** For design changes, what didn't work,
learnings from implementation/testing, alternatives considered, and why a
decision was made the way it was, see `docs/log.md` — read it before
answering questions about project history, direction, or trade-offs, not
just when doing narrow implementation.

### Running it

```bash
sudo apt install -y libportaudio2          # system library sounddevice needs (installed)
venv/bin/pip install -r requirements.txt  # already installed in venv/
ANTHROPIC_API_KEY=... venv/bin/python orchestrate.py   # text-only conversation loop
venv/bin/python playback.py [clip.wav ...]             # play clips through the bird
venv/bin/python listener.py [--model base.en]          # print transcripts of speech to the bird
venv/bin/python coordinator.py --scratch-memory        # voice loop; own terminal (reads Enter)
```

Model files live in `models/` (git-ignored — download once):

```bash
mkdir -p models && cd models
curl -fLO https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.en.bin
curl -fLO https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin
curl -fL -o silero_vad.onnx https://github.com/snakers4/silero-vad/raw/v5.1.2/src/silero_vad/data/silero_vad.onnx
sha1sum ggml-*.bin   # tiny.en c78c86eb..., base.en 137c4040... (whisper.cpp's published hashes)
cd .. && venv/bin/kokoro-pi build --models models/kokoro-pi   # TTS: downloads + builds, ~4 min on the Pi 5
```

`orchestrate.py` needs a live `ANTHROPIC_API_KEY` (or an `ant auth login`
profile). Tests live in `tests/`, indexed with run instructions in
`docs/tests.md`.

## What this project is

An animatronic parrot ("Captain Jack") — an existing 3D-printed, servo-driven
bird — getting a Raspberry Pi 5 "brain" added for interactive voice
conversation, replacing an Arduino-only setup. Full context, hardware specs,
and rationale for every decision below live in
`docs/parrot-project-brief.md` — read it before starting implementation work,
it's the canonical source and more detailed than this summary.

## Architecture: two separate personas, two separate stacks

**Jarvis** (primary desktop assistant, not this repo's code, mentioned for
context) runs on Claude Code + backtalk voice bridge + full ai-memory-vault,
billed on the flat Pro plan.

**Captain Jack** (what actually gets built here) is a deliberately lighter,
separate stack:
- Direct Claude **API** calls (Haiku model), not Claude Code — a small, fixed
  tool schema for home-automation intents only, no open-ended tool access.
- Memory is plain markdown files (identity/boot doc + running log), same
  pattern as ai-memory-vault but with a much simpler save/skip ruleset suited
  to a lighter model.
- **File I/O for memory must live in orchestration code, not be delegated to
  the model as autonomous tool calls.** Each turn: orchestration code reads
  memory and injects it into the system prompt; Haiku responds; orchestration
  code (not the model) decides what to append, in a fixed format.
- Local, zero-marginal-cost wake-word spotting, STT (e.g. local Whisper), and
  TTS on the Pi — only the language-model turn itself goes over the network.

## Hardware/software split

- **Arduino**: shrinks to real-time servo execution only (head pitch/roll/yaw,
  beak position) via a one-directional serial protocol from the Pi —
  single-letter commands with variable-length integers, no
  `HEAD`/`BEAK`/`GESTURE` keywords: `p`/`r`/`y` stage head targets and
  `t` the move time, `s` starts the eased move, and `b<BB>` sets the beak
  immediately (never eased, per issue 8). See `docs/specification.md`
  section 4.13 for ranges and offsets. No
  sensor input, no audio hardware, and no autonomous behavior of its
  own — gestures are composed and stored on the Pi, sent down as the
  same primitive commands (**decided 2026-09-14**, see
  `docs/specification.md` Open Issues issue 7); the Arduino never sees a
  `GESTURE <id>`. If the Pi is down, the Arduino does nothing and Jack is
  motionless — accepted behavior.
- **Pi 5**: owns all "intelligence" — one Python process with a thread per
  shared resource (mic capture, playback + beak-sync, serial port, etc.;
  see `docs/specification.md` section 4.16) — runs the orchestration, reads
  direction-of-arrival from the reSpeaker (`xvf_host AEC_AZIMUTH_VALUES`),
  extracts a real-time RMS amplitude envelope from whatever audio is
  currently playing (idle clips or live TTS) at ~30-50Hz to drive beak-sync —
  one code path for both cases, replacing the old MY1690 dual-channel-clip
  trick.
- **Audio I/O**: Seeed reSpeaker XVF3800 (4-mic array, onboard AEC) — the
  bird's speaker must be wired directly to the XVF3800's own output, not a
  separate sound card, or its AEC has no reference signal to cancel against.

## Decisions already made — don't re-litigate without new information

See `docs/parrot-project-brief.md`'s "Decisions already made" section —
the single canonical list (trust model, two separate birds, removed
electret mics/MY1690, speaker-ID deferral, conversational-privacy stance,
automation-authoring scope, cost/billing approach). Don't re-litigate any
of it without new information.

## Done so far

Full narrative (dates, root-causing, specific numbers) for every item
below is in `docs/log.md`'s "CLAUDE.md History" section.

1. Memory scaffold + save/skip ruleset — `memory/identity.md` +
   `memory/memory.md`, design + ruleset in
   `docs/captain-jack-memory-design.md`.
2. Orchestration script's conversation loop — `orchestrate.py` has the
   system-prompt/memory-loading and Haiku call/response loop (text-only,
   no tools yet), live-tested end to end against the real API.
3. Home-automation intent allowlist — `docs/home-automation-allowlist.md`,
   one section per device category against the real device inventory, with
   bounded actions and per-vendor bridge status. Not yet wired to any tool
   schema or vendor API.
4. `arduino-cli` toolchain (compile + upload) confirmed working end-to-end
   against a real Arduino Uno.
5. Arduino wired to all four servos (head pitch/roll/yaw + beak);
   `ServoControl.ino` drives them correctly. Beak uses plain `Servo`, not
   `ServoEasing`. See `docs/specification.md` Open Issues issue 21
   (resolved) and section 4.14.
6. reSpeaker XVF3800 received and USB-connected to the Pi — not yet
   mounted to the statue. Idle/ambient `.wav` clips are in `wavFiles/`
   (19 as of 2026-09-25, all converted to 16kHz/16-bit), including
   `AlignmentTone.wav` for later beak-sync timing calibration.
7. `exercise_hardware.py` — the original standalone hardware test
   harness for `gesture-catalog.yaml`'s Off Watch/Asleep
   ambient/excursion behavior, which item 8's tuning was done against.
   Superseded by `motion.py` (item 28), a port of the same logic whose
   own standalone mode (`motion.py --mode off_watch [--dry-run]`) now
   fills the harness role; archived 2026-10-10 to
   `docs/archive/exercise_hardware-2026-10-10.py`. `read_doa_azimuth()`
   carried over into `motion.py` as a stub (always `None`) — wiring in a
   real DoA reading later is additive, not a rewrite.
8. The "discrete steps" visible on small/slow gestures (e.g.
   `id-idle-breathing`) were root-caused to servo PWM resolution, not an
   easing bug — see `docs/specification.md` Open Issues issue 25.
   `id-idle-breathing` has been retuned and confirmed smooth on the real
   bird; other single-digit-degree/multi-second gestures haven't been yet.
9. Audio-pipeline engine choices: wake word (openWakeWord, custom-phrase
   training), STT (Whisper via `whisper.cpp` + Silero VAD for utterance
   end-pointing; tiny vs. base model size settled 2026-10-12, see "Done
   so far" item 34; no local-LLM cleanup stage), and speaker recognition
   (ECAPA-TDNN speaker embeddings for tier-1 voice ID) — all design
   decisions, not yet implemented. See `docs/specification.md` sections
   4.1/4.2/4.15 and Open Issues 1/16.
10. Verified the connected XVF3800's actual playback/capture format via
    ALSA `hw_params` (not just vendor docs): fixed at `S16_LE`, 16kHz, 2
    channels on both directions — the board is running Seeed's 16kHz
    "standard" firmware, not the 48kHz Home-Assistant variant. Locked in
    16kHz/16-bit/S16_LE/2ch as the canonical Pi-side audio-output format
    for TTS and idle clips; corrected a spec typo along the way (existing
    `wavFiles/` clips are actually 44100Hz, not the previously-documented
    41000Hz). See `docs/specification.md` sections 3.2/4.7/4.8/4.10.
11. Decided the wake/sleep-phrase confidence-threshold methodology
    (per-phrase thresholds, openWakeWord's 0.5 default as the starting
    point, wake phrase biased stricter than sleep) without picking actual
    numbers — those still need real audio to calibrate against. See
    `docs/specification.md` section 4.1.
12. Decided STT's confidence/no-speech threshold methodology the same
    way: whisper.cpp already exposes `no_speech_thold`/`logprob_thold`/
    `entropy_thold` natively (OpenAI's reference defaults), biased
    stricter same as 4.1, with rejects needing an in-character prompt
    rather than silence during On Watch. Numbers deferred to the same
    real-audio testing. See `docs/specification.md` section 4.2.
13. Decided speaker-ID's enrollment flow: a standalone script (not an
    in-conversation flow), closed to existing household names only, ~5
    utterances averaged into one embedding per person (research-backed —
    EER drops from ~17.6% at one utterance to ~8% at five-plus), stored
    separately from `memory.md` (embeddings are opaque vectors, not
    hand-editable text). Runtime match-confidence threshold intentionally
    left undecided. See `docs/specification.md` section 4.15.
14. Speaker wired to the XVF3800's output (2026-09-25) and playback
    verified by ear: Pi → USB → XVF3800 → speaker works at the fixed
    16kHz/S16_LE/2ch format. At ALSA volume max (60/60), clips play
    clean at −10dBFS but crackle by −6dBFS and turn to static near
    0dBFS — see `docs/specification.md` Open Issues issue 26. Test
    scripts: `tests/test_speaker_level_ladder.py` (listening) and
    `tests/test_wavfiles_format.py` (see `docs/tests.md`). Interim fix
    until then: playback applies a fixed −10dB gain (ladder step 2) with
    hardware volume at max.
15. End-to-end runtime design (2026-09-25): one Python process, one
    thread per shared resource, turn-taking (no barge-in), and
    sentence-by-sentence TTS, with a keyboard stand-in for the wake word
    until the custom models are trained. Includes a 7-step build order.
    See `docs/specification.md` section 4.16.
16. Build step 1 done (2026-09-25): `playback.py`, the Playback thread —
    queued mono clips played gapless through the XVF3800 with the −10dB
    cap and mono→2ch duplication, with started/finished events timed to
    when sound actually leaves the speaker. Verified by ear
    (`tests/test_playback.py --listen`).
17. Build step 2 done (2026-09-25): `capture.py`, the Capture thread —
    continuous 80ms mono frames from the XVF3800's capture channel 1
    (channel 0 is AGC-clipped and noise-gated). Runs alongside
    `playback.py` on the same board with a shared stream clock.
18. Build step 3 done (2026-09-25): `listener.py` (Silero VAD
    end-pointing, turn-taking gate) + `stt.py` (whisper.cpp via
    `pywhispercpp`, window sized per utterance). Live test: 5 utterances
    transcribed, 2 word errors; tiny.en provisionally chosen over
    base.en (same accuracy on this sample, 2.5-3.5x faster).
19. Build step 4 done (2026-09-25): `coordinator.py` — Enter (wake
    stand-in) → beep → speech → Whisper (with household-name spelling
    hint) → `take_turn()` → printed reply, with a 2-minute On Watch
    timeout. Tested with a fake Haiku client and on five recorded
    utterances against the real API, on scratch memory.
20. Build step 5 done (2026-09-25): `tts.py` (kokoro-pi, voice
    `am_santa` chosen by Chip from an audition) — the first live voice
    conversations with Jack. `identity.md` gained a "Speaking aloud"
    section (short replies, no markdown or stage directions). Live runs
    exposed Whisper retry stalls (20s) and gibberish turned into words;
    `stt.py` now skips retries and rejects repetition and very low
    confidence (all three gibberish samples caught, no real speech).
21. Output headroom resolved (2026-10-06): external amp wired from the
    XVF3800's 3.5mm jack, set to the lowest of its 4 strap-pin gain
    settings — clean and adequately loud at full digital scale (the
    other 3 settings stay available if more loudness is ever needed).
    `playback.py`'s `OUTPUT_GAIN_DB` updated from the interim −10dB cap
    to `0.0`. Closes Open Issues issue 26.
22. Physical construction complete (2026-10-06): the electronics
    enclosure was remade and the Pi, Arduino, servo power supply,
    XVF3800, amp, and speaker are all mounted inside it — see
    `docs/specification.md` section 3.6. Unblocks final AEC validation
    and speaker-ID accuracy testing, previously waiting on the board
    being physically mounted.
23. Build step 6 done (2026-10-06): `serial_link.py` (the Serial writer
    thread — a small bounded FIFO delay line for beak commands, timed
    against Playback's dac_time; head/gesture FIFO path exists but
    unused until step 7) and beak-sync added to `playback.py` (RMS
    envelope → beak angle per 20ms block). Automatic tests pass
    (`tests/test_beak_sync.py`); found and fixed a real spec/firmware
    drift along the way (section 4.13's beak/head ranges had gone stale
    — see `docs/specification.md` section 4.8).
24. First live watch against the real bird, 2026-10-06
    (`wavFiles/AlignmentTone.wav` via `playback.py --beak`): found and
    fixed a debounce-vs-throttle bug that meant the first attempt sent
    no beak commands at all (see `docs/specification.md` section 4.8 and
    `docs/log.md`'s 4.8 history for the full diagnosis). Once fixed, 7
    of 8 tone/silence cycles looked well-synced by eye; the first
    consistently started late (repeatable, root cause still open — ruled
    out a Python-side timing bug, a device startup latency spike, and
    cold-servo stiction). Tried two experiments together (widened
    `ARDUINO_BOOT_DELAY_S`, added a throwaway `WARMUP_CMD` sent once
    after boot) and re-watched: all 8 cycles now look evenly timed by
    eye, including the first — visually fixed, not root-caused, and not
    yet confirmed by measurement. `ALIGNMENT_FUDGE_S` and the envelope
    mapping defaults are still untuned — Chip is doing a frame-matched
    video analysis off-line to get a precise offset number, to bring
    back next session. Beak-sync is not yet wired into
    `coordinator.py`'s live loop.
25. Decided TTS-sourced Off Watch clips (one-liners + philosophical
    quotes, supplementing Chip's jokes) get pre-rendered once and stored
    as ordinary `wavFiles/` clips, not synthesized live — see
    `docs/specification.md` section 4.10 for the reasoning (compute
    contention with the always-on wake-word listener, fixed duration for
    gesture pairing, catching TTS mispronunciation during curation
    rather than live). Added `wavFiles/manifest.yaml` to track each
    TTS-sourced clip's source text/category/attribution/rendering voice,
    so a future voice change is a batch re-run, not a lost-text search.
26. `ALIGNMENT_FUDGE_S` measured, 2026-10-07: Chip's frame-matched video
    (30fps, against the file's own precisely-measured tone-on/off
    timing) showed the beak consistently starting to move about one
    frame (~30ms) *after* the sound it was responding to, on both
    opening and closing edges, across all 8 cycles. Updated
    `ALIGNMENT_FUDGE_S` from `0.0` to `0.03` in `serial_link.py`
    accordingly; the 20ms attack time constant looks right as-is. Left
    open, lower confidence: the closing edge looked faster than the
    100ms release time constant predicts — not changed yet, better
    confirmed against real conversational speech (step 7) than further
    analysis of one test tone. See `docs/specification.md` section 4.8.
27. Idle-clip library complete and rendered, 2026-10-07: `wavFiles/`
    grew from 19 to 163 clips. Chip populated `wavFiles/manifest.yaml`
    with ~90 jokes and quotes; review before rendering caught a real
    structural bug (the file never actually parsed), three sets of
    accidentally-duplicated filenames that would have silently
    overwritten each other, and several unbalanced quote marks — all
    fixed, Chip's content/attribution choices left alone. Chip then
    invited Claude to add content of its own (explicitly budgeted, up to
    the rest of the session) — 24 entries: pirate-voiced remixes of a
    few of his quotes, new quotes treated the same way, and original
    lines, attributed "Claude as Captain Jack[, misquoting/paraphrasing
    X]." Wrote `generate_idle_clips.py` (reads the manifest, calls
    `tts.py`'s existing synthesize function, writes `wavFiles/<file>` —
    never edits the manifest itself) and rendered all 144 TTS-sourced
    clips. `tests/test_wavfiles_format.py` is glob-based and now covers
    all 163 automatically. See `docs/specification.md` section 4.10 and
    `docs/log.md`'s 4.10 history for the full review detail.
28. Build step 7 done, 2026-10-07 — Motion & idle thread: `motion.py`,
    a faithful port of `exercise_hardware.py`'s already hardware-validated
    ambient/excursion gesture logic into a real `set_mode()`-driven
    thread over `serial_link.py`'s real writer (not a blocking one).
    `gesture-catalog.yaml`'s `wavs: off_watch:` list populated with all
    162 real `wavFiles/` clips (previously empty). Automatic tests pass
    (`tests/test_motion.py`, a small synthetic catalog); live-watched
    standalone against the real bird (`motion.py --mode off_watch
    --dry-run --seconds 15`) — clean output, no crash, Chip confirmed
    correct movement.
29. Build step 7 done, 2026-10-07 — the full Sleep-Mode State Machine
    (spec 4.11): `orchestrate.py` gained a `MODE: NONE|END_SESSION|NAP`
    meta-tag (same mechanism as `MEMORY:`), and `coordinator.py` now
    owns all three modes — Haiku's tag (applied once the reply finishes
    playing) and the 2-minute no-prompt timeout drive On Watch's exits;
    a keyboard stand-in for "Goodnight, Jack" (type `sleep` + Enter) and
    a 15-minute idle timeout drive Off Watch's exit to Asleep; waking
    from Asleep goes straight back to On Watch, never through Off Watch.
    Motion and the Serial writer are wired in behind new `--port`/
    `--dry-run` flags, so the no-hardware test suite is unaffected.
    Automatic tests pass (`tests/test_mode_tag.py`,
    `tests/test_coordinator.py`'s new state-machine checks); confirmed
    in dry-run that the full thread set (Capture, Listener, Playback,
    Serial writer, Motion, TTS) starts and stops cleanly together. Not
    yet confirmed by an actual live voice conversation. See
    `docs/specification.md` section 4.11 and `docs/log.md`'s 4.11 and
    4.16 history.
30. Step 7 fully validated live, 2026-10-07: across four `--port` runs
    against the real Arduino, confirmed in turn: a beep/listening-cue
    timing fix (full utterances now captured, not clipped at the
    start); beak-sync and ambient motion correctly tracking real
    conversational speech; then a real race found while first
    confirming `MODE: NAP` live — a multi-sentence reply's own
    sentence gaps reopened the mic early, letting a stray sound
    clobber the in-flight reply's tag tracking and nearly drop the
    `MODE:` tag silently (fixed in `coordinator.py`'s `_on_playback`,
    regression test `check_mid_reply_sentence_gap` added); and finally,
    after the fix, a clean `MODE: END_SESSION` transition with no
    recurrence, plus the `sleep` stand-in correctly moving Off Watch ->
    Asleep when typed right after entering Off Watch. Closes the "real
    live voice conversation with `--port`" item from section 4.16's
    build order. See `docs/log.md`'s 4.16 history for the full
    diagnosis of each issue found.
31. Beak-sync's release time constant confirmed, 2026-10-07: the open
    question from item 26 (a test tone's closing edge looked faster
    than the 100ms release constant predicts) was retested by watching
    a clean, dry `kokoro-pi/am_santa` clip (`BilgePumpForAnger.wav`) —
    the same voice/engine Jack actually speaks with — through
    `playback.py --beak`. Chip confirmed "looks about right, closing
    does not seem too early"; `BEAK_RELEASE_S` (0.10) stands unchanged.
    See `docs/specification.md` section 4.8 and `docs/log.md`'s 4.8
    history.
32. Both custom openWakeWord models trained and validated, 2026-10-10/11:
    `wake_phrase.onnx` (accuracy ≈0.873, recall ≈0.748, false-positives
    ≈0.05/hour) and `sleep_phrase.onnx` (accuracy ≈0.794, recall ≈0.594,
    false-positives ≈0.10/hour), both via the community Colab notebook
    (`alfiedennen/openwakeword-colab-2026`). Getting here took a
    multi-day fight with recurring Colab disconnects (root cause never
    confirmed — likely a fixed session-duration cap), fixed well enough
    to work via a faster parallel download for the 17GB negative-feature
    set, swapping the unreliable FMA background-noise source for ESC-50,
    and checkpointing each expensive step's output to Google Drive as a
    zip so a disconnect never costs more than the step in flight. Both
    `.onnx` files are in the repo root. See `docs/log.md`'s 4.1 history
    for the full saga, including a real path-mismatch bug found in
    openWakeWord's own `train.py` along the way.
33. The real wake-word spotter built and live-validated, 2026-10-11:
    `wakeword.py`'s `WakeSpotter` runs openWakeWord's bundled onnx
    feature pipeline over Capture's frames, feeding the two trained
    models, and is wired into `coordinator.py` alongside (not replacing)
    the Enter/`sleep` keyboard stand-ins. Found and fixed a real bug
    along the way: Motion's own idle/excursion/settle-in clips share
    `Playback` with TTS replies but weren't recognized by the mic's
    reopening logic, leaving the mic permanently deaf after the first
    one played in Off Watch/Asleep - invisible until the spotter gave
    Off Watch/Asleep something worth listening with. Live-watched
    cycling through the full state machine repeatedly: wake from Off
    Watch and from Asleep, and the sleep phrase from Off Watch, all
    fired correctly and repeatedly by voice. Closes build step 7's
    wake-word piece and CLAUDE.md's former work-list item 9. See
    `docs/log.md`'s 4.11/4.16 history for the full diagnosis, including
    a false alarm along the way (STT failures, not a real bug, made one
    session look stuck). Still open: real-audio threshold/patience/
    cooldown calibration (spec 4.1's methodology, numbers deferred).
34. STT's "frequently repeated and garbled" reports root-caused and
    fixed, 2026-10-12: built `compare_stt.py` (reads a `coordinator.py
    --save DIR` recording and runs named Whisper models side by side) and
    used it against two real recorded sessions (one noisy, one quiet) to
    find three real bugs, not an accuracy/noise problem as first
    suspected. First: `STT` reused one whisper.cpp Model for the whole
    process life; a reused Model's decode drifts across calls
    (`no_context=True` only disables *text* context, not whatever else
    carries between decodes) - the same phrase came back as different,
    sometimes wrong, text from one attempt to the next on identical
    audio. Fixed by building a fresh Model per `transcribe()` call
    (~0.08-0.1s, trivial against decode time). Second:
    `is_repetition_loop()`'s "same short phrase twice" rule had no
    distance limit, false-rejecting a long, legitimate utterance that
    innocently reused a phrase once, far apart (a Gettysburg/Preamble
    quote test) - fixed by requiring the repeats be adjacent, the way
    every actual hallucination loop is. Third, found from a second
    session in a quiet room (no background noise to blame): the
    household-names spelling-hint prompt (`names_prompt()`) itself can
    push whisper.cpp into a genuine repeat-loop hallucination on some
    short utterances - confirmed it's any non-empty prompt, not its
    wording, and that the same prompt measurably helps confidence on
    ordinary speech otherwise, so `STT.transcribe()` now retries once
    without the prompt specifically when the first attempt rejects as a
    repetition loop. All three fixes verified live against real recorded
    audio and via `git stash` regression tests (`tests/test_stt.py`,
    including a new committed fixture,
    `tests/data/thank_you_jack_ch1.wav`). With all three fixed, re-ran
    the tiny-vs-base comparison on real noisy-room audio and confirmed
    tiny.en (item 9) as the right call - on par with base.en's accuracy
    at 2-2.5x the speed. See `docs/log.md`'s 4.2 history for the full
    diagnosis.
35. Reply-length target raised, 2026-10-12: `identity.md`'s "Speaking
    aloud" target moved from about twenty words to about thirty, based on
    measuring real live replies (mean 31 words, range 19-36, across a
    full ordinary conversation) - Chip's read was that replies don't feel
    overly long once you're used to Jack's cadence, but could still come
    down a little, so the new target sits close to current behavior with
    some room to trim. The existing "unless someone asks for a story..."
    exception was left unchanged and confirmed still doing its job: a
    requested mystery story ran well over a hundred words and that was
    the right call, not a bug. See `docs/log.md`'s 4.4 history.
36. A fourth STT repeat-loop gap found and fixed, 2026-10-12, from the
    same session that confirmed item 35: ambient household noise (someone
    else talking nearby, not Chip) got hallucinated into "No? No? No? No?
    No?" - a single word repeated rapidly, too short (5 words) for either
    of `is_repetition_loop()`'s existing rules to ever fire (both need
    6+ words). Added a third rule catching 4+ back-to-back repeats of a
    single word, kept to zero gap (unlike the looser few-word tolerance
    on the 2/3-word rules) so it doesn't false-positive on common words
    ("the", "a") recurring naturally in long sentences. The other
    hallucination in that same stretch ("Can you tell her to say?") is
    the already-known, accepted gap - a plausible-sounding sentence from
    non-Jack-directed speech, not a repetition-rule miss, and not
    something speaker-ID-less STT can tell apart from real speech (see
    spec 4.2's "Not covered"). See `docs/log.md`'s 4.2 history.
37. Wake threshold calibrated against real household audio, 2026-10-12:
    a voice-only `coordinator.py --save` session (close/soft/distant
    delivery, a second speaker, and a stretch of undirected background
    talk) fired the wake phrase correctly all 5 times (0.82-1.00) and
    never false-triggered on the background talk, so `wakeword.py`'s
    `WAKE_THRESHOLD` moved from the 0.5 starting point to 0.65 - still
    clear of the weakest real attempt, with more false-accept margin,
    per item 9/section 4.1's "bias stricter" call. `SLEEP_THRESHOLD`/
    `PATIENCE_FRAMES`/`COOLDOWN_S` untouched - no real sleep-phrase data
    yet. Two STT "garbled" results from that same session turned out to
    be the far-field/quiet-speech accuracy gap, not a wake-spotter or
    repetition-rule issue - see item 36. See `docs/log.md`'s 4.1
    history.
38. Sleep threshold checked against real data, left unchanged,
    2026-10-12: a follow-up voice-only session focused on "Goodnight,
    Jack" got 4/5 clean fires (0.91-1.00); the one miss printed nothing
    at all, meaning it scored under the 0.1 debug floor - too quiet to
    register as speech-like, not a near-miss on 0.5, so lowering
    `SLEEP_THRESHOLD` wouldn't have caught it. Left at the vanilla
    default. Bonus data point: the same phrase said conversationally
    during On Watch (not as the fixed phrase) correctly went through
    Haiku's own `MODE: NAP` tag instead (per spec 4.11, not a new path)
    and was heard by STT as "Good night, Jack." at a lower confidence
    (p=0.42) than the session's other phrases - consistent with people
    naturally saying "goodnight" more softly, which costs confidence on
    both paths the same way. Also flagged, unresolved: one reply in that
    session took 5.55s to first audio against a 3.2-3.8s baseline, with
    a perfectly normal `stt_s` - a different-looking anomaly from the
    one in item 34, not yet explained. See `docs/log.md`'s 4.1 history.
39. Haiku's reply now streams into TTS, 2026-10-12: `orchestrate.py`
    gained `SpeechStreamer` (an incremental version of `tts.py`'s
    `split_sentences()`, stopping at the first `MODE:`/`MEMORY:` tag
    line - see item 40 for why not simply the first newline) and
    `stream_turn()` (calls the Messages API's streaming endpoint
    instead of waiting for the whole reply). `coordinator.py`'s `handle_utterance()` now calls
    `stream_turn()` instead of `take_turn()`, queuing each sentence to
    TTS as soon as it's ready rather than only after Haiku finishes the
    entire reply (tags included) - the "next lever" flagged since the
    original build (spec 4.16 build step 5). Found and fixed a new race
    this opened: a reply's true last sentence isn't known until the
    full reply has arrived, so if TTS/Playback happen to be faster than
    the network, that sentence's own playback can finish before
    `_last_tag` is set to match it - same class of bug as the
    2026-10-11 sentence-gap race, a different pair of racing events.
    `coordinator.py`'s new `_finish_reply()` catches up immediately
    rather than dropping the mic reopen/`reply_done`. Also fixed, found
    on the error path: a turn that fails with zero sentences ever
    spoken needs to resume the On Watch timeout itself now, since
    `_begin_reply()` pauses it before Haiku's success/failure is known.
    All covered by a new `tests/test_streaming_reply.py` plus new
    `tests/test_coordinator.py` cases; confirmed each new check fails
    without its fix. Not yet confirmed: a real live-device latency
    measurement - blocked this session on an expired
    `ANTHROPIC_API_KEY`, not a code issue. See `docs/log.md`'s 4.3
    history (new section).
40. Streaming's dropped-second-paragraph bug fixed, 2026-10-14: the
    first live run with item 39 in place showed Haiku sometimes splits
    a reply into two paragraphs, and the second was never spoken -
    `SpeechStreamer` stopped at the first newline, on a "replies are
    single-line" assumption that didn't hold. It now stops only at a
    line starting like a tag (`MODE:`/`MEMORY:`/a ``` fence) and treats
    other line breaks as whitespace. Regression cases in
    `tests/test_streaming_reply.py`, confirmed failing on the old code;
    confirmed live the same day (every second paragraph spoken). See
    `docs/log.md`'s 4.3 history.
41. "Degraded" recognition root-caused, 2026-10-14: head-servo motion
    noise, not code. With `--port`, On Watch's nonstop ambient sway
    raises the capture noise floor from about -50 to -34 dBFS, and both
    Whisper models get about half of a fixed script wrong (servos off:
    tiny.en 4/14, base.en 1/14). Powered-but-holding servos are quiet;
    movement of any size is loud (a smaller +-3deg sway with pauses,
    kept for looks, gained only ~3dB). The 2026-10-12 STT/wake
    confirmation runs likely had no `--port`. Recordings in
    `stt_samples/session6`-`11`. Off Watch is worse: the 41deg
    breathing measured within a few dB of speech level and made the
    wake phrase need a raised voice; shrunk to +-3deg with holds as a
    trial (~8dB quieter, steps perceptibly).
    `tests/measure_servo_noise.py` measures this per mode. See
    `docs/log.md`'s 4.2 history.
42. Servo noise path found, 2026-10-14: it reaches the mic by
    conduction, not through the air. A spare B11DLS loose on the bench
    12in away was inaudible at small sways (+-20deg added ~4dB); taped to
    the electronics enclosure, a fast +-20deg move hit -23 dBFS (near
    speech level), and even holding still it added a ~13dB 135-170Hz hum.
    A software high-pass (200/300Hz, `compare_stt.py --highpass`) was
    tried on recorded sessions and changed nothing - the damaging part is
    inside the speech band. Fix is mechanical; Chip's preferred route is
    a separate enclosure for Pi/XVF3800/amp/speaker (only the Arduino
    serial line crossing over, array orientation keyed for future DoA),
    with a heavier, soft-mounted bird base as the alternative. Script:
    `tests/measure_bench_servo.py`. See `docs/log.md`'s 4.2 history.
43. Soft-mounting the bird fixes servo noise, 2026-10-14: the bird
    unbolted and set on a silicone mat (2lb of lead shot made no
    difference) cut motion noise at the mic ~23-26dB (-32 to about -55
    dBFS). Spoken check with the head swaying while listening
    (`coordinator.py --no-hold`, new flag; session15): floor -55.5,
    margin 32.5dB, base.en 1/7 wrong (the "How's" miss that also happens
    servos-off) vs. 3/8 bolted; tiny.en 3/7. Wake phrase 4/4 and sleep
    phrase 1/1 over Off Watch/Asleep motion in a noisy house (vs. often
    under 0.1 bolted). Two-box rework and weighted base no longer needed
    on this evidence. A mat lying over the array made things worse - it
    bridged the isolation. Permanent mount designed (not built) in
    `docs/specification.md` section 3.6 "Bird-to-base isolation mount":
    requirements, candidates (Chip's glued pads, or screw-on rubber
    isolators to stay removable), and an acceptance test. See
    `docs/log.md`'s 4.2 history.
44. Parts list started, 2026-10-14: `docs/parts-list.md` (linked from
    spec section 3) records the exact make/model of every installed
    part - the spec says "9g servo", the list says AGFRC B11DLS. Drafted
    from the repo and the hardware itself (Pi 5 8GB, XVF3800, CH340 on
    the Arduino clone); *TBD* entries are for Chip to fill in.

## Work list — split by hardware dependency

Everything below needs nothing that isn't already on hand — including
the smart-home devices themselves, which already exist and are
controllable today, and now including final AEC validation and
speaker-ID accuracy testing, previously waiting on the XVF3800 being
physically mounted (construction completed 2026-10-06).

### Doable now

Everything below is hardware-unblocked, but items 1/2/4 (home-automation)
are being deliberately sequenced *after* items 3/6/7/8 (the core audio
conversation loop) — Chip's own priority call, not a technical
dependency between them. Nothing here stops home-automation from being
worked in parallel if priorities change.

1. Wire orchestrate.py's tool calls for the vendors with known APIs (Govee,
   Tuya/SmartLife, ecobee, Rachio) per the allowlist, and test live against
   the real devices — none of this touches the parrot's own audio hardware.
2. Research Minoston's actual integration path (direct API vs. needs a
   hub) — the one bridge status the allowlist doc flags as genuinely
   unknown.
3. Build speaker-ID: engine (ECAPA-TDNN) and enrollment flow (standalone
   script, ~5 utterances averaged, closed to existing household names,
   embeddings stored separately from `memory.md`) are both designed —
   see `docs/specification.md` section 4.15. Runtime match-confidence
   threshold still needs deciding (methodology, not numbers, matching
   4.1/4.2's treatment). Prototyping and final accuracy validation can
   both proceed now: the board's mic array is electrically functional
   and, as of 2026-10-06, mounted in its final acoustic geometry (see
   Open Issues issue 1).
4. Flesh out the vendor-executed automation-authoring idea (the "lights off
   at midnight" case from the brief's deferred decision) as a small design
   spec — doesn't need new hardware either.
5. More conversational/memory test vectors as they come up — continuing the
   joke/automation/NONE-case testing from this session.
6. Start on the mic/DoA-only half of the stack —
   wake-word/STT/speaker-ID groundwork (engines now chosen: openWakeWord;
   Whisper via `whisper.cpp` + Silero VAD; ECAPA-TDNN — see
   `docs/specification.md` sections 4.1/4.2/4.15). Includes collecting
   real positive/negative audio to calibrate the wake/sleep phrase
   confidence thresholds and STT's no_speech/logprob/entropy thresholds
   (methodology decided for both, see sections 4.1/4.2 — actual numbers
   for both still pending this testing).
7. Track down Seeed's official XVF3800 control tool/protocol docs — no
   `xvf_host` tool or equivalent exists on this Pi (not found via
   `apt`/`pip`/filesystem search), and reading `AEC_AZIMUTH_VALUES` over
   the exposed USB-HID (`/dev/hidraw0`) or vendor-specific USB interface
   needs Seeed's real reference application, not reverse-engineering.
8. **Build the audio loop per `docs/specification.md` section 4.16's
   build order** — steps 1-7 are now done and fully live-validated (see
   "Done so far" items 24/26/28/29/30): the full thread set
   (`coordinator.py`, beak-sync, Motion, the Sleep-Mode State Machine)
   runs together against the real bird, gated behind `--port`/
   `--dry-run` so the no-hardware test suite stays unaffected. What's
   left, roughly in order:
   - Spotter threshold calibration against real use (spec 4.1 flagged
     these as initial numbers; `coordinator.py` prints a live
     `[spotter] wake=.. sleep=..` readout whenever not On Watch to
     support this). `WAKE_THRESHOLD` calibrated 2026-10-12 against real
     audio (item 37); `SLEEP_THRESHOLD` checked against real data the
     same day and left at the vanilla default - no near-miss evidence it
     needs to move (item 38). Still open: whether `PATIENCE_FRAMES`/
     `COOLDOWN_S` need any change (no data suggesting either does so
     far). The two timeouts (2-minute On Watch, 15-minute Off Watch) are
     **decided, 2026-10-12: left as-is** - Chip's call that a deliberate
     test session doesn't reproduce real social-conversation pacing, so
     "feel" from testing isn't trustworthy either way, and erring short
     risks the known failure mode of other voice assistants cutting
     people off mid-conversation. Don't re-litigate without new
     information (see spec 4.11).
   - On Watch excursions (content/DoA/emotion-triggered) — `motion.py`
     only runs ambient motion in On Watch today.
   - Open refinements from the live conversation runs: `identity.md`'s
     reply-length target raised from twenty to thirty words, 2026-10-12
     (measured real replies averaging 31 words; see "Done so far" item 35);
     Haiku's reply now streams into TTS instead of waiting for the whole
     reply first, 2026-10-12, cutting the delay for any 2+-sentence
     reply (see "Done so far" item 39) - still open: a real live-device
     measurement of how much (blocked on an expired API key, not a code
     issue), and passing low-confidence transcripts to Haiku marked
     unclear (see spec 4.2). The frequent STT repeats/garbling flagged
     after the 2026-10-11 live session turned out to be three real bugs,
     not noise - all root-caused and fixed 2026-10-12, see "Done so far"
     item 34.
   - Servo noise during listening (item 41): hold the head still while
     the mic is open in On Watch - built 2026-10-14 (`Motion.hold()`,
     driven by `coordinator.py`), confirmed live 2026-10-14 (session14:
     floor -46 vs -34 moving/-51 off; 2-3/8 wrong) but frozen until
     speech or the 2-minute timeout. Hold cap / move-abort fixes held in
     reserve. Root fix found 2026-10-14 (items 42/43): soft-mounting
     the bird (temporarily on a silicone mat) removes the noise, Off
     Watch included. Next: a permanent soft mount per spec 3.6's
     design note (physical work, done offline by Chip; test loose pads
     with `tests/measure_servo_noise.py` before gluing); then decide whether to retire the hold
     (session15 says recognition is fine without it). tiny.en stays
     the default for now (**Chip's call, 2026-10-14**): base.en is more
     accurate with the noise gone (1/7 vs 3/7 wrong), but its extra
     ~0.5-1s on an already-noticeable ~3s wait outweighs that today. If
     base.en is picked later, pair it with a filler sound (e.g. a
     squawk) played right after the utterance ends, to cover the wait.
   - Filler sound to cover processing time (**Chip, 2026-10-14**) -
     built 2026-10-15: `coordinator.py` plays a random squawk from
     `wavFiles/fillers/` (never the same twice running; `--no-filler`
     to skip) the moment an utterance is handed over, before STT. The
     three current clips are placeholders cut from the one real squawk
     in the library (`generate_fillers.py`: stretched a third longer
     without changing pitch, then varied in speed, -6dB); Chip says
     "fine for now", Kath says crow-like. Still open: find real parrot
     recordings to drop in (no code change needed), confirm in a live
     `--port` conversation, and the optional one-shot head tilt.
   - Re-run the STT regression (`compare_stt.py` + a `--save` session)
     next time the house is genuinely noisy, not quiet like the
     2026-10-12 confirmation runs - to check recognition doesn't degrade
     significantly now that the four bugs above are fixed (items 34/36).
     Chip's own follow-up, 2026-10-12.
9. Optional: TTS engine bake-off — Supertonic-3 against the `kokoro-pi`
   now in place (see `docs/specification.md` section 4.7 and Open Issues
   issue 16), judged primarily on voice quality with real-time
   throughput as a secondary check.
10. AEC validation against the bird's own speaker — now in its final
    mounted geometry (2026-10-06, see `docs/specification.md` section
    3.6), so this can be the real validation, not just a smoke test.
