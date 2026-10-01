"""Param sweep on the C14+C15 causal engine.

Sweeps one variable at a time, holding others at current best.
Reports trades, gross R, WR, PF, and per-year breakdown.
"""
import sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from src.btc.btc_config import load_btc_df
from src.btc.btc_routes import _compute_swings, _load_fine_1m
from src.btc.engines.htf_ltf.v18_streak_halt import simulate_htf_ltf_streak_halt
from src.walker import FlowCandle

SYMBOL = "BTCUSDT_BYBIT"
BASE = {"sl_buf_atr": 0.01, "chop_thresh": 58.0, "cooldown_bars": 10,
        "max_consecutive_losses": 3, "ext_stop_r": 1.5}

def load_window(tf):
    df = load_btc_df(tf, SYMBOL)
    candles, flow = [], []
    for row in df.itertuples():
        date = row.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        candles.append({"date": date, "ts": int(row.ts), "open": float(row.open),
                        "high": float(row.high), "low": float(row.low), "close": float(row.close),
                        "volume": 0, "oi": 0})
        flow.append(FlowCandle(date=date, open=float(row.open), high=float(row.high),
                               low=float(row.low), close=float(row.close)))
    return candles, flow

def run_engine(c1h, sw1h, c15, sw15, fine, params):
    tr = simulate_htf_ltf_streak_halt(
        c1h, sw1h, c15, sw15, fine_ltf=fine,
        sl_buf_atr=params["sl_buf_atr"], ext_stop_r=params["ext_stop_r"],
        mode="b2_vs_flip_chop",
        chop_thresh=params["chop_thresh"],
        cooldown_bars=params["cooldown_bars"],
        max_consecutive_losses=params["max_consecutive_losses"])["ltf_trades"]
    rs = [t["r_multiple"] for t in tr]
    n = len(rs)
    tot = sum(rs)
    wins = [r for r in rs if r > 0]
    losses = [r for r in rs if r <= 0]
    wr = 100 * len(wins) / n if n else 0
    pf = sum(wins) / abs(sum(losses)) if losses else float("inf")
    years = {}
    for t in tr:
        y = t["entry_date"][:4]
        years.setdefault(y, [0, 0.0])
        years[y][0] += 1
        years[y][1] += t["r_multiple"]
    allyes = all(v[1] > 0 for v in years.values())
    return n, tot, wr, pf, years, allyes

def fmt_row(label, n, tot, wr, pf, years, allyes):
    yr_str = "  ".join(f"{y}:{v[1]:+.0f}R" for y, v in sorted(years.items()))
    flag = "OK" if allyes else "NEG"
    return f"  {label:12s}  {n:4d}t  {tot:+8.1f}R  WR {wr:5.1f}%  PF {pf:5.2f}  [{yr_str}]  {flag}"

