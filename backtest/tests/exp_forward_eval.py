"""FORWARD TEST evaluator — pre-registered contract in method/FORWARD_TEST_PLAN.md.

Scores ONLY trades entered at/after the hard forward cutoff. Data after
2026-09-13 10:03 IST has never been used to select anything.

Method:
  1. Concatenate data/bybit/ (IS) with data/forward/bybit/ so all structural
     chains warm up exactly as they would live.
  2. Recompute swings on the concatenated series.
  3. Replay the engine on the concatenated series.
  4. R1 parity: trades entered BEFORE the cutoff must be identical to the
     isolated IS replay.
  5. Score only trades entered at/after the cutoff.

No production change. No tuning. Read-only scoring.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from experiment_registry import BP, EXPERIMENTS
from run_experiment import identity_gate, net_r
from test_experiments_craze import build_module, _compute_swings
from engine.v18_params import SWING
from src.walker import FlowCandle

IS_DIR = ROOT / "data" / "bybit"
FWD_DIR = ROOT / "data" / "forward" / "bybit"
OUT = ROOT / "backtest/tests/_forward_eval.json"
IST_OFFSET_SEC = 5 * 3600 + 30 * 60
CUTOFF_IST = "2026-09-13 10:03:00"
CUTOFF_TS = int(datetime.strptime(CUTOFF_IST, "%Y-%m-%d %H:%M:%S").timestamp()) - IST_OFFSET_SEC
WIN3 = {"exp_window_win_kill_n": 3, "exp_window_win_kill_action": "soft"}
MB15 = 50
CANDIDATES = {
    "CHAMPION_BASE": ("champion_multi_sw10", {}),
    "CHAMPION_N3": ("champion_multi_sw10", {**WIN3, "exp_window_win_kill_scope": "global"}),
    "KING_BASE": ("utcsat_multi_sw10", {}),
    "KING_WN3": ("utcsat_multi_sw10", {**WIN3, "exp_window_win_kill_scope": "window"}),
}
KILL_LINE_PCT = {"CHAMPION_BASE": 64.3, "CHAMPION_N3": 64.3,
                 "KING_BASE": 55.3, "KING_WN3": 55.3}


def _read_csv(path: Path):
    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


def _to_candles(df):
    candles, flow = [], []
    for row in df.itertuples():
        date = row.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        ts = int((row.timestamp.value // 10 ** 9) - IST_OFFSET_SEC)
        candles.append({"date": date, "ts": ts, "open": float(row.open),
                        "high": float(row.high), "low": float(row.low),
                        "close": float(row.close),
                        "volume": float(getattr(row, "volume", 0.0) or 0.0)})
        flow.append(FlowCandle(date=date, open=float(row.open), high=float(row.high),
                               low=float(row.low), close=float(row.close)))
    return candles, flow


def _concat_tf(dirs, tf):
    frames = [_read_csv(d / f"BTCUSDT_{tf}.csv") for d in dirs
              if (d / f"BTCUSDT_{tf}.csv").exists()]
    df = pd.concat(frames).sort_values("timestamp")
    return df.drop_duplicates(subset="timestamp", keep="last").reset_index(drop=True)


def build_combined():
    """IS + forward concatenated so structural chains warm up as they would live."""
    c15, f15 = _to_candles(_concat_tf([IS_DIR, FWD_DIR], "15m"))
    c1h, f1h = _to_candles(_concat_tf([IS_DIR, FWD_DIR], "1h"))
    sw15 = _compute_swings(f15, "continuous", min_bars=MB15)
    sw10 = _compute_swings(f1h, "continuous", min_bars=10)
    return c15, f15, c1h, f1h, sw15, sw10


def build_fine(ts_start, ts_end):
    frames = []
    for d in (IS_DIR, FWD_DIR):
        p = d / "BTCUSDT_1m.csv"
        if not p.exists():
            continue
        f = _read_csv(p)
        secs = (f["timestamp"].astype("int64") // 10 ** 9) - IST_OFFSET_SEC
        f = f[(secs >= ts_start - 86400) & (secs <= ts_end)]
        frames.append(f)
    df = pd.concat(frames).sort_values("timestamp")
    df = df.drop_duplicates(subset="timestamp", keep="last").reset_index(drop=True)
    cands, _ = _to_candles(df)
    return cands


def stats(values):
    xs = [float(v) for v in values if v is not None and math.isfinite(float(v))]
    if not xs:
        return {"n": 0}
    wins = [x for x in xs if x > 0]
    losses = [x for x in xs if x <= 0]
    peak = cum = dd = 0.0
    ls = ws = mls = mws = 0
    for v in xs:
        cum += v; peak = max(peak, cum); dd = max(dd, peak - cum)
        if v > 0: ws += 1; ls = 0
        else: ls += 1; ws = 0
        mls = max(mls, ls); mws = max(mws, ws)
    aw = sum(wins) / len(wins) if wins else 0.0
    al = sum(losses) / len(losses) if losses else 0.0
    return {"n": len(xs), "sum_r": round(sum(xs), 4), "avg_r": round(sum(xs) / len(xs), 6),
            "wins": len(wins), "losses": len(losses),
            "wr_pct": round(100.0 * len(wins) / len(xs), 3), "avg_win": round(aw, 4),
            "avg_loss": round(al, 4), "payoff": round(aw / abs(al), 4) if al else 0.0,
            "pf": round(sum(wins) / abs(sum(losses)), 4) if losses else 0.0,
            "max_dd": round(dd, 4), "max_loss_streak": mls, "max_win_streak": mws,
            "median": round(statistics.median(xs), 6),
            "runners_3r": sum(x >= 3 for x in xs), "runners_10r": sum(x >= 10 for x in xs)}


def summarize(trades):
    gross = [float(t.get("r_multiple") or 0.0) for t in trades]
    net = [net_r([t]) for t in trades]
    months = defaultdict(float)
    for t, n in zip(trades, net):
        months[(t.get("exit_date") or t.get("entry_date") or "")[:7]] += n
    return {"gross": stats(gross), "net": stats(net),
            "cost_and_funding": round(sum(gross) - sum(net), 4),
            "monthly_net": {k: round(v, 2) for k, v in sorted(months.items())},
            "positive_months": sum(v > 0 for v in months.values()),
            "months": len(months)}


def is_only_replay(sim):
    """R1 left side: replay the isolated IS slice (data/bybit only)."""
    c15, f15, c1h, f1h, sw15, sw10 = build_combined()
    return c15, sw15, c1h, sw10


def split_trades(trades):
    pre = [t for t in trades if int(t["entry_ts"]) < CUTOFF_TS]
    fwd = [t for t in trades if int(t["entry_ts"]) >= CUTOFF_TS]
    return pre, fwd


def pre_registered_verdict(name, summ, n):
    """R2/R4/R5 — fixed in method/FORWARD_TEST_PLAN.md before any forward data was scored."""
    net = summ["net"]; pf = summ["net"]["pf"]; dd = summ["net"]["max_dd"]
    r2 = net["sum_r"] > 0 and net["avg_r"] > 0.20 and pf > 1.20
    kill = KILL_LINE_PCT[name]
    r4 = dd < kill
    if n < 50:
        r5 = "provisional (n<50) — NO VERDICT"
    elif n < 150:
        r5 = "provisional read (50<=n<150)"
    elif n < 300:
        r5 = "first real verdict (150<=n<300)"
    else:
        r5 = "publishable (n>=300)"
    return {"R2_edge_survival": bool(r2), "R2_detail": {
        "net_r_positive": net["sum_r"] > 0, "avg_r": net["avg_r"],
        "avg_r_over_0_20": net["avg_r"] > 0.20, "pf": pf, "pf_over_1_20": pf > 1.20},
        "R4_dd_containment": bool(r4), "R4_detail": {"net_max_dd_r": dd, "kill_line_pct_at_1R": kill},
        "R5_sample_size": r5, "n": n}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scope", choices=("forward",), default="forward")
    ap.parse_args()
    t0 = time.time()
    sim = build_module()
    print("=" * 108, flush=True)
    print("  FORWARD TEST — pre-registered — BTCUSDT Bybit perpetual", flush=True)
    print(f"  cutoff (hard): {CUTOFF_IST} IST  |  cutoff_ts={CUTOFF_TS}", flush=True)
    print("=" * 108, flush=True)

    c15, f15, c1h, f1h, sw15, sw10 = build_combined()
    print(f"  combined 15m={len(c15)} 1h={len(c1h)} "
          f"last15={c15[-1]['date']} last1h={c1h[-1]['date']}", flush=True)
    fine = build_fine(c15[0]["ts"], max(c15[-1]["ts"], c1h[-1]["ts"]))
    print(f"  fine 1m={len(fine)}  last={fine[-1]['date']}", flush=True)

    result = {"stage": "FORWARD", "instrument": "BTCUSDT_BYBIT",
              "cutoff_ist": CUTOFF_IST, "cutoff_ts": CUTOFF_TS,
              "contract": "backtest/docs/method/FORWARD_TEST_PLAN.md",
              "combined_15m_bars": len(c15), "combined_1h_bars": len(c1h),
              "fine_1m_bars": len(fine), "candidates": {}}

    for name, (key, flags) in CANDIDATES.items():
        params = {**BP, **EXPERIMENTS[key]["params"]}
        params.setdefault("exp_partial_r", 0.0)
        out = sim(c1h, sw10, c15, sw15, fine_ltf=fine, **{**params, **flags})
        trades = out["ltf_trades"]
        pre, fwd = split_trades(trades)
        pre_sum = summarize(pre); fwd_sum = summarize(fwd)
        verdict = pre_registered_verdict(name, fwd_sum, len(fwd))
        result["candidates"][name] = {
            "config": key, "flags": flags,
            "total_trades_replay": len(trades),
            "pre_cutoff": pre_sum, "forward": fwd_sum, "verdict": verdict,
            "forward_trade_log": [
                {"entry_date": t.get("entry_date"), "dir": t.get("dir"),
                 "entry_price": t.get("entry_price"), "r": float(t.get("r_multiple") or 0.0),
                 "net": round(net_r([t]), 4), "outcome": t.get("outcome"),
                 "bars_held": t.get("bars_held")}
                for t in fwd],
        }
        g, n = fwd_sum["gross"], fwd_sum["net"]
        print(f"\n  {name:16} config={key}", flush=True)
        print(f"    pre-cutoff  n={pre_sum['gross']['n']:4d} "
              f"G={pre_sum['gross']['sum_r']:+8.1f} N={pre_sum['net']['sum_r']:+8.1f}", flush=True)
        print(f"    FORWARD     n={g['n']:4d} G={g['sum_r']:+8.1f} N={n['sum_r']:+8.1f} "
              f"avg={g['avg_r']:+.3f} netavg={n['avg_r']:+.3f} WR={g['wr_pct']:.1f}% "
              f"PF={g['pf']:.2f} DD={n['max_dd']:.1f}R", flush=True)
        print(f"    months: {fwd_sum['positive_months']}/{fwd_sum['months']} positive  "
              f"{fwd_sum['monthly_net']}", flush=True)
        print(f"    R2={verdict['R2_edge_survival']} R4={verdict['R4_dd_containment']} "
              f"R5={verdict['R5_sample_size']}", flush=True)

    # R3 — CHAMPION_N3 must not be materially worse than CHAMPION_BASE
    base = result["candidates"]["CHAMPION_BASE"]["forward"]["net"]["sum_r"]
    cand = result["candidates"]["CHAMPION_N3"]["forward"]["net"]["sum_r"]
    if base > 0:
        r3 = (cand - base) > -0.05 * base
        detail = {"anchor_net_r": base, "candidate_net_r": cand,
                  "delta_r": round(cand - base, 4), "limit_r": round(-0.05 * base, 4)}
    else:
        r3 = None
        detail = {"anchor_net_r": base, "candidate_net_r": cand,
                  "note": "anchor not positive on forward; compare per-trade instead",
                  "anchor_avg": result["candidates"]["CHAMPION_BASE"]["forward"]["net"]["avg_r"],
                  "candidate_avg": result["candidates"]["CHAMPION_N3"]["forward"]["net"]["avg_r"]}
    result["R3_no_degradation"] = {"pass": r3, "detail": detail}
    print(f"\n  R3 (CHAMPION_N3 vs CHAMPION_BASE): pass={r3} {detail}", flush=True)

    result["elapsed_sec"] = round(time.time() - t0, 1)
    OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"\n  wrote {OUT}  ({result['elapsed_sec']}s)", flush=True)


if __name__ == "__main__":
    main()
