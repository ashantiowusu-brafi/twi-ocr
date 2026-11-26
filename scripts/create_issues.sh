#!/usr/bin/env bash
# Open one GitHub issue per open question in ORTHOGRAPHY.md.
# Run once from the project folder after pushing: bash scripts/create_issues.sh
# (Running it again opens duplicates; to add one issue, run its gh issue create line by hand.)
# Needs the GitHub CLI (brew install gh; gh auth login).
set -euo pipefail

gh label create orthography --color 5319e7 --description "Historical Twi/Akan spelling" --force
gh label create "help wanted" --color 008672 --force
gh label create "good first issue" --color 7057ff --force

issue() {  # title, labels, body
  gh issue create --title "$1" --label "$2" --body "$3

See ORTHOGRAPHY.md (Open questions) for context. Please cite the source and page."
}

issue "O1 [Twi Mmebusɛm 1879]: Mark over w (w̌): caron or breve in the original type?" "orthography,help wanted" \
"Christaller's 1879 key says w̌ = 'wy' (sources/christaller_1879/christaller_1879_seq08.pdf) but the type is hard to read at this scan quality. The project encodes it as U+030C (caron)."
issue "O2 [Twi Mmebusɛm 1879]: Dots the key doesn't list: real marks or scan specks?" "orthography,help wanted" \
"At this scan quality it is hard to tell a real mark from a speck or a flaw in the type. Dots to check: over s in mmuṡũa (p. 1); a raised dot after m in the key's consonant list ('m· f'); possible dots under y in ky, gy, hy (christaller_1879_seq08.pdf). A sharper scan or the 1875 Grammar could settle each one."
issue "O3 [Twi Mmebusɛm 1879 · twi_1879]: Is Christaller's fw (ǹfwe) regularly modern hw (hwɛ)?" "orthography,help wanted" \
"If so, orthography.to_modern could apply it. Needs more examples."
issue "O4 [Grammar 1875]: What do pp. 1–7 add to the 1879 key?" "orthography,help wanted" \
"Especially on the two vowel classes and when ạ is marked."
issue "O5 [Basel Mission books 1853–1881]: Did the spelling change between Riis 1853, 1875, 1879 and 1881?" "orthography,help wanted" \
"Compare the same words across the Basel Mission books."
issue "O6 [Methodist Fante books]: Document the Methodist (Wesleyan) Fante spelling" "orthography,help wanted" \
"What conventions did the Fante books use? Christaller's Grammar pp. 185–196 discusses Akan–Fante differences."
issue "O7 [Basel and Presbyterian publications]: When did Twi publications switch to ɛ/ɔ and drop the other marks?" "orthography,help wanted" \
"Dates and examples from Basel or Presbyterian, Methodist and government publications."
issue "O8 [Twi Mmebusɛm 1879]: Marks in the proverbs that the key doesn't list (â, ị, ạ, ẁ, acute + tilde)" "orthography,help wanted" \
"Real marks or specks on the scan? See eval/christaller_1879/README.md for where each appears."
issue "T1 [Twi Mmebusɛm 1879 · twi_1879]: Proofread test pages 5–13" "good first issue,help wanted" \
"Pages 1–4 are proofread. Draft transcriptions of pages 5–13 (proverbs 97–321) are in eval/christaller_1879/. Check each page against its scan, especially tilde vs macron vs breve; see the list of uncertain readings in that folder's README."
issue "T2 [Dictionary 1881 · twi_1879]: Build a word list from Christaller's 1881 dictionary" "help wanted" \
"Clean the Internet Archive text (https://archive.org/details/adictionaryasan00chrigoog) into a word list for post-correction in 1879 spelling. T4 also uses it to place training marks."
issue "T3 [Twi Mmebusɛm 1879 · twi_1879]: Transcribe the whole book" "good first issue,help wanted" \
"Only 13 pages are transcribed (eval/christaller_1879/). Transcribe and review more pages against the HathiTrust scans (https://hdl.handle.net/2027/nnc1.0027031179), following CONTRIBUTING.md. More pages give a larger test set and show where Christaller put each mark in running text, which T4 needs."
issue "T4 [twi_1879]: Place training marks where Christaller put them" "help wanted" \
"Needs T2 and T3. The twi_1879 training lines are modern Twi converted to 1879 spelling. orthography.add_period_marks adds tildes, accents, w̌ and ṅ with rough rules of thumb and chances judged from pages 1 and 4 (MARK_SHARES in orthography.py). Use the word list from Christaller's 1881 Dictionary (T2; https://archive.org/details/adictionaryasan00chrigoog) to mark the words he marked, and the transcribed pages (T3) to match how often each mark is printed in the proverbs, where the key says tones are marked 'only exceptionally'."
issue "T5 [twi and twi_1879]: A desktop app for running the models locally" "help wanted" \
"Build a simple interface so people can run the models on their own computer without the command line: open a scan or PDF, choose modern or 1879 spelling, and save the text. It should work offline, so scans never leave the user's computer. ocr.py already does the work; the app would wrap it."
issue "T6 [Bu Me Bɛ · twi]: Context correction inside the Modern Twi model" "help wanted" \
"The l → i fix checks single words against the GhanaNLP word list after reading, and neither model contains a dictionary (combine_tessdata -d). Stages: (1) build a word dictionary from the GhanaNLP text into twi.traineddata; (2) choose between Tesseract's alternative readings with a small word-sequence model, so context decides; (3) research only: a character-level correction model trained on OCR output and ground-truth pairs. Change only uncertain words, show every change for review, never alter what the book prints. Measure with compare_models.py on held-out pages, overall and for ɛ/ɔ. If it wins, remove the app's 'Fix l read as i' option."
issue "T7 [Bu Me Bɛ · twi]: English text, especially in italics" "help wanted" \
"Bu Me Bɛ prints English in sans-serif italics, where most remaining errors are. Page 13: comes ir (it), ɔf them (of), I wil! prevent (will), It Is coming (is), frightening;: and fear., (extra mark), and in the Twi ƐEreba (Ɛreba). The training lines have about 15% English but in serif fonts and only sometimes italic. Plan: (1) retrain twi from the current model with more English lines from the GhanaNLP sentence pairs, mostly italic, in sans-serif and serif fonts, keeping the Twi lines; (2) an English check after reading (word list from Tesseract's eng model, Apache 2.0): fix clear cases (ir → it, wil! → will, ɔf → of, mid-sentence Is → is, ƐE → Ɛ when it gives a known Twi word), only flag doubled punctuation, show every change. Adding the eng model damaged Twi in a test (ɔde → ade). English must stay exactly as printed. Measure with compare_models.py: overall, ɛ/ɔ, English lines, Twi words wrongly changed."
echo "Done."
