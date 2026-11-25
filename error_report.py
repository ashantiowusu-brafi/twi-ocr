"""Summarize what one model still gets wrong, as a report anyone can rerun.

It reads the per-proverb details written by compare_models.py and reports:

    1. Overall CER and ɛ/ɔ accuracy.
    2. Twi-letter errors: what ɛ, ɔ, Ɛ and Ɔ were misread as.
    3. Other errors: the most common character swaps, drops and insertions.
    4. Proverbs starting with Ɔ or Ɛ where the OCR lost that capital.
    5. Quote-mark errors: what “ ” ’ were read as.

The report quotes only single characters or short fragments (at most
three characters), never whole words or proverbs, so it can be published.

Input:
    private/eval_details/<model>.csv    From compare_models.py.

Output:
    eval/errors_<model>.md              Also printed to the screen.

Usage:
    python error_report.py --model twi_v4
    python error_report.py --model twi_v4_postcorrect_public
"""

import argparse
import collections
from pathlib import Path

import pandas as pd
from rapidfuzz.distance import Levenshtein

DETAILS_DIR = Path("private/eval_details")
EVAL_DIR = Path("eval")
TWI_SPECIAL_CHARS = set("ɛɔƐƆ")
QUOTE_MARKS = set("“”’‘\"'")
MAX_FRAGMENT = 3   # Longer fragments are summarized, to avoid quoting the book.
TOP_N = 12


def show(fragment: str) -> str:
    """Format a fragment for the report, hiding anything longer than 3 characters."""
    if fragment == "":
        return "(nothing)"
    if len(fragment) > MAX_FRAGMENT:
        return f"({len(fragment)} characters)"
    return repr(fragment)


def tally_errors(details: pd.DataFrame) -> tuple[collections.Counter, collections.Counter, collections.Counter]:
    """Count Twi-letter, quote-mark and other errors from the edit alignment."""
    twi, quotes, other = collections.Counter(), collections.Counter(), collections.Counter()
    for ref, hyp in zip(details["reference"], details["ocr"]):
        for tag, a, b, c, d in Levenshtein.opcodes(ref, hyp):
            if tag == "equal":
                continue
            key_part, ocr_part = ref[a:b], hyp[c:d]
            # One-for-one swaps are split per character so they are counted individually.
            if tag == "replace" and (b - a) == (d - c):
                pairs = list(zip(key_part, ocr_part))
            else:
                pairs = [(key_part, ocr_part)]
            for k, o in pairs:
                if any(ch in TWI_SPECIAL_CHARS for ch in k):
                    twi[(k, o)] += 1
                elif any(ch in QUOTE_MARKS for ch in k + o):
                    quotes[(k, o)] += 1
                else:
                    other[(k, o)] += 1
    return twi, quotes, other


def table(counter: collections.Counter, title: str) -> list[str]:
    """Render the most common (key, ocr) pairs as a Markdown table."""
    lines = [f"## {title}", "", "| Book (answer key) | Read as | Count |", "| --- | --- | --- |"]
    for (k, o), n in counter.most_common(TOP_N):
        lines.append(f"| {show(k)} | {show(o)} | {n} |")
    if not counter:
        lines.append("| — | — | 0 |")
    return lines + [""]


def main() -> None:
    """Build the error report for one model."""
    parser = argparse.ArgumentParser(description="Report one model's remaining errors.")
    parser.add_argument("--model", required=True, help="Name of a file in private/eval_details/")
    args = parser.parse_args()

    path = DETAILS_DIR / f"{args.model}.csv"
    if not path.exists():
        available = ", ".join(p.stem for p in sorted(DETAILS_DIR.glob("*.csv")))
        raise SystemExit(f"{path} not found. Run compare_models.py first. Available: {available}")

    details = pd.read_csv(path).fillna({"ocr": ""})
    cer = details["edits"].sum() / details["chars"].sum()
    special = details["special_correct"].sum() / max(details["special_total"].sum(), 1)
    twi, quotes, other = tally_errors(details)

    lost_capitals = sum(
        1 for ref, hyp in zip(details["reference"], details["ocr"])
        if ref[:1] in "ƆƐ" and ref[:1] not in hyp
    )
    capital_total = sum(1 for ref in details["reference"] if ref[:1] in "ƆƐ")

    report = [
        f"# Remaining errors: `{args.model}`",
        "",
        f"{len(details)} proverbs. CER {cer:.1%}, ɛ/ɔ accuracy {special:.1%}. "
        f"Errors by type: Twi letters {sum(twi.values())}, quote marks {sum(quotes.values())}, "
        f"other {sum(other.values())}.",
        "",
        f"Proverbs starting with Ɔ or Ɛ where the OCR lost that capital: "
        f"{lost_capitals} of {capital_total}.",
        "",
        *table(twi, "Twi letters (ɛ, ɔ, Ɛ, Ɔ)"),
        *table(quotes, "Quote marks"),
        *table(other, "Other errors"),
        "Fragments longer than three characters are shown as a length only, "
        "so that the report does not reproduce the book's text.",
    ]
    text = "\n".join(report) + "\n"
    out = EVAL_DIR / f"errors_{args.model}.md"
    EVAL_DIR.mkdir(exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(text)
    print(f"Saved: {out}")


if __name__ == "__main__":
    main()
