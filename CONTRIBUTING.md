# Contributing

Thank you for helping. The most useful contributions are listed below, from the easiest to the most technical. You don't need to write code for the first three.

## 1. Answer an orthography question

[ORTHOGRAPHY.md](ORTHOGRAPHY.md#open-questions) lists open questions about historical Twi and Akan spelling. Each one has a GitHub issue labelled `orthography`. Open the issue, or the **Orthography evidence** issue form, and give:

- the source: author, title, year, page, and a link to the scan if it's online
- what the page shows, ideally with a cropped screenshot
- what you think it means, and how sure you are

Personal knowledge is welcome too: how your elders wrote, a church book you grew up with. Make sure to note that it's personal knowledge, so readers can weigh it.

## 2. Correct a rule

The 1879 spelling rules are in [`orthography/christaller_1879.tsv`](orthography/christaller_1879.tsv), one row per mark. To correct one:

1. Edit the row's meaning, example or `status`. Use *verified* only with a cited source that describes the rule, such as Christaller's grammar.
2. Put the source in the `source` column.
3. Run `python orthography.py` to check the file still loads.
4. Open a pull request.

## 3. Transcribe a page

Transcriptions are how the models are tested. The goal is to transcribe and review the whole of Christaller's *Twi Mmebusɛm* (issue T3): only 13 pages are done so far, and real pages would also improve training, which now relies on randomly placed marks.

1. Pick a page from a public-domain book, such as Christaller's 1879 *Twi Mmebusɛm* on HathiTrust (https://hdl.handle.net/2027/nnc1.0027031179).
2. Add the image to `eval/christaller_1879/` as `pNN_seqMM.png`, where NN is the printed page number and MM is HathiTrust's scan number, each with at least two digits. The scan number is the `seq=` value in the HathiTrust page address, and the number in the name of the PDF it downloads. For example, printed page 1 is scan 17, so its image is `p01_seq17.png`. Crop out handwritten notes.
3. Type the text into a file with the same name ending in `.gt.txt` (for example `p01_seq17.gt.txt`), **exactly as printed**: same line breaks, every mark kept. Follow the encoding in `eval/christaller_1879/README.md`. The line under e/o is U+0332 and the mark over w is U+030C.
4. List anything you weren't sure of in that README.
5. A second person checking a transcription is just as valuable as typing one, so comment on the pull request.

Don't add pages from books that are still under copyright. That includes modern editions and the Bu Me Bɛ scans used elsewhere in this project, which need to stay private.

## 4. Code and models

- Run `python score_1879.py` before and after a change, and paste both tables into the pull request.
- Keep the scripts runnable from the project folder with the commands in their docstrings.
- Never commit anything under `private/`.
- Models trained on GhanaNLP data are non-commercial (CC BY-NC-SA 4.0). See THIRD_PARTY_NOTICES.md.

## Licensing of contributions

By contributing, you agree that your contribution is released under the repository's terms: MIT for code, CC BY 4.0 for documentation, rules and transcriptions. The books being transcribed are in the public domain.

## Conduct

Be specific. Twi spelling differs between dialects and generations. A different spelling is evidence to record and not necessarily an error to correct.
