"""Local vision captioning via llama-mtmd-cli (SmolVLM), same stack as poc/vision.py."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Protocol

CAPTION_PROMPT = (
    "Describe this image for someone who needs hands-on help. Include: what the object "
    "or scene likely is, any visible labels, model numbers, damage, wear, or safety "
    "concerns. Be specific and practical in 2-4 sentences."
)


@dataclass(frozen=True)
class VisionConfig:
    mtmd_cli_path: str
    model_path: str
    mmproj_path: str
    n_predict: int = 128
    temperature: float = 0.1
    gpu_layers: int = 0


class VisionAdapterProtocol(Protocol):
    def describe_image(self, image_path: str) -> str: ...


class VisionAdapter:
    def __init__(self, config: VisionConfig):
        self._config = config

    def describe_image(self, image_path: str, prompt: str = CAPTION_PROMPT) -> str:
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
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        caption = result.stdout.strip()
        if not caption:
            raise RuntimeError("Vision model returned an empty caption.")
        return caption
