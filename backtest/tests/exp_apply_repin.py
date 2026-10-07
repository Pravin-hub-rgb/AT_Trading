"""exp_apply_repin - write the measured pins from _repin_stale.json into the registry.

This is the mutation step, deliberately separate from the measurement step
(exp_repin_stale.py) so a re-measure can never quietly rewrite the registry.

WHY VALUE SUBSTITUTION AND NOT BLOCK REPLACEMENT
================================================
The 215 pin literals in registry/*.py use 20 distinct line-wrapping shapes and
2 decimal places on some fields, 3 on others. Regenerating a literal would
normalise formatting across the whole file and bury a 187-book value change in
thousands of whitespace lines. Instead this rewrites ONLY the numeric value of
each key that actually changed, inside that book's own pins span. Layout,
key order, comments and every other field survive byte-for-byte.

SAFETY
======
* dry run by default; `--write` performs the edit
* a book is only touched if its key resolves to exactly ONE registry file and
  that file's span for the book contains exactly ONE `"pins"` literal
* every value substitution asserts it matched exactly once, so a duplicate key,
  a missing key or an ambiguous span is a hard failure, never a silent skip
* after writing, the registry is re-imported and compared against the card
* the old pin stays in _repin_stale.json, so history is not overwritten

Usage:
    cd backtest/tests
    python exp_apply_repin.py                       # dry run
    python exp_apply_repin.py --write --verify
"""
import argparse
import importlib
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend", ""):
    sys.path.insert(0, str(ROOT / p) if p else str(ROOT))

CARD = ROOT / "backtest/tests/_repin_stale.json"
REGDIR = ROOT / "backtest/tests/registry"

# A book entry in registry/*.py sits at four-space indent: `    "name": {`
ENTRY = re.compile(r'^ {4}"(?P<k>[^"]+)":\s*\{', re.M)
# A pin field inside a pins literal: `"net": 528.87,` (may be negative)
FIELD = re.compile(r'"(?P<k>[a-z_]+)"\s*:\s*(?P<v>-?\d+(?:\.\d+)?)')


def book_spans(text):
    """{book_key: (start, end)} over one registry file's entry region."""
    ms = list(ENTRY.finditer(text))
    out = {}
    for i, m in enumerate(ms):
        end = ms[i + 1].start() if i + 1 < len(ms) else len(text)
        out[m.group("k")] = (m.start(), end)
    return out


def locate(key, files):
    hits = []
    for path, text in files.items():
        span = book_spans(text).get(key)
        if span:
            hits.append((path, span))
    return hits


def pins_span(text, span):
    """(pins_start, pins_end) inside a book span, or None if not exactly one."""
    seg = text[span[0]:span[1]]
    hits = [m.start() for m in re.finditer(r'"pins"\s*:', seg)]
    if len(hits) != 1:
        return None, "expected exactly one \"pins\" in span, found %d" % len(hits)
    s = hits[0]
    b = seg.index("{", s)
    depth = 0
    for i in range(b, len(seg)):
        if seg[i] == "{":
            depth += 1
        elif seg[i] == "}":
            depth -= 1
            if depth == 0:
                return (span[0] + b, span[0] + i + 1), None
    return None, "unbalanced braces in pins literal"


def fmt(key, value):
    """Render a value the way the existing literal already renders that field."""
    cur = FIELD.search('"%s": %s' % (key, "0"))
    del cur
    return value


def apply_to_text(text, key, new_pin, old_pin):
    """Rewrite only the changed numeric values inside this book's pins literal.

    The span is resolved against the text handed in, NOT against a precomputed
    one: substituting a value can change the file length (24.64 -> 25.5), so a
    span captured before an earlier book in the same file was rewritten points
    at the wrong text and every assertion after it is meaningless.
    """
    spans = book_spans(text)
    if key not in spans:
        return None, "book key not found in this text"
    ps, err = pins_span(text, spans[key])
    if ps is None:
        return None, err
    lit = text[ps[0]:ps[1]]
    new_lit = lit
    subs = []
    for f in FIELD.finditer(lit):
        fk = f.group("k")
        if fk not in new_pin:
            continue
        oldv = f.group("v")
        newv = new_pin[fk]
        # INTEGRITY: the literal must still carry the value the card recorded as
        # the old pin. If it does not, this text is not the book we measured.
        if fk in (old_pin or {}):
            try:
                if abs(float(oldv) - float(old_pin[fk])) > 1e-9:
                    return None, ("field %s: text holds %s but the card says the "
                                  "old pin was %s" % (fk, oldv, old_pin[fk]))
            except (TypeError, ValueError):
                pass
        try:
            same = abs(float(oldv) - float(newv)) < 1e-12
        except (TypeError, ValueError):
            same = str(newv) == oldv
        if same:
            continue
        target = _render(newv)
        pat = re.compile(r'("%s"\s*:\s*)%s(?=[,\s}])' % (re.escape(fk), re.escape(oldv)))
        n = len(pat.findall(new_lit))
        if n != 1:
            return None, ("field %s: expected 1 match of %s, found %d"
                          % (fk, oldv, n))
        new_lit = pat.sub(lambda m: m.group(1) + target, new_lit, count=1)
        subs.append("%s: %s -> %s" % (fk, oldv, target))
    if not subs:
        return text, []
    return text[:ps[0]] + new_lit + text[ps[1]:], subs


