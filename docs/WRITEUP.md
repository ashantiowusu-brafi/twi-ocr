# Twi OCR: what we found

This project trains Tesseract to read printed Twi. It was tested on two books: a modern proverb collection, *Bu Me Bɛ: Proverbs of the Akans*, and J. G. Christaller's *Twi Mmebusɛm* (Basel, 1879), which uses the older Basel Mission spelling. On both, the Twi models cut the character error rate by roughly two thirds compared with stock Tesseract.

## 1. *Bu Me Bɛ* (modern spelling)

*Bu Me Bɛ* is still in copyright, so the scans, the transcriptions and the OCR output are private. This repository publishes only scores and counts. None of the book's text should appear here.

### *Bu Me Bɛ* Scores

Scored on 319 proverbs from the first 14 scanned pages (proverbs 1–320 of the book's 7,015), transcribed with help from Nana Adwoa Agyekum and all proofread. The scoring script is `compare_models.py`; the full table is in [`eval/bu_me_be_results.md`](../eval/bu_me_be_results.md).

| Model | Character error rate | ɛ/ɔ read correctly |
| --- | --- | --- |
| Stock Tesseract (English) | 14.6% | 0.0% |
| `twi` v1: 6,000 rendered lines | 6.0% | 79.9% |
| `twi` v3: lookalike characters fixed | 4.2% | 97.0% |
| `twi` v4: training text in the book's quote style | 4.1% | 97.3% |
| `twi` v4 + public post-correction | 3.4% | 97.3% |

### Reading the whole book

The `twi` v4 model read all 335 pages of the original text, in two columns per page:

- 6,917 of the book's 7,015 numbered proverbs were found and matched to their number. The 98 it missed are on faded or curved pages.
- The model reads the Twi and the English on the same page. The English translations and explanations came out clean.
- About 1 proverb in 4 is flagged for a human check: a likely misread Twi word, an explanation the script had to separate by guesswork, or text unreadable on a faded page.

### The errors it still makes

- **i read as l.** The most common error. Twi has no letter l, so every l in a Twi word is changed to i after OCR.
- **e/ɛ and o/ɔ confused.** Mostly at the start of a word, for example the future prefix bɛ- read as be-. So, the word list can only suggest a fix, because both spellings are usually real words.
- **Quotation marks and brackets.** The book's curly quotes and square brackets are misread on lighter pages.
- **Faded and curved pages.** Whole lines are lost or garbled near the spine.

## 2. *Twi Mmebusɛm* (1879 spelling)

Christaller's book is in the public domain, so the test pages, transcriptions and OCR output are all published in [`eval/christaller_1879/`](../eval/christaller_1879/).

The Basel Mission spelling writes ɛ and ɔ as e̲ and o̲ (an underline), and adds marks modern Twi doesn't use: a tilde for a nasal vowel (ã), a macron for a long vowel (ā), accents for tone (á, à), ṅ for the ng sound and w̌. A separate model, `twi_1879`, was trained to keep these marks. More work needs to be done on the full book and orthographic logic relevant to earlier texts.

### *Twi Mmebusɛm* Scores

On four proofread pages (printed pages 1–4, proverbs 1–96):

| Model | Error rate, as printed | Error rate, converted to modern spelling | 1879 marks read correctly |
| --- | --- | --- | --- |
| Stock Tesseract (English) | 13.5% | 10.1% | 3% |
| `twi` v4 (modern model) | 11.8% | 9.3% | 18% |
| `twi_1879` + clean-up | 5.1% | 4.0% | 80% |

An early question was whether Tesseract would keep the underline (U+0332) at all; it does. By mark, `twi_1879` reads 242 of 276 underlines, 63 of 76 tildes, 40 of 42 macrons and 35 of 36 acute accents. The weak marks are ṅ (28 of 65) and w̌ (8 of 22). A second training run (v2) read more ṅ and w̌ but lost a quarter of the underlines, so overall it scored worse (5.9%) and was not released. Details: [`eval/christaller_1879/results.md`](../eval/christaller_1879/results.md).

### *Twi Mmebusɛm* Demo

Proverb 1 (printed page 1):

| | Text |
| --- | --- |
| As printed | E̲ba a, e̲kã onī. |
| Stock Tesseract | Eba a, eka oni. |
| `twi_1879` | E̲ba a, e̲kāã onī. |
| Converted to modern spelling | Ɛba a, ɛka oni. |

Stock Tesseract drops every mark. `twi_1879` keeps the underline and the macron, but here it adds a macron to the ã. The clean-up step removes doubled marks like this one.

## 3. The two models on each other's books

Both Twi models were scored on both books.

| Model | *Bu Me Bɛ* (modern): error rate | *Bu Me Bɛ*: ɛ/ɔ read correctly | 1879 book: error rate, as printed | 1879 book: marks kept |
| --- | --- | --- | --- | --- |
| Stock Tesseract (English) | 14.6% | 0% | 13.5% | 3% |
| `twi` (v4, modern model) | 4.1% | 97% | 11.8% | 18% |
| `twi_1879` (1879 model) | 12.8% | 37% | 6.1% (5.1% with clean-up) | 80% |

That is what you would expect. The 1879 model was trained to write ɛ and ɔ as e̲ and o̲, so on modern text it scores close to stock Tesseract: it reads only 37% of the ɛ and ɔ in *Bu Me Bɛ*, against 97% for the modern model. The modern model, in turn, keeps only 18% of the 1879 marks, against 80% for the 1879 model. It is a useful result, because it shows each model only works on the spelling it was trained for.

Scores on *Bu Me Bɛ* are for the 319 test proverbs; scores on the 1879 book are for the four proofread pages (proverbs 1–96).

## 4. Next steps and how to help

- **A full answer key for *Bu Me Bɛ*.** Once all 7,015 proverbs are transcribed, the whole book will be reviewed against the scans as an answer key, and the models will be scored on all of it, not just proverbs 1–320. The book is in copyright, so the answer key will stay private; only scores and error counts will be published.
- **1879 spelling.** How some 1879 marks should map to modern spelling is still open (see [`ORTHOGRAPHY.md`](../ORTHOGRAPHY.md)), and pages 5–13 of the 1879 test set still need proofreading. Both are listed as GitHub issues; contributions are welcome (see [`CONTRIBUTING.md`](../CONTRIBUTING.md)).
