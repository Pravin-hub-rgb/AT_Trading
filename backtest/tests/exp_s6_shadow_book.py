"""S6 - the independent 30m/2h shadow BOOK as a feature on the 15m/1h book.

WHY THIS IS A DIFFERENT OBJECT FROM S1-S4
=========================================
S1-S4 compared *bar directions* on 30m and 2h against the trade direction. That
asks "does this one bar point the same way?". Log 109 showed why that family is
exhausted: the books are tail-concentrated (top 5% of trades carry >100% of the
net), so any single-bar split is scored mostly on which handful of large winners
landed in which bucket.

S6 asks a different question. It runs the ENTIRE strategy a second time on the
matched ladder (30m LTF / 2h HTF - cell F3, ladder 4:1) and asks, at each 15m
entry, **is that independent system already positioned, and in which
direction?** The feature is a second opinion from a whole system, not a
reading off one candle. That independence is the thing S1-S4 never had.

HONEST CAVEAT, STATED BEFORE RUNNING
===================================
The shadow book is not a good book. F3 measured IS +222.4R but OOS **-19.9R**
(log 106) - it loses money out of sample. A weak signal is a weak feature: if
its position state is mostly noise, agreement with it should carry no
information, and that is a perfectly acceptable outcome. Its own book is
reported here for exactly that reason, so the feature can be judged against the
quality of the opinion being consulted.

GRID, NOT A KNOB
================
"Within a tolerance" introduces the one tunable this family would otherwise
avoid. It is handled by reporting the WHOLE fixed geometric ladder and
requiring consistency, never by picking the best cell:
    +-0 bars (same 15m bar) | +-1 (15m) | +-4 (1h) | +-8 (2h)
No other tolerance is tried, and no cell is selected out of the grid.

PRE-REGISTERED HIT BAR (all four required)
==========================================
1. The SAME direction in both eras, and
2. a robust statistic (trimmed mean) whose bootstrapped 95% CI excludes zero in
   BOTH eras, and
3. every bucket n >= 30 in both eras, and
4. the sign replicates on the independent dataset (data/btc-fut).
Direction is NOT assumed: "agreement is better" and "disagreement is better"
are both outcomes being tested, and a CI spanning zero either way is a null.

Reporting follows Rule 13 - mean, median, trimmed_mean, stdev and top-5%
concentration for every bucket. A mean-only result is not a result.

Run: $env:PYTHONIOENCODING='utf-8'; python -u exp_s6_shadow_book.py
"""
from __future__ import annotations

import json
import random
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

OUT = ROOT / "backtest/tests/_s6_shadow_book.json"
M15, M30, H1, H2 = 900, 1800, 3600, 7200
TOLERANCES = (0, 1, 4, 8)          # in 15m bars; fixed ladder, all reported
N_FLOOR = 30
LANES = (("champion", "champion_multi_sw10"),
         ("utcsat", "utcsat_multi_sw10"),
         ("age10", "age10_dirmatch_swingpause_single_sw10"))
YEARS = {"is": 3.67, "oos": 2.0, "btcfut": 5.7}


