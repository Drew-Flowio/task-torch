# Task Torch — Offline AI Headset

A head-mounted, fully offline assistant: point a camera at something, ask a
question out loud, get a short, practical, spoken answer. No cloud, no
network dependency once the device is provisioned.

This repo started as a **"brain first" milestone** and now has the
**complete software loop working end-to-end**: camera frame → vision
description → transcribed spoken question → brain LLM → spoken answer,
entirely offline, validated for real on this Mac and designed to run
unchanged on the Pi 5.

## Target hardware (prototype)

- Raspberry Pi 5, 8 GB RAM, microSD storage, **CPU only** (no GPU/NPU assumed)
- Fully offline at runtime — network is only used once, during setup, to
  pull models and toolchains

## Contents

| Doc | Covers |
|---|---|
| [`docs/01-model-choice.md`](docs/01-model-choice.md) | Candidate brain LLMs, quantization tradeoffs, final recommendation |
| [`docs/02-vision-architecture.md`](docs/02-vision-architecture.md) | Where vision plugs in, candidate vision models |
| [`docs/03-mac-poc.md`](docs/03-mac-poc.md) | Mac terminal commands to download + run the brain model |
| [`docs/04-pi-deployment.md`](docs/04-pi-deployment.md) | Confirms the same model/runtime fits an 8 GB Pi 5 |
| [`docs/05-vision-poc.md`](docs/05-vision-poc.md) | Validated vision → brain pipeline, real commands + real output |
| [`docs/06-hardware-shopping-list.md`](docs/06-hardware-shopping-list.md) | Every physical item needed to build the Pi 5 prototype |
| [`docs/07-voice-poc.md`](docs/07-voice-poc.md) | Validated STT + TTS, closing the full voice-to-voice loop |
| [`docs/08-model-swap-mit.md`](docs/08-model-swap-mit.md) | Record of swapping off Llama/Meta to a fully permissive (MIT) brain model |
| [`docs/09-insight-v1-spec.md`](docs/09-insight-v1-spec.md) | Full v1 product/architecture spec for "Insight" — the productionized version of this PoC |
| [`insight_desktop/`](insight_desktop/) | **Insight desktop app** — native PySide6 companion for typing/talking, personality tuning, and memory |
| [`poc/`](poc/) | Runnable proof-of-concept code (same code path for Mac and Pi) |

## The one-line plan

**Brain:** Phi-3.5-mini-instruct (Microsoft, **MIT license**), `Q4_K_M`
GGUF, run with `llama.cpp` / `llama-cpp-python`. ~2.2–2.4 GB on disk,
~3 GB resident, ~4–7.5 tok/s on a Pi 5 CPU, no coding/essay ability needed
or wanted. See `docs/08-model-swap-mit.md` for why this replaced the
original Llama-3.2-3B-Instruct pick.

**Vision:** SmolVLM-500M-Instruct GGUF, run through `llama.cpp`'s
`llama-mtmd-cli`, producing a one-sentence text description of a camera
frame that feeds straight into the brain's prompt.

**Voice:** whisper.cpp (`base.en`) for speech-to-text, Piper
(`en_US-lessac-medium`) for text-to-speech — both offline, both CPU-only,
both confirmed to run on Pi 5.

**Every stage talks to its neighbor only through plain text (or a WAV
file path)** — `poc/vision.py`, `poc/stt.py`, `poc/brain.py`, and
`poc/tts.py` are the exact modules the final headset firmware will call.
Only the physical I/O around the edges (live camera frame instead of a
file, live microphone recording instead of a file, a real speaker instead
of a saved WAV) still needs to be swapped in for real hardware.

## Status: the full loop works, not just the brain

Every stage below has been built and run for real on this machine — not
just designed:

- `poc/run_llm.py` — brain LLM only, tested against hazard and benign
  scenarios (stove, frayed cable, unidentifiable plant) — see
  `docs/03-mac-poc.md` for real transcripts.
- `poc/pipeline.py` — vision → brain, tested against a real photo
  end-to-end in ~8.8 seconds total on this Mac. See `docs/05-vision-poc.md`.
- `poc/pipeline_voice.py` — the **complete loop**: real photo → synthesized
  spoken question → whisper.cpp transcription → brain answer → Piper
  speech, played back audibly, in ~10.2 seconds total, zero network calls.
  See `docs/07-voice-poc.md` for the exact commands, real output, and a
  saved example answer at `poc/test_audio/example_answer.wav`.

## Quickstart

```bash
# 1. Brain LLM only
bash poc/setup_mac.sh
source .venv/bin/activate
python poc/run_llm.py --model models/Phi-3.5-mini-instruct-Q4_K_M.gguf --threads 8

# 2. Add vision (run setup_mac.sh first)
bash poc/setup_vision_mac.sh
python poc/pipeline.py \
  --image poc/test_images/electric_kettle.jpg \
  --question "is this safe to touch right now?" \
  --llm-model models/Phi-3.5-mini-instruct-Q4_K_M.gguf \
  --vision-model models/SmolVLM-500M-Instruct/SmolVLM-500M-Instruct-Q8_0.gguf \
  --mmproj models/SmolVLM-500M-Instruct/mmproj-SmolVLM-500M-Instruct-Q8_0.gguf \
  --mtmd-cli vendor/llama.cpp/build/bin/llama-mtmd-cli \
  --threads 8

# 3. Add voice (run setup_mac.sh + setup_vision_mac.sh first) — the full loop
bash poc/setup_voice_mac.sh
python poc/pipeline_voice.py \
  --image poc/test_images/electric_kettle.jpg \
  --question-audio poc/test_audio/question_is_it_safe.wav \
  --answer-audio /tmp/headset_answer.wav \
  --mtmd-cli vendor/llama.cpp/build/bin/llama-mtmd-cli \
  --vision-model models/SmolVLM-500M-Instruct/SmolVLM-500M-Instruct-Q8_0.gguf \
  --mmproj models/SmolVLM-500M-Instruct/mmproj-SmolVLM-500M-Instruct-Q8_0.gguf \
  --whisper-cli vendor/whisper.cpp/build/bin/whisper-cli \
  --whisper-model vendor/whisper.cpp/models/ggml-base.en.bin \
  --llm-model models/Phi-3.5-mini-instruct-Q4_K_M.gguf \
  --voice-model models/piper-voices/en/en_US/lessac/medium/en_US-lessac-medium.onnx \
  --threads 8
afplay /tmp/headset_answer.wav   # hear it
```

`models/` and `vendor/` are gitignored — they're multi-GB downloaded/built
artifacts, reproducible any time via the setup scripts in `poc/`.

## What's left before this is the real headset

The software loop is done; what remains is physical I/O and the Pi 5
itself:

1. **Re-validate on the real Pi 5** once it arrives (see
   `docs/06-hardware-shopping-list.md` for parts, `docs/04-pi-deployment.md`
   for the build) — everything here should run unchanged with `--threads 4`.
2. **Swap the file-based stand-ins for live hardware:** a Pi Camera Module
   3 frame instead of `poc/test_images/*.jpg`, a live microphone recording
   instead of `poc/test_audio/*.wav`, and a real speaker/earbuds instead of
   a saved WAV — none of which require changing `vision.py`, `stt.py`,
   `brain.py`, or `tts.py`.
3. **Make it wearable:** power bank, headband/mount — see
   `docs/06-hardware-shopping-list.md`.
