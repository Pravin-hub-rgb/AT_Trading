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

eng = FirstSwingEngine({"timeCap": "09:29"})
for g_idx, c in aug17:
    t = c.date[11:16]
    eng.process_bar(c, g_idx)
    if t == "09:33" or t == "09:32" or t == "09:34":
        print(f"\n=== {t} (g_idx={g_idx}) ===")
        print(f"  hi={eng.hi:.2f}  lo={eng.lo:.2f}")
        print(f"  e_hi.px={eng.e_hi.px:.2f}  e_lo.px={eng.e_lo.px:.2f}")
        print(f"  e_hi_prev.px={eng.e_hi_prev.px:.2f}  e_lo_prev.px={eng.e_lo_prev.px:.2f}")
        print(f"  locked_level={eng.locked_level:.2f}")
        print(f"  dir={eng.dir}  state={eng.state}  dir_confirmed={eng.dir_confirmed}")
        print(f"  first_chop_cross_idx={eng.first_chop_cross_idx}  first_chop_cross_px={eng.first_chop_cross_px:.2f}")
        print(f"  confirm_source={eng.confirm_source}")
        print(f"  declared={eng.declared}")
        if eng.normal_highs:
            latest = eng.normal_highs[-1]
            print(f"  latest normal_high: idx={latest.idx} px={latest.px:.2f} time={latest.time}")

# Check 10:14 and 10:15
print("\n--- Restoring state at 10:13 ---")
eng2 = FirstSwingEngine({"timeCap": "09:29"})
for g_idx, c in aug17:
    t = c.date[11:16]
    eng2.process_bar(c, g_idx)
    if t == "10:13" or t == "10:14" or t == "10:15":
        print(f"\n=== {t} (g_idx={g_idx}) ===")
        print(f"  hi={eng2.hi:.2f}  lo={eng2.lo:.2f}")
        print(f"  e_hi.px={eng2.e_hi.px:.2f}  e_lo.px={eng2.e_lo.px:.2f}")
        print(f"  locked_level={eng2.locked_level:.2f}")
        print(f"  dir={eng2.dir}  state={eng2.state}  dir_confirmed={eng2.dir_confirmed}")
        print(f"  first_chop_cross_idx={eng2.first_chop_cross_idx}")
        print(f"  sustain_streak={eng2.sustain_streak}  sustain_bars={eng2.sustain_bars}")
        print(f"  declared={eng2.declared}  confirm_source={eng2.confirm_source}")
        if eng2.normal_highs:
            latest = eng2.normal_highs[-1]
            print(f"  latest normal_high: idx={latest.idx} px={latest.px:.2f} time={latest.time}")
        if eng2.pivot_highs:
            latest = eng2.pivot_highs[-1]
            print(f"  latest pivot_high: idx={latest.idx} px={latest.px:.2f} time={latest.time}")
