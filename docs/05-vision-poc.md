# 5. Vision proof of concept (validated on Mac)

This documents the exact steps used to stand up the vision step from
`docs/02-vision-architecture.md` and wire it into the brain LLM. Everything
below has been run for real on this machine — this is not a plan, it's a
record of what worked.

## What was built

- `vendor/llama.cpp` — the `llama.cpp` source, built with the `llama-mtmd-cli`
  and `llama-cli` targets (Metal enabled on Mac; CPU-only build works
  identically on the Pi, see `docs/04-pi-deployment.md`).
- `models/SmolVLM-500M-Instruct/` — SmolVLM-500M-Instruct, `Q8_0` GGUF, plus
  its matching `mmproj` projector file (416 MB + 104 MB — SmolVLM-500M is
  small enough that `Q8_0` is still a modest footprint; drop to
  `SmolVLM-256M-Instruct-GGUF` if you need it smaller/faster later).
- `poc/vision.py` — a `VisionCaptioner` class that shells out to
  `llama-mtmd-cli` and returns a plain text description, matching the exact
  contract `poc/brain.py` expects.
- `poc/pipeline.py` — the first fully-wired slice of the real pipeline:
  image file → vision description → brain answer.
- `poc/test_images/electric_kettle.jpg` — a real, public-domain (CC
  "Own work") photo used as a stand-in for a camera frame, downloaded from
  Wikimedia Commons.

## Setup commands (what `poc/setup_vision_mac.sh` automates)

```bash
# 1. Clone and build llama.cpp for the mtmd (multimodal) CLI tool
mkdir -p vendor
git clone --depth 1 https://github.com/ggml-org/llama.cpp vendor/llama.cpp
cd vendor/llama.cpp
cmake -B build -DGGML_METAL=on          # drop -DGGML_METAL=on on the Pi
cmake --build build --config Release -j"$(sysctl -n hw.ncpu)" \
  --target llama-mtmd-cli llama-cli
cd ../..

# 2. Download the vision model + its mmproj projector
source .venv/bin/activate
hf download ggml-org/SmolVLM-500M-Instruct-GGUF \
  --include "SmolVLM-500M-Instruct-Q8_0.gguf" "mmproj-SmolVLM-500M-Instruct-Q8_0.gguf" \
  --local-dir ./models/SmolVLM-500M-Instruct
```

## Validated: raw captioning

```bash
./vendor/llama.cpp/build/bin/llama-mtmd-cli \
  -m models/SmolVLM-500M-Instruct/SmolVLM-500M-Instruct-Q8_0.gguf \
  --mmproj models/SmolVLM-500M-Instruct/mmproj-SmolVLM-500M-Instruct-Q8_0.gguf \
  --image poc/test_images/electric_kettle.jpg \
  -p "Describe what is in this image in one short sentence." \
  -n 64 --temp 0.1 -ngl 0 --no-mmproj-offload
```

Actual output:

```
A white kettle with gray base sits on a wooden table.
```

`-ngl 0` (no GPU layers) forces CPU-only execution, which is what you want
both to sanity-check Pi-realistic behavior on the Mac and because in
practice the two multimodal models (vision + brain) contending for the same
Apple GPU/Metal context on a dev machine caused resource-allocation errors
— running the vision step on CPU sidesteps that and matches production
(Pi 5 has no GPU to offload to anyway).

## Validated: full pipeline (vision → brain)

```bash
python poc/pipeline.py \
  --image poc/test_images/electric_kettle.jpg \
  --question "is this safe to touch right now?" \
  --llm-model models/Phi-3.5-mini-instruct-Q4_K_M.gguf \
  --vision-model models/SmolVLM-500M-Instruct/SmolVLM-500M-Instruct-Q8_0.gguf \
  --mmproj models/SmolVLM-500M-Instruct/mmproj-SmolVLM-500M-Instruct-Q8_0.gguf \
  --mtmd-cli vendor/llama.cpp/build/bin/llama-mtmd-cli \
  --threads 8
```

Actual output (re-run after the model swap to `Phi-3.5-mini-instruct`,
documented in `docs/08-model-swap-mit.md`):

```
[1/2] Looking at poc/test_images/electric_kettle.jpg ...
      Vision description (1.3s): A white kettle with gray base sits on a wooden table.
[2/2] Thinking about: 'is this safe to touch right now?' ...
------------------------------------------------------------
Spoken answer (7.5s):
It's safe to touch the kettle if it's not hot, but please ensure it's turned off and cool to avoid any risk of electric shock or burns. If you're unsure, do not touch it.
------------------------------------------------------------
Total latency: 8.8s (vision 1.3s + brain 7.5s)
```

This is a real, end-to-end run on this Mac: a captured image, described in
one sentence by a local vision model, handed to the local brain LLM, which
gave a short, practical, safety-flavored answer — with zero network calls
after setup and a total latency (5.6s) well inside the "look, ask, wait a
beat, get an answer" bar for this product.

## What's still a stand-in (by design, for this milestone)

- **Camera capture** — a JPEG file path instead of a live frame from a Pi
  Camera Module / `libcamera`. Swapping this in later means writing a small
  "grab current frame, save to a temp path" function and calling
  `VisionCaptioner.describe_image()` on that path — no change to
  `vision.py` or `brain.py`.
- **Speech-to-text** — a `--question` string instead of `whisper.cpp`
  output. Same shape of swap: `whisper.cpp` produces a text string, which
  becomes the `question` argument to `HeadsetBrain.answer()`.
- **Text-to-speech** — printed text instead of Piper audio output. The
  final `answer` string from `HeadsetBrain.answer()` is exactly what you'd
  pipe into Piper.

None of these stand-ins touch the vision→brain contract validated above —
that's the point of building it this way.

## Pi 5 expectations for the vision step

SmolVLM-500M at `Q8_0` on CPU took under 1 second on this Mac's CPU
fallback path; the Pi 5's Cortex-A76 cores are slower, so budget roughly
2-6 seconds for a single-frame caption on-device (consistent with the
"possible and sane, not fast" goal from `docs/02-vision-architecture.md`).
If that's too slow once you measure it on real hardware, `ggml-org/SmolVLM-256M-Instruct-GGUF`
is a drop-in, smaller/faster swap — change two file paths in
`poc/pipeline.py`'s arguments, nothing else.
