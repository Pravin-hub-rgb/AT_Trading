"""PARADIGM 3b - CARRY/FUNDING HARVEST, PATH-TRUE (Phase-2 book).

THIS DOCSTRING IS THE BINDING PRE-REGISTRATION. Written BEFORE any run.

PHASE 1 (already run, immutable): exp_carry_descriptive.py screened 5
carry features (funding/basis) on BTCUSDT with the carry position rule
dir = -sign(feature) baked into the forward return. Exactly 1 survived the
pre-registered rule (S1 same-sign 4 cells + S2 monotone >=3/4 + S3 n>=100
days):
  prem_1d  spreads oos_h1 -46.7bp / is_h1 -18.6bp / oos_h7 -121.9bp /
           is_h7 -167.2bp (negative = Q1 most-negative-basis days beat Q3
           most-positive - the basis works as a CONTRARIAN signal: perp
           below index -> long carry wins) - same sign + monotone in ALL 4
           cells.
No feature may be added; direction may not be flipped (Q1 = negative prem
is the long side by Phase-1 sign).

ARMS (fixed, 2 total, all reported): hold H in {1 day, 7 days}, cohorts
non-overlapping (next signal = t + H), single BTCUSDT position.

PATH (no lookahead):
  signal day t: prem_1d computed from day-t hourly premium closes (all
  <= t 23:59 IST) -> dir = -sign(prem_1d) -> ENTER at day t+1 CLOSE ->
  EXIT at day t+1+H CLOSE. Exit of cohort k == entry of cohort k+1
  (contiguous book).

FUNDING WINDOW (settlements the position actually receives):
  price entry/close instants are IST t+1 23:59 = UTC t+1 18:29; funding
  settles 00/08/16 UTC. Window = settlement dates (UTC) t+2 .. t+1+H
  (every settlement inside (entry, exit], none outside - verified by
  hand). Computed from daily settlement sums cumsum-shifted.

COSTS/TURNOVER (stat_arb.costs constants; the paradigm's point is low
turnover - charge only on position changes):
  1R = 1% of $10,000 notional = $100. Transition prev_dir -> dir:
  unchanged = 0; +/-1 <-> 0 = half RT (0.0475%); flip (+1 <-> -1) =
  full RT (0.095%). Book entry (first cohort) pays half RT; book exit
  (last cohort) pays half RT. Funding P&L = -dir * SumF (long pays
  positive funding). Cohort with NaN price on either end is skipped with
  NO transition charge (position carried). AMENDMENT after the first run
  aborted at the contiguity identity BEFORE any verdict was computed:
  21 days in the premium history have no hourly rows (kline gaps:
  2021-07-01, 2021-07-24..27, 2022-10-02, 2023-02-24, 2026-06-29 + the
  2026-09 tail after funding/premium end) - a NaN (or exactly 0) signal
  now CARRIES the open position: cohort emitted with dir = prev_dir,
  cost 0, no transition; before the book has started such days are
  skipped. This preserves the pre-registered contiguity identity
  (b.entry == a.exit) and is the literal execution of the "position
  carried" rule above. The SAME aborted run also caught a stepping bug in
  the h7 arm (day-by-day iteration instead of signal t -> t+H; h1 was
  arithmetically unaffected since step == H == 1); fixed before any arm
  JSON was written - both arms were then produced by this code as-is.

ERAS (house results windows, cohort ENTRY-day assignment):
  OOS = [2021-07-01, 2023-01-01), IS = [2023-07-01, 2026-09-10)
COVERAGE: funding data ends 2026-08-31 - any cohort whose forward
  funding window (t+2..t+1+H) extends past the last settlement date is
  DROPPED entirely (no partial-funding cohort ever enters era stats).

KILL TABLE (per arm per era; PASS = zero kills BOTH eras):
  K1 net R <= 0            K2 any quarter net R <= -15   K3 maxDD > 30R
  K4 monthly Sharpe < 0.5  K6 cohort win rate < 40%
  K7 corr(monthly R, v18 monthly GROSS) > 0.3
  K5 (PRE-REGISTERED DEVIATION for a held carry book): the house
    100(IS)/60(OOS) threshold presumes trade-level independence that a
    contiguous book does not have; here K5 = era months < 24 (IS) /
    < 12 (OOS) OR direction changes within the era < 3 (a book that
    never flips is regime-locked, not a tradeable carry rule).

CONTROLS (abort before verdicts):
  - v18 champion control via exp_stat_arb.v18_control (both house books
    within refs; builds v18m for K7).
  - Phase-1 survivor control: _carry_descriptive_results.json must report
    survivors == ['prem_1d'], else re-register.
  - data controls: premium/funding loaders must yield >= 80 monthly zips
    each; daily price panel non-empty; funding last date >= 2026-08-25.

IDENTITY (after run): entry_d == signal_d + 1 day; exit_d == entry_d + H
  days; consecutive cohorts: b.entry == a.exit; first 5 cohorts recompute
  from stored prices, SumF, transition cost within 1e-9; funding window
  first cohort recompute from raw settlement rows within 1e-12; monthly
  keys from EXIT date (house convention).

RESEARCH_POLICY: both arms x both eras reported; no best-of; no auto-
adopt. Output: live_stuff/tests/_carry_pathtrue_results.json
Run: python -u live_stuff/tests/exp_carry_pathtrue.py
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))

from stat_arb.costs import round_trip_pct  # noqa: E402
from stat_arb.correlation import month_key, quarter_key, month_range, pearson  # noqa: E402
from exp_stat_arb import v18_control  # noqa: E402
from exp_carry_descriptive import build, load_funding, load_premium_daily  # noqa: E402

OUT = Path(__file__).resolve().parent / "_carry_pathtrue_results.json"
PH1 = Path(__file__).resolve().parent / "_carry_descriptive_results.json"

FEATURE = "prem_1d"
NOTIONAL = 10_000.0
R_UNIT = 100.0
HOLD_DAYS = {"h1": 1, "h7": 7}
ERAS = {"oos": ("2021-07-01", "2023-01-01"), "is": ("2023-07-01", "2026-09-10")}
KILL_MIN_MONTHS = {"is": 24, "oos": 12}
KILL_MIN_FLIPS = 3
RT = round_trip_pct()                       # 0.00095


def run_book(f: pd.DataFrame, px: pd.Series, ds: pd.Series, H: int,
             last_fund_day) -> list[dict]:
    dates = list(px.index)
    day_to_i = {d: i for i, d in enumerate(dates)}
    cum = ds.cumsum()
    cohorts = []
    prev_dir = 0
    start_i = 0
    stop_i = len(dates) - H - 2
    i = start_i
    while i <= stop_i:                        # next signal = t + H after emit
        d = dates[i]
        sig = f[FEATURE].get(d, float("nan"))
        if pd.isna(sig) or sig == 0.0:
            if prev_dir == 0:
                i += 1                        # gap before book start
                continue
            dirn = prev_dir                   # carry position through gap
        else:
            dirn = -1.0 if sig > 0 else 1.0
        entry_d = dates[i + 1]
        exit_d = dates[i + 1 + H]
        if exit_d > last_fund_day:          # funding window incomplete
            break
        p0, p1 = float(px.at[entry_d]), float(px.at[exit_d])
        if pd.isna(p0) or pd.isna(p1):
            i += 1                            # skip: no transition charge
            continue
        # funding: settlement dates t+2 .. t+1+H  ==  cum[exit] - cum[signal+1]
        sumf = float(cum.at[exit_d] - cum.at[entry_d])
        # transition cost
        if prev_dir == 0:
            cost = RT / 2.0
        elif dirn == prev_dir:
            cost = 0.0
        elif abs(dirn - prev_dir) == 2.0:
            cost = RT
        else:
            cost = RT / 2.0
        gross = dirn * (p1 / p0 - 1.0)
        r = (gross - cost - dirn * sumf) * NOTIONAL / R_UNIT
        cohorts.append({
            "signal_d": str(d), "entry_d": str(entry_d), "exit_d": str(exit_d),
            "signal_i": i, "entry_i": day_to_i[entry_d],
            "exit_i": day_to_i[exit_d], "dir": dirn, "prev_dir": prev_dir,
            "p0": p0, "p1": p1, "sumf": sumf, "cost": cost, "r": r,
            "flip": prev_dir != 0 and dirn != prev_dir,
            "change": prev_dir != dirn,
        })
        prev_dir = dirn
        i += H
    if cohorts:                              # book close half-RT
        last = cohorts[-1]
        if last["dir"] != 0:
            close_cost = RT / 2.0
            last["r"] -= close_cost * NOTIONAL / R_UNIT
            last["cost"] += close_cost
            last["book_close_cost"] = close_cost
    return cohorts


def eval_era(cs: list[dict], era: str, v18m: dict) -> dict:
    n = len(cs)
    rs = [c["r"] for c in cs]
    net = sum(rs)
    wr = (sum(1 for r in rs if r > 0) / n) if n else 0.0
    cumv = peak = dd = 0.0
    for r in rs:
        cumv += r
        peak = max(peak, cumv)
        dd = max(dd, peak - cumv)
    quarters, months = {}, {}
    last = None
    for c in cs:
        ex = pd.Timestamp(c["exit_d"])
        qk, mk = quarter_key(ex), month_key(ex)
        quarters[qk] = quarters.get(qk, 0.0) + c["r"]
        months[mk] = months.get(mk, 0.0) + c["r"]
        if last is None or c["exit_d"] > last:
            last = c["exit_d"]
    flips = sum(1 for c in cs if c["flip"])
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
        "K5_min_months_or_flips": (len(ml) < KILL_MIN_MONTHS[era]
                                   or flips < KILL_MIN_FLIPS),
        "K6_wr_lt_40": wr < 0.40,
        "K7_corr_gt_0.3": (corr is not None and corr > 0.3),
    }
    return {"n": n, "flips": flips, "net_r": round(net, 4),
            "wr": round(wr, 6), "sharpe_ann": round(sharpe, 4),
            "max_dd_R": round(dd, 4),
            "months": len(ml),
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
    if surv != [FEATURE]:
        raise SystemExit("CONTROL ABORT: survivors %s != [%r] - re-register"
                         % (surv, FEATURE))

    n_fz = len(list((ROOT / "data" / "flow" / "funding").glob("*.zip")))
    n_pz = len(list((ROOT / "data" / "flow" / "premium1h").glob("*.zip")))
    if n_fz < 80 or n_pz < 80:
        raise SystemExit("CONTROL ABORT: funding zips %d premium zips %d"
                         % (n_fz, n_pz))
    fund = load_funding()
    fund["date"] = fund["ts"].dt.date
    prem = load_premium_daily()
    f, px, fwd, ds, last_fund_day = build()
    if str(last_fund_day) < "2026-08-25":
        raise SystemExit("CONTROL ABORT: funding ends %s" % last_fund_day)
    print("[data] premium days=%d price days=%d funding..%s"
          % (len(prem), len(px), last_fund_day), flush=True)

    v18m = {}
    control = v18_control(v18m)

    res = {"meta": {"hypothesis": "BTC carry book (dir=-sign(prem_1d)) "
                    "survives price risk + turnover costs path-true",
                    "arms": list(HOLD_DAYS), "r_unit": "1R = 1% of $10k",
                    "eras": {k: list(v) for k, v in ERAS.items()},
                    "survivor_scope": surv,
                    "k5_note": "months>=24 IS / >=12 OOS AND >=3 direction "
                               "changes per era (pre-registered carry "
                               "deviation)",
                    "build_s": round(time.time() - t0, 1)},
           "controls": {"v18_control": control, "phase1_survivors": surv,
                        "funding_last": str(last_fund_day)},
           "arms": {}}
    passed = []
    for hname, H in HOLD_DAYS.items():
        all_c = run_book(f, px, ds, H, last_fund_day)
        # identity: entry==signal+1, exit==entry+H, contiguous, recompute
        for c in all_c:
            si = pd.Timestamp(c["signal_d"])
            if pd.Timestamp(c["entry_d"]) != si + pd.Timedelta(days=1):
                raise SystemExit("IDENTITY FAIL: entry != signal+1 %s" % hname)
            if pd.Timestamp(c["exit_d"]) != pd.Timestamp(c["entry_d"]) \
                    + pd.Timedelta(days=H):
                raise SystemExit("IDENTITY FAIL: exit != entry+H %s" % hname)
        for a, b in zip(all_c, all_c[1:]):
            if b["entry_d"] != a["exit_d"]:
                raise SystemExit("IDENTITY FAIL: book not contiguous %s %s.."
                                 % (hname, a["exit_d"]))
        for c in all_c[:5]:
            gross = c["dir"] * (c["p1"] / c["p0"] - 1.0)
            rr = (gross - c["cost"] - c["dir"] * c["sumf"]) \
                * NOTIONAL / R_UNIT
            if abs(rr - c["r"]) > 1e-9:
                raise SystemExit("IDENTITY FAIL: cohort R recompute %s" % hname)
        # funding-window recompute from raw rows for first cohort
        c0 = all_c[0]
        si, ei = pd.Timestamp(c0["signal_d"]), pd.Timestamp(c0["entry_d"])
        lo = si + pd.Timedelta(days=2)
        hi = ei + pd.Timedelta(days=H)
        win = fund[(fund["date"] >= lo.date()) & (fund["date"] <= hi.date())]
        if abs(float(win["rate"].sum()) - c0["sumf"]) > 1e-12:
            raise SystemExit("IDENTITY FAIL: funding window recompute %s"
                             % hname)
        eras = {}
        for era, (a0, b0) in ERAS.items():
            ec = [c for c in all_c if a0 <= c["entry_d"] < b0]
            eras[era] = eval_era(ec, era, v18m)
        ok = all(not eras[e]["killed"] for e in ERAS)
        if ok:
            passed.append(hname)
        res["arms"][hname] = {"signal": FEATURE, "hold_days": H,
                              "total_cohorts": len(all_c),
                              "total_flips": sum(1 for c in all_c
                                                 if c["flip"]),
                              "eras": eras, "passes_both_eras": ok,
                              "first5": [{k: c[k] for k in
                                          ("signal_d", "entry_d", "exit_d",
                                           "dir", "r", "cost")}
                                         for c in all_c[:5]]}
        line = " | ".join(
            "%s n=%d flips=%d net=%+.1fR wr=%.0f%% sh=%.2f dd=%.1f months=%d %s"
            % (e.upper(), eras[e]["n"], eras[e]["flips"], eras[e]["net_r"],
               100 * eras[e]["wr"], eras[e]["sharpe_ann"],
               eras[e]["max_dd_R"], eras[e]["months"],
               ("KILLED:" + ",".join(eras[e]["kill_list"]))
               if eras[e]["killed"] else "pass")
            for e in ERAS)
        print("[arm] %-3s %s -> %s" % (hname, line,
              "PASS both" if ok else "FAIL"), flush=True)

    res["passing_arms"] = passed
    res["meta"]["build_s"] = round(time.time() - t0, 1)
    OUT.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print("PASSING ARMS:", passed if passed else "none", flush=True)
    print("JSON:", OUT, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
