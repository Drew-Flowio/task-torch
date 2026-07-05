# 9. Insight v1 — Product & Architecture Spec

**Status:** implementation-ready spec, v1 scope only.
**Audience:** a senior engineer implementing v1 directly from this document.
**Relationship to this repo:** v1 formalizes and productionizes the stack
already validated in `poc/` and `docs/01`–`08` (offline LLM brain, on-demand
vision captioning, local STT/TTS) into a single coherent service with a
real state machine, persistence layer, and config surface. It does not
introduce new model families beyond what's already proven — it wraps them
in a proper application.

---

## 1. Executive summary

**What Insight is:** a fully offline, head-mounted (or desk-mounted, for
bench work) AI coach. The user wakes it with the word **"Insight,"** asks
a question out loud — about a repair, a DIY task, an appliance, a car
problem, code on a screen, or anything situational — and Insight gives a
short, concrete, spoken next action. It can look at what the user is
looking at when asked to. It remembers the current task across a few
follow-up turns so the user doesn't have to repeat context.

**What v1 does:**
- Wake-word activated, voice-first interaction (wake word, VAD, ASR, LLM, TTS).
- On-demand vision capture triggered by voice or a physical button — never continuous.
- A four-state session lifecycle (Sleep / Idle-Awake / Task Session / Error-Degraded) that governs when the mic, camera, and LLM are actually active.
- Local SQLite persistence for sessions, step history, user profile, device profile, and a small set of long-term facts.
- A single hard-coded, config-parameterized system prompt with a built-in safety policy (self-harm hard refusal, conservative handling of electrical/fire/medical/high-risk repair).
- A local CLI for status, log tailing, session inspection, and debugging. No GUI.
- Human-editable config file driving every runtime knob (models, timeouts, thresholds, hardware profile).

**What v1 does *not* do:**
- No cloud calls, no accounts, no telemetry, no OTA updates.
- No continuous/always-on video — camera is off unless explicitly triggered.
- No manual/document library retrieval (hooks exist in the architecture; the feature is Phase 2).
- No multi-process/microservice deployment (the architecture supports splitting later; v1 ships as one process).
- No GUI, no mobile app, no multi-user account system (schema supports more than one profile row, but v1 assumes one primary user per device).

**Why a single-process Python architecture is right for v1:**
On a Pi 5 (8 GB, CPU-only), the constrained resource is CPU and RAM, not
process isolation. A multi-process/microservice split buys fault
isolation and independent scaling at the cost of IPC latency, serialization
overhead, and a lot of orchestration code — none of which this product
needs yet, and all of which competes with the LLM and vision model for the
same four Cortex-A76 cores. A single process with **strict internal module
boundaries and a message-shaped internal event bus** gets v1 shipped
faster, is easier to debug (one log stream, one stack trace), and is
*already* structured so that splitting audio, vision, LLM inference, and
storage into separate services later (e.g., once Insight moves to a
mini-PC with room for a service mesh, or needs to share a GPU-having
inference box) is a mechanical extraction, not a redesign — because
modules never call into each other's internals, only exchange typed events
over an in-process bus that can be swapped for a real IPC transport
without changing any module's own logic.

---

## 2. System architecture

### Internal modules

| Module | Responsibility |
|---|---|
| `core/` | Main event loop (`orchestrator`), the state machine, the in-process event bus, and shared event/message type definitions. This is the only module allowed to wire other modules together. |
| `config/` | Loads and validates the human-editable config file; resolves the active hardware profile (`pi5` / `minipc`) into concrete runtime values; exposes a single immutable config object to the rest of the app. |
| `audio_io/` | Microphone capture, wake-word detection, voice activity detection (VAD), and the physical talk-button listener. Emits `WakeDetected`, `SpeechStarted`, `SpeechEnded` events. |
| `asr/` | Wraps the local speech-to-text engine; consumes captured utterance audio, emits `TranscriptReady` events. |
| `vision/` | Camera lifecycle (on-demand power-on/capture/power-off), frame preprocessing, and the vision captioner. Emits `CaptionReady` events with structured (JSON-like) output. Never runs unless explicitly triggered. |
| `session/` | Task session lifecycle: create/update/end/reset a session, route control phrases ("next step," "start over," etc.) to session actions, and produce the rolling compressed task summary. |
| `prompt/` | Assembles the final prompt from system template + safety policy + session context + vision context + current utterance; enforces the runtime pre-filter/rephrase policy (section 5) before anything reaches the LLM; manages the context-window token budget (section 8). |
| `llm/` | Thin wrapper around the local instruction LLM runtime (same role as `poc/brain.py` in this repo). The *only* module that talks to the LLM. |
| `tts/` | Wraps the local text-to-speech engine and drives audio output. |
| `memory/` | SQLite access layer: repositories for sessions, step events, user profile, device profile, and memory facts. The only module allowed to touch the database file. |
| `storage/` | Filesystem paths (DB file, model files, log files, optional ephemeral snapshot images), and the optional short-lived snapshot retention policy. |
| `logging_/` | Local, lightweight structured logging with rotation. (Named `logging_` to avoid shadowing the Python standard library.) |
| `cli/` | Local debug/inspection CLI — a separate entrypoint, not part of the always-running service, that talks to the same SQLite file and log directory. |

