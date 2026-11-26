---
license: cc-by-nc-sa-4.0
language:
  - tw
  - ak
tags:
  - ocr
  - tesseract
  - twi
  - akan
  - low-resource
  - ghana
pipeline_tag: image-to-text
---

# Model card: Twi Tesseract models (`twi` and `twi_1879`)

This repository holds two Tesseract 5 models for printed Twi, one for each spelling system:

| Model | For | Tested on |
| --- | --- | --- |
| `twi.traineddata` | Modern Twi spelling (ɛ, ɔ, no accents) | 319 proverbs of *Bu Me Bɛ: Proverbs of the Akans* (2007) |
| `twi_1879.traineddata` | The older Basel Mission spelling (e̲ o̲, tildes, accents, ṅ, w̌) | Four proofread pages of J. G. Christaller's *Twi Mmebusɛm* (1879) |

Each model works only on the spelling it was trained for: on *Bu Me Bɛ*, `twi_1879` reads only 37% of the ɛ and ɔ, against 97% for `twi`. Code and instructions: https://github.com/ashantiowusu-brafi/twi-ocr

## `twi`: modern spelling

### Summary

A Tesseract 5 LSTM recognition model for printed Twi (Asante and Akuapem), fine-tuned to read ɛ, ɔ, Ɛ and Ɔ, curly quotes and proverb-style lines, and English printed in italics beside the Twi. The current version is v5 (November 2026).

| Item | Detail |
| --- | --- |
| Author | Ashanti Owusu-Brafi |
| Base model | `Latin.traineddata` from tessdata_best (Apache-2.0), fine-tuned through versions v1–v4; v5 continues from v4 |
| Training tool | tesstrain, Tesseract 5.5.4 |
| Training data | v1–v4: 20,000 synthetic text-line images, about 45% GhanaNLP Twi, 40% Ghana Corpus (Bible) Twi, 15% English. v5: 20,000 more, about 35% GhanaNLP Twi, 30% Bible Twi and 35% English, with most English lines in italics, some in brackets as in the book's explanations, and lookalike letters (Greek ε, reversed ↄ) cleaned out |
| Fonts | Charis SIL, Noto Serif, Noto Sans (from v5) and system fonts containing ɛ and ɔ, upright and italic |
| License | CC BY-NC-SA 4.0 (non-commercial) |

### Use

With the project's helper script (handles PDFs and the i/l correction):

```
python ocr.py page.png
```

Or with Tesseract alone, after placing `twi.traineddata` in a folder such as `models/`:

```
tesseract page.png stdout -l twi --tessdata-dir models
```

For books in the older 1879 spelling, use `twi_1879` instead (see below).

### Results

