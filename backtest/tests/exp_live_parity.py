import sys, os, pickle, types, inspect
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
for p in ("backtest", "backtest/tests", "backtest/sweeps", "backend"):
    sys.path.insert(0,str(ROOT/p))
sys.path.append(str(ROOT/"backend"/"src"))
from engine.v18_params import V18, SYMBOL_PARAMS, V18_ENGINE
import src.btc.engines.htf_ltf.v18_streak_halt as S
live={**V18,**SYMBOL_PARAMS["BTCUSDT"],**V18_ENGINE}
sig=set(inspect.signature(S.simulate_htf_ltf_streak_halt).parameters)
print("LIVE PARITY: does live_loop.py run the same engine as the champion?")
print()
print("  live_loop.py:35 imports simulate_htf_ltf_streak_halt from v18")
print("  engine file:", Path(inspect.getfile(S.simulate_htf_ltf_streak_halt)).name)
print()
print("  live params NOT accepted by the engine (silently ignored):")
for k in sorted(live):
    if k not in sig: print("     %-18s = %r"%(k,live[k]))
print()
print("  live params the engine DOES accept: %d of %d"%(len([k for k in live if k in sig]),len(live)))
print()
print("  consequence: the live bot hardcodes rr_target=3R via")
print("  the engine default. fee_pct / slippage are NOT engine inputs -")
print("  they are applied by the backtest cost model, not the simulator.")