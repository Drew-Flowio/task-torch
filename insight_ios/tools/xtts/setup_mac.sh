#!/usr/bin/env bash
# Install Coqui XTTS on macOS and generate Insight's reference voice clip.
#
# Run from anywhere:
#   bash "/path/to/task-torch/insight_ios/tools/xtts/setup_mac.sh"
#
# Or from the repo root (note the leading ./ or bash):
#   bash insight_ios/tools/xtts/setup_mac.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
INSIGHT_IOS_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
VENV="$INSIGHT_IOS_ROOT/.venv-xtts"
MODELS_DIR="${INSIGHT_MODELS:-$HOME/Library/Application Support/Insight/models}"
REFERENCE="$MODELS_DIR/insight_reference_voice.wav"
SCRIPT_SRC="$INSIGHT_IOS_ROOT/Packages/InsightVoice/Sources/InsightVoice/Resources/insight_xtts_speak.py"
SCRIPT_DST="$MODELS_DIR/insight_xtts_speak.py"

if [[ ! -f "$SCRIPT_SRC" ]]; then
    echo "error: could not find bundled XTTS script at:" >&2
    echo "  $SCRIPT_SRC" >&2
    echo >&2
    echo "Make sure you are running the copy inside the task-torch repo:" >&2
    echo "  bash insight_ios/tools/xtts/setup_mac.sh" >&2
    exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
    echo "error: python3 not found. Install Xcode Command Line Tools or Python 3." >&2
    exit 1
fi

echo "Insight XTTS setup (macOS)"
echo "Voice profile: clear, natural American male, mid-30s, neutral accent,"
echo "medium speed, relaxed and conversational."
echo

python3 -m venv "$VENV"
# shellcheck disable=SC1091
source "$VENV/bin/activate"
python -m pip install --upgrade pip
python -m pip install torch coqui-tts

mkdir -p "$MODELS_DIR"
cp "$SCRIPT_SRC" "$SCRIPT_DST"

REFERENCE_SCRIPT="Hey — I'm Insight. I'll keep this clear and calm. Tell me what you're working on, and we'll figure out the next move together."
TMP_AIFF="$(mktemp /tmp/insight-ref.XXXXXX.aiff)"
say -v Alex -r 175 -o "$TMP_AIFF" "$REFERENCE_SCRIPT"
afconvert "$TMP_AIFF" "$REFERENCE" -d LEI16@16000 -f WAVE
rm -f "$TMP_AIFF"

cat <<EOF

Done.

Reference voice: $REFERENCE
XTTS script:     $SCRIPT_DST
Python venv:     $VENV/bin/python3

For Insight on macOS, set:
  export INSIGHT_XTTS_PYTHON="$VENV/bin/python3"

The first XTTS synthesis will download the xtts_v2 model (~1.8 GB).
EOF
