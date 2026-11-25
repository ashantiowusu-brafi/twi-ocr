"""Score every OCR model on the same proverbs and write one results table.

Every model, from stock Tesseract to the newest Twi model, is scored against
the current answer key on the same proverbs, so the numbers can be compared
fairly and reproduced.

How it works:
    1. Runs each model on every scan (cached, so re-runs are fast).
    2. Decides once which proverbs are on which page, using the reference
       model's reading of the proverb numbers (or private/scan_index.csv).
       A proverb that appears on two pages is assigned to the page where the
       reference model matched it best. Every model is then scored on this
       same set.
    3. Adds post-correction rows for the reference model (public word list
       and, if available, the private one).
    4. Writes the table to eval/bu_me_be_results.md, and per-proverb details
       (which contain book text, and say which scan each proverb is on) to
       private/eval_details/.

Inputs:
    private/Akan_Proverbs.xlsx      Answer key (number, Twi, ...).
    private/scans/                  Page images.
    models/*.traineddata            Twi models, e.g. twi_v1 … twi_v4, twi_1879.
    private/scan_index.csv          Optional manual page ranges (file,first,last).

Outputs:
    eval/bu_me_be_results.md                 Combined results (no book text; publishable).
    private/eval_details/<model>.csv
    private/eval_details/ocr/<model>/<scan>.txt   Cached OCR output.

Usage:
    pip install pandas openpyxl rapidfuzz
    python compare_models.py                    # reference = highest twi_v* model
    python compare_models.py --reference twi_v3
    python compare_models.py --refresh          # re-run OCR, ignore the cache
"""

import argparse
import datetime
import hashlib
import re
import statistics
import subprocess
import unicodedata
from pathlib import Path

import pandas as pd
from rapidfuzz.distance import Levenshtein

import postcorrect as pc

# --- Configuration -----------------------------------------------------------

ANSWER_KEY = Path("private/Akan_Proverbs.xlsx")
SCAN_DIR = Path("private/scans")
SCAN_INDEX = Path("private/scan_index.csv")
MODELS_DIR = Path("models")
DETAILS_DIR = Path("private/eval_details")
RESULTS_MD = Path("eval/bu_me_be_results.md")

IMAGE_TYPES = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}
TWI_SPECIAL_CHARS = set("ɛɔƐƆ")
NUMBER_AT_LINE_START = re.compile(r"^\s*(\d{1,4})[.)]?\s")
MAX_SPREAD = 60            # Proverb numbers this far from a page's median are noise.
MAX_LINES_PER_PROVERB = 4  # A proverb may wrap over this many printed lines.
STOCK_MODEL = "eng"

# What changed in each model, shown in the results table. Add a line for
# each new version you train.
MODEL_NOTES = {
    "eng": "Stock Tesseract English model (baseline)",
    "twi_v1": "6,000 rendered lines, 3,000 iterations",
    "twi_v2": "20,000 lines, 10,000 iterations, more line-initial capitals",
    "twi_v3": "Lookalike characters fixed; proverb numbers before Ɔ/Ɛ-initial lines",
    "twi_v4": "Training text in the book's quote style (“ ” and ’)",
    "twi_1879": "1879-spelling model (writes ɛ ɔ as e̲ o̲); not meant for modern text",
}


# --- Text and scoring helpers -----------------------------------------------

def normalize(text: object) -> str:
    """Apply NFC normalization and collapse whitespace."""
    return " ".join(unicodedata.normalize("NFC", str(text)).split())


def load_answer_key() -> dict[int, str]:
    """Return proverb number -> normalized Twi text from the answer key."""
    df = pd.read_excel(ANSWER_KEY)
    number_col, twi_col = df.columns[0], df.columns[1]
    df = df[pd.to_numeric(df[number_col], errors="coerce").notna()]
    return {int(n): normalize(t) for n, t in zip(df[number_col], df[twi_col])}


def best_match(reference: str, lines: list[str]) -> tuple[str, int]:
    """Return the run of consecutive OCR lines closest to the reference."""
    best_text, best_distance = "", len(reference)
    for start in range(len(lines)):
        for size in range(1, MAX_LINES_PER_PROVERB + 1):
            window = lines[start:start + size]
            if len(window) < size:
                break
            candidate = normalize(NUMBER_AT_LINE_START.sub("", " ".join(window), count=1))
            distance = Levenshtein.distance(reference, candidate)
            if distance < best_distance:
                best_text, best_distance = candidate, distance
    return best_text, best_distance


