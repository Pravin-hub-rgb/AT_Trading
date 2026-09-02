import sys
sys.path.insert(0, "backend")
from backend.src.firstswing import FirstSwingEngine
from backend.src.walker import FlowCandle

lines = open("data/nifty_1min.csv", encoding="utf-8-sig").read().splitlines()
candles = []
for l in lines:
    p = l.split(",")
    if len(p) > 5 and p[0][0].isdigit():
        candles.append(
            FlowCandle(date=p[0], open=float(p[2]), high=float(p[3]), low=float(p[4]), close=float(p[5]))
        )

aug17 = [(i, c) for i, c in enumerate(candles) if c.date[:10] == "2026-08-17"]
eng = FirstSwingEngine({"timeCap": "09:29"})

# Run to 10:15 and print normal_highs
for g_idx, c in aug17:
    t = c.date[11:16]
    eng.process_bar(c, g_idx)
    if t == "10:15":
        print(f"At 10:15 (g_idx={g_idx}):")
        print(f"  hi={eng.hi:.2f}  e_hi.px={eng.e_hi.px:.2f}")
        print(f"  e_hi_prev.px={eng.e_hi_prev.px:.2f}")
        print(f"  locked_level={eng.locked_level:.2f}")
        print(f"  chop target check: hi={eng.hi:.2f} vs e_hi_prev.px={eng.e_hi_prev.px:.2f}")
        print(f"  normal_highs ({len(eng.normal_highs)} entries):")
        for h in eng.normal_highs[-10:]:
            print(f"    idx={h.idx}  px={h.px:.2f}  time={h.time}")
        print(f"  micro_highs ({len(eng.micro_highs) if hasattr(eng, 'micro_highs') else 'N/A'} entries):")
        if hasattr(eng, 'micro_highs'):
            for h in eng.micro_highs[-10:]:
                print(f"    idx={h.idx}  px={h.px:.2f}  time={h.time}")
        print(f"  first_chop_cross_idx={eng.first_chop_cross_idx}")
        print(f"  _latest_choppable test: g_idx={g_idx} => needs idx <= {g_idx - 2}")
        for h in reversed(eng.normal_highs):
            print(f"    normal_high idx={h.idx} => choppable={h.idx <= g_idx - 2}")
            if h.idx <= g_idx - 2:
                print(f"    -> chop target: px={h.px:.2f}, hi={eng.hi:.2f}, break={eng.hi > h.px}")
                break
