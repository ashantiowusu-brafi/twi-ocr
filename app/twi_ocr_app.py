"""Twi OCR desktop app for macOS.

A window around the project's OCR code: pick the spelling of the book
(Modern Twi or Basel Twi 1879), open a PDF, images or a folder, and read every
page with the twi or twi_1879 Tesseract model. Pages can be checked and
corrected side by side with the scan, then saved as .txt files. Nothing is
sent anywhere: the scans and the text stay on this Mac.

Run from the project folder:
    pip install -r app/requirements-app.txt
    python app/twi_ocr_app.py
    python app/twi_ocr_app.py --check   # show what it finds, without a window
    python app/twi_ocr_app.py --debug   # print errors while it runs

Needs Tesseract 5 (the app looks in the usual install places, or set its
location in Settings) and the model files in models/.

License: MIT (code). The models are CC BY-NC-SA 4.0, non-commercial.
"""

from __future__ import annotations

import base64
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

FROZEN = getattr(sys, "frozen", False)   # True inside the packaged .app.
APP_DIR = Path(sys._MEIPASS) if FROZEN else Path(__file__).resolve().parent
PROJECT = APP_DIR if FROZEN else APP_DIR.parent   # Holds models/, data/, ocr.py.
sys.path.insert(0, str(PROJECT))

import orthography   # noqa: E402  (needs the path above)

UI_FILE = APP_DIR / "ui" / "index.html"
MODELS = PROJECT / "models"
WORD_LIST = PROJECT / "data" / "twi_ghananlp.txt"
IS_WINDOWS = sys.platform == "win32"
IS_MAC = sys.platform == "darwin"
if IS_WINDOWS:   # Settings live where each system keeps app settings.
    SETTINGS_DIR = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming") / "Twi OCR"
elif IS_MAC:
    SETTINGS_DIR = Path.home() / "Library" / "Application Support" / "Twi OCR"
else:
    SETTINGS_DIR = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "Twi OCR"
SETTINGS_FILE = SETTINGS_DIR / "settings.json"
DEFAULT_OUTPUT = Path.home() / "Documents" / "Twi OCR"
# Integer ("fast") copies of the models, made once with Tesseract's combine_tessdata.
# They read about twice as fast and may misread a few more letters.
FAST_MODELS = SETTINGS_FILE.parent / "fast-models"

IMAGE_TYPES = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}
PDF_DPI = 300   # Same as ocr.py: the resolution PDF pages are read at.
PREVIEW_WIDTH = 2400   # Width of the page image shown in the window.
# Pages read at the same time. Each Tesseract runs on one core (it is no
# faster on more for one page), so use every core but one, up to 8.
WORKERS = max(1, min(8, (os.cpu_count() or 2) - 1))

