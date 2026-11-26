#!/usr/bin/env bash
# Fine-tune the modern Twi model (twi_v5 by default) from the previous one.
#
# twi_v5 (issue T7 in ORTHOGRAPHY.md) continues from twi_v4 with more English
# lines, mostly in italics and in sans-serif as well as serif fonts, because
# Bu Me Bɛ prints each proverb's English in sans-serif italics. The Twi lines
# stay in the mix so the model keeps what it learned.
#
# Run from the project folder, inside the venv:
#   python render_lines.py --count 20000 --seed 5 --english-share 0.35 \
#       --bible-share 0.30 --italic-english 0.75 --italic-twi 0.05 \
#       --paren-english 0.35 --number-period 0.5 --no-english-numbers \
#       --fix-lookalikes --out private/ground-truth-v5
#   bash scripts/train_twi.sh
#
# Change the settings below if your folders differ. Same tools as the earlier
# models: GNU make 4.2+ (macOS: brew install make, run as gmake) and tesstrain.
set -euo pipefail

TESSTRAIN_DIR="${TESSTRAIN_DIR:-$PWD/tesstrain}"     # your tesstrain checkout
START_MODEL="${START_MODEL:-twi_v4}"                  # model to continue from
START_DIR="${START_DIR:-$PWD/models}"                 # folder holding $START_MODEL.traineddata
GT_DIR="${GT_DIR:-$PWD/private/ground-truth-v5}"      # from render_lines.py --out ...
MODEL_NAME="${MODEL_NAME:-twi_v5}"
MAX_ITERATIONS="${MAX_ITERATIONS:-10000}"
MAKE="${MAKE:-gmake}"
PY="${VIRTUAL_ENV:-}/bin/python"; [ -x "$PY" ] || PY="$(command -v python3)"

[ -f "$START_DIR/$START_MODEL.traineddata" ] || {
  echo "Start model not found: $START_DIR/$START_MODEL.traineddata"; exit 1; }
[ -d "$GT_DIR" ] || { echo "No training lines in $GT_DIR. Run render_lines.py first (see above)."; exit 1; }
[ -f "$TESSTRAIN_DIR/Makefile" ] || {
  echo "tesstrain not found in $TESSTRAIN_DIR."
  echo "Get it with: git clone https://github.com/tesseract-ocr/tesstrain"; exit 1; }
[ -f "models/$MODEL_NAME.traineddata" ] && {
  echo "models/$MODEL_NAME.traineddata already exists. Move it away or set MODEL_NAME."; exit 1; }

PROJECT_DIR="$PWD"
KEEP_AWAKE=""; command -v caffeinate >/dev/null && KEEP_AWAKE="caffeinate -i"   # macOS: stay awake

cd "$TESSTRAIN_DIR"
mkdir -p data   # tesstrain makes it too, but the log below is opened first
$KEEP_AWAKE "$MAKE" training \
  MODEL_NAME="$MODEL_NAME" \
  START_MODEL="$START_MODEL" \
  TESSDATA="$START_DIR" \
  GROUND_TRUTH_DIR="$GT_DIR" \
  MAX_ITERATIONS="$MAX_ITERATIONS" \
  PY_CMD="$PY" 2>&1 | tee "data/$MODEL_NAME-training.log"

# Check that the letters the model must write made it into its character list.
UNICHARSET="data/$MODEL_NAME/unicharset"
check() {  # name, pattern
  if grep -q -E "$2" "$UNICHARSET"; then echo "OK: $1"; else echo "WARNING: $1 missing from $UNICHARSET"; fi
}
check "ɛ and ɔ"          "ɛ|ɔ"
check "Ɛ and Ɔ"          "Ɛ|Ɔ"
check "curly quotes"     "“|”"
check "brackets ( )"     "\(|\)"
# Lookalike letters (ε ↄ ℇ ...) must not be in the training lines. The model's
# full list also holds the starting model's letters (twi_v4 has ℇ, Ↄ and ȼ
# from older text), so the check reads the list made from the training lines.
LOOKALIKE="ε|Ε|ↄ|Ↄ|ℇ|ᴐ|Ꜫ|ꓛ|ȼ"
if grep -q -E "$LOOKALIKE" "data/$MODEL_NAME/my.unicharset"; then
  echo "WARNING: lookalike letters are in the training lines; render with --fix-lookalikes"
else
  echo "OK: no lookalike letters in the training lines"
fi
INHERITED=$(grep -o -E "^($LOOKALIKE) " "$UNICHARSET" | tr -d ' ' | tr '\n' ' ')
[ -n "$INHERITED" ] && echo "Note: kept from $START_MODEL's character list: $INHERITED"

cp "data/$MODEL_NAME.traineddata" "$PROJECT_DIR/models/$MODEL_NAME.traineddata"
echo "Saved models/$MODEL_NAME.traineddata. Next: python compare_models.py"
