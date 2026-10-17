"""Write the re-derived pins into the registry, keeping the old ones verbatim.

Separation of concerns, deliberately:

  exp_repin_all.py   MEASURES.  Runs the engine, writes repin_all.json. Edits
                     nothing. A measurement tool that also writes its own
                     conclusions is how numbers get laundered.
  exp_apply_repin.py WRITES.    Reads repin_all.json, rewrites the pins blocks
                     in backtest/tests/registry/*.py, and moves the previous
                     values to "pins_legacy" so no history is lost.

WHICH BLOCK GETS WRITTEN
------------------------
The registry is six family modules merged in a fixed order - trail, sweep,
signal, risk, d3, kingsweep - and the later one wins on a duplicate key. So the
same book name can appear in more than one file and only the last is real.
Rather than guess from indentation, each candidate block is parsed and compared
against the merged EXPERIMENTS: the block whose value equals what the import
returns is the effective definition, and only that one is rewritten. A book
defined in three files therefore gets exactly one rewrite, and the guard is the
merge itself rather than a hand-maintained list.

THE CONVENTION BEING WRITTEN

  n, net, dd_net, wr_net, gross_win      IS dataset, 2023-01..2026-08
  oos_n, oos_net, oos_dd_net,
    oos_wr_net, oos_gross_win            OOS dataset, 2021-22 (separate file)
  n_all, net_all, dd_net_all             both eras merged, calendar order
  gross_win / oos_gross_win              the old `win`, kept, not deleted

The span part of this is what the existing pins already used: n/net/dd_net
matched the IS column for 54 of 54 books and the oos_* fields matched the OOS
column for 54 of 54. The genuine defects repaired here are that `win` was gross,
that `n` counted open trades on 27 books, that no merged total existed, and
that the field names read like totals when they are one dataset.

Run with --apply to write. Without it, this only reports what it would do.
"""
from __future__ import annotations

import ast
import io
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REGDIR = HERE.parent / "tests" / "registry"
SRC = HERE / "repin_all.json"

sys.path.insert(0, str(HERE.parent / "tests"))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parents[1] / "backend"))

ORDER = ("n", "net", "dd_net", "wr_net", "gross_win",
         "oos_n", "oos_net", "oos_dd_net", "oos_wr_net", "oos_gross_win",
         "n_all", "net_all", "dd_net_all")

MERGE_ORDER = ("trail", "sweep", "signal", "risk", "d3", "kingsweep")


def fmt(v):
    if isinstance(v, float):
        return ("%.4f" % v).rstrip("0").rstrip(".")
    return str(v)


def emit_dict(prefix, d, lead, indent_first=True, width=92):
    """Render `prefix: {...}` wrapped to `width`, returning a list of lines."""
    pad = " " * (len(lead) + len(prefix) + 2)
    items = ['"%s": %s' % (k, fmt(v)) for k, v in d.items()]
    lines, cur = [], ""
    for it in items:
        cand = (cur + ", " if cur else "") + it
        if len(pad) + len(cand) > width and cur:
            lines.append(cur + ",")
            cur = it
        else:
            cur = cand
    lines.append(cur)
    head = (lead + prefix + ": {") if indent_first else (prefix + "{")
    out = [head + lines[0]]
    for b in lines[1:]:
        out.append(pad + b)
    out[-1] = out[-1] + "}"
    return out


def process(path, newpins, live):
    src = io.open(path, encoding="utf-8").read()
    lines = src.split("\n")
    out, changed, shadowed, skipped_legacy = [], [], [], []
    cur = None
    i = 0
    while i < len(lines):
        line = lines[i]
        st = line.lstrip()
        if st.startswith('"') and '": {' in st:
            maybe = st[1:st.index('"', 1)]
            if maybe in newpins:
                cur = maybe
        if st.startswith('"pins":') and cur in newpins:
            depth, block, j = 0, [], i
            while j < len(lines):
                block.append(lines[j])
                depth += lines[j].count("{") - lines[j].count("}")
                if depth == 0:
                    break
                j += 1
            blob = "\n".join(block)
            if "{" not in blob:
                out.append(line)
                i += 1
                continue
            lit = blob[blob.index("{"):].rstrip().rstrip(",")
            try:
                parsed = ast.literal_eval(lit)
            except (ValueError, SyntaxError):
                parsed = None
            if parsed == live.get(cur):
                base = len(block[0]) - len(block[0].lstrip())
                lead = " " * base
                p = {k: newpins[cur][k] for k in ORDER if k in newpins[cur]}
                newblk = emit_dict('"pins"', p, lead)
                newblk[-1] = newblk[-1] + ","
                # Only mint pins_legacy if this book does not already carry one.
                # These books were re-pinned once already, so most already have a
                # pins_legacy from that generation. Writing a second one produces
                # a DUPLICATE LITERAL KEY in the same dict literal, which Python
                # resolves silently by keeping the last - so the complete copy
                # just written is discarded and the older, smaller one survives.
                # It looks like it worked. It did not.
                nxt = j + 1
                has_legacy = nxt < len(lines) and \
                    lines[nxt].lstrip().startswith('"pins_legacy":')
                if not has_legacy:
                    newblk += emit_dict('"pins_legacy"', parsed, lead)
                    newblk[-1] = newblk[-1] + ","
                else:
                    skipped_legacy.append(cur)
                changed.append((cur, blob, "\n".join(newblk)))
                out.extend(newblk)
                i = j + 1
                continue
            shadowed.append((cur, path.name))
        out.append(line)
        i += 1
    return "\n".join(out), changed, shadowed, skipped_legacy


def main() -> int:
    apply = "--apply" in sys.argv
    from experiment_registry import EXPERIMENTS
    newpins = json.loads(io.open(SRC, encoding="utf-8").read())["new_pins"]
    live = {k: v["pins"] for k, v in EXPERIMENTS.items()
            if isinstance(v, dict) and isinstance(v.get("pins"), dict)}

    total, per_file, all_shadow = 0, {}, []
    rendered = {}
    for stem in MERGE_ORDER:
        f = REGDIR / (stem + ".py")
        if not f.exists():
            continue
        txt, ch, sh, _sk = process(f, newpins, live)
        rendered[f] = txt
        if ch:
            per_file[f.name] = len(ch)
            total += len(ch)
        all_shadow.extend(sh)

    print("effective blocks to rewrite : %d of %d books" % (total, len(newpins)))
    for k, v in per_file.items():
        print("   %-14s %d" % (k, v))
    done = {c[0] for f in rendered for c in process(f, newpins, live)[1]}
    missing = sorted(set(newpins) - done)
    print("books with no effective block: %d %s" % (len(missing), missing[:6]))
    print("shadowed definitions skipped : %d" % len(all_shadow))
    print("mode : %s" % ("APPLY" if apply else "DRY RUN"))
    for f in rendered:
        ch = process(f, newpins, live)[1]
        if ch:
            print("\n--- sample: %s (%s) ---" % (ch[0][0], f.name))
            print(ch[0][1])
            print("  =>")
            print(ch[0][2])
            break
    if not apply:
        print("\nDRY RUN. Pass --apply to write.")
        return 0
    for f, txt in rendered.items():
        cur = io.open(f, encoding="utf-8").read()
        if txt != cur:
            io.open(f, "w", encoding="utf-8").write(txt)
            print("wrote %s" % f.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())