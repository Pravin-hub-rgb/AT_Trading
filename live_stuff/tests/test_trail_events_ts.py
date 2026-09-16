"""Trail-events epoch test (C6).

Proves _trail_events_ts converts IST wall-clock confirm times to the TRUE
UTC epoch (was: parsed as UTC -> events born 5.5h in the future -> trail
ratchets 5.5h late vs backtest).

  Regression case: confirmed_at_time "2025-01-01 12:00:00" (IST)
    = 06:30 UTC -> true epoch 1735713000
    (pre-fix: 1735732800 = +19800s = 5.5h skew)

  Bar-alignment: the event must activate at the CONFIRM BAR itself in a
  _trail_sl-style walk (bar close-times >= event epoch), mirroring the
  backtest's confirmed_at_idx semantics (ratchet at conf bar, effective
  from the next bar).

Run: python live_stuff/tests/test_trail_events_ts.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from src.btc.btc_engine import _trail_events_ts, IST_OFFSET_S
from datetime import datetime, timezone


def utc_epoch(y, m, d, hh, mm):
    return int(datetime(y, m, d, hh, mm, tzinfo=timezone.utc).timestamp())


def main():
    # 1. THE regression case: IST wall string -> true UTC epoch
    swings = [{"dir": "up", "confirmed_at_time": "2025-01-01 12:00:00",
               "seg": {"start_px": 100.0}}]
    ev = _trail_events_ts(swings, 1)
    assert len(ev) == 1, f"expected 1 event, got {len(ev)}"
    expected = utc_epoch(2025, 1, 1, 6, 30)  # 12:00 IST = 06:30 UTC
    assert ev[0][0] == expected, f"event epoch {ev[0][0]} != true UTC {expected}"
    assert ev[0][0] == 1735713000, f"known-value regression: {ev[0][0]}"
    assert ev[0][1] == 100.0
    print(f"PASS 1: IST string -> true UTC epoch {ev[0][0]} (pre-fix was {expected + IST_OFFSET_S})")

    # 2. Direction filter
    swings = [
        {"dir": "up", "confirmed_at_time": "2025-01-01 12:00:00", "seg": {"start_px": 100.0}},
        {"dir": "down", "confirmed_at_time": "2025-01-01 13:00:00", "seg": {"start_px": 200.0}},
    ]
    up = _trail_events_ts(swings, 1)
    down = _trail_events_ts(swings, -1)
    assert len(up) == 1 and up[0][1] == 100.0
    assert len(down) == 1 and down[0][1] == 200.0
    print("PASS 2: direction filter (up for longs, down for shorts)")

    # 3. Missing / malformed confirmed_at_time -> skipped, no crash
    swings = [
        {"dir": "up", "seg": {"start_px": 100.0}},                      # missing
        {"dir": "up", "confirmed_at_time": "garbage", "seg": {"start_px": 100.0}},  # malformed
        {"dir": "up", "confirmed_at_time": "2025-01-02 09:00:00", "seg": {"start_px": 110.0}},
    ]
    ev = _trail_events_ts(swings, 1)
    assert len(ev) == 1, f"only the valid swing should produce an event, got {len(ev)}"
    assert ev[0][0] == utc_epoch(2025, 1, 2, 3, 30)  # 09:00 IST = 03:30 UTC
    print("PASS 3: missing/malformed confirm times skipped safely")

    # 4. Multiple swings -> chronological order
    swings = [
        {"dir": "up", "confirmed_at_time": "2025-01-02 09:00:00", "seg": {"start_px": 110.0}},
        {"dir": "up", "confirmed_at_time": "2025-01-01 12:00:00", "seg": {"start_px": 100.0}},
    ]
    ev = _trail_events_ts(swings, 1)
    assert len(ev) == 2 and ev[0][0] < ev[1][0], "events must be chronological"
    print("PASS 4: multiple swings -> chronological order")

    # 5. Activation alignment: event activates AT the confirm bar in a
    #    _trail_sl-style walk (bar_ts = candle close-times)
    confirm_bar_open_ist = "2025-01-01 12:00:00"
    confirm_open_utc = utc_epoch(2025, 1, 1, 6, 30)
    bars = [confirm_open_utc + 900 * (i + 1) for i in range(6)]  # close-times: confirm bar onward
    ev = _trail_events_ts([{"dir": "up", "confirmed_at_time": confirm_bar_open_ist,
                            "seg": {"start_px": 100.0}}], 1)
    event_ts = ev[0][0]
    activation = next(i for i, bt in enumerate(bars) if event_ts <= bt)
    assert activation == 0, f"event must activate AT the confirm bar, got index {activation}"
    print("PASS 5: activation at the confirm bar itself (mirrors confirmed_at_idx)")

    print("=" * 60)
    print("ALL TRAIL EPOCH CHECKS PASSED")


if __name__ == "__main__":
    main()
