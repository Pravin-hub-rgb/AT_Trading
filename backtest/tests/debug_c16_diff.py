"""
Compare retro trades before and after C16 fix.
Run with the C16 fix applied (current state) vs original retroactive mode.
"""
import sys, os, pickle, types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest", "backtest/tests", "backtest/sweeps", "backend"):
    sys.path.insert(0, str(ROOT / p))
sys.path.append(str(ROOT / "backend" / "src"))

from experiment_registry import EXPERIMENTS, BP
from run_experiment import net_r
from exp_concurrency_guard import pf
import test_experiments_craze as tc
from exp_concurrency_guard import load_unseen
from test_4_new_concepts import load_fine_1m as lfo

SRC = (ROOT / "backend/src/btc/engines/htf_ltf/v19_champion.py").read_text(encoding="latin-1")
m = types.ModuleType("causal_probe")
m.__file__ = "causal_probe.py"
exec(compile(SRC, "causal_probe.py", "exec"), m.__dict__)

BASE = {k: v for k, v in {**BP, **EXPERIMENTS["champion_multi_sw10"]["params"]}.items()
        if k not in {"exp_mltf", "exp_persist", "exp_partial_r"}}
import inspect
sig = set(inspect.signature(m.simulate_htf_ltf_streak_halt).parameters)
pr = {k: v for k, v in BASE.items() if k in sig}

with open(Path(os.environ["TEMP"]) / "at_datacache.pkl", "rb") as f:
    d = pickle.load(f)

# Run retro (exp_causal_sl=0) - current state with C16 fix applied
r = m.simulate_htf_ltf_streak_halt(
    d["c1h"], d["sw10"], d["c15"], d["sw15"], fine_ltf=d["fine"], exp_causal_sl=0, **pr)
tr = [t for t in r["ltf_trades"] if t.get("outcome") != "open"]

print(f"Current (C16 applied) retro: n={len(tr)} net={sum(float(t['r_multiple']) for t in tr):.2f}R")

# Save current trades
current_trades = {t['entry_ts']: t for t in tr}

# Now let's check the original engine without C16 fix
# We need to revert the C16 fix in btc_engine.py temporarily

print("\nNow checking the 2024-01-18 13:30 trade...")
for t in tr:
    if t['entry_date'] == '2024-01-18 13:30:00':
        print(f"Found: {t}")
        break
else:
    print("NOT FOUND - this is the vanished trade!")

# Let's also look at all trades on 2024-01-18
print("\nAll trades on 2024-01-18:")
for t in tr:
    if t['entry_date'].startswith('2024-01-18'):
        print(f"  {t['entry_date']} {t['dir']} {t['break_kind']} entry={t['entry_price']} sl={t['sl']} R={t['r_multiple']}")

# Now let's find trades that are different from the original 500
# We need to run without C16 fix. Let me check if we can run the original engine.
# First, let's see what the original retroactive mode would produce by 
# manually setting sl_pivot = sig["swing_start_px"] in the engine

print("\n\nLet's check the 2024-01-18 13:30 SHORT trade details from the original data...")
# Load the original data and check the signal
from src.btc.btc_engine import _collect_signals, CandleStore
from src.btc.btc_swing import compute_btc_swings
from src.walker import FlowCandle

sw15 = tc._compute_swings(d["f15"], "continuous", min_bars=50)
c15 = d["c15"]
store = CandleStore(c15)
sigs = _collect_signals(sw15, "decisive", skip_first=True, selection="stream", candles=c15)

# Find the 2024-01-18 13:30 signal
for s in sigs:
    if s['bar'] == '2024-01-18 13:30:00':
        print(f"Signal: {s}")
        bar = store.pos(s['bar'])
        print(f"  bar index: {bar}")
        if bar >= 0 and bar < len(c15):
            c = c15[bar]
            print(f"  candle: O={c['open']} H={c['high']} L={c['low']} C={c['close']}")
        print(f"  swing_start_px: {s['swing_start_px']}")
        print(f"  swing_no: {s['swing_no']}")
        print(f"  kind: {s['kind']}")
        print(f"  dir: {s['dir']}")
        break

# Check the swing details
swings = d["sw15"]
for s in swings:
    if s.get("swing_index") == 1465:  # approximate
        print(f"\nSwing 1465: dir={s.get('dir')} start_idx={s['seg'].get('start_idx')} end_idx={s['seg'].get('end_idx')} start_px={s['seg'].get('start_px')} end_px={s['seg'].get('end_px')}")
        print(f"  breaks: {s.get('breaks')}")
        for b in s.get('breaks', []):
            if b.get('time') == '2024-01-18 13:30:00':
                print(f"  Break: {b}")
                break