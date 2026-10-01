"""Statistical Arbitrage (Paradigm B) - pre-registered BTC/ETH(-SOL) spread book.

THIS DOCSTRING IS THE BINDING PRE-REGISTRATION (experiment_registry entry
intentionally NOT used - plan fix 6). Written before the first run. No
post-hoc arm additions, threshold changes, or best-of selection.

GOAL: an independent, market-neutral return stream uncorrelated with the
v18 champion (corr kill if it just shadows the engine book).

DATA (on disk only, no fetching): data/btc-fut/BTCUSDT_15m.csv,
data/eth-fut/ETHUSDT_15m.csv, data/scan-fut/SOLUSDT_15m.csv (SOL starts
2023-01-01 05:30 local). CSV timestamps are UTC+5:30 (IST) wall-clock
strings on all three files; every window/bucket below is that local clock.
BTC-ETH inner join for OLS arms; BTC-ETH-SOL join for PCA arms. Identity:
join coverage >= 99.5% per pair, grid gaps <= 1% of rows, monotonic.

ERAS (house convention; Kilo 6-month initial train, quarter math corrected):
  OOS era  [2021-01-01 05:30, 2023-01-01 05:30) local
           results window [2021-07-01 05:30, 2023-01-01 05:30) = 6 quarters
  IS  era  [2023-01-01 05:30, 2026-09-14 05:30) local
           results window [2023-07-01 05:30, 2026-09-14 05:30) = 13 quarters
Era membership of a stat trade = entry FILL inside that era's results window.
Stats bucket by EXIT month/quarter in the local calendar; spill beyond the
window kept (<= 1 month, given max hold 168 bars); zero months in the
start-month..max-exit-month range are included (Sharpe, corr).

ARMS (4 hedges x 6 bands = 24; ALL reported, no best-of; primary A1xB1):
  A1 rolling OLS on log prices, window 288, h = (1, -beta)   [PRIMARY hedge]
  A2 rolling OLS, window 576
  A4 PCA PC1 on 3-asset log prices, window 288, entry gate explained >= 70%
  A5 PCA, window 576
  A3 Kalman DEFERRED (Q/R never specified - plan fix).
  A4/A5 need SOL (2023+) -> can only ever fill in the IS era; such arms are
  judged on the IS kill table only and marked NON-ADOPTABLE (era-incomplete,
  construction robustness only).
  z = (S - rolling mean) / rolling std over the hedge window, ddof=0;
  OU half-life window fixed 288 bars; entry gate half-life in [24, 288]
  bars (6h..72h), checked at entry only; PCA entry gate: BTC loading
  h0 >= 0.10 (construction guard; h sign-fixed positive).
  Bands (entry |z| / exit z level / stop |z|; max hold 168 bars for all):
    B1 2.0/0.5/3.5 (PRIMARY band)   B2 2.0/0.0/3.5   B3 2.5/0.5/4.0
    B4 2.5/0.0/4.0                  B5 1.5/0.5/3.0   B6 1.5/0.0/3.0
  z > +entry -> SHORT spread (short BTC, long hedge legs); z < -entry -> LONG.
  Target is dir-aware: dir=+1 exits when z >= -exit_z, dir=-1 when z <= +exit_z
  (so exit_z=0 means "revert through zero"). Stop before target on the same bar.
  Cooldown: entry fill must be > 24 bars after the previous exit fill.
  One position max, no overlap, no same-bar flip.

CONSTRUCTION NOTE (v2, written before the reported run): the OLS spread is
the regression residual S = (lb - mean_lb) - beta * (le - mean_le) over the
same window (OLS intercept included; same window-demeaning as the PCA arms).
A first diagnostic run used raw lb - beta*le: the wandering OLS intercept
inflated window sigma (p50 1.07 log units vs ~0.03 for a hedge residual),
which blew up risk$ ~20x and decoupled z from leg P&L (all R magnitudes
~100x too small). Caught by scale sanity, NOT by any result's direction;
arms/bands/gates/kill table/control refs unchanged. Entry sigma <= 0.5 is
now a structural identity assertion.

EXECUTION / CAUSALITY: decisions on closed 15m bars only; fills at the NEXT
bar close (both legs, log closes); rolling windows use [t-w+1, t] only.
Trades censored at data end (last bar, reason eod).

COSTS (Binance perp, fixed): taker 0.04%/side + 0.5 bps entry slip +
1.0 bps exit slip => round trip 0.095% of combined leg notional. Funding
FLAT 0.01%/8h per leg notional (longs pay, shorts receive), accrued per 15m
bar as 3.125e-6 of signed leg dollars (no funding data on disk - plan fix).
Sizing: BTC leg fixed $10,000; hedge legs $10k * h_i / h_0 (h_0 > 0).
Leverage NOT modelled (fixed notional, no liquidation path) - caveat.

1R (fixed): risk$ = (10000 / h0_entry) * sigma_entry * (stop_z - entry_z_param);
R = (leg P&L - costs + funding cashflow) / risk$.

KILL TABLE (stated first; evaluated per arm per evaluated era; PASS =
survives every evaluated era; primary A1xB1 is the headline verdict):
  K1 net R <= 0 over the era
  K2 any calendar quarter net R <= -15
  K3 max drawdown (cumulative R in exit order) > 30R
  K4 annualized Sharpe of the monthly R series < 0.5 (mean/sd * sqrt(12),
     sd = sample sd, zero-filled months included)
  K5 trades < 100 (IS era) / < 60 (OOS era) - Kilo's 100-over-3.7y scaled
     to each era's results window length
  K6 win rate < 40% (fraction of R > 0)
  K7 Pearson corr of monthly R vs the v18 champion's monthly gross R
     (sum r_multiple by exit month, same local calendar, IS+OOS v18 books
     combined, zero-filled over the era month range) > 0.3 kills.

CONTROLS (abort before any verdict on mismatch):
  - engine identity gate (shipped vs patched-off, coarse+chop61.8).
  - champion_multi_sw10 BOTH house books run once (fine basis): IS book =
    get_data() (load_candles range) via run_one; OOS book = bybit unseen
    2021-22 file via load_unseen + load_fine_1m + sw10/sw15 swings (the
    exp_sizing_combo/exp_equity_quality load_scope convention). Refs are
    NET (r_multiple - engine costs - funding, net_r): IS 500t/+325.8R,
    OOS 279t/+70.2R, each within +/-2 trades, +/-1.0R, else SystemExit
    BEFORE any stat-arm result is computed or printed. The v18 monthly
    series used for K7 is the GROSS sum of r_multiple by exit month over
    BOTH books combined (pre-registered quantity).
  - join coverage >= 99.5%, gap rows <= 1%.
IDENTITY (stat arms, structural, asserted after the run): every entry fill
inside its era results window; cooldown > 24 bars and no overlap; bars_held
in [0, 168]; first 5 trades per arm: stored logs re-derived from raw frame
closes, R recomputed independently from hardcoded constants (tol 1e-9), and
z at the signal bar recomputed O(w) from the raw spread (tol 1e-9) with
|z| >= entry_z and half-life/PC1 gates true at that bar.

RESEARCH_POLICY: report ALL 24 arms x eras x quarters; no best-of; no
automatic adoption; forward gate (n >= 50 paper spread trades) applies to
any future deployment; no engine flags produced (standalone book); kill
fallback E (CVD fetch) NOT executed - no data fetching in this lane.

Output: backtest/tests/_stat_arb_results.json
Run: python -u backtest/tests/exp_stat_arb.py
"""
from __future__ import annotations

