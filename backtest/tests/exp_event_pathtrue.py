"""PARADIGM 4b - EVENT-DRIVEN TRADES, PATH-TRUE (Phase-2 book).

THIS DOCSTRING IS THE BINDING PRE-REGISTRATION. Written BEFORE any run.

PHASE 1 (already run, immutable): exp_event_descriptive.py screened 28
candidates (7 event_types x 4 windows) on 382 exact-UTC scheduled US
macro events (all known_in_advance, date_only families excluded up
front). Exactly 2 survived the pre-registered rule (S1 n>=10 both eras +
S2 same mean sign both eras + S3 consistency>=0.60 both eras):
  ppi|post1            mean +0.43% OOS / +0.06% IS, cons 0.67/0.62,
                       n 18/37 - LONG BTC for 1h after PPI release
  fomc_statement|pre24 mean +1.75% OOS / +0.04% IS, cons 0.75/0.60,
                       n 12/25 - LONG BTC in the 24h before FOMC
No candidate may be added; directions fixed from Phase 1 (+1 both);
multiplicity over 28 candidates is the stated reason Phase 2's costed
kill table is mandatory before anything is believed.

ARMS (fixed, 2 total, all reported): one arm per survivor.

PATH: anchors identical to Phase 1 (first 15m bar whose END >= anchor
instant, IST) - already causal (entry delayed up to 15m after the event
instant, or at T-24h for pre24 where the schedule is public in advance).
Era by event UTC date. Each event = one trade, independent.

COSTS/UNIT (stat_arb.costs constants): 1R = 1% of $10,000 = $100.
  per event trade: r = dir * (p1/p0 - 1) - RT (full round trip 0.095%,
  entry+exit = one RT). No funding line (windows <= 24h, funding is
  immaterial; stated up front so it is not a silent omission).

ERAS (house results windows, by event date):
  OOS = [2021-07-01, 2023-01-01), IS = [2023-07-01, 2026-09-10)

KILL TABLE (per arm per era; PASS = zero kills BOTH eras):
  K1 net R <= 0            K2 any quarter net R <= -15   K3 maxDD > 30R
  K4 monthly Sharpe < 0.5  K6 event win rate < 40%
  K7 corr(monthly R, v18 monthly GROSS) > 0.3
  K5 (PRE-REGISTERED DEVIATION for an event book): n = EVENTS, threshold
    >= 12 (OOS) / >= 24 (IS) - the house 100/60 presumes trade-level
    frequency a monthly calendar cannot produce (max ~18/41 even for
    monthly releases); calendar-bounded by construction.

CONTROLS (abort before verdicts):
  - v18 champion control via exp_stat_arb.v18_control (builds v18m).
  - Phase-1 survivor control: _event_descriptive_results.json must
    report exactly survivors ['fomc_statement|pre24', 'ppi|post1'] (sorted)
    and their directions (+1, +1); any mismatch -> re-register.
  - event-data control: 382 exact-timestamp events, all known_in_advance,
    all evidence scheduled_exact_utc*; price bars >= 199k.

IDENTITY (after run): for the first 5 trades of each arm, entry/exit
  prices recompute from raw CSV bars + bisect anchor rule within 1e-9;
  entry anchor >= event instant for post windows, entry anchor at T-24h
  for pre24 (event time - 24h); era matches event date; monthly keys
  from EXIT instant (house convention); consecutive trades in an arm are
  strictly time-ordered (no duplicated event).

RESEARCH_POLICY: both arms x both eras reported; no best-of; no auto-
adopt. Output: backtest/tests/_event_pathtrue_results.json
Run: python -u backtest/tests/exp_event_pathtrue.py
"""
from __future__ import annotations

import json
import math
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))

from stat_arb.costs import round_trip_pct  # noqa: E402
from stat_arb.correlation import month_key, quarter_key, month_range, pearson  # noqa: E402
from exp_stat_arb import v18_control  # noqa: E402
from exp_event_descriptive import load_events, load_price_anchors, anchor_price  # noqa: E402

EVENTS_JSON = Path(__file__).resolve().parent / "_event_descriptive_results.json"
OUT = Path(__file__).resolve().parent / "_event_pathtrue_results.json"

NOTIONAL = 10_000.0
R_UNIT = 100.0
WINDOWS = {"pre24": (-24, 0), "post1": (0, 1)}
ERAS = {"oos": ("2021-07-01", "2023-01-01"), "is": ("2023-07-01", "2026-09-10")}
KILL_MIN_N = {"is": 24, "oos": 12}
RT = round_trip_pct()
EXPECT_SURVIVORS = ["fomc_statement|pre24", "ppi|post1"]


def run_arm(evs: list[dict], et: str, win: str, direction: float,
            ends, closes) -> list[dict]:
    wh0, wh1 = WINDOWS[win]
    trades = []
    for e in evs:
        if e["type"] != et:
            continue
        ed = e["t"].date().isoformat()
        a_utc = e["t"] + timedelta(hours=wh0)
        b_utc = e["t"] + timedelta(hours=wh1)
        p0 = anchor_price(a_utc, ends, closes)
        p1 = anchor_price(b_utc, ends, closes)
        if pd.isna(p0) or pd.isna(p1) or p0 <= 0:
            continue
        r = (direction * (p1 / p0 - 1.0) - RT) * NOTIONAL / R_UNIT
        trades.append({
            "event_d": ed, "event_t": e["t"].isoformat(),
            "entry_anchor": a_utc.isoformat(), "exit_anchor": b_utc.isoformat(),
            "entry_d": str(pd.Timestamp(
                a_utc.astimezone(timezone(timedelta(hours=5, minutes=30))
                                 ).replace(tzinfo=None).date())),
            "exit_d": str(pd.Timestamp(
                b_utc.astimezone(timezone(timedelta(hours=5, minutes=30))
                                 ).replace(tzinfo=None).date())),
            "p0": p0, "p1": p1, "dir": direction, "r": r,
        })
    trades.sort(key=lambda t: t["event_t"])
    return trades