def _render(value):
    """Render a measured value so the registry reads back EXACTLY as the card.

    An earlier version reused the old literal's decimal count, which silently
    truncated: a field written 182.0 became 182.01 and landed as 182.0, and
    534.46 landed as 534.4. The card already rounds each field to its own
    convention (n integer, net/dd 2dp, win 3dp), so its own repr is the only
    representation guaranteed to round-trip. That is what the post-write verify
    asserts, so this must be the same string.
    """
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    return str(value)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--verify", action="store_true",
                    help="re-import the registry and compare to the card")
    a = ap.parse_args(argv)

    if not CARD.exists():
        print("no %s - run exp_repin_stale.py --write first" % CARD.name)
        return 2
    card = json.loads(CARD.read_text(encoding="utf-8"))

    files = {p: p.read_text(encoding="utf-8") for p in sorted(REGDIR.glob("*.py"))}
    print("=" * 78)
    print("APPLY RE-PIN - %d book(s)   (%s)"
          % (len(card), "WRITING" if a.write else "dry run, nothing written"))
    print("=" * 78)

    applied, skipped, failed = [], [], []
    edited = {}
    for key, row in sorted(card.items()):
        if "new_pin" not in row:
            skipped.append((key, "no new_pin (measurement errored)"))
            continue
        new_pin, old_pin = row["new_pin"], row["old_pin"]
        hits = locate(key, files)
        if len(hits) != 1:
            failed.append((key, "key resolves to %d registry files" % len(hits)))
            continue
        path = hits[0][0]
        cur = edited.get(path, files[path])
        out, info = apply_to_text(cur, key, new_pin, old_pin)
        if out is None:
            failed.append((key, info))
            continue
        if out != cur:
            edited[path] = out
            applied.append((key, path.name, info))
        else:
            skipped.append((key, "no field value changed"))
    print("applied %d   unchanged %d   failed %d"
          % (len(applied), len(skipped), len(failed)))
    if skipped:
        print("\nunchanged / skipped (%d):" % len(skipped))
        for k, why in skipped[:40]:
            print("    %-44s %s" % (k, why))
    if failed:
        print("\nFAILED (%d):" % len(failed))
        for k, why in failed:
            print("    %-44s %s" % (k, why))
        return 1

    if not a.write:
        print("\nDRY RUN. Sample of what would change:")
        for k, f, subs in applied[:6]:
            print("    %-40s %s" % (k, f))
            for s in subs:
                print("        %s" % s)
        print("\nRe-run with --write to perform the edit.")
        return 0

    for path, text in edited.items():
        path.write_text(text, encoding="utf-8")
    print("\nwrote %d registry file(s): %s"
          % (len(edited), ", ".join(p.name for p in edited)))

    for m in ("experiment_registry", "registry"):
        if m in sys.modules:
            del sys.modules[m]
    import experiment_registry as reg
    importlib.reload(reg)
    bad = []
    for key, row in card.items():
        if "new_pin" not in row:
            continue
        live = (reg.EXPERIMENTS.get(key) or {}).get("pins") or {}
        for f, v in row["new_pin"].items():
            if live.get(f) != v:
                bad.append((key, f, v, live.get(f)))
    print("registry re-imported, %d book(s) compared against the card" % len(card))
    if bad:
        print("\nMISMATCH after write (%d):" % len(bad))
        for k, f, want, got in bad[:40]:
            print("    %-40s %s want %s got %s" % (k, f, want, got))
        return 1
    print("every re-pinned field reads back exactly as measured")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
