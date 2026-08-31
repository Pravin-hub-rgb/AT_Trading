"""Verify the 1-min precision entry hunt respects the swing gate.

Run from backend/: python -m debug._ss_gate_aug28

Tests the user's exact settings on 2026-08-28:
  sl=avg x 1, exec=1min, entry=pace_break, swing=opposite_swing_needed

Expected: NO trades fire before the second-swing (yellow line) is confirmed.
Observed before fix: trades at 9:50 and 10:20, both before fs2 confirmed at ~10:21.
"""
import sys
sys.path.insert(0, ".")

import pandas as pd
from src.intraday import run_backtest, DEFAULT_CFG
from src.bias import compute_bias
from src.config import DATA_DIR

# User's exact settings
CFG = {
    **DEFAULT_CFG,
    "sl_mode": "avg",
    "execution": "1min",
    "entry_method": "pace_break",
    "swing_mode": "opposite_swing_needed",
}

# Load data
df5 = pd.read_csv(DATA_DIR / "nifty_5min.csv")
df5["timestamp"] = pd.to_datetime(df5["timestamp"])
df1 = pd.read_csv(DATA_DIR / "nifty_1min.csv")
df1["timestamp"] = pd.to_datetime(df1["timestamp"])
daily = pd.read_csv(DATA_DIR / "nifty_daily.csv") if (DATA_DIR / "nifty_daily.csv").exists() else None
labels = compute_bias(df5, daily)
labels = [lb for lb in labels if lb["date"] in set(df5["timestamp"].astype(str).str[:10])]

# Run backtest
results = run_backtest(df5, labels, CFG, df_1min=df1)
# run_backtest returns {"days": [...], "stats": {...}}
all_days = results["days"]


def check_day(r: dict) -> list[dict]:
    """Return list of violations (empty = pass)."""
    events = r.get("events", [])
    trades = r.get("trades", [])
    date = r["date"]

    # First swing info — result now stores first_swing_confirmed_idx and
    # first_swing_end_time (set in simulate_day). Fall back to event lookup.
    fs1_dir = r.get("swing_direction")
    fs1_confirmed_idx = r.get("first_swing_confirmed_idx", -1)
    fs1_end_time = r.get("first_swing_end_time", "?")
    if fs1_confirmed_idx < 0 or fs1_end_time == "?":
        fs1_decl = next(
            (e for e in events if e.get("type") in ("first_swing_declared", "fsv2_declared")),
            None,
        )
        if fs1_decl:
            if fs1_confirmed_idx < 0:
                fs1_confirmed_idx = fs1_decl.get("bar", -1)
            if fs1_end_time == "?":
                fs1_end_time = fs1_decl.get("time", "?")

    # Second swing info (1-min, mapped to 5-min index).
    # The fs2_segment event has the confirmed_at_time and confirmed_at_idx.
    fs2_dir = r.get("swing2_direction")
    fs2_confirmed_idx = r.get("swing2_confirmed_idx", -1)
    fs2_seg = next((e for e in events if e.get("type") == "fs2_segment"), None)
    fs2_confirmed_time = (fs2_seg or {}).get("confirmed_at_time", "?") if fs2_seg else "?"
    if fs2_seg and fs2_confirmed_idx < 0:
        fs2_confirmed_idx = fs2_seg.get("confirmed_at_idx", -1)

    print(f"\n=== {date} gate verification ===")
    print(f"  sl_mode={CFG['sl_mode']}, execution={CFG['execution']}, "
          f"entry={CFG['entry_method']}, swing={CFG['swing_mode']}")
    print(f"  First swing FS:  dir={fs1_dir}, confirmed at idx={fs1_confirmed_idx}, time={fs1_end_time}")
    print(f"  Second swing FS: dir={fs2_dir}, confirmed at idx={fs2_confirmed_idx}, time={fs2_confirmed_time}")

    violations = []
    # Find the actual 5-min bar times from the events for context.
    # Look for first 5-min candle time.
    first_5m_time = next(
        (e.get("time") for e in events if e.get("type") == "5min_open"), None
    )
    if not first_5m_time:
        # Fall back to deriving from the first 5-min entry/candle in the events.
        # Use the day_setup event (always present once a break is detected).
        # Otherwise: assume 09:15 market open.
        first_5m_time = "09:15"
    print(f"  5-min grid: idx=0 -> {first_5m_time}, idx=1 -> +5min, ...")
    print(f"\n  Trades ({len(trades)}):")
    for t in trades:
        et = t.get("entry_time", "?")
        eb = t.get("entry_bar", "?")
        print(f"    bar={eb} time={et}  dir={t.get('dir')}  px={t.get('entry_price')}  type={t.get('pace_break_type')}")

        # The gate: first swing (cyan line) FS is the entry gate.
        # Second swing (yellow line) is only for direction filtering.
        # entry_bar must be > first swing's confirmed idx.
        if fs1_confirmed_idx >= 0 and eb <= fs1_confirmed_idx:
            v = {
                "date": date,
                "entry_time": et,
                "entry_bar": eb,
                "gate_idx": fs1_confirmed_idx,
                "gate_time": fs1_end_time,
                "msg": f"VIOLATION: entry_bar {eb} <= fs1_confirmed_idx {fs1_confirmed_idx} ({fs1_end_time})"
            }
            violations.append(v)
            print(f"      !!! {v['msg']}")
        elif fs1_confirmed_idx < 0:
            # fs1 not confirmed — should not happen, but log it
            print(f"      WARN: fs1_confirmed_idx is {fs1_confirmed_idx} (unconfirmed)")
        else:
            print(f"      ok (bar {eb} > gate {fs1_confirmed_idx})")

    # Also check: no pending_direct fires before the gate on any 5-min bar
    pending_disarm_pre_gate = [
        e for e in events
        if e.get("type") in ("setup_disarmed_pre_gate",)
    ]
    if pending_disarm_pre_gate:
        print(f"\n  Stale pending_direct dropped (pre-gate): {len(pending_disarm_pre_gate)}")
        for e in pending_disarm_pre_gate[:5]:
            print(f"    bar={e.get('bar')} time={e.get('time')} reason={e.get('reason')}")

    return violations


# --- 28 Aug focused check ---
aug28 = "2026-08-28"
day28 = [r for r in all_days if r["date"] == aug28]

if not day28:
    print(f"ERROR: no results for {aug28}")
    sys.exit(1)

v28 = check_day(day28[0])
print(f"\n{'='*50}")
if v28:
    print(f"FAIL: {len(v28)} violation(s) on {aug28}")
    for v in v28:
        print(f"  {v['msg']}")
    sys.exit(1)
else:
    print(f"PASS on {aug28}")


# --- Last 30-day broad check ---
from datetime import datetime, timedelta
cutoff = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
recent = [r for r in all_days if r["date"] >= cutoff and r["date"] != aug28]

print(f"\n=== Last-30-day check ({len(recent)} days) ===")
all_violations = list(v28)
for r in recent:
    all_violations.extend(check_day(r))

if all_violations:
    unique_dates = sorted(set(v["date"] for v in all_violations))
    print(f"\nFAIL: {len(all_violations)} violation(s) across {len(unique_dates)} day(s): {unique_dates}")
    sys.exit(1)
else:
    print(f"PASS: 0 violations across {len(recent) + 1} days")
