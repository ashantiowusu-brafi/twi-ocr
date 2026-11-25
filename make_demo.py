"""Build docs/demo.png: a scanned 1879 page beside two OCR readings of it.

The image shows a crop of Christaller's Twi Mmebusɛm (1879), scan 17 (printed page 1), with
stock Tesseract's reading (English model) and this project's Twi model's
reading underneath. Only the proverbs on the crop (7 to 10) are taken from
each OCR file: from the first line containing "7." to the line containing
"569".

Usage (after running the OCR, see docs/demo/SOURCE.md):
    tesseract docs/demo/christaller_1879_seq17.png stdout -l eng --psm 4 \\
        > docs/demo/christaller_1879_seq17_eng.txt
    python ocr.py docs/demo/christaller_1879_seq17.png --orthography 1879 \\
        > docs/demo/christaller_1879_seq17_twi.txt
    python make_demo.py --model-name "twi_1879"

Modern-spelling demo (docs/demo_modern.png), see docs/demo/SOURCE.md:
    python make_demo.py --crop docs/demo/mmoa_akenkan_p8.png \\
        --eng docs/demo/mmoa_akenkan_p8_eng.txt --twi docs/demo/mmoa_akenkan_p8_twi.txt \\
        --whole --model-name "twi v4" --title "..." --subtitle "..." --out docs/demo_modern.png

Requires: pip install pillow
"""

import argparse
import re
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

DEMO_DIR = Path("docs/demo")
WIDTH, MARGIN = 1680, 40
FONT_CANDIDATES = [   # Fonts that contain ɛ, ɔ, ŵ, ă, ũ. First one found is used.
    "fonts/NotoSans-Regular.ttf", "fonts/CharisSIL-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/Library/Fonts/Arial Unicode.ttf",
]
BOLD_CANDIDATES = [
    "fonts/NotoSans-Bold.ttf", "fonts/CharisSIL-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
]


def first_font(paths: list[str], size: int) -> ImageFont.FreeTypeFont:
    """Load the first font that exists, at ``size``."""
    for path in paths:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    raise SystemExit("No suitable font found. Put NotoSans-Regular.ttf and NotoSans-Bold.ttf in fonts/.")


def proverb_lines(path: Path, whole: bool = False) -> list[str]:
    """Return the OCR lines for proverbs 7-10 (from '7.' up to the 'Cf. 569' line),
    or every non-empty line with whole=True."""
    lines = [l.rstrip() for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    if whole:
        return lines
    start = next(i for i, l in enumerate(lines) if re.search(r"(^|\s)7[.,]\s", l))
    end = next(i for i, l in enumerate(lines) if i >= start and "569" in l)
    return lines[start:end + 1]


def panel(draw, top, title, color, lines, fonts) -> int:
    """Draw a grey box with a title and OCR lines; return the y below it."""
    title_font, body_font = fonts
    height = 30 + 34 + 32 * len(lines) + 20
    draw.rectangle([MARGIN, top, WIDTH - MARGIN, top + height], fill="#f9f9f9", outline="#dddddd")
    draw.text((MARGIN + 20, top + 15), title, font=title_font, fill=color)
    for i, line in enumerate(lines):
        draw.text((MARGIN + 20, top + 60 + 32 * i), line, font=body_font, fill="#111111")
    return top + height + 24


def main() -> None:
    parser = argparse.ArgumentParser(description="Build docs/demo.png.")
    parser.add_argument("--crop", type=Path, default=DEMO_DIR / "christaller_1879_seq17_crop.png")
    parser.add_argument("--eng", type=Path, default=DEMO_DIR / "christaller_1879_seq17_eng.txt")
    parser.add_argument("--twi", type=Path, default=DEMO_DIR / "christaller_1879_seq17_twi.txt")
    parser.add_argument("--model-name", default="twi", help="Shown in the Twi panel title")
    parser.add_argument("--caption", default=None, help="Text under the panels")
    parser.add_argument("--out", type=Path, default=DEMO_DIR.parent / "demo.png")
    parser.add_argument("--title", default="Twi OCR on an older orthography: Christaller, Twi Mmebusɛm (1879)",
                        help="Heading at the top of the image")
    parser.add_argument("--subtitle", default="Printed page (proverbs 7–10). Public domain; HathiTrust, Google-digitized.",
                        help="Source line under the heading")
    parser.add_argument("--whole", action="store_true",
                        help="Show every OCR line, not just proverbs 7-10 (for pages other than the 1879 demo)")
    args = parser.parse_args()

    title_font = first_font(BOLD_CANDIDATES, 32)
    head_font = first_font(BOLD_CANDIDATES, 26)
    body_font = first_font(FONT_CANDIDATES, 21)
    small_font = first_font(FONT_CANDIDATES, 19)

    crop = Image.open(args.crop).convert("RGB")
    crop_w = WIDTH - 2 * MARGIN - 2
    crop = crop.resize((crop_w, round(crop.height * crop_w / crop.width)))
    eng, twi = proverb_lines(args.eng, args.whole), proverb_lines(args.twi, args.whole)
    caption = textwrap.wrap(args.caption or "", width=150)

    height = 130 + crop.height + 2 * 24 + 2 * (84 + 32 * max(7, len(eng), len(twi))) + 30 * len(caption) + 60
    image = Image.new("RGB", (WIDTH, height), "white")
    draw = ImageDraw.Draw(image)
    draw.text((MARGIN, 40), args.title, font=title_font, fill="#111111")
    draw.text((MARGIN, 92), args.subtitle, font=small_font, fill="#555555")
    top = 126
    draw.rectangle([MARGIN, top, WIDTH - MARGIN, top + crop.height + 1], outline="#dddddd")
    image.paste(crop, (MARGIN + 1, top + 1))
    y = top + crop.height + 26
    y = panel(draw, y, "Stock Tesseract (English model)", "#777777", eng, (head_font, body_font))
    y = panel(draw, y, f"This project’s Twi model ({args.model_name})", "#1f5aa6", twi,
              (head_font, body_font))
    for i, line in enumerate(caption):
        draw.text((MARGIN, y + 30 * i), line, font=small_font, fill="#555555")
    image = image.crop((0, 0, WIDTH, y + 30 * len(caption) + 30))
    image.save(args.out)
    print(f"Saved {args.out}")


if __name__ == "__main__":
    main()
