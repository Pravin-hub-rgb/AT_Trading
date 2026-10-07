"""exp_unpin_reference - blank the pins on status="reference" books.

WHY
===
`exp_pinrefresh.py` states the rule this repo already follows: a reference book's
whole point is that its number must not be quotable, and "a pin is the most
quotable thing in this repo", so `pins: None` and `status: reference` are the
same statement. 41 books carry `status: reference`; 14 already have `pins: None`.
The other 27 carry pins anyway, and after C17 those pins are also STALE - e.g.
gap_inert_event_shift still reads 499/+239.12, which is the pre-C17 champion
number, so `exp_pinverify.py` reported it as a mismatch.

Both problems have the same fix and it is a deletion, not a rewrite: a reference
book measured LARGE is a measured leak or a measured dead end, and keeping a
re-derived pin for it would make the leak look like a reproducible edge. The
measurement stays in git history and in docs/method/C17_WINDOW_END_CAUSALITY.md.

GUARDS
======
* refuses any book that is not `status: reference`
* refuses a book that has no pins (nothing to do, and a count that silently
  includes no-ops is a count you cannot trust)
* resolves each key to exactly ONE registry file with exactly ONE pins literal,
  and asserts the value it is about to replace is the pin the card read
* dry run by default; `--write` performs the edit and re-imports to verify

Run:  cd backtest/tests
       python -u exp_unpin_reference.py
       python -u exp_unpin_reference.py --write
"""
import argparse
import importlib
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

REGDIR = ROOT / "backtest/tests/registry"
ENTRY = re.compile(r'^ {4}"(?P<k>[^"]+)":\s*\{', re.M)
PINS = re.compile(r'"pins"\s*:\s*(\{[^}]*\}|None)')


def book_spans(text):
    ms = list(ENTRY.finditer(text))
    return {m.group("k"): (m.start(),
                           ms[i + 1].start() if i + 1 < len(ms) else len(text))
            for i, m in enumerate(ms)}


def blank_in_text(text, key, current_literal):
    spans = book_spans(text)
    if key not in spans:
        return None, "key not found in this file"
    seg = text[spans[key][0]:spans[key][1]]
    hits = list(PINS.finditer(seg))
    if len(hits) != 1:
        return None, "expected 1 pins literal in span, found %d" % len(hits)
    h = hits[0]
    if h.group(1).strip() != current_literal.strip():
        return None, "pins literal is %r but the registry reported %r" % (
            h.group(1).strip(), current_literal.strip())
    s = spans[key][0] + h.start()
    e = spans[key][0] + h.end()
    new = text[:s] + '"pins": None' + text[e:]
    # only the value changed, so the file length changes by a predictable amount
    return new, '"pins": {%s} -> None' % h.group(1).strip()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--book", action="append", default=[])
    a = ap.parse_args(argv)

    import experiment_registry as reg
    refs = [k for k, v in reg.EXPERIMENTS.items()
            if isinstance(v, dict) and v.get("status") == "reference"]
    targets = [k for k in (a.book or refs)
               if (reg.EXPERIMENTS.get(k, {}).get("pins") or {}).get("n")]

    print("=" * 78)
    print("UNPIN REFERENCE BOOKS - %d to blank of %d reference books   (%s)"
          % (len(targets), len(refs),
             "WRITING" if a.write else "dry run, nothing written"))
    print("=" * 78)
    if not targets:
        print("nothing to do - every reference book is already unpinned")
        return 0

    files = {p: p.read_text(encoding="utf-8") for p in sorted(REGDIR.glob("*.py"))}
    edited, failed = {}, []
    for key in sorted(targets):
        if reg.EXPERIMENTS[key].get("status") != "reference":
            failed.append((key, "not status=reference - refusing"))
            continue
        hits = [p for p, t in files.items() if key in book_spans(t)]
        if len(hits) != 1:
            failed.append((key, "resolves to %d files" % len(hits)))
            continue
        path = hits[0]
        cur = edited.get(path, files[path])
        lit = PINS.search(cur[slice(*book_spans(cur)[key])])
        if not lit:
            failed.append((key, "no pins literal"))
            continue
        out, info = blank_in_text(cur, key, lit.group(1))
        if out is None:
            failed.append((key, info))
            continue
        if out != cur:
            edited[path] = out
            print("  %-44s %s   [%s]" % (key, info, path.name))

    if failed:
        print("\nFAILED (%d):" % len(failed))
        for k, why in failed:
            print("    %-44s %s" % (k, why))
        return 1
    print("\n%d book(s) to blank across %d file(s)" % (len(targets), len(edited)))
    if not a.write:
        print("DRY RUN. Re-run with --write.")
        return 0

    for path, text in edited.items():
        path.write_text(text, encoding="utf-8")
    # Re-import from DISK, not importlib.reload. experiment_registry is a package
    # whose data lives in registry/*.py submodules; reloading only the package
    # re-imports registry/__init__.py, which does `from .signal import *` out of
    # modules still sitting in sys.modules. The first version of this tool
    # reported all 27 books as still pinned when they had been blanked correctly,
    # which is the worst kind of wrong for a check that exists to confirm a
    # deletion.
    for m in [k for k in list(sys.modules)
              if k == "experiment_registry" or k == "registry" or k.startswith("registry.")]:
        del sys.modules[m]
    import experiment_registry as reg2
    left = [k for k, v in reg2.EXPERIMENTS.items()
            if isinstance(v, dict) and v.get("status") == "reference"
            and (v.get("pins") or {}).get("n")]
    total_ref = sum(1 for v in reg2.EXPERIMENTS.values()
                    if isinstance(v, dict) and v.get("status") == "reference")
    print("wrote %d file(s); registry re-imported" % len(edited))
    print("reference books: %d total, %d still pinned -> %s"
          % (total_ref, len(left), left if left else "none"))
    return 1 if left else 0


if __name__ == "__main__":
    raise SystemExit(main())
