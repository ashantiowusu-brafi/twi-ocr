"""Read printed Twi from images or PDFs with the Twi Tesseract model.

This command: renders PDF pages, runs Tesseract with the Twi
model, and (optionally) fixes common misreadings line by line, as the desktop
app does (postcorrect.correct_page). On Twi lines it fixes the model's main
mistake, "i" read as "l", using a Twi word list; e/ɛ and o/ɔ are never
changed there, because they distinguish different words in Twi. On English
lines (the book's translations) it fixes clear English mistakes instead:
"it Is" -> "it is", "wil!" -> "will", "ɔver" -> "over" (issue T7).

Examples:
    python ocr.py page.png                      # print the text
    python ocr.py book.pdf --out text/          # one .txt file per page
    python ocr.py scans/ --out text/            # each image and PDF in a folder
    python ocr.py page.png --no-correct         # model output only
    python ocr.py christaller.pdf --orthography 1879 --out text/
                                                # 1879 spelling: writes page.txt
                                                # (as printed) and page.modern.txt

Requirements:
    - Tesseract 5 on your PATH (macOS: brew install tesseract)
    - The model file: models/twi.traineddata (from the GitHub release or
      Hugging Face), or pass --tessdata-dir and --model
    - pip install pillow pypdfium2        (pypdfium2 only for PDFs)
    - For --correct (on by default): the public word list built by
      `python download.py`, which writes data/twi_ghananlp.txt. Without it,
      ocr.py prints a note and skips correction. The English word list,
      wordlists/english_words.txt, is part of the project; without it only
      the Twi fixes are made.

1879 mode reads Christaller-era spelling (e̲ o̲ for ɛ ɔ, tildes, accents) with
the twi_1879 model, and fixes two patterns the model gets wrong (see
orthography.cleanup_ocr; --no-correct turns that off). It keeps the text as printed and also writes a
modern-spelling copy made by orthography.py. The i/l correction is skipped,
because the word list is in modern spelling.

License: MIT (code). The model is CC BY-NC-SA 4.0, non-commercial.
"""

import argparse
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from pathlib import Path

DEFAULT_MODEL = "twi"
DEFAULT_TESSDATA = Path(__file__).resolve().parent / "models"
WORD_LIST = Path(__file__).resolve().parent / "data" / "twi_ghananlp.txt"
IMAGE_TYPES = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}
PDF_DPI = 300   # Resolution PDF pages are rendered at; 300 suits OCR.


# --- Inputs ------------------------------------------------------------------

def collect_inputs(paths: list[Path]) -> list[Path]:
    """Expand folders into the images and PDFs they contain, in name order."""
    found: list[Path] = []
    for path in paths:
        if path.is_dir():
            found.extend(sorted(p for p in path.iterdir()
                                if p.suffix.lower() in IMAGE_TYPES | {".pdf"}))
        elif path.exists():
            found.append(path)
        else:
            sys.exit(f"Not found: {path}")
    return found


def pdf_pages(pdf: Path, folder: Path) -> list[Path]:
    """Render each PDF page to a PNG in ``folder`` and return their paths."""
    try:
        import pypdfium2 as pdfium
    except ImportError:
        sys.exit("Reading PDFs needs pypdfium2: pip install pypdfium2")
    pages = []
    document = pdfium.PdfDocument(str(pdf))
    for number, page in enumerate(document, start=1):
        out = folder / f"{pdf.stem}-{number:03d}.png"
        page.render(scale=PDF_DPI / 72).to_pil().save(out)
        pages.append(out)
    document.close()
    return pages


# --- OCR ---------------------------------------------------------------------

def check_setup(model: str, tessdata: Path) -> None:
    """Stop with a clear message if Tesseract or the model is missing."""
    if shutil.which("tesseract") is None:
        sys.exit("Tesseract not found. Install it (macOS: brew install tesseract).")
    if not (tessdata / f"{model}.traineddata").exists():
        sys.exit(f"Model not found: {tessdata / (model + '.traineddata')}\n"
                 f"Download {model}.traineddata from the GitHub release or Hugging Face "
                 "into models/, or use --tessdata-dir and --model.")


