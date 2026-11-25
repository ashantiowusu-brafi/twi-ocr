"""Extract Akan transcriptions from UGSpeechData into a private text file.

UGSpeechData (University of Ghana) is licensed CC BY-NC-ND 4.0: non-commercial
use only, and modified versions may not be shared. So its transcriptions are
used only to enlarge the PRIVATE word list for post-correction. They are never
rendered into training images, never published, and never used by
``postcorrect.py --public``.

The download's file layout is not documented, so this script searches the
folder for spreadsheets and text files, finds the column (or lines) holding
Akan text, and cleans it with the same rules as download.py.

Input:
    private/ug_akan/    Unzipped transcription files from the "Transcribed
                        data" Akan.zip or the Metadata folder (.csv, .tsv,
                        .xlsx, .txt, .json). Audio files are ignored.

Output:
    private/twi_ug.txt  One cleaned transcription per line.

Usage:
    pip install pandas openpyxl
    python prepare_ug.py
    python prepare_ug.py --folder path/to/other/folder
"""

import argparse
import json
from pathlib import Path

import pandas as pd

from download import TWI_SPECIAL_CHARS, clean, deduplicate

DEFAULT_FOLDER = Path("private/ug_akan")
OUT_TXT = Path("private/twi_ug.txt")
TABLE_TYPES = {".csv", ".tsv", ".xlsx", ".xls"}
TEXT_TYPES = {".txt"}
JSON_TYPES = {".json", ".jsonl"}


def twi_score(values: pd.Series) -> int:
    """Count ɛ/ɔ characters in a column: the Akan column scores highest."""
    pattern = f"[{TWI_SPECIAL_CHARS}]"
    return int(values.astype(str).str.count(pattern).sum())


def from_table(path: Path) -> list[str]:
    """Return the Akan column of a spreadsheet, chosen by ɛ/ɔ count."""
    if path.suffix.lower() in {".xlsx", ".xls"}:
        df = pd.read_excel(path)
    else:
        df = pd.read_csv(path, sep="\t" if path.suffix.lower() == ".tsv" else None,
                         engine="python")
    text_columns = df.select_dtypes(include=["object", "string"]).columns
    if len(text_columns) == 0:
        return []
    best = max(text_columns, key=lambda c: twi_score(df[c]))
    if twi_score(df[best]) == 0:
        return []
    print(f"  {path.name}: column '{best}', {df[best].notna().sum():,} rows")
    return df[best].dropna().astype(str).tolist()


def from_text(path: Path) -> list[str]:
    """Return the lines of a plain-text transcript that contain Akan letters."""
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    akan = [line for line in lines if any(c in line for c in TWI_SPECIAL_CHARS)]
    if akan:
        print(f"  {path.name}: {len(akan):,} lines")
    return akan


def from_json(path: Path) -> list[str]:
    """Return string values containing Akan letters from a JSON or JSONL file."""
    text = path.read_text(encoding="utf-8", errors="replace")
    records = ([json.loads(line) for line in text.splitlines() if line.strip()]
               if path.suffix.lower() == ".jsonl" else json.loads(text))
    found: list[str] = []

    def walk(value: object) -> None:
        if isinstance(value, str):
            if any(c in value for c in TWI_SPECIAL_CHARS):
                found.append(value)
        elif isinstance(value, dict):
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(records)
    if found:
        print(f"  {path.name}: {len(found):,} strings")
    return found


def main() -> None:
    """Collect, clean and save every Akan transcription in the folder."""
    parser = argparse.ArgumentParser(description="Extract UGSpeechData Akan transcripts.")
    parser.add_argument("--folder", type=Path, default=DEFAULT_FOLDER)
    args = parser.parse_args()

    if not args.folder.exists():
        raise SystemExit(f"{args.folder} not found. Unzip the Akan transcriptions there first.")

    print(f"Searching {args.folder} ...")
    raw: list[str] = []
    for path in sorted(args.folder.rglob("*")):
        suffix = path.suffix.lower()
        try:
            if suffix in TABLE_TYPES:
                raw.extend(from_table(path))
            elif suffix in TEXT_TYPES:
                raw.extend(from_text(path))
            elif suffix in JSON_TYPES:
                raw.extend(from_json(path))
        except Exception as error:  # A malformed file should not stop the run.
            print(f"  Skipped {path.name}: {error}")

    lines = deduplicate([clean(t) for t in raw])
    if not lines:
        raise SystemExit("No Akan text found. Check which files hold the transcriptions.")

    OUT_TXT.write_text("\n".join(lines), encoding="utf-8")
    words = sum(len(line.split()) for line in lines)
    print(f"Saved {len(lines):,} transcriptions ({words:,} words) to {OUT_TXT}")
    print("Private only: never commit this file or use it for --public.")


if __name__ == "__main__":
    main()
