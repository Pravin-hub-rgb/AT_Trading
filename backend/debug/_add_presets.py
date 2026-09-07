import io

p = "backend/src/btc/btc_routes.py"
s = io.open(p, encoding="utf-8").read()

# 1. renumber labels (descending to avoid collisions)
ren = [
    ('"label": "#10 FLIP Quality \u00b7 15m"', '"label": "#12 FLIP Quality \u00b7 15m"'),
    ('"label": "#9 Trailing Max R \u00b7 15m"', '"label": "#11 Trailing Max R \u00b7 15m"'),
    ('"label": "#8 FLIP + 15m Bias \u00b7 15m"', '"label": "#10 FLIP + 15m Bias \u00b7 15m"'),
    ('"label": "#7 Baseline (ship) \u00b7 15m"', '"label": "#9 Baseline (ship) \u00b7 15m"'),
    ('"label": "#6 Sniper 3R \u00b7 15m"', '"label": "#7 Sniper 3R \u00b7 15m"'),
    ('"label": "#4 Flip Trail 30 \u00b7 1h"', '"label": "#6 Flip Trail 30 \u00b7 1h"'),
]
for old, new in ren:
    assert old in s, old
    s = s.replace(old, new)

# 2. insert the two new 1h presets (after flip30's entry = before sniper)
new_blocks = '''    {"key": "decisive1h30",
     "label": "#4 Decisive Trail 30 \u00b7 1h", "entry_break": "decisive", "sl_mode": "swing",
     "rr_target": 3.0, "trailing": "swing", "breakeven_r": 0.0,
     "min_bars": 30, "bias": "off", "regime": "off"},
    {"key": "flip1h20t",
     "label": "#8 Flip Trail 20 \u00b7 1h", "entry_break": "flip", "sl_mode": "swing",
     "rr_target": 3.0, "trailing": "swing", "breakeven_r": 0.0,
     "min_bars": 20, "bias": "off", "regime": "off"},
'''
anchor = '    {"key": "sniper",'
i = s.find(anchor)
assert i > 0, "sniper anchor not found"
s = s[:i] + new_blocks + s[i:]

io.open(p, "w", encoding="utf-8", newline="\n").write(s)
print("backend presets updated")
