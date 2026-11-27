"""How well does the app sort Bu Me Bɛ pages into proverb / translation / explanation?

Uses the private OCR pages and answer key, so it runs only where private/ exists:

    python eval_structure.py
    python eval_structure.py --teach 20     # also test learning: teach 20 pages, test the rest

Part 1 sorts every page with the starting rules and checks each numbered entry
against the answer key (the Twi must match closely; the key's English is
reworded in places, so English only has to match loosely).

Part 2 makes line labels from the answer key, teaches the sorter some pages and
measures line accuracy on pages it has not seen, against the rules alone.
"""
from __future__ import annotations

import argparse
import difflib
import zipfile
from pathlib import Path

import structure as st

PRIVATE = Path("private")
PAGES_ZIP = PRIVATE / "bu_me_be_ocr_pages.zip"
KEY = PRIVATE / "Akan_Proverbs.xlsx"
ENGLISH = Path("wordlists/english_words.txt")
TWI = Path("data/twi_ghananlp.txt")


def load_words(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {w.lower().replace("’", "'") for w in st.WORD.findall(path.read_text(encoding="utf-8"))}


def load_key() -> dict[int, tuple[str, str, str]]:
    import openpyxl
    ws = openpyxl.load_workbook(KEY, read_only=True).worksheets[0]
    key = {}
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row and row[0] is not None and str(row[0]).strip().isdigit():
            key[int(str(row[0]).strip())] = tuple(str(c or "").strip() for c in row[1:4])
    return key


def load_pages() -> list[tuple[str, str]]:
    with zipfile.ZipFile(PAGES_ZIP) as z:
        names = sorted(n for n in z.namelist() if n.endswith(".txt"))
        return [(n, z.read(n).decode("utf-8")) for n in names]


def ratio(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a.lower(), b.lower(), autojunk=False).ratio()


def contained(line: str, field: str) -> float:
    """Share of the line found in the field."""
    if not line or not field:
        return 0.0
    m = difflib.SequenceMatcher(None, line.lower(), field.lower(), autojunk=False)
    return sum(b.size for b in m.get_matching_blocks()) / len(line)


def silver_labels(lines: list[str], key: dict) -> list[str]:
    """Line labels from the answer key: which field of a nearby entry holds the line."""
    labels, current = [], None
    for line in lines:
        m = st.NUMBER.match(line)
        if m and m.group(1).translate(st.OCR_DIGITS).isdigit():
            current = int(m.group(1).translate(st.OCR_DIGITS))
        best, best_lab = 0.0, st.OTHER
        if current is not None:
            for n in (current - 1, current, current + 1):
                if n not in key:
                    continue
                for lab, field in zip((st.PROVERB, st.TRANSLATION, st.EXPLANATION), key[n]):
                    text = st.NUMBER.sub("", line) if lab == st.PROVERB else line.strip("()., ")
                    s = contained(text, field)
                    if s > best:
                        best, best_lab = s, lab
        labels.append(best_lab if best >= 0.7 else st.OTHER)
    return labels


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--teach", type=int, default=0, help="pages to teach before testing (part 2)")
    ap.add_argument("--show", action="store_true", help="print mix-ups")
    args = ap.parse_args()
    english, twi = load_words(ENGLISH), load_words(TWI)
    key, pages = load_key(), load_pages()
    sorter = st.Sorter("proverbs", english, twi)

    # Part 1: entries against the answer key.
    per_page = []
    for _, text in pages:
        lines = st.page_lines(text)
        per_page.append(st.build_entries(lines, sorter.label(lines)))
    entries = st.merge_pages(per_page)
    numbered = {}
    for e in entries:
        if e["number"].isdigit() and int(e["number"]) in key:
            numbered.setdefault(int(e["number"]), e)
    good = {"proverb": 0, "translation": 0, "explanation": 0, "all": 0}
    for n, e in numbered.items():
        tw, en, ex = key[n]
        ok = [ratio(e["proverb"], tw) >= 0.8, ratio(e["translation"], en) >= 0.6, ratio(e["explanation"], ex) >= 0.6]
        for f, o in zip(("proverb", "translation", "explanation"), ok):
            good[f] += o
        good["all"] += all(ok)
    flagged = sum(bool(e["missing"]) for e in entries if not e["continued"])
    print(f"Answer key: {len(key)} proverbs. Entries found by number: {len(numbered)} "
          f"({len(numbered) / len(key):.1%}); entries in all: {len(entries)}")
    for f in ("proverb", "translation", "explanation", "all"):
        print(f"  {f:12s} matches the key: {good[f] / max(1, len(numbered)):.1%}")
    print(f"  flagged as missing a part: {flagged} ({flagged / max(1, len(entries)):.1%})")

    # Part 2: does teaching help?
    if args.teach:
        data = []
        for name, text in pages:
            lines = st.page_lines(text)
            if lines:
                data.append((name, lines, silver_labels(lines, key)))
        data = [d for d in data if sum(l != st.OTHER for l in d[2]) >= 5]
        # Teach from even pages, test on odd pages, so both span the whole book.
        pool, test = data[0::2], data[1::2]
        train = pool[::max(1, len(pool) // args.teach)][:args.teach]

        def accuracy(s: st.Sorter) -> float:
            right = total = 0
            for _, lines, gold in test:
                for p, g in zip(s.label(lines), gold):
                    right += p == g
                    total += 1
            return right / max(1, total)

        before = accuracy(sorter)
        taught = st.Sorter("proverbs", english, twi)
        for name, lines, gold in train:
            taught.pages[name] = [[l, g] for l, g in zip(lines, gold)]
        taught._train()
        print(f"\nLine labels on {len(test)} unseen pages (labels made from the answer key):")
        print(f"  starting rules only:        {before:.1%}")
        print(f"  after teaching {len(train):3d} pages:    {accuracy(taught):.1%}")
        if args.show:
            import collections
            conf = collections.Counter()
            for _, lines, gold in test:
                for line, p, g in zip(lines, sorter.label(lines), gold):
                    if p != g:
                        conf[(g, p)] += 1
                        if args.show and conf[(g, p)] <= 3:
                            print(f"    key={g:11s} rules={p:11s} | {line[:70]}")
            print("  most common mix-ups (key -> rules):", conf.most_common(8))


if __name__ == "__main__":
    main()