import json
import math
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from stat_arb.loader import load_frames, ERAS  # noqa: E402
from stat_arb.hedge import rolling_pca, ols_residual  # noqa: E402
from stat_arb.ou import half_life  # noqa: E402
from stat_arb.signals import rolling_z, hl_gate, run_backtest  # noqa: E402
from stat_arb.costs import trade_r  # noqa: E402
from stat_arb.correlation import month_key, quarter_key, month_range, pearson  # noqa: E402
import run_experiment as rex  # noqa: E402

HEDGES = {
    "A1": ("ols", 288),
    "A2": ("ols", 576),
    "A4": ("pca", 288),
    "A5": ("pca", 576),
}
BANDS = {
    "B1": (2.0, 0.5, 3.5),
    "B2": (2.0, 0.0, 3.5),
    "B3": (2.5, 0.5, 4.0),
    "B4": (2.5, 0.0, 4.0),
    "B5": (1.5, 0.5, 3.0),
    "B6": (1.5, 0.0, 3.0),
}
PRIMARY = "A1xB1"
KILL_MIN = {"is": 100, "oos": 60}
V18_REFS = {"is": (500, 325.8), "oos": (279, 70.2)}
V18_KEY = "champion_multi_sw10"
OUT_PATH = Path(__file__).resolve().parent / "_stat_arb_results.json"