def eval_era(ts: list[dict], era: str, v18m: dict) -> dict:
    n = len(ts)
    rs = [t["r"] for t in ts]
    net = sum(rs)
    wr = (sum(1 for r in rs if r > 0) / n) if n else 0.0
    cumv = peak = dd = 0.0
    for r in rs:
        cumv += r
        peak = max(peak, cumv)
        dd = max(dd, peak - cumv)
    quarters, months = {}, {}
    last = None
    for t in ts:
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
        "K5_min_events": n < KILL_MIN_N[era],
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
    ph1 = json.loads(EVENTS_JSON.read_text(encoding="utf-8"))
    surv = sorted(f"{et}|{w}" for et, ws in ph1["verdicts"].items()
                  for w, v in ws.items() if v["survives"])
    dirs = {f"{et}|{w}": v["direction"]
            for et, ws in ph1["verdicts"].items()
            for w, v in ws.items() if v["survives"]}
    print("[control] phase-1 survivors:", surv, flush=True)
    if surv != EXPECT_SURVIVORS:
        raise SystemExit("CONTROL ABORT: survivors %s != %s - re-register"
                         % (surv, EXPECT_SURVIVORS))
    if any(dirs[s] != 1 for s in EXPECT_SURVIVORS):
        raise SystemExit("CONTROL ABORT: directions %s - re-register" % dirs)

    evs = load_events()
    if len(evs) != 382:
        raise SystemExit("CONTROL ABORT: %d events != 382" % len(evs))
    ends, closes = load_price_anchors()
    if len(closes) < 199_000:
        raise SystemExit("CONTROL ABORT: %d price bars" % len(closes))
    print("[data] events=%d bars=%d" % (len(evs), len(closes)), flush=True)

    v18m = {}
    control = v18_control(v18m)

    res = {"meta": {"hypothesis": "scheduled-event drift (ppi post1 long, "
                    "fomc pre24 long) survives costs path-true",
                    "arms": EXPECT_SURVIVORS, "r_unit": "1R = 1% of $10k",
                    "eras": {k: list(v) for k, v in ERAS.items()},
                    "survivor_scope": surv,
                    "k5_note": "n = events, >=12 OOS / >=24 IS (pre-"
                               "registered calendar-bounded deviation)",
                    "build_s": round(time.time() - t0, 1)},
           "controls": {"v18_control": control, "phase1_survivors": surv,
                        "phase1_directions": dirs, "events": len(evs)},
           "arms": {}}
    passed = []
    for key in EXPECT_SURVIVORS:
        et, win = key.split("|")
        d = float(dirs[key])
        all_t = run_arm(evs, et, win, d, ends, closes)
        # identity: time-ordered, unique events, anchors, first-5 recompute
        ets = [t["event_t"] for t in all_t]
        if ets != sorted(ets) or len(set(ets)) != len(ets):
            raise SystemExit("IDENTITY FAIL: ordering/dup %s" % key)
        wh0 = WINDOWS[win][0]
        for t in all_t[:5]:
            ev_t = datetime.fromisoformat(t["event_t"])
            a_t = datetime.fromisoformat(t["entry_anchor"])
            if abs((a_t - ev_t).total_seconds() - wh0 * 3600) > 0:
                raise SystemExit("IDENTITY FAIL: anchor %s" % key)
            p0 = anchor_price(a_t, ends, closes)
            p1 = anchor_price(datetime.fromisoformat(t["exit_anchor"]),
                               ends, closes)
            rr = (d * (p1 / p0 - 1.0) - RT) * NOTIONAL / R_UNIT
            if abs(rr - t["r"]) > 1e-9:
                raise SystemExit("IDENTITY FAIL: r recompute %s" % key)
            ed = ev_t.date().isoformat()
            if t["event_d"] != ed:
                raise SystemExit("IDENTITY FAIL: era date %s" % key)
        eras = {}
        for era, (a0, b0) in ERAS.items():
            etr = [t for t in all_t if a0 <= t["event_d"] < b0]
            eras[era] = eval_era(etr, era, v18m)
        ok = all(not eras[e]["killed"] for e in ERAS)
        if ok:
            passed.append(key)
        res["arms"][key] = {"dir": d, "total_trades": len(all_t),
                            "eras": eras, "passes_both_eras": ok,
                            "first5": [{k2: t[k2] for k2 in
                                        ("event_d", "entry_anchor",
                                         "exit_anchor", "p0", "p1", "r")}
                                       for t in all_t[:5]]}
        line = " | ".join(
            "%s n=%d net=%+.1fR wr=%.0f%% sh=%.2f dd=%.1f %s"
            % (e.upper(), eras[e]["n"], eras[e]["net_r"],
               100 * eras[e]["wr"], eras[e]["sharpe_ann"],
               eras[e]["max_dd_R"],
               ("KILLED:" + ",".join(eras[e]["kill_list"]))
               if eras[e]["killed"] else "pass")
            for e in ERAS)
        print("[arm] %-24s %s -> %s" % (key, line,
              "PASS both" if ok else "FAIL"), flush=True)

    res["passing_arms"] = passed
    res["meta"]["build_s"] = round(time.time() - t0, 1)
    OUT.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print("PASSING ARMS:", passed if passed else "none", flush=True)
    print("JSON:", OUT, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
