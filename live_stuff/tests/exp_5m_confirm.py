"""5-MINUTE CONFIRMATION DELAY - the engine's own built-but-disabled entry gate.

THE FINDING THAT PROMPTED THIS
==============================
Recon of the built engine text found a 5-minute confirmation system that is
**fully implemented and off by default**:

    exp_5m_confirm=0        <- the switch
    exp_5m_wait_min=240     <- 4h bound on the wait
    exp_5m_data=None        <- the 5m candle list
    five_m_stats -> {"candidates","confirmed","stop_cancelled","timeout","delayed"}

The shipped logic (v18 built text, ~L1466-1507), read carefully:

  * at a 15m signal, `entry_inst = ltf_bar_ts + 900` (the knowable instant);
  * scan 5m bars whose CLOSE falls in `[entry_inst, entry_inst + wait]`, where a
    5m bar stamped t closes at t+300 (causally correct, matches the repo's
    convention);
  * a 5m bar **confirms** when its close breaks the extreme of the PREVIOUS 3
    5m bars - `close > max(prev 3 highs)` for long, `close < min(prev 3 lows)`
    for short. `if _exp_k < 3: continue` enforces the lookback exists;
  * entry is at that 5m bar's OPEN, taken from the 1m fine data;
  * if the stop is touched between the signal and the confirm, the trade is
    CANCELLED (`stop_cancelled`), not merely deferred;
  * `busy_until`, `cooldown_bars` and `exp_max_concurrent` are all RE-CHECKED at
    the new, later entry time - so a delayed entry cannot silently stack.

This is a **delay with cancellation**, not a plain skip, which matters: the wick
work showed ordinary skip costs -39.0R IS because the freed slot admits a
replacement, while gray was +28.1R. This gate is much closer to gray in spirit.
Whether it actually behaves that way is an open question this run answers.

WHY IT IS STILL A NULL-RISK EXPERIMENT
======================================
`exp_5m_wait_min` is a real knob, so multiplicity is handled by a FIXED
pre-registered ladder with the whole grid reported and no cell selected - the
same discipline as log 110. And per Rule 13, buckets are judged on the trimmed
mean, not avgR, because the books are tail-concentrated (top 5% of trades carry
>100% of the net, Rule 14).

PRE-REGISTERED HIT BAR (all required)
  1. same sign in both eras, AND
  2. trimmed-mean bootstrap 95% CI excludes zero in BOTH eras, AND
  3. replicates on the independent dataset (data/btc has its own 5m file), AND
  4. no reliance on a single ladder step - the direction must be consistent
     across the wait ladder, not just significant at one rung.

Data: 5m exists for data/bybit (22MB), data/unseen/bybit (12MB) and data/btc
(23MB) - not for btc-fut, so replication uses data/btc.

Run: $env:PYTHONIOENCODING='utf-8'; python -u exp_5m_confirm.py
"""
from __future__ import annotations

import json
import random
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

OUT = ROOT / "live_stuff/tests/_5m_confirm.json"
M5, M15 = 300, 900
# fixed ladder, all reported, no cell selected
WAITS = (60, 120, 240, 480)
LANES = (("champion", "champion_multi_sw10"),
         ("utcsat", "utcsat_multi_sw10"),
         ("age10", "age10_dirmatch_swingpause_single_sw10"))
BYBIT_BASE = {"champion": {"is": (500, 325.8), "oos": (279, 70.2)},
              "utcsat": {"is": (454, 358.9), "oos": (253, 60.2)},
              "age10": {"is": (130, 435.7), "oos": (76, 43.2)}}
YEARS = {"is": 3.67, "oos": 2.0, "btc": 3.67}



