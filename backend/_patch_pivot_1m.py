#!/usr/bin/env python3
"""One-off patch: add pivot_break to the 1-min precision path in intraday.py."""
import sys

PATH = "src/intraday.py"
content = open(PATH, "rb").read()

OLD = b'if brk["type"] in ("domination", "candle-size"):\r'
NEW = b'if brk["type"] in ("domination", "candle-size", "pivot_break"):\r'

count = content.count(OLD)
print(f"Matches found: {count}")
if count != 1:
    print(f"ERROR: expected exactly 1 match, got {count}")
    sys.exit(1)

content = content.replace(OLD, NEW)
open(PATH, "wb").write(content)
print("Patched OK")
