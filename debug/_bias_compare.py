"""Compare bias labels between script and server."""
import sys
sys.path.insert(0, "backend")
import pandas as pd
from src.bias import compute_bias
from src.config import DATA_DIR

df = pd.read_csv(DATA_DIR / "nifty_5min.csv")
df["timestamp"] = pd.to_datetime(df["timestamp"])

bl = compute_bias(df)
print(f"Total bias labels: {len(bl)}")
print(f"First: {bl[0] if bl else 'none'}")
print(f"Last: {bl[-1] if bl else 'none'}")
print(f"Traded days: {sum(1 for lb in bl if lb.get('bias') in ('bullish', 'bearish'))}")
