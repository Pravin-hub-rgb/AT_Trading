"""RETRACEMENT DEPTH AT ENTRY - the P1/P2 idea, measured where it IS defined.

WHY THIS, AND WHY THE WAVE HARNESS DIED
=======================================
`exp_p1p2_wave.py` tried to label swings P1/P2 and measure a retracement
ratio. It returned ONE candidate in 2,900 swings. PROBE 1 (run and READ
this time) explains why: the chain is sequential with a mean 10.3-bar gap
between swings, so there is no nested wave pair to measure.

But the INFORMATION P1/P2 wants is real and it is already present: for
every B2/FLIP entry the engine produces, how deep did price retrace INTO
the prior leg before it broke? That is the same quantity Elliott's ladder
measures - the depth of the pullback that precedes a continuation - and
it is computed entirely inside the swing that the entry came from, which
is exactly the level where it IS defined.

Crucially this is NOT another post-hoc filter:
  * the depth is knowable at the entry bar, from candles at or before it;
  * it is a property of the ENTRY GEOMETRY, not of the trade's outcome,
    so it cannot be the calendar/regime proxy the entry-time autopsy
    found everywhere else;
  * the shipped marks cannot express it at all - B2/FLIP say "a pivot
    broke", not "it broke after an N% pullback".

WHAT IS MEASURED
================
For each B2/FLIP signal, in entry-bar units:
    depth = (entry_close - the extreme price reached since the swing's
             start extreme) / risk
i.e. how far price pulled back against the trade's direction before the
break fired. depth 0 = the break fired at the leg extreme (no pullback);
depth 1 = it pulled back a full R before breaking.

LADDER (pre-registered, every rung run, none selected after)
    <0.25, 0.25-0.5, 0.5-0.75, 0.75-1.0, >1.0
    for each: net, WR, PF, trimmed mean, ex-best-3/5, BOTH eras.

THE TEST
========
The ladder must be MONOTONE and of the same sign in both eras. Elliott
says shallow pullbacks continue (high depth = weak, i.e. a deep
retracement means the break is late). If the profile is flat or flips
sign, the entry geometry carries no information and the whole P1/P2
family is dead in its reachable form.

BASELINE: the shipped B2/FLIP champion ledger is asserted exact before any
cell is scored, and the ladder cells are compared against it directly.

PROBE FIRST: run `probe_structure.py` and read PROBE 1 before believing any
statement in this docstring. The first version of the P1/P2 harness assumed
a wave structure that does not exist and cost a full run.
"""
from __future__ import annotations

import bisect as _bs
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

OUT = ROOT / "backtest/tests/_retrace_depth.json"
LANE = "champion_multi_sw10"
BYBIT_BASE = {"is": (500, 325.8), "oos": (279, 70.2)}
YEARS = {"is": 3.67, "oos": 2.0}
# pre-registered depth ladder, in units of the trade's own risk
DEPTH_BANDS = (
    ("<0.25", 0.0, 0.25),
    ("0.25-0.50", 0.25, 0.5),
    ("0.50-0.75", 0.5, 0.75),
    ("0.75-1.00", 0.75, 1.0),
    (">1.00", 1.0, 99.0),
)
LOOKBACK = 60      # bars to look back for the pullback, ~15h on 15m
SL_BUF_ATR = 0.01
ATR_LB = 14
COOLDOWN = 8
MAX_HOLD_MIN = 240.0
TARGET_R = 3.0      # the shipped champion's effective target


def atr_series(candles, lb=ATR_LB):
    n = len(candles)
    tr = [0.0] * n
    for i in range(n):
        hi, lo = float(candles[i]["high"]), float(candles[i]["low"])
        pc = float(candles[i - 1]["close"]) if i else hi
        tr[i] = max(hi - lo, abs(hi - pc), abs(lo - pc))
    out = [0.0] * n
    for i in range(n):
        a = max(0, i - lb + 1)
        out[i] = sum(tr[a:i + 1]) / (i - a + 1)
    return out


def retrace_depth(candles, i, d, sl_pivot, atr_i):
    """How far price pulled BACK against the trade before the break fired.

    Walks BACK from the entry bar over LOOKBACK bars, tracking the most
    adverse excursion against the trade's direction, and expresses it in
    units of the trade's own risk (|entry - sl|), which is the repo's
    standard yardstick (HANDOVER section 5, trap 1).

    Returns 0.0 when price never pulled back at all.
    """
    n = len(candles)
    lo_i = max(0, i - LOOKBACK)
    entry = float(candles[i]["close"])
    risk = abs(entry - float(sl_pivot))
    if risk <= 0:
        return None
    if d == 1:                      # long: adverse = lowest low since
        adverse = entry - min(float(c["low"]) for c in candles[lo_i:i + 1])
    else:                           # short: adverse = highest high since
        adverse = max(float(c["high"]) for c in candles[lo_i:i + 1]) - entry
    return max(0.0, adverse) / risk


