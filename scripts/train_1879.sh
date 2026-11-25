#!/usr/bin/env bash
# Fine-tune a Tesseract model for Christaller-era (1879) Twi spelling.
#
# Starts from the best modern Twi model (twi_v4 by default) and trains it on
# lines from `python render_lines.py --orthography 1879`, so it keeps what it
# learned about Twi letters and adds the 1879 marks (e/o with a line below,
# tildes, accents, dotted n, the mark over w).
#
# Run from the project folder, inside the venv:
#   python render_lines.py --orthography 1879 --count 20000
#   bash scripts/train_1879.sh
#
# Change the settings below if your folders differ. Same tools as the earlier
# models: GNU make 4.2+ (macOS: brew install make, run as gmake) and tesstrain.
set -euo pipefail

TESSTRAIN_DIR="${TESSTRAIN_DIR:-$PWD/tesstrain}"         # your tesstrain checkout
START_MODEL="${START_MODEL:-twi_v4}"                      # model to continue from
START_DIR="${START_DIR:-$PWD/models}"                     # folder holding $START_MODEL.traineddata
GT_DIR="${GT_DIR:-$PWD/private/ground-truth-1879}"        # from render_lines.py --orthography 1879
MODEL_NAME="${MODEL_NAME:-twi_1879}"
MAX_ITERATIONS="${MAX_ITERATIONS:-10000}"
MAKE="${MAKE:-gmake}"
PY="${VIRTUAL_ENV:-}/bin/python"; [ -x "$PY" ] || PY="$(command -v python3)"

[ -f "$START_DIR/$START_MODEL.traineddata" ] || {
  echo "Start model not found: $START_DIR/$START_MODEL.traineddata"
  echo "Copy twi_v4 there first, or run with START_MODEL=twi_v3 (or lat with START_DIR=<tessdata_best>)."
  exit 1; }
[ -d "$GT_DIR" ] || { echo "No training lines in $GT_DIR. Run: python render_lines.py --orthography 1879"; exit 1; }

PROJECT_DIR="$PWD"
KEEP_AWAKE=""; command -v caffeinate >/dev/null && KEEP_AWAKE="caffeinate -i"   # macOS: stay awake

cd "$TESSTRAIN_DIR"
$KEEP_AWAKE "$MAKE" training \
  MODEL_NAME="$MODEL_NAME" \
  START_MODEL="$START_MODEL" \
  TESSDATA="$START_DIR" \
  GROUND_TRUTH_DIR="$GT_DIR" \
  MAX_ITERATIONS="$MAX_ITERATIONS" \
  PY_CMD="$PY" 2>&1 | tee "data/$MODEL_NAME-training.log"

# Check that the 1879 marks made it into the model's character list. If the
# line below (U+0332) is missing, Tesseract dropped it while building the
# character set, and the model will read e̲ as plain e. (The released
# twi_1879 model keeps it; see docs/WRITEUP.md.)
UNICHARSET="data/$MODEL_NAME/unicharset"
# Each mark may be stored on its own (combining) or inside a ready-made letter
# (ã, á, ṅ ...), so both are checked. Marks are typed as real characters,
# not \u escapes, because macOS's built-in bash 3.2 doesn't understand those.
check() {  # name, pattern
  if grep -q -E "$2" "$UNICHARSET"; then echo "OK: $1"; else echo "WARNING: $1 missing from $UNICHARSET"; fi
}
check "line below (e̲ o̲)" "̲"
check "tilde (ã ũ ...)"   "̃|ã|ẽ|ĩ|õ|ũ"
check "acute (á é ...)"   "́|á|é|í|ó|ú"
check "dot above (ṅ)"     "̇|ṅ"

cp "data/$MODEL_NAME.traineddata" "$PROJECT_DIR/models/$MODEL_NAME.traineddata"
echo "Saved models/$MODEL_NAME.traineddata. Next: python score_1879.py --model $MODEL_NAME"