### Directory layout

```
insight/
├── main.py                     # entrypoint: load config, construct modules, start orchestrator
├── core/
│   ├── orchestrator.py         # main loop; owns the event bus and the state machine instance
│   ├── event_bus.py            # in-process typed pub/sub — the future IPC boundary
│   ├── events.py               # event/message type definitions (WakeDetected, TranscriptReady, ...)
│   └── state_machine.py        # Sleep / Idle-Awake / Task Session / Error-Degraded
├── config/
│   ├── loader.py                # reads + validates the YAML config, applies the active profile
│   ├── schema.py                 # config schema / validation rules
│   └── default.yaml              # shipped default config (see section 10)
├── audio_io/
│   ├── mic.py                    # microphone stream handle
│   ├── wake_word.py               # wake-word detector wrapper
│   ├── vad.py                     # voice activity detector wrapper
│   └── talk_button.py             # physical button listener (GPIO on Pi5, config'd input on mini-PC)
├── asr/
│   └── engine.py                  # local ASR engine wrapper
├── vision/
│   ├── camera.py                   # on-demand capture; backend-abstracted (CSI on Pi5, USB/V4L2 on mini-PC)
│   ├── preprocess.py                # resize/orient/crop before captioning
│   └── captioner.py                  # vision-language captioner wrapper; returns structured output
├── session/
│   ├── session_manager.py             # session create/update/end/reset
│   ├── command_router.py               # maps control phrases to session actions
│   └── summarizer.py                    # rule-based rolling history compression
├── prompt/
│   ├── policy.py                         # runtime pre-filter / rephrase / safety gate
│   ├── templates.py                       # system prompt template(s), see section 11
│   └── budget.py                           # context-window token budgeting
├── llm/
│   └── brain.py                            # local LLM runtime wrapper — sole caller of the model
├── tts/
│   └── engine.py                            # local TTS engine wrapper
├── memory/
│   ├── db.py                                 # SQLite connection/session management
│   ├── repositories.py                        # session / step_event / profile / facts repositories
│   └── migrations/                             # versioned schema migrations
├── storage/
│   ├── paths.py                                 # resolves data/model/log/snapshot paths from config
│   └── snapshots.py                              # optional ephemeral image retention (off by default)
├── logging_/
│   └── logger.py                                  # structured local logger + rotation
├── cli/
│   └── debug_cli.py                                # `insight status`, `insight tail`, `insight sessions`, ...
├── models/                                          # GGUF/ONNX model files (gitignored, config-referenced)
├── data/
│   └── insight.db                                    # SQLite database file
└── logs/
    └── insight.log                                    # rotated local log file
```

### How this splits into separate processes later, without a redesign

Every module boundary above is deliberately **message-shaped, not
function-call-shaped**: `audio_io` doesn't call into `asr` directly, it
publishes a `SpeechCaptured` event onto `core/event_bus.py`, which `asr`
subscribes to; `asr` doesn't call into `prompt` directly, it publishes
`TranscriptReady`; and so on through `vision`, `session`, `prompt`, `llm`,
and `tts`. The event bus is in-process (a simple typed queue) for v1, but
because every payload crossing it is already a small, serializable
struct (event type + JSON-able fields, never a live object reference or
an open file handle), the extraction path later is:

1. Replace `core/event_bus.py`'s in-process queue with a real local
   transport (Unix domain socket, or a lightweight local message queue).
2. Move `audio_io/` + `asr/` into a "voice" process, `vision/` into a
   "vision" process, `llm/` into an "inference" process — each keeps its
   own copy of `core/events.py` as its wire schema.
3. `memory/` stays wherever `session/` and `prompt/` live (or becomes its
   own tiny storage service) since it's the one module every other module
   depends on for persistence.

No module's internal logic changes in this migration — only the transport
underneath the event bus and where each module's process boundary is
drawn.

---

## 3. State machine

### States

- **Sleep** — resting state. Only the wake-word detector samples the
  microphone (small rolling buffer, low CPU). ASR, camera, and LLM are
  fully idle (model may stay resident in RAM to avoid reload latency, but
  performs no inference). This is the default state after any period of
  inactivity and is the privacy-safe "at rest" state.
- **Idle-Awake** — the user has woken Insight and it's waiting for a
  command. Full audio pipeline (VAD + ASR) is warm. **Camera remains
  off** unless the very utterance that enters this state is itself a
  vision-trigger phrase. If nothing is said within `idle_awake_timeout_s`,
  Insight returns to Sleep.
- **Task Session** — an active task is in progress. Session context
  exists in memory (and is persisted incrementally to SQLite). The user
  can ask follow-ups, request another vision capture, or issue control
  phrases ("next step," "that worked") without repeating the wake word,
  as long as they stay within `session_timeout_s` of the last turn.
