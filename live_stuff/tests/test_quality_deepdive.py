"""Deep dive on Concept 1 (Leg Quality) — verify it's real, not a bug.
Check IS yearly breakdown, quality component analysis, and robustness."""
import sys, time
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

from run_experiment import get_data
from test_experiments_craze import build_module, _compute_swings
from engine.v18_params import SWING

BASELINE = {"mode": "atr_high", "atr_high_thresh": 0.65, "atr_low_thresh": 0.35,
            "sl_buf_atr": 0.01, "chop_thresh": 58.0, "cooldown_bars": 0,
            "max_consecutive_losses": 3, "ext_stop_r": 3.0,
            "exp_partial_r": 0.0, "exp_wage_h": 10, "exp_skip_weekend": 1,
            "window_end": "exit"}


def compute_leg_quality(trades, c15, sw15):
    """Score leg quality from swing metadata."""
    enriched = []
    for t in trades:
        entry_date = t.get("entry_date", "")[:19]
        bar_idx = -1
        for j, c in enumerate(c15):
            if c["date"][:19] == entry_date:
                bar_idx = j
                break

        if bar_idx < 0:
            enriched.append({**t, "leg_quality": 0.5, "mag_ratio": 0, "speed": 0, "break_density": 0})
            continue

        # ATR at entry
        start = max(0, bar_idx - 13)
        h = max(float(c15[j]["high"]) for j in range(start, bar_idx + 1))
        l = min(float(c15[j]["low"]) for j in range(start, bar_idx + 1))
        atr_now = h - l if h > l else 1.0

        # Find which swing this trade belongs to
        swing_mag = 0; swing_bars = 1; n_breaks = 0
        for sw in reversed(sw15):
            seg = sw.get("seg", {})
            si = int(seg.get("start_idx", -1))
            ei = int(seg.get("end_idx", -1))
            if si <= bar_idx <= ei and ei > si:
                spx = float(seg.get("start_px", 0))
                epx = float(seg.get("end_px", 0))
                swing_mag = abs(epx - spx)
                swing_bars = ei - si
                n_breaks = len(sw.get("breaks", []))
                break

        mag_ratio = swing_mag / atr_now if atr_now > 0 else 0
        speed = swing_bars
        break_density = n_breaks / max(swing_bars, 1)

        quality = 0.0
        if mag_ratio > 3: quality += 0.4
        elif mag_ratio > 2: quality += 0.3
        elif mag_ratio > 1: quality += 0.2
        else: quality += 0.1

        if speed < 20: quality += 0.3
        elif speed < 40: quality += 0.2
        elif speed < 80: quality += 0.1

        if break_density > 0.1: quality += 0.3
        elif break_density > 0.05: quality += 0.2
        elif break_density > 0.02: quality += 0.1

        enriched.append({**t, "leg_quality": quality, "mag_ratio": mag_ratio,
                        "speed": speed, "break_density": break_density})
    return enriched


def analyze(trades):
    rs = [float(t["r_multiple"]) for t in trades]
    n = len(rs); net = sum(rs)
    wins = sum(1 for r in rs if r > 0); wr = wins / max(n, 1) * 100
    peak = 0.0; cum = 0.0; dd = 0.0
    for r in rs: cum += r; peak = max(peak, cum); dd = max(dd, peak - cum)
    ndd = abs(net / dd) if dd > 0 else 0
    yearly = defaultdict(float)
    for t in trades:
        y = (t.get("exit_date") or t.get("entry_date") or "")[:4]
        yearly[y] += float(t["r_multiple"])
    return {"n": n, "net": net, "wr": wr, "dd": dd, "ndd": ndd, "yearly": dict(yearly)}


