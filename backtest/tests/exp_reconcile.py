import sys, os, pickle
# NOTE: this walk recurses through pathlib. Do NOT fix a RecursionError here by
# raising sys.setrecursionlimit - that overflows the C stack and kills the process
# with 0xc00000fd instead of raising. Use backtest/tests/_bigstack.run instead.
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
for p in ("backtest", "backtest/tests", "backtest/sweeps", "backend"):
    sys.path.insert(0,str(ROOT/p))
sys.path.append(str(ROOT/"backend"/"src"))
with open(Path(os.environ["TEMP"])/"at_datacache.pkl","rb") as f: d=pickle.load(f)
import src.btc.engines.htf_ltf.v18_streak_halt as M
from src.btc.btc_routes import _trade_costs
from engine.v18_params import get_v18_params, V18_ENGINE
from exp_concurrency_guard import pf
p=dict(get_v18_params("BTCUSDT_BYBIT")); p.update(V18_ENGINE); p["chop_thresh"]=58.0
kw={k:p[k] for k in ["sl_buf_atr","ext_stop_r","chop_thresh","atr_low_thresh","atr_high_thresh","mode","cooldown_bars","max_consecutive_losses","htf_rr","window_end"] if k in p}
print("live params:",kw)
print()
for name,sw in (("sw20 = golden chain",d["sw20"]),("sw10 = my earlier run",d["sw10"])):
    r=M.simulate_htf_ltf_streak_halt(d["c1h"],sw,d["c15"],d["sw15"],fine_ltf=d["fine"],**kw)
    tr=[t for t in r["ltf_trades"] if t.get("outcome")!="open"]
    rs=[float(t["r_multiple"]) for t in tr]
    c2,_=_trade_costs(tr,p["fee_pct"],0.0,p["entry_slip_pct"],p["exit_slip_pct"])
    g=sum(rs); nn=g-c2
    print("  %-26s n=%3d gross=%+7.2f net=%+7.2f PF=%.3f"%(name,len(rs),g,nn,pf(rs)))
print()
print("  golden test claims:          n=351 gross=+211.72 net=+137.33 PF=1.907")

