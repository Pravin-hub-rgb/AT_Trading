"""EXP LA: Loss Autopsy + Winner Anatomy - deep trade-level analysis.

Hypothesis: The strategy edge comes from rare big runners (4R+) that pay for
many small losses. To improve, we must:
  1. Understand WHY losses happen (which patterns repeat?)
  2. Understand WHAT makes winners big (which conditions produce runners?)
  3. Find filterable loss patterns WITHOUT killing runners

Run:  python backtest/tests/exp_loss_autopsy.py
Output: stdout + _la_results.json
"""
import sys, time, json, bisect
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from test_experiments_craze import (build_module, BASE, load_candles,
    _compute_swings, SWING, MB15, INSTRUMENT, stats)
from engine.v18_params import get_v18_params as _gvp
from src.btc.btc_routes import _trade_costs, _load_fine_1m


def _net(tr, g):
    rs = [float(t["r_multiple"]) for t in tr]
    c2, _ = _trade_costs(tr, g["fee_pct"], 0.0, g["entry_slip_pct"], g["exit_slip_pct"])
    f = 0.0
    for t in tr:
        e, sl = float(t["entry_price"]), float(t["sl"])
        rk = abs(e - sl)
        if rk > 0 and e > 0:
            f += (int(t.get("bars_held") or 0) * 0.25 / 8.0) * 0.0001 * (e / rk)
    return sum(rs) - c2 - f


def compute_mfe(trade, candles_ltf, fine_ltf=None):
    entry_idx = trade["entry_idx"]
    exit_idx = trade.get("exit_idx")
    if exit_idx is None or exit_idx <= entry_idx:
        return abs(float(trade["r_multiple"]))
    direction = 1 if trade["dir"] == "long" else -1
    entry_px = float(trade["entry_price"])
    best = entry_px
    if fine_ltf:
        entry_ts = trade["entry_ts"]
        exit_ts = trade.get("exit_ts")
        if exit_ts is None:
            return abs(float(trade["r_multiple"]))
        for c in fine_ltf:
            ts = int(c["ts"])
            if ts <= entry_ts: continue
            if ts > exit_ts: break
            hi, lo = float(c["high"]), float(c["low"])
            if direction == 1 and hi > best: best = hi
            elif direction == -1 and lo < best: best = lo
    else:
        n = len(candles_ltf)
        for j in range(entry_idx + 1, min(exit_idx + 1, n)):
            c = candles_ltf[j]
            hi, lo = float(c["high"]), float(c["low"])
            if direction == 1 and hi > best: best = hi
            elif direction == -1 and lo < best: best = lo
    risk = abs(entry_px - float(trade["sl"]))
    if risk <= 0: return 0.0
    return round((best - entry_px) * direction / risk, 3)


def categorize(trades, candles_ltf, fine_ltf, intervals):
    iv_starts = [iv[0] for iv in intervals]
    for t in trades:
        r = float(t["r_multiple"])
        t["_r"] = r
        t["_is_win"] = r > 0
        t["_is_loss"] = r <= 0
        t["_abs_r"] = abs(r)
        t["_mfe"] = compute_mfe(t, candles_ltf, fine_ltf)
        t["_mfe_gb"] = t["_mfe"] - r if r > 0 else 0
        bars = t.get("bars_held", 0)
        t["_bars"] = bars
        t["_hours"] = round(bars * 0.25, 1)
        if bars <= 4: t["_speed"] = "instant"
        elif bars <= 12: t["_speed"] = "fast"
        elif bars <= 48: t["_speed"] = "medium"
        else: t["_speed"] = "slow"
        ts = t["entry_ts"]
        idx = bisect.bisect_right(iv_starts, ts) - 1
        if 0 <= idx < len(intervals):
            t["_wage_h"] = round((ts - intervals[idx][0]) / 3600.0, 1)
        else:
            t["_wage_h"] = None
        ds = t.get("entry_date", "")
        t["_year"] = ds[:4] if len(ds) >= 4 else "?"
        t["_hour"] = int(ds[11:13]) if len(ds) >= 13 else 0
    return trades


def pct(a, b): return round(100.0 * a / max(b, 1), 1)

