"""VERIFY THE HALT MECHANISM - I asserted a cause without measuring it.

WHERE THIS COMES FROM
=====================
`exp_kelly_continuous.py` Part A found the IS/OOS split in trade
autocorrelation is explained in IS but not OOS:

    IS   halt k=3 ACF1 +0.0651 (inside band) -> k=0 gives +0.1317 (outside)
    OOS  halt k=3 ACF1 +0.4981 (outside band) -> k=0 gives +0.4813 (outside)

The explanation offered was "the halt fires more often in IS, so it chops
the loss sequence more, which mechanically de-correlates it." That was a
STORY, never measured. Trade density is similar across the two eras (500
trades / 3.67y vs 279 / 2.0y), so "fires more often" was never obviously
true. This measures it.

HOW FIRES ARE COUNTED
=====================
The engine skips the NEXT entry when consecutive_losses >= 3, then resets.
So the number of fires is the number of maximal runs of losses of length
>= 3 in the booked ledger - each such run end is one skip. Counting runs
off the trade list needs no engine internals.

Run:  $env:PYTHONIOENCODING='utf-8'; python -u exp_halt_firing_rate.py
"""
from __future__ import annotations

import json
import statistics
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

OUT = ROOT / "live_stuff/tests/_halt_firing_rate.json"
LANE = "champion_multi_sw10"
BYBIT_BASE = {"is": (500, 325.8), "oos": (279, 70.2)}
HALT_AT = 3


def runs_of_losses(rs):
    """Maximal runs of losing trades, in order."""
    out, cur = [], 0
    for r in rs:
        if r <= 0:
            cur += 1
        else:
            if cur:
                out.append(cur)
            cur = 0
    if cur:
        out.append(cur)
    return out


def main():
    from test_experiments_craze import build_module
    from exp_5m_confirm import load_book
    from exp_sizing_combo import run as sim_fn
    from experiment_registry import BP, EXPERIMENTS
    from exp_equity_quality import equity_quality

    t0 = time.time()
    sim = build_module()
    params = {**BP, **EXPERIMENTS[LANE]["params"]}
    payload = {"lane": LANE, "halt_at": HALT_AT, "eras": {}}
    print("=" * 96, flush=True)
    print("  HALT FIRING RATE - is 'the halt fires more in IS' actually true?",
          flush=True)
    print("=" * 96, flush=True)

    for scope in ("is", "oos"):
        data, _ = load_book(scope)
        out = {}
        for k in (3, 0):
            tr = sim_fn(sim, data, {**params, "max_consecutive_losses": k})
            trades = tr["ltf_trades"] if isinstance(tr, dict) else tr
            rs = [float(t["r_multiple"]) for t in trades]
            m = equity_quality(tr, 3.67 if scope == "is" else 2.0)
            runs = runs_of_losses(rs)
            fires = sum(1 for L in runs if L >= HALT_AT)
            skipped = sum(L - HALT_AT + 1 for L in runs if L >= HALT_AT)
            out[k] = {"n": len(trades), "net": m["net"],
                      "loss_runs": len(runs), "runs_ge3": fires,
                      "entries_skipped": skipped,
                      "run_len_hist": dict(sorted(Counter(runs).items())),
                      "mean_run": (round(statistics.fmean(runs), 2)
                                   if runs else None),
                      "max_run": max(runs) if runs else None,
                      "fire_rate_per_100": round(100.0 * fires / len(trades), 2)
                      if trades else None}
            if k == 3:
                exp_n, exp_net = BYBIT_BASE[scope]
                ok = len(trades) == exp_n and abs(m["net"] - exp_net) < 0.6
                print(f"\n  [{scope}] CONTROL {m['n']}t {m['net']:+.1f}R "
                      f"{'OK' if ok else 'MISMATCH'}", flush=True)

        for k in (3, 0):
            d = out[k]
            tag = " (shipped)" if k == 3 else " (halt off)"
            print(f"    k={k}{tag}: {d['n']}t  runs {d['loss_runs']}  "
                  f"runs>=3: {d['runs_ge3']}  skipped {d['entries_skipped']}  "
                  f"({d['fire_rate_per_100']}/100 trades)  "
                  f"mean {d['mean_run']}  max {d['max_run']}", flush=True)
        delta = round(out[3]["fire_rate_per_100"] - out[0]["fire_rate_per_100"], 2)
        out["fire_rate_delta"] = delta
        print(f"    -> shipped halt fires {delta:+.2f} per 100 trades more "
              f"than no halt", flush=True)
        print(f"       run hist k=3: {out[3]['run_len_hist']}", flush=True)
        print(f"       run hist k=0: {out[0]['run_len_hist']}", flush=True)
        payload["eras"][scope] = out

    di = payload["eras"]["is"]["fire_rate_delta"]
    do = payload["eras"]["oos"]["fire_rate_delta"]
    verdict = ("CONFIRMED: the halt bites harder in IS" if di > do + 0.5
               else "REFUTED: the halt fires about equally in both eras")
    print(f"\n  VERDICT: {verdict}", flush=True)
    print(f"    IS delta {di:+.2f}/100    OOS delta {do:+.2f}/100", flush=True)
    payload["verdict"] = verdict
    payload["elapsed_sec"] = round(time.time() - t0, 1)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"\nwrote {OUT} ({payload['elapsed_sec']}s)")


if __name__ == "__main__":
    main()
