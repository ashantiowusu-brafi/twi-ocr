"""Convert scanned PDF pages to PNG images for OCR.

Each page of a PDF in ``private/scans_pdf/`` is saved as a 300 dpi PNG in
``private/scans/``, named ``<pdf name>-001.png``, ``<pdf name>-002.png``, ...
Uses pypdfium2 (Apache-2.0 / BSD-3-Clause), the same library as ocr.py.

You can adapt this on your local setup by creating a /private folder

Usage:
    pip install pypdfium2
    python pdf_to_png.py              # converts all PDFs in private/scans_pdf/
    python pdf_to_png.py book.pdf     # converts one specific PDF
"""

import sys
from pathlib import Path

import pypdfium2 as pdfium

PDF_DIR = Path("private/scans_pdf")
PNG_DIR = Path("private/scans")
DPI = 300  # High enough for OCR to see the small ɛ and ɔ clearly.


def convert(pdf_path: Path) -> int:
    """Save each page of one PDF as a PNG and return the number of pages."""
    document = pdfium.PdfDocument(str(pdf_path))
    for number, page in enumerate(document, start=1):
        out = PNG_DIR / f"{pdf_path.stem}-{number:03d}.png"
        page.render(scale=DPI / 72).to_pil().save(out)
    count = len(document)
    document.close()
    return count


def main() -> None:
    """Convert the PDF given on the command line, or every PDF in PDF_DIR."""
    PNG_DIR.mkdir(parents=True, exist_ok=True)
    pdfs = [Path(p) for p in sys.argv[1:]] or sorted(PDF_DIR.glob("*.pdf"))
    if not pdfs:
        raise SystemExit(f"No PDFs found. Put them in {PDF_DIR}/ or pass a file name.")
    for pdf in pdfs:
        print(f"{pdf.name}: {convert(pdf)} pages -> {PNG_DIR}/")


if __name__ == "__main__":
    main()
