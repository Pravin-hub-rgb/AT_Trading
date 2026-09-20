"""Full verdict: all 4 remaining experiments, fine fills, identity-gated.
1. (52,60,trail65) aggressive config
2. lb=50 + trail-mb sweep (50/65/80)
3. lb=50 on anchor (no B3)
4. Persist re-check at lb=50
"""
import sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

from test_experiments_craze import build_module, stats, BASE, \
    load_candles, _compute_swings, SWING, MB15, INSTRUMENT
from engine.v18_params import get_v18_params as _gvp
from src.btc.btc_routes import _load_fine_1m, _trade_costs

_g = _gvp(INSTRUMENT)
FEE = (_g["fee_pct"], _g["entry_slip_pct"], _g["exit_slip_pct"])
BP = dict(BASE)
BP["chop_thresh"] = 58.0  # production chop, not V18_ENGINE default 61.8

def net_of(tr):
    c2, _ = _trade_costs(tr, 0.055, 0.0, 0.005, 0.010, 0.01)
    return sum(float(t["r_multiple"]) for t in tr) - c2

def show(tag, s, net):
    print("  %-35s %3dt NET %+8.1f  WR %4.1f%%  DD %5.1f  H1 %+7.1f H2 %+7.1f  %s"
          % (tag, s["n"], net, s["wr"], s["dd"], s["h1"], s["h2"],
             {k: round(v, 1) for k, v in sorted(s["py"].items())}))


t0 = time.time()
(c15, f15), (c1h, f1h) = load_candles()
sw15 = _compute_swings(f15, "continuous", min_bars=MB15)
sw1h20 = _compute_swings(f1h, "continuous", min_bars=20)  # anchor
sw1h10 = _compute_swings(f1h, "continuous", min_bars=10)  # OPTIMAL/B3-OPT
fine = _load_fine_1m(min(c1h[0]["ts"], c15[0]["ts"]),
                     max(c1h[-1]["ts"], c15[-1]["ts"]), symbol=INSTRUMENT)

# Pre-build trail-mb chains
trail_chains = {}
for mb in [50, 65, 80]:
    trail_chains[mb] = _compute_swings(f15, "continuous", min_bars=mb)

sim = build_module()
print("Data loaded + swing chains ready (%0.0fs)" % (time.time() - t0))

# Pre-compute lb variants of 1h swings
# exp31_lb patches the chop lookback inside the engine, not the swings
# So we just pass exp31_lb=N and use sw1h10 for all

# =============================================
# IDENTITY GATE
# =============================================
print("\n=== IDENTITY GATE ===")
r_ship = __import__("src.btc.engines.htf_ltf.v18_streak_halt", fromlist=["simulate_htf_ltf_streak_halt"]).simulate_htf_ltf_streak_halt(
    c1h, sw1h20, c15, sw15, fine_ltf=[], **BP)
s_ship = stats(r_ship["ltf_trades"])
assert s_ship["n"] == 351 and abs(s_ship["gross"] - 211.7) < 0.5, "ANCHOR FAIL got %dt %+.1f" % (s_ship["n"], s_ship["gross"])
r0 = sim(c1h, sw1h20, c15, sw15, fine_ltf=[], **BP)
s0 = stats(r0["ltf_trades"])
assert s0["n"] == 351 and s0["rs"] == s_ship["rs"], "IDENTITY FAIL"
print("  OK (351t exact)\n")

# =============================================
# 1. (52,60,trail65) AGGRESSIVE CONFIG
# =============================================
print("=" * 70)
print("EXPERIMENT 1: (52,60,trail65) aggressive config vs conservative (55,50,trail50)")
print("=" * 70)

B3 = dict(b3_k=8, b3_mode="close")
P2 = dict(exp_persist=2)

# Conservative: (55,50,trail50) = current B3-OPT+halt6 lb50
kw_cons = {**BP, "chop_thresh": 55.0, **B3, **P2,
           "max_consecutive_losses": 6, "cooldown_bars": 10, "exp31_lb": 50}
r = sim(c1h, sw1h10, c15, sw15, fine_ltf=fine, swings_trail=trail_chains[50], **kw_cons)
tr = r["ltf_trades"] if isinstance(r, dict) else r
s = stats(tr)
show("(55,50,trail50) = conservative", s, net_of(tr))

# Aggressive: (52,60,trail65)
kw_agg = {**BP, "chop_thresh": 52.0, **B3, **P2,
          "max_consecutive_losses": 6, "cooldown_bars": 10, "exp31_lb": 60}
r = sim(c1h, sw1h10, c15, sw15, fine_ltf=fine, swings_trail=trail_chains[65], **kw_agg)
tr = r["ltf_trades"] if isinstance(r, dict) else r
s = stats(tr)
show("(52,60,trail65) = aggressive", s, net_of(tr))

