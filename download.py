"""Build the Twi text corpus used to render OCR training images.

This script collects Twi sentences from two sources, normalizes them, removes
duplicates, and writes one sentence per line to plain-text files:

    1. GhanaNLP Twi-English parallel datasets
    2. Bible verses in Asante and Akuapem Twi, produced beforehand with the
       Ghana Corpus Builder and saved to ``private/bible_twi.csv``.

Outputs:
    data/TWI_ENGLISH_PARALLEL_TEXT.csv   Untouched copy of the source dataset.
    data/ENGLISH_TWI_PARALLEL_TEXT.csv   Untouched copy of the source dataset.
    data/twi_ghananlp.txt                Cleaned GhanaNLP Twi sentences.
    private/twi_bible.txt                Cleaned Bible verses (not for release).

Licensing:
    GhanaNLP data: CC BY-NC-SA 4.0 (non-commercial; credit GhanaNLP).
    Ghana Corpus (Bible text): CC BY-NC 4.0; the underlying translations
    belong to their publishers, so the Bible output stays in ``private/``.

Usage:
    pip install datasets pandas openpyxl
    python download.py
"""

import unicodedata
from pathlib import Path

import pandas as pd
from datasets import load_dataset

# --- Configuration -----------------------------------------------------------

OUT_DIR = Path("data")
PRIVATE_DIR = Path("private")
BIBLE_CSV = PRIVATE_DIR / "bible_twi.csv"

# Each GhanaNLP dataset stores Twi in a different column, so each repository
# ID is paired with the name of its Twi column.
GHANANLP_SOURCES = [
    ("Ghana-NLP/TWI_ENGLISH_PARALLEL_TEXT", "text"),   # text = Twi, label = English
    ("Ghana-NLP/ENGLISH_TWI_PARALLEL_TEXT", "label"),  # text = English, label = Twi
]

# Candidate names for the Twi column in the Bible CSV, tried in order.
BIBLE_COLUMN_CANDIDATES = ["local", "twi", "text", "sentence"]

# Twi-specific letters, used to detect the Twi column and to check output.
TWI_SPECIAL_CHARS = "ɛɔƐƆ"

# Lookalike characters found in the source text, mapped to the correct Twi
# letters. They look the same on screen but are different Unicode characters,
# so without this the model would learn two versions of the same letter.
CHARACTER_FIXES = str.maketrans({
    "ε": "ɛ",   # U+03B5 Greek small epsilon      -> U+025B Latin small open e
    "Ε": "Ɛ",   # U+0395 Greek capital epsilon    -> U+0190 Latin capital open E
    "Ꜫ": "Ɛ",   # U+A72A Latin capital tresillo   -> U+0190 Latin capital open E
    "ℇ": "Ɛ",   # U+2107 Euler constant sign      -> U+0190 Latin capital open E (UGSpeechData)
    "ᴐ": "ɔ",   # U+1D10 small capital open O     -> U+0254 Latin small open o
    "ↄ": "ɔ",   # U+2184 Latin small reversed C   -> U+0254 Latin small open o
    "Ↄ": "Ɔ",   # U+2183 Roman numeral reversed C -> U+0186 Latin capital open O
    "ꓛ": "Ɔ",   # U+A4DB Lisu letter (reversed C) -> U+0186 Latin capital open O
    "ȼ": "₵",   # U+023C c with stroke, used for the Ghana cedi sign -> U+20B5
    # Invisible characters copied in from web text. Tesseract cannot learn a
    # character that prints nothing, and skips any line that contains one.
    "​": None,  # zero-width space
    "‌": None,  # zero-width non-joiner
    "‍": None,  # zero-width joiner
    "﻿": None,  # byte-order mark / zero-width no-break space
    "­": None,  # soft hyphen
})

# Lines containing these characters are dropped: they appear only as isolated
# typos in the source text and are not part of Twi spelling.
DROP_LINES_WITH = set("ʋƲ")


# --- Helpers -----------------------------------------------------------------

def clean(text: object) -> str:
    """Normalize a sentence so identical text is always stored identically.

    Applies Unicode NFC normalization, which merges a base letter and a
    separate combining accent (for example ``a`` + ``◌́``) into a single
    precomposed character. Without this, visually identical Twi words with
    tone marks could be stored in two different ways. Also trims the ends and
    collapses runs of whitespace into single spaces, and replaces lookalike
    characters (see ``CHARACTER_FIXES``) with the correct Twi letters.

    Args:
        text: A cell value from a dataset; non-string values are converted.

    Returns:
        The normalized sentence on a single line, or an empty string if the
        line contains a character listed in ``DROP_LINES_WITH``.
    """
    normalized = unicodedata.normalize("NFC", str(text)).strip()
    normalized = normalized.translate(CHARACTER_FIXES)
    if any(c in DROP_LINES_WITH for c in normalized):
        return ""
    return " ".join(normalized.split())


