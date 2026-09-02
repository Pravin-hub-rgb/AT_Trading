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

# Find 17 Aug
aug17 = [(i, c) for i, c in enumerate(candles) if c.date[:10] == "2026-08-17"]

# Run engine with chop trace
eng = FirstSwingEngine({"timeCap": "09:29"})
for g_idx, c in aug17:
    eng.process_bar(c, g_idx)
    t = c.date[11:16]
    if t == "10:13" or t == "10:14" or t == "10:15":
        print(f"\n=== {t} ===")
        print(f"  hi={eng.hi:.2f}  lo={eng.lo:.2f}")
        print(f"  e_hi.px={eng.e_hi.px:.2f}  e_lo.px={eng.e_lo.px:.2f}")
        print(f"  e_hi_prev.px={eng.e_hi_prev.px:.2f}  e_lo_prev.px={eng.e_lo_prev.px:.2f}")
        print(f"  locked_level={eng.locked_level:.2f}")
        print(f"  dir={eng.dir}  state={eng.state}  dir_confirmed={eng.dir_confirmed}")
        print(f"  b1_bar_idx={eng.b1_bar_idx}  b2_pivot={eng.b2_pivot}")
        print(f"  normal_highs count={len(eng.normal_highs)}")
        if eng.normal_highs:
            print(f"  latest normal_high: idx={eng.normal_highs[-1].idx} px={eng.normal_highs[-1].px:.2f} time={eng.normal_highs[-1].time}")
        print(f"  micro_highs count={len(eng.micro_highs)}")
        print(f"  first_chop_cross_idx={eng.first_chop_cross_idx}  first_chop_cross_px={eng.first_chop_cross_px:.2f}")
        print(f"  sustain_streak={eng.sustain_streak}")
        print(f"  declared={eng.declared}  confirm_source={eng.confirm_source}")
