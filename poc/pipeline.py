#!/usr/bin/env python3
"""End-to-end demo: camera frame (a file, for now) + spoken question (typed,
for now) -> vision description -> brain answer.

This is the first fully wired slice of the real headset pipeline. The only
stand-ins left are the camera capture step (a file path instead of a live
CSI frame) and the microphone/STT step (a CLI argument instead of
whisper.cpp output) - everything downstream of those two is the same code
the final device will run.

Example:
    python poc/pipeline.py \\
        --image poc/test_images/electric_kettle.jpg \\
        --question "is this safe to touch right now?" \\
        --llm-model models/Phi-3.5-mini-instruct-Q4_K_M.gguf \\
        --vision-model models/SmolVLM-500M-Instruct/SmolVLM-500M-Instruct-Q8_0.gguf \\
        --mmproj models/SmolVLM-500M-Instruct/mmproj-SmolVLM-500M-Instruct-Q8_0.gguf \\
        --mtmd-cli vendor/llama.cpp/build/bin/llama-mtmd-cli
"""

import argparse
import time

from brain import BrainConfig, HeadsetBrain
from vision import VisionCaptioner, VisionConfig


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True, help="Path to a camera frame (jpg/png).")
    parser.add_argument("--question", required=True, help="The spoken question, as text.")

    parser.add_argument("--mtmd-cli", required=True, help="Path to the llama-mtmd-cli binary.")
    parser.add_argument("--vision-model", required=True, help="Path to the vision model GGUF.")
    parser.add_argument("--mmproj", required=True, help="Path to the matching mmproj GGUF.")

    parser.add_argument("--llm-model", required=True, help="Path to the brain LLM GGUF.")
    parser.add_argument("--threads", type=int, default=4, help="CPU threads for the brain LLM.")
    parser.add_argument("--ctx", type=int, default=4096)
    parser.add_argument("--max-tokens", type=int, default=120)
    parser.add_argument("--temperature", type=float, default=0.3)
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    print(f"[1/2] Looking at {args.image} ...")
    t0 = time.time()
    vision = VisionCaptioner(
        VisionConfig(
            mtmd_cli_path=args.mtmd_cli,
            model_path=args.vision_model,
            mmproj_path=args.mmproj,
        )
    )
    description = vision.describe_image(args.image)
    vision_seconds = time.time() - t0
    print(f"      Vision description ({vision_seconds:.1f}s): {description}")

    print(f"[2/2] Thinking about: {args.question!r} ...")
    t0 = time.time()
    brain = HeadsetBrain(
        BrainConfig(
            model_path=args.llm_model,
            n_ctx=args.ctx,
            n_threads=args.threads,
            max_tokens=args.max_tokens,
            temperature=args.temperature,
        )
    )
    answer = brain.answer(description, args.question)
    brain_seconds = time.time() - t0

    print("-" * 60)
    print(f"Spoken answer ({brain_seconds:.1f}s):")
    print(answer)
    print("-" * 60)
    print(f"Total latency: {vision_seconds + brain_seconds:.1f}s "
          f"(vision {vision_seconds:.1f}s + brain {brain_seconds:.1f}s)")


if __name__ == "__main__":
    main()
