"""Render Twi text lines as images to train Tesseract (synthetic ground truth).

Each output pair is one text-line image and its typed text, in the layout the
tesstrain toolkit expects:

    private/ground-truth/twi_000001.png
    private/ground-truth/twi_000001.gt.txt

Mix of lines (defaults, adjustable with options):
    ~45% GhanaNLP Twi sentences   data/twi_ghananlp.txt
    ~40% Bible Twi verses         private/twi_bible.txt
    ~15% English sentences        data/TWI_ENGLISH_PARALLEL_TEXT.csv
Quote marks are converted to the book's style: “curly double” and n’anim.
English is included because Bu Me Bɛ prints English beside the Twi, and the
model must not forget it.

Images are varied to look like real scans: several fonts, sizes, slight tilt,
blur, noise and ink darkness. Output goes to private/ because the Bible text
may not be republished.

Fonts: every font must contain ɛ, ɔ, Ɛ and Ɔ; fonts that lack them are
skipped. The following were added-- .ttf/.otf files (for example Noto Serif,
Charis SIL, Gentium Plus, all free) --to a fonts/ folder in the project.

Usage:
    pip install pillow fonttools numpy pandas
    python render_lines.py                 # 6,000 lines
    python render_lines.py --count 20000   # more lines
    python render_lines.py --orthography 1879 --count 20000

1879 mode (for Christaller-era books such as Twi Mmebusɛm): Twi lines are
converted with orthography.py (ɛ -> e̲, ɔ -> o̲) and given tildes, accents,
w̌ and dotted n by rough rules of thumb, each applied by chance at rates judged
from pages 1 and 4 (MARK_SHARES in orthography.py), so the model learns to see
those marks. They are not yet where Christaller put them (issue T4 in
ORTHOGRAPHY.md). English lines stay as they are. Output goes to
private/ground-truth-1879/ so it never mixes with the modern training set. The line under e/o and the mark over w are
drawn by this script, not by the font, because few fonts place combining
marks well; the other marks use ready-made letters such as ã and ṅ.
"""

import argparse
import random
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd
from fontTools.ttLib import TTCollection, TTFont
from PIL import Image, ImageDraw, ImageFilter, ImageFont

# --- Configuration -----------------------------------------------------------

GHANANLP_TXT = Path("data/twi_ghananlp.txt")
BIBLE_TXT = Path("private/twi_bible.txt")
ENGLISH_CSV = Path("data/TWI_ENGLISH_PARALLEL_TEXT.csv")
OUT_DIR = Path("private/ground-truth")

# Project fonts first, then common macOS and Linux locations.
FONT_DIRS = [
    Path("fonts"),
    Path("/System/Library/Fonts/Supplemental"),
    Path("/System/Library/Fonts"),
    Path("/Library/Fonts"),
    Path.home() / "Library/Fonts",
    Path("/usr/share/fonts"),
]
FONT_TYPES = {".ttf", ".otf", ".ttc"}
REQUIRED_CHARS = "ɛɔƐƆ"

# Book text is regular-weight print, so extreme weights, novelty and symbol
# fonts are left out. Fonts in the project's fonts/ folder are always used.
EXCLUDED_FONT_WORDS = (
    "black", "heavy", "extrabold", "ultra", "thin", "hairline", "extralight",
    "condensed", "narrow", "mono", "code", "symbol", "emoji", "dingbat",
    "math", "braille", "lastresort", "keyboard",
)

MAX_LINE_CHARS = 60      # Roughly one printed line in the book.
MIN_LINE_CHARS = 8
QUOTE_SHARE = 0.10       # Share of lines wrapped in “curly double quotes”, as in the book.

# Proverbs almost always start with a capital, very often Ɔ or Ɛ, but most
# training lines are cut from mid-sentence and start lowercase. Error analysis
# of the first model showed capital Ɔ was its most common mistake, so some
# lines are rewritten to start with a capital, preferably Ɔ or Ɛ.
CAPITAL_START_SHARE = 0.35   # Share of lines whose first letter is capitalized.
OPEN_VOWEL_START_SHARE = 0.20  # Share of lines moved to start at an ɔ/ɛ word.