def run_tesseract(image: Path, model: str, tessdata: Path, psm: int) -> str:
    """Run Tesseract on one image and hand back the text it read, with the
    letters stored in one standard way. NFC is the standard rule for letters
    that can be stored in more than one form, such as ã as one character or as
    a plus a tilde."""
    result = subprocess.run(
        ["tesseract", str(image), "stdout", "-l", model,
         "--tessdata-dir", str(tessdata), "--psm", str(psm)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        sys.exit(f"Tesseract failed on {image}:\n{result.stderr.strip()}")
    return unicodedata.normalize("NFC", result.stdout)


# --- Post-correction ---------------------------------------------------------

def load_corrector():
    """Return a function that corrects a page, or None if no Twi word list is available."""
    if not WORD_LIST.exists():
        print(f"Note: {WORD_LIST.relative_to(WORD_LIST.parent.parent)} not found, so "
              "i/l correction is off. Run `python download.py` once to enable it.",
              file=sys.stderr)
        return None
    import postcorrect as pc
    pc.CONFUSIONS = pc.SWAP_SETS["i"]   # Only l/I/1 -> i; never e/ɛ or o/ɔ.
    vocab = pc.build_vocabulary([WORD_LIST])
    english = pc.load_english_words() or None   # Without it, every line gets the Twi fixes.
    return lambda text: pc.correct_page(text, vocab, english)[0]


# --- Main --------------------------------------------------------------------

def main() -> None:
    """Parse arguments, read every input, and print or save the text."""
    parser = argparse.ArgumentParser(
        description="Read printed Twi from images or PDFs.",
        epilog="Model: CC BY-NC-SA 4.0 (non-commercial). Code: MIT.")
    parser.add_argument("inputs", nargs="+", type=Path, help="Images, PDFs or folders")
    parser.add_argument("--out", type=Path, help="Folder for .txt files (default: print)")
    parser.add_argument("--model", help="Model name (default: twi, or twi_1879 with --orthography 1879)")
    parser.add_argument("--orthography", choices=["modern", "1879"], default="modern",
                        help="Spelling of the source: modern (default) or 1879 (Christaller era)")
    parser.add_argument("--tessdata-dir", type=Path, default=DEFAULT_TESSDATA,
                        help="Folder containing the .traineddata file (default: models/)")
    parser.add_argument("--psm", type=int, default=None,
                        help="Tesseract page segmentation mode (default 3: full page, or 6 "
                             "with --orthography 1879; 6: one block of text; 7: a single line)")
    parser.add_argument("--no-correct", dest="correct", action="store_false",
                        help="Skip the word fixes (i/l in Twi, clear English mistakes)")
    args = parser.parse_args()

    old_style = args.orthography == "1879"
    # One block keeps the 1879 proverb numbers on their lines; 3 suits other pages.
    args.psm = args.psm if args.psm is not None else (6 if old_style else 3)
    args.model = args.model or ("twi_1879" if old_style else DEFAULT_MODEL)
    check_setup(args.model, args.tessdata_dir)
    correct = load_corrector() if args.correct and not old_style else None
    if old_style:
        import orthography
    if args.out:
        args.out.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        pages: list[Path] = []
        for item in collect_inputs(args.inputs):
            pages.extend(pdf_pages(item, Path(tmp)) if item.suffix.lower() == ".pdf" else [item])
        if not pages:
            sys.exit("No images or PDFs found.")

        for page in pages:
            text = run_tesseract(page, args.model, args.tessdata_dir, args.psm)
            if correct:
                text = correct(text)
            if old_style and args.correct:
                text = orthography.cleanup_ocr(text)   # macron/tilde doubles, stray lines below
            modern = orthography.to_modern(text) if old_style else None
            if args.out:
                target = args.out / f"{page.stem}.txt"
                target.write_text(text, encoding="utf-8")
                print(f"{page.name} -> {target}", file=sys.stderr)
                if modern is not None:
                    target = args.out / f"{page.stem}.modern.txt"
                    target.write_text(modern, encoding="utf-8")
                    print(f"{page.name} -> {target}", file=sys.stderr)
            else:
                if len(pages) > 1:
                    print(f"===== {page.name} =====")
                print(text.rstrip())
                if modern is not None:
                    print("----- modern spelling -----")
                    print(modern.rstrip())


if __name__ == "__main__":
    main()