WINDOWS = [
    (ERAS["oos"]["results"], ERAS["oos"]["end"], "oos"),
    (ERAS["is"]["results"], ERAS["is"]["end"], "is"),
]


def _log(xs):
    return [math.log(v) for v in xs]


def build_series(kind, w, fr):
    """z/sd/hl/gates + spread/logs/closes for one hedge construction."""
    t0 = time.time()
    ts = fr["ts"]
    lb, le = _log(fr["btc"]), _log(fr["eth"])
    if kind == "ols":
        beta, spread = ols_residual(lb, le, w)
        hvecs = [(1.0, -b) if b == b else None for b in beta]
        pc_ok = [True] * len(ts)
        logs = (lb, le)
        closes = (fr["btc"], fr["eth"])
    else:
        pos = {t: i for i, t in enumerate(fr["ts"])}
        idx = [pos[t] for t in fr["ts3"]]
        ts = fr["ts3"]
        lb3, le3 = [lb[i] for i in idx], [le[i] for i in idx]
        ls = _log(fr["sol3"])
        hvecs, spread, explained = rolling_pca((lb3, le3, ls), w)
        hvecs = [h if h == h else None for h in hvecs]
        pc_ok = [(e == e and e >= 0.70) for e in explained]
        logs = (lb3, le3, ls)
        closes = ([fr["btc"][i] for i in idx], [fr["eth"][i] for i in idx],
                  fr["sol3"])
    z, sd = rolling_z(spread, w)
    hl_ok = hl_gate(half_life(spread))
    print("[series] %s w=%d bars=%d (%.1fs)" % (kind, w, len(ts), time.time() - t0), flush=True)
    return {"ts": ts, "z": z, "sd": sd, "hl_ok": hl_ok, "pc_ok": pc_ok,
            "hvecs": hvecs, "spread": spread, "logs": logs, "closes": closes}


def postprocess(trs, ser):
    ts, logs = ser["ts"], ser["logs"]
    for t in trs:
        xb = t["exit_bar"]
        t["log_exit"] = [lg[xb] for lg in logs]
        t["bars_held"] = xb - t["entry_bar"]
        t["entry_dt"] = ts[t["entry_bar"]]
        t["exit_dt"] = ts[xb]
        t.update(trade_r(t["h"], t["dir"], t["log_entry"], t["log_exit"],
                         t["sigma"], t["entry_z_param"], t["stop_z"], t["bars_held"]))
        t["month"] = month_key(t["exit_dt"])
        t["quarter"] = quarter_key(t["exit_dt"])
    return trs


