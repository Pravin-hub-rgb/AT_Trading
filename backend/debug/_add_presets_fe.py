import io

p = "frontend/src/lib/btcMaster.ts"
s = io.open(p, encoding="utf-8").read()

# 1. renumber (descending)
ren = [
    ('label: "#10 FLIP Quality \u00b7 15m"', 'label: "#12 FLIP Quality \u00b7 15m"'),
    ('label: "#9 Trailing Max R \u00b7 15m"', 'label: "#11 Trailing Max R \u00b7 15m"'),
    ('label: "#8 FLIP + 15m Bias \u00b7 15m"', 'label: "#10 FLIP + 15m Bias \u00b7 15m"'),
    ('label: "#7 Baseline (ship) \u00b7 15m"', 'label: "#9 Baseline (ship) \u00b7 15m"'),
    ('label: "#6 Sniper 3R \u00b7 15m"', 'label: "#7 Sniper 3R \u00b7 15m"'),
    ('label: "#4 Flip Trail 30 \u00b7 1h"', 'label: "#6 Flip Trail 30 \u00b7 1h"'),
]
for old, new in ren:
    assert old in s, old
    s = s.replace(old, new)

# 2. update the two existing 1h refs to the 1m-fill numbers
s = s.replace(
    'ref: "1h \u00b7 All: 72 tr \u00b7 55.6% win \u00b7 +82.2R NET (1m-precise fills)"',
    'ref: "1h \u00b7 All: 73 tr \u00b7 56.2% win \u00b7 +85.0R NET (1m-precise fills)"')
s = s.replace(
    'ref: "1h \u00b7 All: 128 tr \u00b7 25.0% win \u00b7 +74.2R NET (1m-precise fills)"',
    'ref: "1h \u00b7 All: 152 tr \u00b7 18.5% win \u00b7 +60.6R NET (1m-precise fills)"')

# 3. insert new presets
b4 = '''  {
    value: "decisive1h30",
    label: "#4 Decisive Trail 30 \u00b7 1h",
    hint: "1h decisive variant - B2+FLIP on mb30 legs, swing-trail, +80R NET after 1m-precise costs. 220 trades.",
    desc: [
      "RANK #4. 1-HOUR candles: entries on ALL decisive breaks (B2 + FLIP) of minBars-30 legs, SL = swing start, swing trailing, breakeven off.",
      "1m-precise fills, full 20-month window: 220 trades / 18.7% win / +95.4R base -> +80.4R NET.",
      "More trades than the flip-only 1h variants - smoother equity, still fee-light at 1h.",
    ],
    ref: "1h \u00b7 All: 220 tr \u00b7 18.7% win \u00b7 +80.4R NET (1m-precise fills)",
    bestTf: "1h",
    preset: {
      entryBreak: "decisive",
      slMode: "swing",
      rrTarget: 3,
      trailing: "swing",
      breakevenR: 0,
      minBars: 30,
      bias: "off",
      regime: "off",
      feePct: 0.05,
      slippagePts: 2,
    },
  },
'''
b8 = '''  {
    value: "flip1h20t",
    label: "#8 Flip Trail 20 \u00b7 1h",
    hint: "1h flip mb20 with swing-trailing - +49R NET, 170 trades. The trail variant of the 55% win-rate config.",
    desc: [
      "RANK #8. 1-HOUR candles: FLIP breaks on minBars-20 legs, swing trailing (no fixed target), breakeven off.",
      "1m-precise fills, full window: 170 trades / 20.1% win / +64.9R base -> +49.3R NET.",
      "Weaker than its fixed-3R sibling (#3) on 1h - the trail exits early on 1h legs. Kept for comparison.",
    ],
    ref: "1h \u00b7 All: 170 tr \u00b7 20.1% win \u00b7 +49.3R NET (1m-precise fills)",
    bestTf: "1h",
    preset: {
      entryBreak: "flip",
      slMode: "swing",
      rrTarget: 3,
      trailing: "swing",
      breakevenR: 0,
      minBars: 20,
      bias: "off",
      regime: "off",
      feePct: 0.05,
      slippagePts: 2,
    },
  },
'''

a5 = '  {\n    value: "flip30",'
i = s.find(a5)
assert i > 0, "flip30 anchor not found"
s = s[:i] + b4 + s[i:]

a9 = '  {\n    value: "baseline",'
i = s.find(a9)
assert i > 0, "baseline anchor not found"
s = s[:i] + b8 + s[i:]

io.open(p, "w", encoding="utf-8", newline="\n").write(s)
print("frontend presets updated")
