"""Convert Twi text between Christaller's 1879 spelling and modern spelling.

The rules are located in orthography/christaller_1879.tsv, so that
people researching the orthography can correct them without touching code.
Each row gives a Christaller character sequence, its modern equivalent and a
direction:

    both       converted in both directions (e + line below <-> ɛ)
    to_modern  only removed or replaced when modernizing (tilde, accents)

Three functions:

    to_modern(text)       1879 diplomatic text -> modern spelling. Lossy: tone
                          accents, nasal tildes and other marks are dropped.
    to_christaller(text)  modern text -> 1879-style spelling (ɛ -> e̲, ɔ -> o̲).
                          Used to make synthetic training lines.
    add_period_marks(text, rng)
                          Sprinkles tildes, accents and other 1879 marks onto
                          converted text so a model sees them during training.
                          This is visual augmentation, not linguistics: the
                          marks are not placed where Christaller would put them.

Text is handled in NFD (letters and marks separate) internally and returned
in NFC. Note that e + U+0332 has no precomposed form, so it stays two code
points even in NFC.

    python orthography.py "O̲ba nsũ a, wommá no nũfu?"     # shows both directions
"""

import csv
import random
import sys
import unicodedata
from pathlib import Path

TABLE = Path(__file__).resolve().parent / "orthography" / "christaller_1879.tsv"


def _decode(codepoints: str) -> str:
    """Turn '0065 0332' into the two-character string e + combining line below."""
    return "".join(chr(int(cp, 16)) for cp in codepoints.split())


def load_rules(path: Path = TABLE) -> list[dict]:
    """Read the mapping table. Each rule gets decoded 'old' and 'new' strings."""
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    for row in rows:
        row["old"] = unicodedata.normalize("NFD", _decode(row["christaller_codepoints"]))
        row["new"] = unicodedata.normalize("NFD", _decode(row["modern_codepoints"]))
    # Longest sequences first, so "e + line below" is handled before a bare mark.
    return sorted(rows, key=lambda r: -len(r["old"]))


RULES = load_rules()


def to_modern(text: str) -> str:
    """Convert 1879 diplomatic text to modern spelling (drops tone and nasal marks)."""
    text = unicodedata.normalize("NFD", text)
    for rule in RULES:
        text = text.replace(rule["old"], rule["new"])
    return unicodedata.normalize("NFC", text)


def to_christaller(text: str) -> str:
    """Convert modern spelling to 1879 style: ɛ -> e̲, ɔ -> o̲ (and capitals)."""
    text = unicodedata.normalize("NFD", text)
    for rule in RULES:
        if rule["direction"] == "both":
            text = text.replace(rule["new"], rule["old"])
    return unicodedata.normalize("NFC", text)


# --- OCR clean-up --------------------------------------------------------------

def cleanup_ocr(text: str) -> str:
    """Fix two patterns the twi_1879 model produces that can never be right.

    1. A vowel written twice, once with a macron and once with a tilde
       (kāã, hōõ): the model hedging between ā and ã, which look alike in
       print. Kept as the tilde vowel, which is what the book has in every
       case found so far.
    2. A line below on a letter other than e or o (g̲, c̲): Christaller only
       underlines e and o, so the line is dropped.
    """
    import re
    text = unicodedata.normalize("NFD", text)
    text = re.sub(r"([aeiouAEIOU])\u0304\1\u0303", "\\1\u0303", text)
    text = re.sub(r"([aeiouAEIOU])\u0303\1\u0304", "\\1\u0303", text)
    text = re.sub(r"([^eoEO])\u0332", "\\1", text)
    return unicodedata.normalize("NFC", text)


# --- Synthetic augmentation (training data only) -----------------------------

TILDE, ACUTE, GRAVE, BREVE, MACRON = "\u0303", "\u0301", "\u0300", "\u0306", "\u0304"
CARON, DOT_ABOVE, DOT_BELOW, LINE_BELOW = "\u030c", "\u0307", "\u0323", "\u0332"
VOWELS = set("aeiouAEIOU")
TOP_MARKS = {TILDE, ACUTE, GRAVE, BREVE, MACRON, CARON, DOT_ABOVE}

