"""Check for data issues."""
import sys
sys.path.insert(0, "backend")
import pandas as pd
from src.bias import compute_bias
from src.config import DATA_DIR

df = pd.read_csv(DATA_DIR / "nifty_5min.csv")
print(f"df shape: {df.shape}")
print(f"df columns: {list(df.columns)}")
print(f"df timestamp sample: {df['timestamp'].head()}")

# Check for duplicates
dupes = df[df.duplicated(subset=['timestamp'], keep=False)]
print(f"\nDuplicate timestamps: {len(dupes)}")
if len(dupes) > 0:
    print(dupes.head(20))

# Check date range
df["timestamp"] = pd.to_datetime(df["timestamp"])
print(f"\nDate range: {df['timestamp'].min()} to {df['timestamp'].max()}")

# Check for future dates
future = df[df["timestamp"] > pd.Timestamp.now()]
print(f"\nFuture dates: {len(future)}")
if len(future) > 0:
    print(future)

# Check if timestamp has timezone
print(f"\nTimestamp dtype: {df['timestamp'].dtype}")
print(f"Timestamp sample tz: {df['timestamp'].iloc[0].tz}")

# Check the last few rows
print(f"\nLast 5 rows:")
print(df.tail())
