#!/usr/bin/env bash
# One-shot setup for the vision half of the PoC, on Raspberry Pi OS (64-bit).
# CPU-only build - no GPU flags. Run poc/setup_pi.sh first (for the brain
# LLM + Python venv). Network is only needed for this script.
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

echo "== Building llama-mtmd-cli (CPU build, ARM-tuned) =="
cd vendor/llama.cpp
cmake -B build -DGGML_NATIVE=OFF -DGGML_CPU_ARM_ARCH=armv8.2-a+dotprod
cmake --build build --config Release -j4 \
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

echo "== Done. Try it (copy a test image onto the Pi first): =="
echo "  source .venv/bin/activate"
echo "  python poc/pipeline.py \\"
echo "    --image poc/test_images/electric_kettle.jpg \\"
echo "    --question \"is this safe to touch right now?\" \\"
echo "    --llm-model models/Phi-3.5-mini-instruct-Q4_K_M.gguf \\"
echo "    --vision-model models/SmolVLM-500M-Instruct/${VISION_MODEL_FILE} \\"
echo "    --mmproj models/SmolVLM-500M-Instruct/${MMPROJ_FILE} \\"
echo "    --mtmd-cli vendor/llama.cpp/build/bin/llama-mtmd-cli \\"
echo "    --threads 4"