def identity_checks(trs, ser, band, tag):
    entry_z = band[0]
    errs = []
    last_exit = -(10 ** 9)
    for i, t in enumerate(trs):
        if not (ERAS[t["era"]]["results"] <= t["entry_dt"] < ERAS[t["era"]]["end"]):
            errs.append("%s t%d entry outside results window" % (tag, i))
        if t["entry_bar"] - last_exit <= 24:
            errs.append("%s t%d cooldown %d <= 24" % (tag, i, t["entry_bar"] - last_exit))
        if not (0 <= t["bars_held"] <= 168):
            errs.append("%s t%d bars_held %d" % (tag, i, t["bars_held"]))
        if t["exit_bar"] < t["entry_bar"]:
            errs.append("%s t%d negative hold" % (tag, i))
        if not (t["sigma"] == t["sigma"] and t["sigma"] <= 0.5):
            errs.append("%s t%d entry sigma %.4f outside scale sanity (<=0.5)"
                        % (tag, i, t["sigma"]))
        last_exit = t["exit_bar"]
        if i < 5:
            h = t["h"]
            scale = 10000.0 / h[0]
            legs = [t["dir"] * scale * hi for hi in h]
            gross = sum(n * (x1 - x0) for n, x0, x1 in zip(legs, t["log_entry"], t["log_exit"]))
            cost = 0.00095 * sum(abs(n) for n in legs)
            funding = -3.125e-6 * sum(legs) * t["bars_held"]
            risk = scale * t["sigma"] * (t["stop_z"] - t["entry_z_param"])
            r_ind = (gross - cost + funding) / risk
            if abs(r_ind - t["r"]) > 1e-9:
                errs.append("%s t%d R mismatch %.12f vs %.12f" % (tag, i, r_ind, t["r"]))
            raw_entry = [math.log(c[t["entry_bar"]]) for c in ser["closes"]]
            raw_exit = [math.log(c[t["exit_bar"]]) for c in ser["closes"]]
            if (any(abs(a - b) > 1e-12 for a, b in zip(t["log_entry"], raw_entry))
                    or any(abs(a - b) > 1e-12 for a, b in zip(t["log_exit"], raw_exit))):
                errs.append("%s t%d raw close log mismatch" % (tag, i))
            sg = t["signal_bar"]
            ww = t["_w"]
            sp = ser["spread"]
            if sg < ww - 1:
                errs.append("%s t%d signal bar before warmup" % (tag, i))
                continue
            win = sp[sg - ww + 1:sg + 1]
            m = sum(win) / ww
            var = sum((v - m) ** 2 for v in win) / ww
            sd_d = math.sqrt(var) if var > 0 else 0.0
            z_d = (sp[sg] - m) / sd_d if sd_d > 1e-12 else float("nan")
            if abs(z_d - t["z_actual"]) > 1e-9:
                errs.append("%s t%d z recompute %.12f vs %.12f" % (tag, i, z_d, t["z_actual"]))
            if not (abs(t["z_actual"]) >= entry_z and ser["hl_ok"][sg] and ser["pc_ok"][sg]):
                errs.append("%s t%d gate/|z| violated at signal bar" % (tag, i))
    return errs


def eval_era(trs, era, v18m):
    n = len(trs)
    rs = [t["r"] for t in trs]
    net = sum(rs)
    win = sum(1 for r in rs if r > 0)
    wr = win / n if n else 0.0
    cum = 0.0
    peak = 0.0
    dd = 0.0
    for r in rs:
        cum += r
        peak = max(peak, cum)
        dd = max(dd, peak - cum)
    quarters = {}
    months = {}
    last_exit = None
    gR = cR = fR = 0.0
    for t in trs:
        quarters[t["quarter"]] = quarters.get(t["quarter"], 0.0) + t["r"]
        months[t["month"]] = months.get(t["month"], 0.0) + t["r"]
        if t["risk"] > 1e-12:
            gR += t["gross"] / t["risk"]
            cR += t["cost"] / t["risk"]
            fR += t["funding"] / t["risk"]
        if last_exit is None or t["exit_dt"] > last_exit:
            last_exit = t["exit_dt"]
    if last_exit is None:
        ml = month_range(ERAS[era]["results"], ERAS[era]["results"])
    else:
        ml = month_range(ERAS[era]["results"], last_exit)
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
    killed = any(kills.values())
    return {
        "n": n, "net_r": round(net, 4),
        "gross_R": round(gR, 3), "cost_R": round(cR, 3), "funding_R": round(fR, 3),
        "wr": round(wr, 6),
        "sharpe_ann": round(sharpe, 4), "max_dd_R": round(dd, 4),
        "quarters": {k: round(v, 3) for k, v in sorted(quarters.items())},
        "monthly_r": {m: round(v, 3) for m, v in zip(ml, vec)},
        "corr_v18_monthly": None if corr is None else round(corr, 4),
        "kills": kills, "killed": killed,
        "kill_list": sorted(k for k, v in kills.items() if v),
        "months": ml,
    }