# In the book every proverb line begins with its number, then the first word
# (for example "14 Ɔba ..."). Model v2 dropped a capital Ɔ that sits right
# after a number in 127 proverbs, because no training line looked like that.
# Some lines therefore get a proverb-style number in front, most often the
# lines that start with Ɔ or Ɛ.
NUMBER_PREFIX_SHARE = 0.20        # Share of ordinary lines given a number.
NUMBER_PREFIX_OPEN_VOWEL = 0.70   # Share of Ɔ/Ɛ-initial lines given a number.
HIGHEST_PROVERB_NUMBER = 7015


# --- Text --------------------------------------------------------------------

def read_lines(path: Path) -> list[str]:
    """Read non-empty, NFC-normalized lines from a text file (empty if missing)."""
    if not path.exists():
        print(f"Skipping {path} (not found)")
        return []
    text = unicodedata.normalize("NFC", path.read_text(encoding="utf-8"))
    return [line.strip() for line in text.splitlines() if line.strip()]


def read_english(path: Path) -> list[str]:
    """Read the English side of the GhanaNLP Twi-to-English dataset."""
    if not path.exists():
        print(f"Skipping {path} (not found)")
        return []
    return [unicodedata.normalize("NFC", str(s)).strip()
            for s in pd.read_csv(path)["label"].dropna()]


def split_into_lines(sentence: str) -> list[str]:
    """Break a sentence into printed-line-sized pieces at word boundaries.

    Tesseract learns from single text lines, so long sentences and verses are
    cut into chunks of at most ``MAX_LINE_CHARS`` characters.
    """
    pieces, current = [], ""
    for word in sentence.split():
        if current and len(current) + 1 + len(word) > MAX_LINE_CHARS:
            pieces.append(current)
            current = word
        else:
            current = f"{current} {word}".strip()
    if current:
        pieces.append(current)
    return [p for p in pieces if len(p) >= MIN_LINE_CHARS]


def sample_lines(sentences: list[str], count: int, rng: random.Random) -> list[str]:
    """Pick ``count`` printed lines from randomly chosen sentences."""
    lines: list[str] = []
    pool = sentences[:]
    rng.shuffle(pool)
    for sentence in pool:
        lines.extend(split_into_lines(sentence))
        if len(lines) >= count:
            break
    return lines[:count]


def capitalize_start(line: str, rng: random.Random) -> str:
    """Make some lines start with a capital, favoring Ɔ and Ɛ.

    With probability ``OPEN_VOWEL_START_SHARE`` the line is cut to begin at a
    word starting with ɔ or ɛ (if it has one), so capital Ɔ and Ɛ appear far
    more often. Then, with probability ``CAPITAL_START_SHARE``, the first
    letter is capitalized; Python's ``upper`` maps ɔ to Ɔ and ɛ to Ɛ.
    """
    words = line.split()
    if rng.random() < OPEN_VOWEL_START_SHARE:
        starts = [i for i, w in enumerate(words) if w[:1] in "ɔɛ"]
        if starts:
            words = words[rng.choice(starts):]
            line = " ".join(words)
            return line[:1].upper() + line[1:]
    if rng.random() < CAPITAL_START_SHARE and line:
        return line[:1].upper() + line[1:]
    return line


def add_proverb_number(line: str, rng: random.Random, style: str = "modern") -> str:
    """Put a proverb number before some lines, as the book prints them.

    Lines that start with Ɔ or Ɛ get a number much more often, because that
    combination is where model v2 failed. The number stays in the line's
    ground-truth text, since it is printed on the page. Bu Me Bɛ prints
    "14 Ɔba"; Christaller's 1879 book prints "7. Oba" (with a full stop) and
    has 3,600 proverbs.
    """
    share = NUMBER_PREFIX_OPEN_VOWEL if line[:1] in "ƆƐ" else NUMBER_PREFIX_SHARE
    if rng.random() < share:
        if style == "1879":
            return f"{rng.randint(1, 3600)}. {line}"
        return f"{rng.randint(1, HIGHEST_PROVERB_NUMBER)} {line}"
    return line


