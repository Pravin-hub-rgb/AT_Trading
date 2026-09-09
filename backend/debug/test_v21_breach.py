"""v21 experiment: "breach is breach" — B2 vs pre-bar corner instead of same-bar-updated corner.

Baseline semantics (firstswing.py _step): the walker seals pivots BEFORE the B2 check
runs, so a bar that sweeps-and-reverses (e.g. Jan 5 2023 19:30) replaces the corner
with its own low and its breach of the B1 extreme is swallowed.

Variant semantics: B2 compares the bar's low/high against e_lo_pivot_prev / e_hi_pivot_prev
(the corner as the PREVIOUS bar ended). Everything else (gap rule, b1_bar_idx, flips,
chop, sustain) untouched. Flip-back-as-B2 path also untouched (dir already confirmed).

Runs: baseline v18 (sanity +331.1R), variant on 15m chain only, variant on both 15m+1h.
"""
import sys, inspect, textwrap
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import src.firstswing as fs
from src.firstswing import SwingEngine
from src.btc.btc_config import load_btc_df
from src.btc.btc_routes import _compute_swings, _load_fine_1m
from src.btc.engines.htf_ltf import v18_streak_halt as v18
from src.walker import FlowCandle

OUT = Path(__file__).resolve().parent / "_v21_breach_results.txt"
def log(s):
    print(s, flush=True)
    with open(OUT, "a", encoding="utf-8") as f:
        f.write(s + "\n")

open(OUT, "w").close()
log("=== v21 'breach is breach' experiment ===")

# ---------- build variant _step ----------
_src = textwrap.dedent(inspect.getsource(SwingEngine._step))
_marker = '    if self.dir == "down":\n        b2_fired = False'
_i = _src.find(_marker)
assert _i > 0, "marker not found"
_head, _tail = _src[:_i], _src[_i:]
_repls = [
    ("self.e_lo_pivot is not None", "self.e_lo_pivot_prev is not None", 1),
    ("self.lo < self.e_lo_pivot.px", "self.lo < self.e_lo_pivot_prev.px", 1),
    ("p = self.e_lo_pivot", "p = self.e_lo_pivot_prev", 1),
    ("self.e_hi_pivot is not None", "self.e_hi_pivot_prev is not None", 1),
    ("self.hi > self.e_hi_pivot.px", "self.hi > self.e_hi_pivot_prev.px", 1),
    ("p = self.e_hi_pivot", "p = self.e_hi_pivot_prev", 1),
]
for a, b, want in _repls:
    n = _tail.count(a)
    assert n == want, f"pattern {a!r} found {n}x (want {want})"
    _tail = _tail.replace(a, b)
_ns = dict(fs.__dict__)
exec(compile(_head + _tail, "<step_variant>", "exec"), _ns)
PreBreachEngine = type("PreBreachEngine", (SwingEngine,), {"_step": _ns["_step"]})
log("variant engine built (6 surgical replacements verified)")

import src.btc.btc_swing as btc_swing  # noqa: E402  (imports SwingEngine by name)

# ---------- data ----------
def load_window(tf):
    df = load_btc_df(tf)
    candles, flow = [], []
    for row in df.itertuples():
        date = row.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        candles.append({"date": date, "ts": int(row.ts), "open": float(row.open), "high": float(row.high), "low": float(row.low), "close": float(row.close), "volume": 0, "oi": 0})
        flow.append(FlowCandle(date=date, open=float(row.open), high=float(row.high), low=float(row.low), close=float(row.close)))
    return candles, flow

c1h, f1h = load_window("1h")
c15, f15 = load_window("15m")
sw1h = _compute_swings(f1h, "continuous", min_bars=20)
sw15_base = _compute_swings(f15, "continuous", min_bars=50)
t0 = min(c1h[0]["ts"], c15[0]["ts"]); t1 = max(c1h[-1]["ts"], c15[-1]["ts"])
fine = _load_fine_1m(t0, t1)
log("data loaded")

# ---------- variant chains ----------
btc_swing.SwingEngine = PreBreachEngine  # the name compute_btc_swings actually resolves
fs.SwingEngine = PreBreachEngine
try:
    sw15_v = _compute_swings(f15, "continuous", min_bars=50)
    sw1h_v = _compute_swings(f1h, "continuous", min_bars=20)
finally:
    btc_swing.SwingEngine = SwingEngine
    fs.SwingEngine = SwingEngine

