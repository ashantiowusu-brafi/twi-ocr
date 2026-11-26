"""Fix common OCR letter mistakes using a Twi word list (post-correction).

The trained model still makes a few predictable swaps, above all reading i as
l ("firl" for "firi"). This script checks each OCR word against a word list
built from the Twi training text. If a word is not in the list, it tries
swapping only the letters the model is known to confuse; if exactly that swap
produces a known word, the word is replaced. Words already in the list, and
words with no known correction, are left alone.

Inputs:
    data/twi_ghananlp.txt          GhanaNLP sentences (always used).
    private/twi_bible.txt          Bible verses (used unless --public).
    private/twi_ug.txt             UGSpeechData transcripts, if prepared with
                                   prepare_ug.py (used unless --public).
    private/eval_details/<model>.csv   Per-proverb OCR results written by
                                   compare_models.py (default: the newest
                                   twi_vN model; choose with --model).

Outputs:
    private/postcorrect_details.csv   Per-proverb scores after correction.
    Printed before/after scores, so the effect is measured, not assumed.

Usage:
    python postcorrect.py                # i/l fixes only (default)
    python postcorrect.py --swaps all    # also e/ɛ and o/ɔ swaps
    python postcorrect.py --public       # word list from GhanaNLP only
    python postcorrect.py --model twi_v3 # results of another model
"""

from __future__ import annotations   # Type hints below name pandas without importing it.

import argparse
import collections
import itertools
import re
import unicodedata
from pathlib import Path

# pandas and rapidfuzz are imported inside the functions that score results,
# so ocr.py and the desktop app can use the correction alone without them.

# --- Configuration -----------------------------------------------------------

GHANANLP_TXT = Path("data/twi_ghananlp.txt")
BIBLE_TXT = Path("private/twi_bible.txt")
UG_TXT = Path("private/twi_ug.txt")   # From prepare_ug.py; private only.
DETAILS_DIR = Path("private/eval_details")   # Written by compare_models.py.
OUT_CSV = Path("private/postcorrect_details.csv")


def details_csv(model: str | None = None) -> Path:
    """Return the per-proverb results file for ``model`` from compare_models.py.

    With no model given, use the newest twi_vN model. Stops with a clear
    message if compare_models.py has not been run yet.
    """
    if model is None:
        versions = sorted(
            (int(m.group(1)), path) for path in DETAILS_DIR.glob("twi_v*.csv")
            if (m := re.fullmatch(r"twi_v(\d+)", path.stem)))
        if not versions:
            raise SystemExit(f"No results in {DETAILS_DIR}/. Run `python compare_models.py` first.")
        return versions[-1][1]
    path = DETAILS_DIR / f"{model}.csv"
    if not path.exists():
        available = ", ".join(p.stem for p in sorted(DETAILS_DIR.glob("*.csv")))
        raise SystemExit(f"{path} not found. Run `python compare_models.py` first. "
                         f"Available: {available or 'none'}")
    return path

# Letters the model confuses, from the error analysis: what OCR printed ->
# what the book may really have. Swaps keep word length the same.
#
# Two sets: "i" targets only the i/l mistake, the model's main remaining
# error. "all" also swaps e/ɛ and o/ɔ; the first test showed this does more
# harm than good, because the model already reads those letters well and the
# word list's spellings do not always match the book's.
SWAP_SETS = {
    "i": {"l": "i", "I": "i", "1": "i"},
    "all": {
        "l": "iI", "I": "li", "1": "li",
        "e": "ɛ", "ɛ": "e", "o": "ɔ", "ɔ": "o",
        "E": "Ɛ", "Ɛ": "E", "O": "Ɔ", "Ɔ": "O",
        "c": "ɛe",
    },
}
CONFUSIONS = SWAP_SETS["i"]   # Replaced at run time by --swaps.
MAX_SWAPS = 2          # At most this many letters changed in one word.
MIN_WORD_COUNT = 2     # A word must appear this often to count as known.

# A "word" is a run of letters (including ɛ, ɔ and accented letters) or
# digits; everything else (spaces, punctuation) is kept exactly as it is.
WORD = re.compile(r"[^\W_]+", re.UNICODE)
TWI_SPECIAL_CHARS = set("ɛɔƐƆ")


# --- Word list ---------------------------------------------------------------

def build_vocabulary(paths: list[Path]) -> collections.Counter:
    """Count lowercase words across the given text files."""
    counts: collections.Counter = collections.Counter()
    for path in paths:
        if not path.exists():
            print(f"Skipping {path} (not found)")
            continue
        text = unicodedata.normalize("NFC", path.read_text(encoding="utf-8"))
        counts.update(w.lower() for w in WORD.findall(text))
    return collections.Counter({w: n for w, n in counts.items() if n >= MIN_WORD_COUNT})


# --- Correction --------------------------------------------------------------

