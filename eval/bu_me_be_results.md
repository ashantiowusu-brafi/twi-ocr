# OCR results: Bu Me Bɛ

Generated 26 November 2026 by `compare_models.py`. All rows are scored on the same 319 proverbs from 14 scanned pages, against the answer key: proverbs 1–320 of the book's 7,015, all proofread.

| Model | What changed | CER | Change vs stock | ɛ/ɔ accuracy |
| --- | --- | --- | --- | --- |
| `eng` | Stock Tesseract English model (baseline) | 14.6% | — | 0.0% |
| `twi_v1` | 6,000 rendered lines, 3,000 iterations | 6.0% | -59% | 79.9% |
| `twi_v2` | 20,000 lines, 10,000 iterations, more line-initial capitals | 6.0% | -58% | 85.2% |
| `twi_v3` | Lookalike characters fixed; proverb numbers before Ɔ/Ɛ-initial lines | 4.2% | -71% | 97.0% |
| `twi_v4` | Training text in the book's quote style (“ ” and ’) | 4.1% | -72% | 97.3% |
| `twi_v5` | From twi_v4: more English lines, mostly italic, sans-serif fonts too (issue T7) | 4.0% | -72% | 97.4% |
| `twi_1879` | 1879-spelling model (writes ɛ ɔ as e̲ o̲); not meant for modern text | 12.8% | -12% | 36.5% |
| `twi_v5 + post-correction (public)` | l → i word-list fixes; word list: ghananlp (6,023 words) | 3.3% | -78% | 97.4% |
| `twi_v5 + post-correction (private)` | l → i word-list fixes; word list: ghananlp, bible, ug (38,266 words) | 3.1% | -79% | 97.4% |
| `twi_v5 + post-correction + English check (public)` | Line by line: l → i on Twi lines; clear English fixes on English lines | 3.3% | -78% | 97.4% |
| `twi_v5 + post-correction + English check (private)` | Line by line: l → i on Twi lines; clear English fixes on English lines | 3.1% | -79% | 97.4% |

**CER** (character error rate): edits needed to turn the OCR output into the answer key, divided by the number of characters in the key. Lower is better.

**ɛ/ɔ accuracy**: share of ɛ, ɔ, Ɛ and Ɔ in the answer key that the OCR read correctly.

## English: clear mistakes per 1,000 English words

The book prints each proverb's English in italics (issue T7). Counted in the English lines of the same 14 pages: a capital *Is/It* after a lowercase word, ɔ or ɛ inside an English word, "!" inside a word, and doubled punctuation such as ";:". These are wrong wherever they appear, so no transcription is needed; mistakes that still make a real word are not counted.

| Model | English words | Is/It | ɔ/ɛ | ! | ;: ., | All, per 1,000 words |
| --- | --- | --- | --- | --- | --- | --- |
| `twi_v1` | 8,800 | 44 | 15 | 2 | 2 | 7.2 |
| `twi_v2` | 8,773 | 61 | 17 | 8 | 3 | 10.1 |
| `twi_v3` | 8,758 | 73 | 17 | 8 | 6 | 11.9 |
| `twi_v4` | 8,764 | 61 | 23 | 11 | 13 | 12.3 |
| `twi_v5` | 8,754 | 83 | 12 | 8 | 2 | 12.0 |
| `twi_v5 + English check` | 8,740 | 0 | 4 | 5 | 2 | 1.3 |

Proverbs are assigned to pages using `twi_v5`'s reading of the printed proverb numbers. Post-correction swaps only l → i, using a Twi word list (public: GhanaNLP text only; private: adds Bible and UGSpeechData text). The English check (`postcorrect.correct_page`) skips the l → i fixes on English lines and fixes clear English mistakes instead (it Is → it is, wil! → will, ɔver → over).
