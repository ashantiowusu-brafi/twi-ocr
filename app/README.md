# Twi OCR desktop app (Mac and Windows)

A window for reading printed Twi without the command line. Choose the spelling of the book (Modern Twi or Basel Twi 1879), open a PDF, images or a folder, and the app reads every page with the `twi` or `twi_1879` model. Check each page next to its scan, correct the text, and save it as numbered `.txt` files. It works offline: scans and text never leave your computer.

This is a first version (issue T5 in `ORTHOGRAPHY.md`). The same code runs on macOS and Windows; on Windows, Ctrl takes the place of ⌘.

## Run it from the project folder

You need the project set up as in the main README (Python, `.venv`, Tesseract 5 and the two model files in `models/`). Then:

```
cd ~/Downloads/twi-ocr
source .venv/bin/activate
pip install -r app/requirements-app.txt
python app/twi_ocr_app.py
```

Two other ways to start it:

```
python app/twi_ocr_app.py --check   # show what it finds (Tesseract, models, word list), without a window
python app/twi_ocr_app.py --debug   # print errors in the Terminal while it runs
```

The l → i fix for Modern Twi uses `data/twi_ghananlp.txt`, made by `python download.py`. Without it the app still works, with that fix off.

## Using it

**Start page**

1. **Choose the spelling of your book.** *Modern Twi* uses the `twi` model. *Basel Twi 1879* uses the `twi_1879` model for Christaller-era books, and also makes a modern-spelling copy of each page.
2. **Open your scans:** a PDF, several images, or a folder. You can also drop them on the window.
3. **Options:**
   - *Pages* chooses what to read, as in a print dialog: all pages, odd pages, even pages, or a custom list such as `1-5, 8, 11-13`. Pages are counted across everything you opened, and the app shows how many there are.
   - *Fix l read as i (Modern Twi)* turns on the word-list fix.
   - *Modern-spelling copy (Basel 1879)* saves a `.modern.txt` next to each page.
   - *Faster reading (beta)* reads about twice as fast with a smaller copy of the model (see below).
   - *Save text to* sets the folder. *File name* and *starting at* set how the pages are named: `name_001.txt`, `name_002.txt`, … The name starts as the PDF's name. Use *starting at* when the PDF begins partway through a book, for example 17 if its first page is page 17. Files are numbered by their page in the PDF, so reading only odd pages saves `name_001`, `name_003`, …

Press **Start reading**. The progress window shows how many pages are done and about how long is left. **Cancel** stops and keeps the pages already read.

**Results page**

- **Scan on the left:** zoom with the buttons, by pinching, or by holding ⌘ and scrolling. Drag to move around the page.
- **Text on the right:** correct it there. For a Basel Twi 1879 book there are two tabs, *As printed (1879)* and *Modern spelling*.
- **Special characters:** the buttons above the text put a letter where the cursor is. They change with the spelling: ɛ Ɛ ɔ Ɔ for Modern Twi; e̲ o̲ E̲ O̲ ṅ w̌ ã ẽ ĩ õ ũ for 1879.
- **Marks** (shown on a dotted circle) go on the letter just before the cursor: tone marks, tilde, macron, breve, caron, dot below and line below. Each letter keeps one mark above and one below, except that a tilde can sit with an acute or grave accent (ã́). Clicking a mark the letter already has takes it off. The line below only goes on e and o.
- **Find:** ⌘F (or Ctrl+F) opens a find bar above the text. Every match is highlighted and the current one is orange; Return goes to the next, ⇧ Return to the previous, and Esc closes it with the cursor on the match. It ignores capitals but not marks, so o̲ finds o̲ and not o.
- **Files:** shows the file name and numbering, and can change them. These are the same settings as on the start page.
- **Saving:** *Save page* saves the page you are on; *Save all pages* saves every page. Saving again overwrites the same files, so you can save after more corrections.
- **Status bar:** the bar at the bottom shows the model, how long the reading took, and any pages that could not be read. A page Tesseract cannot read is left empty for you to type in.

**Back** returns to the start page without losing anything. **Return to results** takes you back to the page you were on, with your corrections. The results are replaced only when you start a new reading; if you have unsaved corrections, the app asks first.

## Speed

The app reads several pages at once, one per core of your Mac (all but one core, up to 8). PDF pages are drawn one at a time just before they are read and deleted straight after, so a long book uses almost no disk space.

*Faster reading (beta)* uses an integer copy of the model, which Tesseract's `combine_tessdata` makes the first time. It is kept in `~/Library/Application Support/Twi OCR/fast-models/`. On a test page it read about 1.8 times as fast, but its text differed from the full model's in about 2% of characters, sometimes better and sometimes worse. Its accuracy has not been measured on the held-out pages. The accuracy figures in the main README are for the full model, so turn this option off when accuracy matters most. If `combine_tessdata` is not found, the app uses the full model and says so.

On one Mac, *Bu Me Bɛ* read at about 1.4 seconds a page with faster reading on (2.4 seconds before parallel reading and the fast model). At that rate a 350-page book takes about 8 minutes.

## Build the app people can download

