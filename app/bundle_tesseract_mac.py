"""Copy Tesseract and the libraries it needs into one folder for the Mac app.

Homebrew's tesseract program loads about a dozen libraries from /opt/homebrew
(Leptonica, libpng, libtiff, libarchive ...). This copies the program, its
combine_tessdata tool (for the app's faster reading) and every library they
load outside macOS itself into OUT/ and OUT/libs/, rewrites each file to look
for its libraries in libs/ next to the program (install_name_tool), and signs
everything again (codesign; Apple Silicon will not run a changed, unsigned
file). The folder then works on a Mac without Homebrew.

Uses only Apple's command line tools (otool, install_name_tool, codesign).
Language files are not copied: the app passes its own models folder.

Usage (build_mac.sh runs this):
    python app/bundle_tesseract_mac.py app/build/tesseract
"""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

SYSTEM_PREFIXES = ("/usr/lib/", "/System/")
LIB_REF = "@executable_path/libs/"


def run(*args: str) -> str:
    return subprocess.run(args, capture_output=True, text=True, check=True).stdout


def rpaths(path: Path) -> list[str]:
    """Return the LC_RPATH entries of a binary."""
    out = run("otool", "-l", str(path))
    return re.findall(r"cmd LC_RPATH\n\s+cmdsize \d+\n\s+path (.+?) \(offset", out)


def dependencies(path: Path) -> list[str]:
    """Return the libraries a binary loads, as written in it (otool -L)."""
    lines = run("otool", "-L", str(path)).splitlines()[1:]
    deps = [line.strip().split(" (")[0] for line in lines if line.strip()]
    own_id = run("otool", "-D", str(path)).splitlines()[1:]   # a library lists itself first
    return [d for d in deps if not own_id or d != own_id[0].strip()]


def resolve(ref: str, origin: Path) -> Path | None:
    """Turn a reference such as @rpath/libfoo.dylib into a real file, or None for system ones."""
    if ref.startswith(SYSTEM_PREFIXES):
        return None
    if ref.startswith("@loader_path/") or ref.startswith("@executable_path/"):
        candidate = origin.resolve().parent / ref.split("/", 1)[1]
        return candidate.resolve() if candidate.exists() else None
    if ref.startswith("@rpath/"):
        for rp in rpaths(origin):
            base = rp.replace("@loader_path", str(origin.resolve().parent))
            candidate = Path(base) / ref.split("/", 1)[1]
            if candidate.exists():
                return candidate.resolve()
        return None
    return Path(ref).resolve() if Path(ref).exists() else None


def main() -> None:
    if sys.platform != "darwin":
        raise SystemExit("This script is for macOS.")
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "app/build/tesseract")
    tesseract = shutil.which("tesseract")
    if not tesseract:
        raise SystemExit("tesseract not found. Install it with: brew install tesseract")
    programs = [Path(tesseract).resolve()]
    combine = Path(tesseract).with_name("combine_tessdata")
    if combine.exists():
        programs.append(combine.resolve())

    if out.exists():
        shutil.rmtree(out)
    (out / "libs").mkdir(parents=True)

    # Walk every library the programs load, and the libraries those load.
    copied: dict[Path, Path] = {}      # original -> copy
    refs: dict[Path, list[tuple[str, Path]]] = {}   # copy -> [(reference as written, original)]
    queue = [(p, out / p.name) for p in programs]
    while queue:
        original, copy = queue.pop()
        if original in copied:
            continue
        shutil.copy2(original, copy)
        os.chmod(copy, 0o755)
        copied[original] = copy
        refs[copy] = []
        for ref in dependencies(original):
            target = resolve(ref, original)
            if target is None:
                continue
            refs[copy].append((ref, target))
            if target not in copied:
                queue.append((target, out / "libs" / target.name))

    # Point every file at the copies in libs/, then sign them again.
    for copy, deps in refs.items():
        args = ["install_name_tool"]
        if copy.parent.name == "libs":
            args += ["-id", LIB_REF + copy.name]
        for ref, target in deps:
            args += ["-change", ref, LIB_REF + copied[target].name]
        for rp in rpaths(copy):
            args += ["-delete_rpath", rp]
        if len(args) > 1:
            subprocess.run(args + [str(copy)], check=True, capture_output=True)
    for copy in copied.values():
        subprocess.run(["codesign", "--force", "--sign", "-", str(copy)], check=True, capture_output=True)

    # Check: nothing still points outside the folder, and the program runs.
    leftovers = [f"{c.name}: {d}" for c in copied.values() for d in dependencies(c)
                 if not d.startswith(SYSTEM_PREFIXES) and not d.startswith(LIB_REF)]
    if leftovers:
        raise SystemExit("Still pointing outside the folder:\n  " + "\n  ".join(leftovers))
    version = subprocess.run([str(out / "tesseract"), "--version"], capture_output=True, text=True,
                             env={"PATH": "/usr/bin:/bin"})
    if version.returncode != 0:
        raise SystemExit(f"The copied tesseract does not run:\n{version.stderr}")
    size = sum(f.stat().st_size for f in out.rglob("*") if f.is_file()) / 1e6
    print(f"Tesseract packed into {out}: {len(copied)} files, {size:.0f} MB.")
    print(version.stdout.splitlines()[0] if version.stdout else version.stderr.splitlines()[0])


if __name__ == "__main__":
    main()
