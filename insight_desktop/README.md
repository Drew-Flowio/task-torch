# Insight — local desktop companion app

A native desktop app (PySide6, not a browser wrapper) for talking to your
offline "Insight" personality, typed or spoken, and for inspecting and
tuning exactly how it behaves. Fully offline: no cloud services, no
hosted APIs, no telemetry, no remote model calls. Everything — the LLM,
speech-to-text, and text-to-speech — runs as a local process on this
machine.

This app reuses the exact models and tools already validated elsewhere in
this repo (`docs/01`, `docs/07`, `docs/08`): Phi-3.5-mini-instruct (MIT
license) as the brain, whisper.cpp for speech-to-text, and Piper for
text-to-speech. It does not duplicate those multi-GB files — its config
points at the same `models/` and `vendor/` folders already set up at the
repo root.

## Quickstart

### Option A — double-click the Desktop app (recommended)

```bash
cd "Task Torch"
source .venv/bin/activate
pip install -r insight_desktop/requirements.txt
bash insight_desktop/packaging/build_app.sh
```

This builds **Insight.app** and installs a copy to **`~/Desktop/Insight.app`**. Double-click it to launch.

**If your project folder is on the Desktop** (like `~/Desktop/Task Torch`), macOS privacy rules block double-clicked apps from reading Desktop files. The launcher automatically opens a small **Terminal** window to start Insight with the right permissions — that's expected. You can minimize Terminal; Insight's window is the main UI.

For a cleaner double-click launch with no Terminal window, either:
- Move the project to something like `~/Projects/Task Torch`, then re-run `bash insight_desktop/packaging/build_app.sh`, or
- Grant **Full Disk Access** to Insight in **System Settings → Privacy & Security → Full Disk Access** (add `~/Desktop/Insight.app`).

If the app still fails, check `insight_desktop/logs/launcher.log`.

### Option B — run from the terminal

```bash
cd "Task Torch"
source .venv/bin/activate
pip install -r insight_desktop/requirements.txt
python insight_desktop/app/main.py
```

The first run creates `insight_desktop/data/insight_app.db` (SQLite) and
seeds it with the personality prompt from `insight_desktop/prompts/system_prompt.txt`.

**Don't have the models downloaded / just want to try the UI first?** Set
`engine.mock_mode: true` in `insight_desktop/config/config.yaml` and run
the same command — you'll get instant, canned responses with no models
loaded, useful for a quick smoke test of the whole app.

## What you can do in the app

- **Type or talk.** A text box + Send button, and a microphone button:
  click once to start recording, click again ("Stop & Send") to stop,
  transcribe, and send. A separate Stop button cancels whatever's
  currently happening — recording, thinking, or speaking.
- **Hear replies.** Voice turns are spoken back through Piper automatically.
- **See the conversation.** The chat pane shows the full session history
  and streams the assistant's reply token-by-token as it's generated.
- **Inspect the personality.** The right-hand panel has three tabs:
  - **Personality** — the exact system prompt in use, editable in place.
    Saving creates a new *version* (nothing is overwritten/lost); double-click
    any past version in the history list to make it active again — this is
    how you compare how different prompt wording changes the replies.
  - **Memory & Session** — current session summary, long-term memory
    facts (add/remove freely; these persist across resets), and the two
    reset buttons.
  - **Last Answer** — the exact, fully-assembled prompt (personality +
    memory facts + recent history + your message) that produced the most
    recent reply, plus its latency. This is the "why did it answer that
    way" view.

## Directory layout

```
insight_desktop/
├── app/
│   ├── main.py            # entrypoint: loads config, builds the engine, starts the Qt app
│   └── logging_setup.py    # local rotating file + console logging
├── engine/                  # everything model/storage-related - the UI never reaches past this layer
│   ├── interface.py          # InsightEngine - the one class the UI calls
│   ├── llm_adapter.py          # llama-cpp-python wrapper (streaming chat completion)
│   ├── stt_adapter.py           # whisper.cpp wrapper
│   ├── tts_adapter.py            # Piper wrapper + playback
│   ├── audio_recorder.py          # microphone capture (sounddevice)
│   ├── prompt_builder.py           # assembles the exact message list sent to the LLM
│   ├── session.py                   # session/turn history + the ephemeral/session/long-term memory split
│   ├── mock_adapters.py              # canned LLM/STT/TTS stand-ins for engine.mock_mode
│   └── types.py                       # AppState, TurnResult, SessionStateView - the UI<->engine contract
├── storage/
│   ├── db.py                # SQLite connection + schema
│   ├── repository.py         # the only place that runs SQL
│   └── models.py              # Session / Message / PromptVersion / MemoryFact dataclasses
├── prompts/
│   └── system_prompt.txt    # the editable personality prompt (source of truth, versioned in SQLite on save)
├── ui/
│   ├── main_window.py       # the main window: chat pane, input row, status
│   ├── inspector_panel.py    # the personality/memory/debug side panel
│   ├── chat_widgets.py         # the chat transcript widget (bubbles, streaming)
│   └── workers.py               # QThread wrappers so engine calls never block the UI
├── config/
│   ├── config.yaml          # human-editable settings (models, audio, timeouts, logging)
│   └── loader.py              # loads + resolves config.yaml into typed config objects
├── data/                     # insight_app.db lives here (gitignored)
└── logs/                      # insight_app.log lives here (gitignored)
```

## Architecture