def boot_diff(a, b, n_boot=20000, seed=20260927):
    """Bootstrap the TRIMMED-MEAN DIFFERENCE (book - control) against ZERO.

    A first version of this bootstrapped each book's trimmed mean against 0,
    which answers "is this book profitable?" - not the question being asked.
    Verified wrong: two halves of one pool from the same distribution produced a
    CI that excluded zero, because resampling WITHIN each half measures each
    half's own mean, never the difference. Comparing a gated book to its own
    control requires resampling each side independently and differencing, so
    that is what this does.
    """
    if len(a) < 30 or len(b) < 30:
        return {"diff": None, "ci95": None, "p": None, "n_a": len(a), "n_b": len(b)}

    def tm(x):
        s = sorted(x)
        k = int(len(s) * 0.05)
        t = s[k:len(s) - k] if len(s) - 2 * k > 0 else s
        return sum(t) / len(t)
    rng = random.Random(seed)
    obs = tm(a) - tm(b)
    draws = []
    for _ in range(n_boot):
        sa = tm([a[rng.randrange(len(a))] for _ in range(len(a))])
        sb = tm([b[rng.randrange(len(b))] for _ in range(len(b))])
        draws.append(sa - sb)
    draws.sort()
    pl = sum(1 for x in draws if x <= 0) / n_boot
    pg = sum(1 for x in draws if x >= 0) / n_boot
    return {"diff": round(obs, 4),
            "ci95": [round(draws[int(0.025 * n_boot)], 4),
                     round(draws[int(0.975 * n_boot)], 4)],
            "p": round(min(1.0, 2.0 * min(pl, pg)), 4),
            "n_a": len(a), "n_b": len(b)}