- **Error / Degraded** — a subsystem has failed in a way the app can't
  silently route around (mic device lost, model failed to load, DB file
  corrupted/unwritable, disk full, camera hardware fault during a
  required capture). Insight stays alive, reports its degraded status via
  the CLI and logs, and attempts bounded automatic recovery; it does not
  crash the process for a single subsystem's failure whenever the failure
  is isolated to that subsystem (see section 9 for degraded-mode
  behavior per subsystem).

### Transitions

| From | To | Trigger |
|---|---|---|
| *(process start)* | Idle-Awake | Service boot — default entry state is Idle-Awake, not Sleep, so a freshly powered-on device is immediately responsive. |
| Sleep | Idle-Awake | Wake word **"Insight"** detected, or talk button pressed. |
| Idle-Awake | Sleep | `idle_awake_timeout_s` elapses with no recognized utterance; or voice command "go to sleep" / "stop listening". |
| Idle-Awake | Task Session | A recognized task-shaped utterance (any real question/request); or a vision-trigger phrase ("what's this," "what am I looking at"); or the talk-button used as a shutter (single press = talk, held/double-press = vision capture, per `interaction.vision_trigger_mode` config). |
| Task Session | Task Session *(self-loop)* | Any follow-up utterance within `session_timeout_s`: "next step," "that didn't work," a new vision-capture request, or "start over" (clears step history but keeps the session open). |
| Task Session | Idle-Awake | Explicit "stop helping" / "that's all" / "thanks that's it"; or "that worked" with no further ask; or `session_timeout_s` elapses with no activity. Ending a session always lands in Idle-Awake first (a brief grace window) rather than jumping straight to Sleep, in case the user has one more quick ask. |
| *any state* | Error / Degraded | Unrecoverable subsystem fault detected (see section 9). |
| Error / Degraded | Sleep | Automatic recovery succeeds and no session context existed at time of fault; or operator runs `insight set-state sleep`. |
| Error / Degraded | Idle-Awake | Automatic recovery succeeds while a session existed (the prior session is marked `abandoned`; the user starts fresh from Idle-Awake). |

### State diagram

```
                         wake word "Insight" / talk button
        ┌────────┐ ─────────────────────────────────────▶ ┌─────────────┐
        │ Sleep  │                                          │ Idle-Awake  │
        └────────┘ ◀───────────────────────────────────── └─────────────┘
             ▲         idle_awake_timeout_s / "go to sleep"       │
             │                                                    │ task utterance /
             │                                                    │ "what's this" /
             │  session ends via Idle-Awake grace,                │ vision-trigger
             │  then idle_awake_timeout_s from there               ▼
             │                                            ┌──────────────────┐
             └────────────────────────────────────────────│   Task Session   │
                                                            │ (self-loops on   │
                                                            │  follow-ups)     │
                                                            └──────────────────┘

   any state ──── unrecoverable subsystem fault ────▶ ┌─────────────────┐
                                                        │ Error / Degraded │
   Sleep ◀── recovered, no session ──────────────────  │                  │
   Idle-Awake ◀── recovered, had session ────────────  └─────────────────┘
```

### Default behavior called out explicitly

- **Camera off in Idle-Awake unless explicitly triggered.** `vision/camera.py` only powers the camera inside the specific code path triggered by a vision-trigger utterance or the shutter button — there is no polling, no background frame grabbing, ever, in v1.
- **Wake word or talk button wakes the audio pipeline.** Both are handled identically by `core/orchestrator.py` — they emit the same `WakeDetected` event, so downstream logic never needs to know which one fired.
- **"What's this?" or a shutter action triggers vision capture**, whether it happens fresh from Idle-Awake (starts a new Task Session with a vision-grounded first turn) or mid Task Session (adds a new vision capture to the existing session).
- **Task sessions auto-expire after idle timeout** (`session_timeout_s`), always passing through the Idle-Awake grace window described above before falling further to Sleep.

---

## 4. Model stack

All models are local, CPU-only-compatible, and already validated in this
repo's `poc/` (LLM, vision captioner, ASR, TTS) or are small, well-known
local-only components (wake word, VAD) added for v1's always-listening
front end.

