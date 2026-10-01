import sys, pickle, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest","backtest/tests","backtest/sweeps","backend"):
    sys.path.insert(0, str(ROOT / p))
sys.path.append(str(ROOT / "backend" / "src"))
arm = sys.argv[1]
csl = int(sys.argv[3]) if len(sys.argv) > 3 else 0
import src.btc.btc_engine as _be
from src.btc.engines.htf_ltf.v19_champion import simulate_htf_ltf_streak_halt as V19
d = pickle.load(open(Path(__import__("os").environ["TEMP"]) / "at_datacache.pkl", "rb"))
o = _be._collect_signals
if arm == "origin":
    def w(*a, **k):
        k["pivot_rule"] = "origin"; return o(*a, **k)
    _be._collect_signals = w
r = V19(d["c1h"], d["sw10"], d["c15"], d["sw15"], fine_ltf=d["fine"], exp_causal_sl=csl,
        sl_buf_atr=0.01, ext_stop_r=3.0, mode="atr_high", chop_thresh=58.0,
        cooldown_bars=8, max_consecutive_losses=3, htf_rr=3.0, window_end="exit")["ltf_trades"]
cl = [x for x in r if x.get("outcome") != "open"]
FEE, ES, XS, FUND = 0.055, 0.005, 0.01, 0.01
tot = 0.0
for x in cl:
    rk = abs(float(x["entry_price"]) - float(x["sl"]))
    if rk <= 0: continue
    e = abs(float(x["entry_price"])); xp = abs(float(x.get("exit_price", x["entry_price"])))
    tot += ((e + xp) * (FEE/100.0) + e*(ES/100.0) + xp*(XS/100.0)) / rk \
           + e * (FUND/100.0)/32.0 * int(x.get("bars_held", 0)) / rk
g = sum(float(x["r_multiple"]) for x in cl)
Path(sys.argv[2]).write_text(json.dumps({"arm": arm, "n": len(cl), "gross": round(g,2),
    "cost": round(tot,2), "net": round(g-tot,2),
    "keys": sorted({str(x.get("entry_ts")) for x in cl})}))
print(arm, "done")