# Also try (52,60,trail50) — does trail65 matter or is it chop/lb?
kw_mid = {**BP, "chop_thresh": 52.0, **B3, **P2,
          "max_consecutive_losses": 6, "cooldown_bars": 10, "exp31_lb": 60}
r = sim(c1h, sw1h10, c15, sw15, fine_ltf=fine, swings_trail=trail_chains[50], **kw_mid)
tr = r["ltf_trades"] if isinstance(r, dict) else r
s = stats(tr)
show("(52,60,trail50) — isolate chop/lb effect", s, net_of(tr))

# And (55,50,trail65) — does trail65 help at conservative chop/lb?
kw_t65 = {**BP, "chop_thresh": 55.0, **B3, **P2,
          "max_consecutive_losses": 6, "cooldown_bars": 10, "exp31_lb": 50}
r = sim(c1h, sw1h10, c15, sw15, fine_ltf=fine, swings_trail=trail_chains[65], **kw_t65)
tr = r["ltf_trades"] if isinstance(r, dict) else r
s = stats(tr)
show("(55,50,trail65) — isolate trail65 effect", s, net_of(tr))

# =============================================
# 2. lb=50 + TRAIL-MB SWEEP at B3-OPT
# =============================================
print("\n" + "=" * 70)
print("EXPERIMENT 2: trail-mb sweep at lb=50 (B3-OPT+halt6 cd10)")
print("=" * 70)

for tmb in [50, 65, 80]:
    kw = {**BP, "chop_thresh": 55.0, **B3, **P2,
          "max_consecutive_losses": 6, "cooldown_bars": 10, "exp31_lb": 50}
    r = sim(c1h, sw1h10, c15, sw15, fine_ltf=fine, swings_trail=trail_chains[tmb], **kw)
    tr = r["ltf_trades"] if isinstance(r, dict) else r
    s = stats(tr)
    show("trail-mb=%d" % tmb, s, net_of(tr))

# =============================================
# 3. lb=50 on ANCHOR (no B3)
# =============================================
print("\n" + "=" * 70)
print("EXPERIMENT 3: lb sweep on ANCHOR (no B3, production params)")
print("=" * 70)

for lb in [14, 20, 30, 40, 50, 60]:
    kw = {**BP}
    if lb != 14:
        kw["exp31_lb"] = lb
    r = sim(c1h, sw1h20, c15, sw15, fine_ltf=fine, **kw)
    tr = r["ltf_trades"] if isinstance(r, dict) else r
    s = stats(tr)
    show("anchor lb=%d" % lb, s, net_of(tr))

# =============================================
# 4. PERSIST RE-CHECK AT lb=50 (B3-OPT+halt6)
# =============================================
print("\n" + "=" * 70)
print("EXPERIMENT 4: persist re-check at lb=50 (B3-OPT+halt6 cd10)")
print("=" * 70)

for pers in [0, 2, 5]:
    kw = {**BP, "chop_thresh": 55.0, **B3,
          "max_consecutive_losses": 6, "cooldown_bars": 10, "exp31_lb": 50}
    if pers > 0:
        kw["exp_persist"] = pers
    r = sim(c1h, sw1h10, c15, sw15, fine_ltf=fine, **kw)
    tr = r["ltf_trades"] if isinstance(r, dict) else r
    s = stats(tr)
    show("persist=%d" % pers, s, net_of(tr))

# =============================================
# WALK-FORWARD on the aggressive config
# =============================================
print("\n" + "=" * 70)
print("WALK-FORWARD: (52,60,trail65) aggressive config")
print("=" * 70)

T0 = int(c15[0]["ts"])
T1 = int(c15[-1]["ts"]) + 900

kw_agg_wf = {**BP, "chop_thresh": 52.0, **B3, **P2,
             "max_consecutive_losses": 6, "cooldown_bars": 10, "exp31_lb": 60}
r = sim(c1h, sw1h10, c15, sw15, fine_ltf=fine, swings_trail=trail_chains[65], **kw_agg_wf)
tr = r["ltf_trades"] if isinstance(r, dict) else r

for pct, label in [(0.50, "50/50"), (0.66, "66/34"), (0.75, "75/25")]:
    cut = T0 + (T1 - T0) * pct
    train = [t for t in tr if t["outcome"] != "open" and int(t["entry_ts"]) < cut]
    test = [t for t in tr if t["outcome"] != "open" and int(t["entry_ts"]) >= cut]
    tr_net = net_of(train) if train else 0
    te_net = net_of(test) if test else 0
    print("  %s: train %dt %+7.1fR  test %dt %+7.1fR" % (label, len(train), tr_net, len(test), te_net))

print("\n" + "=" * 70)
print("DONE (%0.0fs)" % (time.time() - t0))
