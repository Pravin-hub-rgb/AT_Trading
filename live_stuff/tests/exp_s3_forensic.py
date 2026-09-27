"""S3 deep dive: is "2h-opposing trades are better" a real mean shift, or a
distribution-shape artifact?

WHY THIS FILE EXISTS
====================
Log 108 found the only shadow-TF pattern that was consistent: trades pushing
AGAINST the slow 2h context had higher avgR in 6/6 cells (both eras, all three
lanes) - the exact opposite of the pre-registered mechanism, and never
significant (every p > 0.27, every CI straddling zero). It was recorded as a
pattern, not an edge.

This does NOT chase it with more predicates. There is one obvious next predicate
("keep trades where 30m and 2h both oppose") and running it would be the 6.026
fishing failure. Instead this buys POWER and tests the ALTERNATIVE EXPLANATION,
which is the only way to learn something:

  A1  SHAPE. Is the avgR gap a shift in the MEAN, or is it a tail/variance
      artifact? Counter-trend trades in crypto tend to be wider and rarer. If
      the opposing bucket merely has fatter tails, then a higher avgR is a
      property of its risk profile, not of its edge, and no filter should chase
      it. Reported: mean vs MEDIAN vs 5%-TRIMMED mean vs stdev, plus payoff
      ratio and win rate. The trimmed mean and the median are the two numbers
      that a tail artifact cannot fake. This is the decisive diagnostic and it
      needs no new data.
  A2  REPLICATION on an independent dataset (data/btc-fut, 49,974 1h rows,
      2020-12 -> 2026). Same predicate, same code, same lanes. If the direction
      holds on a second book it is a property of the strategy; if it flips, it
      was a property of the bybit snapshot. NOTE: btc-fut covers the SAME dates
      as bybit IS+OOS, so this is replication across datasets, NOT extra
      calendar time - stated so nobody reads it as more n than it is.
  A3  DOSE-RESPONSE, only if A1 shows a genuine trimmed-mean shift: does the
      effect grow with 2h swing magnitude? The fade mechanism predicts yes. This
      is mechanistically motivated rather than a blind sweep, but it introduces
      a magnitude split, so it is gated behind A1 deliberately.

THE NULL IS PRE-REGISTERED
==========================
A1 verdict: if the trimmed-mean and median gaps collapse toward zero while the
raw mean gap persists, the pattern is a tail artifact -> CLOSED, and no filter
is proposed. If the trimmed mean moves with the raw mean in both eras, A3 runs.
A2 never rescues a failed A1; it is reported alongside, not instead.

Run: $env:PYTHONIOENCODING='utf-8'; python -u exp_s3_forensic.py
"""
from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

OUT = ROOT / "live_stuff/tests/_s3_forensic.json"
M15, M30, H1, H2 = 900, 1800, 3600, 7200
YEARS = {"is": 3.67, "oos": 2.0}
LANES = (("champion", "champion_multi_sw10"),
         ("utcsat", "utcsat_multi_sw10"),
         ("age10", "age10_dirmatch_swingpause_single_sw10"))
IST_OFFSET_SEC = 19800


