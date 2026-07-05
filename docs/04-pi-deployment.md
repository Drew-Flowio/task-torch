# 4. Pi-ready confirmation

This confirms the chosen model + quantization + runtime is not just a Mac
toy — it's the same thing you'll run on the Raspberry Pi 5.

## Memory footprint check (Raspberry Pi 5, 8 GB RAM)

| Item | Size |
|---|---|
| `Phi-3.5-mini-instruct-Q4_K_M.gguf` file on disk | ~2.2–2.4 GB |
| Resident RAM while running (model weights + KV cache at 2–4K context) | ~3.0 GB |
| Remaining RAM for Raspberry Pi OS + STT + TTS + vision model | ~4+ GB |

Multiple independent Pi 5 (8 GB) `llama.cpp` benchmarks report 3–4B-class
Q4_K_M models running at roughly **4–7.5 tokens/second** decode speed with
active cooling and 4 threads pinned to the Cortex-A76 cores — comfortably
inside the "short interactive Q&A" bar this product needs (a 40–60 token
spoken answer completes in single-digit seconds). This is well clear of the
point where Pi 5 `llama.cpp` performance falls off a cliff (7B+ models,
which consistently benchmark at 1–2 tok/s or worse and are not
interactive).

**Storage note:** the prototype targets microSD. A ~2.3 GB model file is fine
to *store* on microSD, but random-read latency on microSD can slow initial
model load (memory-mapping the GGUF file). If first-response latency after
boot matters, consider booting/storing models from a USB3 SSD or the Pi 5's
NVMe HAT instead of microSD for the production headset — this doesn't
change anything about the model or runtime, only where the `.gguf` file
physically lives.

## Runtime check: does it compile and run on Raspberry Pi OS?

Yes — `llama.cpp` (and therefore `llama-cpp-python`, which wraps it) is a
plain C/C++ project with ARM NEON optimizations and is one of the
best-supported ways to run LLMs on Raspberry Pi hardware specifically. It
has no CUDA/Metal dependency requirement — the Pi build simply compiles the
CPU backend.

```bash
# On Raspberry Pi OS (64-bit, Bookworm or newer)
sudo apt update
sudo apt install -y build-essential cmake git python3-venv python3-dev

git clone https://github.com/ggml-org/llama.cpp
cd llama.cpp

# Build with ARM-specific CPU flags for the Pi 5's Cortex-A76 cores
cmake -B build -DGGML_NATIVE=OFF -DGGML_CPU_ARM_ARCH=armv8.2-a+dotprod
cmake --build build --config Release -j4

# Copy the same GGUF file you validated on the Mac (no re-download needed
# if you sneakernet/scp it over; otherwise re-run the same `hf download`
# command from docs/03-mac-poc.md directly on the Pi)
./build/bin/llama-cli -m models/Phi-3.5-mini-instruct-Q4_K_M.gguf \
  -t 4 -c 2048 -p "You are a concise, safety-aware assistant."
```

For the Python path used by `poc/brain.py`:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
# CPU-only build on the Pi — no GGML_METAL/GGML_CUDA flags needed
pip install llama-cpp-python
pip install -r poc/requirements.txt

python poc/run_llm.py \
  --model models/Phi-3.5-mini-instruct-Q4_K_M.gguf \
  --threads 4 \
  --vision-description "a stainless steel pot of water on a lit gas burner, the flame is large and blue" \
  --question "is it safe to touch the pot handle right now?"
```

`poc/run_llm.py` and `poc/brain.py` take `--threads`/`n_threads` as a
parameter specifically so the only thing that changes between Mac and Pi is
that one number (8-ish performance threads on an Apple Silicon Mac vs. 4 on
the Pi 5's four Cortex-A76 cores) — everything else, including the system
prompt, the chat template, and the GGUF file itself, is identical.

## Practical Pi 5 tuning notes

- **Active cooling matters.** Sustained multi-token generation will
  thermal-throttle a passively-cooled Pi 5 within a couple of minutes;
  budget for the official active cooler (or equivalent) in the headset's
  base-station/compute-puck design.
- **Keep context modest.** 2–4K tokens of context is plenty for "vision
  description + question + short answer" and keeps KV-cache RAM small,
  leaving more headroom for the vision model and voice stack running
  alongside the brain LLM.
- **`n_threads=4`** uses all four physical cores; going higher doesn't
  help and can hurt on a 4-core part.
- **Same model file, same prompt contract** as the Mac PoC — nothing about
  moving from prototype to Pi requires re-validating model choice, only
  re-validating timing/thermals on the real board.

## Bottom line

`Phi-3.5-mini-instruct` (MIT license) at `Q4_K_M` is confirmed compatible
with the target 8 GB Raspberry Pi 5: it fits in RAM with room to spare for
the rest of the pipeline, its runtime (`llama.cpp` / `llama-cpp-python`) is natively
supported and commonly benchmarked on this exact board, and it hits a
tokens/second rate that supports a short, spoken interaction loop rather
than a multi-minute wait.
