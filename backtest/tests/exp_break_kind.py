"""B1 / B2 / FLIP decomposition of the ALREADY-SIMULATED champion books.

ZERO new sims, zero new data, zero new code.

The engine tags every trade with its break kind at build time:

    ltf_trades.append({... "break_kind": sig["kind"] ...})      # L1811

and `_collect_signals` emits `kind` in {"B1", "B2", "FLIP", ...}. The live LTF
path already branches on it four separate times (exp_b1_b2_mode, exp_vol_b2_rvol,
exp_kinds, exp_entry_skip_b2_doji), so the engine itself already treats these
states as different kinds of thing.

So the entire question "do B1 / B2 / FLIP have different economics?" is already
answered by the books we have. This script just buckets them.

WHY THIS FRAMING AND NOT ANOTHER TIMEFRAME PREDICATE
====================================================
Every experiment in this programme (S1-S6, the 2h plane, log 111's 5m gate)
treated a signal as a *point in time* carrying a direction, and asked whether to
take it, skip it, or delay it. That framing is exhausted - Rule 17 closed it,
and the 5m gate lost 222R in 36/36 cells.

B1/B2/FLIP is a different object. They are states of a state machine:

    B1   = first A/B break -> LOCK the direction, dir is NOT yet confirmed
    B2   = fresh-extreme extension -> CONFIRM that lock
    FLIP = opposite extreme breaks -> the engine reverses its own lock

A FLIP is the engine *admitting it was wrong*. That is a self-declared error,
not a market-derived label, and it is exactly the kind of information a filter
cannot manufacture - it is already in the book.

Note this is a DECOMPOSITION, not a predicate: it proposes no threshold, is not
scanned, and cannot be fished. If FLIP and B2 differ, that is either a real
structural fact or it is not there.

Run: $env:PYTHONIOENCODING='utf-8'; python -u exp_break_kind.py
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

OUT = ROOT / "backtest/tests/_break_kind.json"
BASE = {"champion": {"is": (500, 325.8), "oos": (279, 70.2)},
        "utcsat": {"is": (453, 279.5), "oos": (254, 66.9)},
        "age10": {"is": (130, 435.7), "oos": (76, 43.2)}}


def shape(rs):
    n = len(rs)
    if n == 0:
        return {"n": 0, "net": 0.0}
    s = sorted(rs)
    k = int(n * 0.05)
    tr = s[k:n - k] if n - 2 * k > 0 else s
    w = [x for x in rs if x > 0]
    loss = -sum(x for x in rs if x < 0)
    return {"n": n, "net": round(sum(rs), 1),
            "mean": round(sum(rs) / n, 4),
            "median": round(statistics.median(rs), 4),
            "trimmed": round(sum(tr) / len(tr), 4),
            "wr": round(100.0 * len(w) / n, 1),
            "pf": round(sum(w) / loss, 3) if loss > 1e-9 else None,
            "top5_pct": round(100.0 * sum(s[-max(1, n // 20):]) /
                              max(sum(rs), 1e-9), 1)}


def main():
    from exp_5m_confirm import load_book          # same loaders, already verified
    from exp_tf_family import build_family_module
    from run_experiment import net_r
    from experiment_registry import BP, EXPERIMENTS
    sim = build_family_module()
    payload = {"stage": "break_kind_decomposition",
               "note": "decomposition of already-simulated books; no new sim, no "
                       "new data, no threshold, no scanning",
               "semantics": {
                   "B1": "first A/B break -> locks direction, NOT yet confirmed",
                   "B2": "fresh-extreme extension -> confirms that lock",
                   "FLIP": "opposite extreme breaks -> engine reverses its own lock",
               },
               "books": {}}

    for era in ("is", "oos"):
        print(f"\n=== bybit [{era.upper()}] ===", flush=True)
        data, _ = load_book(era)
        for lane, key in (("champion", "champion_multi_sw10"),
                          ("utcsat", "utcsat_multi_sw10"),
                          ("age10", "age10_dirmatch_swingpause_single_sw10")):
            out = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                      fine_ltf=data["fine"], **{**BP, **EXPERIMENTS[key]["params"]})
            trades = out["ltf_trades"]
            rs = [net_r([t]) for t in trades]
            if lane == "champion":
                en, ev = BASE[lane][era]
                assert len(trades) == en and abs(sum(rs) - ev) < 0.5, \
                    f"CONTROL FAIL {era}/{lane}"
            buckets = {}
            for t, r in zip(trades, rs):
                buckets.setdefault(t.get("break_kind", "?"), []).append(r)
            payload["books"].setdefault(f"bybit/{era}", {})[lane] = {
                "total": shape(rs),
                "by_kind": {k: shape(v) for k, v in sorted(buckets.items())}}
            tot = shape(rs)
            print(f"  {lane:<9} n={tot['n']:>3} net={tot['net']:>+7.1f}", flush=True)
            for k in sorted(buckets):
                s = payload["books"][f"bybit/{era}"][lane]["by_kind"][k]
                share = 100.0 * s["n"] / tot["n"]
                netshare = 100.0 * s["net"] / tot["net"] if tot["net"] else 0.0
                print(f"      {k:<5} n={s['n']:>3} ({share:>4.1f}% of trades) "
                      f"net={s['net']:>+7.1f} ({netshare:>5.1f}% of net)  "
                      f"med={s['median']:>+5.2f} trim={s['trimmed']:>+5.2f} "
                      f"PF={(s['pf'] or 0):>4.2f} top5={s['top5_pct']:>6.1f}%",
                      flush=True)
    OUT.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
