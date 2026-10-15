"""Regression for the unknown-mode guard.

The guard changes engine behaviour on a path no registry book takes, so the test
that matters is not "does it run" but "does every pinned book still produce
exactly its pinned numbers". A guard that quietly changed a book's equity curve
would be a far worse bug than the one it removes.

    python exp_mode_guard_test.py
"""
from __future__ import annotations

import ast
import io
import os
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

import exp_repin_stale as repin                                  # noqa: E402
import test_experiments_craze as craze                           # noqa: E402
from registry import EXPERIMENTS                                # noqa: E402

SRC = ROOT / "backend/src/btc/engines/htf_ltf/unified.py"
HERE = Path(__file__).resolve().parent
RESULTS = HERE / "mode_guard_test_results.json"


def sets_from_source():
    tree = ast.parse(io.open(SRC, encoding="utf-8").read())
    declared = None
    for node in tree.body:
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "HTF_MODES":
            declared = set(ast.literal_eval(node.value.args[0]))
    chain = set()
    for node in ast.walk(tree):
        if (isinstance(node, ast.Compare) and isinstance(node.left, ast.Name)
                and node.left.id == "mode" and len(node.ops) == 1
                and isinstance(node.ops[0], ast.Eq)
                and isinstance(node.comparators[0], ast.Constant)
                and isinstance(node.comparators[0].value, str)):
            chain.add(node.comparators[0].value)
    return declared, chain


def main() -> int:
    t0 = time.time()
    out = {}

    print("=" * 92)
    print("1. THE SETS AGREE  (a valid mode must never be rejected)")
    print("=" * 92)
    declared, chain = sets_from_source()
    print("  HTF_MODES binds %d, chain routes %d" % (len(declared), len(chain)))
    print("  chain branch missing from HTF_MODES : %s" % (sorted(chain - declared) or "none"))
    print("  HTF_MODES name with no branch      : %s" % (sorted(declared - chain) or "none"))
    out["sets"] = {"declared": sorted(declared), "chain": sorted(chain),
                   "missing": sorted(chain - declared), "extra": sorted(declared - chain)}
    sets_ok = not (chain - declared) and not (declared - chain)

    print()
    print("=" * 92)
    print("2. THE BUG IS NOW AN ERROR  (it used to trade silently as flip)")
    print("=" * 92)
    sim = craze.build_module()
    from exp_signal_metrics import load_era
    d = load_era("is")
    base = dict(EXPERIMENTS["fsent_champ_long"])
    base["swing"] = "sw10"
    base["basis"] = "fine"
    bug = {}
    for bad in ("GARBAGE_MODE_xyz", "", "atr-hiogh", "Session", "union_"):
        cfg = dict(base)
        cfg["params"] = dict(base["params"], mode=bad)
        try:
            r = repin.measure(sim, d, cfg)
            bug[bad] = {"raised": False, "n": r["n"], "net": r["net"]}
            print("  %-20r STILL SILENT  n=%d net=%.2f   <-- FIX DID NOT WORK"
                  % (bad, r["n"], r["net"]))
        except ValueError as e:
            bug[bad] = {"raised": True}
            print("  %-20r ValueError  %s" % (bad, str(e)[:60]))
    bug_ok = all(v["raised"] for v in bug.values())
    out["bug"] = bug

    print()
    print("=" * 92)
    print("3. EVERY PINNED BOOK STILL HITS ITS PINS")
    print("=" * 92)
    books = {k: v for k, v in EXPERIMENTS.items() if isinstance(v, dict) and v.get("pins")}
    print("  %d pinned books, both eras\n" % len(books))
    mism = []
    eras = {"is": load_era("is"), "oos": load_era("oos")}
    for i, (b, cfg) in enumerate(sorted(books.items()), 1):
        c = dict(cfg)
        c["basis"] = "fine"
        pin = c["pins"]
        for era, k in (("is", "n"), ("is", "net"), ("oos", "oos_n"), ("oos", "oos_net")):
            m = repin.measure(sim, eras[era], c)[k.replace("oos_", "")]
            want = pin[k]
            ok = m == want if k.endswith("n") else abs(m - want) < 0.01
            if not ok:
                mism.append({"book": b, "field": k, "measured": m, "pinned": want})
        print("  [%3d/%3d] %-40s %s" % (i, len(books), b, "ok" if not mism else ""))
    print()
    print("  %d books x 4 pinned fields = %d checks, %d mismatches"
          % (len(books), len(books) * 4, len(mism)))
    for m in mism[:10]:
        print("    MISMATCH %s %s measured %s pinned %s" % (m["book"], m["field"], m["measured"], m["pinned"]))
    out["pin_mismatches"] = mism

    ok = sets_ok and bug_ok and not mism
    print()
    print("RESULT: %s" % ("PASS" if ok else "FAIL"))
    print("The guard removes a silent fallback. It must not move a single pinned number,")
    print("and the check above is what establishes that.")
    # Was: RESULTS.write_text(io.open(RESULTS, "w", ...).write(...)). The inner
    # write() already saved the file and returns a byte count, which write_text
    # then rejects - so every run ended in a TypeError after printing PASS.
    # Harmless, but a spurious traceback trains people to ignore stderr.
    RESULTS.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("wrote %s  (%.0fs)" % (RESULTS.name, time.time() - t0))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())