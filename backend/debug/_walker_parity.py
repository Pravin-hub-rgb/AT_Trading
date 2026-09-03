"""Walker parity test: run walker.py over nifty_1min.csv per day, emit every
sealed pivot from process_bar (exactly what firstswing.py consumes).
Output lines: date|gIdx|kind|px|time — compared 1:1 against flowline.ts output.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pandas as pd
from src.walker import WalkerEngine, FlowCandle

df = pd.read_csv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "nifty_1min.csv"))
df["timestamp"] = pd.to_datetime(df["timestamp"])
out = []
for d, g in df.groupby(df["timestamp"].dt.strftime("%Y-%m-%d"), sort=True):
    g = g.reset_index(drop=True)
    w = WalkerEngine()
    for i, r in enumerate(g.itertuples()):
        fc = FlowCandle(
            date=r.timestamp.strftime("%Y-%m-%dT%H:%M:%S"),
            open=float(r.open), high=float(r.high),
            low=float(r.low), close=float(r.close),
        )
        for p in w.process_bar(fc, i):
            if not p.sealed:
                continue
            out.append(f"{d}|{i}|{p.kind}|{p.px:.2f}|{p.time}")
print("\n".join(out))