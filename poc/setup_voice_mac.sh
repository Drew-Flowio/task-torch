#!/usr/bin/env bash
# One-shot setup for the voice half of the PoC (STT + TTS), on a Mac.
# Builds whisper.cpp and installs Piper + a default English voice.
# Run poc/setup_mac.sh first (for the brain LLM + Python venv). Network is
# only needed for this script.
set -euo pipefail

cd "$(dirname "$0")/.."

WHISPER_MODEL="base.en"
PIPER_VOICE_REPO="rhasspy/piper-voices"
PIPER_VOICE_PATH="en/en_US/ryan/medium/en_US-ryan-medium.onnx"
PIPER_VOICE_FALLBACK="en/en_US/lessac/medium/en_US-lessac-medium.onnx"

echo "== Cloning whisper.cpp (for offline speech-to-text) =="
mkdir -p vendor
if [ ! -d vendor/whisper.cpp ]; then
  git clone --depth 1 https://github.com/ggml-org/whisper.cpp vendor/whisper.cpp
fi

echo "== Building whisper-cli (Metal build) =="
cd vendor/whisper.cpp
cmake -B build -DGGML_METAL=on
cmake --build build --config Release -j"$(sysctl -n hw.ncpu)" --target whisper-cli
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

echo "== Downloading fallback Piper voice: ${PIPER_VOICE_FALLBACK} =="
hf download "${PIPER_VOICE_REPO}" "${PIPER_VOICE_FALLBACK}" --local-dir ./models/piper-voices
hf download "${PIPER_VOICE_REPO}" "${PIPER_VOICE_FALLBACK}.json" --local-dir ./models/piper-voices

echo "== Done. Try the full voice loop: =="
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
echo "    --threads 8"
echo "  afplay /tmp/headset_answer.wav   # hear the spoken answer"