def build_signals(sw15, c15, pos_of):
    """Every B2/FLIP entry the champion can take, tagged with retrace depth.

    Deliberately enumerated from the swing chain the same way the engine
    does, so the UNFILTERED set reproduces the champion's population. That
    is what makes the baseline comparison honest: each ladder rung is a
    subset of the same book, not a different book.
    """
    from src.btc.btc_engine import _collect_signals
    atr = atr_series(c15, ATR_LB)
    sigs = _collect_signals(sw15, "decisive", skip_first=True,
                           selection="stream", candles=c15)
    out = []
    for sg in sigs:
        i = pos_of.get(sg["bar"], -1)
        if i < 0 or i >= len(c15) - 1:
            continue
        d = 1 if sg["dir"] == 1 else -1
        entry = float(c15[i]["close"])
        pivot = float(sg["swing_start_px"])
        sl = pivot - SL_BUF_ATR * atr[i] if d == 1 else pivot + SL_BUF_ATR * atr[i]
        dep = retrace_depth(c15, i, d, sl, atr[i])
        if dep is None:
            continue
        out.append({"i": i, "dir": d, "entry": entry, "sl": sl,
                    "depth": dep, "kind": sg.get("kind", "")})
    return out


def run_book(candles, sigs, band, stats):
    """Simulate the champion's own book restricted to one depth band."""
    n = len(candles)
    lo_b, hi_b = band[1], band[2]
    atr = atr_series(candles, ATR_LB)
    trades = []
    busy_until = -1
    last_loss = -10 ** 9
    excl = 0
    for sg in sigs:
        i = sg["i"]
        if not (lo_b <= sg["depth"] < hi_b):
            continue
        if i <= busy_until or i - last_loss < COOLDOWN:
            continue
        d, entry, sl = sg["dir"], sg["entry"], sg["sl"]
        if d == 1:
            if sl >= entry:
                excl += 1
                continue
            risk = entry - sl
        else:
            if sl <= entry:
                excl += 1
                continue
            risk = sl - entry
        if risk <= 0 or (atr[i] > 0 and risk < 0.25 * atr[i]):
            excl += 1
            continue
        target = entry + TARGET_R * risk * d
        exit_i = exit_px = None
        outcome = "open"
        lim = min(n - 1, i + int(MAX_HOLD_MIN))
        for j in range(i + 1, lim + 1):
            hi, lo = float(candles[j]["high"]), float(candles[j]["low"])
            if d == 1:
                if lo <= sl:
                    exit_i, exit_px = j, min(sl, float(candles[j]["open"]))
                    outcome = "sl"
                    break
                if hi >= target:
                    exit_i, exit_px = j, max(target, float(candles[j]["open"]))
                    outcome = "target"
                    break
            else:
                if hi >= sl:
                    exit_i, exit_px = j, max(sl, float(candles[j]["open"]))
                    outcome = "sl"
                    break
                if lo <= target:
                    exit_i, exit_px = j, min(target, float(candles[j]["open"]))
                    outcome = "target"
                    break
        if exit_i is None:
            exit_i = lim
            exit_px = float(candles[exit_i]["close"])
            outcome = "time_stop"
        move = (exit_px - entry) * d
        r = move / risk
        trades.append({
            "dir": "long" if d == 1 else "short", "depth": sg["depth"],
            "entry_ts": int(candles[i]["ts"]), "exit_ts": int(candles[exit_i]["ts"]),
            "r_multiple": round(float(r), 3), "outcome": outcome,
            "bars_held": exit_i - i, "risk": round(risk, 2),
        })
        busy_until = exit_i
        if r < 0:
            last_loss = exit_i
    stats.update({"trades": len(trades), "excluded_geometry": excl})
    return trades


def _metrics(trades, years):
    n = len(trades)
    if n == 0:
        return {"n": 0, "net": 0.0, "net_yr": 0.0, "wr": 0, "pf": None,
                "avg_r": 0.0, "trimmed_mean": 0.0, "max_dd": 0.0,
                "ex_best3": 0.0, "ex_best5": 0.0}
    rs = [float(t["r_multiple"]) for t in trades]
    wins = [x for x in rs if x > 0]
    loss = -sum(x for x in rs if x < 0)
    peak = cum = dd = 0.0
    for t in sorted(trades, key=lambda z: int(z["exit_ts"])):
        cum += float(t["r_multiple"])
        peak = max(peak, cum)
        dd = max(dd, peak - cum)
    k = int(n * 0.05)
    tr = sorted(rs)[k:n - k] if n - 2 * k > 0 else rs
    s = sorted(rs, reverse=True)
    return {"n": n, "net": round(sum(rs), 1),
            "net_yr": round(sum(rs) / years, 2),
            "wr": round(100.0 * len(wins) / n, 1),
            "pf": round(sum(wins) / loss, 3) if loss > 1e-9 else None,
            "avg_r": round(sum(rs) / n, 3),
            "trimmed_mean": round(sum(tr) / len(tr), 3),
            "max_dd": round(dd, 1),
            "ex_best3": round(sum(s[3:]), 1),
            "ex_best5": round(sum(s[5:]), 1)}


