"""Score Tesseract models on Christaller's 1879 spelling.

Every pair in eval/christaller_1879/ (an image plus its .gt.txt diplomatic
transcription) is read with each model, and three numbers are reported:

    diplomatic CER  errors against the key exactly as printed (marks included)
    modern CER      errors after both sides are converted to modern spelling
                    with orthography.to_modern, which shows how usable the
                    text is even when the 1879 marks are lost
    mark recall     for each kind of 1879 mark, the share of marks in the
                    key that the model reproduced in the right place

Each model also gets a "+ clean-up" row: the same output after
orthography.cleanup_ocr (macron/tilde doubles, stray lines below), which is
what ocr.py --orthography 1879 applies.

CER is counted on NFD code points, so a missing tilde or line below counts
as one error, the same as a wrong letter.

Usage:
    python score_1879.py                          # every model in models/ plus eng
    python score_1879.py --model twi_1879 twi_v4
    python score_1879.py --pages 1-4             # only the proofread pages
    python score_1879.py --psm 4

Writes eval/christaller_1879/results.md.
Requires: Tesseract 5, pip install rapidfuzz
"""

import argparse
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path

from rapidfuzz.distance import Levenshtein

import orthography

EVAL_DIR = Path("eval/christaller_1879")
MODELS_DIR = Path("models")
RESULTS = EVAL_DIR / "results.md"
MARKS = {
    "\u0332": "line below (e̲ o̲)",
    "\u0323": "dot below (ẹ ọ ạ)",
    "\u0303": "tilde (ã)",
    "\u0304": "macron (ā)",
    "\u0306": "breve (ă)",
    "\u0301": "acute (á)",
    "\u0300": "grave (à)",
    "\u0302": "circumflex (â)",
    "\u030c": "mark over w (w̌)",
    "\u0307": "dot above (ṅ)",
}


def tidy(text: str) -> str:
    """NFD, single spaces, no blank lines: the form both sides are compared in."""
    lines = (" ".join(line.split()) for line in unicodedata.normalize("NFD", text).splitlines())
    return "\n".join(line for line in lines if line)


def read_image(image: Path, model: str, psm: int) -> str | None:
    """Run Tesseract; uses models/ when the model is there, else the system tessdata."""
    command = ["tesseract", str(image), "stdout", "-l", model, "--psm", str(psm)]
    if (MODELS_DIR / f"{model}.traineddata").exists():
        command += ["--tessdata-dir", str(MODELS_DIR)]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Skipping {model}: Tesseract could not load it.", file=sys.stderr)
        return None
    return result.stdout


def mark_hits(key: str, ocr: str) -> dict[str, list[int]]:
    """Count, per mark type, [marks in key, marks the OCR matched in place]."""
    matched = set()
    for tag, k0, k1, _, _ in Levenshtein.opcodes(key, ocr):
        if tag == "equal":
            matched.update(range(k0, k1))
    counts = {mark: [0, 0] for mark in MARKS}
    for i, ch in enumerate(key):
        if ch in MARKS:
            counts[ch][0] += 1
            counts[ch][1] += i in matched
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Score models on 1879 Twi spelling.")
    parser.add_argument("--model", nargs="+", help="Model names (default: models/*.traineddata and eng)")
    parser.add_argument("--pages", help="Only these printed pages, e.g. 1-4 (the proofread ones) or 1,3,5")
    parser.add_argument("--psm", type=int, default=6, help="Page segmentation mode (default 6: one block; 4 splits off the proverb numbers)")
    args = parser.parse_args()

    if shutil.which("tesseract") is None:
        sys.exit("Tesseract not found.")
    # twi_1879_v1 is the same file as the released twi_1879, so it is left out.
    models = args.model or ["eng"] + sorted(p.stem for p in MODELS_DIR.glob("*.traineddata")
                                            if p.stem != "twi_1879_v1")
    pairs = [(p, p.with_suffix("").with_suffix(".gt.txt")) for p in sorted(EVAL_DIR.glob("*.png"))]
    pairs = [(img, gt) for img, gt in pairs if gt.exists()]
    if args.pages:
        wanted = set()
        for part in args.pages.split(","):
            lo, _, hi = part.partition("-")
            wanted.update(range(int(lo), int(hi or lo) + 1))
        pairs = [(img, gt) for img, gt in pairs
                 if img.stem[:1] == "p" and img.stem[1:3].isdigit() and int(img.stem[1:3]) in wanted]
    if not pairs:
        sys.exit(f"No image + .gt.txt pairs in {EVAL_DIR}/")

    rows, mark_rows = [], []
    for model in models:
        outputs = []
        for image, gt in pairs:
            raw = read_image(image, model, args.psm)
            if raw is None:
                break
            (EVAL_DIR / "ocr").mkdir(exist_ok=True)
            (EVAL_DIR / "ocr" / f"{image.stem}.{model}.txt").write_text(
                unicodedata.normalize("NFC", raw), encoding="utf-8")
            outputs.append((gt, raw))
        if len(outputs) < len(pairs):      # Model failed to load.
            continue
        for label, fix in ((model, None), (f"{model} + clean-up", orthography.cleanup_ocr)):
            dip_err = dip_len = mod_err = mod_len = 0
            totals = {mark: [0, 0] for mark in MARKS}
            for gt, raw in outputs:
                key = tidy(gt.read_text(encoding="utf-8"))
                ocr = tidy(fix(raw) if fix else raw)
                dip_err += Levenshtein.distance(key, ocr)
                dip_len += len(key)
                key_m, ocr_m = (tidy(orthography.to_modern(t)) for t in (key, ocr))
                mod_err += Levenshtein.distance(key_m, ocr_m)
                mod_len += len(key_m)
                for mark, (n, hit) in mark_hits(key, ocr).items():
                    totals[mark][0] += n
                    totals[mark][1] += hit
            n_all = sum(n for n, _ in totals.values())
            hit_all = sum(h for _, h in totals.values())
            rows.append(f"| {label} | {100 * dip_err / dip_len:.1f}% | {100 * mod_err / mod_len:.1f}% "
                        f"| {hit_all}/{n_all} |")
            mark_rows.append(f"| {label} | " + " | ".join(
                f"{h}/{n}" for n, h in totals.values()) + " |")

    lines = [
        "# 1879 spelling: results",
        "",
        f"Test set: {len(pairs)} image(s) in `{EVAL_DIR}/`, Tesseract `--psm {args.psm}`. "
        "Produced by `score_1879.py`; OCR output is saved in `ocr/`.",
        "",
        "| Model | Diplomatic CER | Modern CER | 1879 marks kept |",
        "|---|---|---|---|",
        *rows,
        "",
        "## Marks, by type",
        "",
        "| Model | " + " | ".join(MARKS.values()) + " |",
        "|---|" + "---|" * len(MARKS),
        *mark_rows,
        "",
    ]
    RESULTS.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"Saved {RESULTS}")


if __name__ == "__main__":
    main()
