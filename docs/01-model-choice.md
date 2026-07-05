# 1. Model choice — the "brain" LLM

Goal: a small, fully open-source, **permissively licensed** (MIT/Apache-2.0
or equivalent), instruction-tuned LLM that gives short, grounded,
safety-aware, step-by-step answers about real-world objects and
situations. It does **not** need to write code or long-form prose — that
lets us pick a much smaller model than a general-purpose "coding assistant"
model, which is exactly what makes CPU-only Pi 5 inference realistic.

> **Update:** this project no longer uses any Meta/Llama model. The
> original recommendation (Llama-3.2-3B-Instruct) is licensed under the
> Llama 3.2 Community License, which — despite being usable for most
> projects — is **not** a plain MIT/Apache license: it carries Meta
> branding/attribution requirements and a clause that requires a separate
> license from Meta once a product exceeds 700 million monthly active
> users. That's not a real constraint for a hobby headset, but it fails
> the "fully open-source, permissive" bar this project now requires, so
> it's been dropped entirely — see `docs/08-model-swap-mit.md` for the
> swap record.

All candidates below are evaluated against three requirements:

- **Genuinely permissive license** (MIT, Apache-2.0, or equivalent) with
  no non-commercial or research-only clauses — checked against each
  model's actual Hugging Face license field, not just its reputation.
  This disqualifies a couple of models that look open at a glance (see
  the Qwen note below).