# Apps opened from Finder or the Start menu may not see the Terminal's PATH, so
# look where Tesseract is usually installed: Homebrew, MacPorts and conda on a
# Mac; the UB Mannheim installer, Chocolatey, Scoop and conda on Windows.
if IS_WINDOWS:
    _program_files = [os.environ.get(v) for v in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA")]
    TESSERACT_PLACES = [str(Path(p) / sub / "tesseract.exe") for p in _program_files if p
                        for sub in ("Tesseract-OCR", "Programs/Tesseract-OCR")] + [
        r"C:\ProgramData\chocolatey\bin\tesseract.exe",
        str(Path.home() / "scoop" / "shims" / "tesseract.exe"),
        str(Path.home() / "anaconda3" / "Library" / "bin" / "tesseract.exe"),
        str(Path.home() / "miniconda3" / "Library" / "bin" / "tesseract.exe"),
    ]
else:
    TESSERACT_PLACES = [
        "/opt/homebrew/bin/tesseract", "/usr/local/bin/tesseract", "/opt/local/bin/tesseract",
        "/opt/anaconda3/bin/tesseract", str(Path.home() / "anaconda3/bin/tesseract"),
        str(Path.home() / "miniconda3/bin/tesseract"), "/usr/bin/tesseract",
    ]
# A copy of Tesseract packed inside the app (the Windows build includes one).
BUNDLED_TESSERACT = APP_DIR / "tesseract" / ("tesseract.exe" if IS_WINDOWS else "tesseract")
# On Windows, keep each Tesseract run from flashing a console window.
NO_WINDOW = {"creationflags": subprocess.CREATE_NO_WINDOW} if IS_WINDOWS else {}

SPELLINGS = {
    # model file, Tesseract page mode (6 keeps 1879 proverb numbers on their lines)
    "modern": {"model": "twi", "psm": 3, "label": "Modern Twi"},
    "basel1879": {"model": "twi_1879", "psm": 6, "label": "Basel Twi 1879"},
}


# --- Settings ----------------------------------------------------------------

def load_settings() -> dict:
    """Return saved settings, or the defaults on first run."""
    settings = {"tesseract": "", "output": str(DEFAULT_OUTPUT), "fix_il": True, "modern_copy": True, "fast": True}
    try:
        settings.update(json.loads(SETTINGS_FILE.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        pass
    return settings


def save_settings(settings: dict) -> None:
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps(settings, indent=2), encoding="utf-8")


def find_tesseract(saved: str = "") -> str | None:
    """Return the path to Tesseract: the saved one, the app's own copy, then PATH and usual places."""
    for candidate in [saved, str(BUNDLED_TESSERACT), shutil.which("tesseract"), *TESSERACT_PLACES]:
        if candidate and Path(candidate).is_file() and os.access(candidate, os.X_OK):
            return candidate
    return None


def tesseract_version(path: str) -> str:
    try:
        out = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=10, **NO_WINDOW)
        first = (out.stdout or out.stderr).splitlines()[0]
        return first.replace("tesseract", "Tesseract").strip()
    except (OSError, IndexError, subprocess.SubprocessError):
        return "Tesseract"


def fast_models(tesseract: str, model: str) -> Path | None:
    """Return the folder holding an integer copy of ``model``, making it the first time.

    combine_tessdata -c converts the model's float network to 8-bit integers,
    as in Tesseract's "fast" models. Returns None if that is not possible.
    """
    source = MODELS / f"{model}.traineddata"
    target = FAST_MODELS / f"{model}.traineddata"
    if target.exists() and target.stat().st_mtime >= source.stat().st_mtime:
        return FAST_MODELS
    combine = Path(tesseract).with_name("combine_tessdata.exe" if IS_WINDOWS else "combine_tessdata")
    if not combine.exists():
        combine = Path(shutil.which("combine_tessdata") or "")
    if not combine.is_file():
        return None
    FAST_MODELS.mkdir(parents=True, exist_ok=True)
    temp = target.with_suffix(".tmp")
    shutil.copyfile(source, temp)
    os.chmod(temp, 0o644)
    try:
        done = subprocess.run([str(combine), "-c", str(temp)], capture_output=True, timeout=300, **NO_WINDOW)
    except (OSError, subprocess.SubprocessError):
        temp.unlink(missing_ok=True)
        return None
    if done.returncode != 0 or temp.stat().st_size >= source.stat().st_size:
        temp.unlink(missing_ok=True)
        return None
    temp.replace(target)
    return FAST_MODELS


def clean_name(name: str) -> str:
    """Make a file name safe: keep letters (ɛ, ɔ and accents too), digits, spaces, - and _."""
    name = unicodedata.normalize("NFC", name or "").strip()
    name = "".join(c if c.isalnum() or c in " -_." else "_" for c in name)
    return name.strip(" .")[:80]


# --- Reading pages -----------------------------------------------------------

def collect_inputs(paths: list[str]) -> list[Path]:
    """Expand folders into the images and PDFs they hold, in name order."""
    found: list[Path] = []
    for raw in paths:
        path = Path(raw)
        if path.is_dir():
            found.extend(sorted(p for p in path.iterdir() if p.suffix.lower() in IMAGE_TYPES | {".pdf"}))
        elif path.suffix.lower() in IMAGE_TYPES | {".pdf"} and path.exists():
            found.append(path)
    return found


_pdf_lock = threading.Lock()   # pdfium is not thread-safe: one PDF call at a time.


class Cancelled(Exception):
    """The user pressed Cancel while a page was being read."""


def list_pages(inputs: list[Path]) -> list[dict]:
    """Every page to read, in order: each page of each PDF, and each image."""
    import pypdfium2 as pdfium
    pages: list[dict] = []
    for item in inputs:
        if item.suffix.lower() == ".pdf":
            with _pdf_lock:
                document = pdfium.PdfDocument(str(item))
                count = len(document)
                document.close()
            pages += [{"pdf": item, "number": n, "name": f"{item.stem}-{n:03d}"} for n in range(1, count + 1)]
        else:
            pages.append({"file": item, "name": item.stem})
    for seq, page in enumerate(pages, 1):   # Page number across everything opened, from 1.
        page["seq"] = seq
    return pages


def choose_pages(mode: str, custom: str, total: int) -> list[int]:
    """Page numbers to read, as in a print dialog: all, odd, even, or custom ("1-5, 8, 11-13")."""
    if mode == "odd":
        return list(range(1, total + 1, 2))
    if mode == "even":
        return list(range(2, total + 1, 2))
    if mode != "custom":
        return list(range(1, total + 1))
    chosen: set[int] = set()
    for part in (custom or "").replace(" ", "").split(","):
        if not part:
            continue
        bounds = part.split("-")
        if len(bounds) > 2 or not all(b.isdigit() for b in bounds):
            raise ValueError(f"“{part}” is not a page or range. Write pages like 1-5, 8, 11-13.")
        first, last = int(bounds[0]), int(bounds[-1])
        if first > last:
            first, last = last, first
        if first < 1 or last > total:
            raise ValueError(f"“{part}” is outside pages 1–{total}.")
        chosen.update(range(first, last + 1))
    if not chosen:
        raise ValueError("Write the pages to read, like 1-5, 8, 11-13.")
    return sorted(chosen)


def render_page(page: dict, max_width: int | None = None):
    """Return one page as a PIL image: a PDF page at 300 dpi (as ocr.py does), or the image file."""
    from PIL import Image
    if "file" in page:
        with Image.open(page["file"]) as img:
            img = img.convert("RGB")
            if max_width and img.width > max_width:
                img = img.resize((max_width, round(img.height * max_width / img.width)))
            return img.copy()
    import pypdfium2 as pdfium
    with _pdf_lock:
        document = pdfium.PdfDocument(str(page["pdf"]))
        try:
            pdf_page = document[page["number"] - 1]
            scale = PDF_DPI / 72
            if max_width:
                scale = min(scale, max_width / pdf_page.get_width())
            bitmap = pdf_page.render(scale=scale)
            image = bitmap.to_pil().copy()
            bitmap.close()
            pdf_page.close()
        finally:
            document.close()
    return image


def preview(page: dict) -> str:
    """Return a page image, scaled down for the window, as a data: URL ("" if it can't be opened)."""
    try:
        image = render_page(page, PREVIEW_WIDTH).convert("RGB")
    except Exception:
        return ""
    buf = io.BytesIO()
    image.save(buf, format="JPEG", quality=85)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def load_corrector():
    """Return the l -> i fixer from postcorrect.py, or None without a word list."""
    if not WORD_LIST.exists():
        return None
    import postcorrect as pc
    pc.CONFUSIONS = pc.SWAP_SETS["i"]   # Only l/I/1 -> i; never e/ɛ or o/ɔ.
    vocab = pc.build_vocabulary([WORD_LIST])
    return lambda text: pc.correct_text(text, vocab)


# --- The bridge the window calls ---------------------------------------------

class Api:
    """Methods the page's JavaScript calls as window.pywebview.api.<name>()."""

    def __init__(self) -> None:
        self._window = None
        self._settings = load_settings()
        self._pages: list[dict] = []   # {name, image, text, modern}
        self._spelling = "modern"
        self._source_name = ""
        self._tmp = tempfile.TemporaryDirectory(prefix="twi-ocr-")   # One page image at a time per reader.
        self._busy = False
        self._cancel = threading.Event()
        self._lock = threading.Lock()
        self._procs: set[subprocess.Popen] = set()   # Tesseract runs to stop on Cancel.

    # Status and settings
    def status(self) -> dict:
        tesseract = find_tesseract(self._settings.get("tesseract", ""))
        return {
            "tesseract": tesseract,
            "tesseract_version": tesseract_version(tesseract) if tesseract else None,
            "models": {key: (MODELS / f"{s['model']}.traineddata").exists() for key, s in SPELLINGS.items()},
            "word_list": WORD_LIST.exists(),
            "workers": WORKERS, "cores": os.cpu_count(),
            "platform": "windows" if IS_WINDOWS else "mac" if IS_MAC else "linux",
            "settings": self._settings,
        }

    def set_option(self, key: str, value) -> dict:
        if key in {"fix_il", "modern_copy", "fast"}:
            self._settings[key] = bool(value)
            save_settings(self._settings)
        return self._settings

    def choose_tesseract(self) -> dict:
        import webview
        start = os.environ.get("ProgramFiles", "C:\\") if IS_WINDOWS else "/opt/homebrew/bin"
        picked = self._window.create_file_dialog(webview.FileDialog.OPEN, directory=start)
        if picked:
            self._settings["tesseract"] = picked[0]
            save_settings(self._settings)
        return self.status()

    def choose_output(self) -> dict:
        import webview
        picked = self._window.create_file_dialog(webview.FileDialog.FOLDER, directory=self._settings["output"])
        if picked:
            self._settings["output"] = picked[0]
            save_settings(self._settings)
        return self._settings

    # Choosing scans
    def choose(self, kind: str) -> list[str]:
        import webview
        if kind == "folder":
            picked = self._window.create_file_dialog(webview.FileDialog.FOLDER)
        else:
            types = ("PDF files (*.pdf)",) if kind == "pdf" else ("Images (*.png;*.jpg;*.jpeg;*.tif;*.tiff;*.bmp;*.webp)",)
            picked = self._window.create_file_dialog(webview.FileDialog.OPEN, allow_multiple=kind == "images", file_types=types)
        return list(picked or [])

    # Reading
    def count_pages(self, paths: list[str]) -> dict:
        """How many pages the chosen PDFs and images have, for the page choice."""
        try:
            return {"pages": len(list_pages(collect_inputs(paths)))}
        except Exception as error:
            return {"pages": 0, "error": str(error)}

    def start(self, paths: list[str], spelling: str, page_mode: str = "all", custom: str = "") -> dict:
        if self._busy:
            return {"ok": False, "error": "Already reading."}
        if spelling not in SPELLINGS:
            return {"ok": False, "error": "Choose Modern Twi or Basel Twi 1879."}
        tesseract = find_tesseract(self._settings.get("tesseract", ""))
        if not tesseract:
            return {"ok": False, "error": "Tesseract was not found. Install it, or set its location in Settings."}
        model = SPELLINGS[spelling]["model"]
        if not (MODELS / f"{model}.traineddata").exists():
            return {"ok": False, "error": f"The {model} model is missing from {MODELS}."}
        inputs = collect_inputs(paths)
        if not inputs:
            return {"ok": False, "error": "No PDFs or images were found in what you chose."}
        try:   # Check the page choice before starting, so a typo is shown at once.
            total = len(list_pages(inputs))
            choose_pages(page_mode, custom, total)
        except ValueError as error:
            return {"ok": False, "error": str(error)}
        except Exception as error:
            return {"ok": False, "error": f"Could not open the files: {error}"}
        self._busy = True
        self._cancel = threading.Event()
        self._spelling = spelling
        if len(paths) == 1 and Path(paths[0]).is_dir():
            self._source_name = Path(paths[0]).name   # A folder: name the results after it.
        else:
            self._source_name = inputs[0].name if len(inputs) == 1 else f"{len(inputs)} files"
        threading.Thread(target=self._read_all, args=(inputs, spelling, tesseract, page_mode, custom), daemon=True).start()
        return {"ok": True}

    def _report(self, function: str, *args) -> None:
        if self._window:   # Called from reading threads; evaluate_js is safe from any thread.
            self._window.evaluate_js(f"{function}({', '.join(json.dumps(a) for a in args)})")

    def cancel(self) -> None:
        """Stop reading. Pages already read are kept."""
        self._cancel.set()
        with self._lock:
            for proc in self._procs:
                proc.terminate()

    def _tesseract(self, tesseract: str, image: Path | None, model: str, psm: int,
                   tessdata: Path = MODELS, data: bytes | None = None) -> str:
        """Read one page image and return its text in NFC form (as ocr.py does).

        Give either ``image`` (a file) or ``data`` (the image's bytes, sent to
        Tesseract directly; used on Windows, where it may not open file paths
        that contain letters such as ɛ or ɔ).
        """
        source = "stdin" if data is not None else str(image)
        proc = subprocess.Popen(
            [tesseract, source, "stdout", "-l", model, "--tessdata-dir", str(tessdata), "--psm", str(psm)],
            stdin=subprocess.PIPE if data is not None else None,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env=dict(os.environ, OMP_THREAD_LIMIT="1"),   # One core each; pages run side by side.
            **NO_WINDOW,
        )
        with self._lock:
            self._procs.add(proc)
        try:
            out, err = proc.communicate(input=data)
        finally:
            with self._lock:
                self._procs.discard(proc)
        if self._cancel.is_set():
            raise Cancelled()
        err_text = err.decode("utf-8", errors="replace").strip()
        if proc.returncode != 0:
            raise RuntimeError(err_text.splitlines()[-1] if err_text else "Tesseract stopped with an error.")
        return unicodedata.normalize("NFC", out.decode("utf-8", errors="replace"))

    def _read_one(self, index: int, page: dict, tesseract: str, settings: dict, correct, old_style: bool,
                  tessdata: Path) -> dict:
        """Read one page. A PDF page is drawn to a temporary PNG, read, and the PNG deleted."""
        if self._cancel.is_set():
            raise Cancelled()
        temp, data, image = None, None, None
        if IS_WINDOWS:   # Send the image itself, so no file path is involved.
            if "file" in page:
                data = Path(page["file"]).read_bytes()
            else:
                buf = io.BytesIO()
                render_page(page).convert("L").save(buf, format="PNG", compress_level=1)
                data = buf.getvalue()
        elif "file" in page:
            image = page["file"]
        else:
            temp = Path(self._tmp.name) / f"page-{index:05d}.png"
            # Grey, as Tesseract would make it anyway: the same text, a smaller file to write and read.
            render_page(page).convert("L").save(temp, compress_level=1)
            image = temp
        try:
            text = self._tesseract(tesseract, image, settings["model"], settings["psm"], tessdata, data)
        finally:
            if temp:
                temp.unlink(missing_ok=True)
        if correct:
            text = correct(text)
        if old_style:
            text = orthography.cleanup_ocr(text)
        return {
            **page, "text": text.rstrip() + "\n", "error": None,
            "modern": orthography.to_modern(text).rstrip() + "\n" if old_style else None,
        }

    def _read_all(self, inputs: list[Path], spelling: str, tesseract: str, page_mode: str = "all", custom: str = "") -> None:
        settings = SPELLINGS[spelling]
        old_style = spelling == "basel1879"
        fix_il = self._settings.get("fix_il", True) and not old_style
        try:
            self._report("onProgress", 0, 0, "Opening…")
            correct = load_corrector() if fix_il else None
            tessdata, model_label, notes = MODELS, settings["model"], []
            if self._settings.get("fast", True):
                self._report("onProgress", 0, 0, "Preparing the fast model…")
                folder = fast_models(tesseract, settings["model"])
                if folder:
                    tessdata, model_label = folder, f"{settings['model']} (fast)"
                else:
                    notes.append("Fast reading was not available, so pages were read with the full model.")
            pages = list_pages(inputs)
            wanted = set(choose_pages(page_mode, custom, len(pages)))
            pages = [page for page in pages if page["seq"] in wanted]
            total = len(pages)
            results: list[dict | None] = [None] * total
            failed: list[str] = []
            done = 0
            self._report("onProgress", 0, total, f"Reading {total} page{'s' if total != 1 else ''}…")
            started = time.monotonic()
            with ThreadPoolExecutor(max_workers=WORKERS) as pool:
                futures = {pool.submit(self._read_one, i, page, tesseract, settings, correct, old_style, tessdata): i
                           for i, page in enumerate(pages)}
                for future in as_completed(futures):
                    i = futures[future]
                    try:
                        results[i] = future.result()
                    except Cancelled:
                        continue
                    except Exception as error:   # Keep going; the page is left empty to type in.
                        failed.append(pages[i]["name"])
                        results[i] = {**pages[i], "text": "", "modern": "" if old_style else None, "error": str(error)}
                    done += 1
                    if not self._cancel.is_set():
                        self._report("onProgress", done, total, f"Read {done} of {total} pages…")
            kept = [page for page in results if page is not None]
            if not kept:
                self._report("onError", "no pages were read." if self._cancel.is_set() else "there were no pages to read.")
                return
            if len(failed) == len(kept):   # Every page failed: Tesseract itself is not working.
                self._report("onError", f"Tesseract could not read any page. {kept[0]['error']}")
                return
            if self._cancel.is_set():
                notes.append(f"Stopped: {len(kept)} of {total} pages read.")
            if failed:
                shown = ", ".join(failed[:5]) + (f" and {len(failed) - 5} more" if len(failed) > 5 else "")
                notes.append(f"Could not read {shown}; those pages are empty.")
            self._pages = kept
            self._report("onPages", [page["seq"] for page in kept])
            self._report("onDone", len(kept), self._source_name, settings["label"],
                         model_label, bool(correct), old_style, " ".join(notes), round(time.monotonic() - started))
        except Exception as error:   # Shown in the window instead of crashing.
            self._report("onError", str(error))
        finally:
            self._busy = False

    # Results
    def page(self, index: int) -> dict:
        page = self._pages[index]
        return {"name": page["name"], "image": preview(page), "text": page["text"],
                "modern": page["modern"], "error": page.get("error"), "index": index, "count": len(self._pages)}

    def update_text(self, index: int, which: str, text: str) -> None:
        """Keep a correction the user typed into the text box."""
        if which in {"text", "modern"} and 0 <= index < len(self._pages):
            self._pages[index][which] = text

    def default_name(self) -> str:
        """The file name the results start with: the PDF's or folder's name."""
        return clean_name(Path(self._source_name).stem) or "page"

    def save(self, index: int | None = None, name: str = "", start: int = 1) -> dict:
        """Save one page (index) or every page as name_001.txt, name_002.txt, ...

        Each file is numbered by its page in the PDF, counted from ``start``, so
        reading only odd pages saves name_001, name_003, ... It goes in a folder called
        ``name`` inside the output folder. A Basel Twi 1879 page also gets name_001.modern.txt.
        """
        name = clean_name(name) or self.default_name()
        start = max(0, int(start or 0))
        last = max((page.get("seq", i + 1) for i, page in enumerate(self._pages)), default=1)
        width = max(3, len(str(start + last - 1)))
        out = Path(self._settings["output"]) / name
        out.mkdir(parents=True, exist_ok=True)
        chosen = range(len(self._pages)) if index is None else [index]
        written: list[str] = []
        for i in chosen:
            page = self._pages[i]
            stem = f"{name}_{start + page.get('seq', i + 1) - 1:0{width}d}"
            (out / f"{stem}.txt").write_text(page["text"], encoding="utf-8")
            written.append(f"{stem}.txt")
            if page["modern"] is not None and self._settings.get("modern_copy", True):
                (out / f"{stem}.modern.txt").write_text(page["modern"], encoding="utf-8")
                written.append(f"{stem}.modern.txt")
        return {"folder": str(out), "files": len(written), "first": written[0] if written else ""}

    def reveal(self, folder: str) -> None:
        """Open the folder in Finder (Mac) or File Explorer (Windows)."""
        if IS_WINDOWS:
            os.startfile(folder)   # noqa: S606  (opens the folder in File Explorer)
        elif IS_MAC:
            subprocess.run(["open", folder])
        else:
            subprocess.run(["xdg-open", folder])

    def open_link(self, url: str) -> None:
        if url.startswith("https://github.com/ashantiowusu-brafi/"):
            import webbrowser
            webbrowser.open(url)


def bind_drop(window, api: Api) -> None:
    """Accept PDFs and images dropped on the drop area."""
    from webview.dom import DOMEventHandler

    def on_drop(event):
        paths = [f.get("pywebviewFullPath") for f in event["dataTransfer"].get("files", [])]
        paths = [p for p in paths if p]
        if paths:
            window.evaluate_js(f"onDropped({json.dumps(paths)})")

    zone = window.dom.get_element("#drop")
    if zone:
        zone.events.dragover += DOMEventHandler(lambda e: None, True, True)
        zone.events.drop += DOMEventHandler(on_drop, True, True)


def unblock_own_files() -> None:
    """Windows: remove the "downloaded from the internet" mark from the app's own files.

    Windows marks downloaded files, and unzipping passes the mark to every file
    inside. .NET then refuses to load the window library's components
    (pythonnet's Python.Runtime.dll, WebView2), and the app stops with "Failed to
    resolve Python.Runtime.Loader.Initialize". The mark is a hidden
    Zone.Identifier stream next to each file; deleting it is what "Unblock"
    in a file's Properties does.
    """
    for path in APP_DIR.rglob("*"):
        if path.suffix.lower() in {".dll", ".exe", ".pyd"}:
            try:
                os.remove(f"{path}:Zone.Identifier")
            except OSError:
                pass   # Not marked, or not allowed: nothing to do.


def main() -> None:
    if IS_WINDOWS and FROZEN:
        unblock_own_files()
    if "--check" in sys.argv:   # Print what the app can find, without opening a window.
        status = Api().status()
        print(json.dumps({k: v for k, v in status.items() if k != "settings"}, indent=2))
        return
    debug = "--debug" in sys.argv   # Show errors and allow Inspect Element in the window.
    if debug:
        import faulthandler
        import logging
        faulthandler.enable()
        logging.basicConfig(level=logging.DEBUG)
        print(f"UI file: {UI_FILE} (exists: {UI_FILE.exists()})", flush=True)
    import webview
    api = Api()
    width, height = 1100, 680   # The main view fits in this without scrolling.
    try:   # Never open taller or wider than the screen (leave room for the menu bar and Dock).
        screen = webview.screens[0]
        width, height = min(width, screen.width - 40), min(height, screen.height - 80)
    except Exception:
        pass
    window = webview.create_window(
        "Twi OCR", url=str(UI_FILE), js_api=api, width=width, height=height, min_size=(900, 600),
        background_color="#EDEDF0",
    )
    api._window = window
    webview.start(bind_drop, (window, api), debug=debug)
    if debug:
        print("The window closed.", flush=True)


if __name__ == "__main__":
    main()
