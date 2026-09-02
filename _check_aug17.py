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
print(f"17 Aug: {len(aug17)} bars, idx {aug17[0][0]} to {aug17[-1][0]}")

# Run engine
eng = FirstSwingEngine({"timeCap": "09:29"})
for g_idx, c in aug17:
    eng.process_bar(c, g_idx)
    t = c.date[11:16]
    if t >= "10:10" and t <= "10:20":
        state = eng.state
        dc = eng.dir_confirmed
        dir_ = eng.dir
        hi = eng.e_hi_prev.px
        lo = eng.e_lo_prev.px
        b1 = eng.b1_bar_idx
        arms = eng.armed
        print(f"  {t}  H:{c.high:.2f} L:{c.low:.2f}  dir={dir_}  confirmed={dc}  state={state}  armed={arms}  b1Bar={b1}  eHiPrev={hi:.2f}  eLoPrev={lo:.2f}")

print(f"\nFinal: day={eng.day}  dir={eng.dir}  declared={eng.declared}  confirmed={eng.confirmed_at_idx}  start={eng.start_idx}")
print(f"Breakmarks: {[(bm.kind, bm.time, bm.dir, bm.px) for bm in eng.break_marks]}")
