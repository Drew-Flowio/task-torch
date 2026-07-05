"""The headset "brain": a thin, swap-friendly wrapper around a local GGUF
instruction model, served through llama-cpp-python.

CURRENT MODEL
-------------
Name:    Phi-3.5-mini-instruct (3.8B params)
Creator: Microsoft
License: MIT - fully open-source, no usage/commercial restrictions
Link:    https://huggingface.co/microsoft/Phi-3.5-mini-instruct
GGUF:    https://huggingface.co/bartowski/Phi-3.5-mini-instruct-GGUF
         (this project uses the Q4_K_M quant: ~2.2 GB file, ~3.0 GB
         resident RAM, real-time-usable on a Raspberry Pi 5 CPU)

This module has zero model-specific code - it only ever sees a path to a
GGUF file and a chat message list. llama-cpp-python reads the chat
template baked into the GGUF's own metadata, so swapping models is purely
a matter of pointing `BrainConfig.model_path` at a different file. No code
in this file, prompts.py, or any of the pipeline scripts needs to change.

HOW TO SWAP TO A DIFFERENT PERMISSIVE MODEL LATER
--------------------------------------------------
1. Pick another MIT/Apache-2.0-licensed instruct model with a published
   GGUF (check the model's Hugging Face license field - many small models
   use custom "research-only" licenses that look open but restrict
   commercial use, e.g. Qwen2.5-3B-Instruct's "Qwen Research License").
2. Download its GGUF, e.g.:
     hf download <hf-repo>-GGUF --include "*Q4_K_M.gguf" --local-dir ./models
3. Point every `--llm-model` / `--model` CLI argument (or `BrainConfig.model_path`
   if calling this module directly) at the new .gguf file.
4. That's it - no changes to this file, prompts.py, brain.py's public
   interface, or any pipeline script are required.

This module is deliberately the *only* place that talks to the LLM. The
long-term headset will call `HeadsetBrain.answer(vision_description,
question)` from a loop driven by a camera + microphone instead of CLI
arguments - nothing else about this module needs to change when that
happens.
"""

from __future__ import annotations

from dataclasses import dataclass

from llama_cpp import Llama

from prompts import SYSTEM_PROMPT, build_user_message


@dataclass
class BrainConfig:
    model_path: str
    n_ctx: int = 4096
    n_threads: int = 4
    max_tokens: int = 120
    temperature: float = 0.3


class HeadsetBrain:
    """Loads a local GGUF instruct model once, then answers grounded,
    safety-aware questions about a text description of a camera frame."""

    def __init__(self, config: BrainConfig):
        self._config = config
        self._llm = Llama(
            model_path=config.model_path,
            n_ctx=config.n_ctx,
            n_threads=config.n_threads,
            verbose=False,
        )

    def answer(self, vision_description: str, question: str) -> str:
        user_message = build_user_message(vision_description, question)

        response = self._llm.create_chat_completion(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            max_tokens=self._config.max_tokens,
            temperature=self._config.temperature,
        )
        return response["choices"][0]["message"]["content"].strip()
