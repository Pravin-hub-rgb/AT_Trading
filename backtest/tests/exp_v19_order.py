import sys, pickle, json, os
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest","backtest/tests","backtest/sweeps","backend"):
    sys.path.insert(0, str(ROOT / p))
sys.path.append(str(ROOT / "backend" / "src"))
import src.btc.btc_engine as _be
from src.btc.engines.htf_ltf.v19_champion import simulate_htf_ltf_streak_halt as V19

TRUE = _be._collect_signals
print("TRUE _collect_signals id =", hex(id(TRUE)))

def run(rule, csl=0):
    # EXPLICIT install + UNINSTALL every time. No one-shot patch leaks.
    if rule == "origin":
        def w(*a, **k):
            k["pivot_rule"] = "origin"; return TRUE(*a, **k)
        _be._collect_signals = w
    else:
        _be._collect_signals = TRUE
    active = "origin-wrapper" if rule == "origin" else ("TRUE" if _be._collect_signals is TRUE else "OTHER!")
    d = pickle.load(open(Path(os.environ["TEMP"]) / "at_datacache.pkl", "rb"))
    r = V19(d["c1h"], d["sw10"], d["c15"], d["sw15"], fine_ltf=d["fine"], exp_causal_sl=csl,
        sl_buf_atr=0.01, ext_stop_r=3.0, mode="atr_high", chop_thresh=58.0,
        cooldown_bars=8, max_consecutive_losses=3, htf_rr=3.0, window_end="exit")["ltf_trades"]
    cl = [x for x in r if x.get("outcome") != "open"]
    _be._collect_signals = TRUE          # ALWAYS restore
    g = sum(float(x["r_multiple"]) for x in cl)
    return len(cl), round(g, 2), active

seq = sys.argv[1].split(",")
for rule in seq:
    csl = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    n, g, active = run(rule, csl)
    print(f"  {rule:8s} csl={csl} active={active:16s} -> {n} trades / {g}R")