**UI and engine are fully separated.** `ui/` only ever calls methods on
`InsightEngine` (`engine/interface.py`) and only ever receives plain
dataclasses or strings back — it never imports `llama_cpp`, `piper`,
`whisper`, or `sqlite3` directly. That boundary is what makes it possible
to swap the LLM, STT, or TTS engine (or flip on mock mode) by editing
`config/config.yaml` alone, with zero changes to any file in `ui/`.

```
InsightEngine (engine/interface.py)
  ├─ send_text_message(text, on_token, on_state) -> TurnResult
  ├─ start_recording(on_state) / cancel_recording(on_state)
  ├─ send_voice_utterance(on_transcript, on_token, on_state) -> TurnResult | None
  ├─ speak(text, on_state)
  ├─ cancel_current()                     # the Stop button's one entry point
  ├─ get_session_state() -> SessionStateView
  ├─ get_system_prompt() / update_prompt(text, label) / get_prompt_history() / activate_prompt_version(id)
  ├─ list_memory_facts() / add_memory_fact(text) / remove_memory_fact(id)
  ├─ get_history() -> list[Message]
  └─ reset_memory(scope="session" | "all")
```

Internally, `InsightEngine` holds one `LlmAdapter`, one `SttAdapter`, one
`TtsAdapter` (or their mock equivalents), one `Repository` (SQLite), one
`SessionManager`, and one `PromptBuilder`. None of those five know about
each other directly or about Qt — `InsightEngine` is the only thing that
wires them together, the same "wire modules together in one place, keep
every module boundary a clean, swappable contract" approach used in the
headset spec (`docs/09-insight-v1-spec.md`). If this app ever needs to
grow into separate processes (e.g., a shared inference server used by
multiple front-ends), the extraction boundary is exactly `engine/` vs.
`ui/` — `engine/interface.py`'s public methods are already
message-shaped (plain strings and dataclasses in, plain strings and
dataclasses out), not sharing any live object references with `ui/`.

### Event flow — typed message

1. User types in the input box, clicks Send (or presses Enter).
2. `MainWindow` appends a user bubble, starts an empty assistant bubble,
   and starts a `TextMessageWorker` (a `QThread`) so the UI stays responsive.
3. The worker calls `engine.send_text_message(text, on_token=..., on_state=...)`.
4. Inside the engine: the active personality prompt + long-term memory
   facts + recent session history are assembled into a message list
   (`PromptBuilder`); the user's message is recorded to SQLite; the LLM
   streams its reply, calling `on_token` for every chunk (which the
   worker turns into a Qt signal that appends to the assistant bubble
   live); the assistant's full reply is recorded to SQLite.
5. The worker emits `finished_ok(TurnResult)`; `MainWindow` finalizes the
   bubble text and refreshes the inspector's "Last Answer" tab with the
   exact assembled prompt and latency.

### Event flow — voice message

Same as above, except before step 2: click the mic button once to start
recording (`engine.start_recording()`, mic button becomes "Stop &
Send"); click it again to stop recording and kick off a
`VoiceUtteranceWorker`, which calls `engine.send_voice_utterance(...)`.
That method stops the recording, transcribes it with whisper.cpp
(temp WAV deleted immediately after — no raw audio is ever kept on disk),
emits the transcript (which the UI turns into the user bubble), runs the
exact same LLM turn pipeline as a typed message, and finally speaks the
reply through Piper before returning to idle.

### Conversation memory model

- **Ephemeral turn context** — the in-flight utterance, the streaming
  token buffer, and the microphone recording buffer. Lives only in local
  variables inside `engine/interface.py` and `engine/audio_recorder.py`;
  never written anywhere. The temp recording WAV is deleted the moment
  transcription finishes.
- **Current session context** — every message in the current conversation,
  persisted to SQLite (`messages` table) as it happens. Only the most
  recent `interaction.history_turns_in_prompt` turns (config, default 6)
  are replayed verbatim into the prompt; anything older collapses into a
  one-line note so the context sent to the LLM stays bounded no matter
  how long the conversation runs (`engine/session.py`).
- **Long-term memory** — `memory_facts` rows. These are not auto-extracted
  by the LLM in v1 (deliberately, to keep this simple and predictable) —
  you add/remove them explicitly from the Memory & Session tab, and every
  active fact is injected into every prompt regardless of how many times
  the conversation itself has been reset.

"Reset conversation" (from the Memory & Session tab) ends the current
session and starts a fresh one — nothing is deleted from SQLite, the old
session's messages just stop being replayed into new prompts. "Full
reset" does the same and also clears long-term memory facts.

## Config reference (`config/config.yaml`)

| Section | Purpose |
|---|---|
| `engine.mock_mode` | `true` = canned responses, no real models loaded |
| `models` | GGUF/model paths + inference knobs (ctx, threads, max tokens, temperature, top_p) for the LLM, plus whisper.cpp and Piper paths |
| `audio` | Sample rate, max recording length, input/output device selection |
| `interaction` | Assistant name, how many turns get replayed verbatim into the prompt |
| `storage.db_path` | Where the SQLite file lives |
| `prompts.system_prompt_path` | The editable personality prompt file, seeded into SQLite on first run |
| `logging` | Log directory, level, and whether transcript text is logged locally (never raw audio) |

All model paths are relative to the repo root (the folder containing
`insight_desktop/`, `poc/`, `models/`, `vendor/`), so swapping to a
different LLM/voice/STT model later is a config edit, not a code change —
see `docs/08-model-swap-mit.md` for how this repo already did exactly
that once.
