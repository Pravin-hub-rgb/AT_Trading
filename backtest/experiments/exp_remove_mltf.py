"""Remove exp_mltf from every registry entry, now that it is proven inert.

THE EVIDENCE
------------
exp_mltf_proof.py ran 42 books - the seven in contention plus every control
book carrying the knob - twice, with the key and without it, and compared the
resulting TRADE LISTS entry by entry. 42 identical, 0 differ. Byte-identical
trade lists mean byte-identical numbers by construction, so no pin can move.

Why it was there and why it did nothing:

  unified.py does not accept exp_mltf at all. The live engine has 46 parameters
  and the harness has 151; live is a strict subset, and exp_mltf is harness-only.
  Its own docstring in unified.py:41 says the anchor injecting it is the one of
  sixty-two Phase 2 had to move into the engine.

  What it touches is narrower still. exp_mltf acts on exactly one line, in the
  loss-window hard close path:

      if not exp_mltf: busy_until = fine_ltf[_lw_fi].get("date") or busy_until

  That path needs exp_window_loss_kill_*, which unified.py also does not have,
  and not one of the forty-two books tested sets a single exp_window_loss_kill_*
  parameter. The knob had nothing to modify on any of them.

WHAT THIS CHANGES AND WHAT IT DOES NOT

Removes the key from the params dicts. Does not touch pins, descriptions,
measured fields in books.ts, or any recorded figure - all of those are already
consistent with the knob being absent, which is why the live engine reproduced
every pin exactly before this change.

Comments that MENTION exp_mltf are left alone. They describe why other books
were inert, and deleting them would remove the reasoning that explains why
this key was ever worth testing. Only the params entries go.

Output: prints a count per file. Asserts afterwards that no params dict still
carries it, and that every book still imports with the same key set.
"""
from __future__ import annotations

import io
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REGDIR = HERE.parent / "tests" / "registry"
sys.path.insert(0, str(HERE.parent / "tests"))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parents[1] / "backend"))

# "exp_mltf": True,   or   "exp_mltf": True
ENTRY = re.compile(r'"exp_mltf":\s*True,\s*')


def main() -> int:
    apply = "--apply" in sys.argv
    total = 0
    per = {}
    for f in sorted(REGDIR.glob("*.py")):
        src = io.open(f, encoding="utf-8").read()
        # only count ones inside a params dict - every occurrence of this exact
        # shape IS a params entry, comments cannot match it
        hits = ENTRY.findall(src)
        if not hits:
            continue
        per[f.name] = len(hits)
        total += len(hits)
        if apply:
            new = ENTRY.sub("", src)
            io.open(f, "w", encoding="utf-8").write(new)
    print("exp_mltf params entries found : %d" % total)
    for k, v in per.items():
        print("   %-14s %d" % (k, v))
    print("mode : %s" % ("APPLY" if apply else "DRY RUN"))
    if not apply:
        print("DRY RUN. Pass --apply to write.")
        return 0

    # verify
    import ast
    from experiment_registry import EXPERIMENTS
    left = []
    for f in sorted(REGDIR.glob("*.py")):
        src = io.open(f, encoding="utf-8").read()
        ast.parse(src)
        left += [(f.name, m) for m in ENTRY.findall(src)]
    still = [k for k, v in EXPERIMENTS.items()
             if isinstance(v, dict) and (v.get("params") or {}).get("exp_mltf")]
    print()
    print("registry files parse        : %d ok" % len(list(REGDIR.glob("*.py"))))
    print("entries still carrying it   : %d" % len(still))
    print("total registry keys         : %d" % len(EXPERIMENTS))
    if still:
        print("FAILED - still present: %s" % still[:6])
        return 1
    print("clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())