def shape(rs):
    n = len(rs)
    if n == 0:
        return {"n": 0}
    s = sorted(rs)
    w = [x for x in rs if x > 0]
    k = int(n * 0.05)
    tr = s[k:n - k] if n - 2 * k > 0 else s
    return {"n": n, "mean": round(sum(rs) / n, 4),
            "median": round(statistics.median(rs), 4),
            "trimmed_mean": round(sum(tr) / len(tr), 4),
            "stdev": round(statistics.pstdev(rs), 4),
            "wr": round(100.0 * len(w) / n, 1),
            "net": round(sum(rs), 1),
            "top5_share_pct": round(100.0 * sum(s[-max(1, n // 20):]) /
                                    max(sum(rs), 1e-9), 1)}


def boot_trimmed(a, b, n_boot=20000, seed=20260927):
    """Bootstrap the TRIMMED-mean difference, not the raw mean (Rule 13)."""
    if len(a) < N_FLOOR or len(b) < N_FLOOR:
        return {"diff": None, "ci95": None, "p": None}

    def tmean(x):
        s = sorted(x)
        k = int(len(s) * 0.05)
        t = s[k:len(s) - k] if len(s) - 2 * k > 0 else s
        return sum(t) / len(t)
    rng = random.Random(seed)
    diffs = []
    for _ in range(n_boot):
        sa = tmean([a[rng.randrange(len(a))] for _ in range(len(a))])
        sb = tmean([b[rng.randrange(len(b))] for _ in range(len(b))])
        diffs.append(sa - sb)
    diffs.sort()
    pl = sum(1 for x in diffs if x <= 0) / n_boot
    pg = sum(1 for x in diffs if x >= 0) / n_boot
    return {"diff": round(tmean(a) - tmean(b), 4),
            "ci95": [round(diffs[int(0.025 * n_boot)], 4),
                     round(diffs[int(0.975 * n_boot)], 4)],
            "p": round(min(1.0, 2.0 * min(pl, pg)), 4),
            "n_agree": len(a), "n_oppose": len(b)}


# ---------------------------------------------------------------- shadow state
def shadow_timeline(data, _SIM):
    """Run the FULL strategy on the matched ladder (30m/2h, F3) and return the
    intervals during which that independent system held a position.

    Returns, per lane, a list of (entry_ts, exit_ts, dir) sorted by entry. The
    15m book is slot-constrained too, so at most one shadow position is live at
    a time and a sorted interval list represents its state exactly - no queueing
    or partial-fill modelling needed.
    """
    from exp_tf_family import resample_30m
    from exp_htf_2h import resample_2h, flow_2h
    from exp_sizing_combo import run as sim_fn
    from exp_s3_forensic import _compute_swings
    from experiment_registry import BP, EXPERIMENTS
    from exp_shadow_tf import tdir

    c30 = resample_30m(data["c15"])
    c2h = resample_2h(data["c1h"])
    ltf = {"c15": c30, "sw15": _compute_swings(flow_2h(c30), "continuous",
                                               min_bars=50)}
    htf = {"c1h": c2h, "sw20": _compute_swings(flow_2h(c2h), "continuous",
                                               min_bars=20),
           "sw10": _compute_swings(flow_2h(c2h), "continuous", min_bars=10)}
    out = {}
    for lane, key in LANES:
        trades = sim_fn(_SIM, {**htf, **ltf, "fine": data["fine"]},
                        {**BP, **EXPERIMENTS[key]["params"]},
                        htf_bar_secs=H2, ltf_bar_secs=M30)
        out[lane] = sorted((int(t["entry_ts"]), int(t["exit_ts"]), tdir(t))
                           for t in trades)
    return out


def state_at(iv, instant, tol_s):
    """Shadow direction within +/- tol_s of `instant`, else 0 (no position)."""
    for a, b, d in iv:
        if a - tol_s <= instant <= b + tol_s:
            return d
    return 0


def bucketise(trades, rs, iv, tol_bars):
    """Split the 15m book into shadow-agrees / shadow-opposes / shadow-flat.

    Flat is kept SEPARATE from opposing. A shadow system not in a trade has not
    expressed an opinion; folding that in with genuine disagreement would blur
    the exact thing being measured. If flat dominated, the feature would be
    uninformative and that would show up honestly rather than as a fake split.
    """
    from exp_shadow_tf import tdir
    tol_s = tol_bars * M15
    ag, op, fl = [], [], []
    for t, r in zip(trades, rs):
        sd = state_at(iv, int(t["entry_ts"]) + M15, tol_s)
        td = tdir(t)
        if sd == 0:
            fl.append(r)
        elif sd == td:
            ag.append(r)
        else:
            op.append(r)
    return ag, op, fl


def analyse(data, tag, _SIM, payload):
    """Run both books, then score the 15m book against the shadow's state."""
    from exp_sizing_combo import run as sim_fn
    from run_experiment import net_r
    from experiment_registry import BP, EXPERIMENTS

    shadow = shadow_timeline(data, _SIM)
    htf = {"c1h": data["c1h"], "sw20": data["sw20"], "sw10": data["sw10"]}
    ltf = {"c15": data["c15"], "sw15": data["sw15"]}
    res = {}
    for lane, key in LANES:
        trades = sim_fn(_SIM, {**htf, **ltf, "fine": data["fine"]},
                        {**BP, **EXPERIMENTS[key]["params"]})
        rs = [net_r([t]) for t in trades]
        cell = {"main15m": {"n": len(trades), "net": round(sum(rs), 1)},
                "shadow30m2h": {"n": len(shadow[lane]),
                                "n_long": sum(1 for _, _, d in shadow[lane] if d > 0),
                                "n_short": sum(1 for _, _, d in shadow[lane] if d < 0),
                                "coverage_pct": round(
                                    100.0 * len([1 for t in trades
                                                if state_at(shadow[lane],
                                                            int(t["entry_ts"]) + M15,
                                                            0) != 0]) /
                                    max(len(trades), 1), 1)},
                "tolerances": {}}
        for tb in TOLERANCES:
            ag, op, fl = bucketise(trades, rs, shadow[lane], tb)
            cell["tolerances"][f"+-{tb}"] = {
                "agrees": shape(ag), "opposes": shape(op), "flat": shape(fl),
                "boot_trimmed": boot_trimmed(ag, op)}
        res[lane] = cell
    payload["books"][tag] = res
    return res
def _print_book(tag, res):
    print(f"\n--- {tag} ---", flush=True)
    for lane, c in res.items():
        s, m = c["shadow30m2h"], c["main15m"]
        print(f"  {lane:<9} 15m/1h n={m['n']:>4} net={m['net']:>+8.1f} | "
              f"shadow n={s['n']:>4} (L{s['n_long']}/S{s['n_short']}) "
              f"covers {s['coverage_pct']:>5.1f}% of 15m entries", flush=True)
        for tb, d in c["tolerances"].items():
            a, o, f = d["agrees"], d["opposes"], d["flat"]
            bt = d["boot_trimmed"]
            ci = bt["ci95"] if bt["ci95"] else ["-", "-"]
            dt = bt["diff"] if bt["diff"] is not None else 0
            print(f"     {tb:<5} agree n={a.get('n',0):>3} trim={a.get('trimmed_mean',0):>+5.2f} "
                  f"| oppose n={o.get('n',0):>3} trim={o.get('trimmed_mean',0):>+5.2f} "
                  f"| flat n={f.get('n',0):>3} | dtrim={dt:>+5.2f} "
                  f"CI[{ci[0]},{ci[1]}] p={bt['p']}", flush=True)


def _verdict(payload):
    """Apply the pre-registered hit bar to the whole grid, no cell selected."""
    hits, checked = [], 0
    for tag, res in payload["books"].items():
        if "error" in res:
            continue
        for lane, c in res.items():
            for tb, d in c["tolerances"].items():
                bt = d["boot_trimmed"]
                if bt["ci95"] is None:
                    continue
                checked += 1
                excl = bt["ci95"][0] > 0 or bt["ci95"][1] < 0
                if excl and d["agrees"]["n"] >= N_FLOOR and d["opposes"]["n"] >= N_FLOOR:
                    hits.append((tag, lane, tb))
    if not checked:
        return ("every cell had a bucket below the n>=30 floor, so nothing could be "
                "tested. CLOSED - feature carries no usable signal.")
    if not hits:
        return (f"0/{checked} testable cells have a bootstrapped trimmed-mean CI "
                f"excluding zero with both buckets n>={N_FLOOR}. CLOSED - the shadow "
                f"book's position state does not discriminate the 15m book's trades.")
    return (f"{len(hits)}/{checked} cells clear the robustness bar: "
            + "; ".join(f"{t}/{l}/{tb}" for t, l, tb in hits[:8])
            + ". STILL NOT ADOPTABLE on that alone - the bar also requires the same "
              "sign in both eras and replication on btc-fut; check both before action.")


def main():
    t0 = time.time()
    print("=" * 104, flush=True)
    print("  S6 - independent 30m/2h shadow BOOK as a feature on the 15m/1h book", flush=True)
    print("  Fixed tolerance ladder, whole grid reported, no cell selected", flush=True)
    print("=" * 104, flush=True)
    global _SIM
    from exp_tf_family import build_family_module
    from exp_s3_forensic import load_bybit, load_btcfut
    _SIM = build_family_module()
    payload = {"stage": "s6_shadow_book",
               "feature": "is the independent 30m/2h system positioned, and in which "
                          "direction, at each 15m entry (within a fixed tolerance)",
               "caveat": "the shadow book is weak OOS (F3 IS +222.4 / OOS -19.9), so "
                         "its opinion may itself be noise; its book is reported",
               "flat_kept_separate": "a shadow system not in a trade has not "
                                     "expressed an opinion",
               "tolerances_15m_bars": list(TOLERANCES),
               "hit_bar": f"same sign both eras AND trimmed-mean CI excludes zero in "
                          f"both AND n>={N_FLOOR} both buckets AND replicates on btc-fut",
               "books": {}}

    for scope in ("is", "oos"):
        print(f"\n=== bybit [{scope.upper()}] ===", flush=True)
        _print_book(f"bybit/{scope}",
                    analyse(load_bybit(scope), f"bybit/{scope}", _SIM, payload))
    print("\n=== REPLICATION: data/btc-fut ===", flush=True)
    try:
        d = load_btcfut()
        print(f"  btc-fut 1h {len(d['c1h'])} | 15m {len(d['c15'])} | "
              f"1m {len(d['fine'])}", flush=True)
        _print_book("btcfut", analyse(d, "btcfut", _SIM, payload))
    except Exception as e:
        payload["books"]["btcfut"] = {"error": f"{type(e).__name__}: {e}"}
        print(f"  FAILED: {type(e).__name__}: {e}", flush=True)

    payload["verdict"] = _verdict(payload)
    payload["elapsed_sec"] = round(time.time() - t0, 2)
    OUT.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    print("\n" + "=" * 104)
    print("  VERDICT:", payload["verdict"], flush=True)
    print(f"wrote {OUT} ({payload['elapsed_sec']}s)")


if __name__ == "__main__":
    main()
