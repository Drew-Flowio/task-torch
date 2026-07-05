#!/usr/bin/env bash
# One-shot setup for the headset brain PoC, on Raspberry Pi OS (64-bit).
# CPU-only build - no GPU/Metal/CUDA flags. Run this once with network
# access; poc/run_llm.py runs fully offline afterward.
set -euo pipefail

cd "$(dirname "$0")/.."

MODEL_REPO="bartowski/Phi-3.5-mini-instruct-GGUF"
MODEL_FILE="Phi-3.5-mini-instruct-Q4_K_M.gguf"

echo "== Installing system build dependencies =="
sudo apt update
sudo apt install -y build-essential cmake git python3-venv python3-dev

echo "== Creating virtual environment =="
python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate

echo "== Installing llama-cpp-python (CPU build) =="
pip install -U pip
pip install llama-cpp-python

echo "== Installing PoC + download dependencies =="
pip install -r poc/requirements.txt

echo "== Downloading ${MODEL_FILE} from ${MODEL_REPO} =="
mkdir -p models
hf download "${MODEL_REPO}" \
  --include "${MODEL_FILE}" \
  --local-dir ./models

echo "== Done. Try it (4 threads = Pi 5's 4 physical cores): =="
echo "  source .venv/bin/activate"
echo "  python poc/run_llm.py --model models/${MODEL_FILE} --threads 4"
