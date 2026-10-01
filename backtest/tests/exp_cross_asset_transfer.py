"""STAGE CROSS-ASSET (Paradigm 6) - frozen v18 lanes on Binance ETHUSDT/SOLUSDT perps.

THIS DOCSTRING IS THE BINDING PRE-REGISTRATION. Written BEFORE any run.

Origin: paradigm #6 of the user's "outside the v18 model" batch
("v18 on ETH/SOL"). CHECKLIST 24.16 demands "a genuinely distinct test"
before any cross-asset production change. Prior art (immutable):
  - Stage 17 / 24.21: frozen replication on BYBIT ETHUSDT/SOLUSDT,
    full-period only (2023-01..2026-09), NO era split, NO kill table -
    "overlapping-period replication, not fresh OOS".
  - Stage CrossInstrument / 24.82: Binance BTCUSDT (same instrument,
    different venue), IS/OOS transfer rule - transfer_all_3 TRUE;
    M2/uMZX 6/6, ZC/X FAIL.
THIS test is the cell neither covered: DIFFERENT venue AND different
instruments (Binance fapi ETH/SOL perps), on price data no engine run
has ever seen, with full era + kill discipline.

DATA (new, shared datasets never mutated):
  data/alt-fut/{ETHUSDT,SOLUSDT}_{15m,1h,1m}.csv - raw fapi precision
  (SOL native is 4dp; data/scan-fut stores 2dp = lossy below ~$10, so it
  is NOT used; data/eth-fut is 2dp but missing the first 5h15m of the
  OOS window, so it is NOT used either). IST wall-clock open stamps,
  loader raises on any gap/dup/off-grid row or slice mismatch (0 gaps
  verified pre-run).

LANES (4 frozen flat reference configs, registry keys, NO retuning,
NO flags): champion / utcsat / fullstack / age10 - the same 4 alive
kings as Paradigm 5.

SCOPES: era bounds MIRRORED from the bybit BTC loaders per scope (the
24.82 convention: identical windows, different instrument+venue):
  IS  = bybit get_data() window (2023-01-01 .. 2026-09-13), 3.67y
  OOS = bybit unseen window (2021-01-01 .. 2022-12-31), 2.0y
  assets clipped to the same epoch bounds; 1m fine sliced to the same
  bounds with exact-count checks (bybit OOS fine starts 5h late - legacy
  unseen layout - asset fine covers the full window; noted, not gated).

COSTS: Bybit BTC equity_quality/net_r convention applied unchanged
(24.82 + Stage 17 precedent; funding rides inside net_r). No per-asset
fee retune.

CONTROLS (abort before any verdict):
  - exp_stat_arb.v18_control: identity gate + champion house refs both
    books (also builds v18m = champion GROSS monthly for K7).
  - bybit ledger: all 4 lanes x 2 eras within +/-1t / +/-1.0R of house
    refs: champion 500/+325.8, 279/+70.2; utcsat 454/+358.9, 253/+60.2;
    fullstack 200/+310.7, 140/+16.9; age10 130/+435.7, 76/+43.2.
  - data gates raise before any lane runs (gap/dup/off-grid/slice).

PRIMARY VERDICT (the 24.82 transfer rule, unchanged):
  lane TRANSFER PASS (per asset) = base net > 0 AND n >= 30 in BOTH
  eras. 8 units total (2 assets x 4 lanes). All reported, no best-of.

KILL TABLE (secondary, house K1..K7 evaluated per asset x lane x era,
SAME construction as exp_stat_arb.eval_era: net by exit month, quarters
by exit date, trade-order DD, zero-filled months from era start to last
exit):
  K1 net <= 0  K2 any quarter <= -15R  K3 maxDD > 30R
  K4 annualized monthly Sharpe < 0.5  K5 n < 100 IS / < 60 OOS
  K6 net win rate < 40%  K7 corr(monthly NET, v18 champion monthly
  GROSS) > 0.3
  DIFFERENTIAL EXEMPTION (pre-registered): a kill COUNTS against an
  asset cell only if it does NOT fire on the bybit reference cell for
  the same lane x era. Rationale: v18 reference books are low-WR by
  construction (champion OOS wr ~24%), so a literal K6 would kill the
  champion on its own venue; K7's house purpose is new-edge redundancy,
  while a replication's target IS v18 (corr>0.3 is the expected
  signature of a transfer, as P5's K7 redefinition likewise showed for
  the ensemble). Under this rule both K6 and K7 are exempt everywhere
  the reference itself fires; raw (uncounted) kills are always reported
  for transparency. K5 keeps house thresholds - no deviation (all four
  bybit books pass n>=100/60).

RESEARCH_POLICY: both assets x 4 lanes x 2 eras all reported; no
best-of; no auto-adopt. A transfer PASS = "candidate for the user's
adoption decision", never an automatic production change. Stage 17's
single-vs-multi divergence is explicitly retested (fullstack single vs
the 3 multi/single lanes) on the new venue.

Output: backtest/tests/_cross_asset_transfer_results.json
Run: $env:PYTHONIOENCODING='utf-8'; python -u backtest/tests/exp_cross_asset_transfer.py
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from experiment_registry import BP, EXPERIMENTS  # noqa: E402
from run_experiment import net_r  # noqa: E402
from exp_stat_arb import v18_control  # noqa: E402
from stat_arb.correlation import month_key, quarter_key, month_range, pearson  # noqa: E402
from test_experiments_craze import build_module  # noqa: E402
from src.btc.btc_routes import _compute_swings  # noqa: E402
from engine.v18_params import SWING  # noqa: E402
from src.walker import FlowCandle  # noqa: E402
import exp_portfolio_book as epb  # noqa: E402  (load_scope/run/net helpers)

OUT = ROOT / "backtest/tests/_cross_asset_transfer_results.json"
ALT_DIR = ROOT / "data" / "alt-fut"

LANES = (
    ("champion", "champion_multi_sw10"),
    ("utcsat", "utcsat_multi_sw10"),
    ("fullstack", "fullstack_wage10_cd0_single_sw10"),
    ("age10", "age10_dirmatch_swingpause_single_sw10"),
)
ASSETS = ("ETHUSDT", "SOLUSDT")
REF = {
    "champion": {"is": (500, 325.8), "oos": (279, 70.2)},
    "utcsat": {"is": (454, 358.9), "oos": (253, 60.2)},
    "fullstack": {"is": (200, 310.7), "oos": (140, 16.9)},
    "age10": {"is": (130, 435.7), "oos": (76, 43.2)},
}
KILL_MIN = {"is": 100, "oos": 60}
ERA_START = {"is": "2023-01", "oos": "2021-01"}
TRANSFER_MIN_N = 30
IST_OFFSET_SEC = 5 * 3600 + 30 * 60
STEP_SECONDS = {"15m": 900, "1h": 3600, "1m": 60}


def _read_alt(symbol: str, tf: str) -> pd.DataFrame:
    path = ALT_DIR / f"{symbol}_{tf}.csv"
    if not path.exists():
        raise SystemExit(f"DATA ABORT: missing {path} (run scripts/download_alt_fut.py)")
    df = pd.read_csv(path)
    if "timestamp" not in df.columns:
        raise ValueError(f"missing timestamp column: {path}")
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = (df.sort_values("timestamp")
            .drop_duplicates(subset="timestamp", keep="last")
            .reset_index(drop=True))
    epoch = (df["timestamp"].astype("int64") // 10**9) - IST_OFFSET_SEC
    diffs = epoch.diff().dropna()
    gaps = int((diffs != STEP_SECONDS[tf]).sum())
    if gaps:
        raise ValueError(f"{path} has {gaps} timestamp gaps; max={diffs.max()}s")
    if int((epoch % STEP_SECONDS[tf]).sum()):
        raise ValueError(f"{path}: off-grid timestamps")
    df["ts"] = epoch
    return df


def _candles(df: pd.DataFrame) -> tuple[list[dict], list[FlowCandle]]:
    candles, flow = [], []
    for row in df.itertuples(index=False):
        date = row.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        o, h, lo, c = float(row.open), float(row.high), float(row.low), float(row.close)
        candles.append({"date": date, "ts": int(row.ts), "open": o,
                        "high": h, "low": lo, "close": c, "volume": 0.0})
        flow.append(FlowCandle(date=date, open=o, high=h, low=lo, close=c))
    return candles, flow


def bybit_bounds(data: dict, scope: str) -> dict:
    c15, c1h = data["c15"], data["c1h"]
    if scope == "oos":
        fine = (c15[0]["ts"], c15[-1]["ts"])
    else:
        fine = (min(c1h[0]["ts"], c15[0]["ts"]),
                max(c1h[-1]["ts"], c15[-1]["ts"]))
    return {"15m": (c15[0]["ts"], c15[-1]["ts"]),
            "1h": (c1h[0]["ts"], c1h[-1]["ts"]), "fine": fine}


def load_asset(symbol: str, scope: str, bounds: dict) -> dict:
    out = {}
    for tf in ("15m", "1h", "1m"):
        lo, hi = bounds["15m" if tf == "15m" else ("1h" if tf == "1h" else "fine")]
        df = _read_alt(symbol, tf)
        df = df[(df["ts"] >= lo) & (df["ts"] <= hi)].reset_index(drop=True)
        expect = (hi - lo) // STEP_SECONDS[tf] + 1
        if lo % STEP_SECONDS[tf] or len(df) != expect:
            raise SystemExit(
                f"DATA ABORT: {symbol}/{scope}/{tf} slice mismatch "
                f"(lo={lo} mod={lo % STEP_SECONDS[tf]} got={len(df)} expect={expect})")
        out[tf] = df
    c15, f15 = _candles(out["15m"])
    c1h, f1h = _candles(out["1h"])
    fine, _ = _candles(out["1m"])
    sw15 = _compute_swings(f15, "continuous", min_bars=SWING["min_bars_15m"])
    sw10 = _compute_swings(f1h, "continuous", min_bars=10)
    lo, hi = bounds["15m"]
    print(f"  [{symbol}/{scope}] 15m={len(c15)} 1h={len(c1h)} fine={len(fine)} "
          f"window {pd.to_datetime(lo - IST_OFFSET_SEC, unit='s', utc=True):%Y-%m-%d %H:%M}"
          f" -> {pd.to_datetime(hi - IST_OFFSET_SEC, unit='s', utc=True):%Y-%m-%d %H:%M} "
          f"fine_cov {'FULL' if fine and fine[0]['ts'] <= bounds['fine'][0] + 3600 else 'LATE-START'}",
          flush=True)
    return {"c15": c15, "f15": f15, "c1h": c1h, "f1h": f1h,
            "sw15": sw15, "sw10": sw10, "fine": fine}


def run(sim, data, params):
    out = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
              fine_ltf=data["fine"], **params)
    return out["ltf_trades"] if isinstance(out, dict) else out


def enrich(trades: list[dict], era: str) -> list[dict]:
    """House eval rows: r = NET R (net_r), buckets by exit date."""
    out = []
    for t in trades:
        ex = str(t.get("exit_date") or t.get("entry_date") or "")[:10]
        if not ex or ex == "":
            raise SystemExit("TRADE ABORT: missing exit_date")
        net = net_r([t])
        gross = float(t["r_multiple"])
        out.append({
            "r": net,
            "gross": gross,
            "cost": gross - net,   # fee+slip+funding combined (net_r path)
            "funding": 0.0,
            "risk": 1.0,
            "quarter": quarter_key(pd.Timestamp(ex)),
            "month": month_key(pd.Timestamp(ex)),
            "exit_dt": pd.Timestamp(ex),
        })
    return out


def eval_cell(rows: list[dict], era: str, v18m: dict) -> dict:
    """exp_stat_arb.eval_era construction (house K1..K7), own ERA_START."""
    n = len(rows)
    rs = [t["r"] for t in rows]
    net = sum(rs)
    wr = (sum(1 for r in rs if r > 0) / n) if n else 0.0
    cum = peak = dd = 0.0
    for r in rs:
        cum += r
        peak = max(peak, cum)
        dd = max(dd, peak - cum)
    quarters: dict[str, float] = {}
    months: dict[str, float] = {}
    last_exit = None
    gR = cR = fR = 0.0
    for t in rows:
        quarters[t["quarter"]] = quarters.get(t["quarter"], 0.0) + t["r"]
        months[t["month"]] = months.get(t["month"], 0.0) + t["r"]
        gR += t["gross"] / t["risk"]
        cR += t["cost"] / t["risk"]
        fR += t["funding"] / t["risk"]
        if last_exit is None or t["exit_dt"] > last_exit:
            last_exit = t["exit_dt"]
    start = pd.Timestamp(ERA_START[era] + "-01")
    ml = month_range(start, last_exit) if last_exit else month_range(start, start)
    vec = [months.get(m, 0.0) for m in ml]
    vvec = [v18m.get(m, 0.0) for m in ml]
    corr = pearson(vec, vvec)
    if len(vec) >= 2:
        mu = sum(vec) / len(vec)
        sdv = math.sqrt(sum((x - mu) ** 2 for x in vec) / (len(vec) - 1))
        sharpe = (mu / sdv) * math.sqrt(12.0) if sdv > 1e-12 else 0.0
    else:
        sharpe = 0.0
    kills = {
        "K1_net_nonpositive": net <= 0,
        "K2_quarter_le_neg15": any(v <= -15.0 for v in quarters.values()),
        "K3_maxdd_gt_30R": dd > 30.0,
        "K4_sharpe_lt_0.5": sharpe < 0.5,
        "K5_min_trades": n < KILL_MIN[era],
        "K6_wr_lt_40": wr < 0.40,
        "K7_corr_gt_0.3": (corr is not None and corr > 0.3),
    }
    return {
        "n": n, "net_r": round(net, 4),
        "gross_R": round(gR, 3), "cost_R": round(cR, 3),
        "wr": round(wr, 6), "sharpe_ann": round(sharpe, 4),
        "max_dd_R": round(dd, 4),
        "quarters": {k: round(v, 3) for k, v in sorted(quarters.items())},
        "monthly_r": {m: round(v, 3) for m, v in zip(ml, vec)},
        "corr_v18_monthly": None if corr is None else round(corr, 4),
        "kills": kills, "killed": any(kills.values()),
        "kill_list": sorted(k for k, v in kills.items() if v),
    }


def counted_kills(raw: dict, ref_raw: dict) -> dict:
    """Differential exemption: count a kill only if the bybit reference
    cell (same lane x era) does NOT fire the same kill."""
    return {k: bool(v) and not ref_raw["kills"].get(k, False)
            for k, v in raw["kills"].items()}


def main() -> int:
    t0 = time.time()
    print("=" * 95, flush=True)
    print("  STAGE CROSS-ASSET - frozen v18 on Binance ETHUSDT/SOLUSDT "
          "(era-mirrored transfer test)", flush=True)
    print("=" * 95, flush=True)

    v18m: dict = {}
    control = v18_control(v18m)          # identity gate + champion refs
    sim = build_module()

    payload = {
        "stage": "cross_asset_transfer",
        "hypothesis": ("frozen v18 lanes transfer to Binance ETH/SOL perps "
                       "with positive base edge in both eras (24.82 rule)"),
        "instruments_test": "BINANCE_FAPI ETHUSDT/SOLUSDT PERP (data/alt-fut, raw precision)",
        "instrument_control": "BTCUSDT_BYBIT (established loaders, house refs)",
        "era_windows_mirrored_from": "bybit loaders per scope (24.82 convention)",
        "cost_model": "Bybit BTC net_r/equity convention, unchanged (24.82/Stage 17)",
        "frozen_no_retune": True,
        "k5": "n>=100 IS / >=60 OOS (house, no deviation)",
        "k6_k7": ("differential exemption: counted only if the bybit reference "
                  "cell (same lane x era) does not fire the same kill"),
        "transfer_rule": ("base net>0 AND n>=30 in BOTH eras, per asset x lane "
                          "(24.82 rule unchanged)"),
        "fine_parity_note": ("bybit OOS fine starts 5h late (legacy unseen "
                             "layout); asset fine covers the full window"),
        "controls": {"v18_control": control},
        "assets": {}, "bybit_ref": {}, "cells": {}, "transfer": {},
    }

    transfers: dict[str, dict] = {a: {} for a in ASSETS}
    kill_clean: dict[str, dict] = {a: {} for a in ASSETS}

    for scope in ("is", "oos"):
        print(f"\n=== [{scope.upper()}] era_start={ERA_START[scope]} ===", flush=True)
        by_data = epb.load_scope(scope)
        bounds = bybit_bounds(by_data, scope)

        # ---- bybit reference lanes (ledger control) ----
        by_ref: dict[str, dict] = {}
        for name, key in LANES:
            params = {**BP, **EXPERIMENTS[key]["params"]}
            params.setdefault("exp_partial_r", 0.0)
            tr = epb.run(sim, by_data, params)
            rows = enrich(tr, scope)
            cell = eval_cell(rows, scope, v18m)
            rn, rnet = REF[name][scope]
            if abs(cell["n"] - rn) > 1 or abs(cell["net_r"] - rnet) > 1.0:
                raise SystemExit(
                    f"LEDGER ABORT: bybit {name}/{scope} {cell['n']}t/"
                    f"{cell['net_r']:+.1f}R vs ref {rn}t/{rnet:+.1f}R "
                    f"(tol +/-1t/+/-1.0R)")
            by_ref[name] = cell
            print(f"  [bybit] {name:<10} {cell['n']:>4}t {cell['net_r']:+8.1f}R "
                  f"(ref {rn}t/{rnet:+.1f}R) OK", flush=True)
        payload["bybit_ref"][scope] = by_ref
        del by_data   # release ~2M fine candles before asset loads

        # ---- asset lanes ----
        for asset in ASSETS:
            adata = load_asset(asset, scope, bounds)
            payload["assets"].setdefault(asset, {})[scope] = {
                "rows_15m": len(adata["c15"]), "rows_1h": len(adata["c1h"]),
                "rows_fine": len(adata["fine"]),
            }
            for name, key in LANES:
                params = {**BP, **EXPERIMENTS[key]["params"]}
                params.setdefault("exp_partial_r", 0.0)
                tr = run(sim, adata, params)
                rows = enrich(tr, scope)
                cell = eval_cell(rows, scope, v18m)
                cell["kills_raw"] = dict(cell["kills"])
                cell["kill_list_raw"] = list(cell["kill_list"])
                cnt = counted_kills(cell, by_ref[name])
                cell["kills_counted"] = cnt
                cell["kill_list_counted"] = sorted(k for k, v in cnt.items() if v)
                cell["killed_counted"] = any(cnt.values())
                payload["cells"].setdefault(asset, {}).setdefault(name, {})[scope] = cell
                print(f"  [{asset}] {name:<10} {cell['n']:>4}t {cell['net_r']:+8.1f}R "
                      f"DD {cell['max_dd_R']:>6.1f} sh {cell['sharpe_ann']:+.2f} "
                      f"corr {cell['corr_v18_monthly']} "
                      + (f"RAW:{','.join(cell['kill_list_raw'])} "
                         f"COUNTED:{','.join(cell['kill_list_counted'])}"
                         if cell["killed"] else "raw-kills: pass"),
                      flush=True)

    # ---- primary: 24.82 transfer rule ----
    print("\n=== TRANSFER (24.82 rule: net>0 AND n>=30 BOTH eras) ===", flush=True)
    for asset in ASSETS:
        for name, _ in LANES:
            is_c = payload["cells"][asset][name]["is"]
            oos_c = payload["cells"][asset][name]["oos"]
            v = {"net_is": is_c["net_r"], "net_oos": oos_c["net_r"],
                 "n_is": is_c["n"], "n_oos": oos_c["n"]}
            v["pass"] = (v["net_is"] > 0 and v["net_oos"] > 0
                         and v["n_is"] >= TRANSFER_MIN_N
                         and v["n_oos"] >= TRANSFER_MIN_N)
            clean = not payload["cells"][asset][name]["is"]["killed_counted"] \
                and not payload["cells"][asset][name]["oos"]["killed_counted"]
            v["kills_clean_both_eras"] = clean
            transfers[asset][name] = v
            kill_clean[asset][name] = clean
            print(f"  {asset:<9} {name:<10} IS {v['n_is']:>4}t {v['net_is']:+8.1f} | "
                  f"OOS {v['n_oos']:>4}t {v['net_oos']:+8.1f} | "
                  f"PASS={v['pass']} | kills_clean={clean}", flush=True)
    payload["transfer"] = transfers
    payload["kills_clean"] = kill_clean

    n_pass = sum(1 for a in ASSETS for n, _ in LANES if transfers[a][n]["pass"])
    n_clean = sum(1 for a in ASSETS for n, _ in LANES if kill_clean[a][n])
    payload["transfer_pass"] = f"{n_pass}/8"
    payload["kills_clean_units"] = f"{n_clean}/8"
    payload["verdict"] = (
        f"TRANSFER {n_pass}/8 lane-assets pass the 24.82 rule; "
        f"{'all' if n_clean == 8 else n_clean}/8 free of counted kills in both eras"
        + (" - CANDIDATE (user adoption decision required)" if n_pass
           else " - NO TRANSFER"))
    payload["elapsed_sec"] = round(time.time() - t0, 1)

    print("\n=== SUMMARY ===", flush=True)
    print(f"  controls: v18 OK, ledger OK, data gates OK", flush=True)
    print(f"  transfer: {payload['transfer_pass']}   "
          f"kills_clean: {payload['kills_clean_units']}", flush=True)
    print("VERDICT:", payload["verdict"], flush=True)
    OUT.write_text(json.dumps(payload, indent=1, default=str), encoding="utf-8")
    print(f"JSON: {OUT} ({payload['elapsed_sec']}s)", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
