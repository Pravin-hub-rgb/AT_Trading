"""Stage ETH-LEDNESS - the only cross-asset axis that can reach a 6/6 gate.

WHY THIS STAGE EXISTS
---------------------
The whole sizing queue just closed twice on the same gate. ZCX (24.86) is
profitable on both venues but fails `curve_better`; the size-cap sweep (24.87)
showed that failure is structural, not a matter of picking a better multiplier.

So the next lever has to be a genuinely different INPUT, not a different size.
Everything tried so far (M2, ZC, X) is derived from BTC's own swing, volume or
window geometry. ETH is a second asset entirely.

DATA AVAILABILITY (checked on disk, not assumed)
-----------------------------------------------
  funding / open-interest / liquidations / CVD : ABSENT. Every CSV header is
      timestamp,open,high,low,close (+ dead x,y). This axis does not exist here.
  data/scan-fut 15 alts                        : 2023-01-01 -> 2026-09-10.
      Covers the IS era but NOT the OOS era, so it can never satisfy a 6/6 gate
      (3 lanes x 2 eras). Structurally excluded, not merely weak.
  data/eth-fut                                 : 2021-01-01 -> 2026-09-23, 50200
      1h rows. Covers BOTH eras. This is the only cross-asset on disk that can.

PRE-REGISTERED BEFORE THE RUN (2026-09-27)
------------------------------------------
  Method: SIZING ONLY, post-process. Under AGENT_COORDINATION.md "Sizing
    exemption" this is a real measurement - no engine rerun. Explicitly NOT a
    removal/filter: the Stage-B retraction showed a post-process ledger skip is
    only an UPPER BOUND there (cascade 3-5x the direct effect), so filtering is
    out of scope for this stage by rule, not by preference.
  Feature: ETH-vs-BTC return divergence on 1h.
      eth_ret = ETH close[t]/close[t-L] - 1 over the same lookback
      btc_ret = BTC close[t]/close[t-L] - 1
      div     = eth_ret - btc_ret
  CAUSALITY: an ETH bar at ts closes at ts+3600, so a bar may only be used when
    ts + 3600 <= entry_ts. The harness uses ts <= entry_ts - 3600, i.e. it
    requires the bar to have FULLY CLOSED before the entry, not merely started.
    Same strictness as the repo's `exit_ts <= candidate entry_ts` rule.
  Arms (4, no percentile search - the threshold is a hard zero):
      E_lead_L : x1.5 when div > 0   (ETH outperforming)
      E_lag_L  : x1.5 when div < 0   (ETH underperforming)
      L in (24, 168) hours = 1d and 1w
  Gate: ARM PASS = dNet > 0 AND curve_better in ALL 6 cells (3 lanes x 2 eras)
      on Bybit. Binance is a transfer check, not the primary gate.
  Control: bybit base ledgers must reproduce the 24.85 references, or abort.
  Nothing is retuned after the run.

  PREDICTION RECORDED BEFORE RUNNING - carried over from what 24.87 taught.
  24.87 measured that an arm's curve deltas are LINEAR in (cap - 1) and that
  ZCX's d_max_dd was NEGATIVE, i.e. the flagged cohort sat ON the base book's
  deepest drawdown. That is a property of WHERE the flag lives, not of its
  size. So the question this stage must answer is not "does x1.5 on ETH-ledness
  profit" but "does the ETH-ledness flag overlap the base drawdown". The
  `drawdown_diagnostic` block measures that directly - the fraction of flagged
  trades sitting inside the base max-DD window, and the base's own R inside it.
  If flagged trades are concentrated in the drawdown, d_max_dd goes negative
  by construction and this stage fails for the same structural reason as ZCX.
  Recording it here means the run either surprises us or confirms the mechanism,
  and either way we learn which.

Run: $env:PYTHONIOENCODING='utf-8'; python -u exp_eth_ledness.py
"""
from __future__ import annotations

import bisect
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

OUT = ROOT / "backtest/tests/_eth_ledness.json"
ETH_DIR = ROOT / "data" / "eth-fut"
IST_OFFSET_SEC = 19800          # 5:30, same wall clock as every other CSV
STEP_SECONDS = {"1h": 3600}
SIZE = 1.5
LOOKBACKS = (24, 168)           # 1 day, 1 week - pre-registered, not swept
CLOSE_GUARD = STEP_SECONDS["1h"]  # bar must be fully closed before the entry

BYBIT_BASE = {
    "champion": {"is": (500, 325.8), "oos": (279, 70.2)},
    "utcsat": {"is": (454, 358.9), "oos": (253, 60.2)},
    "age10": {"is": (130, 435.7), "oos": (76, 43.2)},
}

