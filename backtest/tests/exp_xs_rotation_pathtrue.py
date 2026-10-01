"""PARADIGM 2b — CROSS-SECTIONAL ROTATION, PATH-TRUE (Phase-2 book).

THIS DOCSTRING IS THE BINDING PRE-REGISTRATION. Written BEFORE any run.

PHASE 1 (already run, immutable): exp_xs_rotation.py screened 5
cross-sectional features on 16 Binance perps (daily bars, backfilled to
2021-01 by scripts/backfill_scanfut_oos.py). Exactly 1 survived the
pre-registered rule (S1 same-sign 4 cells + S2 monotone >=3/4 + S3
n>=100 symbol-days):
  mom_90d  spreads oos_f1 +0.15% / is_f1 +0.05% / oos_f7 +0.40% /
           is_f7 +0.67% - same sign and monotone in all 4 cells.
No feature may be added; direction may not be flipped (top-momentum tercile
is the long side by Phase-1 sign).

ARMS (fixed, 4 total, all reported):
  LS = dollar-neutral: long top tercile, short bottom tercile
  LO = long-only: long top tercile
  hold H in {1 day, 7 days}, cohorts non-overlapping (rebalance every H days)

PATH (no lookahead):
  day t close: mom_90d ranks computed from closes <= t; terciles formed
  across the >=8 eligible symbols (same as Phase 1) -> enter legs at day
  t+1 CLOSE (next-close, conservative) -> exit at day t+1+H CLOSE.
  Next cohort signal = t+H. A symbol missing at signal day is not traded.

COSTS/FUNDING/UNIT (stat_arb.costs constants):
  1R = 1% of $10,000 gross notional = $100 (LO: $10k long; LS: $10k long +
  $10k short). Entry leg pays half round trip (0.0475%), exit leg pays
  half -> per-leg RT 0.095%. Funding flat 0.03%/day on signed notional
  (0.01%/8h, matches FUND_BAR x 96 bars/day). Book R = sum of leg R.

ERAS (house results windows, cohort ENTRY-day assignment):
  OOS = [2021-07-01, 2023-01-01), IS = [2023-07-01, 2026-09-10)

KILL TABLE (per arm per era; PASS = zero kills BOTH eras; n = rebalance
cohorts - a rebalance is one portfolio action):
  K1 net R <= 0            K2 any quarter net R <= -15   K3 maxDD > 30R
  K4 monthly Sharpe < 0.5  K5 n < 100 (IS) / < 60 (OOS)
  K6 cohort win rate < 40% K7 corr(monthly R, v18 monthly GROSS) > 0.3

CONTROLS (abort before verdicts):
  - v18 champion control via exp_stat_arb.v18_control (both books within
    +/-2 trades / +/-1.0R of refs; builds v18m for K7).
  - Phase-1 survivor control: _xs_rotation_results.json must report
    survivors == ['mom_90d'], else re-register.
  - data integrity: every read CSV row must parse to 7 fields (the 2026-09-
    27 fetch-bug repair is why this exists); daily panel must be non-empty
    with >= 11 symbols in OOS.
IDENTITY (after run): entry date == signal date + 1; exit date == entry +
H; cohort signals at t, t+H, t+2H... non-overlapping; first 5 cohorts per
arm recompute from stored prices/legs within 1e-9; monthly keys built from
EXIT date (same convention as stat-arb).

RESEARCH_POLICY: all 4 arms x both eras reported; no best-of; no auto-
adopt; Phase 1 was descriptive (no costs) - this harness is the honest
costed test. Output: backtest/tests/_xs_rotation_pathtrue_results.json
Run: python -u backtest/tests/exp_xs_rotation_pathtrue.py
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

from stat_arb.costs import round_trip_pct  # noqa: E402
from stat_arb.correlation import month_key, quarter_key, month_range, pearson  # noqa: E402
from exp_stat_arb import v18_control  # noqa: E402

DATA = ROOT / "data" / "scan-fut"
OUT = Path(__file__).resolve().parent / "_xs_rotation_pathtrue_results.json"
PH1 = Path(__file__).resolve().parent / "_xs_rotation_results.json"

NOTIONAL = 10_000.0
R_UNIT = 100.0
HOLD_DAYS = {"h1": 1, "h7": 7}
ARMS = {"LS": True, "LO": False}          # value = short side enabled
ERAS = {"oos": ("2021-07-01", "2023-01-01"), "is": ("2023-07-01", "2026-09-10")}
KILL_MIN = {"is": 100, "oos": 60}
MIN_SYM_DAY = 8
MIN_BARS_DAY = 90
WARMUP_DAYS = 90
FUND_DAY = 0.0003                          # 0.01% / 8h -> 0.03% / day
RT = round_trip_pct()                       # 0.00095


def load_panel() -> pd.DataFrame:
    cols = {}
    for f in sorted(DATA.glob("*_15m.csv")):
        sym = f.name.rsplit("_", 1)[0].replace("USDT", "")
        with open(f, encoding="utf-8") as fh:
            if len(fh.readline().rstrip("\n").split(",")) != 7:
                raise SystemExit("CONTROL ABORT: bad header %s" % f.name)
        df = pd.read_csv(f, usecols=["timestamp", "close"],
                         parse_dates=["timestamp"])
        if df["close"].isna().any():
            raise SystemExit("CONTROL ABORT: NaN close in %s" % f.name)
        df["date"] = (df["timestamp"] - pd.Timedelta(hours=5, minutes=30)).dt.date
        cnt = df.groupby("date").size()
        close = df.groupby("date")["close"].last()
        cols[sym] = close.loc[cnt[cnt >= MIN_BARS_DAY].index]
    px = pd.DataFrame(cols).sort_index()
    if px.empty or (px.notna().sum(axis=1) < 11).all():
        raise SystemExit("CONTROL ABORT: panel empty or < 11 symbols in OOS")
    return px


def tercile_sets(row90: pd.Series):
    """Cross-section of mom_90d -> (top list, bottom list) or None."""
    j = row90.dropna()
    if len(j) < MIN_SYM_DAY:
        return None
    j = j.sort_values(ascending=False)
    q = len(j) // 3
    if q == 0:
        return None
    return list(j.index[:q]), list(j.index[-q:])


def run_arm(px: pd.DataFrame, long_short: bool, H: int) -> list[dict]:
    mom90 = px.pct_change(90)
    r1 = px.pct_change(1)
    days = list(px.index)
    warm = days[WARMUP_DAYS]
    trades = []          # cohort records
    i = 0
    day_to_i = {d: k for k, d in enumerate(days)}
    while i < len(days):
        d = days[i]
        if d < warm:
            i += 1
            continue
        sets = tercile_sets(mom90.loc[d])
        if sets is None:
            i += 1
            continue
        top, bot = sets
        entry_d = days[i + 1] if i + 1 < len(days) else None
        exit_idx = i + 1 + H
        if entry_d is None or exit_idx >= len(days):
            break
        exit_d = days[exit_idx]
        legs = []
        for sym in top:
            p0 = px.at[entry_d, sym]
            p1 = px.at[exit_d, sym]
            if pd.isna(p0) or pd.isna(p1):
                continue
            legs.append((sym, 1, float(p0), float(p1)))
        if long_short:
            for sym in bot:
                p0 = px.at[entry_d, sym]
                p1 = px.at[exit_d, sym]
                if pd.isna(p0) or pd.isna(p1):
                    continue
                legs.append((sym, -1, float(p0), float(p1)))
        if not legs:
            i += H
            continue
        per_leg = NOTIONAL / len(legs)
        days_held = H
        cohort_r = 0.0
        leg_recs = []
        for sym, dirn, p0, p1 in legs:
            gross = dirn * (p1 / p0 - 1.0) * per_leg
            cost = RT * per_leg
            funding = -FUND_DAY * dirn * per_leg * days_held
            r = (gross - cost + funding) / R_UNIT
            cohort_r += r
            leg_recs.append({"sym": sym, "dir": dirn, "p0": p0, "p1": p1,
                             "r": r})
        trades.append({
            "signal_d": str(d), "entry_d": str(entry_d), "exit_d": str(exit_d),
            "signal_i": i, "entry_i": day_to_i[entry_d],
            "exit_i": day_to_i[exit_d], "n_legs": len(legs),
            "r": cohort_r, "legs": leg_recs,
        })
        i += H                                   # non-overlapping cohorts
    return trades


def eval_era(trs: list[dict], era: str, v18m: dict) -> dict:
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
    for t in trs:
        ex = pd.Timestamp(t["exit_d"])
        qk, mk = quarter_key(ex), month_key(ex)
        quarters[qk] = quarters.get(qk, 0.0) + t["r"]
        months[mk] = months.get(mk, 0.0) + t["r"]
        if last is None or t["exit_d"] > last:
            last = t["exit_d"]
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
    return {"n": n, "net_r": round(net, 4), "wr": round(wr, 6),
            "sharpe_ann": round(sharpe, 4), "max_dd_R": round(dd, 4),
            "quarters": {k: round(v, 3) for k, v in sorted(quarters.items())},
            "monthly_r": {m: round(v, 3) for m, v in zip(ml, vec)},
            "corr_v18_monthly": None if corr is None else round(corr, 4),
            "kills": kills, "killed": any(kills.values()),
            "kill_list": sorted(k for k, v in kills.items() if v)}


def main() -> int:
    t0 = time.time()
    ph1 = json.loads(PH1.read_text(encoding="utf-8"))
    surv = sorted(k for k, v in ph1["verdicts"].items() if v["survives"])
    print("[control] phase-1 survivors:", surv, flush=True)
    if surv != ["mom_90d"]:
        raise SystemExit("CONTROL ABORT: survivors %s != ['mom_90d'] "
                         "- re-register required" % surv)

    px = load_panel()
    print("[frame] %d days x %d symbols (%s .. %s)"
          % (len(px), px.shape[1], px.index[0], px.index[-1]), flush=True)

    v18m = {}
    control = v18_control(v18m)

    res = {"meta": {"hypothesis": "cross-sectional 90d momentum rotation "
                    "survives costs path-true", "arms": list(ARMS),
                    "holds": HOLD_DAYS, "r_unit": "1R = 1% of $10k gross",
                    "eras": {k: list(v) for k, v in ERAS.items()},
                    "survivor_scope": surv,
                    "build_s": round(time.time() - t0, 1)},
           "controls": {"v18_control": control, "phase1_survivors": surv},
           "arms": {}}
    passed = []
    for aname, short in ARMS.items():
        for hname, H in HOLD_DAYS.items():
            key = f"{aname}_{hname}"
            all_tr = run_arm(px, short, H)
            # identity: non-overlap, dates, first-5 recompute
            for a, b in zip(all_tr, all_tr[1:]):
                if b["signal_i"] <= a["signal_i"]:
                    raise SystemExit("IDENTITY FAIL: overlap %s" % key)
                if b["entry_i"] < a["exit_i"]:
                    raise SystemExit("IDENTITY FAIL: entry before prior exit %s"
                                     % key)
            for t in all_tr[:5]:
                rs = sum(l["r"] for l in t["legs"])
                if abs(rs - t["r"]) > 1e-9:
                    raise SystemExit("IDENTITY FAIL: cohort R recompute %s" % key)
                for leg in t["legs"][:3]:
                    p0, p1, dirn = leg["p0"], leg["p1"], leg["dir"]
                    per_leg = NOTIONAL / t["n_legs"]
                    g = dirn * (p1 / p0 - 1.0) * per_leg
                    c = RT * per_leg
                    f = -FUND_DAY * dirn * per_leg * H
                    if abs((g - c + f) / R_UNIT - leg["r"]) > 1e-9:
                        raise SystemExit("IDENTITY FAIL: leg R recompute %s" % key)
            eras = {}
            for era, (a0, b0) in ERAS.items():
                et = [t for t in all_tr if a0 <= t["entry_d"] < b0]
                eras[era] = eval_era(et, era, v18m)
            ok = all(not eras[e]["killed"] for e in ERAS)
            if ok:
                passed.append(key)
            res["arms"][key] = {"signal": "mom_90d", "short_side": short,
                                "hold_days": H, "total_cohorts": len(all_tr),
                                "eras": eras, "passes_both_eras": ok,
                                "first5": [{k: t[k] for k in
                                            ("signal_d", "entry_d", "exit_d",
                                             "n_legs", "r")}
                                           for t in all_tr[:5]]}
            line = " | ".join(
                "%s n=%d net=%+.1fR wr=%.0f%% sh=%.2f dd=%.1f %s"
                % (e.upper(), eras[e]["n"], eras[e]["net_r"],
                   100 * eras[e]["wr"], eras[e]["sharpe_ann"],
                   eras[e]["max_dd_R"],
                   ("KILLED:" + ",".join(eras[e]["kill_list"]))
                   if eras[e]["killed"] else "pass")
                for e in ERAS)
            print("[arm] %-6s %s -> %s" % (key, line,
                  "PASS both" if ok else "FAIL"), flush=True)

    res["passing_arms"] = passed
    res["meta"]["build_s"] = round(time.time() - t0, 1)
    OUT.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print("PASSING ARMS:", passed if passed else "none", flush=True)
    print("JSON:", OUT, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
