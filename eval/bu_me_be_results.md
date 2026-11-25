# OCR results: Bu Me Bɛ

Generated 25 November 2026 by `compare_models.py`. All rows are scored on the same 319 proverbs from 14 scanned pages, against the answer key: proverbs 1–320 of the book's 7,015, all proofread.

| Model | What changed | CER | Change vs stock | ɛ/ɔ accuracy |
| --- | --- | --- | --- | --- |
| `eng` | Stock Tesseract English model (baseline) | 14.6% | — | 0.0% |
| `twi_v1` | 6,000 rendered lines, 3,000 iterations | 6.0% | -59% | 79.9% |
| `twi_v2` | 20,000 lines, 10,000 iterations, more line-initial capitals | 6.0% | -58% | 85.2% |
| `twi_v3` | Lookalike characters fixed; proverb numbers before Ɔ/Ɛ-initial lines | 4.2% | -71% | 97.0% |
| `twi_v4` | Training text in the book's quote style (“ ” and ’) | 4.1% | -72% | 97.3% |
| `twi_1879` | 1879-spelling model (writes ɛ ɔ as e̲ o̲); not meant for modern text | 12.8% | -12% | 36.5% |
| `twi_v4 + post-correction (public)` | l → i word-list fixes; word list: ghananlp (6,023 words) | 3.4% | -76% | 97.3% |
| `twi_v4 + post-correction (private)` | l → i word-list fixes; word list: ghananlp, bible (32,009 words) | 3.3% | -77% | 97.3% |

**CER** (character error rate): edits needed to turn the OCR output into the answer key, divided by the number of characters in the key. Lower is better.

**ɛ/ɔ accuracy**: share of ɛ, ɔ, Ɛ and Ɔ in the answer key that the OCR read correctly.

Proverbs are assigned to pages using `twi_v4`'s reading of the printed proverb numbers. Post-correction swaps only l → i, using a Twi word list (public: GhanaNLP text only; private: adds Bible and UGSpeechData text).
