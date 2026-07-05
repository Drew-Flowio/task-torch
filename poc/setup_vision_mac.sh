#!/usr/bin/env bash
# One-shot setup for the vision half of the PoC, on a Mac.
# Builds llama.cpp's multimodal CLI (llama-mtmd-cli) and downloads
# SmolVLM-500M-Instruct. Run poc/setup_mac.sh first (for the brain LLM +
# Python venv). Network is only needed for this script.
set -euo pipefail

cd "$(dirname "$0")/.."

VISION_REPO="ggml-org/SmolVLM-500M-Instruct-GGUF"
VISION_MODEL_FILE="SmolVLM-500M-Instruct-Q8_0.gguf"
MMPROJ_FILE="mmproj-SmolVLM-500M-Instruct-Q8_0.gguf"

echo "== Cloning llama.cpp (for llama-mtmd-cli) =="
mkdir -p vendor
if [ ! -d vendor/llama.cpp ]; then
  git clone --depth 1 https://github.com/ggml-org/llama.cpp vendor/llama.cpp
fi

echo "== Building llama-mtmd-cli (Metal build) =="
cd vendor/llama.cpp
cmake -B build -DGGML_METAL=on
cmake --build build --config Release -j"$(sysctl -n hw.ncpu)" \
  --target llama-mtmd-cli llama-cli
cd ../..

echo "== Installing PoC dependencies (if not already installed) =="
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -r poc/requirements.txt

echo "== Downloading ${VISION_MODEL_FILE} + ${MMPROJ_FILE} from ${VISION_REPO} =="
mkdir -p "models/SmolVLM-500M-Instruct"
hf download "${VISION_REPO}" \
  --include "${VISION_MODEL_FILE}" "${MMPROJ_FILE}" \
  --local-dir "./models/SmolVLM-500M-Instruct"

echo "== Done. Try it: =="
echo "  source .venv/bin/activate"
echo "  python poc/pipeline.py \\"
echo "    --image poc/test_images/electric_kettle.jpg \\"
echo "    --question \"is this safe to touch right now?\" \\"
echo "    --llm-model models/Phi-3.5-mini-instruct-Q4_K_M.gguf \\"
echo "    --vision-model models/SmolVLM-500M-Instruct/${VISION_MODEL_FILE} \\"
echo "    --mmproj models/SmolVLM-500M-Instruct/${MMPROJ_FILE} \\"
echo "    --mtmd-cli vendor/llama.cpp/build/bin/llama-mtmd-cli \\"
echo "    --threads 8"
