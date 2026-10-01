"""Stage N — vs BTC buy&hold benchmark + risk-metrics table (descriptive).

Question: with everything reported in R so far, how does the book actually
compare to just holding BTC — total return, CAGR, Sharpe, Sortino, maxDD,
Calmar — in percent terms?

Assumptions (frozen, stated in payload):
  - Strategy: 1R = 1% of equity at month start (risk-based sizing, no
    compounding WITHIN month; monthly chain-compounding across months).
    Monthly return = sum(net_r of trades EXITING that month) * 1%.
    net_r already subtracts fees+slip+funding.
  - Buy & hold: buy at first 15m close of window, hold; monthly returns
    from month-end closes; no leverage, no funding, no costs (favorable
    to B&H, conservative for us).
  - Windows: IS 2023-01..2026-09 (data range), OOS 2021-01..2022-12.
  - Sharpe = mean(monthly)/std(monthly) * sqrt(12), rf=0; Sortino uses
    downside dev of negative months; Calmar = CAGR / maxDD%.

Subjects (cand arms): champion, utcsat, age10, trio book (all trades merged).
Descriptive only; no gate.

Run: $env:PYTHONIOENCODING='utf-8'; python -u backtest/tests/exp_buyhold_benchmark.py
"""
from __future__ import annotations

import json
import math
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from experiment_registry import BP, EXPERIMENTS
from run_experiment import get_data, identity_gate, net_r
from test_experiments_craze import build_module
from test_4_new_concepts import load_fine_1m, load_unseen
from src.btc.btc_routes import _compute_swings
from engine.v18_params import SWING

OUT = ROOT / "backtest/tests/_buyhold_benchmark_results.json"
RISK_PCT = 0.01  # 1R = 1% of equity

HALF = dict(exp_trail_half=1, exp_trail_delay_r=1.0)
SKIPD = dict(exp_skip_decisive=1)
RETEST = dict(exp_retest_fill=0.25, exp_retest_wait=240)

LANES = (
    ("champion", "champion_multi_sw10", dict(HALF, **SKIPD)),
    ("utcsat", "utcsat_multi_sw10", dict(HALF, **SKIPD)),
    ("age10", "age10_dirmatch_swingpause_single_sw10", dict(RETEST)),
)


def load_scope(scope):
    if scope == "oos":
        (c15, f15), (c1h, f1h) = load_unseen("15m"), load_unseen("1h")
        sw15 = _compute_swings(f15, "continuous", min_bars=SWING["min_bars_15m"])
        sw10 = _compute_swings(f1h, "continuous", min_bars=10)
        return {
            "c15": c15, "sw15": sw15, "c1h": c1h, "sw10": sw10,
            "fine": load_fine_1m(c15[0]["ts"], c15[-1]["ts"]),
        }
    data = get_data()
    identity_gate(data, build_module())
    return data


def run(sim, data, params, **flags):
    out = sim(
        data["c1h"], data["sw10"], data["c15"], data["sw15"],
        fine_ltf=data["fine"], **{**params, **flags},
    )
    return out["ltf_trades"] if isinstance(out, dict) else out


def strategy_months(trades):
    """month (YYYY-MM) -> return fraction (net_R * risk, chained by caller)."""
    agg = defaultdict(float)
    for t in trades:
        m = str(t.get("exit_date") or "")[:7]
        if m:
            agg[m] += net_r([t])
    return {m: v * RISK_PCT for m, v in sorted(agg.items())}


def bh_months(c15):
    """Month -> return from month-end closes; first month from first close."""
    closes = defaultdict(list)
    for c in c15:
        closes[str(c["date"])[:7]].append(float(c["close"]))
    months = sorted(closes)
    ends = {m: closes[m][-1] for m in months}
    first_px = closes[months[0]][0]
    rets = {}
    prev = first_px
    for m in months:
        rets[m] = ends[m] / prev - 1.0
        prev = ends[m]
    # first month: entry at first close of window
    rets[months[0]] = closes[months[0]][-1] / first_px - 1.0
    return rets, first_px, closes[months[-1]][-1]


