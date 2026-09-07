"""BTC sweep phase 2 — combos of the S2/S3/S4 winners from btc_sweep.py."""
from btc_sweep import (  # noqa: F401
    build, collect_signals, compute_btc_swings, daily_colors, fmt, sim, stats,
    streak_regime_gate, load_btc_df,
)


def main() -> None:
    df5 = load_btc_df("5m")
    candles, flow = build(df5)
    n = len(flow)
    days, colors = daily_colors(df5)
    gate31 = streak_regime_gate(days, colors)

    df15 = load_btc_df("15m")
    c15, f15 = build(df15)
    sw15 = compute_btc_swings(f15, max_swings=len(f15) // 2)
    bias15 = sorted(
        (int(c15[s["confirmed_at_idx"]]["ts"]), s["dir"])
        for s in sw15
        if 0 <= int(s.get("confirmed_at_idx", -1)) < len(c15)
    )

    swings = compute_btc_swings(flow, max_swings=n // 2)
    swings20 = compute_btc_swings(flow, opts={"minBars": 20}, max_swings=n // 2)
    print(f"swings 14/7: {len(swings)}   swings 20/7: {len(swings20)}\n")

    sig14d = collect_signals(swings, "decisive", True)
    sig14f = collect_signals(swings, "flip", True)
    sig20d = collect_signals(swings20, "decisive", True)
    sig20f = collect_signals(swings20, "flip", True)
    sigs = {("14", "decisive"): sig14d, ("14", "flip"): sig14f,
            ("20", "decisive"): sig20d, ("20", "flip"): sig20f}

    tests = [
        # (name, swings_key, entry_break, sim kwargs)
        ("A1 flip + swingTrail be1 (14/7)", "14", "flip", {"trailing": "swing", "be": 1.0}),
        ("A2 flip + swingTrail be0", "14", "flip", {"trailing": "swing", "be": 0.0}),
        ("A3 decisive + swingTrail be1 (14/7)", "14", "decisive", {"trailing": "swing", "be": 1.0}),
        ("B1 minBars20 flip + swingTrail be1", "20", "flip", {"trailing": "swing", "be": 1.0}),
        ("B2 minBars20 decisive + swingTrail be1", "20", "decisive", {"trailing": "swing", "be": 1.0}),
        ("C1 flip + swingTrail be1 + 15m bias", "14", "flip", {"trailing": "swing", "be": 1.0, "bias15": bias15}),
        ("C2 flip + swingTrail be1 + streak311", "14", "flip", {"trailing": "swing", "be": 1.0, "day_gate": gate31}),
        ("C3 minBars20 flip + swingTrail + 15m bias", "20", "flip", {"trailing": "swing", "be": 1.0, "bias15": bias15}),
        ("C4 minBars20 flip + swingTrail + streak311", "20", "flip", {"trailing": "swing", "be": 1.0, "day_gate": gate31}),
        ("C5 minBars20 flip + swingTrail + bias + streak", "20", "flip", {"trailing": "swing", "be": 1.0, "bias15": bias15, "day_gate": gate31}),
        ("C6 minBars20 decisive + swingTrail + bias", "20", "decisive", {"trailing": "swing", "be": 1.0, "bias15": bias15}),
        ("D1 flip rr3 off be1 + 15m bias", "14", "flip", {"rr": 3.0, "be": 1.0, "bias15": bias15}),
        ("D2 flip rr3 off be1 + streak311", "14", "flip", {"rr": 3.0, "be": 1.0, "day_gate": gate31}),
        ("D3 flip rr3 off be1 + bias + streak", "14", "flip", {"rr": 3.0, "be": 1.0, "bias15": bias15, "day_gate": gate31}),
        ("D4 minBars20 flip rr3 off be1 + bias + streak", "20", "flip", {"rr": 3.0, "be": 1.0, "bias15": bias15, "day_gate": gate31}),
        ("D5 minBars20 decisive rr3 off be1 + bias + streak", "20", "decisive", {"rr": 3.0, "be": 1.0, "bias15": bias15, "day_gate": gate31}),
        ("E1 flip r1 trail + 15m bias", "14", "flip", {"trailing": "r", "trail_r": 1.0, "be": 1.0, "bias15": bias15}),
        ("E2 flip r1 trail + streak311", "14", "flip", {"trailing": "r", "trail_r": 1.0, "be": 1.0, "day_gate": gate31}),
        ("E3 minBars20 flip r1 + bias + streak", "20", "flip", {"trailing": "r", "trail_r": 1.0, "be": 1.0, "bias15": bias15, "day_gate": gate31}),
    ]
    sw_by_key = {"14": swings, "20": swings20}
    for name, key, eb, kwargs in tests:
        sw = sw_by_key[key]
        tr = sim(candles, sw, sigs[(key, eb)], sl_mode="swing", **kwargs)
        print(fmt(name, stats(tr)))


if __name__ == "__main__":
    main()
