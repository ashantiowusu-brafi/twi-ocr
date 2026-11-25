"""Find words where the book's spelling differs from the word list's spelling.

Runs the full post-correction (including e/ɛ and o/ɔ swaps) on the OCR
results and keeps only the changes that broke a word the OCR had read
correctly. Each of these is a word the book spells differently from the
GhanaNLP/Bible text, for example "efiri" in the book versus "ɛfiri" in the
word list. Check them against the scans: some may be answer-key typos, and
the rest show the book's own spelling conventions.

Input:
    private/eval_details/<model>.csv   Written by compare_models.py
                                       (default: the newest twi_vN model).
    postcorrect.py                  Must be in the same folder.

Output:
    private/spelling_review.xlsx    One row per affected word (book text,
                                    so it stays private).

Columns:
    number, scan        Where to look.
    book_word           The word as in the answer key, which the OCR matched.
    changed_to          What post-correction turned it into.
    book_word_count     How often the book's spelling appears in the word list.
    changed_to_count    How often the "standard" spelling appears.
    book_shows          Left blank: fill in what the scan actually shows.

Usage:
    python tools/answer_key/spelling_review.py
    python tools/answer_key/spelling_review.py --model twi_v3
"""

import argparse
from pathlib import Path

import pandas as pd

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # main folder, for postcorrect.py
import postcorrect as pc

REVIEW_XLSX = Path("private/spelling_review.xlsx")


def main() -> None:
    """List every correct OCR word that the full swap set changed."""
    parser = argparse.ArgumentParser(description="List words the book spells differently from the word list.")
    parser.add_argument("--model", help="Model whose results to check "
                        "(a file in private/eval_details/; default: newest twi_vN)")
    source = pc.details_csv(parser.parse_args().model)
    print(f"Results: {source}")

    pc.CONFUSIONS = pc.SWAP_SETS["all"]
    vocab = pc.build_vocabulary([pc.GHANANLP_TXT, pc.BIBLE_TXT])

    details = pd.read_csv(source).dropna(subset=["reference", "ocr"])
    details = details.drop_duplicates("number")

    rows = []
    for number, scan, ref, ocr in zip(details["number"], details["scan"],
                                      details["reference"], details["ocr"]):
        key_words = {w for w in pc.WORD.findall(ref)}
        for word in pc.WORD.findall(ocr):
            fixed = pc.correct_word(word, vocab)
            # Harmful change: the OCR word matched the key, the new one does not.
            if fixed != word and word in key_words and fixed not in key_words:
                rows.append({
                    "number": int(number),
                    "scan": scan,
                    "book_word": word,
                    "changed_to": fixed,
                    "book_word_count": vocab.get(word.lower(), 0),
                    "changed_to_count": vocab.get(fixed.lower(), 0),
                    "book_shows": "",
                })

    if not rows:
        print("No correct words were changed.")
        return

    review = pd.DataFrame(rows).sort_values(["number", "book_word"])
    review.to_excel(REVIEW_XLSX, index=False)

    print(f"{len(review)} correct words changed, in {review['number'].nunique()} proverbs")
    print("Most common spelling differences (book -> word list):")
    common = review.groupby(["book_word", "changed_to"]).size().sort_values(ascending=False)
    for (book, changed), n in common.head(15).items():
        print(f"  {book} -> {changed}: {n}")
    print(f"\nReview sheet: {REVIEW_XLSX}")


if __name__ == "__main__":
    main()