def sec(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def main():
    t0 = time.time()
    (c15, f15), (c1h, f1h) = load_candles()
    sw15 = _compute_swings(f15, "continuous", min_bars=MB15)
    sw1h = _compute_swings(f1h, "continuous", min_bars=SWING["min_bars_1h"])
    fine = _load_fine_1m(min(c1h[0]["ts"], c15[0]["ts"]),
                         max(c1h[-1]["ts"], c15[-1]["ts"]), symbol=INSTRUMENT)
    sim = build_module()
    g = _gvp(INSTRUMENT)

    print("Running baseline with fine fills...")
    r = sim(c1h, sw1h, c15, sw15, fine_ltf=fine, **BASE)
    tr, ivs = r["ltf_trades"], r["intervals"]
    net = _net(tr, g)
    s = stats(tr)
    print(f"Baseline: {s['n']}t, gross {s['gross']:+.1f}R, NET {net:+.1f}R, "
          f"WR {s['wr']:.1f}%, DD {s['dd']:.1f}")

    tr = categorize(tr, c15, fine, ivs)
    W = [t for t in tr if t["_is_win"]]
    L = [t for t in tr if t["_is_loss"]]
    speed = [
        ("instant (0-4 bars)", lambda t: t["_bars"] <= 4),
        ("fast (5-12 bars)", lambda t: 5 <= t["_bars"] <= 12),
        ("medium (13-48 bars)", lambda t: 13 <= t["_bars"] <= 48),
        ("slow (49-192 bars)", lambda t: 49 <= t["_bars"] <= 192),
        ("very slow (>192 bars)", lambda t: t["_bars"] > 192),
    ]

    sec("1. OVERVIEW")
    print(f"  Trades: {len(tr)}  W: {len(W)} ({pct(len(W),len(tr))}%)  L: {len(L)} ({pct(len(L),len(tr))}%)")
    aw = sum(t["_r"] for t in W) / max(len(W), 1)
    al = sum(t["_r"] for t in L) / max(len(L), 1)
    am = sum(t["_mfe"] for t in W) / max(len(W), 1)
    ag = sum(t["_mfe_gb"] for t in W) / max(len(W), 1)
    print(f"  Avg winner: {aw:+.2f}R  Avg loser: {al:+.2f}R  Avg MFE(wins): {am:+.2f}R  Avg giveback: {ag:+.2f}R")

    sec("2. LOSS SIZE DISTRIBUTION")
    tl = sum(t["_r"] for t in L)
    lb = [
        ("<0.10R (sl exact)", lambda t: t["_abs_r"] < 0.10),
        ("0.10-0.25R", lambda t: 0.10 <= t["_abs_r"] < 0.25),
        ("0.25-0.50R", lambda t: 0.25 <= t["_abs_r"] < 0.50),
        ("0.50-0.75R", lambda t: 0.50 <= t["_abs_r"] < 0.75),
        ("0.75-1.00R", lambda t: 0.75 <= t["_abs_r"] < 1.00),
        (">=1.00R (slippage)", lambda t: t["_abs_r"] >= 1.00),
    ]
    print(f"  Total loss: {tl:.1f}R")
    for nm, fn in lb:
        bt = [t for t in L if fn(t)]
        br = sum(t["_r"] for t in bt)
        print(f"  {nm:25s} {len(bt):3d}t {pct(len(bt),len(L)):5.1f}% {br:+7.1f}R  ({pct(abs(br),abs(tl)):.1f}% of loss)")

    sec("3. SPEED OF DEATH (losses by time-to-SL)")
    for nm, fn in speed:
        bt = [t for t in L if fn(t)]
        br = sum(t["_r"] for t in bt)
        av = br / max(len(bt), 1)
        print(f"  {nm:35s} {len(bt):3d}t {pct(len(bt),len(L)):5.1f}% {br:+7.1f}R  avg {av:+.2f}R")

    sec("4. WINNER ANATOMY (time-to-exit)")
    for nm, fn in speed:
        bt = [t for t in W if fn(t)]
        br = sum(t["_r"] for t in bt)
        av = br / max(len(bt), 1)
        print(f"  {nm:35s} {len(bt):3d}t {pct(len(bt),len(W)):5.1f}% {br:+7.1f}R  avg {av:+.2f}R")

    sec("5. WINNER SIZE (where does the edge come from?)")
    gw = sum(t["_r"] for t in W)
    wb = [
        ("0.01-0.50R", lambda t: 0.01 <= t["_r"] <= 0.50),
        ("0.50-1.00R", lambda t: 0.50 < t["_r"] <= 1.00),
        ("1.00-2.00R", lambda t: 1.00 < t["_r"] <= 2.00),
        ("2.00-3.00R", lambda t: 2.00 < t["_r"] <= 3.00),
        ("3.00-5.00R", lambda t: 3.00 < t["_r"] <= 5.00),
        ("5.00-10.0R", lambda t: 5.00 < t["_r"] <= 10.0),
        (">10.0R (monsters)", lambda t: t["_r"] > 10.0),
    ]
    for nm, fn in wb:
        bt = [t for t in W if fn(t)]
        br = sum(t["_r"] for t in bt)
        print(f"  {nm:22s} {len(bt):3d}t {pct(len(bt),len(W)):5.1f}% {br:+7.1f}R  ({pct(br,gw):.1f}% of gross wins)")

    sec("6. MFE GIVEBACK (winners that gave back too much)")
    big_w = [t for t in W if t["_mfe"] >= 2.0]
    print(f"  Trades with MFE >= 2R: {len(big_w)}")
    gb = [
        ("gave back 0-25%", lambda t: t["_mfe_gb"] / max(t["_mfe"], 0.01) < 0.25),
        ("gave back 25-50%", lambda t: 0.25 <= t["_mfe_gb"] / max(t["_mfe"], 0.01) < 0.50),
        ("gave back 50-75%", lambda t: 0.50 <= t["_mfe_gb"] / max(t["_mfe"], 0.01) < 0.75),
        ("gave back >75%", lambda t: t["_mfe_gb"] / max(t["_mfe"], 0.01) >= 0.75),
    ]
    for nm, fn in gb:
        bt = [t for t in big_w if fn(t)]
        br = sum(t["_r"] for t in bt)
        mf = sum(t["_mfe"] for t in bt)
        print(f"  {nm:25s} {len(bt):3d}t  NET {br:+7.1f}R  MFE was {mf:+.1f}R  gave back {mf-br:.1f}R")

    sec("7. REGIME ANALYSIS (which HTF regime is best?)")
    regimes = defaultdict(list)
    for t in tr:
        regimes[t.get("htf_regime", "?")].append(t)
    for regime, rtr in sorted(regimes.items()):
        rw = [t for t in rtr if t["_is_win"]]
        gr = sum(t["_r"] for t in rtr)
        print(f"  {regime:12s}  {len(rtr):3d}t  W{len(rw):3d}  "
              f"WR {pct(len(rw),len(rtr)):5.1f}%  {gr:+7.1f}R  avg {gr/max(len(rtr),1):+.2f}R/t")

    sec("8. SIGNAL TYPE (break_kind) ANALYSIS")
    kinds = defaultdict(list)
    for t in tr:
        kinds[t.get("break_kind", "?")].append(t)
    for kind, ktr in sorted(kinds.items()):
        kw = [t for t in ktr if t["_is_win"]]
        gr = sum(t["_r"] for t in ktr)
        print(f"  {kind:8s}  {len(ktr):3d}t  W{len(kw):3d}  "
              f"WR {pct(len(kw),len(ktr)):5.1f}%  {gr:+7.1f}R  avg {gr/max(len(ktr),1):+.2f}R/t")

    sec("9. WINDOW AGE AT ENTRY (hypothesis: fresh windows are riskier)")
    ageb = [
        ("0-6h (fresh)", lambda t: t["_wage_h"] is not None and t["_wage_h"] <= 6),
        ("6-12h", lambda t: t["_wage_h"] is not None and 6 < t["_wage_h"] <= 12),
        ("12-24h", lambda t: t["_wage_h"] is not None and 12 < t["_wage_h"] <= 24),
        ("24-48h", lambda t: t["_wage_h"] is not None and 24 < t["_wage_h"] <= 48),
        ("48h+", lambda t: t["_wage_h"] is not None and t["_wage_h"] > 48),
    ]
    for nm, fn in ageb:
        bt = [t for t in tr if fn(t)]
        bw = [t for t in bt if t["_is_win"]]
        bl = [t for t in bt if t["_is_loss"]]
        gr = sum(t["_r"] for t in bt)
        print(f"  {nm:22s} {len(bt):3d}t  W{len(bw):3d}/L{len(bl):3d}  "
              f"WR {pct(len(bw),len(bt)):5.1f}%  {gr:+7.1f}R  avg {gr/max(len(bt),1):+.2f}R/t")

    sec("10. YEARLY BREAKDOWN")
    years = defaultdict(list)
    for t in tr:
        years[t["_year"]].append(t)
    for year in sorted(years.keys()):
        yr = years[year]
        yw = [t for t in yr if t["_is_win"]]
        gr = sum(t["_r"] for t in yr)
        big = [t for t in yr if t["_r"] >= 4.0]
        big_r = sum(t["_r"] for t in big)
        print(f"  {year}  {len(yr):3d}t  W{len(yw):3d}  "
              f"WR {pct(len(yw),len(yr)):5.1f}%  {gr:+7.1f}R  "
              f"big(>=4R): {len(big)}t {big_r:+.1f}R")

    sec("11. TOP 15 LOSSES (what went wrong?)")
    sl = sorted(L, key=lambda t: t["_r"])
    for t in sl[:15]:
        print(f"  #{t['trade_no']:3d}  {t['dir']:5s}  {t['htf_regime']:8s}  {t['break_kind']:6s}  "
              f"R={t['_r']:+6.2f}  bars={t['_bars']:3d}  "
              f"MFE={t['_mfe']:+.2f}  age={t['_wage_h']}h  "
              f"{t['entry_date']}")

    sec("12. TOP 15 WINNERS (what worked?)")
    sw = sorted(W, key=lambda t: t["_r"], reverse=True)
    for t in sw[:15]:
        print(f"  #{t['trade_no']:3d}  {t['dir']:5s}  {t['htf_regime']:8s}  {t['break_kind']:6s}  "
              f"R={t['_r']:+6.2f}  bars={t['_bars']:3d}  "
              f"MFE={t['_mfe']:+.2f}  gb={t['_mfe_gb']:.1f}  age={t['_wage_h']}h  "
              f"{t['entry_date']}")

    sec("13. FAST DEATH PATTERN (instant losses: 0-4 bars)")
    fast = [t for t in L if t["_bars"] <= 4]
    if fast:
        by_regime = defaultdict(list)
        for t in fast:
            by_regime[t.get("htf_regime", "?")].append(t)
        print(f"  {len(fast)} instant deaths ({pct(len(fast),len(L))}% of all losses)")
        for reg, rtr in sorted(by_regime.items()):
            print(f"    {reg}: {len(rtr)}t")
        fast_years = defaultdict(list)
        for t in fast:
            fast_years[t["_year"]].append(t)
        for yr in sorted(fast_years.keys()):
            print(f"    {yr}: {len(fast_years[yr])}t")

    sec("14. CROSS-DIMENSIONAL: Regime x Speed")
    for regime in sorted(regimes.keys()):
        rtr = regimes[regime]
        rl = [t for t in rtr if t["_is_loss"]]
        print(f"  {regime}:")
        for nm, fn in speed:
            bt = [t for t in rl if fn(t)]
            br = sum(t["_r"] for t in bt)
            print(f"    {nm:30s} {len(bt):3d}t {br:+7.1f}R")

    sec("15. KEY FINDINGS SUMMARY")
    instant_l = [t for t in L if t["_bars"] <= 4]
    slow_w = [t for t in W if t["_bars"] > 48]
    monsters = [t for t in W if t["_r"] > 5.0]
    mfe_3plus = [t for t in W if t["_mfe"] >= 3.0]
    gave_back_most = [t for t in mfe_3plus if t["_mfe_gb"] / max(t["_mfe"], 0.01) > 0.5]
    print(f"  1. Instant deaths (0-4 bars): {len(instant_l)} trades, {sum(t['_r'] for t in instant_l):+.1f}R")
    print(f"  2. Slow winners (>48 bars):   {len(slow_w)} trades, {sum(t['_r'] for t in slow_w):+.1f}R")
    print(f"  3. Monsters (>5R):            {len(monsters)} trades, {sum(t['_r'] for t in monsters):+.1f}R")
    print(f"  4. Trades with MFE>=3R:       {len(mfe_3plus)} trades, MFE total {sum(t['_mfe'] for t in mfe_3plus):+.1f}R")
    print(f"     -> gave back >50%:         {len(gave_back_most)} trades, gave back {sum(t['_mfe_gb'] for t in gave_back_most):+.1f}R")
    fresh = [t for t in L if t["_wage_h"] is not None and t["_wage_h"] <= 6]
    print(f"  5. Fresh window losses (<=6h): {len(fresh)} trades, {sum(t['_r'] for t in fresh):+.1f}R")

    # Save JSON
    out = {
        "baseline": {"n": len(tr), "gross": round(s["gross"], 1), "net": round(net, 1),
                      "wr": round(s["wr"], 1), "dd": round(s["dd"], 1)},
        "wins": {"n": len(W), "avg_r": round(aw, 3), "total_r": round(gw, 1),
                  "avg_mfe": round(am, 3), "avg_giveback": round(ag, 3)},
        "losses": {"n": len(L), "total_r": round(tl, 1), "avg_r": round(al, 3)},
        "fast_deaths": {"n": len(instant_l), "r": round(sum(t["_r"] for t in instant_l), 1)},
        "monsters": {"n": len(monsters), "r": round(sum(t["_r"] for t in monsters), 1)},
    }
    (ROOT / "backtest/tests/_la_results.json").write_text(json.dumps(out, indent=1))
    print(f"\n(la done %.0fs)" % (time.time() - t0))


if __name__ == "__main__":
    main()