def metrics(rets, label):
    """Chain-compounded stats from monthly return dict."""
    months = sorted(rets)
    if not months:
        return {"label": label, "n_months": 0}
    vals = [rets[m] for m in months]
    eq = 1.0
    peak = 1.0
    maxdd = 0.0
    for v in vals:
        eq *= (1.0 + v)
        peak = max(peak, eq)
        dd = (peak - eq) / peak
        maxdd = max(maxdd, dd)
    total = eq - 1.0
    n = len(vals)
    yrs = n / 12.0
    cagr = (eq ** (1.0 / yrs) - 1.0) if yrs > 0 and eq > 0 else None
    mean = sum(vals) / n
    var = sum((v - mean) ** 2 for v in vals) / (n - 1) if n > 1 else 0.0
    sd = math.sqrt(var)
    sharpe = (mean / sd * math.sqrt(12)) if sd > 1e-12 else None
    downs = [min(0.0, v) for v in vals]
    dvar = sum(d * d for d in downs) / (n - 1) if n > 1 else 0.0
    dsd = math.sqrt(dvar)
    sortino = (mean / dsd * math.sqrt(12)) if dsd > 1e-12 else None
    calmar = (cagr / maxdd) if (cagr is not None and maxdd > 1e-9) else None
    return {
        "label": label, "n_months": n,
        "total_pct": round(100.0 * total, 1),
        "cagr_pct": round(100.0 * cagr, 1) if cagr is not None else None,
        "sharpe": round(sharpe, 2) if sharpe is not None else None,
        "sortino": round(sortino, 2) if sortino is not None else None,
        "maxdd_pct": round(100.0 * maxdd, 1),
        "calmar": round(calmar, 2) if calmar is not None else None,
        "best_month_pct": round(100.0 * max(vals), 1),
        "worst_month_pct": round(100.0 * min(vals), 1),
        "pos_month_pct": round(100.0 * sum(1 for v in vals if v > 0) / n, 1),
    }


def main():
    t0 = time.time()
    print("=" * 104, flush=True)
    print("  STAGE N — vs BTC BUY&HOLD BENCHMARK (1R=1% equity, monthly chain)", flush=True)
    print("=" * 104, flush=True)

    sim = build_module()
    payload = {
        "instrument": "BTCUSDT_BYBIT",
        "stage": "buyhold_benchmark",
        "lens": "descriptive percent comparison; no gate",
        "assumptions": {
            "risk_pct_per_R": RISK_PCT,
            "strategy": "net_r per trade x 1% risk, grouped by exit month, monthly chain-compounded",
            "buyhold": "buy at first close of window, hold; month-end closes; no leverage/funding/costs",
        },
        "scopes": {},
    }

    for scope in ("is", "oos"):
        print(f"\n=== [{scope.upper()}] ===", flush=True)
        data = load_scope(scope)
        c15 = data["c15"]
        bh_rets, bh_first, bh_last = bh_months(c15)
        bh_m = metrics(bh_rets, "buy_hold")
        print(f"  BTC path: {bh_first:.0f} -> {bh_last:.0f} "
              f"({100.0 * (bh_last / bh_first - 1):+.1f}%)", flush=True)
        print(f"  {'subject':<14} {'months':>6} {'total%':>8} {'CAGR%':>7} "
              f"{'Sharpe':>7} {'Sortino':>7} {'maxDD%':>7} {'Calmar':>6} {'posM%':>6}",
              flush=True)
        sc = {"buy_hold": bh_m}
        lanes_tr = {}
        for name, key, flags in LANES:
            cfg = EXPERIMENTS[key]
            params = {**BP, **cfg["params"]}
            params.setdefault("exp_partial_r", 0.0)
            tr = run(sim, data, params, **flags)
            lanes_tr[name] = tr
            m = metrics(strategy_months(tr), name)
            sc[name] = m
            print(f"  {name:<14} {m['n_months']:>6} {m['total_pct']:>+8.1f} "
                  f"{(m['cagr_pct'] or 0):>+7.1f} {(m['sharpe'] or 0):>7.2f} "
                  f"{(m['sortino'] or 0):>7.2f} {m['maxdd_pct']:>7.1f} "
                  f"{(m['calmar'] or 0):>6.2f} {m['pos_month_pct']:>6.1f}", flush=True)
        trio = sorted((t for tr in lanes_tr.values() for t in tr),
                      key=lambda t: int(t["entry_ts"]))
        m = metrics(strategy_months(trio), "trio_book")
        sc["trio_book"] = m
        print(f"  {'trio_book':<14} {m['n_months']:>6} {m['total_pct']:>+8.1f} "
              f"{(m['cagr_pct'] or 0):>+7.1f} {(m['sharpe'] or 0):>7.2f} "
              f"{(m['sortino'] or 0):>7.2f} {m['maxdd_pct']:>7.1f} "
              f"{(m['calmar'] or 0):>6.2f} {m['pos_month_pct']:>6.1f}", flush=True)
        print(f"  {'buy_hold':<14} {bh_m['n_months']:>6} {bh_m['total_pct']:>+8.1f} "
              f"{(bh_m['cagr_pct'] or 0):>+7.1f} {(bh_m['sharpe'] or 0):>7.2f} "
              f"{(bh_m['sortino'] or 0):>7.2f} {bh_m['maxdd_pct']:>7.1f} "
              f"{(bh_m['calmar'] or 0):>6.2f} {bh_m['pos_month_pct']:>6.1f}", flush=True)
        payload["scopes"][scope] = sc

    payload["elapsed_sec"] = round(time.time() - t0, 2)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nwrote {OUT} ({payload['elapsed_sec']}s)", flush=True)


if __name__ == "__main__":
    main()
