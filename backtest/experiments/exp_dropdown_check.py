"""Join the three lists that decide whether a dropdown book can actually run.

THE JOIN THAT WAS MISSING
-------------------------
A book is only runnable if the same name appears in three places:

  books.ts          the frontend dropdown - what the owner sees and picks
  BTC_VERSIONS      btc_routes.py        - the allowlist that rejects unknown
                                           versions with a 400
  a dispatch branch btc_routes.py        - the code that actually runs it

These drifted. On 2026-10-16 the dropdown listed 16 books, BTC_VERSIONS knew 11,
and the dispatch knew 10. Selecting fsent_champ_long_htf15_htffs returned
"version must be one of [...]" while that book had a registry pin, a monthly
breakdown, a row in the pick scorecard and a code in the dropdown.

Nothing in either direction caught it. books.ts is a TypeScript file that
nobody diffs against Python, and the version list is a hand-maintained list in a
2465-line route module. Every individual artefact was correct. The seam between
them was never written down, so it was never checked.

The same class of failure removed four champion books from the dropdown today -
they were in books.ts and in BTC_VERSIONS and had a dispatch branch, but had no
registry pin and negative out-of-sample numbers. This check cannot see that; it
only asserts the three lists agree, which is the half that broke loudly.

Output: exit 0 if every dropdown book is runnable, 1 otherwise.
"""
from __future__ import annotations

import io
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
# HERE is <repo>/backtest/experiments, so three parents up is the repo root.
ROOT = HERE.parents[1]
BOOKS_TS = ROOT / "frontend" / "src" / "lib" / "books.ts"
ROUTES = ROOT / "backend" / "src" / "btc" / "btc_routes.py"
API_TS = ROOT / "frontend" / "src" / "lib" / "btcApi.ts"

sys.path.insert(0, str(ROOT / "backtest" / "tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))


def dropdown_books():
    """(code, id, version_sent) for every entry in books.ts, indent-agnostic."""
    ui = io.open(BOOKS_TS, encoding="utf-8").read()
    out = []
    cur = None
    for ln in ui.split("\n"):
        mid = re.match(r'^\s+id: "([a-z0-9_]+)"', ln)
        if mid:
            cur = mid.group(1)
        mcode = re.match(r'^\s+code: "(\d+)"', ln)
        if mcode and cur:
            out.append([mcode.group(1), cur, None])
        mver = re.match(r'^\s+version: "([^"]+)"', ln)
        if mver and out and out[-1][1] == cur and out[-1][2] is None:
            out[-1][2] = mver.group(1)
    return out


def main() -> int:
    src = io.open(ROUTES, encoding="utf-8").read()
    btc = set(re.findall(r'"([^"]+)"',
                         re.search(r"BTC_VERSIONS = \[(.*?)\]", src, re.S).group(1)))
    standalone = set(re.findall(
        r'"([^"]+)"',
        re.search(r"STANDALONE_HTF_LTF_VERSIONS = \{(.*?)\}", src, re.S).group(1)))
    dispatched = set(re.findall(r'(?:elif|if) version == "([a-z0-9_]+)"', src))
    api = io.open(API_TS, encoding="utf-8").read()
    ts_type = set(re.findall(
        r'"([^"]+)"',
        re.search(r"export type BtcVersion\s*=\s*(.*?);", api, re.S).group(1)))

    books = dropdown_books()
    print("=" * 76)
    print("DROPDOWN / BACKEND JOIN")
    print("=" * 76)
    print("books.ts entries : %d" % len(books))
    print("BTC_VERSIONS     : %d" % len(btc))
    print("standalone set   : %d" % len(standalone))
    print("dispatch branches: %d" % len(dispatched))
    print("TS BtcVersion    : %d" % len(ts_type))
    print()
    print("%-6s %-34s %-9s %-11s %-9s" % ("code", "book", "BTC_VER", "standalone", "branch"))
    print("-" * 76)
    bad = []
    for code, bid, ver in books:
        sent = ver or bid
        row = []
        for label, have in (("BTC_VER", sent in btc), ("standalone", sent in standalone),
                            ("branch", sent in dispatched)):
            row.append("yes" if have else "** NO **")
            if not have:
                bad.append((code, bid, sent, label))
        print("%-6s %-34s %-9s %-11s %-9s" % (code, bid, row[0], row[1], row[2]))
    print()
    if bad:
        print("RESULT: FAIL - %d dropdown books cannot be run" % len({b[1] for b in bad}))
        for code, bid, sent, what in bad:
            print("   %s %-34s missing %s" % (code, bid, what))
        return 1
    print("RESULT: PASS - every dropdown book routes to a dispatch branch")
    extra = sorted(btc - {b[2] or b[1] for b in books})
    if extra:
        print()
        print("runnable but not on the dropdown (%d): %s" % (len(extra), extra))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())