#!/usr/bin/env python3
"""CLI demo of the headset brain.

Simulates the eventual pipeline: a text description standing in for "what
the vision model saw," plus a text question standing in for "what
whisper.cpp transcribed," fed into the same brain module the real headset
will use.

Example:
    python poc/run_llm.py \\
        --model models/Phi-3.5-mini-instruct-Q4_K_M.gguf \\
        --vision-description "a stainless steel pot of water on a lit gas burner, the flame is large and blue" \\
        --question "is it safe to touch the pot handle right now?"
"""

import argparse

from brain import BrainConfig, HeadsetBrain


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--model",
        required=True,
        help="Path to a GGUF model file, e.g. models/Phi-3.5-mini-instruct-Q4_K_M.gguf",
    )
    parser.add_argument(
        "--vision-description",
        default=(
            "a stainless steel pot of water on a lit gas burner, "
            "the flame is large and blue"
        ),
        help="Stand-in for the text description a vision model would produce from a camera frame.",
    )
    parser.add_argument(
        "--question",
        default="is it safe to touch the pot handle right now?",
        help="Stand-in for a speech-to-text transcription of the user's spoken question.",
    )
    parser.add_argument(
        "--threads",
        type=int,
        default=4,
        help="CPU threads for inference. Use ~8 on Apple Silicon, 4 on a Raspberry Pi 5.",
    )
    parser.add_argument("--ctx", type=int, default=4096, help="Context window size.")
    parser.add_argument("--max-tokens", type=int, default=120)
    parser.add_argument("--temperature", type=float, default=0.3)
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    brain = HeadsetBrain(
        BrainConfig(
            model_path=args.model,
            n_ctx=args.ctx,
            n_threads=args.threads,
            max_tokens=args.max_tokens,
            temperature=args.temperature,
        )
    )

    print(f"Vision description: {args.vision_description}")
    print(f"Question:           {args.question}")
    print("-" * 60)

    answer = brain.answer(args.vision_description, args.question)
    print(answer)


if __name__ == "__main__":
    main()
