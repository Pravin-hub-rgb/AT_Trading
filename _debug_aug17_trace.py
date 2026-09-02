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

# Run engine with detailed state trace
eng = FirstSwingEngine({"timeCap": "09:29"})
for g_idx, c in aug17:
    eng.process_bar(c, g_idx)
    t = c.date[11:16]
    if t >= "09:00" and t <= "10:20":
        state = eng.state
        dc = eng.dir_confirmed
        dcl = eng.declared
        b1 = eng.b1_bar_idx if eng.b1_bar_idx >= 0 else -1
        b2 = eng.b2_pivot.idx if eng.b2_pivot else -1
        chop = eng.first_chop_cross_idx
        sus = eng.sustain_streak
        print(f"  {t}  H:{c.high:.2f} L:{c.low:.2f}  state={state}  dir={eng.dir}  confirmed={dc}  declared={dcl}  b1={b1}  b2={b2}  chop={chop}  sus={sus}")
