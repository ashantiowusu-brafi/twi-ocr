# Historical Twi and Akan spelling

Twi has been written in the Latin alphabet since the 1840s, but the spelling has changed several times. Older books can't be read correctly by a model that only knows modern spelling. This file sums up what is known, lists what isn't, and explains how to help. **Contributions are welcome**: see [Open questions](#open-questions) and [CONTRIBUTING.md](CONTRIBUTING.md).

## Timeline (short)

| Period | System | Key features | Sources |
|---|---|---|---|
| 1842–1881 | Basel Mission and Christaller (Akuapem as the book language) | Five vowel letters plus diacritics, following Lepsius: a line under (underline) e and o for the open vowels, a dot under vowels, marks for nasal, long and short vowels and for tone, a dot over n | [Akuapem Twi (Wikipedia)](https://en.wikipedia.org/wiki/Akuapem_Twi): orthography begun by the Basel Mission in 1842, Riis's grammars of 1853; [Christaller 1875, *Grammar*, preface](https://archive.org/details/agrammarasantea00chrigoog): Riis's grammars of 1853 and 1854; Christaller 1879, key to the letters: `sources/christaller_1879/christaller_1879_seq08.pdf`; [Lepsius, *Standard Alphabet*, 1863](https://archive.org/details/standardalphabet00lepsuoft) |
| 1927–1930 | *Africa Alphabet* and *Practical Orthography of African Languages* | New letters instead of diacritics: ɛ, ɔ | ["The Practical Orthography of African Languages", *Africa* 1, no. 1 (1928): 125–129](https://www.cambridge.org/core/journals/africa/article/practical-orthography-of-african-languages/F704294AD6C3D97D51FE557970934165) (Memorandum I, first issued 1927; revised edition, Oxford University Press, 1930); [Africa Alphabet (Wikipedia)](https://en.wikipedia.org/wiki/Africa_Alphabet) |
| 1968 / 1978 | Akan Orthography Committee, then the unified common orthography | One standard for the Akan dialects, based mainly on Akuapem | Bureau of Ghana Languages, [*Writing Akan: Report of the Akan Orthography Committee* (1968)](https://glottolog.org/resource/reference/id/155646); Bureau of Ghana Languages and Language Centre, University of Ghana, *Unified Akan Orthography* (1978), cited in ["Fante: the orthography versus speech", *Journal of the International Phonetic Association*](https://www.cambridge.org/core/journals/journal-of-the-international-phonetic-association/article/fante-the-orthography-versus-speech/2A6072D0CD3724CD3C18D337F57662E7); [Akan language (Wikipedia)](https://en.wikipedia.org/wiki/Akan_language): "based mainly on Akuapem" |
| 1995 (launched 1997) | Bureau of Ghana Languages revision | Today's spelling: 22 letters, with ɛ and ɔ but no tone or nasal marks | Akan Language Committee, [*Akan Orthography: Spelling Rules* (Bureau of Ghana Languages, 1995)](https://openlibrary.org/books/OL145328M/Akan_orthography); launch in 1997: [Ghana Place Names, "Languages & Locations"](https://sites.google.com/site/ghanaplacenames/languages-locations); 22 letters: [Twi (Wikipedia)](https://en.wikipedia.org/wiki/Twi) |

There are four literary standards: Asante Twi, Akuapem Twi, Bono and Fante.

## How this repository handles 1879 spelling

- **Rules & data.** [`orthography/christaller_1879.tsv`](orthography/christaller_1879.tsv) lists each 1879 mark, its modern equivalent, an example and its **status**:
  - *observed:* seen on a scanned page
  - *assumed:* inferred by analogy
  - *verified:* confirmed in Christaller's own key to the letters

  [`orthography.py`](orthography.py) reads the table, so you can fix a spelling rule by editing the table, without touching any programming code.
- **Read then modernize.** `ocr.py --orthography 1879` keeps every mark exactly as printed and also writes a modern-spelling copy. 1879 spelling can be converted to modern spelling, but not back. Converting is simple: e̲ becomes ɛ and ã becomes a. Going back can't be done, because the modern copy drops the tildes and accents: ɛka doesn't show whether its a had a tilde. So `ocr.py` always keeps the as-printed copy as well. Sources: e̲ as the open vowel, Christaller's 1879 key to the letters (`sources/christaller_1879/christaller_1879_seq08.pdf`); today's ɛ and ɔ with no nasal or tone marks, the Bureau of Ghana Languages' *Akan Orthography: Spelling Rules* (1995) and Dolphyne (1988).
- **Training.** There is very little typed text in 1879 spelling: only the 13 transcribed test pages, far too few to train on, and they are kept for testing. So the training data starts from the plentiful modern Twi text (the same text used for the modern model) and makes it look like 1879 spelling. `render_lines.py --orthography 1879` does this in two steps. First it converts the letters that can be converted exactly: ɛ → e̲ and ɔ → o̲. Then it adds tildes, accents, w̌ and dotted n using rough rules of thumb (for example, a tilde on some vowels after m or n), each applied by chance at rates judged from pages 1 and 4, because modern text does not say where the marks belong (see above). This teaches the model what the marks look like, but they are not where Christaller would have put them (issue T4). The lines are drawn as scan-like images, and `scripts/train_1879.sh` fine-tunes the model on them. These rough rules are a stopgap for too little transcribed text: Christaller's 1881 dictionary (issue T2) and more transcribed pages of his book (issue T3) would let training place the marks where he actually used them (issue T4).
- **Testing.** `eval/christaller_1879/` holds transcribed pages, and `score_1879.py` scores every model on them.

## Christaller's key to the letters (1879)

The 1879 book opens with a one-page key (scan `sources/christaller_1879/christaller_1879_seq08.pdf`). It says the letters "sound as in Dr. Lepsius' Standard Alphabet" and refers readers to the 1875 *Grammar*, pages 1–7, and pages 185–196 on Akan and Fante differences. What it says, with modern equivalents:

**Vowels form two classes** (what linguists now call vowel harmony; see Dolphyne 1988 and Clements 1981, listed under Sources):

- **Class I:** a, e̲, o̲, ẹ, ọ
- **Class II:** ạ, e, o, i, u

| 1879 | Christaller's description | Modern |
|---|---|---|
| e̲ o̲ (line below) | as in "let, there, not, nor" | ɛ ɔ |
| e o, plain (class II) | "full, as in bed, fate, note" | e o |
| ẹ ọ (dot below, class I) | "diminished, approaching i, u" | e o (modern e and o cover both sounds) |
| a | "full", as in "far" | a |
| ạ (dot below) | "thin", before i, u, full e, o, gya, nyã, tw̌a: as in "fat" (in Fante, as e in "prey") | a |
| ā ē ī ō ū (macron) | long | not marked |
| ã ẽ ĩ õ ũ (tilde) | nasal | not marked |
| ă ĕ ĭ ŏ ŭ (breve) | very short | not marked |
| á é … ḿ ń ṅ́ (acute) | high or middle tone | not marked |
| à è … (grave) | low tone | not marked |
| ṅ | ng as in "sing" | n |
| w̌ | "wy"; in tw̌ (and dw̌) a sound like sh (zh) mixed with a palatal t (d) and w̌; in fw̌ the f is made with tongue and both lips "nearly as for whistling" | w (tw, dw) |
| hy | χ (like German ch) | hy |

Christaller adds that tones "are only exceptionally marked in single words, clauses, or whole proverbs". So an unmarked vowel says nothing about its tone.

The consonants are listed as: p b m f w, t d n s r, k g ṅ h, y; ky gy ny hy; kw (gw) ṅw hw; tw̌ dw̌ ṅw fw̌ w̌.

This settles the earlier puzzle about dots. Christaller uses both marks under vowels, for different things: a **line below** for the open vowels (modern ɛ ɔ), and a **dot below** for the "diminished" class I e/o and the "thin" class II a. In modern terms the dot-below letters are the advanced-tongue-root (+ATR) vowels and the underlined letters are the open −ATR vowels ɛ ɔ (Dolphyne 1988, see Sources). Christaller describes the two classes himself in his 1875 *Grammar*, §§ 2–5 and 17, and says in its preface (p. III) that the spelling follows Lepsius's Standard Alphabet ([Internet Archive](https://archive.org/details/agrammarasantea00chrigoog)).

## Open questions

Each question is meant to become a GitHub issue (`scripts/create_issues.sh` opens them). Answers should cite a page of a scanned source.

**Issue titles.** Every issue title gives its number, then the book or model it is about in square brackets, then the question: `O1 [Twi Mmebusɛm 1879]: …`. Use these names so issues can be searched and grouped:

- Books: *Twi Mmebusɛm 1879* (Christaller's proverbs, the `twi_1879` test book), *Grammar 1875*, *Dictionary 1881*, *Bu Me Bɛ* (the `twi` test book)
- Models: `twi` (modern spelling), `twi_1879` (1879 spelling)
- When an issue involves a book and a model, give both, separated by " · ": `[Twi Mmebusɛm 1879 · twi_1879]`. When it spans several books, name the group: `[Basel Mission books 1853–1881]`.

**Answered by the 1879 key** (keep as evidence; corrections welcome): the line below, tilde, breve, acute and grave accents, macron, dot below, ṅ, and what w̌ sounds like.

**Still open**

- **O1 [Twi Mmebusɛm 1879]. The mark over w: caron or breve?** The key says what w̌ sounds like, but the type is hard to tell apart at this scan quality. This project encodes it as U+030C (caron) and needs a sharper scan or the 1875 *Grammar* to confirm.
- **O2 [Twi Mmebusɛm 1879]. Dots the key doesn't list: real marks or scan specks?** Several dots on the scans don't appear in Christaller's key to the letters, and at this scan quality it is hard to tell a real mark from a speck of ink or a flaw in the type. They are: a dot over s in mmuṡũa (p. 1); a raised dot after m in the key's consonant list ("m· f"); and what may be dots under y in ky, gy, hy in the same list. A sharper scan (from another copy of the book) or the 1875 *Grammar* could settle each one. (Proofreading found no dot in o̲se, earlier thought to be o̲ṡe.)
- **O3 [Twi Mmebusɛm 1879 · twi_1879]. fw̌ / fw and modern hw.** Christaller writes ǹfwe (p. 9), where modern Twi writes hwɛ. Is fw → hw a regular correspondence that `to_modern` should apply?
- **O4 [Grammar 1875]. Does the 1875 *Grammar* (pp. 1–7) say more?** In particular, about the vowel classes and when ạ is marked.
- **O5 [Basel Mission books 1853–1881]. Change over time.** Does the spelling differ between Riis (1853), the 1875 *Grammar*, the 1879 proverbs and the 1881 dictionary?
- **O6 [Methodist Fante books]. Fante.** The Methodist (Wesleyan) Fante books used their own spelling. What were its conventions? Grammar pp. 185–196 is a starting point.
- **O7 [Basel and Presbyterian publications]. Dates.** When did each Basel or Presbyterian publication switch to ɛ and ɔ, and drop the other marks?
- **O8 [Twi Mmebusɛm 1879]. Other marks in the proverbs that the key doesn't list.** A circumflex (nâ, mmâã), dots under i and a (dị, ạgō), and a grave on w (nsé̲ẁ). Also vowels that seem to carry an acute and a tilde together (Abanõmá, wammá, wámà, aṅkyèafóo̲): a nasal vowel with a tone mark? Real marks or specks on the scan? See `eval/christaller_1879/README.md`.

**Technical**

- **T1 [Twi Mmebusɛm 1879 · twi_1879]. Proofread pages 5–13.** Pages 1–4 (proverbs 1–96) are proofread. Draft transcriptions of pages 5–13 (proverbs 97–321) are in `eval/christaller_1879/`. Check each against its scan, especially tilde, macron and breve. Transcribing more pages also helps. Good first issue.
- **T2 [Dictionary 1881 · twi_1879]. A period word list.** Clean the text of Christaller's 1881 dictionary (public domain, on the Internet Archive) into a word list for post-correction in 1879 spelling. T4 also uses it to place training marks.
- **T3 [Twi Mmebusɛm 1879 · twi_1879]. Transcribe the whole of *Twi Mmebusɛm*.** Only 13 of the book's pages are transcribed. Transcribing and reviewing the rest, page by page against the HathiTrust scans, would give a larger test set and show where Christaller put each mark in running text, which T4 needs. See CONTRIBUTING.md, "Transcribe a page".
- **T4 [twi_1879]. Place training marks where Christaller put them.** Needs T2 and T3. The `twi_1879` training lines are modern Twi converted to 1879 spelling. ɛ → e̲ and ɔ → o̲ convert exactly, but modern text doesn't say where the tildes, accents, w̌ and ṅ belong, so `orthography.add_period_marks` adds them with rough rules of thumb (for example, a tilde on some vowels after m or n) and chances judged from pages 1 and 4 (`MARK_SHARES` in `orthography.py`). Two sources can replace the guesses. The word list from Christaller's 1881 *Dictionary* (T2; see Sources) gives each word as he spelled it, so training can mark the words he marked. The transcribed pages (T3) show how often each mark is actually printed in the proverbs: the key says tones are marked "only exceptionally" there, which may be less often than in the dictionary.
- **T5 [twi and twi_1879]. A desktop app.** Build a simple interface so people can run the models on their own computer without the command line: open a scan or PDF, choose modern or 1879 spelling, and save the text. It should work offline, so scans never leave the user's computer. A first version is in `app/` (see `app/README.md`): a Mac app and a Windows app, both with Tesseract included; GitHub builds the Windows one (`.github/workflows/build-windows.yml`; not yet tested on a Windows PC). Still to do: testing on Windows, and signing both apps.
- **T6 [Bu Me Bɛ · twi]. Context correction inside the Modern Twi model.** The l → i fix (`postcorrect.py`, and an option in the app) checks single words against the GhanaNLP word list after reading, and neither model contains a dictionary of its own (checked with `combine_tessdata -d`). Proposed stages: (1) build a word dictionary from the GhanaNLP text into `twi.traineddata`, so Tesseract prefers real words while reading; (2) choose between Tesseract's alternative readings with a small model of which words follow which, so the surrounding words decide; (3) research only: a character-level correction model trained on pairs of OCR output and ground truth. Rules: change only words Tesseract is unsure of, show every change for review, and never alter what the book prints (old spellings, dialect and the author's grammar stay). Measure each stage with `compare_models.py` on held-out pages, overall and for ɛ/ɔ. If it wins, it becomes part of the Modern Twi model and the app's "Fix l read as i" option is removed.
- **T7 [Bu Me Bɛ · twi]. English text, especially in italics.** *Bu Me Bɛ* prints each proverb's English translation and explanation in sans-serif italics, and most of the `twi` model's remaining errors on a page are there. Examples from page 13: *comes ir* (it), *ɔf them* (of), *I wil! prevent* (will), *It Is coming* (is, several times), *frightening;:* and *fear.,* (an extra mark), and in the Twi, “*ƐEreba* (Ɛreba). Causes: the training lines include about 15% English, but drawn in serif fonts (Charis SIL and Noto Serif) and only sometimes in italics, so the model has hardly seen sans-serif italic type; and ɔ is so common in Twi that the model guesses it for a worn o. This is not the l → i fix, which only changes l, I and 1. Adding Tesseract's `eng` model fixed nothing in a test while damaging Twi (ɔde → ade). Plan: (1) retrain `twi` from the current model with more English lines (from the English side of the GhanaNLP sentence pairs), drawn mostly in italics and in sans-serif as well as serif fonts with ɛ and ɔ, keeping the Twi lines so nothing is forgotten; (2) an English check after reading: with an English word list (from Tesseract's `eng` model, Apache 2.0), fix clear cases such as ir → it, wil! → will, ɔf → of and a mid-sentence Is → is, and ƐE → Ɛ when that gives a known Twi word, but only flag doubled punctuation such as ;: or ., for review, since "etc.," is correct; every change is shown in the app. English text must stay exactly as printed. Measure with `compare_models.py` on *Bu Me Bɛ* (overall, ɛ/ɔ, and the English lines), counting English words fixed and Twi words wrongly changed. Related to T6. Status (26 November 2026): both steps are done. `twi_v5` scores as well as v4 on the Twi (CER 4.0% against 4.1%, ɛ/ɔ 97.4%) and makes fewer of most English mistakes, though more "it Is". The English check (`postcorrect.correct_page`, also in the app) cuts the clear English mistakes on the 14 test pages from 12.0 to 1.3 per 1,000 English words without changing the Twi score. Still to do: an exact English score on proofread pages (`private/eval_pages/`).

## Sources

- Christaller, J. G. (1881). *A Dictionary of the Asante and Fante Language called Tshi (Chwee, Tw̌i)*. Basel. [Internet Archive](https://archive.org/details/adictionaryasan00chrigoog). The preface discusses the vowel system.
- Christaller, J. G. (1879). *Twi Mmebusɛm*. Basel. Key to the letters and pages 1–13: `sources/christaller_1879/` (HathiTrust, nnc1.0027031179).
- Christaller, J. G. (1875). *A Grammar of the Asante and Fante Language called Tshi*. Basel. [Internet Archive](https://archive.org/details/agrammarasantea00chrigoog). Vowel classes in §§ 2–5 and 17; Lepsius in the preface, p. III.
- Akan Language Committee (1995). *Akan Orthography: Spelling Rules*. Accra: Bureau of Ghana Languages. [Open Library](https://openlibrary.org/books/OL145328M/Akan_orthography). The current standard spelling.
- Dolphyne, Florence Abena (1988). *The Akan (Twi-Fante) Language: Its Sound Systems and Tonal Structure*. Accra: Ghana Universities Press. The standard description of Akan's two vowel sets and vowel harmony.
- Clements, G. N. (1981). "Akan vowel harmony: a nonlinear analysis." *Harvard Studies in Phonology* 2. See also Clements (1984), ["Vowel harmony in Akan: a consideration of Stewart's word structure conditions"](https://journals.flvc.org/sal/article/download/107510/102830/146739), *Studies in African Linguistics* 15(3).
- Wikipedia: [Akuapem Twi](https://en.wikipedia.org/wiki/Akuapem_Twi), [Akan language](https://en.wikipedia.org/wiki/Akan_language), [Johann Gottlieb Christaller](https://en.wikipedia.org/wiki/Johann_Gottlieb_Christaller), [Africa Alphabet](https://en.wikipedia.org/wiki/Africa_Alphabet), [Standard Alphabet by Lepsius](https://en.wikipedia.org/wiki/Standard_Alphabet_by_Lepsius).
