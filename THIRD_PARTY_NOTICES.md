# Third-party software, models, data and fonts

This project's own code is MIT-licensed. It depends on, or was built with, the components below, each under its own license. None of their files are included in this repository unless stated.

## Software

| Component | Used for | License |
| --- | --- | --- |
| [Tesseract](https://github.com/tesseract-ocr/tesseract) | OCR engine and training tools | Apache-2.0 |
| [tesstrain](https://github.com/tesseract-ocr/tesstrain) | Training workflow | Apache-2.0 |
| [Ghana Corpus Builder](https://github.com/GhanaNLP/ghana-corpus-builder) | Downloading the Ghana Corpus | MIT |
| [pandas](https://pandas.pydata.org/) | Tables and spreadsheets | BSD-3-Clause |
| [NumPy](https://numpy.org/) | Image noise | BSD-3-Clause |
| [Pillow](https://python-pillow.org/) | Rendering line images | MIT-CMU (HPND) |
| [fontTools](https://github.com/fonttools/fonttools) | Checking fonts for ɛ and ɔ | MIT |
| [RapidFuzz](https://github.com/rapidfuzz/RapidFuzz) | Edit distance for scoring | MIT |
| [openpyxl](https://openpyxl.readthedocs.io/) | Reading and editing the answer key | MIT |
| [Hugging Face datasets](https://github.com/huggingface/datasets) and [huggingface_hub](https://github.com/huggingface/huggingface_hub) | Downloading GhanaNLP data | Apache-2.0 |
| [pypdfium2](https://github.com/pypdfium2-team/pypdfium2) and PDFium | Reading PDFs (`ocr.py`, `pdf_to_png.py`) | Apache-2.0 or BSD-3-Clause; PDFium BSD-style |

## Models

| Model | Used for | License |
| --- | --- | --- |
| [tessdata_best `Latin.traineddata`](https://github.com/tesseract-ocr/tessdata_best) | Base model for fine-tuning | Apache-2.0 |

The [Ewe Tesseract OCR](https://huggingface.co/NissiKlaus/ewe-tesseract-ocr) model's method was followed; none of its files are used.

## Data

| Dataset | Used for | License |
| --- | --- | --- |
| GhanaNLP Parallel Corpora | Training text; public word list | CC BY-NC-SA 4.0 plus GhanaNLP terms: commercial use only with written permission and a paid license; no military use; keep original metadata and attribution; do not remove cultural or dialectal references |
| Ghana Corpus (Bible translations) | Training text; private word list | CC BY-NC 4.0; underlying translations owned by their publishers |
| UGSpeechData | Private word list only | CC BY-NC-ND 4.0 |
| *Bu Me Bɛ: Proverbs of the Akans* | Evaluation only | In copyright; not redistributed |
| J. G. Christaller, *Twi Mmebusɛm* (Basel, 1879), via HathiTrust | 1879 test pages and demo image (`eval/christaller_1879/`, `sources/christaller_1879/`, `docs/demo/`) | Public domain |
| *Mmoa Akenkan* (*Counting animals*), Akuapem Twi, [African Storybook](https://global-asp.github.io/storybooks-ghana/stories/tw-akua/0327/): text by Zanele Buthelezi, Thembani Dladla and Clare Verbeek; illustrations by Rob Owen; translated by Michael Anguah-Mante (OLE Ghana) | Modern-spelling demo image (`docs/demo/mmoa_akenkan_p8*`, `docs/demo_modern.png`); cropped screenshot of page 8 | CC BY 3.0 |

## Fonts

| Font | Used for | License |
| --- | --- | --- |
| [Charis SIL](https://software.sil.org/charis/) | Rendering training images | SIL Open Font License 1.1 (Reserved Font Names "Charis", "SIL") |
| [Noto Serif](https://fonts.google.com/noto/specimen/Noto+Serif) | Rendering training images | SIL Open Font License 1.1 |

The fonts are not included; download them from the links above. If they are ever added to the repository, their OFL licence files must be included too.
