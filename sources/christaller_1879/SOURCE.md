# Source scans: Christaller, *Twi Mmebusɛm* (1879)

Christaller, J. G. *Twi mmebusɛm, mpensã-ahansĩa mmoaano: A Collection of Three Thousand and Six Hundred Tshi Proverbs, in Use among the Negroes of the Gold Coast Speaking the Asante and Fante Language*. Basel: Basel Evangelical Missionary Society, 1879.

Page images from the HathiTrust Digital Library, from a copy held by Columbia University (volume nnc1.0027031179): https://hdl.handle.net/2027/nnc1.0027031179. Each PDF is one page as downloaded. The `seq` number in each file name is HathiTrust's page sequence, not the printed page number.

## Rights

The 1879 text is in the public domain. HathiTrust marks these scans "Public Domain, Google-digitized". Google-digitized volumes carry a request for non-commercial use and attribution, which this project follows. Keep this file with the scans.

## Files

| File | Printed page | Contents |
|---|---|---|
| `christaller_1879_seq08.pdf` | unnumbered, before p. 1 | **Christaller's key to the letters**: the vowel classes, the marks and their sounds (see ORTHOGRAPHY.md) |
| `christaller_1879_seq17.pdf` | 1 | Title, section B, proverbs 1–13 (the demo page) |
| `christaller_1879_seq18.pdf` | 2 | from proverb 14 |
| `christaller_1879_seq19.pdf` | 3 | from proverb 40 |
| `christaller_1879_seq20.pdf` | 4 | from proverb 68 |
| `christaller_1879_seq21.pdf` | 5 | from proverb 97 |
| `christaller_1879_seq22.pdf` | 6 | from proverb 120 |
| `christaller_1879_seq23.pdf` | 7 | from proverb 142 |
| `christaller_1879_seq24.pdf` | 8 | from proverb 166 |
| `christaller_1879_seq25.pdf` | 9 | from proverb 193 |
| `christaller_1879_seq26.pdf` | 10 | from proverb 216 |
| `christaller_1879_seq27.pdf` | 11 | from proverb 238 |
| `christaller_1879_seq28.pdf` | 12 | from proverb 265 |
| `christaller_1879_seq29.pdf` | 13 | from proverb 294 |

The PDFs contain Google's own OCR text layer. It drops most of the 1879 marks, so don't use it as an answer key.

## Using them

`ocr.py` reads the PDFs directly:

```
python ocr.py sources/christaller_1879/christaller_1879_seq18.pdf --psm 4                      # modern model
python ocr.py sources/christaller_1879/christaller_1879_seq18.pdf --orthography 1879 --psm 4   # once twi_1879 is trained
```

To add a page to the test set, crop out handwritten margin notes and transcribe it into `eval/christaller_1879/` (see that folder's README).
