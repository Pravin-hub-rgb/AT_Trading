"""Data layer tests - validator, backfill, binance."""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine.candle import Candle
from data.validator import (
    validate_candle,
    detect_gaps,
    check_no_gaps,
    find_duplicates,
    validate_sequence,
    interval_seconds,
)
from data.backfill import need_backfill
from data.streamer import MockStreamer


class TestValidator:
    def test_validate_valid_candle(self):
        c = Candle(ts=1000, date="", open=100, high=110, low=95, close=105)
        valid, err = validate_candle(c)
        assert valid, f"Should be valid: {err}"

    def test_validate_invalid_timestamp(self):
        c = Candle(ts=0, date="", open=100, high=110, low=95, close=105)
        valid, err = validate_candle(c)
        assert not valid
        assert "timestamp" in err.lower()

    def test_validate_invalid_ohlc(self):
        c = Candle(ts=1000, date="", open=-100, high=110, low=95, close=105)
        valid, err = validate_candle(c)
        assert not valid

    def test_validate_high_low(self):
        c = Candle(ts=1000, date="", open=100, high=90, low=95, close=105)
        valid, err = validate_candle(c)
        assert not valid
        assert "high" in err.lower() or "low" in err.lower()


class TestGapDetection:
    def test_no_gaps(self):
        candles = [
            Candle(ts=1000, date="", open=100, high=110, low=95, close=105),
            Candle(ts=1900, date="", open=105, high=115, low=100, close=110),
            Candle(ts=2800, date="", open=110, high=120, low=105, close=115),
        ]
        no_gaps, gaps = check_no_gaps(candles, 900)
        assert no_gaps
        assert len(gaps) == 0

    def test_detect_gap(self):
        candles = [
            Candle(ts=1000, date="", open=100, high=110, low=95, close=105),
            Candle(ts=3700, date="", open=110, high=120, low=105, close=115),
        ]
        no_gaps, gaps = check_no_gaps(candles, 900)
        assert not no_gaps
        assert len(gaps) == 1
        assert gaps[0]["missing_count"] == 2

    def test_find_duplicates(self):
        candles = [
            Candle(ts=1000, date="", open=100, high=110, low=95, close=105),
            Candle(ts=1000, date="", open=100, high=110, low=95, close=105),
        ]
        dupes = find_duplicates(candles)
        assert len(dupes) == 1


class TestIntervalSeconds:
    def test_15m(self):
        assert interval_seconds("15m") == 900

    def test_1h(self):
        assert interval_seconds("1h") == 3600

    def test_1d(self):
        assert interval_seconds("1d") == 86400


class TestBackfill:
    def test_need_backfill_no_gap(self):
        candles = [
            Candle(ts=1000, date="", open=100, high=110, low=95, close=105),
            Candle(ts=1900, date="", open=105, high=115, low=100, close=110),
        ]
        assert not need_backfill(candles, "15m", max_gap_seconds=3600)

    def test_need_backfill_with_gap(self):
        candles = [
            Candle(ts=1000, date="", open=100, high=110, low=95, close=105),
            Candle(ts=10000, date="", open=110, high=120, low=105, close=115),
        ]
        assert need_backfill(candles, "15m", max_gap_seconds=3600)


class TestMockStreamer:
    def test_start_stop(self):
        s = MockStreamer()
        assert not s.is_running
        s.start()
        assert s.is_running
        s.stop()
        assert not s.is_running

    def test_get_tick(self):
        s = MockStreamer()
        s.start()
        tick = s.get_tick(timeout=0.1)
        assert tick is not None
        assert "price" in tick
        assert "ts" in tick
        s.stop()


if __name__ == "__main__":
    t = TestValidator()
    t.test_validate_valid_candle()
    t.test_validate_invalid_timestamp()
    t.test_validate_invalid_ohlc()
    t.test_validate_high_low()
    print("TestValidator: PASS")

    t = TestGapDetection()
    t.test_no_gaps()
    t.test_detect_gap()
    t.test_find_duplicates()
    print("TestGapDetection: PASS")

    t = TestIntervalSeconds()
    t.test_15m()
    t.test_1h()
    t.test_1d()
    print("TestIntervalSeconds: PASS")

    t = TestBackfill()
    t.test_need_backfill_no_gap()
    t.test_need_backfill_with_gap()
    print("TestBackfill: PASS")

    t = TestMockStreamer()
    t.test_start_stop()
    t.test_get_tick()
    print("TestMockStreamer: PASS")

    print("\nAll data layer tests passed!")
