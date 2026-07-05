#!/usr/bin/env bash
# One-shot setup for the headset brain PoC, on a Mac.
# Downloads the recommended model and installs llama-cpp-python with Metal
# acceleration. Network is only needed for this script; poc/run_llm.py runs
# fully offline afterward.
set -euo pipefail

cd "$(dirname "$0")/.."

MODEL_REPO="bartowski/Phi-3.5-mini-instruct-GGUF"
MODEL_FILE="Phi-3.5-mini-instruct-Q4_K_M.gguf"

echo "== Creating virtual environment =="
python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate

echo "== Installing llama-cpp-python (Metal build) =="
pip install -U pip
CMAKE_ARGS="-DGGML_METAL=on" pip install llama-cpp-python

echo "== Installing PoC + download dependencies =="
pip install -r poc/requirements.txt

echo "== Downloading ${MODEL_FILE} from ${MODEL_REPO} =="
mkdir -p models
hf download "${MODEL_REPO}" \
  --include "${MODEL_FILE}" \
  --local-dir ./models

echo "== Done. Try it: =="
echo "  source .venv/bin/activate"
echo "  python poc/run_llm.py --model models/${MODEL_FILE} --threads 8"
