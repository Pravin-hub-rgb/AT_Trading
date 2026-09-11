import sys; sys.path.insert(0, '.')
from src.btc.btc_routes import _load_window, _compute_swings
from src.btc.btc_engine import _collect_signals

htf_win, _ = _load_window('1h', None, 'BTCUSDT')
htf_candles, htf_flow = htf_win
htf_swings = _compute_swings(htf_flow, 'b2_vs_flip_chop', min_bars=20)

print(f'Swings: {len(htf_swings)}')
for i, sw in enumerate(htf_swings[:8]):
    si = sw.get("swing_index", "MISSING")
    brks = sw.get("breaks", [])
    kinds = [b["kind"] for b in brks]
    print(f'  [{i}] swing_index={si} dir={sw["dir"]} break_kind={sw.get("break_kind")} breaks={kinds}')

# Try without skip_first
sigs = _collect_signals(htf_swings, 'b2', skip_first=False, selection='stream', candles=htf_candles)
print(f'\nb2 signals (no skip): {len(sigs)}')
sigs2 = _collect_signals(htf_swings, 'flip', skip_first=False, selection='stream', candles=htf_candles)
print(f'flip signals (no skip): {len(sigs2)}')
sigs3 = _collect_signals(htf_swings, 'decisive', skip_first=False, selection='stream', candles=htf_candles)
print(f'decisive signals (no skip): {len(sigs3)}')