| Role | Component | License | Notes |
|---|---|---|---|
| Wake word detector | **openWakeWord** (ONNX runtime) | Apache-2.0 | Custom "Insight" wake word trained offline via openWakeWord's synthetic-data pipeline (TTS-generated samples — Piper, already in the stack, can generate the synthetic training utterances — plus noise/room augmentation). No cloud training step required. Always-on, sub-300ms detection, negligible CPU. |
| VAD | **Silero VAD** (ONNX) | MIT | ~1 MB model, ~30ms frame hops, used to trim silence and detect end-of-utterance for ASR. |
| ASR | **whisper.cpp** (`base.en`, Pi mode / `small.en`, mini-PC mode) | MIT | Same engine validated in `docs/07-voice-poc.md`. |
| Vision captioner / grounder | **SmolVLM-500M-Instruct** GGUF via `llama.cpp`'s `llama-mtmd-cli` (Pi mode); `SmolVLM2` or a larger SmolVLM variant for mini-PC mode | Apache-2.0 | Same engine validated in `docs/05-vision-poc.md`; output is parsed into the structured `vision_context` shape defined in section 8, not passed through as free text. |
| Instruction-tuned LLM ("the brain") | **Phi-3.5-mini-instruct**, `Q4_K_M` GGUF via `llama.cpp` / `llama-cpp-python` (Pi mode); same model at `Q5_K_M`/`Q6_K`, or a larger permissively-licensed model (e.g. Qwen2.5-7B-Instruct, Apache-2.0) for mini-PC mode | MIT | Same model and runtime validated in `docs/08-model-swap-mit.md`. |
| TTS | **Piper**, `en_US-lessac-low` (Pi mode) / `en_US-lessac-high` (mini-PC mode) | — (Piper project; verify current license terms of the specific voice/engine build in use before shipping) | Same engine validated in `docs/07-voice-poc.md`. |

### Hard assumptions — latency and token limits (Pi 5, 8 GB)

- Wake word detection: **< 300 ms** from utterance start.
- VAD end-of-speech decision: **< 300 ms** after the user stops talking.
- ASR (whisper.cpp `base.en`, ≤ 8s utterance): **1–3 s**.
- Vision capture + caption (SmolVLM-500M, single frame): **1–3 s**.
- LLM decode (Phi-3.5-mini-instruct `Q4_K_M`): **4–7.5 tok/s**; `max_tokens` is hard-capped at **140** in Pi mode, bounding worst-case generation time to roughly **20–25 s** and typical generation (60–90 tokens for a 1–4 step spoken answer) to **8–15 s**.
- TTS synthesis (Piper, low/medium voice): **< 1.5 s** for a typical reply, faster than real-time playback.
- **Context window (`n_ctx`): hard-capped at 2048 tokens in Pi mode** (keeps KV-cache RAM small alongside the vision model and ASR model sharing the same 8 GB); raised to 4096–8192 in mini-PC mode. See section 8 for how the token budget inside that window is allocated.
- **End-to-end target, vision-grounded question, Pi mode:** ≤ 12 s typical, ≤ 25 s worst case. **Mini-PC mode target:** ≤ 5 s typical.

---

## 5. Prompt policy

### Requirements every LLM call must satisfy

- Identify Insight as a fully offline assistant (no browsing, no live data).
- Default to **1–4 concrete steps**, never a long explanation, unless the user explicitly asks for more detail (`{detail_level}` placeholder, section 11).
- Never bluff: if the available context (vision, task summary, or the question itself) doesn't support a confident answer, say what's missing instead of guessing.
- Warm, encouraging, mechanically inclined tone — competent shop-buddy, not a chatbot and not a textbook.
- Handle arbitrary situational questions (not just repair/DIY) without sounding like a narrow "repair bot" that's confused by an off-topic question — it should answer plainly and, if relevant, gently steer back toward being useful for the physical task at hand.
- Apply the safety policy (section 6) inline, every call, unconditionally — it is part of the system prompt itself, not a separate call or a moderation pass.

### Runtime policy block (pre-filter / rephrase, applied by `prompt/policy.py` before every LLM call)

This is an ordered set of checks the orchestrator runs on every recognized
utterance **before** it becomes an LLM call. Several of these paths never
reach the LLM at all:

