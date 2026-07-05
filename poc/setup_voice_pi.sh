#!/usr/bin/env bash
# One-shot setup for the voice half of the PoC (STT + TTS), on Raspberry Pi
# OS (64-bit). Builds whisper.cpp and installs Piper + a default English
# voice. Run poc/setup_pi.sh first (for the brain LLM + Python venv).
# Network is only needed for this script.
#
# IMPORTANT: this requires the 64-bit Raspberry Pi OS. On the 32-bit
# userland image, `uname -m` still reports aarch64 but pip will fail to
# find a compatible piper-tts wheel. Check with: file /bin/ls
# (should say "64-bit", not "32-bit").
set -euo pipefail

cd "$(dirname "$0")/.."

WHISPER_MODEL="base.en"
PIPER_VOICE_REPO="rhasspy/piper-voices"
PIPER_VOICE_PATH="en/en_US/lessac/medium/en_US-lessac-medium.onnx"

echo "== Installing system audio dependencies =="
sudo apt update
sudo apt install -y build-essential cmake git libsdl2-dev alsa-utils

echo "== Cloning whisper.cpp (for offline speech-to-text) =="
mkdir -p vendor
if [ ! -d vendor/whisper.cpp ]; then
  git clone --depth 1 https://github.com/ggml-org/whisper.cpp vendor/whisper.cpp
fi

echo "== Building whisper-cli (CPU build, ARM-tuned) =="
cd vendor/whisper.cpp
cmake -B build -DGGML_NATIVE=OFF -DGGML_CPU_ARM_ARCH=armv8.2-a+dotprod
cmake --build build --config Release -j4 --target whisper-cli
bash ./models/download-ggml-model.sh "${WHISPER_MODEL}"
cd ../..

echo "== Installing Piper (offline text-to-speech) =="
# shellcheck disable=SC1091
source .venv/bin/activate
pip install piper-tts
pip install -r poc/requirements.txt

echo "== Downloading Piper voice: ${PIPER_VOICE_PATH} =="
mkdir -p models/piper-voices
hf download "${PIPER_VOICE_REPO}" "${PIPER_VOICE_PATH}" --local-dir ./models/piper-voices
hf download "${PIPER_VOICE_REPO}" "${PIPER_VOICE_PATH}.json" --local-dir ./models/piper-voices

echo "== Done. Try the full voice loop (copy a test image + question WAV onto the Pi first): =="
echo "  source .venv/bin/activate"
echo "  python poc/pipeline_voice.py \\"
echo "    --image poc/test_images/electric_kettle.jpg \\"
echo "    --question-audio poc/test_audio/question_is_it_safe.wav \\"
echo "    --answer-audio /tmp/headset_answer.wav \\"
echo "    --mtmd-cli vendor/llama.cpp/build/bin/llama-mtmd-cli \\"
echo "    --vision-model models/SmolVLM-500M-Instruct/SmolVLM-500M-Instruct-Q8_0.gguf \\"
echo "    --mmproj models/SmolVLM-500M-Instruct/mmproj-SmolVLM-500M-Instruct-Q8_0.gguf \\"
echo "    --whisper-cli vendor/whisper.cpp/build/bin/whisper-cli \\"
echo "    --whisper-model vendor/whisper.cpp/models/ggml-${WHISPER_MODEL}.bin \\"
echo "    --llm-model models/Phi-3.5-mini-instruct-Q4_K_M.gguf \\"
echo "    --voice-model models/piper-voices/${PIPER_VOICE_PATH} \\"
echo "    --threads 4"
echo "  aplay /tmp/headset_answer.wav   # hear the spoken answer"
