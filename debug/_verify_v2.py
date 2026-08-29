"""Quick smoke test for FsV2Engine port — verify declaration on extended data."""
import sys
sys.path.insert(0, "backend")
from src.walker import FlowCandle
from src.swing_engine import FsV2Engine


def make_candle(g_idx: int, h: int, m: int, o: float, hi: float, lo: float, cl: float) -> FlowCandle:
    return FlowCandle(
        date=f"2026-08-29T{h:02d}:{m:02d}:00+05:30",
        open=o, high=hi, low=lo, close=cl,
    )


def scenario_sell_with_sustain():
    """Selling day — 2 same-side breaks → dir confirmed, then 7 bars sustain below 98.0 → declared."""
    candles = [
        # bars 0-13: morning setup (first low at bar 3 = 99.0, reversal up bar 10 = 100.5)
        make_candle(0, 9, 15, 100.0, 100.2, 99.8, 100.0),
        make_candle(1, 9, 16, 100.0, 100.1, 99.7, 99.8),
        make_candle(2, 9, 17, 99.8, 99.9, 99.6, 99.7),
        make_candle(3, 9, 18, 99.7, 99.8, 99.0, 99.1),  # first low 99.0
        make_candle(4, 9, 19, 99.1, 99.2, 98.9, 99.0),
        make_candle(5, 9, 20, 99.0, 99.1, 98.7, 98.8),
        make_candle(6, 9, 21, 98.8, 99.0, 98.6, 98.7),
        make_candle(7, 9, 22, 98.7, 98.8, 98.5, 98.6),
        make_candle(8, 9, 23, 98.6, 98.7, 98.4, 98.5),
        make_candle(9, 9, 24, 98.5, 98.6, 98.3, 98.4),
        make_candle(10, 9, 25, 98.4, 100.5, 98.3, 100.3),  # reversal up bar (high 100.5)
        make_candle(11, 9, 26, 100.3, 100.4, 100.0, 100.1),
        make_candle(12, 9, 27, 100.1, 100.2, 99.5, 99.6),
        make_candle(13, 9, 28, 99.6, 99.7, 99.0, 99.1),
        # bar 14 = 09:29: back below 99.0 → LOCK, dir=down, base=down, SSB=1
        make_candle(14, 9, 29, 99.1, 99.2, 98.5, 98.6),
        # bars 15-18: same-side breaks
        make_candle(15, 9, 30, 98.6, 98.7, 98.4, 98.5),
        make_candle(16, 9, 31, 98.5, 98.6, 98.3, 98.4),
        make_candle(17, 9, 32, 98.4, 98.5, 98.2, 98.3),
        # bar 18 = 09:33: second same-side break → DIR CONFIRMED, locked at 98.1
        make_candle(18, 9, 33, 98.3, 98.4, 98.1, 98.2),
        # bars 19+: 7 bars holding below 98.1 with NO new extreme
        # (lateral move around 97.9-98.0, e_lo.px stays at 98.0)
        make_candle(19, 9, 34, 98.00, 98.05, 98.00, 98.02),  # streak=1 (close 98.02 < 98.1, e_lo unchanged 98.0)
        make_candle(20, 9, 35, 98.02, 98.06, 98.00, 98.01),  # streak=2
        make_candle(21, 9, 36, 98.01, 98.05, 98.00, 98.03),  # streak=3
        make_candle(22, 9, 37, 98.03, 98.07, 98.00, 98.04),  # streak=4
        make_candle(23, 9, 38, 98.04, 98.08, 98.00, 98.05),  # streak=5
        make_candle(24, 9, 39, 98.05, 98.09, 98.00, 98.06),  # streak=6
        make_candle(25, 9, 40, 98.06, 98.09, 98.00, 98.07),  # streak=7 → DECLARE
    ]
    eng = FsV2Engine()
    for i, c in enumerate(candles):
        eng.process_bar(c, i)
    return eng


def main():
    eng = scenario_sell_with_sustain()
    print("== Scenario SELL with 7-bar sustain ==")
    print("declared:", eng.declared)
    print("dir:", eng.dir)
    print("tier:", eng.tier)
    print("start_idx:", eng.start_idx, "start_px:", round(eng.start_px, 2))
    print("end_idx:", eng.end_idx, "end_px:", round(eng.end_px, 2))
    print("confirmed_at_idx:", eng.confirmed_at_idx)
    print("confirm_source:", eng.confirm_source)
    print("locked_level_px:", round(eng.locked_level_px, 2) if eng.locked_level_px == eng.locked_level_px else float("nan"))
    print("dir_confirmed_idx:", eng.dir_confirmed_idx)
    print("last_confirm_hit:", eng.last_confirm_hit)
    print()
    print("Pools:", eng.debug_pools())


if __name__ == "__main__":
    main()
