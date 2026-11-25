# Demo source: Christaller, *Twi Mmebusɛm* (1879), scan 17 (printed page 1)

## Citation

Christaller, J. G. *Twi mmebusɛm, mpensã-ahansĩa mmoaano: A Collection of Three Thousand and Six Hundred Tshi Proverbs, in Use among the Negroes of the Gold Coast Speaking the Asante and Fante Language*. Basel: Basel Evangelical Missionary Society, 1879.

Page image: HathiTrust Digital Library, from a copy held by Columbia University (volume nnc1.0027031179), scan 17 (printed page 1). Rights statement printed on the page image: "Public Domain, Google-digitized". HathiTrust record: https://hdl.handle.net/2027/nnc1.0027031179

## Rights

The 1879 text is in the public domain, and HathiTrust marks this scan "Public Domain, Google-digitized". Google-digitized volumes carry a request for non-commercial use and attribution, which this project follows. Keep this file next to the images.

## Files

| File | What it is |
| --- | --- |
| `christaller_1879_seq17.png` | Rendered at 600 dpi from `sources/christaller_1879/christaller_1879_seq17.pdf` |
| `christaller_1879_seq17_crop.png` | Proverbs 7–10, cut from the 600 dpi image, used for the README demo |
| `christaller_1879_seq17_twi.txt` | Output of this project's `twi_1879` model, as printed and then in modern spelling: `python ocr.py christaller_1879_seq17.png --orthography 1879` |
| `christaller_1879_seq17_eng.txt` | Output of stock Tesseract (English), for comparison: `tesseract christaller_1879_seq17.png stdout -l eng --psm 4` |

## Why this page, and what to expect

The page opens section B (proverbs 1–13), which includes proverbs that also appear in *Bu Me Bɛ*, so the same sayings can be compared across two spelling systems, 1879 and 2007.

Christaller's spelling is older than modern Twi orthography, so the demo uses the `twi_1879` model, which was trained to keep its marks. The page still has things that make it harder than *Bu Me Bɛ*:

- Open vowels are written as underlined e and o (for example *O̲ba*, *se̲*), where modern Twi uses ɛ and ɔ.
- Nasal vowels carry tildes (*nsũ*, *nũfu*) and tone or length marks appear (*Wommá*, *sumănã*).

All the example words are on this page (see its transcription, `eval/christaller_1879/p01_seq17.gt.txt`). What the marks mean comes from Christaller's own key to the letters in the same book (`sources/christaller_1879/christaller_1879_seq08.pdf`): a line below for the open vowels, a tilde for nasal vowels, a macron or breve for long or very short vowels, and acute and grave accents for tone. Modern Twi writes the open vowels as ɛ and ɔ and marks neither nasal vowels nor tone (Bureau of Ghana Languages, *Akan Orthography: Spelling Rules*, 1995; see ORTHOGRAPHY.md for the full key and sources).
- Handwritten margin numbers (for example "341R") are a later reader's annotations, possibly cross-references to Rattray's *Ashanti Proverbs* (1916); they are not part of the printed text.

The demo shows proverbs 7–10, and `make_demo.py` uses the as-printed part of the OCR output. It is an honest test of an older orthography, not a showcase of the model's best case: some ṅ and w̌ are still missed.

## Modern-spelling demo: *Mmoa Akenkan* (Akuapem Twi)

`docs/demo_modern.png` shows this project's `twi` model on page 8 of *Mmoa Akenkan* (*Counting animals*), an Akuapem Twi storybook from the African Storybook Project: https://global-asp.github.io/storybooks-ghana/stories/tw-akua/0327/

- Text: Zanele Buthelezi, Thembani Dladla, Clare Verbeek
- Illustrations: Rob Owen
- Translation: Michael Anguah-Mante (OLE Ghana)
- License: [Creative Commons Attribution 3.0](https://creativecommons.org/licenses/by/3.0/)
- Changes: screenshot of the web page, cropped to page 8; OCR text added below it in the demo image

| File | What it is |
| --- | --- |
| `mmoa_akenkan_p8.png` | Screenshot of page 8 as shown on the website |
| `mmoa_akenkan_p8_twi.txt` | Output of this project's `twi` model (v4) on the text of that page |
| `mmoa_akenkan_p8_eng.txt` | Output of stock Tesseract (English), for comparison |

This is digital text on a web page, not a scan, so it is an easier test than a printed book. On all eight text pages of the story, `twi` v4 read every character correctly, including ɛ, ɔ and Ɔ; stock Tesseract dropped every ɛ and ɔ (for example "Ɔno nso pɛ sɛ ɔnom" became "Jno nso pe se dnom").

