"""Full-day sweep driver for the backend FirstSwingEngine port (working tree)."""
import sys

sys.path.insert(0, ".")
from src.firstswing import compute_fs_v2_results
from src.walker import FlowCandle

lines = open("../data/nifty_1min.csv", encoding="utf-8-sig").read().splitlines()
candles = []
for l in lines:
    p = l.split(",")
    if len(p) > 5 and p[0][0].isdigit():
        candles.append(
            FlowCandle(date=p[0], open=float(p[2]), high=float(p[3]), low=float(p[4]), close=float(p[5]))
        )

res = compute_fs_v2_results(candles, {"timeCap": "09:29"})
n = 0
for r in res:
    seg = r.seg
    if seg is None:
        continue
    n += 1
    ct = candles[r.conf_idx].date[11:16] if 0 <= r.conf_idx < len(candles) else "-"
    et = candles[seg.end_idx].date[11:16] if 0 <= seg.end_idx < len(candles) else "-"
    st = candles[seg.start_idx].date[11:16] if 0 <= seg.start_idx < len(candles) else "-"
    print(f"{r.day}|{r.dir}|start={st}|end={et}|fs={ct}|{r.source}")
print(f"TOTAL {n}", file=sys.stderr)