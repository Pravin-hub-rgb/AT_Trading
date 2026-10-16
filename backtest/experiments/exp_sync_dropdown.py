"""Sync the frontend dropdown's numbers with the registry pins.

books.ts carries each book's IS/OOS figures in two places: hardcoded inside the
`label` string a human reads in the dropdown, and in a `measured` object the code
can read. Both had drifted from the pins.

Two problems, one cosmetic and one structural:

1. Seven trade counts were one high - they predate the repin that started
   dropping open trades. A trade with no exit has no realised R, so counting it
   inflated n and diluted R-per-trade.

2. `fsent_champ_long_atr_low` does not exist in the registry. The real key is
   `fsent_champ_long_mode_atr_low`. The entry carries its own inline config so
   the chart still renders, which is exactly why nobody noticed - but anyone who
   read the dropdown id and went looking for that book in the registry found
   nothing. The alias below keeps the frontend id (other components reference
   it) while recording that it is not the registry key.

The underlying disease is the one this repo already fixed twice, in prose and
then in pins: a number written down by hand goes stale the moment the engine
moves, and nothing catches it because nothing checks it. These counts were wrong
by one for weeks and the page rendered happily the whole time.

An earlier version of this edited a window of surrounding text and corrupted
books.ts - the window reached past the end of one entry into the next. This
version is strictly LINE SCOPED: it only rewrites the figures inside the label
on the label line, and the numbers inside the measured object on the measured
line. Nothing else on either line is touched.

Run with --apply to write. Without it, reports only.
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

# frontend id -> registry key, where the two differ
ALIAS = {"fsent_champ_long_atr_low": "fsent_champ_long_mode_atr_low"}

ID_RE = re.compile(r'id:\s*"([a-z0-9_]+)"')
MEAS_RE = re.compile(r"(isN:\s*)(\d+)(,\s*isNet:\s*)([\d.]+)(,\s*oosN:\s*)(\d+)(,\s*oosNet:\s*)([\d.]+)")
LAB_RE = re.compile(r"(IS\s+)(\d+)(t\s*\+)([\d.]+)(R\s*\|\s*OOS\s+)(\d+)(t\s*\+)([\d.]+)(R)")


def main() -> int:
    apply = "--apply" in sys.argv
    lines = io.open(BOOKS_TS, encoding="utf-8").read().split("\n")

    cur = None
    out = []
    touched = []
    for ln in lines:
        mid = ID_RE.search(ln)
        if mid:
            cur = mid.group(1)
        reg_id = ALIAS.get(cur, cur)
        cfg = EXPERIMENTS.get(reg_id) if cur else None
        p = cfg.get("pins") if isinstance(cfg, dict) else None
        if not p:
            out.append(ln)
            continue

        new = ln
        if "measured:" in ln:
            m = MEAS_RE.search(ln)
            if m and (int(m.group(2)) != p["n"] or int(m.group(6)) != p["oos_n"]
                      or abs(float(m.group(4)) - p["net"]) > 0.005
                      or abs(float(m.group(8)) - p["oos_net"]) > 0.005):
                new = MEAS_RE.sub(
                    lambda _m: "%s%d%s%.2f%s%d%s%.2f" % (
                        _m.group(1), p["n"], _m.group(3), p["net"],
                        _m.group(5), p["oos_n"], _m.group(7), p["oos_net"]),
                    new, count=1)
                touched.append((cur, "measured", m.group(0), new[max(0, new.find("measured")):]))
        elif "label:" in ln:
            m = LAB_RE.search(new)
            if m and (int(m.group(2)) != p["n"] or int(m.group(6)) != p["oos_n"]):
                new = LAB_RE.sub(
                    lambda _m: "%s%d%s%.1f%s%d%s%.1f%s" % (
                        _m.group(1), p["n"], _m.group(3), p["net"],
                        _m.group(5), p["oos_n"], _m.group(7), p["oos_net"],
                        _m.group(9)),
                    new, count=1)
                touched.append((cur, "label", m.group(0), LAB_RE.search(new).group(0)))
        out.append(new)

    print("lines carrying registry figures that were wrong : %d" % len(touched))
    print("mode                                              : %s" % ("APPLY" if apply else "DRY RUN"))
    for bid, kind, old, new in touched:
        print("  %-34s %-9s %s" % (bid, kind, old[:56]))
    if not apply:
        print("\nDRY RUN. Pass --apply to write.")
        return 0
    io.open(BOOKS_TS, "w", encoding="utf-8").write("\n".join(out))
    print("\nwrote %s" % BOOKS_TS.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())