def v18_control(v18m):
    from test_4_new_concepts import load_unseen, load_fine_1m

    data = rex.get_data()
    sim = rex.build_module()
    rex.identity_gate(data, sim)
    t0 = time.time()
    tr_is, _ = rex.run_one(V18_KEY, data, sim)
    (c15, f15), (c1h, f1h) = load_unseen("15m"), load_unseen("1h")
    sw15 = rex._compute_swings(f15, "continuous", min_bars=rex.SWING["min_bars_15m"])
    sw10 = rex._compute_swings(f1h, "continuous", min_bars=10)
    oos_data = {"c15": c15, "c1h": c1h, "sw15": sw15, "sw10": sw10,
                "fine": load_fine_1m(c15[0]["ts"], c15[-1]["ts"])}
    tr_oos, _ = rex.run_one(V18_KEY, oos_data, sim)
    print("[control] %s ran both books %.0fs (is=%do oos=%dn)"
          % (V18_KEY, time.time() - t0, len(tr_is), len(tr_oos)), flush=True)
    out = {"key": V18_KEY}
    for era, book in (("is", tr_is), ("oos", tr_oos)):
        n = len(book)
        net = rex.net_r(book)
        rn, rg = V18_REFS[era]
        out[era] = {"n": n, "net": round(net, 4), "ref_n": rn, "ref_net": rg,
                    "gross": round(sum(float(t["r_multiple"]) for t in book), 4)}
        if abs(n - rn) > 2 or abs(net - rg) > 1.0:
            raise SystemExit(
                "CONTROL ABORT: %s %s book %dt/%+.1fR(net) vs ref %dt/%+.1fR "
                "(tol +/-2t, +/-1.0R) - stat results not computed"
                % (V18_KEY, era.upper(), n, net, rn, rg)
            )
        print("[control] %s %s OK: %dt / %+.1fR net (ref %dt/%+.1fR)"
              % (V18_KEY, era.upper(), n, net, rn, rg), flush=True)
        for t in book:
            ex = str(t.get("exit_date") or t.get("entry_date") or "")[:7]
            v18m[ex] = v18m.get(ex, 0.0) + float(t["r_multiple"])
    return out


