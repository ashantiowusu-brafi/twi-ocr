"""Convert the answer key's quote marks to the book's printed style.

Bu Me Bɛ prints curly double quotes for quotations (“like this”) and a curly
apostrophe inside words (n’anim). The typed key mixes straight " and ', single
curly ‘ ’, and curly ’. This script converts the Twi column to the book's
style and lists anything whose role is unclear instead of guessing.

Rules, applied to each proverb:
    letter ' letter  or  letter ’ letter   -> ’   (apostrophe, as in n’anim)
    ‘ or an opening ' (after a space)      -> “
    closing ’ or ' after an opening quote  -> ”
    straight "                             -> “ or ” by position
    a ’ or ' that closes nothing           -> left as is, listed for review

Input:   private/Akan_Proverbs.xlsx (Twi text in the second column)
Outputs: private/Akan_Proverbs.xlsx          converted key
         private/Akan_Proverbs_before_quotes.xlsx  backup of the original
         private/quote_review.csv            marks left unchanged, to check

Usage:
    python tools/answer_key/fix_key_quotes.py
"""

import csv
import shutil
from pathlib import Path

from openpyxl import load_workbook

KEY = Path("private/Akan_Proverbs.xlsx")
BACKUP = Path("private/Akan_Proverbs_before_quotes.xlsx")
REVIEW = Path("private/quote_review.csv")
TWI_COLUMN = 2  # Column B
OPENING_CONTEXT = " ([{—–-"  # Characters after which a quote mark opens.


def convert(text: str) -> tuple[str, list[int]]:
    """Return the text in book style and positions of marks left unchanged."""
    chars = list(text)
    unclear: list[int] = []
    quote_open = False
    for i, ch in enumerate(chars):
        before = chars[i - 1] if i > 0 else " "
        after = chars[i + 1] if i + 1 < len(chars) else " "
        if ch not in "'’‘\"“”":
            continue
        if ch in "'’" and before.isalpha() and after.isalpha():
            chars[i] = "’"                       # Apostrophe inside a word.
        elif ch in "‘“" or (ch in "'\"" and before in OPENING_CONTEXT):
            chars[i] = "“"
            quote_open = True
        elif ch == "\"" or (ch in "'’”" and quote_open):
            chars[i] = "”"
            quote_open = False
        else:
            unclear.append(i)                    # Closes nothing: leave it.
    return "".join(chars), unclear


def main() -> None:
    """Convert the key's Twi column and report what changed."""
    shutil.copy(KEY, BACKUP)
    workbook = load_workbook(KEY)
    sheet = workbook.active

    changed, review_rows = 0, []
    for row in range(2, sheet.max_row + 1):
        cell = sheet.cell(row, TWI_COLUMN)
        if not isinstance(cell.value, str):
            continue
        new, unclear = convert(cell.value)
        if new != cell.value:
            cell.value = new
            changed += 1
        for i in unclear:
            review_rows.append({
                "number": sheet.cell(row, 1).value,
                "mark": new[i],
                "context": new[max(0, i - 15):i + 15],
            })

    workbook.save(KEY)
    with REVIEW.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["number", "mark", "context"])
        writer.writeheader()
        writer.writerows(review_rows)

    print(f"Proverbs changed: {changed}")
    print(f"Marks left for review: {len(review_rows)} (see {REVIEW})")
    print(f"Backup of the original key: {BACKUP}")


if __name__ == "__main__":
    main()