def main():
    c1h, f1h = load_window("1h")
    c15, f15 = load_window("15m")
    sw1h = _compute_swings(f1h, "continuous", min_bars=20)
    sw15 = _compute_swings(f15, "continuous", min_bars=50)
    t0 = min(c1h[0]["ts"], c15[0]["ts"])
    t1 = max(c1h[-1]["ts"], c15[-1]["ts"])
    fine = _load_fine_1m(t0, t1, symbol=SYMBOL)

    print("=" * 100)
    print("V18 CAUSAL ENGINE SWEEP  (C14+C15 active)")
    print("=" * 100)
    print(f"  Baseline: {BASE}")
    print()

    # Baseline
    t0b = time.time()
    n, tot, wr, pf, years, allyes = run_engine(c1h, sw1h, c15, sw15, fine, BASE)
    dt = time.time() - t0b
    print(fmt_row("BASELINE", n, tot, wr, pf, years, allyes))
    print(f"  ({dt:.1f}s)")
    print()

    # --- SWEEP 1: sl_buf_atr ---
    print("-" * 100)
    print("  SWEEP 1: sl_buf_atr")
    print("-" * 100)
    best_slbuf = (tot, BASE["sl_buf_atr"])
    for v in [0.001, 0.005, 0.01, 0.02, 0.05, 0.10, 0.15, 0.25]:
        p = {**BASE, "sl_buf_atr": v}
        n, tot, wr, pf, years, allyes = run_engine(c1h, sw1h, c15, sw15, fine, p)
        marker = " <-- BEST" if tot > best_slbuf[0] else ""
        if tot > best_slbuf[0]:
            best_slbuf = (tot, v)
        print(fmt_row(f"sl={v}", n, tot, wr, pf, years, allyes) + marker)
    print(f"  >>> Best sl_buf_atr = {best_slbuf[1]} ({best_slbuf[0]:+.1f}R)")
    print()

    # --- SWEEP 2: chop_thresh ---
    print("-" * 100)
    print("  SWEEP 2: chop_thresh")
    print("-" * 100)
    best_chop = (tot, BASE["chop_thresh"])
    for v in [45, 50, 55, 58, 60, 62, 65, 70]:
        p = {**BASE, "chop_thresh": v}
        n, tot, wr, pf, years, allyes = run_engine(c1h, sw1h, c15, sw15, fine, p)
        marker = " <-- BEST" if tot > best_chop[0] else ""
        if tot > best_chop[0]:
            best_chop = (tot, v)
        print(fmt_row(f"chop={v}", n, tot, wr, pf, years, allyes) + marker)
    print(f"  >>> Best chop_thresh = {best_chop[1]} ({best_chop[0]:+.1f}R)")
    print()

    # --- SWEEP 3: cooldown_bars ---
    print("-" * 100)
    print("  SWEEP 3: cooldown_bars")
    print("-" * 100)
    best_cd = (tot, BASE["cooldown_bars"])
    for v in [0, 3, 5, 8, 10, 15, 20, 30]:
        p = {**BASE, "cooldown_bars": v}
        n, tot, wr, pf, years, allyes = run_engine(c1h, sw1h, c15, sw15, fine, p)
        marker = " <-- BEST" if tot > best_cd[0] else ""
        if tot > best_cd[0]:
            best_cd = (tot, v)
        print(fmt_row(f"cd={v}", n, tot, wr, pf, years, allyes) + marker)
    print(f"  >>> Best cooldown_bars = {best_cd[1]} ({best_cd[0]:+.1f}R)")
    print()

    # --- SWEEP 4: max_consecutive_losses ---
    print("-" * 100)
    print("  SWEEP 4: max_consecutive_losses (halt)")
    print("-" * 100)
    best_halt = (tot, BASE["max_consecutive_losses"])
    for v in [1, 2, 3, 4, 5, 7, 10, 0]:
        p = {**BASE, "max_consecutive_losses": v}
        n, tot, wr, pf, years, allyes = run_engine(c1h, sw1h, c15, sw15, fine, p)
        label = f"halt={v}" if v > 0 else "halt=off"
        marker = " <-- BEST" if tot > best_halt[0] else ""
        if tot > best_halt[0]:
            best_halt = (tot, v)
        print(fmt_row(label, n, tot, wr, pf, years, allyes) + marker)
    print(f"  >>> Best halt = {best_halt[1]} ({best_halt[0]:+.1f}R)")
    print()

    # --- SWEEP 5: ext_stop_r ---
    print("-" * 100)
    print("  SWEEP 5: ext_stop_r")
    print("-" * 100)
    best_ext = (tot, BASE["ext_stop_r"])
    for v in [0.0, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 5.0]:
        p = {**BASE, "ext_stop_r": v}
        n, tot, wr, pf, years, allyes = run_engine(c1h, sw1h, c15, sw15, fine, p)
        marker = " <-- BEST" if tot > best_ext[0] else ""
        if tot > best_ext[0]:
            best_ext = (tot, v)
        print(fmt_row(f"ext={v}", n, tot, wr, pf, years, allyes) + marker)
    print(f"  >>> Best ext_stop_r = {best_ext[1]} ({best_ext[0]:+.1f}R)")
    print()

    # --- SUMMARY ---
    print("=" * 100)
    print("  SUMMARY")
    print("=" * 100)
    print(f"  Current:  sl={BASE['sl_buf_atr']}  chop={BASE['chop_thresh']}  cd={BASE['cooldown_bars']}  halt={BASE['max_consecutive_losses']}  ext={BASE['ext_stop_r']}")
    print(f"  Best:     sl={best_slbuf[1]}  chop={best_chop[1]}  cd={best_cd[1]}  halt={best_halt[1]}  ext={best_ext[1]}")

    # Run best combo
    best_combo = {
        "sl_buf_atr": best_slbuf[1],
        "chop_thresh": best_chop[1],
        "cooldown_bars": best_cd[1],
        "max_consecutive_losses": best_halt[1],
        "ext_stop_r": best_ext[1],
    }
    print(f"\n  Running best combo: {best_combo}")
    n, tot, wr, pf, years, allyes = run_engine(c1h, sw1h, c15, sw15, fine, best_combo)
    print(fmt_row("BEST COMBO", n, tot, wr, pf, years, allyes))
    print()

    # --- Grid: top 2 combos per param ---
    print("=" * 100)
    print("  GRID: 2x2x2x2x2 = 32 combos")
    print("=" * 100)
    sl_vals = sorted([best_slbuf[1], BASE["sl_buf_atr"]], key=lambda x: x)
    chop_vals = sorted([best_chop[1], BASE["chop_thresh"]], key=lambda x: x)
    cd_vals = sorted([best_cd[1], BASE["cooldown_bars"]], key=lambda x: x)
    halt_vals = sorted([best_halt[1], BASE["max_consecutive_losses"]], key=lambda x: x)
    ext_vals = sorted([best_ext[1], BASE["ext_stop_r"]], key=lambda x: x)

    grid_best = (float("-inf"), None)
    grid_worst = (float("inf"), None)
    results = []
    for sl in sl_vals:
        for ch in chop_vals:
            for cd in cd_vals:
                for ht in halt_vals:
                    for ex in ext_vals:
                        p = {"sl_buf_atr": sl, "chop_thresh": ch, "cooldown_bars": cd,
                             "max_consecutive_losses": ht, "ext_stop_r": ex}
                        n, tot, wr, pf, years, allyes = run_engine(c1h, sw1h, c15, sw15, fine, p)
                        results.append((tot, n, wr, pf, allyes, p))
                        if tot > grid_best[0]:
                            grid_best = (tot, p, n, wr, pf, allyes)
                        if tot < grid_worst[0]:
                            grid_worst = (tot, p, n, wr, pf, allyes)

    results.sort(key=lambda x: -x[0])
    print(f"\n  Top 5:")
    for tot, n, wr, pf, allyes, p in results[:5]:
        flag = "OK" if allyes else "NEG"
        print(f"    {n:4d}t  {tot:+8.1f}R  WR {wr:5.1f}%  PF {pf:5.2f}  {flag}  {p}")
    print(f"\n  Bottom 3:")
    for tot, n, wr, pf, allyes, p in results[-3:]:
        flag = "OK" if allyes else "NEG"
        print(f"    {n:4d}t  {tot:+8.1f}R  WR {wr:5.1f}%  PF {pf:5.2f}  {flag}  {p}")
    print(f"\n  Grid best: {grid_best[1]}  -> {grid_best[2]}t / {grid_best[0]:+.1f}R")
    print(f"  Grid worst: {grid_worst[1]}  -> {grid_worst[2]}t / {grid_worst[0]:+.1f}R")

    # Check if grid best differs from single-var best
    combo_r = grid_best[0]
    single_r = best_slbuf[0]  # any single var best is close enough for comparison
    print(f"\n  Grid best vs baseline: {combo_r:+.1f}R vs {BASE} baseline")
    print("=" * 100)

if __name__ == "__main__":
    main()
