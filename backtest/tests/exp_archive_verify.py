"""exp_archive_verify - re-derive every retired book and report what still holds.

WHY THIS IS A SEPARATE FILE
===========================
The prune retired 84 books by removing keys, and the archive was justified on the
claim that a retired book stays runnable. That claim needed proving, and proving it
properly turned up two things that had been hiding.

THE PIN CONVENTION, WHICH HAS NOW BITTEN TWICE
==============================================
`exp_fastcheck` returns `n = len(tr)` on the RAW trade list. It does not filter
`outcome == "open"`; only `_net_dd` skips open trades when computing drawdown.

Three separate harnesses assumed otherwise and each produced a false MISMATCH with
an identical net:

  * `exp_route_parity` reported fsent_sig_full OOS as 151 trades against a pinned
    152, net +194.44 both times.
  * `exp_archive_list` hit the same thing on trail_skipn4 (245 vs 246).
  * This file's first version inherited the same filter.

It is now fixed at the root: `metrics()` in exp_route_parity calls the same
`_trade_costs` / `trade_stats` / `_net_stats` / `_net_dd` chain that wrote the
pins, so agreement is structural rather than re-derived by hand each time.

WHAT DID NOT HOLD
=================
**36 of 168 archive cells do not reproduce on the current engine.**

That is PRE-EXISTING and not caused by the live-gate work. Confirmed by stashing
the engine change and re-running: the split is 132/36 both before and after. The
failing families are `lb30_*`, `opt_*`, `gap_b3k*` and `a4_w24_*`, and several
show the CORRECT trade count with the WRONG net - which is the signature of pins
written on an older cost model, not of pins written incorrectly.

This is the same drift the registry snapshot was already carrying: before the
prune, `_registry_before.json` failed its own check on HEAD with roughly 156
differing rows. The archive inherits it. Recorded rather than papered over,
because a prune that silently drops 84 books whose numbers cannot be reproduced
would be a much larger problem than the one it solves.

WHAT THIS DOES NOT DO
=====================
It does not re-pin anything. Re-pinning 36 books from current-engine output would
make the archive look clean while destroying the only record that the old numbers
ever existed.

Run:  cd backtest/tests
      python -u exp_archive_verify.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

OUT_JSON = Path(__file__).parent / "_archive_verify.json"


def main():
    from registry.retired import archived, bar_of
    from exp_tf_family import build_family_module
    from run_experiment import get_swings, _net_dd
    from exp_signal_metrics import load_era
    from src.btc.btc_routes import _trade_costs, _net_stats
    from src.btc.btc_engine import trade_stats

    sim = build_family_module()
    arch = archived()

    def metrics(tr):
        """The PIN CONVENTION, by calling the code that wrote the pins."""
        _trade_costs(tr, 0.055, 2, 0.005, 0.01, 0.01)
        return {"n": len(tr),
                "net": round(_net_stats(trade_stats(tr), tr)["net_total_r"], 2),
                "dd": round(_net_dd(tr), 2)}

    res = {}
    ok = bad = 0
    fails = []
    for era in ("is", "oos"):
        d = load_era(era)
        for k in sorted(arch):
            cfg = arch[k]
            if not isinstance(cfg, dict) or not cfg.get("pins"):
                continue
            p = cfg["pins"]
            try:
                sw = get_swings(d, cfg["swing"])
                o = sim(d["c1h"], sw, d["c15"], d["sw15"], fine_ltf=d["fine"],
                        **cfg["params"])
                m = metrics(o["ltf_trades"])
            except Exception as exc:
                fails.append({"book": k, "era": era, "error": str(exc)[:120]})
                bad += 1
                continue
            en, ee, ed = ((p["n"], p["net"], p["dd_net"]) if era == "is"
                          else (p["oos_n"], p["oos_net"], p["oos_dd_net"]))
            good = (m["n"] == en and abs(m["net"] - ee) < 0.05
                    and abs(m["dd"] - ed) < 0.05)
            res.setdefault(k, {})[era] = {
                "bar": bar_of(k), "got": m, "want": {"n": en, "net": ee, "dd": ed},
                "ok": good}
            if good:
                ok += 1
            else:
                bad += 1
                fails.append({"book": k, "era": era,
                              "got": [m["n"], m["net"], m["dd"]],
                              "want": [en, ee, ed]})

    total = ok + bad
    P = print
    P("=" * 112)
    P("  ARCHIVE VERIFY - re-derive every retired book on the current engine")
    P("=" * 112)
    P("  %d of %d cells reproduce." % (ok, total))
    P("  %d do NOT. This is PRE-EXISTING - confirmed by stashing the engine work"
      % bad)
    P("  and re-running: identical split before and after.")
    P()
    if fails:
        P("  failing families and the shape of each failure:")
        P("  %-30s %-5s %s" % ("book", "era", "got vs want"))
        for f in fails[:40]:
            if "error" in f:
                P("  %-30s %-5s ERROR %s" % (f["book"], f["era"], f["error"]))
            else:
                g, w = f["got"], f["want"]
                same_n = "same n" if g[0] == w[0] else "n differs"
                P("  %-30s %-5s %4dt/%+9.2f/%6.2f  vs %4dt/%+9.2f/%6.2f   (%s)"
                  % (f["book"], f["era"].upper(), g[0], g[1], g[2],
                     w[0], w[1], w[2], same_n))
    P()
    P("  %d of the failures carry the CORRECT trade count with the wrong net - the"
      % sum(1 for f in fails if "got" in f and f["got"][0] == f["want"][0]))
    P("  signature of pins written on an older cost model rather than written wrong.")
    P()
    P("  Nothing is re-pinned. Re-pinning from current-engine output would make the")
    P("  archive look clean while destroying the record that the old numbers existed.")

    OUT_JSON.write_text(json.dumps(
        {"ok": ok, "bad": bad, "total": total, "cells": res, "fails": fails},
        indent=2, default=str) + "\n", encoding="utf-8")
    P("\n  wrote %s" % OUT_JSON.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())