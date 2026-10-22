"""Bring the prose measured-claims back onto the pins, and anchor them to a chain.

A desc sentence of the form "IS 560t / +616.17R / DD 15.13R" is a claim about
this book. When the engine moves and the prose does not, that claim becomes a
lie told in the registry - and a reader has no way to tell it from a correct
one, because it looks exactly like the neighbouring correct sentences.

So this rewrites those claims to the re-derived pin values and stamps them with
the chain that produced them. It touches only the numeric claim; it does not
rewrite the reasoning around it, because the reasoning is often still correct
and the numbers were the part that went stale.

Deliberately NOT done here:
  - deleting cross-references to other books, other configurations or null
    baselines. Those are history being cited, not claims about this book.
  - adding new claims. Nothing is inserted that the pins do not already say.

Idempotent: running it twice produces no second change.

Run with --apply to write. Without it, reports only.
"""
from __future__ import annotations

import io
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REGDIR = HERE.parent / "tests" / "registry"
SRC = HERE / "repin_all.json"
# The anchor says WHICH chain produced the numbers, and - since the wait-for-FS
# gate moved the engine and only this book's own claims are rewritten - it also
# says the cross-references to other books are still the pre-gate ones.
ANCHOR = ("as of 2026-10-22 (exp_repin_all.py, net lens, wait-for-FS gate; "
          "cross-references are pre-gate)")
OLD_ANCHORS = ("as of 2026-10-15 (exp_repin_all.py, net lens)",)

MERGE_ORDER = ("trail", "sweep", "signal", "risk", "d3", "kingsweep")

CLAIM = re.compile(
    r"\b(IS|OOS)\s+(\d+)t\s*/\s*([+-][\d.]+)R\s*(?:/\s*(?:DD|dd|drawdown)(?:_net)?\s*([\d.]+)R)?",
    re.I)

KEY = re.compile(r'^(?P<ind>\s*)"(?P<name>[^"]+)":\s*\{')
NEXTKEY = re.compile(r'^\s*"(?!desc")\w+":')


def fix_desc_span(text, pins):
    """Rewrite measured claims in one desc literal's source span."""
    out = text
    edits = []

    def sub(m):
        era, n_txt, net_txt, dd_txt = m.group(1), m.group(2), m.group(3), m.group(4)
        k = "is" if era.lower() == "is" else "oos"
        n = pins["n"] if k == "is" else pins["oos_n"]
        net = pins["net"] if k == "is" else pins["oos_net"]
        dd = pins["dd_net"] if k == "is" else pins["oos_dd_net"]
        rep = "%s %dt / %+.2fR" % (era.upper(), n, net)
        if dd_txt is not None:
            rep += " / DD %.2fR" % dd
        if rep.replace(" ", "") != m.group(0).replace(" ", ""):
            edits.append((m.group(0), rep))
        return rep

    out = CLAIM.sub(sub, out)
    # Move an existing anchor to the new chain before anything else looks for
    # one. Without this a desc would keep the old anchor and gain the new one
    # next to it, and the reader would be told two different things.
    for old in OLD_ANCHORS:
        if old in out:
            out = out.replace(old, ANCHOR)
            edits.append((old, ANCHOR))
    # The anchor is added whenever the desc makes a measured claim, whether or
    # not the numbers had moved. A claim that is currently correct still needs
    # to say which chain made it correct, otherwise there is no signal the day
    # the chain moves again.
    if CLAIM.search(out) and ANCHOR not in out:
        out = CLAIM.sub(lambda m: m.group(0) + " [" + ANCHOR + "]", out, count=1)
        edits.append(("anchor", ANCHOR))
    return out, edits


def process(path, newpins, live):
    src = io.open(path, encoding="utf-8").read()
    lines = src.split("\n")
    out, changes = [], []
    cur = None
    i = 0
    while i < len(lines):
        m = KEY.match(lines[i])
        if m and m.group("name") in newpins:
            cur = m.group("name")
        m2 = re.match(r'^(?P<ind>\s*)"desc":', lines[i])
        if m2 and cur in newpins and (cur in live):
            # collect the desc literal: from here until the next key at or
            # before this indent, or the end of the entry
            ind = m2.group("ind")
            j = i + 1
            while j < len(lines):
                if lines[j].strip() in ("},", "}"):
                    break
                if len(lines[j]) - len(lines[j].lstrip()) <= len(ind) and NEXTKEY.match(lines[j]):
                    break
                j += 1
            span = "\n".join(lines[i:j])
            new_span, edits = fix_desc_span(span, newpins[cur])
            if edits:
                changes.append((cur, edits))
                out.extend(new_span.split("\n"))
                i = j
                continue
        out.append(lines[i])
        i += 1
    return "\n".join(out), changes


def main() -> int:
    apply = "--apply" in sys.argv
    sys.path.insert(0, str(HERE.parent / "tests"))
    sys.path.insert(0, str(HERE.parent))
    sys.path.insert(0, str(HERE.parents[1] / "backend"))
    from experiment_registry import EXPERIMENTS
    live = {k: v for k, v in EXPERIMENTS.items() if isinstance(v, dict)}
    newpins = json.loads(io.open(SRC, encoding="utf-8").read())["new_pins"]

    total, shown = 0, 0
    rendered = {}
    for stem in MERGE_ORDER:
        f = REGDIR / (stem + ".py")
        if not f.exists():
            continue
        txt, ch = process(f, newpins, live)
        rendered[f] = txt
        if ch:
            total += len(ch)
            print("%s:" % f.name)
            for name, edits in ch:
                for a, b in edits:
                    if shown < 12:
                        print("   %-36s %s  =>  %s" % (name, a[:52], b[:52]))
                        shown += 1
    print()
    print("descs to correct : %d" % total)
    print("mode             : %s" % ("APPLY" if apply else "DRY RUN"))
    if not apply:
        print("DRY RUN. Pass --apply to write.")
        return 0
    for f, txt in rendered.items():
        if txt != io.open(f, encoding="utf-8").read():
            io.open(f, "w", encoding="utf-8").write(txt)
            print("wrote %s" % f.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())