def to_book_quotes(line: str) -> str:
    """Convert quote marks to the book's style: “curly double” and n’anim.

    The GhanaNLP and Bible text mostly uses straight " and ', but Bu Me Bɛ
    prints curly double quotes for quotations and a curly apostrophe inside
    words. Model v3 read the book's curly marks as straight ones, because
    that is what it had been trained on. Same rules as tools/answer_key/fix_key_quotes.py.
    """
    chars = list(line)
    quote_open = False
    for i, ch in enumerate(chars):
        if ch not in "'’‘\"“”":
            continue
        before = chars[i - 1] if i > 0 else " "
        after = chars[i + 1] if i + 1 < len(chars) else " "
        if ch in "'’" and before.isalpha() and after.isalpha():
            chars[i] = "’"                       # Apostrophe inside a word.
        elif ch in "‘“" or (ch in "'\"" and before in " ([{—–-"):
            chars[i] = "“"
            quote_open = True
        elif ch == "\"" or quote_open:
            chars[i] = "”"
            quote_open = False
        else:
            chars[i] = "’"                       # Stray mark: treat as apostrophe.
    return "".join(chars)


def add_book_quotes(line: str, rng: random.Random) -> str:
    """Sometimes wrap a line in the book's curly double quotes (“ ”)."""
    return f"“{line}”" if rng.random() < QUOTE_SHARE else line


# --- Fonts -------------------------------------------------------------------

def font_has_chars(path: Path, chars: str) -> bool:
    """Return True if the font (first face, for .ttc) contains every character."""
    try:
        font = TTCollection(path).fonts[0] if path.suffix.lower() == ".ttc" else TTFont(path)
        cmap = font.getBestCmap() or {}
        return all(ord(c) in cmap for c in chars)
    except Exception:
        return False


def find_fonts() -> list[Path]:
    """Find installed fonts that can draw ɛ, ɔ, Ɛ and Ɔ."""
    found = []
    for folder in FONT_DIRS:
        if folder.exists():
            for path in folder.rglob("*"):
                if path.suffix.lower() not in FONT_TYPES:
                    continue
                name = path.stem.lower().replace("-", "").replace(" ", "")
                if folder != Path("fonts") and any(w in name for w in EXCLUDED_FONT_WORDS):
                    continue
                if font_has_chars(path, REQUIRED_CHARS):
                    found.append(path)
    return sorted(set(found))


# --- Images ------------------------------------------------------------------

def render(text: str, font_path: Path, rng: random.Random) -> Image.Image:
    """Draw one line of text and degrade it slightly to resemble a scan."""
    font = ImageFont.truetype(str(font_path), rng.randint(28, 44))
    left, top, right, bottom = font.getbbox(text)
    pad_x, pad_y = rng.randint(10, 30), rng.randint(8, 20)
    width, height = right - left + 2 * pad_x, bottom - top + 2 * pad_y

    paper = rng.randint(225, 255)    # Off-white page.
    ink = rng.randint(0, 60)         # Dark grey to black ink.
    image = Image.new("L", (width, height), paper)
    ImageDraw.Draw(image).text((pad_x - left, pad_y - top), text, font=font, fill=ink)

    return degrade(image, paper, rng)


def degrade(image: Image.Image, paper: int, rng: random.Random) -> Image.Image:
    """Tilt, blur and add grain so a clean rendering looks like a scan."""
    if rng.random() < 0.5:           # Slightly tilted scan.
        image = image.rotate(rng.uniform(-1.0, 1.0), expand=True, fillcolor=paper)
    if rng.random() < 0.6:           # Soft focus.
        image = image.filter(ImageFilter.GaussianBlur(rng.uniform(0.2, 1.0)))
    if rng.random() < 0.6:           # Paper grain.
        pixels = np.asarray(image, dtype=np.int16)
        noise = np.random.default_rng(rng.randint(0, 2**31)).normal(0, rng.uniform(3, 12), pixels.shape)
        image = Image.fromarray(np.clip(pixels + noise, 0, 255).astype(np.uint8))
    return image