def shape(rs):
    """Full return-shape description. mean is the number that fooled us; the
    median and the trimmed mean are the ones a tail artifact cannot fake."""
    n = len(rs)
    if n == 0:
        return {"n": 0}
    s = sorted(rs)
    wins = [x for x in rs if x > 0]
    loss = [x for x in rs if x < 0]
    k = int(n * 0.05)
    trimmed = s[k:n - k] if n - 2 * k > 0 else s
    aw = sum(wins) / len(wins) if wins else 0.0
    al = abs(sum(loss) / len(loss)) if loss else 0.0
    return {
        "n": n, "mean": round(sum(rs) / n, 4),
        "median": round(statistics.median(rs), 4),
        "trimmed_mean": round(sum(trimmed) / len(trimmed), 4),
        "stdev": round(statistics.pstdev(rs), 4),
        "wr": round(100.0 * len(wins) / n, 1),
        "avg_win": round(aw, 4), "avg_loss": round(al, 4),
        "payoff": round(aw / al, 4) if al > 1e-9 else None,
        "p10": round(s[int(0.10 * n)], 3), "p90": round(s[int(0.90 * n)], 3),
        "best": round(max(rs), 2), "worst": round(min(rs), 2),
        "top5_share_pct": round(100.0 * sum(s[-max(1, n // 20):]) /
                                max(sum(rs), 1e-9), 1),
    }


def gaps(a, b):
    """agree-minus-oppose for every shape statistic, so the reader sees which
    statistics actually move and which do not."""
    out = {}
    for k in ("mean", "median", "trimmed_mean", "stdev", "wr", "payoff"):
        if a.get(k) is not None and b.get(k) is not None:
            out[k] = round(a[k] - b[k], 4)
    return out


# ---------------------------------------------------------------- data loading
def _read_tf(path):
    """CSV -> candle dicts + epoch ts, using the repo's IST -> UTC convention."""
    import sys as _s
    _s.path.insert(0, str(ROOT / "backend"))
    import pandas as pd
    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = (df.sort_values("timestamp").drop_duplicates(subset="timestamp", keep="last")
            .reset_index(drop=True))
    df["ts"] = (df["timestamp"].astype("int64") // 10 ** 9) - IST_OFFSET_SEC
    return df


def _candles(df):
    from src.walker import FlowCandle
    cs, fl = [], []
    for r in df.itertuples(index=False):
        d = r.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        o, h, lo, c = float(r.open), float(r.high), float(r.low), float(r.close)
        v = float(getattr(r, "volume", 0.0) or 0.0)
        cs.append({"date": d, "ts": int(r.ts), "open": o, "high": h, "low": lo,
                   "close": c, "volume": v})
        fl.append(FlowCandle(date=d, open=o, high=h, low=lo, close=c))
    return cs, fl


def load_1m(path, t0, t1):
    df = _read_tf(path)
    df = df[(df["ts"] >= t0) & (df["ts"] <= t1)]
    return [{"date": r.timestamp.strftime("%Y-%m-%d %H:%M:%S"), "ts": int(r.ts),
             "open": float(r.open), "high": float(r.high), "low": float(r.low),
             "close": float(r.close)} for r in df.itertuples(index=False)]


def load_bybit(scope):
    from run_experiment import get_data
    from test_4_new_concepts import load_unseen, load_fine_1m
    from exp_shadow_tf import _flow
    if scope == "is":
        d = get_data()
        return {"c15": d["c15"], "f15": d["f15"], "c1h": d["c1h"], "f1h": d["f1h"],
                "sw15": d["sw15"], "sw10": d["sw10"],
                "sw20": _compute_swings(d["f1h"], "continuous", min_bars=20),
                "fine": d["fine"]}
    (c15, f15), (c1h, f1h) = load_unseen("15m"), load_unseen("1h")
    from engine.v18_params import SWING
    return {"c15": c15, "f15": f15, "c1h": c1h, "f1h": f1h,
            "sw15": _compute_swings(f15, "continuous", min_bars=SWING["min_bars_15m"]),
            "sw10": _compute_swings(_flow(c1h), "continuous", min_bars=10),
            "sw20": _compute_swings(_flow(c1h), "continuous", min_bars=20),
            "fine": load_fine_1m(c15[0]["ts"], c15[-1]["ts"])}


def load_btcfut():
    """Independent dataset: data/btc-fut, 49,974 1h rows from 2020-12-31.

    Same calendar span as bybit IS+OOS, so this is REPLICATION ACROSS DATASETS,
    not extra time. The 1m file is 174MB so it is read once and filtered, not
    loaded whole into the harness.
    """
    from engine.v18_params import SWING
    from exp_shadow_tf import _flow
    d = ROOT / "data/btc-fut"
    c15, f15 = _candles(_read_tf(d / "BTCUSDT_15m.csv"))
    c1h, f1h = _candles(_read_tf(d / "BTCUSDT_1h.csv"))
    return {"c15": c15, "f15": f15, "c1h": c1h, "f1h": f1h,
            "sw15": _compute_swings(f15, "continuous", min_bars=SWING["min_bars_15m"]),
            "sw10": _compute_swings(_flow(c1h), "continuous", min_bars=10),
            "sw20": _compute_swings(_flow(c1h), "continuous", min_bars=20),
            "fine": load_1m(d / "BTCUSDT_1m.csv", c15[0]["ts"], c15[-1]["ts"])}


# ---------------------------------------------------------------- S3 labelling
def s3_split(data, scope):
    """Run the shipped book, label every trade by 2h-swing agreement, return shapes.

    Reuses exp_shadow_tf's causality-checked helpers rather than re-deriving
    them, so the closed-bar arithmetic that log 108 unit-tested is the exact
    arithmetic used here. Swings use confirmed_at_idx (never the backdated
    seg.start_idx), verified 300/300 against confirmed_at_time in log 108.
    """
    from exp_shadow_tf import (last_closed, dir_series, htf_swing_events,
                               swing_dir_at, tdir)
    from exp_htf_2h import resample_2h, flow_2h
    from exp_sizing_combo import run as sim_fn
    from run_experiment import net_r
    from experiment_registry import BP, EXPERIMENTS

    c2h = resample_2h(data["c1h"])
    t2h, cl2h, d2h = dir_series(c2h, H2)
    ev2h = htf_swing_events(c2h, _compute_swings(flow_2h(c2h), "continuous",
                                                 min_bars=5))
    htf = {"c1h": data["c1h"], "sw20": data["sw20"], "sw10": data["sw10"]}
    ltf = {"c15": data["c15"], "sw15": data["sw15"]}
    out = {}
    for lane, key in LANES:
        params = {**BP, **EXPERIMENTS[key]["params"]}
        trades = sim_fn(_SIM, {**htf, **ltf, "fine": data["fine"]}, params)
        rs = [net_r([t]) for t in trades]
        agree, oppose = [], []
        for t, r in zip(trades, rs):
            e = int(t["entry_ts"]) + M15
            i = last_closed(t2h, cl2h, e)
            d2 = d2h[i] if i >= 0 else 0
            (agree if d2 == tdir(t) else oppose).append(r)
        out[lane] = {"total": {"n": len(rs), "net": round(sum(rs), 1)},
                     "agree": shape(agree), "oppose": shape(oppose),
                     "gap_agree_minus_oppose": gaps(shape(agree), shape(oppose))}
    return out


def _print_cell(lane, c):
    a, o, g = c["agree"], c["oppose"], c["gap_agree_minus_oppose"]
    print(f"  {lane:<9} n={c['total']['n']:>4} net={c['total']['net']:>+8.1f}")
    print(f"     agree  n={a.get('n',0):>3} mean={a.get('mean',0):>+6.2f} "
          f"median={a.get('median',0):>+6.2f} trim={a.get('trimmed_mean',0):>+6.2f} "
          f"sd={a.get('stdev',0):>5.2f} wr={a.get('wr',0):>4.1f} "
          f"top5%={a.get('top5_share_pct',0):>5.1f}")
    print(f"     oppose n={o.get('n',0):>3} mean={o.get('mean',0):>+6.2f} "
          f"median={o.get('median',0):>+6.2f} trim={o.get('trimmed_mean',0):>+6.2f} "
          f"sd={o.get('stdev',0):>5.2f} wr={o.get('wr',0):>4.1f} "
          f"top5%={o.get('top5_share_pct',0):>5.1f}")
    print(f"     gap(agree-oppose) mean={g.get('mean',0):>+6.2f} "
          f"median={g.get('median',0):>+6.2f} trim={g.get('trimmed_mean',0):>+6.2f} "
          f"sd={g.get('stdev',0):>+5.2f}", flush=True)


def _verdict(p):
    """Mean-shift vs tail-artifact, decided on the ROBUST statistics only.

    The raw mean is the number that produced the 6/6 pattern. If the trimmed
    mean and the median move with it, the shift is in the body of the
    distribution. If they move less, the gap is carried by a few large trades
    and chasing it with a filter would be trading on tail luck.
    """
    rows, mean_m, trim_m, med_m = [], 0, 0, 0
    for book, res in p["books"].items():
        if "error" in res:
            continue
        for lane, c in res.items():
            g = c["gap_agree_minus_oppose"]
            rows.append((book, lane, g))
            mean_m += g.get("mean", 0) < 0
            trim_m += g.get("trimmed_mean", 0) < 0
            med_m += g.get("median", 0) < 0
    n = len(rows)
    if n == 0:
        return "no cells produced"
    head = (f"{mean_m}/{n} cells have a lower mean in the opposing bucket, "
            f"{trim_m}/{n} on TRIMMED mean, {med_m}/{n} on MEDIAN. ")
    if trim_m == mean_m and med_m == mean_m:
        return head + ("The robust statistics agree with the raw mean, so this is "
                       "a genuine mean shift; the A3 dose-response test is warranted.")
    return head + ("The robust statistics move LESS than the raw mean, so a "
                   "substantial part of the gap is a tail/variance artifact. "
                   "CLOSED - no filter proposed.")


def _compute_swings(flow, mode, min_bars):
    """Placed before main() on purpose: the __main__ guard calls main() at import
    time, so a def below the guard would not yet exist when load_bybit needs it."""
    from src.btc.btc_routes import _compute_swings as f
    return f(flow, mode, min_bars=min_bars)


def main():
    t0 = time.time()
    print("=" * 100, flush=True)
    print("  S3 deep dive - mean shift or distribution-shape artifact?", flush=True)
    print("=" * 100, flush=True)
    global _SIM
    from exp_tf_family import build_family_module
    _SIM = build_family_module()
    payload = {"stage": "s3_forensic",
               "question": "is '2h-opposing is better' a mean shift or a tail artifact?",
               "pre_registered_null": "if trimmed-mean and median gaps collapse while "
                                      "the raw mean gap persists -> tail artifact, CLOSED",
               "btcfut_caveat": "replication across datasets, NOT extra calendar time "
                                "(btc-fut spans the same dates as bybit IS+OOS)",
               "books": {}}

    for scope in ("is", "oos"):
        print(f"\n=== bybit [{scope.upper()}] ===", flush=True)
        res = s3_split(load_bybit(scope), scope)
        payload["books"][f"bybit/{scope}"] = res
        for lane in res:
            _print_cell(lane, res[lane])

    print("\n=== REPLICATION: data/btc-fut (independent dataset) ===", flush=True)
    try:
        data = load_btcfut()
        print(f"  btc-fut 1h {len(data['c1h'])} | 15m {len(data['c15'])} | "
              f"1m {len(data['fine'])}", flush=True)
        res = s3_split(data, "btcfut")
        payload["books"]["btcfut"] = res
        for lane in res:
            _print_cell(lane, res[lane])
    except Exception as e:
        payload["books"]["btcfut"] = {"error": f"{type(e).__name__}: {e}"}
        print(f"  btc-fut replication FAILED: {type(e).__name__}: {e}", flush=True)

    payload["verdict"] = _verdict(payload)
    payload["elapsed_sec"] = round(time.time() - t0, 2)
    OUT.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    print("\n" + "=" * 100)
    print("  VERDICT:", payload["verdict"], flush=True)
    print(f"wrote {OUT} ({payload['elapsed_sec']}s)")


if __name__ == "__main__":
    main()