def _san(o):
    if isinstance(o, float):
        if o != o or o in (float("inf"), float("-inf")):
            return None
        return o
    if isinstance(o, dict):
        return {k: _san(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_san(v) for v in o]
    if isinstance(o, tuple):
        return [_san(v) for v in o]
    return o


def main():
    t_start = time.time()
    fr = load_frames(ROOT)
    ck = fr["checks"]
    print("[loader] %s" % ck, flush=True)
    if ck["coverage2"] < 0.995 or ck["gaps2"] > 0.01 * ck["n_join2"] or not ck["monotonic2"]:
        raise SystemExit("IDENTITY ABORT: btc-eth join coverage/gaps/monotonic failed")
    if ck["n_join3"] == 0 or ck["coverage3"] < 0.995 or ck["gaps3"] > 0.01 * ck["n_join3"]:
        raise SystemExit("IDENTITY ABORT: btc-eth-sol join coverage/gaps failed")

    v18m = {}
    control = v18_control(v18m)

    series = {}
    for hk, (kind, w) in HEDGES.items():
        series[hk] = build_series(kind, w, fr)

    arms = {}
    errs_all = []
    for hk, (kind, w) in HEDGES.items():
        ser = series[hk]
        adoptable = kind == "ols"
        for bk, band in BANDS.items():
            aid = "%sx%s" % (hk, bk)
            t0 = time.time()
            raw = run_backtest(ser["ts"], ser["logs"], ser["z"], ser["sd"],
                               ser["hvecs"], ser["hl_ok"], ser["pc_ok"],
                               band, WINDOWS)
            trs = postprocess(raw, ser)
            for t in trs:
                t["_w"] = w
            errs = identity_checks(trs, ser, band, aid)
            errs_all.extend(errs)
            eras = {}
            for era in ("is", "oos"):
                et = [t for t in trs if t["era"] == era]
                if not adoptable and era == "oos":
                    eras[era] = {"skipped": "PCA needs SOL (2023+); IS-ERA ONLY, NON-ADOPTABLE"}
                    continue
                eras[era] = eval_era(et, era, v18m)
            if not adoptable:
                verdict = "PASS-IS-ONLY-NONADOPT" if not eras["is"]["killed"] else "FAIL"
            else:
                verdict = "PASS" if (not eras["is"]["killed"]
                                     and not eras["oos"]["killed"]) else "FAIL"
            arms[aid] = {
                "hedge": hk, "kind": kind, "window": w, "band": bk,
                "band_values": list(band), "adoptable": adoptable,
                "eras": eras, "verdict": verdict,
                "elapsed_s": round(time.time() - t0, 1),
            }
            if aid == PRIMARY:
                arms[aid]["trades"] = [
                    {"entry": str(t["entry_dt"]), "exit": str(t["exit_dt"]),
                     "era": t["era"], "dir": t["dir"], "reason": t["exit_reason"],
                     "bars": t["bars_held"], "r": round(t["r"], 4),
                     "gross": round(t["gross"], 3), "cost": round(t["cost"], 3),
                     "funding": round(t["funding"], 3), "risk": round(t["risk"], 2),
                     "sigma": round(t["sigma"], 5)}
                    for t in trs
                ]
            ik = eras["is"]
            ok_i = "%s IS: %dt %+.1fR wr%.0f%% sh%.2f dd%.1f corr%s %s" % (
                aid, ik["n"], ik["net_r"], 100 * ik["wr"], ik["sharpe_ann"],
                ik["max_dd_R"], ik["corr_v18_monthly"],
                "KILL" if ik["killed"] else "pass")
            if "skipped" in eras["oos"]:
                ok_o = "OOS skipped"
            else:
                ok_o = "OOS: %dt %+.1fR wr%.0f%% sh%.2f dd%.1f corr%s %s" % (
                    eras["oos"]["n"], eras["oos"]["net_r"], 100 * eras["oos"]["wr"],
                    eras["oos"]["sharpe_ann"], eras["oos"]["max_dd_R"],
                    eras["oos"]["corr_v18_monthly"],
                    "KILL" if eras["oos"]["killed"] else "pass")
            print("%s | %s -> %s (%.0fs)" % (ok_i, ok_o, verdict,
                                             arms[aid]["elapsed_s"]), flush=True)

    if errs_all:
        for e in errs_all[:20]:
            print("[identity FAIL] %s" % e, flush=True)
        raise SystemExit("IDENTITY ABORT: %d stat-arm structural failures" % len(errs_all))
    print("[identity] all structural checks passed (%d arms)" % len(arms), flush=True)

    grid = {
        "pass_both_ols": sorted(a for a, v in arms.items()
                                if v["adoptable"] and v["verdict"] == "PASS"),
        "pass_is_pca": sorted(a for a, v in arms.items()
                              if not v["adoptable"] and v["verdict"] == "PASS-IS-ONLY-NONADOPT"),
        "fail": sorted(a for a, v in arms.items() if v["verdict"] == "FAIL"),
        "primary": PRIMARY,
        "primary_verdict": arms[PRIMARY]["verdict"],
    }
    result = {
        "meta": {
            "file": "exp_stat_arb.py",
            "pre_registration": "binding docstring of this file (no registry entry)",
            "generated": str(datetime.now()),
            "elapsed_s": round(time.time() - t_start, 1),
            "hedges": {k: list(v) for k, v in HEDGES.items()},
            "bands": {k: list(v) for k, v in BANDS.items()},
            "kill_min": KILL_MIN, "v18_refs": {k: list(v) for k, v in V18_REFS.items()},
            "costs": {"fee": 0.0004, "slip_entry": 0.00005, "slip_exit": 0.0001,
                      "funding_8h": 0.0001, "round_trip_pct": 0.00095,
                      "fund_bar_dollars": 3.125e-6},
            "max_hold": 168, "cooldown": 24,
            "eras": {k: {"start": str(v["start"]), "results": str(v["results"]),
                         "end": str(v["end"])} for k, v in ERAS.items()},
        },
        "loader_checks": ck,
        "v18_control": control,
        "arms": arms,
        "grid": grid,
    }
    OUT_PATH.write_text(json.dumps(_san(result), indent=1), encoding="utf-8")
    print("[done] %d arms, primary %s -> %s, json=%s (%.0fs total)"
          % (len(arms), PRIMARY, grid["primary_verdict"], OUT_PATH.name,
             time.time() - t_start), flush=True)
    print("grid: pass_both(ols)=%d pass_is(pca)=%d fail=%d"
          % (len(grid["pass_both_ols"]), len(grid["pass_is_pca"]), len(grid["fail"])),
          flush=True)


if __name__ == "__main__":
    main()
