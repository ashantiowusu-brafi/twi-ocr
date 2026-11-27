"""Sort the lines of a read page into entries: proverb, translation, explanation.

A book of proverbs prints each entry the same way:

    212. Ɔbanyansafoɔ na yɛkyerɛ no adeɛ soro a, ɔhwɛ      <- proverb (Twi), numbered
    fam.                                                   <- proverb, continued
    A wise person, if we show them something above,       <- English translation
    looks on the ground.
    (A wise person considers all sides to a question).    <- explanation, in brackets

Each line gets a label. Starting rules give a first answer (a number starts a
proverb, English lines are the translation, a bracket starts the explanation).
On top of the rules sits a small model that learns from the lines the user
re-sorts in the app: it weighs clues such as "starts with a number", "mostly
English words", "inside an open bracket" and "the line before was a
translation". With no corrections it follows the rules; every page the user
sorts by hand teaches it the book's habits. It runs offline in plain Python.

The text is never changed: lines are only sorted into columns. The one
exception is the bracket pair around an explanation, which the table leaves out
(as in the answer key); the saved .txt files keep the page as printed.

    sorter = Sorter("proverbs", english, twi, store=Path("proverbs.json"))
    labels = sorter.label(lines)
    entries = build_entries(lines, labels)
    sorter.teach("book.pdf#12", lines, corrected_labels)
"""
from __future__ import annotations

import json
import os
import random
import re
from pathlib import Path

PROVERB, TRANSLATION, EXPLANATION, OTHER = "proverb", "translation", "explanation", "other"

LAYOUTS = {
    "proverbs": {
        "label": "Proverbs",
        "labels": [PROVERB, TRANSLATION, EXPLANATION, OTHER],
        "names": {PROVERB: "Proverb (Twi)", TRANSLATION: "English translation",
                  EXPLANATION: "Explanation", OTHER: "Not part of an entry"},
        "required": [PROVERB, TRANSLATION, EXPLANATION],   # Every entry has all three.
    },
}

WORD = re.compile(r"[^\W\d_]+(?:['’][^\W\d_]+)*")
# "212." / "2010." / OCR slips such as "218," or "2S.," at the start of a line.
NUMBER = re.compile(r"^\s*([0-9][0-9SOolI]{0,4})\s*[.,]+\s+(?=\S)")
SENTENCE_END = re.compile(r"[.!?][”’\"']?\s*$")
OCR_DIGITS = str.maketrans("SOolI", "50011")
TWI_LETTERS = set("ɛɔƐƆ")
OPEN_TO_PLAIN = str.maketrans("ɛɔƐƆ", "eoEO")
# Running heads and the column marker between two columns of a page.
HEADER = re.compile(r"^(=+COLUMN=+|proverbs of the akans\.?|bu me b[ɛe]\.?)$", re.IGNORECASE)


# --- Clues about one line ------------------------------------------------------

def _counts(line: str, english: set[str], twi: set[str]) -> tuple[int, int]:
    """(English-only words, Twi-only words) in a line."""
    words = [w.lower().replace("’", "'") for w in WORD.findall(line) if len(w) > 1]
    eng = sum((w in english or w.translate(OPEN_TO_PLAIN) in english) and w not in twi for w in words)
    tw = sum(w in twi and w not in english for w in words)
    return eng, tw


def _is_junk(line: str) -> bool:
    """A scrap of noise: almost no letters (stray marks, page numbers, smudges)."""
    letters = sum(c.isalpha() for c in line)
    return letters < 3 or letters < 0.45 * len(line.replace(" ", ""))


def _language(eng: int, tw: int, line: str) -> str:
    has_twi_letter = any(c in TWI_LETTERS for c in line)
    if eng >= 2 and eng > tw:
        return "english"
    if tw > eng or (has_twi_letter and eng <= 1):
        return "twi"
    if eng == 1 and tw == 0:
        return "english-ish"
    return "unknown"


def _paren_depths(lines: list[str]) -> list[int]:
    """How many brackets are still open before each line (never below zero)."""
    depth, out = 0, []
    for line in lines:
        out.append(depth)
        depth = max(0, depth + line.count("(") - line.count(")"))
        if depth > 2:   # A missing ")" should not swallow the rest of the page.
            depth = 0
    return out


def page_lines(text: str) -> list[str]:
    """The lines worth sorting: every line that is not blank, as printed."""
    return [l.strip() for l in text.splitlines() if l.strip()]


# --- Starting rules -------------------------------------------------------------