def main():
    from test_experiments_craze import build_module
    from exp_5m_confirm import load_book
    from exp_sizing_combo import run as sim_fn
    from experiment_registry import BP, EXPERIMENTS
    from exp_equity_quality import equity_quality

    t0 = time.time()
    sim = build_module()
    params = {**BP, **EXPERIMENTS[LANE]["params"]}
    payload = {"lane": LANE, "bands": [b[0] for b in DEPTH_BANDS],
               "lookback": LOOKBACK, "target_r": TARGET_R, "eras": {}}
    print("=" * 104, flush=True)
    print("  RETRACEMENT DEPTH AT ENTRY - the P1/P2 quantity, where it exists",
          flush=True)
    print("=" * 104, flush=True)

    for scope in ("is", "oos"):
        data, _ = load_book(scope)
        c15, sw15 = data["c15"], data["sw15"]
        pos_of = {c["date"]: i for i, c in enumerate(c15)}

        ctl = equity_quality(sim_fn(sim, data, dict(params)), YEARS[scope])
        exp_n, exp_net = BYBIT_BASE[scope]
        ok = ctl["n"] == exp_n and abs(ctl["net"] - exp_net) < 0.6
        print(f"\n  [{scope}] BASELINE (shipped champion) {ctl['n']}t "
              f"{ctl['net']:+.1f}R net  WR {ctl['wr']}%  PF {ctl['pf']}  "
              f"DD {ctl['max_dd']}   {'OK' if ok else 'MISMATCH'}", flush=True)
        if not ok:
            payload.setdefault("errors", []).append(scope)
            continue

        sigs = build_signals(sw15, c15, pos_of)
        deps = sorted(s["depth"] for s in sigs)
        print(f"    B2/FLIP signals: {len(sigs):,}  "
              f"(champion books {ctl['n']} after window+cooldown gates)",
              flush=True)
        if deps:
            q = lambda p: deps[int(p * (len(deps) - 1))]  # noqa: E731
            print(f"    retrace depth (R): p10 {q(.1):.3f} p25 {q(.25):.3f} "
                  f"MED {q(.5):.3f} p75 {q(.75):.3f} p90 {q(.9):.3f} "
                  f"max {deps[-1]:.2f}", flush=True)

        rows = {}
        for bname, lo, hi in DEPTH_BANDS:
            st = {}
            tr = run_book(c15, sigs, (bname, lo, hi), st)
            m = _metrics(tr, YEARS[scope])
            rows[bname] = {**m, "stats": st}
            dn = round(m["net"] - ctl["net"], 1) if m["n"] else 0.0
            print(f"    {bname:<10} {m['n']:>4}t ({m['n']/max(ctl['n'],1)*100:>5.1f}% "
                  f"of book)  net {m['net']:>+8.1f}R  vs baseline {dn:>+8.1f}  "
                  f"WR {m.get('wr',0):>5}%  PF {str(m.get('pf')):>6}  "
                  f"trim {str(m.get('trimmed_mean')):>7}  "
                  f"exB5 {str(m.get('ex_best5')):>8}", flush=True)
        payload["eras"][scope] = {"baseline": {"n": ctl["n"], "net": ctl["net"]},
                                  "signals": len(sigs), "rows": rows}

    print("\n  " + "=" * 104, flush=True)
    print("  LADDER PROFILE - monotone AND same sign in both eras = real")
    print("  " + "=" * 104, flush=True)
    ise = payload["eras"].get("is", {})
    ose = payload["eras"].get("oos", {})
    if ise and ose:
        print(f"    {'band':<11}{'IS net':>10}{'IS trim':>10}"
              f"{'OOS net':>11}{'OOS trim':>11}", flush=True)
        for b, _, _ in DEPTH_BANDS:
            a = ise["rows"].get(b, {})
            o = ose["rows"].get(b, {})
            print(f"    {b:<11}{a.get('net',0):>+10.1f}"
                  f"{a.get('trimmed_mean',0):>+10.3f}"
                  f"{o.get('net',0):>+11.1f}"
                  f"{o.get('trimmed_mean',0):>+11.3f}", flush=True)
        print(f"    {'BASELINE':<11}"
              f"{ise['baseline']['net']:>+10.1f}{'':>10}"
              f"{ose['baseline']['net']:>+11.1f}", flush=True)

    payload["elapsed_sec"] = round(time.time() - t0, 1)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"\nwrote {OUT} ({payload['elapsed_sec']}s)")


if __name__ == "__main__":
    main()

