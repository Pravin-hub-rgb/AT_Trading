"""Patch the entry loop in intraday.py to add detailed tracing, then run simulate_day."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path

intraday_path = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / "src" / "intraday.py"
src = intraday_path.read_text(encoding="utf-8")

orig = "        # ---- entry trigger: pace_break or pivot_break ----\n        if i > 0 and cur_swing is not None and can_enter:"
patched = """        # ---- entry trigger: pace_break or pivot_break ----
        # DEBUG PATCH
        result["events"].append({
            "type": "_entry_attempt",
            "bar": i, "time": cur["time"],
            "cur_swing": cur_swing,
            "can_enter": can_enter,
            "open_trade": open_trade is not None,
            "entries_done": entries_done,
            "fs_gate_ok": entry_swing_confirmed_idx < 0 or i > entry_swing_confirmed_idx,
            "entry_gate_idx": entry_swing_confirmed_idx,
            "want_dir": want_dir,
            "cur_low": cur.get("low"),
            "cur_high": cur.get("high"),
        })
        if i > 0 and cur_swing is not None and can_enter:"""

if patched not in src:
    src = src.replace(orig, patched, 1)

intraday_path.write_text(src, encoding="utf-8")
print(f"Patched {intraday_path}")

# Run
import pandas as pd
from src.config import DATA_DIR
import src.intraday as idm

df5 = pd.read_csv(DATA_DIR / "nifty_5min.csv")
df5["timestamp"] = pd.to_datetime(df5["timestamp"])
df5["ts"] = df5["ts"].astype("int64")
df5 = df5[df5["timestamp"].dt.strftime("%Y-%m-%d") == "2026-08-28"].copy().reset_index(drop=True)

df1 = pd.read_csv(DATA_DIR / "nifty_1min.csv")
df1["timestamp"] = pd.to_datetime(df1["timestamp"])
df1["ts"] = df1["ts"].astype("int64")
df1 = df1[df1["timestamp"].dt.strftime("%Y-%m-%d") == "2026-08-28"].copy().reset_index(drop=True)

cfg = {
    "sl_mode": "avg",
    "execution": "1min",
    "trailing": "off",
    "trail_distance_r": 1.0,
    "gap_pct": 0.0027,
    "sl_pivot_buffer": 1.0,
    "ft_fail_enabled": True,
    "entry_method": "pivot_break",
    "swing_mode": "opposite_swing_needed",
}

ctx = {"gap": "flat", "extreme": None, "avg_range": 50.0}
result = idm.simulate_day(df5, "bearish", cfg, m1_day=df1, ctx=ctx)

print("\n=== ENTRY ATTEMPTS (bars 0-10) ===")
for ev in result.get("events", []):
    if ev.get("type") == "_entry_attempt" and ev.get("bar", -1) <= 10:
        print(f"  [{ev['bar']}] {ev['time']} | cur_swing={ev['cur_swing']} can_enter={ev['can_enter']} open_trade={ev['open_trade']} fs_gate_ok={ev['fs_gate_ok']} gate_idx={ev['entry_gate_idx']} want_dir={ev['want_dir']} L={ev['cur_low']} H={ev['cur_high']}")

print("\n=== TRADES ===")
for t in result.get("trades", []):
    print(f"  {t.get('entry_time', 'N/A')} | entry_bar={t.get('entry_bar')}")

print(f"\n1-min FS confirmed_idx_5min: {result.get('fs1_1min_confirmed_idx_5min')}")
print(f"Case: {result.get('case')}")