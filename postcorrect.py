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
UG_TXT = Path("private/twi_ug.txt")
# English words for the English check (issue T7): the lowercase words of
# Tesseract's English model (tessdata_best eng.traineddata, Apache-2.0).
ENGLISH_TXT = Path(__file__).resolve().parent / "wordlists" / "english_words.txt"   # From prepare_ug.py; private only.
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


# --- Correcting a whole page (Twi and English lines) ------------------------
#
# Bu Me Bɛ prints English beside the Twi, and the Twi models misread the italic
# English in their own ways (issue T7 in ORTHOGRAPHY.md). correct_page() looks
# at each line: on a Twi line it makes the l -> i fixes above; on an English
# line it skips them (they were built for Twi) and fixes only clear English
# mistakes. Every change is returned with its position, so it can be shown and
# undone. Doubled punctuation (";:", ".,") is only flagged, because "etc.," is
# correct English.

OPEN_TO_PLAIN = str.maketrans("ɔɛƆƐ", "oeOE")
SMALL_CAPITAL_WORDS = {"Is": "is", "It": "it", "In": "in", "If": "if", "Its": "its"}
# A capital Is/It/In/If/Its straight after a lowercase word, as in "coming, it Is coming".
MID_SENTENCE_CAPITAL = re.compile(r"(?<=[a-z][,;] )(Is|It|In|If|Its)\b|(?<=[a-z] )(Is|It|In|If|Its)\b")
# A word, which may contain "!" read for l (wil!, va!ued) or an apostrophe.
TOKEN = re.compile(r"[^\W\d_!]+(?:[!’'][^\W\d_!]+)*!?")
DOUBLED_PUNCTUATION = re.compile(r"[;:,.][;:,]|[;:,][.]")


def load_english_words(path: Path = ENGLISH_TXT) -> set[str]:
    """Return the English word list (lowercase), or an empty set if it is missing."""
    if not path.exists():
        return set()
    return {w.strip() for w in path.read_text(encoding="utf-8").splitlines() if w.strip()}


def _line_kind(line: str, english: set[str], twi: set[str]) -> tuple[int, int]:
    """Return (English-only words, Twi-only words) in a line."""
    words = [w.lower().replace("’", "'") for w in WORD.findall(line) if len(w) > 1]
    eng = sum((w in english or w.translate(OPEN_TO_PLAIN) in english) and w not in twi for w in words)
    tw = sum(w in twi and w not in english for w in words)
    return eng, tw


def english_lines(lines: list[str], english: set[str], twi: set[str]) -> list[bool]:
    """Mark which lines are English: clearly English, or English-leaning next to one."""
    counts = [_line_kind(l, english, twi) for l in lines]
    clear = [e >= 2 and e > t for e, t in counts]
    return [c or (e >= 1 and t == 0 and ((i > 0 and clear[i - 1]) or (i + 1 < len(lines) and clear[i + 1])))
            for i, (c, (e, t)) in enumerate(zip(clear, counts))]


COMMON_TWO_LETTER = {"of", "on", "or", "so", "to", "no", "go", "do", "be", "he", "me", "we", "oh"}


def _fix_english_word(word: str, english: set[str], twi: set[str],
                      followed_by: str) -> tuple[str, str, str] | None:
    """Return (new word, kind, reason) for a misread English word, else None.

    kind is "fix" when one reading is clear, or "check" when it is not.
    """
    lower = word.lower().replace("’", "'")
    if "!" in word:
        if word.endswith("!") and not re.match(r" [a-z]", followed_by):
            return None   # A real "!" at the end of a clause.
        as_l, as_t = word.replace("!", "l"), word.replace("!", "t")
        l_ok, t_ok = as_l.lower() in english, as_t.lower() in english
        if lower in english or len(as_l) < 4 or not (l_ok or t_ok):
            return None
        if l_ok and (not t_ok or as_l.lower().endswith("ll")):
            return as_l, "fix", "! read for l"
        if t_ok and not l_ok:   # Often an apostrophe (don!t, don't): check, don't change.
            return word, "check", f"! may be t or an apostrophe ({as_t})"
        return word, "check", f"! read for l or t ({as_l} or {as_t})"
    if re.search("[ɔɛƆƐ]", word):
        fixed = word.translate(OPEN_TO_PLAIN)
        if lower in twi or fixed.lower() not in english:
            return None
        if len(fixed) == 2 and fixed.lower() not in COMMON_TWO_LETTER:
            return None
        return fixed, "fix", "ɔ/ɛ in an English word"
    if word == "ir":
        return "it", "fix", "ir read for it"
    return None


def correct_page(text: str, vocab: collections.Counter, english: set[str] | None = None) -> tuple[str, list[dict]]:
    """Correct a page line by line; return the new text and a list of changes.

    Each change is {"start", "end", "old", "new", "kind", "why"}: start and end
    are positions in the returned text; kind is "fix" for a change made, or
    "check" for a spot flagged for review (old == new). Without an English word
    list, every line gets the l -> i fixes, as correct_text() does.
    """
    twi = set(vocab)
    lines = text.split("\n")
    is_english = english_lines(lines, english, twi) if english else [False] * len(lines)
    out_lines, changes, offset = [], [], 0
    for line, eng in zip(lines, is_english):
        edits: list[tuple[int, int, str, str]] = []   # (start, end, new, why) in the original line
        checks: list[tuple[int, int, str]] = []        # (start, end, why): flagged, not changed
        if eng:
            for m in TOKEN.finditer(line):
                fix = _fix_english_word(m.group(0), english, twi, line[m.end():m.end() + 2])
                if fix and fix[1] == "fix":
                    edits.append((m.start(), m.end(), fix[0], fix[2]))
                elif fix:
                    checks.append((m.start(), m.end(), fix[2]))
            for m in MID_SENTENCE_CAPITAL.finditer(line):
                if not any(a <= m.start() < b for a, b, _, _ in edits):
                    edits.append((m.start(), m.end(), SMALL_CAPITAL_WORDS[m.group(0)], "capital I read for i"))
        else:
            for m in WORD.finditer(line):
                word = m.group(0)
                new = correct_word(word, vocab)
                if new == word and word[:2] in ("ƐE", "ƆO") and word.lower() not in twi:
                    candidate = word[0] + word[2:]
                    if candidate.lower() in twi:
                        new = candidate
                        edits.append((m.start(), m.end(), new, "letter read twice"))
                        continue
                if new != word:
                    edits.append((m.start(), m.end(), new, "l read for i"))
        edits.sort()
        built, last, shift = [], 0, 0
        for start, end, new, why in edits:
            built.append(line[last:start] + new)
            changes.append({"start": offset + start + shift, "end": offset + start + shift + len(new),
                            "old": line[start:end], "new": new, "kind": "fix", "why": why})
            shift += len(new) - (end - start)
            last = end
        built.append(line[last:])
        new_line = "".join(built)
        for start, end, why in checks:   # Flagged words: move their positions past earlier edits.
            moved = start + sum(len(n) - (e - s) for s, e, n, _ in edits if e <= start)
            changes.append({"start": offset + moved, "end": offset + moved + end - start,
                            "old": line[start:end], "new": line[start:end], "kind": "check", "why": why})
        if eng:
            for m in DOUBLED_PUNCTUATION.finditer(new_line):
                changes.append({"start": offset + m.start(), "end": offset + m.end(), "old": m.group(0),
                                "new": m.group(0), "kind": "check", "why": "doubled punctuation"})
        out_lines.append(new_line)
        offset += len(new_line) + 1
    return "\n".join(out_lines), sorted(changes, key=lambda c: c["start"])


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
