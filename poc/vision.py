"""The headset "eyes": turns a camera frame into a short text description
using a small local vision-language model, via llama.cpp's `mtmd` tool.

Kept deliberately separate from brain.py: this module's only contract with
the rest of the system is `describe_image(path) -> str`. Swapping SmolVLM
for moondream2, a different SmolVLM size, or a completely different
captioning approach later only means changing this file.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass

DEFAULT_PROMPT = "Describe what is in this image in one short sentence."


@dataclass
class VisionConfig:
    mtmd_cli_path: str
    model_path: str
    mmproj_path: str
    n_predict: int = 64
    temperature: float = 0.1
    gpu_layers: int = 0  # 0 = CPU only, matches the Pi 5 target hardware


class VisionCaptioner:
    """Wraps the `llama-mtmd-cli` binary to produce a text description of
    an image. Shelling out (rather than binding via ctypes/pybind) keeps
    this identical to the exact command validated in
    docs/02-vision-architecture.md, so what you test here is exactly what
    runs on the Pi."""

    def __init__(self, config: VisionConfig):
        self._config = config

    def describe_image(self, image_path: str, prompt: str = DEFAULT_PROMPT) -> str:
        cfg = self._config
        cmd = [
            cfg.mtmd_cli_path,
            "-m", cfg.model_path,
            "--mmproj", cfg.mmproj_path,
            "--image", image_path,
            "-p", prompt,
            "-n", str(cfg.n_predict),
            "--temp", str(cfg.temperature),
            "-ngl", str(cfg.gpu_layers),
            "--no-mmproj-offload",
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