def find_twi_column(df: pd.DataFrame) -> str:
    """Return the name of the column that holds Twi text.

    The Ghana Corpus Builder does not document its column names, so known
    names are tried first. If none match, the text column containing the most
    Twi-specific letters (ɛ, ɔ) is chosen.

    Args:
        df: The Bible CSV loaded as a DataFrame.

    Returns:
        The name of the Twi column.
    """
    for name in BIBLE_COLUMN_CANDIDATES:
        if name in df.columns:
            return name

    # Covers both the classic "object" dtype and pandas' newer "string" dtype.
    text_columns = df.select_dtypes(include=["object", "string"]).columns
    pattern = f"[{TWI_SPECIAL_CHARS}]"
    return max(text_columns, key=lambda c: df[c].astype(str).str.count(pattern).sum())


def deduplicate(sentences: list[str]) -> list[str]:
    """Remove empty strings and repeated sentences, keeping first-seen order.

    Args:
        sentences: Cleaned sentences, possibly with duplicates.

    Returns:
        Unique, non-empty sentences in their original order.
    """
    return list(dict.fromkeys(s for s in sentences if s))


def count_with_special_chars(sentences: list[str]) -> int:
    """Count sentences that contain at least one ɛ or ɔ (either case)."""
    return sum(1 for s in sentences if any(c in s for c in TWI_SPECIAL_CHARS))


# --- Data loading ------------------------------------------------------------

def load_ghananlp() -> list[str]:
    """Download the GhanaNLP datasets and return their cleaned Twi sentences.

    An untouched CSV copy of each dataset is saved to ``OUT_DIR`` so the
    original source can always be checked.

    Returns:
        Cleaned Twi sentences from all GhanaNLP sources (may contain
        duplicates across datasets).
    """
    sentences: list[str] = []
    for repo_id, twi_column in GHANANLP_SOURCES:
        dataset = load_dataset(repo_id, split="train")

        repo_name = repo_id.split("/")[1]
        dataset.to_csv(OUT_DIR / f"{repo_name}.csv")

        rows = [clean(value) for value in dataset[twi_column] if value]
        print(f"{repo_id}: {len(rows):,} Twi sentences")
        sentences.extend(rows)
    return sentences


def load_bible() -> list[str]:
    """Load and clean the Bible verses produced by the Ghana Corpus Builder.

    Returns:
        Cleaned Twi verses, or an empty list if ``BIBLE_CSV`` is missing.
    """
    if not BIBLE_CSV.exists():
        print(f"{BIBLE_CSV} not found; skipping Bible text")
        return []

    df = pd.read_csv(BIBLE_CSV)
    twi_column = find_twi_column(df)
    verses = [clean(value) for value in df[twi_column].dropna()]
    print(f"{BIBLE_CSV}: {len(verses):,} verses (column '{twi_column}')")
    return verses


# --- Main --------------------------------------------------------------------

def main() -> None:
    """Build, save and summarize the GhanaNLP and Bible Twi corpora."""
    OUT_DIR.mkdir(exist_ok=True)
    PRIVATE_DIR.mkdir(exist_ok=True)

    ghananlp = deduplicate(load_ghananlp())
    bible = deduplicate(load_bible())

    # Sources are written separately so the training mix can be controlled
    # later; the Bible text is formal and far larger than the GhanaNLP set.
    # UTF-8 is required to store ɛ, ɔ and tone marks correctly.
    (OUT_DIR / "twi_ghananlp.txt").write_text("\n".join(ghananlp), encoding="utf-8")
    (PRIVATE_DIR / "twi_bible.txt").write_text("\n".join(bible), encoding="utf-8")

    print(f"Saved {len(ghananlp):,} GhanaNLP sentences to {OUT_DIR / 'twi_ghananlp.txt'}")
    print(f"Saved {len(bible):,} Bible verses to {PRIVATE_DIR / 'twi_bible.txt'}")

    # Sanity check: nearly every Twi line should contain ɛ or ɔ.
    for name, sentences in [("GhanaNLP", ghananlp), ("Bible", bible)]:
        print(f"{name}: {count_with_special_chars(sentences):,} lines contain ɛ or ɔ")


if __name__ == "__main__":
    main()