def main():
    print("=" * 100)
    print("  LEG QUALITY SCORE — DEEP DIVE")
    print("=" * 100)

    data = get_data()
    sim = build_module()

    trades_is = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                    fine_ltf=data["fine"], **BASELINE)["ltf_trades"]
    eq_is = compute_leg_quality(trades_is, data["c15"], data["sw15"])

    # IS yearly breakdown at different thresholds
    print("\n  IS YEARLY BREAKDOWN:")
    print(f"  {'Threshold':<15} {'n':>5} {'NET':>8} {'DD':>6} {'N/D':>6} {'2023':>8} {'2024':>8} {'2025':>8} {'2026':>8}")
    print(f"  {'-'*85}")

    base_is = analyze(trades_is)
    print(f"  {'base':<15} {base_is['n']:>5} {base_is['net']:>+7.1f}R {base_is['dd']:>5.1f} {base_is['ndd']:>5.2f} "
          f"{base_is['yearly'].get('2023',0):>+7.1f} {base_is['yearly'].get('2024',0):>+7.1f} "
          f"{base_is['yearly'].get('2025',0):>+7.1f} {base_is['yearly'].get('2026',0):>+7.1f}")

    for q in [0.3, 0.4, 0.5, 0.6, 0.7]:
        filt = [t for t in eq_is if t["leg_quality"] >= q]
        a = analyze(filt)
        print(f"  {'q>=' + str(q):<15} {a['n']:>5} {a['net']:>+7.1f}R {a['dd']:>5.1f} {a['ndd']:>5.2f} "
              f"{a['yearly'].get('2023',0):>+7.1f} {a['yearly'].get('2024',0):>+7.1f} "
              f"{a['yearly'].get('2025',0):>+7.1f} {a['yearly'].get('2026',0):>+7.1f}")

    # Component analysis: which component matters most?
    print(f"\n  QUALITY COMPONENT ANALYSIS (IS):")
    print(f"  Each component independently:")
    for name, vals in [("mag_ratio", [t["mag_ratio"] for t in eq_is]),
                       ("speed", [t["speed"] for t in eq_is]),
                       ("break_density", [t["break_density"] for t in eq_is])]:
        # Wins vs losses
        wins = [eq_is[i] for i, v in enumerate(vals) if float(trades_is[i]["r_multiple"]) > 0]
        losses = [eq_is[i] for i, v in enumerate(vals) if float(trades_is[i]["r_multiple"]) <= 0]
        avg_w = sum(v["mag_ratio" if name == "mag_ratio" else "speed" if name == "speed" else "break_density"] for v in wins) / max(len(wins), 1)
        avg_l = sum(v["mag_ratio" if name == "mag_ratio" else "speed" if name == "speed" else "break_density"] for v in losses) / max(len(losses), 1)
        print(f"    {name:<20} wins avg={avg_w:.3f}  losses avg={avg_l:.3f}  delta={avg_w-avg_l:+.3f}")

    # The REAL test: does mag_ratio alone explain the edge?
    print(f"\n  MAG RATIO ALONE (IS):")
    for lo, hi in [(0, 1), (1, 2), (2, 3), (3, 5), (5, 100)]:
        filt = [t for t in eq_is if lo <= t["mag_ratio"] < hi]
        a = analyze(filt)
        print(f"    mag {lo}-{hi}: {a['n']:>4}t {a['net']:>+7.1f}R  WR={a['wr']:.0f}%  avg={a['net']/max(a['n'],1):+.3f}R/t")

    # Speed alone
    print(f"\n  SPEED ALONE (IS):")
    for lo, hi in [(0, 20), (20, 40), (40, 80), (80, 200)]:
        filt = [t for t in eq_is if lo <= t["speed"] < hi]
        a = analyze(filt)
        print(f"    speed {lo}-{hi}: {a['n']:>4}t {a['net']:>+7.1f}R  WR={a['wr']:.0f}%  avg={a['net']/max(a['n'],1):+.3f}R/t")

    # The critical question: is quality>=0.5 picking the SAME trades as mag>=2?
    q50_trades = set(t["entry_date"][:16] for t in eq_is if t["leg_quality"] >= 0.5)
    mag2_trades = set(t["entry_date"][:16] for t in eq_is if t["mag_ratio"] >= 2)
    print(f"\n  OVERLAP:")
    print(f"    quality>=0.5: {len(q50_trades)} trades")
    print(f"    mag_ratio>=2: {len(mag2_trades)} trades")
    print(f"    overlap: {len(q50_trades & mag2_trades)} trades")
    print(f"    quality-only: {len(q50_trades - mag2_trades)} trades")
    print(f"    mag-only: {len(mag2_trades - q50_trades)} trades")

    # Test mag_ratio>=2 as a simpler filter
    mag2_is = [t for t in eq_is if t["mag_ratio"] >= 2]
    a2 = analyze(mag2_is)
    print(f"\n  mag_ratio>=2 alone: IS {a2['n']}t {a2['net']:+.1f}R  DD={a2['dd']:.1f}  N/D={a2['ndd']:.2f}")

    # What about mag_ratio alone on OOS?
    from test_4_new_concepts import load_unseen, load_fine_1m
    (c15o, f15o), (c1ho, f1ho) = load_unseen("15m"), load_unseen("1h")
    fine_oos = load_fine_1m(c1ho[0]["ts"], c1ho[-1]["ts"])
    sw10_oos = _compute_swings(f1ho, "continuous", min_bars=10)
    sw15_oos = _compute_swings(f15o, "continuous", min_bars=SWING["min_bars_15m"])

    trades_oos = sim(c1ho, sw10_oos, c15o, sw15_oos, fine_ltf=fine_oos, **BASELINE)["ltf_trades"]
    eq_oos = compute_leg_quality(trades_oos, c15o, sw15_oos)
    base_oos = analyze(trades_oos)

    print(f"\n  OOS MAG RATIO ALONE:")
    for lo, hi in [(0, 1), (1, 2), (2, 3), (3, 5), (5, 100)]:
        filt = [t for t in eq_oos if lo <= t["mag_ratio"] < hi]
        a = analyze(filt)
        print(f"    mag {lo}-{hi}: {a['n']:>4}t {a['net']:>+7.1f}R  WR={a['wr']:.0f}%  avg={a['net']/max(a['n'],1):+.3f}R/t  21={a['yearly'].get('2021',0):+.1f} 22={a['yearly'].get('2022',0):+.1f}")

    print(f"\n  OOS QUALITY>=0.5 vs mag>=2:")
    q50_oos = [t for t in eq_oos if t["leg_quality"] >= 0.5]
    aq = analyze(q50_oos)
    m2_oos = [t for t in eq_oos if t["mag_ratio"] >= 2]
    am = analyze(m2_oos)
    print(f"    quality>=0.5: {aq['n']}t {aq['net']:+.1f}R  N/D={aq['ndd']:.2f}  21={aq['yearly'].get('2021',0):+.1f} 22={aq['yearly'].get('2022',0):+.1f}")
    print(f"    mag_ratio>=2: {am['n']}t {am['net']:+.1f}R  N/D={am['ndd']:.2f}  21={am['yearly'].get('2021',0):+.1f} 22={am['yearly'].get('2022',0):+.1f}")
    print(f"    baseline:     {base_oos['n']}t {base_oos['net']:+.1f}R  N/D={base_oos['ndd']:.2f}")


if __name__ == "__main__":
    main()