def special_counts(reference: str, hypothesis: str) -> tuple[int, int]:
    """Return (correct, total) ɛ/ɔ/Ɛ/Ɔ characters in the reference."""
    total = sum(c in TWI_SPECIAL_CHARS for c in reference)
    correct = sum(
        sum(c in TWI_SPECIAL_CHARS for c in reference[a:b])
        for tag, a, b, _, _ in Levenshtein.opcodes(reference, hypothesis)
        if tag == "equal"
    )
    return correct, total


# --- Models and OCR ----------------------------------------------------------

def find_models() -> list[str]:
    """Return stock English plus each distinct Twi model file, in name order.

    Versioned files come first, so a working copy identical to one of them
    (for example models/twi.traineddata being a copy of twi_v4) is skipped
    and the versioned name is the one shown.
    """
    def order(path: Path) -> tuple[int, int, str]:
        """Versioned files (twi_v1, twi_v2, ...) first, by number; others after."""
        match = re.search(r"_v(\d+)$", path.stem)
        return (0, int(match.group(1)), path.stem) if match else (1, 0, path.stem)

    models, seen = [STOCK_MODEL], set()
    for path in sorted(MODELS_DIR.glob("*.traineddata"), key=order):
        if re.fullmatch(r"twi_1879_v\d+", path.stem):
            continue  # unreleased 1879 training runs; twi_1879 is the released one
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest in seen:
            print(f"Skipping {path.name}: identical to another model file")
            continue
        seen.add(digest)
        models.append(path.stem)
    return models


def ocr(scan: Path, model: str, refresh: bool) -> str:
    """Run one model on one scan, using the cached result when available."""
    cache = DETAILS_DIR / "ocr" / model / f"{scan.stem}.txt"
    if cache.exists() and not refresh:
        return cache.read_text(encoding="utf-8")
    command = ["tesseract", str(scan), "stdout", "-l", model]
    if model != STOCK_MODEL:
        command += ["--tessdata-dir", str(MODELS_DIR)]
    text = unicodedata.normalize("NFC", subprocess.run(
        command, capture_output=True, text=True, check=True).stdout)
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(text, encoding="utf-8")
    return text


def page_range(text: str, highest: int) -> tuple[int, int] | None:
    """Guess the first and last proverb numbers printed on a page."""
    numbers = [int(m.group(1)) for line in text.splitlines()
               if (m := NUMBER_AT_LINE_START.match(line)) and 1 <= int(m.group(1)) <= highest]
    if not numbers:
        return None
    middle = statistics.median(numbers)
    kept = [n for n in numbers if abs(n - middle) <= MAX_SPREAD]
    return min(kept), max(kept)


def assign_pages(reference_ocr: dict[str, str], answers: dict[int, str]) -> dict[int, str]:
    """Decide, once, which scan each proverb is scored on."""
    manual = {}
    if SCAN_INDEX.exists():
        df = pd.read_csv(SCAN_INDEX)
        manual = {str(f): (int(a), int(b)) for f, a, b in zip(df["file"], df["first"], df["last"])}

    best: dict[int, tuple[int, str]] = {}   # number -> (distance, scan)
    for scan, text in reference_ocr.items():
        span = manual.get(scan) or page_range(text, max(answers))
        if span is None:
            print(f"  {scan}: no proverb numbers found; add it to {SCAN_INDEX}")
            continue
        lines = [line for line in text.splitlines() if line.strip()]
        for number in range(span[0], span[1] + 1):
            if number in answers:
                _, distance = best_match(answers[number], lines)
                if number not in best or distance < best[number][0]:
                    best[number] = (distance, scan)
    return {number: scan for number, (_, scan) in sorted(best.items())}


# --- Scoring -----------------------------------------------------------------

def score(name: str, readings: dict[int, str], answers: dict[int, str],
          pages: dict[int, str]) -> dict:
    """Score one set of readings (proverb -> OCR text) and save its details.

    ``pages`` maps each proverb number to its scan, so the details say where
    to look (the answer-key review tools need this).
    """
    rows = []
    for number, hypothesis in readings.items():
        reference = answers[number]
        correct, total = special_counts(reference, hypothesis)
        rows.append({"number": number, "scan": pages[number],
                     "reference": reference, "ocr": hypothesis,
                     "edits": Levenshtein.distance(reference, hypothesis),
                     "chars": len(reference), "special_correct": correct,
                     "special_total": total})
    details = pd.DataFrame(rows)
    details.to_csv(DETAILS_DIR / f"{name}.csv", index=False, encoding="utf-8")
    return {
        "cer": details["edits"].sum() / details["chars"].sum(),
        "special": details["special_correct"].sum() / max(details["special_total"].sum(), 1),
        "proverbs": len(details),
    }