LANES = (
    ("champion", "champion_multi_sw10"),
    ("utcsat", "utcsat_multi_sw10"),
    ("age10", "age10_dirmatch_swingpause_single_sw10"),
)
ARMS = (("E_lead", 24, "lead"), ("E_lag", 24, "lag"),
        ("E_lead_w", 168, "lead"), ("E_lag_w", 168, "lag"))


def load_eth_1h():
    """ETH 1h as (sorted_ts_list, close_list), gap-checked like _read_binance."""
    import pandas as pd
    path = ETH_DIR / "ETHUSDT_1h.csv"
    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = (df.sort_values("timestamp")
            .drop_duplicates(subset="timestamp", keep="last")
            .reset_index(drop=True))
    epoch = (df["timestamp"].astype("int64") // 10 ** 9) - IST_OFFSET_SEC
    diffs = epoch.diff().dropna()
    gaps = int((diffs != STEP_SECONDS["1h"]).sum())
    if gaps:
        raise ValueError(f"{path} has {gaps} gaps; max={diffs.max()}s")
    return list(map(int, epoch)), [float(c) for c in df["close"]]


def btc_closes(data):
    """BTC 1h closes as (sorted_ts_list, close_list) for the era bundle."""
    ts = [int(c["ts"]) for c in data["c1h"]]
    cl = [float(c["close"]) for c in data["c1h"]]
    order = sorted(range(len(ts)), key=lambda i: ts[i])
    return [ts[i] for i in order], [cl[i] for i in order]


def divergence(ets, ecl, bts, bcl, entry_ts, L):
    """ETH-minus-BTC return over L hours, using only fully-closed bars."""
    cut = int(entry_ts) - CLOSE_GUARD
    ei = bisect.bisect_right(ets, cut) - 1
    bi = bisect.bisect_right(bts, cut) - 1
    if ei - L < 0 or bi - L < 0:
        return None
    return ((ecl[ei] / ecl[ei - L] - 1.0) - (bcl[bi] / bcl[bi - L] - 1.0))


def flag_keys(trades, ets, ecl, bts, bcl, L, direction):
    """Trade keys where the causal ETH-minus-BTC divergence is on-side."""
    keys = set()
    for t in trades:
        d = divergence(ets, ecl, bts, bcl, int(t["entry_ts"]), L)
        if d is None:
            continue
        if (direction == "lead" and d > 0) or (direction == "lag" and d < 0):
            keys.add((int(t["entry_ts"]), int(t["exit_ts"])))
    return keys


def apply_size(trades, keys, mult=None):
    """Sizing post-process. Identity + sign asserts (sizing exemption cnd 1)."""
    out = []
    mult = SIZE if mult is None else mult
    for t in trades:
        t2 = dict(t)
        if (int(t["entry_ts"]), int(t["exit_ts"])) in keys:
            t2["r_multiple"] = round(float(t["r_multiple"]) * mult, 6)
        out.append(t2)
    assert [(t["entry_ts"], t["exit_ts"]) for t in out] == \
           [(t["entry_ts"], t["exit_ts"]) for t in trades], "key sequence changed"
    assert [float(t["r_multiple"]) > 0 for t in out] == \
           [float(t["r_multiple"]) > 0 for t in trades], "loss sign changed"
    return out


def drawdown_window(trades):
    """Peak-to-trough index span of the base equity curve (chronological)."""
    eq, peak, peak_i, dd, lo_i, hi_i = 0.0, 0.0, 0, 0.0, 0, 0
    best = (0.0, 0, 0)
    for i, t in enumerate(trades):
        eq += float(t["r_multiple"])
        if eq > peak:
            peak, peak_i = eq, i
        d = peak - eq
        if d > best[0]:
            best = (d, peak_i, i)
    _d, hi_i, lo_i = best
    return hi_i, lo_i, round(best[0], 4)


def drawdown_diagnostic(trades, keys, divs):
    """Does the flagged cohort sit ON the base max-DD window? (24.87's lesson)

    ZCX's d_max_dd was negative because its flags were concentrated in the
    deepest drawdown. This quantifies the same thing for any arm: if the
    flagged share of the drawdown window greatly exceeds the flagged share of
    the book, the arm deepens the drawdown by construction and no multiplier
    can fix it.
    """
    a, b, dd = drawdown_window(trades)
    lo_ts, hi_ts = int(trades[a]["entry_ts"]), int(trades[b]["exit_ts"])
    in_dd = [t for t in trades if lo_ts <= int(t["exit_ts"]) <= hi_ts]
    n_flag = sum(1 for t in trades
                 if (int(t["entry_ts"]), int(t["exit_ts"])) in keys)
    n_flag_dd = sum(1 for t in in_dd
                    if (int(t["entry_ts"]), int(t["exit_ts"])) in keys)
    frac_all = n_flag / len(trades) if trades else 0.0
    frac_dd = n_flag_dd / len(in_dd) if in_dd else 0.0
    d_flag = [float(t["r_multiple"]) for t in trades
              if (int(t["entry_ts"]), int(t["exit_ts"])) in keys]
    r_dd = sum(float(t["r_multiple"]) for t in in_dd)
    r_dd_flag = sum(float(t["r_multiple"]) for t in in_dd
                    if (int(t["entry_ts"]), int(t["exit_ts"])) in keys)
    return {
        "dd_R": dd, "dd_n": len(in_dd), "n_flagged": n_flag,
        "frac_flagged_book": round(frac_all, 4),
        "frac_flagged_in_dd": round(frac_dd, 4),
        "concentration": round(frac_dd / frac_all, 3) if frac_all else None,
        "mean_r_flagged": round(sum(d_flag) / len(d_flag), 4) if d_flag else None,
        "sum_r_in_dd": round(r_dd, 3),
        "sum_r_in_dd_flagged": round(r_dd_flag, 3),
        "sits_on_drawdown": (frac_dd > frac_all * 1.5) if frac_all else None,
    }


def run_venue(venue, data, sim, sim_fn, years, ets, ecl):
    """All 4 ETH-ledness arms on every lane for one venue bundle."""
    from experiment_registry import BP, EXPERIMENTS
    from exp_equity_quality import equity_quality, arm_scores, curve_better

    bts, bcl = btc_closes(data)
    res = {}
    for name, key in LANES:
        params = {**BP, **EXPERIMENTS[key]["params"]}
        trades = sim_fn(sim, data, params)
        m_base = equity_quality(trades, years)
        best_i = max(range(len(trades)), key=lambda i: float(trades[i]["r_multiple"]))
        m_base_nb = equity_quality([t for i, t in enumerate(trades) if i != best_i], years)

        arms_out = {}
        for arm, L, direction in ARMS:
            keys = flag_keys(trades, ets, ecl, bts, bcl, L, direction)
            book = apply_size(trades, keys)
            m = equity_quality(book, years)
            d = arm_scores(m, m_base)
            best_j = max(range(len(book)), key=lambda i: float(book[i]["r_multiple"]))
            m_nb = equity_quality([t for i, t in enumerate(book) if i != best_j], years)
            d_nb = arm_scores(m_nb, m_base_nb)
            arms_out[arm] = {
                "lookback_h": L, "direction": direction,
                "n_flagged": len(keys),
                "d_net": d.get("d_net"),
                "d_max_dd": d.get("d_max_dd"),
                "d_ulcer": d.get("d_ulcer"),
                "d_calmar": d.get("d_calmar"),
                "d_pf": d.get("d_pf"),
                "curve_better": curve_better(d),
                "d_net_no_best": d_nb.get("d_net"),
                "robust": (d_nb.get("d_net") or 0) > 0,
                "diagnostic": drawdown_diagnostic(trades, keys, None),
            }
        res[name] = {"n": m_base["n"], "net": m_base["net"], "arms": arms_out}
    return res


def main():
    t0 = time.time()
    print("=" * 100, flush=True)
    print("  ETH-LEDNESS - does a second asset give a 6/6 sizing lever?", flush=True)
    print("=" * 100, flush=True)

    from test_experiments_craze import build_module
    from exp_sizing_combo import run as sim_fn
    from exp_cross_instrument_transfer import (
        load_bybit, bybit_bounds, load_binance)

    sim = build_module()
    ets, ecl = load_eth_1h()
    print(f"  ETH 1h loaded: {len(ets)} rows", flush=True)

    years = {"is": 3.67, "oos": 2.0}
    payload = {
        "stage": "eth_ledness",
        "lens": ("SIZING-ONLY post-process on flat books; trade keys identical; "
                 "no removal/filter (forbidden by the Stage-B upper-bound rule)"),
        "feature": "ETH-minus-BTC return divergence on 1h, fully-closed bars only",
        "arms": {a: f"x{SIZE} when ETH-BTC divergence {dr}>0 over {L}h"
                 for a, L, dr in ARMS},
        "size": SIZE, "lookbacks": list(LOOKBACKS), "eth_rows": len(ets),
        "years": years, "scopes": {"bybit": {}, "binance": {}},
        "pre_registered": {
            "arm_pass": "dNet>0 AND curve_better in ALL 6 cells (3 lanes x 2 eras) on Bybit",
            "threshold": "hard zero, no percentile search, L in (24,168) only",
            "causality": "ETH bar must be fully closed: ts <= entry_ts - 3600",
            "control": "bybit base ledgers reproduce the 24.85 references",
            "no_retune": "nothing is retuned after the run",
        },
    }

    for scope in ("is", "oos"):
        print(f"\n=== [{scope.upper()}] ===", flush=True)
        byb = load_bybit(scope, sim)
        r_byb = run_venue("bybit", byb, sim, sim_fn, years[scope], ets, ecl)
        for name, _ in LANES:
            exp_n, exp_net = BYBIT_BASE[name][scope]
            got = r_byb[name]
            assert got["n"] == exp_n, (
                f"CONTROL FAIL bybit/{scope}/{name} n: {got['n']} != {exp_n}")
            assert abs(got["net"] - exp_net) < 0.5, (
                f"CONTROL FAIL bybit/{scope}/{name} net: {got['net']} != {exp_net}")
        print(f"  [control-ok] bybit/{scope}: base ledgers reproduce 24.85", flush=True)
        payload["scopes"]["bybit"][scope] = r_byb

        bounds = bybit_bounds(byb, scope)
        bin_ = load_binance(scope, bounds)
        payload["scopes"]["binance"][scope] = run_venue(
            "binance", bin_, sim, sim_fn, years[scope], ets, ecl)

    # per-arm report, after BOTH eras exist
    for arm, _, _ in ARMS:
        cells = [(s, n, payload["scopes"]["bybit"][s][n]["arms"][arm])
                 for s in ("is", "oos") for n, _ in LANES]
        npass = sum(1 for _, _, c in cells
                    if (c["d_net"] or 0) > 0 and c["curve_better"])
        print(f"  bybit {arm:<9} {npass}/6  "
              f"nFlag={[c['n_flagged'] for _, _, c in cells]}", flush=True)
        print(f"         dNet={[c['d_net'] for _, _, c in cells]}", flush=True)
        print(f"         curve={[c['curve_better'] for _, _, c in cells]} "
              f"sits_on_dd={[c['diagnostic']['sits_on_drawdown'] for _, _, c in cells]} "
              f"conc={[c['diagnostic']['concentration'] for _, _, c in cells]}",
              flush=True)

    # ---- verdicts -------------------------------------------------------
    def cells_of(venue, arm):
        return [payload["scopes"][venue][s][n]["arms"][arm]
                for s in ("is", "oos") for n, _ in LANES]

    verdicts = {}
    for arm, _, _ in ARMS:
        cb = cells_of("bybit", arm)
        nb = cells_of("binance", arm)
        verdicts[arm] = {
            "bybit_pass": all((c["d_net"] or 0) > 0 and c["curve_better"] for c in cb),
            "bybit_curve_cells": sum(1 for c in cb if c["curve_better"]),
            "binance_pass": all((c["d_net"] or 0) > 0 and c["curve_better"] for c in nb),
            "binance_curve_cells": sum(1 for c in nb if c["curve_better"]),
            "all_robust": all(c["robust"] for c in cb),
            "any_sits_on_dd": any(c["diagnostic"]["sits_on_drawdown"] for c in cb),
        }
    payload["verdicts"] = verdicts
    payload["any_arm_passes_bybit"] = any(v["bybit_pass"] for v in verdicts.values())
    payload["any_arm_passes_both"] = any(
        v["bybit_pass"] and v["binance_pass"] for v in verdicts.values())
    payload["elapsed_sec"] = round(time.time() - t0, 2)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    print("\n" + "=" * 100, flush=True)
    print("  VERDICTS (Bybit is the 6/6 gate):", flush=True)
    for arm, v in verdicts.items():
        print(f"    {arm:<9} bybit {v['bybit_curve_cells']}/6 "
              f"pass={v['bybit_pass']} | binance {v['binance_curve_cells']}/6 "
              f"| robust={v['all_robust']} | sits_on_dd={v['any_sits_on_dd']}", flush=True)
    print("=" * 100, flush=True)
    print(f"  ANY ARM PASSES (bybit): "
          f"{'YES' if payload['any_arm_passes_bybit'] else 'NO'}", flush=True)
    print(f"  ANY ARM PASSES (both venues): "
          f"{'YES' if payload['any_arm_passes_both'] else 'NO'}", flush=True)
    print(f"wrote {OUT} ({payload['elapsed_sec']}s)", flush=True)


if __name__ == "__main__":
    main()