1. **Control-phrase check first.** If the utterance matches a known
   control phrase ("next step," "that worked," "that didn't work," "start
   over," "stop helping," "go to sleep"), route it directly to
   `session/command_router.py` and the state machine — **do not** send it
   to the LLM. This keeps control latency near-zero and keeps the LLM's
   context free of pure mechanics.
2. **Self-harm / crisis check.** Run a lightweight local keyword/phrase
   classifier (no network call) against the utterance. If flagged,
   short-circuit straight to the hard-refusal safety response (section 6)
   without assembling the normal prompt bundle at all.
3. **Vision-staleness check.** If the current turn references "this" /
   "it" / "that" and no vision context exists yet, or the existing vision
   context is older than `interaction.vision_context_ttl_s`, inject an
   explicit `vision_context: null` marker rather than silently reusing
   stale data, and let the prompt template's instruction to "ask what's
   missing" handle it.
4. **ASR normalization.** Strip filler artifacts and normalize
   punctuation/casing quirks from the ASR transcript before it's embedded
   in the prompt (cheap text cleanup, not a rewrite of meaning).
5. **Budget check.** Hand the cleaned utterance, current task summary, and
   vision context to `prompt/budget.py` to confirm the assembled prompt
   fits the active `n_ctx` (section 8); if not, the summarizer compresses
   further before assembly, never by truncating the current utterance.

Only utterances that pass all of the above are assembled into the full
prompt (section 11) and sent to `llm/brain.py`.

---

## 6. Safety policy

These rules are deliberately short enough to live directly inside the
system prompt (see the literal block in section 11) as well as being
enforced procedurally by the pre-filter in section 5.

- **Self-harm / suicide — hard refusal, not a deflection.** If the user's
  words suggest self-harm, suicidal ideation, or intent to hurt
  themselves or someone else, Insight immediately drops the
  repair-coach framing for that turn. It responds with a short, calm,
  caring message, does not provide any method/means information under
  any framing, and encourages reaching out to a trusted person or, if
  there's any indication of immediate danger, emergency services or a
  crisis line. It does not continue the interrupted task in the same
  turn — it waits for the user's next words.
- **Electrical, fire/gas, structural, high-voltage automotive
  (EV battery packs, airbags), and invasive medical/first-aid topics —
  conservative by default.** Insight stays useful for the low-risk version
  of these tasks (e.g., "how do I reset a tripped breaker," "how do I
  check my tire pressure") but does not give step-by-step instructions for
  irreversible or high-risk invasive procedures (e.g., opening a live
  panel, disassembling an EV battery pack, working on a pressurized gas
  line). In those cases it names the risk plainly, gives the single
  safest immediate action (usually: stop, de-energize/de-pressurize if
  safe to do so, and call a licensed professional), and does not proceed
  further into the procedure even if asked again in the same session.
- **Escalation language** (used consistently, not improvised per turn):
  *"This looks like it could be dangerous — here's the safest next step:
  [stop / call a professional / don't proceed] ..."* — short, direct, no
  hedging filler, no lecture.
- **Everything else** gets Insight's normal short, concrete, practical
  answer — the safety policy is a narrow set of exceptions, not the
  default posture, so Insight doesn't become unhelpfully cautious about
  ordinary tasks.

---

## 7. Memory and sessions

### SQLite schema (practical level — exact column types are an
implementation detail, but names, relationships, and intent are fixed)

```sql
-- One row per task session (a "help me do X" episode).
CREATE TABLE sessions (
  id              TEXT PRIMARY KEY,      -- uuid
  started_at      TEXT NOT NULL,
  ended_at        TEXT,
  status          TEXT NOT NULL,         -- active | completed | abandoned
  outcome         TEXT,                  -- success | failure | unknown
  category        TEXT,                  -- repair | diy | appliance | automotive | code | general
  task_summary    TEXT,                  -- rolling, rule-compressed summary (section 8)
  device_id       TEXT NOT NULL REFERENCES device_profile(id)
);

-- One row per turn/action within a session — the append-only history.
CREATE TABLE step_events (
  id              TEXT PRIMARY KEY,
  session_id      TEXT NOT NULL REFERENCES sessions(id),
  ts              TEXT NOT NULL,
  role            TEXT NOT NULL,         -- user | assistant | system | control
  type            TEXT NOT NULL,         -- utterance | vision_capture | llm_response | control_command
  content_text    TEXT,                  -- transcript / response text / control phrase (never raw audio)
  vision_ref      TEXT,                  -- JSON caption+tags blob, if type = vision_capture (never raw image bytes by default)
  outcome_flag    TEXT,                  -- success | failure | null — set by "that worked" / "that didn't work"
  latency_ms      INTEGER
);

-- Effectively one row in v1 (the primary user), schema allows more later.
CREATE TABLE user_profile (
  id                  TEXT PRIMARY KEY,
  name                TEXT,
  preferred_detail    TEXT DEFAULT 'short',   -- short | detailed
  voice_pref          TEXT,
  created_at          TEXT NOT NULL,
  updated_at          TEXT NOT NULL
);

-- One row per physical device instance.
CREATE TABLE device_profile (
  id                TEXT PRIMARY KEY,
  hardware_type     TEXT NOT NULL,        -- pi5 | minipc
  model_config_name TEXT NOT NULL,        -- which named profile from config is active
  software_version  TEXT,
  last_boot_at      TEXT
);

-- Small set of durable, explicitly-confirmed long-term facts.
CREATE TABLE memory_facts (
  id                  TEXT PRIMARY KEY,
  user_id             TEXT NOT NULL REFERENCES user_profile(id),
  fact_text           TEXT NOT NULL,       -- e.g. "2016 Honda Civic, 1.5T"
  category            TEXT,                -- vehicle | appliance | tool | preference
  confidence          REAL,
  source_session_id   TEXT REFERENCES sessions(id),
  active              INTEGER NOT NULL DEFAULT 1,
  created_at          TEXT NOT NULL,
  last_confirmed_at   TEXT
);
```

### Ephemeral (RAM only) vs. persisted

| Ephemeral — RAM only, never written to disk | Persisted — SQLite |
|---|---|
| Raw microphone audio buffers | Session metadata (`sessions`) |
| Wake-word / VAD internal state | Turn-by-turn text history (`step_events.content_text`) |
| In-flight ASR partial hypotheses | Structured vision captions/tags as JSON text (`step_events.vision_ref`) — **not** raw image bytes, unless `storage.retain_snapshots: true` is explicitly set |
| Raw camera frame bytes/tensors | User profile, device profile |
| In-flight LLM token stream buffer | Long-term memory facts, only after explicit confirmation |
| In-flight TTS audio buffer | Log lines (redacted per `logging` config, section 10) |

### Session lifecycle

- **Start:** a new `sessions` row is created the moment Idle-Awake
  transitions to Task Session (on the first task utterance or vision
  trigger). `category` is inferred cheaply from the first utterance/vision
  tags; `task_summary` starts as a one-line restatement of the request.
- **Update:** every turn appends one or more `step_events` rows. Every
  `N` turns (config: `interaction.summary_refresh_turns`, default 3) or
  whenever the token budget check in section 8 would otherwise be
  exceeded, `session/summarizer.py` recomputes `task_summary` using a
  **rule-based** compression (not another LLM call, to keep this
  deterministic and cheap) — keep the original request, keep the most
  recent outcome flag, keep the last vision context tags, drop
  intermediate turns to a one-line count ("3 steps tried so far").
- **End:** triggered by "stop helping," "that worked" with no follow-up,
  or `session_timeout_s`. Sets `status` and `outcome`, sets `ended_at`,
  transitions the state machine to Idle-Awake.
- **Reset ("start over"):** does **not** end the session row — it inserts
  a `control` step event marking the reset point, clears the in-memory
  working history used for prompt assembly back to just the original
  request, and continues in Task Session. This preserves the full history
  for later inspection via the CLI while giving the LLM a clean slate.

### Voice command → state/session mapping

| Phrase | Effect |
|---|---|
| "start over" | Session stays open; working history reset to the original request; `control` step event logged. |
| "that worked" | Last relevant step marked `outcome_flag = success`; session `outcome = success`; if no further utterance follows within the Idle-Awake grace window, session ends as `completed`. |
| "that didn't work" | Last relevant step marked `outcome_flag = failure`; LLM is asked for an alternative next step in the same session (no session-ending). |
| "next step" | Advances the session without the user re-explaining anything; prompt assembly uses `task_summary` + last step only, not full history (see section 8). |
| "stop helping" | Session ends immediately (`status = abandoned` unless a prior "that worked" already set `success`); transitions Task Session → Idle-Awake. |

---

## 8. Vision + language pipeline

Vision is **on-demand only** — there is no polling loop, no background
capture, and no frame ever leaves `vision/` as raw bytes into any other
module.

### Trigger flow

1. **Trigger.** Explicit voice phrase ("what's this," "what am I looking
   at," "can you see this") recognized by ASR + a lightweight intent
   check in `prompt/policy.py`; **or** the talk button used in its
   shutter mode (`interaction.vision_trigger_mode: hold` or `double_press`,
   config-selected).
2. **Camera power-on + capture.** `vision/camera.py` powers the camera
   (if not already on for a rapid follow-up capture within
   `vision.warm_window_s`), captures a short burst (default 3 frames,
   config: `vision.burst_frames`), and picks the sharpest by a cheap
   local sharpness heuristic (e.g., variance of Laplacian) — no ML model
   needed for this step.
3. **Preprocess.** Resize to the captioner's expected input resolution
   (`vision.capture_resolution`, profile-dependent, section 9), correct
   orientation.
4. **Caption / ground.** The captioner produces a **structured** result —
   not free text passed straight into the prompt:

   ```json
   {
     "caption": "a stainless steel pot of water on a lit gas burner",
     "tags": ["pot", "stovetop", "gas burner", "flame"],
     "hazard_hints": ["open flame", "possible hot surface"],
     "confidence": 0.81
   }
   ```

5. **Confidence gate.** If `confidence` is below `vision.min_confidence`
   (default **0.35**) or the captioner returns an empty/degenerate result,
   `vision_context` is passed to the prompt as an explicit low-confidence
   marker rather than the raw (unreliable) caption — **the app does not
   let the LLM guess** when vision itself wasn't confident. In this case
   the assembled prompt instructs the model to ask the user to point the
   camera more directly or describe what they see, rather than
   fabricating detail.
6. **Prompt bundle assembly.** `prompt/templates.py` combines the system
   prompt, safety policy, `task_summary`, `vision_context` (or the
   low-confidence marker), and `current_utterance` (section 11).
7. **LLM response**, then **8. TTS output.**

### Context window budget (Pi mode, `n_ctx = 2048`)

| Component | Token budget |
|---|---|
| System prompt + safety policy (fixed) | ~300 |
| `task_summary` (rule-compressed, section 7) | ~150 |
| `vision_context` (structured JSON, when present) | ~150 |
| `current_utterance` | ~100 |
| Reserved for generation (`max_tokens`, section 4) + safety margin | ~1300+ |

History beyond the last one or two verbatim turns is **never** replayed
into the prompt in full — only `task_summary`. This is a deliberate,
simple, rule-based design for v1: it keeps latency and memory bounded and
avoids the complexity (and cost) of an LLM-based summarization pass. If a
future revision needs richer long-context recall, that's an isolated
change to `session/summarizer.py` and `prompt/budget.py` — it does not
touch `llm/brain.py`, the prompt template's placeholder shape, or any
other module.

---

## 9. Hardware and performance

### Base assumptions

- Raspberry Pi 5, 8 GB RAM, active cooling, fast local storage (USB3 SSD
  or NVMe HAT preferred over microSD for model load latency — see
  `docs/04-pi-deployment.md`).
- Local USB or I2S microphone; local speaker or earbuds (wired or
  Bluetooth) for TTS output.
- Optional Camera Module (CSI on Pi 5; USB/V4L2-compatible on a mini-PC)
  — entirely optional at the hardware level; if absent, vision-trigger
  phrases get a spoken "no camera available" response instead of an
  error state.
- All of the above is abstracted behind `device.profile` in config — no
  code path should ever hard-check "am I a Pi" outside of `vision/camera.py`'s
  backend selection and `config/loader.py`'s profile resolution.

### Defaults by profile

| Setting | Pi mode (default) | Mini-PC mode |
|---|---|---|
| LLM model / quant | Phi-3.5-mini-instruct, `Q4_K_M` | Phi-3.5-mini-instruct, `Q6_K` (or larger Apache/MIT model) |
| `n_ctx` | 2048 | 4096–8192 |
| `n_threads` | 4 | `os.cpu_count()` or configured cap |
| `max_tokens` | 140 | 220 |
| `temperature` | 0.3 | 0.3 |
| `top_p` | 0.9 | 0.9 |
| VAD sensitivity threshold | 0.5 | 0.5 |
| `idle_awake_timeout_s` | 10 | 10 |
| `session_timeout_s` | 60 | 90 |
| Vision capture resolution | 512×512 | 768×768 |
| ASR model | whisper.cpp `base.en` | whisper.cpp `small.en` |
| TTS voice quality | `en_US-lessac-low` | `en_US-lessac-high` |

Everything in this table is a config value under `models` / `interaction`
/ `vision` (section 10) — moving Insight from a Pi 5 to a mini-PC means
changing `device.profile: pi5` to `device.profile: minipc` (and pointing
`models.*` at the larger files), not touching any module's code.

### Degraded-mode behavior per subsystem (Error/Degraded state)

- **Mic/audio device lost:** retry with backoff (e.g. 3 attempts over
  10s); if still failing, stay in Error/Degraded, log continuously at a
  throttled rate (not per-attempt spam), expose status via `insight status`.
- **Camera hardware fault:** does **not** force the whole app into
  Error/Degraded — a vision trigger simply fails gracefully with a
  spoken "I can't access the camera right now" and the session continues
  voice-only.
- **Model load failure (LLM/ASR/TTS/vision):** app enters Error/Degraded
  at boot if a *required* model fails to load; a *non-critical* model
  (e.g., vision captioner) failing to load instead disables that
  capability with the same graceful voice-only fallback as a camera fault.
- **SQLite unavailable/corrupt:** app enters Error/Degraded; in-memory
  session state continues to function for the current interaction (so a
  DB hiccup mid-conversation doesn't cut the user off), but nothing new
  persists until recovered; this is logged clearly and surfaced via the CLI.

---

## 10. Config, logging, and local library hooks

### Config file

Single human-editable YAML file (`config/default.yaml`, overridable via a
user config path). Structure:

```yaml
device:
  profile: pi5                  # pi5 | minipc — drives every default in section 9
  talk_button_gpio: 17          # ignored on minipc profile
  camera_backend: csi           # csi | usb

models:
  wake_word_model: models/wake/insight.onnx
  vad_model: models/vad/silero_vad.onnx
  asr_model: models/whisper/ggml-base.en.bin
  vision_model: models/vision/SmolVLM-500M-Instruct-Q8_0.gguf
  vision_mmproj: models/vision/mmproj-SmolVLM-500M-Instruct-Q8_0.gguf
  llm_model: models/llm/Phi-3.5-mini-instruct-Q4_K_M.gguf
  tts_voice: models/tts/en_US-lessac-low.onnx

audio:
  vad_threshold: 0.5
  max_utterance_s: 12
  input_device: default
  output_device: default

vision:
  min_confidence: 0.35
  capture_resolution: [512, 512]
  burst_frames: 3
  warm_window_s: 5

interaction:
  wake_phrase: "insight"
  idle_awake_timeout_s: 10
  session_timeout_s: 60
  vision_trigger_mode: hold      # hold | double_press
  vision_context_ttl_s: 30
  summary_refresh_turns: 3
  default_detail_level: short    # short | detailed

safety:
  self_harm_hard_refusal: true
  conservative_domains: [electrical, fire_gas, structural, automotive_hv, medical_invasive]

storage:
  db_path: data/insight.db
  retain_snapshots: false        # if true, saves last N vision frames to disk (off by default)
  snapshot_retention_count: 5

logging:
  level: info                    # debug | info | warn | error
  log_dir: logs/
  max_file_mb: 10
  backup_count: 5
  log_transcripts: false         # if true, log short excerpts only (see below)
  transcript_excerpt_chars: 120

library:                          # Phase 2 placeholder — inert in v1
  enabled: false
  index_path: null
  doc_dirs: []
```

### Logging rules

- **Local only, no network sink, ever.**
- **No raw audio is ever written to disk**, in any log level.
- **No raw image bytes are logged**; vision output in logs is the same
  structured JSON caption stored in `step_events.vision_ref`.
- By default (`log_transcripts: false`), logs contain event types,
  timings, state transitions, and error detail — **not** user speech
  content. The durable record of what was actually said/answered lives in
  SQLite (`step_events`), which is the intended source of truth for
  session content; logs are for operations/debugging.
- If `log_transcripts: true` is explicitly set, only a short excerpt
  (`transcript_excerpt_chars`, default 120) of each transcript/response is
  included in the log line — full text still only lives in SQLite.
- Rotation is size-based (`max_file_mb`, `backup_count`) — no unbounded
  log growth on constrained storage.

### Local CLI / debug utilities (`insight` command, separate from the service)

- `insight status` — current state, uptime, which models are loaded, last error (if any).
- `insight tail` — follow the live log.
- `insight sessions list` / `insight sessions show <id>` — inspect session history from SQLite.
- `insight replay-last-capture` — dump the last vision caption JSON (and the snapshot image, if retention was enabled).
- `insight test-mic` / `insight test-speaker` — quick hardware sanity checks.
- `insight set-state <state>` — force a state transition, for debugging (e.g., manually clearing Error/Degraded).
- `insight config validate` — validate the active config file against the schema without starting the service.

### Local manual/library hooks (Phase 2, inert in v1)

The `library` config block above and a defined extension point in
`prompt/` are the only Phase 2 groundwork laid in v1: `prompt/templates.py`
accepts an optional additional "retrieved context" slot in the same shape
as `vision_context` (structured, budgeted, confidence-gated). In Phase 2,
a `library/` module (a document/manual retriever) would populate that slot
by publishing the same kind of event the vision pipeline does today. No
change to the prompt template's placeholder shape or to `llm/brain.py` is
required to add it later — v1 simply never populates it.

---

## 11. Final prompt template

Literal system prompt, parameterized per call. This is the exact string
`prompt/templates.py` renders and passes as the `system` message on every
LLM call (paired with the assembled user message containing
`{current_utterance}`, `{vision_context}`, and `{task_summary}` as shown).

```text
You are Insight, a fully offline AI coach. You have no internet access
and no live data — you only know what the user tells you and what you
can see through the camera when it's used.

Your job: give short, concrete, practical help for repair, DIY,
appliance, automotive, code-on-screen, and everyday situational
questions. You are warm, encouraging, and mechanically inclined — a
competent shop-buddy, not a chatbot and not a textbook.

Rules:
- Prefer 1-4 short, concrete steps over any explanation. Detail level:
  {detail_level}.
- Never bluff. If you don't have enough information (from the question,
  the task summary, or what you can see), say plainly what you'd need to
  know instead of guessing.
- Be conservative about electrical, fire/gas, structural, high-voltage
  automotive, and invasive medical situations: give the single safest
  immediate action (usually: stop, de-energize/de-pressurize if it's safe
  to do so, and call a licensed professional) rather than step-by-step
  instructions for anything irreversible or high-risk. Use this framing
  when needed: "This looks like it could be dangerous - here's the safest
  next step: ..."
- If the user's words suggest self-harm or suicidal intent, stop the
  current task, respond with a short, calm, caring message, provide no
  method/means information under any framing, and encourage reaching out
  to a trusted person or, if there's any sign of immediate danger,
  emergency services or a crisis line. Do not continue the interrupted
  task in the same reply.
- Never write code, code blocks, or long-form essays. Never use markdown
  formatting, bullet lists, or headings - this response will be spoken
  aloud, not read.
- Handle ordinary or off-topic questions plainly and helpfully; you are
  not limited to repair topics, you just happen to be especially good at
  them.

Context for this turn:
- User: {user_name}
- Task so far: {task_summary}
- What the camera currently sees: {vision_context}

User's current question: {current_utterance}

Respond briefly, clearly, and out loud - as if speaking, not writing.
```

**Placeholder notes:**
- `{user_name}` — from `user_profile.name`; falls back to a neutral
  greeting-free phrasing if unset (v1 does not require the user to set a name).
- `{detail_level}` — `short` (default) or `detailed`, from
  `interaction.default_detail_level` or a per-session override.
- `{task_summary}` — the rolling, rule-compressed summary from section 7;
  literal string `"(no active task yet)"` when Idle-Awake is transitioning
  into a brand-new Task Session.
- `{vision_context}` — the structured JSON caption from section 8, or the
  literal string `"(no visual context available)"` when there is none or
  it failed the confidence gate — never silently omitted, so the model
  always knows whether it has visual grounding or not.
- `{current_utterance}` — the cleaned (section 5, step 4) ASR transcript
  of the user's current turn.
