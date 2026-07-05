# 7. Voice proof of concept (validated on Mac) — the full loop closes

This documents standing up speech-to-text and text-to-speech and wiring
them around the already-validated vision → brain pipeline. After this
step, every model in the "look, listen, think, speak" loop has been run
for real, end-to-end, fully offline, on code paths confirmed to build and
run on the Pi 5.

## What was added

- `vendor/whisper.cpp` — built with the `whisper-cli` target (Metal on Mac;
  ARM-tuned CPU build documented for Pi, matching the pattern already used
  for `llama.cpp`).
- `vendor/whisper.cpp/models/ggml-base.en.bin` — the `base.en` model
  (142 MB disk / ~388 MB resident per the upstream project's own published
  figures), a good accuracy/speed balance for Pi 5 (`tiny.en` is the
  faster/lower-accuracy fallback if `base.en` proves too slow on-device).
- Piper (`pip install piper-tts`, the actively maintained
  `OHF-Voice/piper1-gpl` project) + `en_US-lessac-medium`, a 60 MB neural
  voice model.
- `poc/stt.py` — `SpeechToText` class wrapping `whisper-cli`, same
  "shell out to the exact binary you'll run on the Pi" pattern as
  `vision.py`.
- `poc/tts.py` — `TextToSpeech` class wrapping Piper.
- `poc/pipeline_voice.py` — the complete loop: image → vision description,
  question WAV → transcribed text, both → brain answer, answer → spoken
  WAV.
- `poc/test_audio/question_is_it_safe.wav` — a synthesized test question
  ("Is it safe to touch this right now?"), standing in for a real
  microphone recording.

## Setup commands (what `poc/setup_voice_mac.sh` automates)

```bash
# 1. Clone and build whisper.cpp
mkdir -p vendor
git clone --depth 1 https://github.com/ggml-org/whisper.cpp vendor/whisper.cpp
cd vendor/whisper.cpp
cmake -B build -DGGML_METAL=on            # drop -DGGML_METAL=on on the Pi
cmake --build build --config Release -j"$(sysctl -n hw.ncpu)" --target whisper-cli
bash ./models/download-ggml-model.sh base.en
cd ../..

# 2. Install Piper + a voice
source .venv/bin/activate
pip install piper-tts
hf download rhasspy/piper-voices "en/en_US/lessac/medium/en_US-lessac-medium.onnx" --local-dir ./models/piper-voices
hf download rhasspy/piper-voices "en/en_US/lessac/medium/en_US-lessac-medium.onnx.json" --local-dir ./models/piper-voices
```

## Validated: the complete voice-to-voice loop

```bash
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
```

Actual output (re-run after the model swap to `Phi-3.5-mini-instruct`,
documented in `docs/08-model-swap-mit.md`):

```
[1/4] Looking at poc/test_images/electric_kettle.jpg ...
      Vision description (1.1s): A white kettle with gray base sits on a wooden table.
[2/4] Listening to poc/test_audio/question_is_it_safe.wav ...
      Transcribed question (0.3s): 'Is it safe to touch this right now?'
[3/4] Thinking ...
      Answer (7.8s): Without seeing the current temperature or any visible signs of heat, it's not safe to assume it's safe to touch. Please ensure the kettle is not hot before attempting to touch it.
[4/4] Speaking ...
      Wrote spoken answer (1.0s): /tmp/headset_answer.wav
------------------------------------------------------------
Total end-to-end latency: 10.2s (vision 1.1s + stt 0.3s + brain 7.8s + tts 1.0s)
```

`afplay /tmp/headset_answer.wav` (or open the file in Finder) plays the
result back — a real, audible spoken answer, generated with zero network
calls, from a real photo and a real (synthesized-for-testing) spoken
question. A copy of that output is saved at
`poc/test_audio/example_answer.wav`.

One quality note, now favorable: unlike the earlier run with the previous
model (which inferred "it's hot and may be emitting steam" from a
description that only said "a kettle sits on a table"), `Phi-3.5-mini-instruct`
correctly declines to assume heat it can't see evidence of — "without
seeing the current temperature or any visible signs of heat, it's not safe
to assume it's safe to touch." That's exactly the "say what you'd need to
know" behavior the system prompt asks for, and a good sign for the new
model's fit with this product's safety-aware requirements. This kind of
per-model behavioral difference is worth watching for any time you swap
models — see `poc/brain.py`'s header comment for how.

## What was validated vs. what's still a stand-in

| Stage | Validated with | Real headset version |
|---|---|---|
| Vision | Real photo file | Live Pi Camera Module 3 frame |
| STT | Synthesized WAV (macOS `say` → 16kHz mono WAV) | Live microphone recording, same WAV format into `whisper-cli` |
| Brain | Real GGUF model, real inference | Unchanged |
| TTS | Real Piper synthesis, played over Mac speakers | Same WAV played over the headset's speaker/earbuds |

The only remaining stand-ins are on the I/O edges (camera capture,
microphone recording, audio playback device) — every model and every
prompt contract in between is the same code validated here.

## Pi 5 expectations for the voice stack

- **whisper.cpp** (`base.en`): published Pi 5 benchmarks and community
  reports show `tiny.en`/`base.en` transcribing short utterances in roughly
  1-3 seconds on-device — consistent with the "look, ask, wait a beat, get
  an answer" interaction budget.
- **Piper**: reported to run in real time (faster than the audio plays
  back) on a Pi 5 CPU with no GPU — the smallest of the four models in
  this pipeline in practice.
- **Piper install caveat:** requires the **64-bit** Raspberry Pi OS. The
  32-bit-userland image (still common on older Pi setups/tutorials) reports
  `aarch64` from `uname -m` but will fail to resolve a compatible
  `piper-tts` wheel. Verify with `file /bin/ls` — it should say "64-bit,"
  not "32-bit." (This project has assumed 64-bit Raspberry Pi OS
  throughout — see `docs/04-pi-deployment.md`.)
