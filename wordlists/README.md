# Word lists

`english_words.txt`: 84,189 lowercase English words, one per line. The English check (`postcorrect.correct_page`, issue T7 in `ORTHOGRAPHY.md`) uses it to recognise English lines and to fix clear misreadings in them (it Is → it is, wil! → will, ɔver → over).

Source: the word list inside Tesseract's English model, `eng.traineddata` from [tessdata_best](https://github.com/tesseract-ocr/tessdata_best) (Apache-2.0), extracted with Tesseract's own tools:

```
combine_tessdata -u eng.traineddata eng.
dawg2wordlist eng.lstm-unicharset eng.lstm-word-dawg words.txt
```

and then kept to words of lowercase letters (with at most one apostrophe), 2 to 20 letters long, sorted.