```
bash app/build_mac.sh
```

This makes `app/dist/Twi OCR.app` and `app/dist/Twi-OCR.dmg` (about 100–200 MB). The models, the 1879 spelling rules, Tesseract and, if present, the word list are packed inside. Tesseract is copied from your Homebrew installation with the libraries it needs by `bundle_tesseract_mac.py`, which points it at its own copies and signs them again, so the app runs on Macs without Homebrew. To leave Tesseract out, run `SKIP_TESSERACT=1 bash app/build_mac.sh`. The app is built for the kind of Mac it is built on, so a build on an Apple Silicon Mac does not run on an Intel Mac ("This app is not supported on this Mac").

**Building on GitHub.** `.github/workflows/build-mac.yml` builds both kinds on GitHub's Macs: `Twi-OCR-Mac-Intel.dmg` and `Twi-OCR-Mac-AppleSilicon.dmg`. In the **Actions** tab choose **Build Mac app** and **Run workflow** (or `gh workflow run build-mac.yml`); the files appear under the run's **Artifacts**, and are attached to a release if you name one. Because Tesseract comes from Homebrew on macOS 15, these need macOS 15 or newer. To find out which kind of Mac you have: Apple menu > About This Mac (Chip: Apple M… is Apple Silicon; Processor: Intel is Intel), or `uname -m` in Terminal (arm64 or x86_64). `app/build/` holds temporary files and can be deleted. Both folders are kept out of git. Attach the `.dmg` to a GitHub release to share it.

## Windows

The Windows app is built on GitHub, so no Windows computer is needed to make it: in the repository's **Actions** tab, choose **Build Windows app** and **Run workflow**. It takes the models from a release (v1.0 unless you choose another), builds the GhanaNLP word list, installs Tesseract and packs everything into `Twi-OCR-Windows.zip`. The zip appears under the run's **Artifacts**, and is attached to a release if you name one. To build on a Windows PC instead, see the top of `build_windows.ps1`.

To use it, unzip the folder and open **Twi OCR.exe**. Tesseract is included, so nothing else needs installing. Windows 10 and 11 already have the WebView2 component the window uses. The app is not signed, so the first time Windows may show "Windows protected your PC": choose **More info**, then **Run anyway**.

Settings are saved in `%APPDATA%\Twi OCR\settings.json`, and text by default in `Documents\Twi OCR\`. Page images are sent to Tesseract directly rather than through files, because Tesseract on Windows may not open paths that contain letters such as ɛ or ɔ. Faster reading keeps its smaller model copies in `%APPDATA%\Twi OCR\fast-models\`; if your Windows user name contains such letters and every page fails with it on, untick Faster reading.

## What people need (Mac)

- **Nothing else to install.** Tesseract is included. The app uses its own copy first; to use another, open **Settings** and choose the `tesseract` program. When run from the project folder (`python app/twi_ocr_app.py`), it uses your installed Tesseract instead.
- **Opening an unsigned app.** The app is not signed with an Apple Developer ID, so the first time macOS says Apple cannot check it. On macOS 14 and earlier, right-click the app and choose **Open**. On macOS 15 and newer: double-click it, click **Done**, then straight away open **System Settings → Privacy & Security**, scroll down to **Security** and click **Open Anyway** (the button shows for about an hour after the attempt). Or, in Terminal: `xattr -dr com.apple.quarantine "/Applications/Twi OCR.app"`. Signing and notarising need the paid Apple Developer Program.

## Files

| File | What it does |
| --- | --- |
| `twi_ocr_app.py` | The app: finds Tesseract, reads pages in parallel, keeps corrections, saves numbered text files. Uses `orthography.py` and `postcorrect.py` from the project. |
| `ui/index.html` | The window's layout, buttons and special-character tools. |
| `ui/fonts/Charis-Regular.ttf` | Shows the 1879 marks (such as the line under e̲ and o̲) in the text box; the Mac's system font does not draw them. SIL Open Font License, see `ui/fonts/OFL.txt`. |
| `ui/icons-LICENSE.txt` | Licence for the Tabler icons in `ui/index.html`. |
| `requirements-app.txt` | Extra Python packages for the app and for building it. |
| `build_mac.sh` | Builds the `.app` and `.dmg`. |
| `bundle_tesseract_mac.py` | Copies Tesseract and its libraries into one folder for the Mac app (run by `build_mac.sh`). |
| `build_windows.ps1`, `requirements-windows.txt` | Build the Windows app folder and `Twi-OCR-Windows.zip`, with Tesseract inside; run by `.github/workflows/build-windows.yml`. |

Settings (Tesseract location, output folder, options) are saved in `~/Library/Application Support/Twi OCR/settings.json` on a Mac. Text is saved by default to `~/Documents/Twi OCR/<file name>/`, one `.txt` per page, plus `.modern.txt` for Basel Twi 1879.

## Licences

Code: MIT. The models are CC BY-NC-SA 4.0 (non-commercial); so are the fast copies the app makes of them, and the GhanaNLP word list if it is bundled. Other components are listed in `../THIRD_PARTY_NOTICES.md`.
