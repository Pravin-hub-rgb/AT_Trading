"""v23 CANDIDATE A/B: skip LTF entries whose mark fired while the PREVIOUS
swing was still unconfirmed (the 'churn state' from test_pre_fs_marks).
Baseline = v18 (330 trades, +331.1R gross). Single variable: LTF signal filter.
HTF windows unchanged."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from test_pre_fs_marks import c1h, f1h, c15, f15, sw1h, sw15, fine, tr  # baseline trades

import src.btc.btc_engine as beng
_orig_cs = beng._collect_signals

def patched(swings, *a, **k):
    sigs = _orig_cs(swings, *a, **k)
    conf = {s["swing_index"]: int(s.get("confirmed_at_idx", -1)) for s in swings}
    out = []
    for sg in sigs:
        pc = conf.get(sg["swing_no"] - 1, -1)
        if sg["swing_no"] >= 1 and (pc < 0 or sg["bar"] < pc):
            continue  # prev swing unconfirmed at fire time -> skip
        out.append(sg)
    return out

beng._collect_signals = patched
from src.btc.engines.htf_ltf.v18_streak_halt import simulate_htf_ltf_streak_halt
res2 = simulate_htf_ltf_streak_halt(c1h, sw1h, c15, sw15, fine_ltf=fine,
    sl_buf_atr=0.25, ext_stop_r=1.5, mode="b2_vs_flip_chop",
    cooldown_bars=20, max_consecutive_losses=5)
tr2 = [t for t in res2["ltf_trades"] if t["outcome"] != "open"]


def stats(ts, label):
    gross = sum(t["r_multiple"] for t in ts)
    gw = sum(t["r_multiple"] for t in ts if t["r_multiple"] > 0)
    gl = -sum(t["r_multiple"] for t in ts if t["r_multiple"] <= 0)
    pf = gw / gl if gl > 0 else float("inf")
    win = sum(1 for t in ts if t["r_multiple"] > 0)
    eq = peak = dd = 0.0
    for t in ts:
        eq += t["r_multiple"]; peak = max(peak, eq); dd = max(dd, peak - eq)
    yr = {}
    for t in ts:
        y = str(t["entry_date"])[:4]
        yr[y] = yr.get(y, 0.0) + t["r_multiple"]
    net = gross - 0.398 * len(ts)  # same per-trade cost as v18 (~0.4R)
    print(f"{label:<10} {len(ts):>4}t  gross {gross:+8.1f}R  ~net {net:+8.1f}R"
          f"  PF {pf:.2f}  win {100*win/max(1,len(ts)):.1f}%  maxDD {dd:.1f}R"
          f"  | per-year " + " ".join(f"{y}:{v:+.0f}" for y, v in sorted(yr.items())))


stats(tr, "v18 base")
stats(tr2, "v23 skip")
