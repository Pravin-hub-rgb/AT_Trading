"""Give every dropdown book a numeric code, grouped by position class.

The owner asked for codes like 111, 112, 113 so the list can be referred to
without pasting long book names. The grouping is not cosmetic here: this repo
has spent weeks being confused about which books hold one position and which
hold many, and BASELINE.md is explicit that comparing a serial book against a
multi book is off by a hundred R. So the first digit carries that fact.

  1xx   max_positions = 0, multi - may hold several at once
  2xx   max_positions = 1, serial - one position at a time

The class is read from the registry params, never from the name. Several books
here carry "sig" in the name and are multi, which is the exact mis-filing bug
exp_results_export.py already had to fix for itself.

The code is rendered as a prefix on the label, so it is what the owner sees in
the dropdown, and it is also stored on the option so anything selecting a book
by code does not have to parse the label.

Line-scoped by design, and indent-preserving: entries sit at two different
indents in books.ts (a group of five is nested one level deeper) and an earlier
attempt that rewrote a window of surrounding text corrupted the file. This only
inserts one line after an id line and rewrites the digits on the label line.
"""
from __future__ import annotations

import io
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tests"))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parents[1] / "backend"))

from experiment_registry import EXPERIMENTS  # noqa: E402

BOOKS_TS = HERE.parents[1] / "frontend" / "src" / "lib" / "books.ts"
ALIAS = {"fsent_champ_long_atr_low": "fsent_champ_long_mode_atr_low"}

ID_LINE = re.compile(r'^(\s+)id: "([a-z0-9_]+)",$')
LABEL_LINE = re.compile(r'^(\s*label: )"(.*)$')


def is_serial(bid):
    key = ALIAS.get(bid, bid)
    cfg = EXPERIMENTS.get(key)
    if not isinstance(cfg, dict):
        return None
    return (cfg.get("params") or {}).get("max_positions", 0) == 1


def main() -> int:
    apply = "--apply" in sys.argv
    src = io.open(BOOKS_TS, encoding="utf-8").read()
    lines = src.split("\n")

    ids = [ID_LINE.match(ln).group(2) for ln in lines if ID_LINE.match(ln)]
    multi = [b for b in ids if is_serial(b) is False]
    serial = [b for b in ids if is_serial(b) is True]
    unknown = [b for b in ids if is_serial(b) is None]

    codes = {}
    for n, bid in enumerate(multi, 101):
        codes[bid] = str(n)
    for n, bid in enumerate(serial, 201):
        codes[bid] = str(n)

    print("multi  (1xx): %d" % len(multi))
    for bid in multi:
        print("   %s  %s" % (codes[bid], bid))
    print("serial (2xx): %d" % len(serial))
    for bid in serial:
        print("   %s  %s" % (codes[bid], bid))
    if unknown:
        print("unclassified (no registry pins, left uncoded): %s" % unknown)
    print()
    print("mode: %s" % ("APPLY" if apply else "DRY RUN"))
    if not apply:
        print("DRY RUN. Pass --apply to write.")
        return 0

    out = []
    cur = None
    added = 0
    for ln in lines:
        m = ID_LINE.match(ln)
        if m and m.group(2) in codes:
            cur = m.group(2)
            out.append(ln)
            out.append('%scode: "%s",' % (m.group(1), codes[cur]))
            added += 1
            continue
        lm = LABEL_LINE.match(ln)
        if lm and cur in codes and not lm.group(2).startswith(codes[cur] + " "):
            body = lm.group(2)
            # body still carries the string's closing quote and the object's
            # trailing comma, so the prefix goes inside it rather than after.
            assert body.endswith('",'), "label line does not close: %r" % body
            inner = body[:-2]
            out.append('%s"%s - %s",' % (lm.group(1), codes[cur], inner))
            continue
        out.append(ln)

    text = "\n".join(out)
    if "code?: string;" not in text:
        text = text.replace(
            "export interface BookOption {\n  id: BookId;\n  label: string;",
            "export interface BookOption {\n  id: BookId;\n"
            "  /** 1xx = multi (max_positions 0), 2xx = serial (max_positions 1). */\n"
            "  code?: string;\n  label: string;")
    io.open(BOOKS_TS, "w", encoding="utf-8").write(text)
    print("wrote %s - %d codes" % (BOOKS_TS.name, added))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())