def candidates(word: str):
    """Yield versions of ``word`` with up to MAX_SWAPS confusable letters swapped."""
    positions = [i for i, ch in enumerate(word) if ch in CONFUSIONS]
    for n_swaps in range(1, MAX_SWAPS + 1):
        for chosen in itertools.combinations(positions, n_swaps):
            for replacements in itertools.product(*(CONFUSIONS[word[i]] for i in chosen)):
                letters = list(word)
                for i, new in zip(chosen, replacements):
                    letters[i] = new
                yield "".join(letters)


def correct_word(word: str, vocab: collections.Counter) -> str:
    """Return the most frequent known spelling reachable by confusable swaps.

    Known words and words with no known correction are returned unchanged.
    """
    if word.lower() in vocab or word.isdigit():
        return word
    best, best_count = word, 0
    for option in candidates(word):
        count = vocab.get(option.lower(), 0)
        if count > best_count:
            best, best_count = option, count
    return best


def correct_text(text: str, vocab: collections.Counter) -> str:
    """Correct every word in a line, keeping spacing and punctuation intact."""
    return WORD.sub(lambda m: correct_word(m.group(0), vocab), text)


# --- Scoring -----------------------------------------------------------------

def special_correct(reference: str, hypothesis: str) -> int:
    """Count ɛ/ɔ/Ɛ/Ɔ in the reference that fall in unchanged alignment blocks."""
    from rapidfuzz.distance import Levenshtein
    return sum(
        sum(c in TWI_SPECIAL_CHARS for c in reference[a:b])
        for tag, a, b, _, _ in Levenshtein.opcodes(reference, hypothesis)
        if tag == "equal"
    )


def summarize(details: pd.DataFrame, ocr_column: str) -> str:
    """Return CER and ɛ/ɔ accuracy for one OCR column as a printable line."""
    from rapidfuzz.distance import Levenshtein
    edits = sum(Levenshtein.distance(r, h) for r, h in zip(details["reference"], details[ocr_column]))
    special = sum(special_correct(r, h) for r, h in zip(details["reference"], details[ocr_column]))
    cer = edits / details["reference"].str.len().sum()
    acc = special / max(details["special_total"].sum(), 1)
    return f"CER {cer:.1%}   ɛ/ɔ accuracy {acc:.1%}"


def print_change_tally(details: pd.DataFrame) -> None:
    """Show which letter swaps were made in improved vs worsened proverbs.

    A swap that appears mostly in worsened proverbs is doing harm and should
    be removed from the swap set.
    """
    tally: collections.Counter = collections.Counter()
    for ocr, fixed, before, after in zip(details["ocr"], details["corrected"],
                                         details["edits_before"], details["edits_after"]):
        if ocr == fixed or before == after:
            continue
        outcome = "improved" if after < before else "worse"
        for old, new in zip(ocr, fixed):
            if old != new:
                tally[(f"{old}->{new}", outcome)] += 1
    swaps = sorted({swap for swap, _ in tally})
    if swaps:
        print("Swaps made (in improved / worse proverbs):")
        for swap in swaps:
            print(f"  {swap}: {tally[(swap, 'improved')]} / {tally[(swap, 'worse')]}")


# --- Main --------------------------------------------------------------------

def main() -> None:
    """Correct the OCR column of one model's results and report the effect."""
    import pandas as pd
    from rapidfuzz.distance import Levenshtein
    parser = argparse.ArgumentParser(description="Twi word-list post-correction.")
    parser.add_argument("--public", action="store_true",
                        help="Build the word list from GhanaNLP text only")
    parser.add_argument("--swaps", choices=SWAP_SETS, default="i",
                        help="Which letter swaps to try (default: i)")
    parser.add_argument("--model", help="Model whose results to correct "
                        "(a file in private/eval_details/; default: newest twi_vN)")
    args = parser.parse_args()

    global CONFUSIONS
    CONFUSIONS = SWAP_SETS[args.swaps]

    sources = [GHANANLP_TXT] if args.public else [GHANANLP_TXT, BIBLE_TXT, UG_TXT]
    vocab = build_vocabulary(sources)
    print(f"Word list: {len(vocab):,} known words from {', '.join(p.name for p in sources)}")

    source = details_csv(args.model)
    print(f"Results: {source}")
    details = pd.read_csv(source).dropna(subset=["reference", "ocr"])
    details = details.drop_duplicates("number")
    details["corrected"] = [correct_text(t, vocab) for t in details["ocr"]]

    # Compare each proverb's errors before and after, so harm is visible too.
    before = [Levenshtein.distance(r, h) for r, h in zip(details["reference"], details["ocr"])]
    after = [Levenshtein.distance(r, h) for r, h in zip(details["reference"], details["corrected"])]
    details["edits_before"], details["edits_after"] = before, after
    details.to_csv(OUT_CSV, index=False, encoding="utf-8")

    better = sum(a < b for a, b in zip(after, before))
    worse = sum(a > b for a, b in zip(after, before))
    print(f"Before: {summarize(details, 'ocr')}   ({len(details)} proverbs)")
    print(f"After:  {summarize(details, 'corrected')}")
    print(f"Proverbs improved: {better}   made worse: {worse}   unchanged: {len(details) - better - worse}")
    print_change_tally(details)
    print(f"Details: {OUT_CSV}")


if __name__ == "__main__":
    main()
