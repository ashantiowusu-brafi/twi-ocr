"""List every e/ɛ and o/ɔ disagreement between the answer key and the OCR.

Some of these are OCR mistakes and some are typos in the answer key. This
script writes a review sheet so each case can be checked against the scan.

Input:
    private/eval_details/<model>.csv   Written by compare_models.py
                                       (default: the newest twi_vN model).

Output:
    private/letter_review.xlsx     One row per disagreement, sorted by
                                   proverb number. Contains book text, so it
                                   stays private.

Columns:
    number, scan    Where to look.
    key_word        The whole word as typed in the answer key.
    ocr_word        The same word as the OCR read it.
    key_letter      The letter in the key (for example e).
    ocr_letter      What the OCR read instead (for example ɛ).
    book_shows      Left blank: fill in what the scan actually shows.

Usage:
    python tools/answer_key/review_letters.py
    python tools/answer_key/review_letters.py --model twi_v3
"""

import argparse
import sys
from pathlib import Path

import pandas as pd
from rapidfuzz.distance import Levenshtein

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # main folder, for postcorrect.py
import postcorrect as pc

REVIEW_XLSX = Path("private/letter_review.xlsx")

# Pairs of letters the model confuses, in both directions.
CONFUSABLE = {("e", "ɛ"), ("ɛ", "e"), ("o", "ɔ"), ("ɔ", "o"),
              ("E", "Ɛ"), ("Ɛ", "E"), ("O", "Ɔ"), ("Ɔ", "O")}


def word_at(text: str, index: int) -> str:
    """Return the whole space-separated word that contains ``text[index]``."""
    start = text.rfind(" ", 0, index) + 1
    end = text.find(" ", index)
    return text[start:end if end != -1 else len(text)]


def main() -> None:
    """Find every confusable-letter substitution and write the review sheet."""
    parser = argparse.ArgumentParser(description="List e/ɛ and o/ɔ disagreements for review.")
    parser.add_argument("--model", help="Model whose results to check "
                        "(a file in private/eval_details/; default: newest twi_vN)")
    source = pc.details_csv(parser.parse_args().model)
    print(f"Results: {source}")
    details = pd.read_csv(source).dropna(subset=["reference", "ocr"])
    rows = []
    for number, scan, ref, hyp in zip(details["number"], details["scan"],
                                      details["reference"], details["ocr"]):
        for tag, a, b, c, d in Levenshtein.opcodes(ref, hyp):
            # Only one-for-one swaps, such as e -> ɛ, are of interest here.
            if tag != "replace" or (b - a) != (d - c):
                continue
            for offset in range(b - a):
                key_letter, ocr_letter = ref[a + offset], hyp[c + offset]
                if (key_letter, ocr_letter) in CONFUSABLE:
                    rows.append({
                        "number": int(number),
                        "scan": scan,
                        "key_word": word_at(ref, a + offset),
                        "ocr_word": word_at(hyp, c + offset),
                        "key_letter": key_letter,
                        "ocr_letter": ocr_letter,
                        "book_shows": "",
                    })

    review = pd.DataFrame(rows).sort_values(["number", "key_word"])
    review.to_excel(REVIEW_XLSX, index=False)

    print(f"{len(review)} disagreements in {review['number'].nunique()} proverbs")
    print(review.groupby(["key_letter", "ocr_letter"]).size().sort_values(ascending=False).to_string())
    print(f"\nReview sheet: {REVIEW_XLSX}")


if __name__ == "__main__":
    main()