# Rough shares, judged from pages 1 and 4 of the 1879 book. Tune them when
# more pages are transcribed. Christaller's key says tones are marked "only
# exceptionally", so accents stay rare.
MARK_SHARES = {
    "tilde_after_nasal": 0.35,   # vowel after m/n gets a tilde (nsũ, nũfu)
    "tilde_final_a": 0.10,       # word-final a gets a tilde (sumănã)
    "acute": 0.04,               # high or middle tone (wommá, abébew)
    "grave": 0.02,               # low tone (mù, abébesĕrè̲)
    "macron": 0.03,              # long vowel (Abedw̌eā)
    "breve": 0.02,               # very short vowel (sumănã, sĕre̲)
    "dot_below": 0.03,           # ẹ ọ ạ (diminished e/o, thin a)
    "w_mark": 0.6,               # w in tw/dw gets the mark (ntw̌a, Abedw̌eā)
    "w_mark_front": 0.5,         # w before e/i gets the mark (w̌erefo, aw̌ia, o̲w̌e)
    "hw_to_fw": 0.5,             # modern hw drawn as Christaller's fw̌ (fw̌e̲ = hwɛ)
    "dotted_n": 0.6,             # n before k/g gets a dot (ṅkyene)
    "dotted_n_other": 0.5,       # n at word end, or before h/w, gets a dot (baṅ, ṅhyira, ṅwo)
}


def _hw_to_fw(text: str, rng: random.Random) -> str:
    """Replace some modern 'hw' with Christaller's 'fw' (the mark over w is added later)."""
    out, i = [], 0
    while i < len(text):
        if text[i:i + 2] in ("hw", "Hw") and rng.random() < MARK_SHARES["hw_to_fw"]:
            out.append("f" if text[i] == "h" else "F")
            out.append("w")
            i += 2
        else:
            out.append(text[i])
            i += 1
    return "".join(out)


def add_period_marks(text: str, rng: random.Random) -> str:
    """Add 1879-style diacritics at plausible-looking places (visual augmentation).

    At most one mark above each letter. A tone or length mark can sit on an
    underlined vowel (è̲), as in the book; NFC puts the marks in canonical order.
    """
    text = unicodedata.normalize("NFD", text)
    text = _hw_to_fw(text, rng)        # Christaller wrote fw̌ where modern Twi has hw.
    chars = list(text)
    out: list[str] = []
    for i, ch in enumerate(chars):
        out.append(ch)
        if unicodedata.combining(ch):
            continue
        prev = chars[i - 1] if i > 0 else " "
        following = chars[i + 1:i + 3]
        if any(m in TOP_MARKS or m == DOT_BELOW for m in following):
            continue                         # Already marked.
        nxt = next((c for c in chars[i + 1:] if not unicodedata.combining(c)), " ")
        underlined = LINE_BELOW in following
        r = rng.random()
        if ch in VOWELS:
            shares = MARK_SHARES
            if prev in "mn" and r < shares["tilde_after_nasal"]:
                out.append(TILDE)
            elif ch == "a" and not nxt.isalpha() and r < shares["tilde_final_a"]:
                out.append(TILDE)
            else:
                pick = rng.random()
                cumulative = 0.0
                for name, mark in (("acute", ACUTE), ("grave", GRAVE), ("macron", MACRON),
                                   ("breve", BREVE), ("dot_below", DOT_BELOW)):
                    cumulative += shares[name]
                    if pick < cumulative:
                        if not (mark == DOT_BELOW and (underlined or ch.lower() not in "eoa")):
                            out.append(mark)
                        break
        elif ch == "w" and prev in "tTdDfF" and r < MARK_SHARES["w_mark"]:
            out.append(CARON)
        elif ch in "wW" and nxt in "eiEI" and prev not in "hH" and r < MARK_SHARES["w_mark_front"]:
            out.append(CARON)
        elif ch == "n" and nxt in "kg" and r < MARK_SHARES["dotted_n"]:
            out.append(DOT_ABOVE)
        elif ch == "n" and prev.lower() in "aeiou" and not nxt.isalpha() \
                and r < MARK_SHARES["dotted_n_other"]:
            out.append(DOT_ABOVE)           # word-final n after a vowel (baṅ)
        elif ch == "n" and nxt in "hwn" and r < MARK_SHARES["dotted_n_other"]:
            out.append(DOT_ABOVE)           # ṅhyira, ṅwo, ṅṅu
    return unicodedata.normalize("NFC", "".join(out))


if __name__ == "__main__":
    sample = " ".join(sys.argv[1:]) or "O̲ba nsũ a, wo̲mmá no nũfu?"
    print("input:         ", sample)
    print("to_modern:     ", to_modern(sample))
    print("to_christaller:", to_christaller(to_modern(sample)))
