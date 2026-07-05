#!/usr/bin/env python3
"""Full end-to-end demo: camera frame + recorded spoken question -> vision
description -> transcribed question -> brain answer -> spoken WAV answer.

This is the complete software loop for the headset, with only the physical
I/O still stubbed:
  - "camera frame" is a JPEG file instead of a live CSI frame
  - "spoken question" is a WAV file instead of a live microphone recording
  - "spoken answer" is a WAV file written to disk instead of driving a
    speaker directly

Every model in the loop (vision, brain, STT, TTS) is the same local,
offline, CPU-compatible model validated in docs/01 through docs/05, run
through the same binaries that build and run on the Pi 5.

Example:
    python poc/pipeline_voice.py \\
        --image poc/test_images/electric_kettle.jpg \\
        --question-audio poc/test_audio/question_is_it_safe.wav \\
        --answer-audio /tmp/answer.wav
"""

import argparse
import time

from brain import BrainConfig, HeadsetBrain
from stt import SpeechToText, SttConfig
from tts import TextToSpeech, TtsConfig
from vision import VisionCaptioner, VisionConfig


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True, help="Path to a camera frame (jpg/png).")
    parser.add_argument("--question-audio", required=True, help="Path to a WAV recording of the spoken question.")
    parser.add_argument("--answer-audio", default="/tmp/headset_answer.wav", help="Where to write the spoken answer WAV.")

    parser.add_argument("--mtmd-cli", required=True, help="Path to the llama-mtmd-cli binary.")
    parser.add_argument("--vision-model", required=True, help="Path to the vision model GGUF.")
    parser.add_argument("--mmproj", required=True, help="Path to the matching mmproj GGUF.")

    parser.add_argument("--whisper-cli", required=True, help="Path to the whisper-cli binary.")
    parser.add_argument("--whisper-model", required=True, help="Path to the whisper.cpp ggml model.")

    parser.add_argument("--llm-model", required=True, help="Path to the brain LLM GGUF.")
    parser.add_argument("--threads", type=int, default=4, help="CPU threads for the brain LLM.")
    parser.add_argument("--ctx", type=int, default=4096)
    parser.add_argument("--max-tokens", type=int, default=120)
    parser.add_argument("--temperature", type=float, default=0.3)

    parser.add_argument("--voice-model", required=True, help="Path to the Piper .onnx voice model.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    timings = {}

    print(f"[1/4] Looking at {args.image} ...")
    t0 = time.time()
    vision = VisionCaptioner(
        VisionConfig(
            mtmd_cli_path=args.mtmd_cli,
            model_path=args.vision_model,
            mmproj_path=args.mmproj,
        )
    )
    description = vision.describe_image(args.image)
    timings["vision"] = time.time() - t0
    print(f"      Vision description ({timings['vision']:.1f}s): {description}")

    print(f"[2/4] Listening to {args.question_audio} ...")
    t0 = time.time()
    stt = SpeechToText(
        SttConfig(
            whisper_cli_path=args.whisper_cli,
            model_path=args.whisper_model,
            threads=args.threads,
        )
    )
    question = stt.transcribe(args.question_audio)
    timings["stt"] = time.time() - t0
    print(f"      Transcribed question ({timings['stt']:.1f}s): {question!r}")

    print("[3/4] Thinking ...")
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
    answer = brain.answer(description, question)
    timings["brain"] = time.time() - t0
    print(f"      Answer ({timings['brain']:.1f}s): {answer}")

    print("[4/4] Speaking ...")
    t0 = time.time()
    tts = TextToSpeech(TtsConfig(voice_model_path=args.voice_model))
    answer_path = tts.speak(answer, output_path=args.answer_audio)
    timings["tts"] = time.time() - t0
    print(f"      Wrote spoken answer ({timings['tts']:.1f}s): {answer_path}")

    total = sum(timings.values())
    print("-" * 60)
    print(f"Total end-to-end latency: {total:.1f}s "
          f"(vision {timings['vision']:.1f}s + stt {timings['stt']:.1f}s + "
          f"brain {timings['brain']:.1f}s + tts {timings['tts']:.1f}s)")


if __name__ == "__main__":
    main()
