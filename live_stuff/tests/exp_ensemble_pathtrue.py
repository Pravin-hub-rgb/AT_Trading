"""PARADIGM 5 - PORTFOLIO ENSEMBLE OF ALIVE KINGS (path-true decision).

THIS DOCSTRING IS THE BINDING PRE-REGISTRATION. Written BEFORE any run.

Origin: user-selected paradigm #5 of the "outside the v18 model" batch.
BACKGROUND (immutable): Stage G (exp_portfolio_book.py, CHECKLIST 24.46,
LOG 41) ran a DESCRIPTIVE combination study of 3 candidate-stack lanes and
concluded "no gate, no production change" - champion~utcsat were one
stream (corr 0.97), age10-cand genuinely independent, portfolio = an
absolute-return lever, not a risk-adjusted edge. This harness is the
missing DECISION phase with a different, binding membership: the FOUR
FLAT REFERENCE LANES (the alive kings as shipped), a pre-registered
correlation-membership rule, and a kill table whose decisive gate is
risk-adjusted dominance over the champion (the production anchor).

KINGS (fixed, all flat/default registry configs, priority order FIXED
A PRIORI - higher priority survives a collinearity drop):
  P1 champion -> champion_multi_sw10   (CHAMPION_BASE, house refs:
       IS 500t/+325.8R, OOS 279t/+70.2R)
  P2 utcsat   -> utcsat_multi_sw10     (KING_BASE, IS 454t/+358.9R,
       OOS 253t/+60.2R)
  P3 fullstack-> fullstack_wage10_cd0_single_sw10 (KING SINGLE,
       IS 200t/+310.7R, OOS 140t/+16.9R)
  P4 age10    -> age10_dirmatch_swingpause_single_sw10 (candidate,
       IS 130t/+435.7R, OOS 76t/+43.2R)
No stacks/flags - flat reference params only (the kings themselves).

SCOPES (as shipped; matches registry/v18 refs, NOT the house
[2023-07..) windows used by the data-side paradigms - lane results are
scoped to their data windows):
  IS  = data/bybit window, 2023-01..2026-09 (3.67y)
  OOS = unseen window,      2021-01..2022-12 (2.0y)

MEMBERSHIP (pre-registered, decided on IS only; OOS corrs reported but
never used for selection - OOS is the holdout):
  iterate priority P1..P4; keep a lane iff |corr_IS(daily exit-day NET R,
  kept)| <= 0.90 against EVERY already-kept lane. Threshold 0.90 fixed.
  If fewer than 2 lanes remain -> no ensemble exists -> verdict
  NO ENSEMBLE (reported, no arms).

ARMS (fixed, 2 total, both reported), k = number of retained lanes:
  scaled -> every trade's NET R multiplied by 1/k (risk ~= single lane;
            costs scale with size, so the NET scales exactly)
  full   -> every trade at full NET R (capital up to k concurrent R)
  baseline control = champion alone (full size), same eval path.

NET / ACCOUNTING: net per trade = run_experiment.net_r([t]) (gross
r_multiple minus fee/slip/funding at that lane's configured size);
scaled arm multiplies that NET by 1/k (economically exact - a smaller
book pays proportionally smaller costs). Trades merged and sorted by
entry_ts; DD/max-streak on trade order; monthly + quarterly buckets from
EXIT date (house convention).

KILL TABLE (per arm per era; PASS = zero kills BOTH eras):
  K1 net <= 0
  K2 any calendar quarter <= -15R (scaled) / <= -15*k R (full)
  K3 maxDD > 30R (scaled) / > 30*k R (full)   [capital ~ k, thresholds
       scale linearly with it - stated here so it is not post-hoc]
  K4 annualized monthly Sharpe < 0.5 (mean/sd*sqrt(12), zero-filled
       months from scope start 2023-01 / 2021-01 to last exit)
  K5 n < 100 (IS) / n < 60 (OOS)               [house, trade count]
  K6 win rate (net > 0) < 40%
  K7 (DECISIVE ENSEMBLE GATE, replaces the house corr-vs-v18 kill,
       which is N/A by construction: the ensemble INTENTIONALLY
       contains v18 - corr would kill every valid ensemble): ensemble
       Calmar (net / maxDD) must STRICTLY EXCEED the champion-alone
       Calmar in the SAME scope - kill if <= in either scope.

CONTROLS (abort before verdicts):
  - v18 champion control via exp_stat_arb.v18_control (house refs, both
    books; also runs the identity gate).
  - champion stream control: this harness's own champion run must match
    house refs within +/-1 trade / +/-1.0R both scopes (IS 500/+325.8,
    OOS 279/+70.2) or SystemExit.
  - lane runs: each king must produce > 0 trades in IS (empty lane ->
    SystemExit). Other lanes' docs numbers reported soft, not gated.
  - identity: first 5 trades of each arm recompute from member trades
    (net_r * w) within 1e-9; retained set obeys the 0.90 rule against
    every pairwise IS corr recorded.

RESEARCH_POLICY: both arms x both scopes reported; no best-of; no
auto-adopt. A PASS = "ensemble is a candidate for the user's adoption
decision", never an automatic production change.

Output: live_stuff/tests/_ensemble_pathtrue_results.json
Run: python -u live_stuff/tests/exp_ensemble_pathtrue.py
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
sys.path.insert(0, str(ROOT / "backend"))

from experiment_registry import BP, EXPERIMENTS  # noqa: E402
from run_experiment import net_r  # noqa: E402
from exp_stat_arb import v18_control  # noqa: E402
from stat_arb.correlation import month_key, quarter_key, month_range  # noqa: E402
from test_experiments_craze import build_module  # noqa: E402
import exp_portfolio_book as epb  # noqa: E402  (load_scope/run/daily_r/pearson)

OUT = ROOT / "live_stuff/tests/_ensemble_pathtrue_results.json"

LANES = (                          # a-priori priority order
    ("champion", "champion_multi_sw10"),
    ("utcsat", "utcsat_multi_sw10"),
    ("fullstack", "fullstack_wage10_cd0_single_sw10"),
    ("age10", "age10_dirmatch_swingpause_single_sw10"),
)
PRIORITY = [n for n, _ in LANES]
SCOPES = {"is": "2023-01", "oos": "2021-01"}
CORR_MAX = 0.90
KILL_MIN = {"is": 100, "oos": 60}
CHAMP_REF = {"is": (500, 325.8), "oos": (279, 70.2)}


def scope_series(trades: list[dict], w: float) -> list[dict]:
    out = []
    for t in sorted(trades, key=lambda x: int(x["entry_ts"])):
        out.append({"entry_ts": int(t["entry_ts"]),
                    "exit_d": str(t.get("exit_date") or "")[:10],
                    "net": net_r([t]) * w})
    return out


def calmar_of(ser: list[dict]) -> float:
    net = sum(s["net"] for s in ser)
    cum = peak = dd = 0.0
    for s in ser:
        cum += s["net"]
        peak = max(peak, cum)
        dd = max(dd, peak - cum)
    if dd <= 1e-9:
        return 999.0 if net > 0 else 0.0
    return net / dd


def eval_series(ser: list[dict], scope: str, k_full: int,
                full: bool, champ_calmar: float) -> dict:
    n = len(ser)
    nets = [s["net"] for s in ser]
    net = sum(nets)
    wr = (sum(1 for x in nets if x > 0) / n) if n else 0.0
    cum = peak = dd = 0.0
    for x in nets:
        cum += x
        peak = max(peak, cum)
        dd = max(dd, peak - cum)
    quarters: dict[str, float] = {}
    months: dict[str, float] = {}
    last = None
    for s in ser:
        ex = s["exit_d"]
        if not ex:
            continue
        qk, mk = quarter_key(pd.Timestamp(ex)), month_key(pd.Timestamp(ex))
        quarters[qk] = quarters.get(qk, 0.0) + s["net"]
        months[mk] = months.get(mk, 0.0) + s["net"]
        if last is None or ex > last:
            last = ex
    start = pd.Timestamp(SCOPES[scope] + "-01")
    ml = month_range(start, pd.Timestamp(last)) if last else month_range(start, start)
    vec = [months.get(m, 0.0) for m in ml]
    if len(vec) >= 2:
        mu = sum(vec) / len(vec)
        sd = math.sqrt(sum((x - mu) ** 2 for x in vec) / (len(vec) - 1))
        sharpe = (mu / sd) * math.sqrt(12.0) if sd > 1e-12 else 0.0
    else:
        sharpe = 0.0
    calmar = (net / dd) if dd > 1e-9 else (999.0 if net > 0 else 0.0)
    kk = k_full if full else 1
    kills = {
        "K1_net_nonpositive": net <= 0,
        "K2_quarter": any(v <= -15.0 * kk for v in quarters.values()),
        "K3_maxdd": dd > 30.0 * kk,
        "K4_sharpe_lt_0.5": sharpe < 0.5,
        "K5_min_trades": n < KILL_MIN[scope],
        "K6_wr_lt_40": wr < 0.40,
        "K7_calmar_not_above_champion": calmar <= champ_calmar,
    }
    return {"n": n, "net": round(net, 4), "wr": round(wr, 6),
            "max_dd": round(dd, 4), "calmar": round(calmar, 4),
            "sharpe_ann": round(sharpe, 4),
            "champ_calmar": round(champ_calmar, 4),
            "quarters": {a: round(b, 3) for a, b in sorted(quarters.items())},
            "monthly_r": {m: round(v, 3) for m, v in zip(ml, vec)},
            "kills": kills, "killed": any(kills.values()),
            "kill_list": sorted(a for a, b in kills.items() if b)}


def main() -> int:
    t0 = time.time()
    print("=" * 90, flush=True)
    print("  PARADIGM 5 - PORTFOLIO ENSEMBLE OF ALIVE KINGS (decision)", flush=True)
    print("=" * 90, flush=True)

    v18m: dict = {}
    control = v18_control(v18m)

    sim = build_module()
    raw: dict[str, dict[str, list[dict]]] = {}
    for scope in ("is", "oos"):
        data = epb.load_scope(scope)
        raw[scope] = {}
        for name, key in LANES:
            cfg = EXPERIMENTS[key]
            params = {**BP, **cfg["params"]}
            params.setdefault("exp_partial_r", 0.0)
            tr = epb.run(sim, data, params)
            if scope == "is" and not tr:
                raise SystemExit("CONTROL ABORT: empty lane %s" % name)
            raw[scope][name] = tr

    # champion house-ref control (hard)
    for scope in ("is", "oos"):
        n = len(raw[scope]["champion"])
        net = sum(net_r([t]) for t in raw[scope]["champion"])
        rn, rnet = CHAMP_REF[scope]
        print("[control] champion %s: %dt %+.1fR (ref %dt/%+.1fR)"
              % (scope, n, net, rn, rnet), flush=True)
        if abs(n - rn) > 1 or abs(net - rnet) > 1.0:
            raise SystemExit("CONTROL ABORT: champion %s %d/%.1f vs ref %d/%.1f"
                             % (scope, n, net, rn, rnet))

    # pairwise IS/OOS daily-R corr (exit-day NET R, full size - scale-free)
    dr = {s: {n: epb.daily_r(raw[s][n]) for n, _ in LANES}
          for s in ("is", "oos")}
    pairs = [(LANES[i][0], LANES[j][0])
             for i in range(len(LANES)) for j in range(i + 1, len(LANES))]
    corr_is = {f"{a}|{b}": epb.pearson(dr["is"][a], dr["is"][b])
               for a, b in pairs}
    corr_oos = {f"{a}|{b}": epb.pearson(dr["oos"][a], dr["oos"][b])
                for a, b in pairs}
    print("[corr IS ]", corr_is, flush=True)
    print("[corr OOS]", corr_oos, flush=True)

    # membership on IS, priority order
    kept: list[str] = []
    drops: dict[str, str] = {}
    for lane in PRIORITY:
        ok = True
        reason = ""
        for j in kept:
            c = corr_is.get(f"{lane}|{j}", corr_is.get(f"{j}|{lane}"))
            if c is None:
                c = 0.0
            if abs(c) > CORR_MAX:
                ok = False
                reason = "|corr| %.3f vs %s > %.2f" % (abs(c), j, CORR_MAX)
                break
        if ok:
            kept.append(lane)
        else:
            drops[lane] = reason
    print("[membership] kept=%s dropped=%s" % (kept, drops), flush=True)

    res = {"meta": {"hypothesis": "correlation-filtered ensemble of alive "
                    "kings beats the champion on risk-adjusted terms in "
                    "both scopes",
                    "priority": PRIORITY, "corr_max": CORR_MAX,
                    "arms": ["scaled", "full"],
                    "k5": "n>=100 IS / >=60 OOS (house)",
                    "k7": "calmar strictly above champion-alone in the "
                          "same scope (replaces corr-vs-v18: N/A by "
                          "construction)",
                    "build_s": round(time.time() - t0, 1)},
           "controls": {"v18_control": control,
                        "champ_ref": {s: {"n": len(raw[s]["champion"]),
                                          "net": round(sum(net_r([t]) for t
                                                           in raw[s]["champion"]), 1)}
                                      for s in ("is", "oos")},
                        "corr_is": corr_is, "corr_oos": corr_oos,
                        "membership_kept": kept, "membership_dropped": drops},
           "lane_stats": {}, "arms": {}}

    for scope in ("is", "oos"):
        res["lane_stats"][scope] = {
            n: {"n": len(raw[scope][n]),
                "net": round(sum(net_r([t]) for t in raw[scope][n]), 1)}
            for n, _ in LANES}

    if len(kept) < 2:
        res["verdict"] = "NO ENSEMBLE - membership rule retained <2 lanes"
        res["passing_arms"] = []
        OUT.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
        print("VERDICT:", res["verdict"], flush=True)
        print("JSON:", OUT, flush=True)
        return 0

    k = len(kept)
    champ_cal = {}
    for s in ("is", "oos"):
        champ_cal[s] = calmar_of(scope_series(raw[s]["champion"], 1.0))
        print("[champion] %s calmar=%.3f" % (s, champ_cal[s]), flush=True)

    passed = []
    for mode in ("scaled", "full"):
        w = (1.0 / k) if mode == "scaled" else 1.0
        arm = {"members": kept, "weight": w, "eras": {}}
        for scope in ("is", "oos"):
            ser = scope_series([t for n in kept for t in raw[scope][n]], w)
            arm["eras"][scope] = eval_series(ser, scope, k, mode == "full",
                                             champ_cal[scope])
            if scope == "is":
                # identity: first 5 nets recompute from merged member trades
                iso = sorted((t for n in kept for t in raw["is"][n]),
                             key=lambda x: int(x["entry_ts"]))
                if len(iso) < 5:
                    raise SystemExit("IDENTITY FAIL: fewer than 5 trades")
                for i in range(5):
                    expect = net_r([iso[i]]) * w
                    if abs(expect - ser[i]["net"]) > 1e-9:
                        raise SystemExit("IDENTITY FAIL: arm net recompute")
                arm["first5"] = [{"exit_d": s["exit_d"],
                                  "net": round(s["net"], 9)} for s in ser[:5]]
        ok = all(not arm["eras"][s]["killed"] for s in ("is", "oos"))
        if ok:
            passed.append(mode)
        res["arms"][mode] = arm
        line = " | ".join(
            "%s n=%d net=%+.1fR dd=%.1f cal=%.2f sh=%.2f %s"
            % (s.upper(), arm["eras"][s]["n"], arm["eras"][s]["net"],
               arm["eras"][s]["max_dd"], arm["eras"][s]["calmar"],
               arm["eras"][s]["sharpe_ann"],
               ("KILLED:" + ",".join(arm["eras"][s]["kill_list"]))
               if arm["eras"][s]["killed"] else "pass")
            for s in ("is", "oos"))
        print("[arm] %-7s %s -> %s" % (mode, line,
              "PASS both" if ok else "FAIL"), flush=True)

    res["passing_arms"] = passed
    res["verdict"] = ("ENSEMBLE CANDIDATE - passes kill table (user "
                      "adoption decision required)" if passed
                      else "NO NEW EDGE - ensemble fails kill table")
    res["meta"]["build_s"] = round(time.time() - t0, 1)
    OUT.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print("VERDICT:", res["verdict"], flush=True)
    print("PASSING ARMS:", passed if passed else "none", flush=True)
    print("JSON:", OUT, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