def write_results(rows: list[dict], n_proverbs: int, n_scans: int, reference: str) -> None:
    """Write the combined, publishable results table."""
    stock_cer = rows[0]["cer"]
    lines = [
        "# OCR results: Bu Me Bɛ",
        "",
        f"Generated {datetime.date.today():%d %B %Y} by `compare_models.py`. "
        f"All rows are scored on the same {n_proverbs} proverbs from {n_scans} scanned pages, "
        "against the answer key: proverbs 1–320 of the book's 7,015, all proofread.",
        "",
        "| Model | What changed | CER | Change vs stock | ɛ/ɔ accuracy |",
        "| --- | --- | --- | --- | --- |",
    ]
    for r in rows:
        change = "—" if r is rows[0] else f"{(r['cer'] - stock_cer) / stock_cer:+.0%}"
        lines.append(f"| `{r['name']}` | {r['notes']} | {r['cer']:.1%} | {change} | {r['special']:.1%} |")
    lines += [
        "",
        "**CER** (character error rate): edits needed to turn the OCR output into the "
        "answer key, divided by the number of characters in the key. Lower is better.",
        "",
        "**ɛ/ɔ accuracy**: share of ɛ, ɔ, Ɛ and Ɔ in the answer key that the OCR read correctly.",
        "",
        f"Proverbs are assigned to pages using `{reference}`'s reading of the printed "
        "proverb numbers. Post-correction swaps only l → i, using a Twi word list "
        "(public: GhanaNLP text only; private: adds Bible and UGSpeechData text).",
    ]
    RESULTS_MD.parent.mkdir(exist_ok=True)
    RESULTS_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


# --- Main --------------------------------------------------------------------

def main() -> None:
    """Score all models on one shared proverb set and write the results."""
    parser = argparse.ArgumentParser(description="Compare every OCR model fairly.")
    parser.add_argument("--reference", help="Model used to assign proverbs to pages "
                                            "(default: the highest-numbered twi_v* model)")
    parser.add_argument("--refresh", action="store_true", help="Re-run OCR instead of using the cache")
    args = parser.parse_args()

    DETAILS_DIR.mkdir(parents=True, exist_ok=True)
    answers = load_answer_key()
    scans = sorted(p for p in SCAN_DIR.iterdir() if p.suffix.lower() in IMAGE_TYPES)
    models = find_models()
    versioned = [m for m in models if re.search(r"_v\d+$", m)]
    reference = args.reference or (versioned or models)[-1]
    if reference not in models:
        raise SystemExit(f"Reference model '{reference}' not found. Models: {', '.join(models)}")

    # 1. OCR every scan with every model.
    all_ocr: dict[str, dict[str, str]] = {}
    for model in models:
        print(f"OCR with {model} ...")
        all_ocr[model] = {scan.name: ocr(scan, model, args.refresh) for scan in scans}

    # 2. Fix the proverb set once.
    pages = assign_pages(all_ocr[reference], answers)
    print(f"Scoring {len(pages)} proverbs on {len(set(pages.values()))} pages "
          f"(page assignment from {reference})")

    # 3. Score every model on that set.
    results = []
    for model in models:
        lines_by_scan = {s: [l for l in t.splitlines() if l.strip()] for s, t in all_ocr[model].items()}
        readings = {n: best_match(answers[n], lines_by_scan[s])[0] for n, s in pages.items()}
        row = score(model, readings, answers, pages)
        row.update(name=model, notes=MODEL_NOTES.get(model, "(add a note in MODEL_NOTES)"))
        results.append(row)
        if model == reference:
            reference_readings = readings

    # 4. Post-correction rows for the reference model.
    pc.CONFUSIONS = pc.SWAP_SETS["i"]
    word_lists = {"public": [pc.GHANANLP_TXT],
                  "private": [pc.GHANANLP_TXT, pc.BIBLE_TXT, pc.UG_TXT]}
    for label, sources in word_lists.items():
        available = [s for s in sources if s.exists()]
        if label == "private" and len(available) <= 1:
            continue  # No private text: identical to the public row.
        vocab = pc.build_vocabulary(available)
        corrected = {n: pc.correct_text(t, vocab) for n, t in reference_readings.items()}
        row = score(f"{reference}_postcorrect_{label}", corrected, answers, pages)
        names = ", ".join(s.stem.replace("twi_", "") for s in available)
        row.update(name=f"{reference} + post-correction ({label})",
                   notes=f"l → i word-list fixes; word list: {names} ({len(vocab):,} words)")
        results.append(row)

    write_results(results, len(pages), len(set(pages.values())), reference)
    for r in results:
        print(f"  {r['name']:<40} CER {r['cer']:.1%}   ɛ/ɔ {r['special']:.1%}")
    print(f"\nResults table: {RESULTS_MD}")
    print(f"Per-proverb details: {DETAILS_DIR}/")


if __name__ == "__main__":
    main()