- Already published as GGUF (or trivially convertible with
  `llama.cpp`'s `convert_hf_to_gguf.py`)
- In the 1.5B–4B parameter range, which is the realistic ceiling for
  *interactive* (not batch) CPU-only inference on a Pi 5 — public
  Pi 5 `llama.cpp` benchmarks consistently show 7B-class models dropping
  to ~1–2 tok/s, which is too slow for a "look and ask" interaction loop.

## Candidates

### 1. Phi-3.5-mini-instruct (Microsoft) — recommended starting model

- **Link (base model):** https://huggingface.co/microsoft/Phi-3.5-mini-instruct
- **Link (GGUF quants):** https://huggingface.co/bartowski/Phi-3.5-mini-instruct-GGUF
- **License:** **MIT** — no usage, attribution, or commercial restrictions of any kind
- **Params:** 3.8B
- **Quant options:** Q4_K_M (~2.2–2.4 GB, recommended) → Q5_K_M (~2.6 GB) → Q6_K → Q8_0 (~4.1 GB)
- **Tradeoffs:** Trained on "reasoning-dense" synthetic data, so it's
  noticeably good at multi-step logical/practical reasoning (e.g. "the
  stove is on and the pan is smoking — what's the safest next step?").
  Being ~25% bigger than a 3B model, it runs at the lower end of
  interactive speed on Pi 5 (**~4–7.5 tok/s** at Q4_K_M), but that's still
  well inside the "short spoken answer in single-digit seconds" budget
  this product needs.

### 2. Qwen2.5-1.5B-Instruct (Alibaba/Qwen team)

- **Link (base model):** https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct
- **Link (GGUF quants):** https://huggingface.co/bartowski/Qwen2.5-1.5B-Instruct-GGUF
- **License:** **Apache-2.0** — fully permissive
- **Params:** 1.5B
- **Quant options:** Q4_K_M (~1.0 GB) → Q5_K_M (~1.2 GB) → Q6_K (~1.4 GB) → Q8_0 (~1.6 GB)
- **Tradeoffs:** Noticeably faster (~10–14 tok/s at Q4_K_M on Pi 5) and
  smaller than the 3–4B tier, at the cost of shallower reasoning — good
  enough for simple, direct safety calls ("is this hot", "is this
  edible-looking") but more likely to need hand-holding via the system
  prompt for anything requiring multi-step judgment.
- **Good pick if:** you want the snappiest possible turn-taking and are
  willing to trade some reasoning depth for it.

⚠️ **A licensing trap worth knowing about, since it's easy to get wrong:**
Qwen2.5 ships across many sizes (0.5B/1.5B/3B/7B/14B/32B/72B), and
**licensing differs by size within the same model family.** The 0.5B,
1.5B, 7B, 14B, and 32B sizes are Apache-2.0. The **3B and 72B sizes**,
including **Qwen2.5-3B-Instruct** — the model this project's earlier
docs floated as a secondary candidate — are released under the **"Qwen
RESEARCH LICENSE"**, which restricts use to **non-commercial purposes
only** unless you separately request a commercial license from Alibaba
Cloud. That disqualifies Qwen2.5-3B-Instruct outright for a "safe for
commercial use" requirement, even though the Qwen name and most of the
family are Apache-2.0. Always check the specific model card's license
field, not just the family's general reputation.

### 3. TinyLlama-1.1B-Chat (TinyLlama project) — smallest/fastest fallback

- **Link (base model):** https://huggingface.co/TinyLlama/TinyLlama-1.1B-Chat-v1.0
- **Link (GGUF quants):** https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF
- **License:** **Apache-2.0** — fully permissive. (Note: despite the
  name, this is an independent community project, not a Meta/Llama-family
  model or license — the name refers only to its Llama-style
  architecture.)
- **Params:** 1.1B
- **Quant options:** Q4_K_M (~700 MB) → Q5_K_M (~800 MB) → Q8_0 (~1.2 GB)
- **Tradeoffs:** The fastest and smallest option here (~14–18 tok/s at
  Q4_K_M on Pi 5), but meaningfully weaker instruction-following and
  safety-hedging than either model above — best treated as an emergency
  "needs to run on very constrained hardware" fallback, not a first
  choice for a safety-aware product.

## Head-to-head summary

| Model | Params | Recommended quant | File size | RAM (resident) | Pi 5 decode speed | License | Strength |
|---|---|---|---|---|---|---|---|
| **Phi-3.5-mini-instruct** ✅ recommended | 3.8B | Q4_K_M | ~2.2–2.4 GB | ~3.0 GB | ~4–7.5 tok/s | **MIT** | Best step-by-step reasoning of the permissive options |
| Qwen2.5-1.5B-Instruct | 1.5B | Q4_K_M | ~1.0 GB | ~1.6 GB | ~10–14 tok/s | **Apache-2.0** | Fastest fully-permissive option |
| TinyLlama-1.1B-Chat | 1.1B | Q4_K_M | ~0.7 GB | ~1.1 GB | ~14–18 tok/s | **Apache-2.0** | Smallest, for very constrained hardware |
| ~~Llama-3.2-3B-Instruct~~ (removed) | 3.21B | — | — | — | — | Llama 3.2 Community (not plain permissive) | — |
| ~~Qwen2.5-3B-Instruct~~ (never adopted) | 3.09B | — | — | — | — | Qwen Research License (non-commercial only) | — |

Because everything in this repo talks to the model only through a GGUF
file path and a chat template baked into that file's own metadata,
swapping between any of these is a one-line config change (see
`poc/brain.py`'s header comment), not a rewrite.

## Recommendation: starting model + quantization

> **Phi-3.5-mini-instruct, `Q4_K_M` GGUF, run through `llama.cpp` /
> `llama-cpp-python`.**

Why this one:

1. **Fully permissive, no exceptions.** MIT license — no attribution
   clause, no monthly-active-user threshold, no non-commercial
   restriction. Safe to ship in a commercial product without legal review.
2. **Fits comfortably in 8 GB.** ~2.2–2.4 GB on disk, ~3.0 GB resident with
   a modest context window (2–4K tokens) — still leaves ~4+ GB of headroom
   for Raspberry Pi OS, `whisper.cpp` (STT), Piper (TTS), and a vision
   model running in the same session.
3. **Fast enough for short interactive Q&A.** At ~4–7.5 tok/s, a 40–60
   token spoken-length answer completes in roughly 6–15 seconds on a Pi 5
   — usable for "look, ask, wait a beat, get an answer."
4. **Trained for reasoning, not essays or code.** The system prompt (see
   `docs/03-mac-poc.md`) explicitly forbids code and long-form writing
   regardless of model choice, and Phi-3.5-mini's reasoning-dense training
   data plays directly to the "grounded, step-by-step, practical" answer
   style this product needs.

Treat **Qwen2.5-1.5B-Instruct** as the "swap in for snappier turn-taking"
alternative if Phi-3.5-mini's ~4–7.5 tok/s proves too slow once measured
on the real Pi 5, and **TinyLlama-1.1B-Chat** as the last-resort fallback
if you ever need to run this on hardware smaller than a Pi 5. All three
use the identical runtime, prompt contract, and file layout in `poc/` —
see `poc/brain.py`'s header comment for the exact swap steps.