def rule_labels(lines: list[str], english: set[str], twi: set[str]) -> list[str]:
    """A first answer from the layout's habits, line by line."""
    depths = _paren_depths(lines)
    labels: list[str] = []
    state = OTHER
    for i, line in enumerate(lines):
        eng, tw = _counts(line, english, twi)
        lang = _language(eng, tw, line)
        starts_paren = line.startswith(("(", "[("))
        # A closing bracket with no opening one: an explanation whose "(" was misread.
        stray_close = depths[i] == 0 and ")" in line and "(" not in line
        # A short line that closes an open bracket ("it).") ends the explanation; it is not noise.
        closes = depths[i] > 0 and ")" in line and any(c.isalpha() for c in line)
        if HEADER.match(line) or (_is_junk(line) and not closes):
            labels.append(OTHER)
            continue
        if NUMBER.match(line):
            state = PROVERB
        elif state == PROVERB:
            if starts_paren:
                state = EXPLANATION
            elif lang == "english" or (lang == "english-ish" and line[:1].isupper()):
                state = TRANSLATION        # "fam." finishing a proverb stays with the proverb.
        elif state == TRANSLATION:
            # A new sentence after a finished translation is the explanation, even when
            # its "(" was misread ("dn time of need ...").
            prev_eng, prev_tw = _counts(lines[i - 1], english, twi)
            finished = (bool(SENTENCE_END.search(lines[i - 1])) and depths[i] == 0
                        and _language(prev_eng, prev_tw, lines[i - 1]) == "english")
            if starts_paren or stray_close or (finished and line[:1].isupper() and lang != "twi"):
                state = EXPLANATION
        elif state == EXPLANATION:
            if depths[i] > 0:
                pass                       # Still inside the explanation's brackets.
            elif starts_paren:
                pass                       # A second bracketed note.
            elif lang == "english" and len(line) >= 25:
                pass                       # An explanation printed without brackets.
            else:
                state = OTHER
        else:   # Top of a page: the end of an entry begun on the page before.
            if starts_paren or stray_close:
                state = EXPLANATION
            elif lang == "english":
                state = TRANSLATION
            elif lang == "twi":
                state = PROVERB
            else:
                labels.append(OTHER)
                continue
        labels.append(state)
    return labels


# --- The learning part ------------------------------------------------------------

def _features(lines: list[str], i: int, prev: str, rule: str, depth: int,
              english: set[str], twi: set[str]) -> list[str]:
    line = lines[i]
    eng, tw = _counts(line, english, twi)
    lang = _language(eng, tw, line)
    words = WORD.findall(line)
    first = words[0].lower() if words else ""
    f = ["bias", f"rule={rule}", f"prev={prev}", f"lang={lang}", f"prev={prev}|lang={lang}",
         f"open={depth > 0}", f"prev={prev}|open={depth > 0}"]
    if NUMBER.match(line):
        f += ["number", f"prev={prev}|number"]
    if line.startswith("("):
        f += ["starts(", f"prev={prev}|starts("]
    if line.rstrip(".,;: ").endswith(")"):
        f.append("ends)")
    if ")" in line and "(" not in line and depth == 0:
        f.append("stray)")
    if line[:1].islower():
        f += ["starts-lower", f"prev={prev}|starts-lower"]
    if line[:1] in "“\"‘'":
        f.append("starts-quote")
    if any(c in TWI_LETTERS for c in line):
        f.append("twi-letter")
    if _is_junk(line):
        f.append("junk")
    if HEADER.match(line):
        f.append("header")
    f.append(f"len={min(len(line) // 15, 4)}")
    if first:
        f.append(f"first={first}")
    if i == 0:
        f.append("first-line")
    return f


class Sorter:
    """Labels lines with the starting rules plus what it learned from corrections."""

    # How strongly the starting rules count: one corrected line must not overturn them
    # everywhere, but a habit the user corrects again and again does.
    RULE_WEIGHT = float(os.environ.get("TWI_OCR_RULE_WEIGHT", "3"))
    EPOCHS = 8

    def __init__(self, layout: str, english: set[str], twi: set[str], store: Path | None = None):
        self.layout = layout
        self.labels = LAYOUTS[layout]["labels"]
        self.english, self.twi = english, twi
        self.store = store
        self.pages: dict[str, list[list[str]]] = {}   # page id -> [[line, label], ...]
        self.weights: dict[tuple[str, str], float] = {}
        if store and store.exists():
            try:
                self.pages = json.loads(store.read_text(encoding="utf-8")).get("pages", {})
            except (OSError, ValueError):
                self.pages = {}
        self._train()

    @property
    def taught_pages(self) -> int:
        return len(self.pages)

    def _score(self, feats: list[str], label: str) -> float:
        prior = self.RULE_WEIGHT if f"rule={label}" in feats else 0.0
        return prior + sum(self.weights.get((f, label), 0.0) for f in feats)

    def _best(self, feats: list[str]) -> str:
        return max(self.labels, key=lambda lab: self._score(feats, lab))

    def label(self, lines: list[str]) -> list[str]:
        rules = rule_labels(lines, self.english, self.twi)
        depths = _paren_depths(lines)
        out: list[str] = []
        prev = "start"
        for i in range(len(lines)):
            lab = self._best(_features(lines, i, prev, rules[i], depths[i], self.english, self.twi))
            out.append(lab)
            prev = lab
        return out

    def _train(self) -> None:
        """Averaged perceptron over every page the user has sorted.

        Pages are read top to bottom as the app reads them, using the model's own
        label for the line before, so it learns to recover from its own slips.
        """
        pages = []
        for rows in self.pages.values():
            lines = [r[0] for r in rows]
            gold = [r[1] if r[1] in self.labels else OTHER for r in rows]
            pages.append((lines, gold, rule_labels(lines, self.english, self.twi), _paren_depths(lines)))
        self.weights = {}
        if not pages:
            return
        totals: dict[tuple[str, str], float] = {}
        stamps: dict[tuple[str, str], int] = {}
        step = 0
        rng = random.Random(0)
        for _ in range(self.EPOCHS):
            rng.shuffle(pages)
            for lines, gold, rules, depths in pages:
                prev = "start"
                for i in range(len(lines)):
                    step += 1
                    feats = _features(lines, i, prev, rules[i], depths[i], self.english, self.twi)
                    guess = self._best(feats)
                    if guess != gold[i]:
                        for f in feats:
                            for lab, delta in ((gold[i], 1.0), (guess, -1.0)):
                                key = (f, lab)
                                w = self.weights.get(key, 0.0)
                                totals[key] = totals.get(key, 0.0) + (step - stamps.get(key, 0)) * w
                                stamps[key] = step
                                self.weights[key] = w + delta
                    prev = guess
        for key, w in self.weights.items():
            totals[key] = totals.get(key, 0.0) + (step - stamps.get(key, 0)) * w
        self.weights = {k: v / step for k, v in totals.items() if abs(v) > 1e-9}

    def teach(self, page_id: str, lines: list[str], labels: list[str]) -> None:
        """Remember the user's sorting of one page and learn from it."""
        self.pages[page_id] = [[l, lab] for l, lab in zip(lines, labels)]
        self._train()
        if self.store:
            self.store.parent.mkdir(parents=True, exist_ok=True)
            self.store.write_text(json.dumps({"layout": self.layout, "pages": self.pages},
                                             ensure_ascii=False), encoding="utf-8")

    def forget(self) -> None:
        """Drop everything learned and go back to the starting rules."""
        self.pages, self.weights = {}, {}
        if self.store and self.store.exists():
            self.store.unlink()


