#!/bin/bash
# Build "Twi OCR.app" and a disk image (Twi-OCR.dmg) people can download.
#
# Run from anywhere, with the project's .venv active:
#     bash app/build_mac.sh
# The results go in app/dist/. app/build/ holds temporary files and can be
# deleted afterwards; both folders are kept out of git.
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$PWD"

for model in twi twi_1879; do
  if [ ! -f "models/$model.traineddata" ]; then
    echo "Missing models/$model.traineddata (download it from the GitHub release)." >&2
    exit 1
  fi
done

# The word list for the l -> i fix is bundled if it has been built.
EXTRA=()
if [ -f data/twi_ghananlp.txt ]; then
  EXTRA+=(--add-data "$ROOT/data/twi_ghananlp.txt:data")
else
  echo "Note: data/twi_ghananlp.txt not found, so the app's l -> i fix will be off." >&2
fi

pyinstaller --noconfirm --windowed --name "Twi OCR" \
  --distpath app/dist --workpath app/build --specpath app/build \
  --paths "$ROOT" --hidden-import postcorrect --hidden-import orthography \
  --add-data "$ROOT/app/ui:ui" \
  --add-data "$ROOT/models/twi.traineddata:models" \
  --add-data "$ROOT/models/twi_1879.traineddata:models" \
  --add-data "$ROOT/orthography/christaller_1879.tsv:orthography" \
  ${EXTRA[@]+"${EXTRA[@]}"} \
  app/twi_ocr_app.py

rm -f app/dist/Twi-OCR.dmg
hdiutil create -volname "Twi OCR" -srcfolder "app/dist/Twi OCR.app" -ov -format UDZO app/dist/Twi-OCR.dmg
echo
echo "Built: app/dist/Twi OCR.app and app/dist/Twi-OCR.dmg"