def shape(rs):
    n = len(rs)
    if n == 0:
        return {"n": 0}
    s = sorted(rs)
    w = [x for x in rs if x > 0]
    loss = -sum(x for x in rs if x < 0)
    k = int(n * 0.05)
    tr = s[k:n - k] if n - 2 * k > 0 else s
    return {"n": n, "net": round(sum(rs), 1), "mean": round(sum(rs) / n, 4),
            "median": round(statistics.median(rs), 4),
            "trimmed_mean": round(sum(tr) / len(tr), 4),
            "stdev": round(statistics.pstdev(rs), 4),
            "wr": round(100.0 * len(w) / n, 1),
            "pf": round(sum(w) / loss, 3) if loss > 1e-9 else None,
            "top5_share_pct": round(100.0 * sum(s[-max(1, n // 20):]) /
                                    max(sum(rs), 1e-9), 1)}


# ---------------------------------------------------------------- data
def _read(path):
    from exp_s3_forensic import _read_tf
    return _read_tf(path)


def _load_1m(path, t0, t1):
    from exp_s3_forensic import load_1m
    return load_1m(path, t0, t1)


def _compute_swings(flow, mode, min_bars):
    from src.btc.btc_routes import _compute_swings as f
    return f(flow, mode, min_bars=min_bars)


def _5m_candles(path):
    """5m CSV -> candle dicts on the engine's convention: ts is UTC epoch and a
    bar stamped t closes at t+300, which is exactly what the built engine
    assumes (it does sorted(..., key=int(c['ts'])+300)).

    Reuses exp_s3_forensic._read_tf so the IST -> UTC conversion is identical to
    every other load in this programme rather than re-derived.
    """
    df = _read(path)
    return [{"date": r.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
             "ts": int(r.ts), "open": float(r.open), "high": float(r.high),
             "low": float(r.low), "close": float(r.close)}
            for r in df.itertuples(index=False)]


def load_book(era):
    """(data, five_m_candles) for one era, on the shape every harness here uses."""
    from run_experiment import get_data
    from test_4_new_concepts import load_unseen, load_fine_1m
    from exp_shadow_tf import _flow
    from exp_s3_forensic import _candles
    from engine.v18_params import SWING
    if era == "is":
        d = get_data()
        data = {"c15": d["c15"], "f15": d["f15"], "c1h": d["c1h"], "f1h": d["f1h"],
                "sw15": d["sw15"], "sw10": d["sw10"], "fine": d["fine"],
                "sw20": _compute_swings(d["f1h"], "continuous", min_bars=20)}
        five = _5m_candles(ROOT / "data/bybit/BTCUSDT_5m.csv")
    elif era == "oos":
        (c15, f15), (c1h, f1h) = load_unseen("15m"), load_unseen("1h")
        data = {"c15": c15, "f15": f15, "c1h": c1h, "f1h": f1h,
                "fine": load_fine_1m(c15[0]["ts"], c15[-1]["ts"]),
                "sw15": _compute_swings(f15, "continuous",
                                        min_bars=SWING["min_bars_15m"]),
                "sw10": _compute_swings(_flow(c1h), "continuous", min_bars=10),
                "sw20": _compute_swings(_flow(c1h), "continuous", min_bars=20)}
        five = _5m_candles(ROOT / "data/unseen/bybit/BTCUSDT_5m.csv")
    else:  # btc - independent dataset with its own 5m file
        d = ROOT / "data/btc"
        c15, f15 = _candles(_read(d / "BTCUSDT_15m.csv"))
        c1h, f1h = _candles(_read(d / "BTCUSDT_1h.csv"))
        data = {"c15": c15, "f15": f15, "c1h": c1h, "f1h": f1h,
                "fine": _load_1m(d / "BTCUSDT_1m.csv", c15[0]["ts"], c15[-1]["ts"]),
                "sw15": _compute_swings(f15, "continuous",
                                        min_bars=SWING["min_bars_15m"]),
                "sw10": _compute_swings(_flow(c1h), "continuous", min_bars=10),
                "sw20": _compute_swings(_flow(c1h), "continuous", min_bars=20)}
        five = _5m_candles(d / "BTCUSDT_5m.csv")
    return data, five


def run_arm(sim, data, five, lane_key, wait_min, use_5m):
    """One engine call. `use_5m=False` is the control (gate off).

    Calls the engine DIRECTLY rather than through exp_sizing_combo.run, because
    that helper returns only out["ltf_trades"] and throws away the
    `five_m_stats` dict. Without the breakdown (candidates / confirmed /
    stop_cancelled / timeout) a bad result cannot be diagnosed - we would not
    know whether the gate cancelled good trades or entered later at worse
    prices. Those are very different stories and the writeup needs one of them.
    """
    from run_experiment import net_r
    from experiment_registry import BP, EXPERIMENTS
    flags = {}
    if use_5m:
        flags = {"exp_5m_confirm": 1, "exp_5m_wait_min": wait_min,
                 "exp_5m_data": five}
    params = {**BP, **EXPERIMENTS[lane_key]["params"]}
    out = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
              fine_ltf=data["fine"], **params, **flags)
    trades = out["ltf_trades"] if isinstance(out, dict) else out
    return trades, [net_r([t]) for t in trades], (
        out.get("five_m_stats") if isinstance(out, dict) else None)


def equity(trades, rs):
    """maxDD on the trade-indexed equity curve, same convention as elsewhere."""
    peak = cum = dd = 0.0
    for x in rs:
        cum += x
        peak = max(peak, cum)
        dd = max(dd, peak - cum)
    sh = shape(rs)
    sh["max_dd"] = round(dd, 1)
    return sh


def _verdict(p):
    rows = []
    for book, res in p["books"].items():
        if "error" in res:
            continue
        for lane, c in res.items():
            for w, d in c["waits"].items():
                b = d["boot"]
                if b["ci95"] is not None:
                    rows.append((book, lane, w, b))
    if not rows:
        return "no book had n>=30 to bootstrap. CLOSED."
    sig = [r for r in rows if r[3]["ci95"][0] > 0 or r[3]["ci95"][1] < 0]
    if not sig:
        return (f"0/{len(rows)} bootstrapped trimmed-mean DIFFERENCE CIs (book - "
                f"control) exclude zero across the whole wait ladder and every book. "
                f"CLOSED - the 5m confirmation delay does not improve the book.")
    return (f"{len(sig)}/{len(rows)} cells exclude zero: " +
            "; ".join(f"{b}/{l}/w{w} {bt['diff']:+.2f}" for b, l, w, bt in sig[:8]) +
            ". NOT ADOPTABLE on that alone - the bar also requires the same sign in "
            "both eras, consistency across the wait ladder, and replication on data/btc.")


def _bybit_arms(sim, data, five, era, payload, tag):
    for lane, key in LANES:
        ctl_t, ctl_r, _ = run_arm(sim, data, five, key, 0, False)
        ctl = equity(ctl_t, ctl_r)
        if era in ("is", "oos") and lane == "champion":
            en, ev = BYBIT_BASE[lane][era]
            assert len(ctl_t) == en and abs(sum(ctl_r) - ev) < 0.5, \
                f"CONTROL FAIL {era}/{lane}: {len(ctl_t)}/{sum(ctl_r):.1f} != {en}/{ev}"
        print(f"  {lane:<9} CONTROL n={ctl['n']:>3} net={ctl['net']:>+7.1f} "
              f"trim={ctl['trimmed_mean']:>+5.2f} PF={ctl['pf']:>4.2f} "
              f"DD={ctl['max_dd']:>5.1f} [EXACT]", flush=True)
        rows = {}
        for w in WAITS:
            t, r, st = run_arm(sim, data, five, key, w, True)
            s = equity(t, r)
            f5 = st or {}
            rows[str(w)] = {"book": s, "boot": boot_diff(r, ctl_r),
                            "five_m_stats": st,
                            "vs_control_net": round(s["net"] - ctl["net"], 1),
                            "vs_control_trim": round(s["trimmed_mean"] -
                                                     ctl["trimmed_mean"], 4)}
            print(f"     wait {w:>3}m n={s['n']:>3} net={s['net']:>+7.1f} "
                  f"trim={s['trimmed_mean']:>+5.2f} med={s['median']:>+5.2f} "
                  f"PF={(s['pf'] or 0):>4.2f} DD={s['max_dd']:>5.1f} "
                  f"| dNet={rows[str(w)]['vs_control_net']:>+7.1f} "
                  f"| dtrim={rows[str(w)]['boot']['diff']:>+5.2f} "
                  f"CI{rows[str(w)]['boot']['ci95']} "
                  f"| cand={f5.get('candidates',0)} conf={f5.get('confirmed',0)} "
                  f"stopx={f5.get('stop_cancelled',0)} tmo={f5.get('timeout',0)}",
                  flush=True)
        payload["books"].setdefault(tag, {})[lane] = {"control": ctl, "waits": rows}


def main():
    t0 = time.time()
    print("=" * 104, flush=True)
    print("  5-MINUTE CONFIRMATION DELAY - the engine's own built-but-disabled gate", flush=True)
    print("  confirm = a 5m close breaks the extreme of the previous 3 5m bars", flush=True)
    print("  fixed wait ladder, whole grid reported, no cell selected", flush=True)
    print("=" * 104, flush=True)
    from exp_tf_family import build_family_module
    sim = build_family_module()
    payload = {"stage": "5m_confirm",
               "mechanism": "delay entry until a 5m close breaks the prior-3 extreme; "
                            "cancel if the stop is touched while waiting",
               "contract": "a 5m bar stamped t closes at t+300 (engine uses ts+300)",
               "wait_ladder_min": list(WAITS), "fixed_grid_no_cell_selected": True,
               "hit_bar": "same sign both eras AND trimmed-mean CI excludes zero in both "
                          "AND replicates on data/btc AND direction consistent across "
                          "the whole wait ladder",
               "books": {}}

    for era in ("is", "oos"):
        print(f"\n=== bybit [{era.upper()}] ===", flush=True)
        data, five = load_book(era)
        print(f"  5m bars: {len(five)}  span {five[0]['date']} -> {five[-1]['date']}",
              flush=True)
        _bybit_arms(sim, data, five, era, payload, f"bybit/{era}")

    print("\n=== REPLICATION: data/btc ===", flush=True)
    try:
        data, five = load_book("btc")
        print(f"  5m bars: {len(five)}", flush=True)
        for lane, key in LANES:
            ctl_t, ctl_r, _ = run_arm(sim, data, five, key, 0, False)
            ctl = equity(ctl_t, ctl_r)
            rows = {}
            for w in WAITS:
                t, r, st = run_arm(sim, data, five, key, w, True)
                rows[str(w)] = {"book": equity(t, r), "boot": boot_diff(r, ctl_r),
                                "five_m_stats": st}
            payload["books"].setdefault("btc", {})[lane] = {"control": ctl, "waits": rows}
            print(f"  {lane:<9} CONTROL n={ctl['n']:>3} net={ctl['net']:>+7.1f} | " +
                  "  ".join(f"w{w} n={rows[str(w)]['book']['n']:>3} "
                            f"net={rows[str(w)]['book']['net']:>+7.1f}" for w in WAITS),
                  flush=True)
    except Exception as e:
        payload["books"]["btc"] = {"error": f"{type(e).__name__}: {e}"}
        print(f"  FAILED: {type(e).__name__}: {e}", flush=True)

    payload["verdict"] = _verdict(payload)
    payload["elapsed_sec"] = round(time.time() - t0, 2)
    OUT.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    print("\n" + "=" * 104)
    print("  VERDICT:", payload["verdict"], flush=True)
    print(f"wrote {OUT} ({payload['elapsed_sec']}s)")


if __name__ == "__main__":
    main()
