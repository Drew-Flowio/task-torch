# 3. Proof of concept on your Mac

Two equally valid paths — pick one:

- **Path A: `llama.cpp` CLI** — fastest way to sanity-check the model and
  quantization, no Python required.
- **Path B: `llama-cpp-python`** — what the actual `poc/brain.py` module in
  this repo uses, so you get the real prompt-template/system-prompt
  behavior you'll ship.

Both use the exact same GGUF file, so there's no wasted work.

## 0. One-time prerequisites

```bash
# Homebrew, if you don't already have it
xcode-select --install         # Apple command line tools (needed to build)
brew install cmake git
```

## Path A — `llama.cpp` CLI

```bash
# 1. Clone and build llama.cpp (Metal backend is enabled automatically on Apple Silicon)
git clone https://github.com/ggml-org/llama.cpp
cd llama.cpp
cmake -B build
cmake --build build --config Release -j"$(sysctl -n hw.ncpu)"

# 2. Download the recommended model in GGUF form directly from Hugging Face
#    (llama.cpp downloads + caches it for you — no separate hf CLI needed)
./build/bin/llama-cli -hf bartowski/Phi-3.5-mini-instruct-GGUF:Q4_K_M \
  -p "You are a concise, safety-aware assistant." -n 64

# Alternative: download the file explicitly, useful if you also want the
# .gguf file on disk to copy over to the Pi later
pip install -U "huggingface_hub[cli]"
hf download bartowski/Phi-3.5-mini-instruct-GGUF \
  --include "Phi-3.5-mini-instruct-Q4_K_M.gguf" \
  --local-dir ./models
```

## Path B — `llama-cpp-python` (used by `poc/brain.py`)

```bash
# 1. Create an isolated environment
cd "/Users/andrewcoghill/Desktop/Task Torch"
python3 -m venv .venv
source .venv/bin/activate

# 2. Install llama-cpp-python
#    (Metal acceleration on Apple Silicon; CPU-only build is what you'll
#    later use on the Pi — see docs/04-pi-deployment.md)
pip install -U pip
CMAKE_ARGS="-DGGML_METAL=on" pip install llama-cpp-python

# 3. Install the Hugging Face CLI and download the recommended GGUF
pip install -U "huggingface_hub[cli]"
mkdir -p models
hf download bartowski/Phi-3.5-mini-instruct-GGUF \
  --include "Phi-3.5-mini-instruct-Q4_K_M.gguf" \
  --local-dir ./models

# 4. Run the proof-of-concept script
pip install -r poc/requirements.txt
python poc/run_llm.py \
  --model models/Phi-3.5-mini-instruct-Q4_K_M.gguf \
  --vision-description "a stainless steel pot of water on a lit gas burner, the flame is large and blue" \
  --question "is it safe to touch the pot handle right now?"
```

Expected shape of the output: a couple of short, direct sentences — no
code, no essay, no bullet-point lecture. Actual output from a real run
with the current coworker-tone system prompt:

```
No, it's not safe. The pot is on a gas burner with a large flame, which
means it's very hot. Don't touch the handle.

Next action: Turn off the gas burner immediately to stop the flame and
let the pot cool down before attempting to touch it again.
```

Honest note: Phi-3.5-mini-instruct doesn't perfectly nail the casual
"coworker" voice from the system prompt alone every time — this run is
serviceable (short, direct, no code/markdown) but still reads a bit more
formal than the "Yeah, that's probably the fuse" tone examples in the
prompt. This is exactly the kind of thing to iterate on using the
desktop app's Personality tab (`insight_desktop/`) — tweak the wording,
save it as a new version, and compare replies side by side.

## The system prompt and message contract

This is the exact contract `poc/brain.py` builds and enforces (see the file
for the real implementation). It's deliberately strict about *not* letting
the model wander into code or long-form writing, since neither is useful
for a spoken, glanceable answer:

**System prompt:**

```text
You are Insight: a practical, friendly coworker. The user is looking at
something in the real world through a camera and asking a spoken question
about it.

Style:
- Talk like a coworker, not a manual - casual, direct, a little rough
  around the edges is fine. Mild swearing is okay if it fits naturally,
  but never edgy for its own sake.
- Not corporate, not formal, not preachy, not polished.
- Default to 2-4 short sentences. Say it like you're talking out loud,
  not writing an essay.

Response shape:
- Give the short answer first, then what to do next.
- Only use a numbered list if the user clearly asks for steps, or
  there's a real safety risk - never more than 4 items. No long
  tutorials unless asked.

How to help:
- Focus on the actual thing in front of them, based on what the camera
  sees - say what it likely is and what matters right now.
- Prefer one concrete next action over general advice. If you're not
  sure, say so plainly instead of guessing.

Safety:
- Be conservative around electricity, gas, fire, ladders, pressure,
  spinning tools, vehicles, or anything else that can hurt someone. Say
  the risk plainly and give the safest next move - don't over-explain
  the dangerous part.
- If they ask for something unsafe, stop and point them to a safer
  alternative instead.

Sound like this:
- "Yeah, that's probably the fuse. Check that first."
- "Okay, don't keep poking that. Kill the power and look for heat or
  smell."
- "I'm not sure from this alone, but the safest next step is to stop
  and take a closer photo."

Never mention the internet, cloud services, logging, or remote systems,
and never imply you're checking live data - you're only working from
what you can see and hear right now. Never write code, code blocks, or
long-form essays. Never use markdown formatting, bullet lists, or
headings outside of the rare numbered-list case above - this response
will be spoken, not read.
```

**User message template:**

```text
Here is a text description of what the camera sees: {vision_description}.
Here is the question: {question}.
Give me the short version.
```

Both are just Python string constants in `poc/prompts.py` — change them
freely as you tune behavior; nothing else in the pipeline needs to change
when you do.

## Minimal `llama-cpp-python` call (what `run_llm.py` does under the hood)

Note: `llama_cpp` / `Llama` here is the **`llama-cpp-python` library's**
package and class name — a general-purpose GGUF runtime that runs Phi,
Qwen, Mistral, Gemma, and dozens of other architectures, not a
Meta/Llama-specific tool. It's named after the `llama.cpp` project it
wraps, which itself outgrew its original LLaMA-only scope years ago. No
Meta model or code is involved in loading `Phi-3.5-mini-instruct` through
it.

```python
from llama_cpp import Llama

llm = Llama(
    model_path="models/Phi-3.5-mini-instruct-Q4_K_M.gguf",
    n_ctx=4096,
    n_threads=8,     # Mac: as many performance cores as you have; Pi 5: use 4
    verbose=False,
)

vision_description = "a stainless steel pot of water on a lit gas burner, the flame is large and blue"
question = "is it safe to touch the pot handle right now?"

response = llm.create_chat_completion(
    messages=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Here is a text description of what the camera sees: "
                f"{vision_description}. Here is the question: {question}. "
                f"Respond briefly and clearly."
            ),
        },
    ],
    max_tokens=120,
    temperature=0.3,
)

print(response["choices"][0]["message"]["content"])
```