# --- 1879 rendering ----------------------------------------------------------

LINE_BELOW = "\u0332"   # Combining low line: Christaller's mark for open e/o.
W_MARK = "\u030c"       # Combining caron over w (ntw̌a); no precomposed w̌ exists.
_CMAPS: dict[Path, set[int]] = {}


def font_cmap(path: Path) -> set[int]:
    """Return (and cache) the set of code points a font can draw."""
    if path not in _CMAPS:
        try:
            font = TTCollection(path).fonts[0] if path.suffix.lower() == ".ttc" else TTFont(path)
            _CMAPS[path] = set((font.getBestCmap() or {}).keys())
        except Exception:
            _CMAPS[path] = set()
    return _CMAPS[path]


def split_marked(text: str) -> tuple[list[str], list[bool], list[bool]]:
    """Split text into drawable letters plus flags for the hand-drawn marks.

    Returns (letters, underlined, w_marked). Each letter is NFC (so ã, ṅ, á
    come out as single ready-made characters); the line below and the mark
    over w are removed from the letter and recorded in the flags instead.
    """
    letters, under, wmark = [], [], []
    for ch in unicodedata.normalize("NFD", text):
        if unicodedata.combining(ch) and letters:
            if ch == LINE_BELOW:
                under[-1] = True
            elif ch == W_MARK:
                wmark[-1] = True
            else:
                letters[-1] += ch
            continue
        letters.append(ch)
        under.append(False)
        wmark.append(False)
    return [unicodedata.normalize("NFC", l) for l in letters], under, wmark


def ink_box(font: ImageFont.FreeTypeFont, text: str) -> tuple[int, int, int, int]:
    """Return the true ink box of ``text`` relative to the drawing origin.

    Pillow's getbbox stretches the box down to the baseline, which is wrong
    for a mark that floats above the letters, so the text is drawn and the
    ink is measured instead.
    """
    size = int(font.size * 3)
    canvas = Image.new("L", (size, size), 0)
    ImageDraw.Draw(canvas).text((font.size, font.size), text, font=font, fill=255)
    left, top, right, bottom = canvas.getbbox() or (0, 0, 0, 0)
    return left - font.size, top - font.size, right - font.size, bottom - font.size


def render_1879(text: str, fonts: list[Path], rng: random.Random) -> Image.Image | None:
    """Draw a line in 1879 spelling, adding the line below and w mark by hand.

    Picks a font that has every letter in the line (tildes, accents and
    dotted n need ready-made glyphs); returns None if no font fits.
    """
    letters, under, wmark = split_marked(text)
    drawable = "".join(letters)
    needed = {ord(c) for c in drawable if not c.isspace()} | {ord("ˇ")}
    usable = [f for f in fonts if needed <= font_cmap(f)]
    if not usable:
        return None
    size = rng.randint(28, 44)
    font = ImageFont.truetype(str(rng.choice(usable)), size)

    left, top, right, bottom = font.getbbox(drawable)
    pad_x, pad_y = rng.randint(10, 30), rng.randint(8, 20)
    extra_top, extra_bottom = int(size * 0.35), int(size * 0.25)   # Room for the marks.
    width = right - left + 2 * pad_x
    height = bottom - top + 2 * pad_y + extra_top + extra_bottom
    paper, ink = rng.randint(225, 255), rng.randint(0, 60)
    image = Image.new("L", (width, height), paper)
    draw = ImageDraw.Draw(image)
    ox, oy = pad_x - left, pad_y - top + extra_top
    draw.text((ox, oy), drawable, font=font, fill=ink)

    ascent = font.getmetrics()[0]
    thickness = max(1, round(size * 0.055))
    caron_box = ink_box(font, "ˇ")
    for i, letter in enumerate(letters):
        if not (under[i] or wmark[i]):
            continue
        x0 = ox + font.getlength("".join(letters[:i]))
        w = font.getlength(letter)
        if under[i]:     # A short bar under the letter, as in the book.
            y = oy + ascent + round(size * rng.uniform(0.08, 0.14))
            draw.rectangle([x0 + w * 0.12, y, x0 + w * 0.88, y + thickness - 1], fill=ink)
        if wmark[i]:     # Caron centred above the w, just over its top.
            letter_top = ink_box(font, letter)[1]
            cx = x0 + w / 2 - (caron_box[0] + caron_box[2]) / 2
            cy = oy + letter_top - round(size * 0.05) - caron_box[3]
            draw.text((cx, cy), "ˇ", font=font, fill=ink)
    return degrade(image, paper, rng)


