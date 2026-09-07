import io

p = "../frontend/src/lib/btcMaster.ts"
s = io.open(p, encoding="utf-8").read()

sniper = '''  {
    value: "sniper",
    label: "#4 Sniper 3R (15m)",
    hint: "Most selective - FLIP + minBars20 + streak regime, fixed 3R. +80R NET, 27.8% win, 252 trades.",
    desc: [
      "RANK #4. The most selective preset - FLIP breaks on minBars-20 swings + daily-color streak regime (3-1-1).",
      "Exit: fixed 1:3 target or SL, breakeven at +1R.",
      "1m-precise fills, full window: 252 trades / 27.8% win / +124.0R base -> +80.3R NET.",
      "Best per-trade discipline; capital-preservation profile.",
    ],
    ref: "15m: 252 tr / 27.8% win / +80.3R NET (1m-precise fills)",
    bestTf: "15m",
    preset: {
      entryBreak: "flip", slMode: "swing", rrTarget: 3,
      trailing: "off", breakevenR: 1, minBars: 20,
      bias: "15m", regime: "streak_311", feePct: 0.05, slippagePts: 2,
    },
  },
'''

anchor = '    label: "#5 Flip Fixed 3R (1h)",'
i = s.find(anchor)
assert i > 0, "#5 anchor not found"
# find the start of this preset object (the "  {" before the label)
obj_start = s.rfind("  {\n", 0, i)
assert obj_start > 0, "preset object start not found"
s = s[:obj_start] + sniper + s[obj_start:]

io.open(p, "w", encoding="utf-8", newline="\n").write(s)
print("sniper restored")
