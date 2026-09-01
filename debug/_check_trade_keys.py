"""Debug: inspect raw trade dict to check entry_ts/exit_ts are set."""
import sys
sys.path.insert(0, "backend/src")
from intraday import run_backtest
import json

cfg = {
    "ft_fail_enabled": True,
    "entry_method": "pivot_break",
    "swing_mode": "opposite_swing_needed",
}

# Use the same data file as test_aug27.py
import os
# Just call run_backtest and grab first day's trade
import pandas as pd

# load 5min and 1min
df5 = pd.read_json(r"C:\Users\Pravin\Desktop\main\AT_Trading\debug\_ts_2026-08-27.json")
df1 = pd.read_json(r"C:\Users\Pravin\Desktop\main\AT_Trading\debug\_py_2026-08-27.json")

print("DF5 cols:", df5.columns.tolist())
print("DF1 cols:", df1.columns.tolist())
print("DF5 rows:", len(df5))
print("DF1 rows:", len(df1))

# Need bias labels - inspect what run_backtest needs