# --- Main --------------------------------------------------------------------

def main() -> None:
    """Build the mixed line list and write image and text pairs."""
    parser = argparse.ArgumentParser(description="Render Twi training lines.")
    parser.add_argument("--count", type=int, default=6000, help="Total lines (default 6000)")
    parser.add_argument("--bible-share", type=float, default=0.40)
    parser.add_argument("--english-share", type=float, default=0.15)
    parser.add_argument("--seed", type=int, default=42, help="Same seed gives the same output")
    parser.add_argument("--orthography", choices=["modern", "1879"], default="modern",
                        help="modern (default) or 1879: Christaller spelling, "
                             "written to private/ground-truth-1879/")
    args = parser.parse_args()
    old_style = args.orthography == "1879"
    out_dir = Path("private/ground-truth-1879") if old_style else OUT_DIR
    prefix = "twi1879" if old_style else "twi"
    if old_style:
        import orthography

    rng = random.Random(args.seed)
    fonts = find_fonts()
    if not fonts:
        raise SystemExit("No fonts with ɛ/ɔ found. Add .ttf files to a fonts/ folder.")
    print(f"Using {len(fonts)} fonts:", ", ".join(f.stem for f in fonts[:10]),
          "..." if len(fonts) > 10 else "")

    n_bible = int(args.count * args.bible_share)
    n_english = int(args.count * args.english_share)
    n_ghananlp = args.count - n_bible - n_english

    # Each line is tagged True for Twi, False for English (English is never
    # converted to 1879 spelling).
    lines = (
        [(l, True) for l in sample_lines(read_lines(GHANANLP_TXT), n_ghananlp, rng)]
        + [(l, True) for l in sample_lines(read_lines(BIBLE_TXT), n_bible, rng)]
        + [(l, False) for l in sample_lines(read_english(ENGLISH_CSV), n_english, rng)]
    )
    rng.shuffle(lines)

    out_dir.mkdir(parents=True, exist_ok=True)
    written = skipped = 0
    for line, is_twi in lines:
        text = capitalize_start(to_book_quotes(line), rng)
        text = add_proverb_number(add_book_quotes(text, rng), rng, args.orthography)
        if old_style:
            if is_twi:
                text = orthography.add_period_marks(orthography.to_christaller(text), rng)
            image = render_1879(text, fonts, rng)
            if image is None:          # No font has every mark in this line.
                skipped += 1
                continue
        else:
            image = render(text, rng.choice(fonts), rng)
        written += 1
        stem = out_dir / f"{prefix}_{written:06d}"
        image.save(stem.with_suffix(".png"))
        stem.with_suffix(".gt.txt").write_text(text + "\n", encoding="utf-8")
        if written % 1000 == 0:
            print(f"{written:,} lines rendered")

    if skipped:
        print(f"Skipped {skipped:,} lines that no font could draw. Add fonts such as "
              "Charis SIL or Gentium Plus to fonts/ to keep more.")
    print(f"Done: {written:,} image/text pairs in {out_dir}/")


if __name__ == "__main__":
    main()