# --- From labelled lines to entries --------------------------------------------------

def _join(parts: list[str]) -> str:
    text = ""
    for part in parts:
        if not text:
            text = part
        elif text.endswith("-") and part[:1].isalpha():
            text += part               # dum- / dum-dum -> dum-dum-dum (hyphen kept as printed)
        else:
            text += " " + part
    return text


def _drop_outer_brackets(text: str) -> str:
    """'(A wise person ...).' -> 'A wise person ....'  (only the pair around the whole note)"""
    t = text.strip()
    if t.startswith("("):
        t = t[1:].lstrip()
    m = re.search(r"\)\s*([.,;:]?)\s*$", t)
    if m and t.count(")") > t.count("("):
        t = t[:m.start()].rstrip() + m.group(1)
    return t


def build_entries(lines: list[str], labels: list[str], layout: str = "proverbs") -> list[dict]:
    """Group labelled lines into entries.

    Each entry: {"number", "proverb", "translation", "explanation", "lines": [indexes],
    "continued": True if it carries on from the page before, "missing": [fields]}.
    """
    required = LAYOUTS[layout]["required"]
    entries: list[dict] = []
    current: dict | None = None
    prev = None
    for i, (line, lab) in enumerate(zip(lines, labels)):
        if lab == OTHER:
            continue
        starts_new = lab == PROVERB and (NUMBER.match(line) or prev != PROVERB)
        if current is None or starts_new or (lab == PROVERB and current["parts"][EXPLANATION]):
            current = {"number": "", "parts": {PROVERB: [], TRANSLATION: [], EXPLANATION: []},
                       "lines": [], "continued": current is None and lab != PROVERB}
            m = NUMBER.match(line) if lab == PROVERB else None
            if m:
                current["number"] = m.group(1).translate(OCR_DIGITS)
                line = line[m.end():]
            entries.append(current)
        current["parts"][lab].append(line)
        current["lines"].append(i)
        prev = lab
    out = []
    last_number = None
    for e in entries:
        parts = e.pop("parts")
        e["proverb"] = _join(parts[PROVERB])
        e["translation"] = _join(parts[TRANSLATION])
        e["explanation"] = _drop_outer_brackets(_join(parts[EXPLANATION]))
        e["missing"] = [] if e["continued"] else [f for f in required if not e[f]]
        e["out_of_order"] = False
        if e["number"].isdigit():
            n = int(e["number"])
            e["out_of_order"] = last_number is not None and n != last_number + 1
            last_number = n
        out.append(e)
    return out


def merge_pages(pages: list[list[dict]], layout: str = "proverbs") -> list[dict]:
    """Join entries across pages: an entry continued at the top of a page joins the one before."""
    required = LAYOUTS[layout]["required"]
    merged: list[dict] = []
    for entries in pages:
        for e in entries:
            if e.get("continued") and merged:
                last = merged[-1]
                for field in (PROVERB, TRANSLATION, EXPLANATION):
                    if e[field]:
                        last[field] = _join([last[field], e[field]]) if last[field] else e[field]
                last[EXPLANATION] = _drop_outer_brackets(last[EXPLANATION])
                last["missing"] = [f for f in required if not last[f]]
            else:
                merged.append(dict(e))
    return merged