Tested on 319 proverbs from the first 14 scanned pages of *Bu Me Bɛ: Proverbs of the Akans* (proverbs 1–320 of the book's 7,015), all proofread; every model scored on the same proverbs. Full table: [`eval/bu_me_be_results.md`](https://github.com/ashantiowusu-brafi/twi-ocr/blob/main/eval/bu_me_be_results.md).

| | Character error rate | ɛ/ɔ accuracy |
| --- | --- | --- |
| Stock Tesseract (English) | 14.6% | 0.0% |
| `twi` (v4) | 4.1% | 97.3% |
| `twi` (v5, current) | 4.0% | 97.4% |
| `twi` (v5) + public post-correction | 3.3% | 97.4% |

These scores are for the Twi proverb text. For the English, which the book prints in italics, v5 made about 20% fewer non-word errors than v4 on the same 14 pages, with fewer ɔ/ɛ inside English words and fewer stray marks such as "wil!" or ";:". These are estimates from error counts, not a full English score.

### Limitations

- **Tested on one book.** Results on other printing styles and handwriting are unknown. It will be scored on the whole of *Bu Me Bɛ* once all 7,015 proverbs are transcribed.
- **It can't read 19th-century spelling** (e̲ o̲, tildes, accents): use `twi_1879` for that.
- **Remaining errors:** mostly i read as l (fixed by the post-correction); details for v4 in [`eval/errors_twi_v4.md`](https://github.com/ashantiowusu-brafi/twi-ocr/blob/main/eval/errors_twi_v4.md). In italic English, v5 reads the lowercase *i* as a capital *I* more often than v4 ("it Is", about 18% of mid-sentence "is" on the test pages, against 13%).
- **Spelling is reproduced, not standardized.** The model reads the page as printed. It does not modernize spellings, and it should not be used to "correct" e/ɛ or o/ɔ, which distinguish different words in Twi.
- **Tone marks** were not tested: the test book prints none.

## `twi_1879`: 1879 spelling

### Summary

A Tesseract 5 LSTM model for books in the Basel Mission spelling, such as Christaller's *Twi Mmebusɛm* (1879): e̲ o̲ for ɛ ɔ, tildes, macrons, accents, ṅ and w̌. It was fine-tuned from `twi` v4 on modern Twi text converted to 1879 spelling (ɛ → e̲, ɔ → o̲), with tildes, accents, w̌ and dotted n added by rough rules of thumb and chance so the model learns how they look. License: CC BY-NC-SA 4.0 (non-commercial).

### Use

```
python ocr.py page.png --orthography 1879
```

This writes the text exactly as printed, and a copy converted to modern spelling.

### Results

On four proofread pages of the 1879 book (proverbs 1–96), with the clean-up step. Full results: [`eval/christaller_1879/results.md`](https://github.com/ashantiowusu-brafi/twi-ocr/blob/main/eval/christaller_1879/results.md).

| | Error rate, as printed | Error rate, modern spelling | 1879 marks read correctly |
| --- | --- | --- | --- |
| Stock Tesseract (English) | 13.5% | 10.1% | 3% |
| `twi` (modern model) | 11.8% | 9.3% | 18% |
| `twi_1879` + clean-up | 5.1% | 4.0% | 80% |

### Limitations

- **Tested on four pages of one book.** Pages 5–13 of the test set are drafts, and other Basel Mission books are untested.
- **Weakest marks:** ṅ (28 of 65) and w̌ (8 of 22) are often missed.
- **Training marks are placed by rough rules of thumb,** not where Christaller used them, because too little 1879 text is transcribed. Issues T2, T3 and T4 in [`ORTHOGRAPHY.md`](https://github.com/ashantiowusu-brafi/twi-ocr/blob/main/ORTHOGRAPHY.md) would fix this.
- **It is not meant for modern text:** on *Bu Me Bɛ* its error rate is 12.8%, close to stock Tesseract.
- **The modern-spelling copy drops tildes and accents,** so keep the as-printed copy when the marks matter.

## Training data and license

The training text comes from the GhanaNLP Parallel Corpora (CC BY-NC-SA 4.0) and the Ghana NLP Community's Ghana Corpus (CC BY-NC 4.0), whose text is derived from Bible translations owned by their publishers. Whether a trained model counts as an adaptation of its training data is legally unsettled, so the model is released under CC BY-NC-SA 4.0, for non-commercial use only, with credit to both sources. Commercial use would need permission from the data owners; GhanaNLP requires written permission and a separate paid license for any commercial use of its data or derivative works. The training images and text are not distributed.

No *Bu Me Bɛ* text was used in training.

## Credits

Hosted by the Si Hene Foundation. Transcription of the *Bu Me Bɛ* answer key: Nana Adwoa Agyekum.

Ghana NLP Community; GhanaNLP (Adu Gyamfi et al., 2026); the tesseract-ocr project (tessdata_best, tesstrain); the Ewe Tesseract OCR model (method); SIL International and Google (fonts). Full references: [`README.md`](https://github.com/ashantiowusu-brafi/twi-ocr/blob/main/README.md) and [`CITATION.cff`](https://github.com/ashantiowusu-brafi/twi-ocr/blob/main/CITATION.cff).
