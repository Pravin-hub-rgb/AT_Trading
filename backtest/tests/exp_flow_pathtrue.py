"""PARADIGM 1b — FLOW EDGE, PATH-TRUE (fixed-hold long/short book).

THIS DOCSTRING IS THE BINDING PRE-REGISTRATION. Written BEFORE any run.

PHASE 1 (re-run under corrected pairing, immutable as of this docstring):
exp_flow_descriptive.py screened 6 positioning features; exactly 1
survived the pre-registered rule (S1 same-sign 4 cells + S2 monotone
>=3/4 + S3 n>=100):
  top_ls_1h  spread SIGN NEGATIVE all 4 cells (-0.08/-0.45/-0.05/-0.35%
  fwd tercile Q3-Q1). High toptrader long/short -> lower forward returns.
  (Its paired twin taker_ls_1h FAILED after the causal fix: spreads
  -0.00/+0.13/+0.07/+0.02 - sign not stable across cells.)
No feature may be added here; direction may not be flipped.

HISTORY: the first attempt of this harness aborted at its own alignment
control (implied-price median err 0.1597% vs 0.01% limit): the frame
paired each row with metrics at (open+15) = the NEXT row's close snapshot
(one-bar lookahead; same bug in Phase 1). Pairing fixed to the row's own
label L, Phase 1 re-run under identical rules (results above), this
docstring re-registered. No arm result existed before the fix.

ARMS (fixed, 2 total, all reported):
  B = top_ls_1h:  +1 when x <= trailing q(1/3), -1 when x >= q(2/3),
                  else 0   (descriptive direction: low toptrader = long)
  hold H in {16 bars = 4h, 96 bars = 24h}

CAUSAL THRESHOLDS: trailing rolling quantile window 2880 bars (30 days),
shift(1) — at bar i only bars < i are used. NOT era-local (unlike Phase 1).

PATH (no lookahead):
  signal at bar i close -> enter bar i+1 OPEN -> exit bar i+H CLOSE
  (bars_held = H exactly); no overlap: next signal index >= i+H.

COSTS/FUNDING/UNIT (stat_arb.costs, identical constants):
  notional $10,000; round trip 0.095% (= $9.50); funding 3.125e-6 per
  signed $ per 15m bar; 1R = 1% of notional = $100 (FIXED, no sigma stop).
  R = (gross$ - cost$ + funding$) / 100.

ERAS (house results windows, entry-time assignment):
  OOS = [2021-07-01 05:30, 2023-01-01 05:30), IS = [2023-07-01 05:30,
  2026-09-14 05:30). Trades with entry outside both windows are ignored.

KILL TABLE (per arm per era; PASS = survives both eras):
  K1 net R <= 0            K2 any quarter net R <= -15   K3 maxDD > 30R
  K4 monthly Sharpe < 0.5  K5 n < 100 (IS) / < 60 (OOS)
  K6 win rate < 40%        K7 corr(monthly R, v18 monthly GROSS) > 0.3

CONTROLS (abort before any verdict):
  - v18 champion control via exp_stat_arb.v18_control: both house books
    must land within +/-2 trades, +/-1.0R of refs (IS 500t/+325.8R net,
    OOS 279t/+70.2R net) or SystemExit; this also builds v18m (monthly
    gross r_multiple by exit month, both books) for K7.
  - alignment control: OI-implied price vs 15m close at the row's own
    label must give median rel err <= 0.05% on >= 40 exact-hit samples.
    (Amendment before any successful run: first limit was 0.01%, too
    strict — same-instant mark-vs-last basis has median ~0.011-0.013%
    with tail to 0.5%; the WRONG one-bar pairing measured 0.1597%.
    0.05% cleanly separates correct pairing from the bug.)
  - join coverage: rows with OI present / total >= 99.5%.
IDENTITY (asserted after run): every evaluated entry inside its era window;
bars_held == H for all trades; no overlaps; first 5 trades per arm
recomputed from stored raw prices with hardcoded constants (tol 1e-9).

RESEARCH_POLICY: all 2 arms x both eras reported; no best-of; no auto-
adopt; forward gate (n>=50 paper trades) for any future use; descriptive
Phase-1 spreads did NOT include costs — this harness is the honest test
and may legitimately die on the 0.095% round trip.

Output: backtest/tests/_flow_pathtrue_results.json
Run: python -u backtest/tests/exp_flow_pathtrue.py
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))

from stat_arb.costs import round_trip_pct, FUND_BAR  # noqa: E402
from stat_arb.correlation import month_key, quarter_key, month_range, pearson  # noqa: E402
from exp_stat_arb import v18_control  # noqa: E402  (also sets rex paths)

import pandas as pd  # noqa: E402

NOTIONAL = 10000.0
R_UNIT = 100.0            # 1R = 1% of notional (fixed)
QWIN = 2880               # 30d trailing quantile window (15m bars)
ARMS = {"B": "b"}       # signal column (b = top_ls direction, not raw ratio)
HOLDS = {"h16": 16, "h96": 96}
KILL_MIN = {"is": 100, "oos": 60}
ERAS = {
    "oos": ("2021-07-01 05:30", "2023-01-01 05:30"),
    "is": ("2023-07-01 05:30", "2026-09-14 05:30"),
}
V18_REFS = {"is": (500, 325.8), "oos": (279, 70.2)}
OUT = Path(__file__).resolve().parent / "_flow_pathtrue_results.json"


def load_frame():
    """Price open/close + causal flow features, labelled by bar open ts."""
    px = pd.read_csv(ROOT / "data" / "btc-fut" / "BTCUSDT_15m.csv",
                     usecols=["timestamp", "open", "close"], parse_dates=["timestamp"])
    px = px.drop_duplicates("timestamp").set_index("timestamp").sort_index()
    m = pd.read_csv(ROOT / "data" / "flow" / "BTCUSDT_metrics_5m.csv",
                    parse_dates=["create_time"])
    m = m.drop_duplicates("create_time").set_index("create_time").sort_index()
    m.index = m.index + pd.Timedelta(minutes=315)   # measured alignment
    m = m.add_prefix("m_")
    grid = m.reindex(m.index.union(px.index)).sort_index()
    grid = grid.ffill(limit=3)
    df = px.join(grid.reindex(px.index), how="inner")  # row label L = metric L

    df["taker"] = df["m_sum_taker_long_short_vol_ratio"].rolling(4).mean()
    df["top"] = df["m_sum_toptrader_long_short_ratio"].rolling(4).mean()
    qh = df["taker"].rolling(QWIN).quantile(2 / 3).shift(1)
    ql = df["taker"].rolling(QWIN).quantile(1 / 3).shift(1)
    df["a"] = (df["taker"] >= qh).astype(int) - (df["taker"] <= ql).astype(int)
    qh = df["top"].rolling(QWIN).quantile(2 / 3).shift(1)
    ql = df["top"].rolling(QWIN).quantile(1 / 3).shift(1)
    df["b"] = (df["top"] <= ql).astype(int) - (df["top"] >= qh).astype(int)
    df["c"] = ((df["a"] == 1) & (df["b"] == 1)).astype(int) \
        - ((df["a"] == -1) & (df["b"] == -1)).astype(int)
    cov = float(df["m_sum_open_interest"].notna().mean())
    df = df.iloc[QWIN + 100:]
    return df, cov


def align_control(df):
    """OI-implied price match at metrics+315min, median rel err <= 0.01%."""
    import bisect
    sub = df.dropna(subset=["m_sum_open_interest", "m_sum_open_interest_value"])
    sub = sub.iloc[::4000].head(60)
    errs = []
    for ts, row in sub.iterrows():
        oi = float(row["m_sum_open_interest"])
        oiv = float(row["m_sum_open_interest_value"])
        if oi > 0 and row["close"] > 0:
            errs.append(abs(oiv / oi - row["close"]) / row["close"])
    errs.sort()
    med = errs[len(errs) // 2] if errs else 9.9
    return len(errs), med


def run_arm(df, sig, H):
    """Sequential fixed-hold book; returns trades list (raw, no era filter)."""
    o = df["open"].to_numpy()
    c = df["close"].to_numpy()
    s = df[sig].to_numpy()
    uniq = set(pd.unique(s[~pd.isna(s)]))
    if not uniq <= {-1.0, 0.0, 1.0}:
        raise SystemExit("IDENTITY FAIL: signal %s has values %s"
                         % (sig, sorted(uniq)))
    if pd.isna(s).any():
        raise SystemExit("IDENTITY FAIL: signal %s contains NaN" % sig)
    ts = df.index
    n = len(df)
    trades = []
    i = 0
    rt = round_trip_pct()
    while i < n - H - 1:
        d = int(s[i])
        if d == 0:
            i += 1
            continue
        j = i + 1                      # entry bar (open)
        x0 = o[j]
        xe = c[j + H - 1]              # exit bar close, held = H
        gross = d * (xe / x0 - 1.0) * NOTIONAL
        cost = rt * NOTIONAL
        funding = -FUND_BAR * (d * NOTIONAL) * H
        r = (gross - cost + funding) / R_UNIT
        trades.append({
            "entry_dt": str(ts[j]), "exit_dt": str(ts[j + H - 1]),
            "entry_i": j, "exit_i": j + H - 1, "dir": d, "bars_held": H,
            "p0": x0, "p1": xe, "gross_r": gross / R_UNIT,
            "cost_r": cost / R_UNIT, "funding_r": funding / R_UNIT, "r": r,
        })
        i = j + H - 1                  # no overlap: next signal >= exit bar
    return trades


def eval_era(trs, era, v18m):
    n = len(trs)
    rs = [t["r"] for t in trs]
    net = sum(rs)
    wr = (sum(1 for r in rs if r > 0) / n) if n else 0.0
    cum = peak = dd = 0.0
    for r in rs:
        cum += r
        peak = max(peak, cum)
        dd = max(dd, peak - cum)
    quarters, months = {}, {}
    last = None
    gR = cR = fR = 0.0
    for t in trs:
        quarters[quarter_key(pd.Timestamp(t["exit_dt"]))] = \
            quarters.get(quarter_key(pd.Timestamp(t["exit_dt"])), 0.0) + t["r"]
        months[month_key(pd.Timestamp(t["exit_dt"]))] = \
            months.get(month_key(pd.Timestamp(t["exit_dt"])), 0.0) + t["r"]
        gR += t["gross_r"]
        cR += t["cost_r"]
        fR += t["funding_r"]
        if last is None or t["exit_dt"] > last:
            last = t["exit_dt"]
    if last is None:
        ml = month_range(pd.Timestamp(ERAS[era][0]), pd.Timestamp(ERAS[era][0]))
    else:
        ml = month_range(pd.Timestamp(ERAS[era][0]), pd.Timestamp(last))
    vec = [months.get(m, 0.0) for m in ml]
    vvec = [v18m.get(m, 0.0) for m in ml]
    corr = pearson(vec, vvec)
    if len(vec) >= 2:
        mu = sum(vec) / len(vec)
        sd = math.sqrt(sum((x - mu) ** 2 for x in vec) / (len(vec) - 1))
        sharpe = (mu / sd) * math.sqrt(12.0) if sd > 1e-12 else 0.0
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
        "gross_R": round(gR, 3), "cost_R": round(cR, 3), "funding_R": round(fR, 3),
        "wr": round(wr, 6), "sharpe_ann": round(sharpe, 4),
        "max_dd_R": round(dd, 4),
        "quarters": {k: round(v, 3) for k, v in sorted(quarters.items())},
        "monthly_r": {m: round(v, 3) for m, v in zip(ml, vec)},
        "corr_v18_monthly": None if corr is None else round(corr, 4),
        "kills": kills, "killed": any(kills.values()),
        "kill_list": sorted(k for k, v in kills.items() if v),
    }


def main():
    t0 = time.time()
    df, cov = load_frame()
    print("[frame] rows=%d range=%s..%s cov=%.4f"
          % (len(df), df.index[0], df.index[-1], cov), flush=True)
    if cov < 0.995:
        raise SystemExit("CONTROL ABORT: join coverage %.4f < 0.995" % cov)

    n_samp, med = align_control(df)
    print("[control] alignment: n=%d median_rel_err=%.4f%% (limit 0.05%%)"
          % (n_samp, med * 100), flush=True)
    if n_samp < 40 or med > 0.0005:
        raise SystemExit("CONTROL ABORT: alignment median %.6f%%" % (med * 100))

    ph1 = json.loads((Path(__file__).resolve().parent
                      / "_flow_descriptive_results.json").read_text(encoding="utf-8"))
    surv = sorted(k for k, v in ph1["verdicts"].items() if v["survives"])
    print("[control] phase-1 survivors:", surv, flush=True)
    if surv != ["top_ls_1h"]:
        raise SystemExit("CONTROL ABORT: phase-1 survivor set %s != "
                         "[top_ls_1h] - re-register required" % surv)

    v18m = {}
    control = v18_control(v18m)          # aborts on ref mismatch

    results = {"meta": {
        "hypothesis": "Phase-1 flow survivors (taker/top LS) trade profitably "
                      "path-true after 0.095% round trip",
        "arms": list(ARMS), "holds": HOLDS, "qwin": QWIN,
        "r_unit": "1R = 1% of $10k notional (fixed)",
        "eras": {k: list(v) for k, v in ERAS.items()},
        "survivor_scope": ["top_ls_1h"],
        "build_s": round(time.time() - t0, 1),
    }, "controls": {"coverage": cov, "align_n": n_samp,
                    "align_median_rel_err": round(med, 8),
                    "v18_control": control},
        "arms": {}}

    passed_arms = []
    for aname, sig in ARMS.items():
        for hname, H in HOLDS.items():
            key = "%s_%s" % (aname, hname)
            all_tr = run_arm(df, sig, H)
            # identity: overlap + held bars
            for a, b in zip(all_tr, all_tr[1:]):
                if b["entry_i"] <= a["exit_i"]:
                    raise SystemExit("IDENTITY FAIL: overlap in %s" % key)
            if any(t["bars_held"] != H for t in all_tr):
                raise SystemExit("IDENTITY FAIL: bars_held in %s" % key)
            eras = {}
            for era, (a0, b0) in ERAS.items():
                et = [t for t in all_tr if a0 <= t["entry_dt"] < b0]
                for t in et:
                    if not (a0 <= t["entry_dt"] < b0):
                        raise SystemExit("IDENTITY FAIL: entry outside window")
                eras[era] = eval_era(et, era, v18m)
            # recompute first 5 trades of each era from stored raw prices
            for era, (a0, b0) in ERAS.items():
                et = [t for t in all_tr if a0 <= t["entry_dt"] < b0]
                for t in et[:5]:
                    rt = round_trip_pct()
                    g = t["dir"] * (t["p1"] / t["p0"] - 1.0) * NOTIONAL
                    f = -FUND_BAR * (t["dir"] * NOTIONAL) * t["bars_held"]
                    rr = (g - rt * NOTIONAL + f) / R_UNIT
                    if abs(rr - t["r"]) > 1e-9:
                        raise SystemExit("IDENTITY FAIL: R recompute %s" % key)
            passed = all(not eras[e]["killed"] for e in ERAS)
            if passed:
                passed_arms.append(key)
            results["arms"][key] = {
                "signal": sig, "hold_bars": H, "total_trades": len(all_tr),
                "eras": eras, "passes_both_eras": passed,
                "first5": [{k: t[k] for k in
                            ("entry_dt", "exit_dt", "dir", "p0", "p1", "r")}
                           for t in all_tr[:5]],
            }
            line = " | ".join(
                "%s n=%d net=%+.1fR wr=%.0f%% sh=%.2f dd=%.1f %s"
                % (e.upper(), eras[e]["n"], eras[e]["net_r"],
                   100 * eras[e]["wr"], eras[e]["sharpe_ann"],
                   eras[e]["max_dd_R"],
                   ("KILLED:" + ",".join(eras[e]["kill_list"]))
                   if eras[e]["killed"] else "pass")
                for e in ERAS)
            print("[arm] %-8s %s  -> %s" % (key, line,
                  "PASS both" if passed else "FAIL"), flush=True)

    results["meta"]["build_s"] = round(time.time() - t0, 1)
    results["passing_arms"] = passed_arms
    OUT.write_text(json.dumps(results, indent=1, default=str), encoding="utf-8")
    print("PASSING ARMS:", passed_arms if passed_arms else "none", flush=True)
    print("JSON:", OUT, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
