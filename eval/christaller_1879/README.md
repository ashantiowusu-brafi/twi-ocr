# 1879 evaluation set

Test pages for reading Christaller-era Twi spelling: J. G. Christaller, *Twi Mmebusɛm* (Basel, 1879), printed pages 1–13, proverbs 1–321. The book is in the public domain. The scans and their source are in `sources/christaller_1879/`.

Image page and paired text file:

| File | What it is |
|---|---|
| `pNN_seqMM.png` | Printed page NN (HathiTrust scan sequence MM) at 600 dpi, cut on the left to remove the handwritten margin numbers. The Google footer is cut off too. |
| `pNN_seqMM.gt.txt` | Diplomatic transcription: every mark kept as printed, one printed line per line, including the page header ("B. 3"), cross-references (R. 208, Cf. 569) and footnotes |

**Status.** The transcriptions were typed by eye from the 600 dpi scans, using Google's OCR text layer as a guide.

- **Pages 1–4 (proverbs 1–96):** proofread against the scans by the project author (22 Nov 2026).
- **Pages 5–13 (proverbs 97–321):** draft, not yet proofread. Corrections are welcome (see CONTRIBUTING.md)!

`score_1879.py` scores all 13 pages together. Treat the scores on pages 5–13 as provisional.

The set has 409 lines and 1,718 marks: 699 lines below, 348 dots above (mostly ṅ), 231 tildes, 158 acute accents, 89 macrons, 74 marks over w, 56 breves, 53 grave accents, 6 dots below and 4 circumflexes.

## Proofreading notes, pages 1–4

The proofreading changed 11 readings: afã and o̲se (p. 1); ṅhinā, Bákõmã and n’nyae (p. 2); etĩa, emmĩa, yo̲ṅkõ, ba-bone and oṅkúm’ (p. 3); abieṅ (p. 4). It left these as they were but noted them:

- **What look like two marks at once (acute and tilde) on one vowel:** Abanõmá (p. 3, proverb 43), wammá and wámà (p. 3, 61), aṅkyèafóo̲ (p. 4, 71). Typed with the clearer mark. This may be a real combination (nasal vowel plus tone), and it's recorded as evidence for open question O8.
- **Indeterminate marks:** the ī of ṅhinā (p. 2, 27; possibly a type flaw), õ in O̲bākõ (p. 2, 38), nī (p. 4, 70), the ā in [:mpere̲nsā] (p. 4, 75).
- **High tone on a syllabic nasal** is printed as a mark after the letter (n’nyae, oṅkúm’), the way Christaller's key writes it ("m′ n′ ṅ′"). It's typed as ’ after the letter.
- **Faint ink** that was judged to be specks, not marks: yo̲ṅkõ (p. 3, 49), ba-bone (p. 3, 55), abieṅ (p. 4, 87).

## Readings to check (pages 5–13 and the rest)

These are where the print was hard to read, or where a mark isn't in Christaller's key:

- **Tilde, macron or breve?** On small letters these three can look alike (for example fĕam and prekō on p. 8, mã’ on p. 11). Each was read as the closest match. These are the most likely errors.
- **Grave or dot over e in nè** (pp. 1, 2, 3, 8, 11, 12). Read as a grave (nè), since the key lists the grave and not a dotted e.
- **Marks not in the key:**
  - dotted s (mmuṡũa, p. 1)
  - dot under i (dị, p. 3, proverb 56)
  - dot under a (ạgō p. 3; ạde p. 7)
  - circumflex (nâ, mmâã, ṅkonyâã, mmâ)
  - grave on n or w (nsé̲ẁ p. 11, ǹnomé p. 12)

  These were kept as printed. Some may be specks on the scan.
- **Word spacing.** The book sets some words almost touching ("wommá no", "ka no", "ne nã"). The key uses a normal space.
- **Ditto marks** on p. 10 (proverb 228) are typed as „.
- **Margin remnants.** On a few pages (1, 5, 6, 9, 13) the handwritten numbers touch the printed ones, so small bits remain at the left edge.

## How marks are encoded

The marks and their meanings come from Christaller's key to the letters (`sources/christaller_1879/christaller_1879_seq08.pdf`, summarized in ORTHOGRAPHY.md). Text is stored in NFC. Letters that have a ready-made Unicode form use it (ã ũ ẽ á à ā ă ĕ ẹ ọ ạ ṅ ṡ â). Some marks have no ready-made form and are stored as a letter plus a combining mark:

- the line below e and o: U+0332 (e̲ o̲ O̲)
- the mark over w: U+030C (w̌)
- a few rare combinations, such as m̀ and ẁ

`orthography.py` converts the text to modern spelling. The rules are in `orthography/christaller_1879.tsv`.

## Scoring

```
python score_1879.py                       # every model in models/ plus eng
python score_1879.py --model twi_1879 twi_v4
python score_1879.py --pages 1-4           # only the proofread pages
```

`score_1879.py` reads each page as one block of text (`--psm 6`). The `--psm 4` setting splits the proverb numbers off into a separate column and loses them, which added about 4 percentage points of errors. Each model gets two rows: its raw output, and "+ clean-up", the same output after `orthography.cleanup_ocr`, which `ocr.py --orthography 1879` applies. Each row reports three numbers:

- **diplomatic CER:** errors against the key exactly as printed
- **modern CER:** errors after converting both sides to modern spelling
- **marks kept:** for each kind of 1879 mark, the share the model got right

## Adding pages

Name each pair `pNN_seqMM.png` / `.gt.txt`, follow the encoding above, and add any uncertain readings to the list above.
