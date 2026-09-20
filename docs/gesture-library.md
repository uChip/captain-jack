🦜 Roll‑Enhanced Gesture Library (Full Motion Primitives)
Brainstormed with Gemini

> **Mapped 2026-09-20** into the actual Gesture/Move data structure (see
> `specification.md` section 4.12) as
> [gesture-catalog.yaml](gesture-catalog.yaml) — concrete servo values,
> clamped to real hardware headroom, with assumptions/gaps documented
> inline. This file remains the free-text source; the YAML is the
> structured, hardware-aware translation of it.

🎤 Speech‑Driven Gestures
These gestures synchronize with prosody, emphasis, and rhythm, now with roll added for nuance.

Beat Pulse — yaw pulse + micro‑roll
  Yaw: ±10
  Roll: ±5
  Pitch: 0
  Duration: 80–120 ms

Emphasis Nod — pitch dip + slight roll
  Pitch: −15 → 0
  Roll: +5
  Duration: 120 ms

Vowel Drift — slow yaw drift + subtle roll
  Yaw: +15 over 300 ms
  Roll: +8
  Duration: vowel length

Sentence Start Lift — pitch lift + roll
  Pitch: +10
  Roll: +10
  Duration: 150 ms

Sentence End Settle — pitch settle + roll relaxation
  Pitch: −10
  Roll: −8
  Duration: 200 ms

😃 Emotional Gestures
Roll is essential here—birds express emotion heavily through head tilt.

Curious Tilt — roll + pitch + slight yaw
  Roll: +25
  Pitch: +15
  Yaw: +10
  Duration: 300–500 ms

Skeptical Lean — roll + yaw
  Roll: −20
  Yaw: +15
  Duration: 300–500 ms

Excited Bob — pitch oscillation + roll pulses
  Pitch: ±20
  Roll: ±10
  Frequency: 4–6 Hz
  Duration: 400–800 ms

Thinking Sway — yaw sweep + roll modulation
  Yaw: −20 → +20
  Roll: ±10
  Duration: 1–2 s

Affirmation Nod — pitch nod + roll stabilization
  Pitch: −20 → 0 → −20
  Roll: +5
  Duration: 300 ms per nod

Negation Shake — yaw shake + roll counter‑tilt
  Yaw: +25 → −25 → +25
  Roll: −10
   Duration: 400–600 ms

💤 Idle Gestures
Idle motion becomes dramatically more lifelike with roll.

Idle Breathing — pitch oscillation + micro‑roll
  Pitch: ±5
  Roll: ±3
  Frequency: 0.2–0.3 Hz

Ambient Scanning — yaw drift + roll tilt
  Yaw: −30 → +30
  Roll: +10
  Duration: 3–5 s

Micro‑Twitch — tiny random pulses
  Yaw: ±3
  Pitch: ±2
  Roll: ±4
  Duration: 40–60 ms

Preen Motion — bird‑like grooming
  Roll: +20
  Pitch: −15
  Yaw: +10
  Duration: 600–900 ms

🗣️ Conversational Gestures
Roll helps convey attention and engagement.

Listening Lean — pitch forward + roll
  Pitch: −10
  Roll: +10
  Duration: 300 ms

Turn Toward Speaker — yaw toward mic + roll stabilization
  Yaw: ±30
  Roll: +5
  Duration: 200–400 ms

Agreement Motion — nod + roll
  Pitch: −10
  Roll: +10
  Duration: 300 ms

Disagreement Motion — shake + roll counter‑tilt
  Yaw: ±15
  Roll: −10
  Duration: 300–500 ms

🎭 Expressive Gestures
These are the “character” motions—roll is the star.

Showmanship Bob — exaggerated pitch bob + roll
  Pitch: ±25
  Roll: ±15
  Duration: 600–900 ms

Head Cock — classic parrot tilt
  Roll: +30
  Pitch: +10
  Yaw: +10
  Duration: 400 ms

Rapid Chatter — beak pulses + roll
  Beak: 0 → 3 → 0 → 3
  Roll: +10
  Duration: 200–300 ms

Look Away — disengagement
  Yaw: +40
  Roll: −20
  Pitch: −10
  Duration: 500–700 ms

Look Back — re‑engagement
  Yaw: −40 → 0
  Roll: +15
  Duration: 500 ms