# sanity: the Jan 5 19:30 case must now fire B2 (break times are "HH:MM" — map idx->date)
def d15(i):
    return c15[i]["date"][:16]

def show_around(sw, candles, label):
    shown = 0
    for s in sw:
        si, ei = s["seg"]["start_idx"], s["seg"]["end_idx"]
        if not (0 <= si < len(candles)) or not ("2023-01-05" <= candles[si]["date"][:10] <= "2023-01-06"):
            continue
        log(f"  [{label}] swing#{s['swing_index']} {s['break_kind']} "
            f"{candles[si]['date'][5:16]}({s['seg']['start_px']:.2f}) -> "
            f"{candles[ei]['date'][5:16]}({s['seg']['end_px']:.2f}) :: "
            + " | ".join(f"{x['kind']}@{candles[x['idx']]['date'][5:16]} px={x['px']:.2f}" for x in s["breaks"]))
        shown += 1
        if shown >= 4:
            break

log("\n--- Jan 5-6 swings (your swing 9) ---")
show_around(sw15_base, c15, "BASE")
show_around(sw15_v, c15, "VARIANT")

# chain diff
def kinds(sw):
    from collections import Counter
    return Counter(s["break_kind"] for s in sw)
log(f"\n15m chain: base swings={len(sw15_base)} {dict(kinds(sw15_base))}")
log(f"15m chain: variant swings={len(sw15_v)} {dict(kinds(sw15_v))}")
log(f"1h chain: base={len(sw1h)} {dict(kinds(sw1h))} | variant={len(sw1h_v)} {dict(kinds(sw1h_v))}")

# ---------- v18 runs ----------
def run(sw15, sw1h_, label):
    r = v18.simulate_htf_ltf_streak_halt(
        c1h, sw1h_, c15, sw15, fine_ltf=fine,
        sl_buf_atr=0.25, ext_stop_r=1.5, mode="b2_vs_flip_chop",
        cooldown_bars=20, max_consecutive_losses=5, chop_thresh=61.8)
    tr = r["ltf_trades"]
    rs = [t["r_multiple"] for t in tr]
    net = sum(rs)
    from collections import defaultdict
    yr = defaultdict(float); yn = defaultdict(int)
    for t in tr:
        y = t["entry_date"][:4]; yr[y] += t["r_multiple"]; yn[y] += 1
    ys = " ".join(f"{y}:{yr[y]:+.1f}R/{yn[y]}t" for y in sorted(yr))
    log(f"\n{label}: trades={len(tr)} net={net:+.1f}R worst={min(rs):+.2f}")
    log(f"  yearly: {ys}")
    return net

log("\n=== v18 A/B ===")
nets = {}
nets["BASELINE          "] = run(sw15_base, sw1h, "BASELINE          ")
nets["VARIANT 15m only  "] = run(sw15_v, sw1h, "VARIANT 15m only  ")
nets["VARIANT 15m + 1h  "] = run(sw15_v, sw1h_v, "VARIANT 15m + 1h  ")

# bootstrap significance of the 15m-only delta
import random
def trades_of(sw15, sw1h_):
    r = v18.simulate_htf_ltf_streak_halt(
        c1h, sw1h_, c15, sw15, fine_ltf=fine,
        sl_buf_atr=0.25, ext_stop_r=1.5, mode="b2_vs_flip_chop",
        cooldown_bars=20, max_consecutive_losses=5, chop_thresh=61.8)
    return [t["r_multiple"] for t in r["ltf_trades"]]

tb = trades_of(sw15_base, sw1h)
tv = trades_of(sw15_v, sw1h)
random.seed(42)
deltas = []
for _ in range(2000):
    sb = sum(random.choice(tb) for _ in tb)
    sv = sum(random.choice(tv) for _ in tv)
    deltas.append(sv - sb)
deltas.sort()
mean_d = sum(deltas) / len(deltas)
sd = (sum((d - mean_d) ** 2 for d in deltas) / (len(deltas) - 1)) ** 0.5
t_stat = (sum(tv) - sum(tb)) / (sd * (len(deltas) ** 0.5)) if sd > 0 else float("inf")
p5, p95 = deltas[int(0.05 * len(deltas))], deltas[int(0.95 * len(deltas))]
log(f"\nbootstrap delta (variant15m - base): mean={mean_d:+.1f}R t={t_stat:.2f} 90%CI=[{p5:+.1f}, {p95:+.1f}]")
log("\ndone")