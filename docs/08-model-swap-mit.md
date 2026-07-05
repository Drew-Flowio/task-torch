# 8. Model swap: off Llama/Meta, onto a fully permissive (MIT) brain model

This documents a deliberate swap of the "brain" LLM, made **after** the
vision and voice pipelines were already validated end-to-end (docs 05 and
07). The goal: stop depending on any Meta/Llama model, and use a model
under a genuinely permissive open-source license instead — without
touching the architecture, prompt contract, or any module's public
interface.

## Why the swap

The original recommendation in `docs/01-model-choice.md`,
**Llama-3.2-3B-Instruct**, is released under the **Llama 3.2 Community
License** — a license that is usable for the vast majority of projects,
but is **not** a plain MIT/Apache-2.0 permissive license: it includes
Meta-specific branding/attribution requirements and a clause requiring a
separate commercial license from Meta once a downstream product exceeds
700 million monthly active users. For a project that specifically wants
"fully open-source, permissive (MIT/Apache or similar), safe for
commercial use with no exceptions," that disqualifies it.

## What was checked before picking a replacement

Rather than assume a model's reputation implies its license, the actual
Hugging Face license field was checked for each candidate:

| Model | Checked license | Verdict |
|---|---|---|
| Llama-3.2-3B-Instruct | Llama 3.2 Community License | ❌ Not plain permissive (attribution + MAU clause) |
| Qwen2.5-3B-Instruct | **Qwen RESEARCH LICENSE** (`license_name: qwen-research` on the model card) — non-commercial use only, commercial use requires requesting a separate license from Alibaba Cloud | ❌ Disqualified — this is easy to miss, since most other Qwen2.5 sizes (0.5B/1.5B/7B/14B/32B) *are* Apache-2.0, but 3B and 72B specifically are not |
| **Phi-3.5-mini-instruct** | **MIT** (`license: mit` on the model card) | ✅ Fully permissive, no restrictions |
| Qwen2.5-1.5B-Instruct | Apache-2.0 | ✅ Fully permissive (kept as a documented faster alternative) |

## What changed

Only model identity and file paths changed — no architecture, module
interface, or prompt behavior:

| File | Change |
|---|---|
| `poc/brain.py` | Added a header comment block with the new model's name, link, license, and swap instructions (nothing else in this file changed — `HeadsetBrain`, `BrainConfig`, and `.answer()` are byte-for-byte the same) |
| `poc/setup_mac.sh`, `poc/setup_pi.sh` | `MODEL_REPO`/`MODEL_FILE` updated to `bartowski/Phi-3.5-mini-instruct-GGUF` / `Phi-3.5-mini-instruct-Q4_K_M.gguf` |
| `poc/setup_vision_mac.sh`, `poc/setup_vision_pi.sh`, `poc/setup_voice_mac.sh`, `poc/setup_voice_pi.sh` | Printed example commands now reference the new model filename |
| `poc/run_llm.py`, `poc/pipeline.py` | Docstring/help-text examples updated to the new model filename (both scripts already took `--model`/`--llm-model` as a required CLI argument with no hardcoded default, so no functional code changed) |
| `docs/01-model-choice.md` | Rewritten: Llama-3.2-3B-Instruct removed, Phi-3.5-mini-instruct is now the recommended model, Qwen2.5-1.5B-Instruct (Apache-2.0) and TinyLlama-1.1B-Chat (Apache-2.0) added as permissive alternatives, and the Qwen2.5-3B-Instruct licensing trap is called out explicitly |
| `docs/02-vision-architecture.md`, `docs/04-pi-deployment.md` | Model name, license, file size, and RAM figures updated throughout |
| `docs/05-vision-poc.md`, `docs/07-voice-poc.md` | Model name/path updated, and the pipelines were **re-run for real** with the new model — the "actual output" blocks in both docs now reflect genuine `Phi-3.5-mini-instruct` output, not the old model's output with a find-and-replaced name |
| `README.md` | "The one-line plan," quickstart commands, and doc index updated |
| `poc/test_audio/example_answer.wav` | Regenerated from the new model's actual answer |

**What did *not* change:** `poc/prompts.py` (the system prompt and user
message template are model-agnostic and untouched), `poc/vision.py`,
`poc/stt.py`, `poc/tts.py`, `poc/pipeline_voice.py`'s logic, and every
function name / input / output shape across the whole `poc/` package.

### A note on `llama_cpp` / `Llama` in the code

`poc/brain.py` still does `from llama_cpp import Llama` and constructs a
`Llama(...)` object. This is **not** a Meta model — it's the
**`llama-cpp-python`** library's package and class name. `llama.cpp` (the
C++ project it wraps) is a general-purpose GGUF inference runtime that
supports dozens of model architectures — Phi, Qwen, Mistral, Gemma, and
many more — not just Meta's LLaMA family it was originally named after.
Swapping the runtime itself was out of scope (and unnecessary): the
user-facing requirement was to stop using **Meta's model weights**, which
this swap does, while keeping the same battle-tested, Pi-5-proven,
CPU-only local inference engine.

## New model in use

> **Phi-3.5-mini-instruct**
> Creator: Microsoft
> License: **MIT** — https://huggingface.co/microsoft/Phi-3.5-mini-instruct/blob/main/LICENSE
> Model card: https://huggingface.co/microsoft/Phi-3.5-mini-instruct
> GGUF quants used: https://huggingface.co/bartowski/Phi-3.5-mini-instruct-GGUF
> Quantization: `Q4_K_M` (~2.2–2.4 GB file, ~3.0 GB resident RAM)
> Params: 3.8B

## Commands to download it

```bash
source .venv/bin/activate   # or run poc/setup_mac.sh / poc/setup_pi.sh, which do this automatically
hf download bartowski/Phi-3.5-mini-instruct-GGUF \
  --include "Phi-3.5-mini-instruct-Q4_K_M.gguf" \
  --local-dir ./models
```

No conversion step is needed — `bartowski` publishes ready-to-use GGUF
quants directly, the same pattern this project already used for the
previous model and for the vision/voice models.

## Re-validation after the swap

Both existing end-to-end pipelines were re-run against the new model
(not just have their file paths edited) to confirm real, current behavior
— see the updated "Actual output" sections in `docs/05-vision-poc.md` and
`docs/07-voice-poc.md`. Notably, the new model's answer in the voice
pipeline test is *more* safety-appropriate than the old one: it correctly
declines to assume the test kettle is hot ("without seeing the current
temperature or any visible signs of heat, it's not safe to assume it's
safe to touch") rather than guessing it's "hot and may be emitting
steam" the way the previous model did from the same one-sentence vision
description — a good sign, not just a neutral swap.

## How to swap to a different permissive model later

1. Confirm the model's actual license field on its Hugging Face model
   card (not just its reputation — see the Qwen2.5-3B trap above).
2. Download its GGUF quant, e.g.:
   ```bash
   hf download <hf-repo>-GGUF --include "*Q4_K_M.gguf" --local-dir ./models
   ```
3. Point `--model` / `--llm-model` (or `BrainConfig.model_path` if calling
   `poc/brain.py` directly) at the new `.gguf` file. That's the entire
   change — `poc/brain.py`'s chat-template handling comes from the GGUF's
   own embedded metadata via `llama-cpp-python`, so no code changes are
   needed for a different model family.
