"""TEMP TEST — run the real update flow for all intervals, then status."""
import sys
sys.path.insert(0, "backend")

from src import config
from src import upstox_fetcher as F

tok = config.get_access_token()

for iv in ["daily", "5min", "1min"]:
    res = F.update_data(tok, iv)
    print(f"[{iv}] rows_fetched={res['rows_fetched']} up_to_date={res['up_to_date']}")

print("\n--- STATUS ---")
for iv in ["daily", "5min", "1min"]:
    s = F.interval_status(iv)
    print(f"[{iv}] badge={s.get('badge')} | {s.get('message')}")
