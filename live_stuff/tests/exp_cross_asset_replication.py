"""Frozen cross-asset replication on Bybit linear-perpetual ETHUSDT/SOLUSDT.

This is replication, not optimization. It loads only isolated Bybit asset files,
applies existing v18 single/multi references without retuning, and reports the
same Bybit BTC execution-cost model for comparable net R.
"""
from __future__ import annotations

import json
import math
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

from experiment_registry import BP, EXPERIMENTS
from test_experiments_craze import build_module
from src.btc.btc_routes import _compute_swings, _trade_costs
from engine.v18_params import SWING, get_v18_params
from src.walker import FlowCandle

ASSET_DIR = ROOT / "data" / "bybit-assets"
OUT = ROOT / "live_stuff/tests/_thesis_cross_asset_replication_results.json"
ASSETS = ("ETHUSDT", "SOLUSDT")
CONFIGS = (
    "fullstack_wage10_cd0_single_sw10",
    "champion_multi_sw10",
    "utcsat_multi_sw10",
)
IST_OFFSET_SEC = 5 * 3600 + 30 * 60
STEP_SECONDS = {"15m": 900, "1h": 3600, "1m": 60}


def _read_csv(symbol: str, tf: str) -> pd.DataFrame:
    path = ASSET_DIR / f"{symbol}_{tf}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing isolated Bybit asset file: {path}")
    df = pd.read_csv(path)
    if "timestamp" not in df.columns:
        raise ValueError(f"Missing timestamp column: {path}")
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = (df.sort_values("timestamp")
            .drop_duplicates(subset="timestamp", keep="last")
            .reset_index(drop=True))
    expected = STEP_SECONDS[tf]
    epoch = (df["timestamp"].astype("int64") // 10**9) - IST_OFFSET_SEC
    diffs = epoch.diff().dropna()
    gaps = int((diffs != expected).sum())
    if gaps:
        raise ValueError(f"{path} has {gaps} timestamp gaps; max gap={diffs.max()}s")
    if df.empty:
        raise ValueError(f"Empty asset file: {path}")
    df["ts"] = epoch
    return df


def _candles(df: pd.DataFrame) -> tuple[list[dict], list[FlowCandle]]:
    candles = []
    flow = []
    for row in df.itertuples(index=False):
        date = row.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        o, h, lo, c = float(row.open), float(row.high), float(row.low), float(row.close)
        candles.append({"date": date, "ts": int(row.ts), "open": o,
                        "high": h, "low": lo, "close": c,
                        "volume": float(getattr(row, "volume", 0.0) or 0.0)})
        flow.append(FlowCandle(date=date, open=o, high=h, low=lo, close=c))
    return candles, flow




def _summary(values):
    xs = [float(x) for x in values if x is not None and math.isfinite(float(x))]
    if not xs:
        return {"n": 0}
    wins = [x for x in xs if x > 0]
    losses = [x for x in xs if x <= 0]
    peak = cum = dd = 0.0
    ls = ws = mls = mws = 0
    for value in xs:
        cum += value; peak = max(peak, cum); dd = max(dd, peak - cum)
        if value > 0: ws += 1; ls = 0
        else: ls += 1; ws = 0
        mls = max(mls, ls); mws = max(mws, ws)
    aw = sum(wins) / len(wins) if wins else 0.0
    al = sum(losses) / len(losses) if losses else 0.0
    return {
        "n": len(xs), "sum_r": round(sum(xs), 4), "avg_r": round(sum(xs) / len(xs), 6),
        "wins": len(wins), "losses": len(losses), "wr_pct": round(100.0 * len(wins) / len(xs), 3),
        "avg_win": round(aw, 4), "avg_loss": round(al, 4),
        "payoff": round(aw / abs(al), 4) if al else 0.0,
        "pf": round(sum(wins) / abs(sum(losses)), 4) if losses and sum(losses) else 0.0,
        "max_dd": round(dd, 4), "max_loss_streak": mls, "max_win_streak": mws,
        "median": round(statistics.median(xs), 6),
        "std": round(statistics.pstdev(xs), 6) if len(xs) > 1 else 0.0,
        "runners": {str(th): {"n": sum(x >= th for x in xs), "r": round(sum(x for x in xs if x >= th), 4)}
                    for th in (2.0, 3.0, 5.0, 10.0)},
    }


def _funding(trades):
    return sum((int(t.get("bars_held") or 0) * 0.25 / 8.0) * 0.0001 *
               (float(t["entry_price"]) / abs(float(t["entry_price"]) - float(t["sl"])))
               for t in trades if abs(float(t["entry_price"]) - float(t["sl"])) > 0)


def _metrics(trades):
    gross = [float(t.get("r_multiple") or 0.0) for t in trades]
    bybit = get_v18_params("BTCUSDT_BYBIT")
    fee_total, _ = _trade_costs(trades, bybit["fee_pct"], 0.0, bybit["entry_slip_pct"], bybit["exit_slip_pct"])
    funding = _funding(trades)
    net = []
    for g, t in zip(gross, trades):
        risk = abs(float(t["entry_price"]) - float(t["sl"]))
        fund_r = ((int(t.get("bars_held") or 0) * 0.25 / 8.0) * 0.0001 *
                  (float(t["entry_price"]) / risk) if risk > 0 else 0.0)
        net.append(g - float(t.get("cost_r", 0.0)) - fund_r)
    yg = defaultdict(float); yn = defaultdict(float)
    for t, g, n in zip(trades, gross, net):
        year = str(t.get("exit_date") or t.get("entry_date") or "")[:4]
        yg[year] += g; yn[year] += n
    return {"gross": _summary(gross), "net": _summary(net),
            "fee_slip_r": round(fee_total, 4), "funding_r": round(funding, 4),
            "yearly_gross": dict(sorted(yg.items())), "yearly_net": dict(sorted(yn.items()))}

def _load_asset(symbol: str) -> dict:

    started = time.time()
    c15, f15 = _candles(_read_csv(symbol, "15m"))
    c1h, f1h = _candles(_read_csv(symbol, "1h"))
    fine, _ = _candles(_read_csv(symbol, "1m"))
    lo = min(c15[0]["ts"], c1h[0]["ts"])
    hi = max(c15[-1]["ts"], c1h[-1]["ts"])
    fine = [c for c in fine if lo <= c["ts"] <= hi]
    if not fine or fine[0]["ts"] > lo + 3600 or fine[-1]["ts"] < hi - 3600:
        raise ValueError(f"{symbol} 1m does not cover simulation span")
    data = {
        "c15": c15, "f15": f15, "c1h": c1h, "f1h": f1h, "fine": fine,
        "sw15": _compute_swings(f15, "continuous", min_bars=SWING["min_bars_15m"]),
        "sw10": _compute_swings(f1h, "continuous", min_bars=10),
        "sw20": _compute_swings(f1h, "continuous", min_bars=SWING["min_bars_1h"]),
    }
    print(f"  {symbol}: 15m={len(c15)} 1h={len(c1h)} 1m={len(fine)} "
          f"sw15={len(data['sw15'])} sw10={len(data['sw10'])} ({time.time()-started:.1f}s)", flush=True)
    return data


def run():
    result = {"stage": "cross_asset_replication", "instrument_scope": "Bybit linear perpetual ETHUSDT/SOLUSDT",
              "period": "2023-01-01 through download endpoint", "frozen_no_retune": True,
              "cost_model": "BTCUSDT_BYBIT model applied to each asset", "assets": {}}
    sim = build_module()
    for symbol in ASSETS:
        data = _load_asset(symbol)
        asset_result = {"data": {"15m": len(data["c15"]), "1h": len(data["c1h"]), "1m": len(data["fine"])}, "configs": {}}
        for key in CONFIGS:
            cfg = EXPERIMENTS[key]
            params = {**BP, **cfg["params"]}
            params.setdefault("exp_partial_r", 0.0)
            started = time.time()
            out = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"], fine_ltf=data["fine"], **params)
            trades = out["ltf_trades"] if isinstance(out, dict) else out
            metrics = _metrics(trades)
            asset_result["configs"][key] = {"description": cfg.get("desc", ""), "metrics": metrics,
                                             "elapsed_sec": round(time.time() - started, 2)}
            g = metrics["gross"]; n = metrics["net"]
            print(f"    {symbol:7} {key:34} n={g['n']:4d} gross={g['sum_r']:+9.1f} net={n['sum_r']:+9.1f} "
                  f"avg={g['avg_r']:+.3f} WR={g['wr_pct']:5.1f}% PF={g['pf']:4.2f} DD={g['max_dd']:6.1f}", flush=True)
        result["assets"][symbol] = asset_result
    OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"  wrote {OUT}", flush=True)


if __name__ == "__main__":
    run()
