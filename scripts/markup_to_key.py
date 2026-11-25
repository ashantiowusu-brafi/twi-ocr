"""Turn quick-typing markup into a key file: "_" after a letter adds the line below (U+0332), "w^" gives w̌.

Usage: python scripts/markup_to_key.py page.mk   # writes page.gt.txt
"""
import sys, unicodedata, pathlib
for p in sys.argv[1:]:
    src = pathlib.Path(p).read_text(encoding="utf-8")
    out = src.replace("w^", "w̌").replace("W^", "W̌").replace("_", "̲")
    pathlib.Path(p.replace(".mk", ".gt.txt")).write_text(unicodedata.normalize("NFC", out), encoding="utf-8")
