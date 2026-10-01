import sys, pickle, os
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest","backtest/tests","backtest/sweeps","backend"):
    sys.path.insert(0, str(ROOT / p))
sys.path.append(str(ROOT / "backend" / "src"))
import src.btc.btc_engine as _be
from src.btc.engines.htf_ltf.v19_champion import simulate_htf_ltf_streak_halt as V19

TRUE = _be._collect_signals

def v7mod():
    import src.btc.engines.v7_timecap as m
    return m

def label(fn):
    if fn is TRUE:
        return "TRUE"
    return getattr(fn, "_arm", "WRAPPER?")

def load():
    with open(Path(os.environ["TEMP"]) / "at_datacache.pkl", "rb") as f:
        return pickle.load(f)

def run(rule, csl=0):
    if rule == "origin":
        def w(*a, **k):
            k["pivot_rule"] = "origin"; return TRUE(*a, **k)
        w._arm = "WRAPPER"
        _be._collect_signals = w
    else:
        _be._collect_signals = TRUE
    ltf = label(_be._collect_signals)
    try:
        htf_pre = label(v7mod()._collect_signals)
    except Exception:
        htf_pre = "(v7 not imported yet)"
    d = load()
    r = V19(d["c1h"], d["sw10"], d["c15"], d["sw15"], fine_ltf=d["fine"], exp_causal_sl=csl,
        sl_buf_atr=0.01, ext_stop_r=3.0, mode="atr_high", chop_thresh=58.0,
        cooldown_bars=8, max_consecutive_losses=3, htf_rr=3.0, window_end="exit")["ltf_trades"]
    cl = [x for x in r if x.get("outcome") != "open"]
    htf = label(v7mod()._collect_signals)
    _be._collect_signals = TRUE
    g = sum(float(x["r_multiple"]) for x in cl)
    print(f"  {rule:7s} csl={csl}  LTF(:439)={ltf:8s} HTF(v7:29)={htf:8s} "
          f"[before run: {htf_pre:18s}] -> {len(cl)} trades / {round(g,2)}R")

print("seq:", sys.argv[1])
for rule in sys.argv[1].split(","):
    run(rule, int(sys.argv[2]) if len(sys.argv) > 2 else 0)
