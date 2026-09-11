import sys; sys.path.insert(0, '.')
from src.btc.btc_routes import _load_window, _compute_swings
from src.btc.btc_engine import _collect_signals

htf_win, _ = _load_window('1h', None, 'BTCUSDT')
htf_candles, htf_flow = htf_win
htf_swings = _compute_swings(htf_flow, 'b2_vs_flip_chop', min_bars=20)

sigs_flip = _collect_signals(htf_swings, 'flip', skip_first=True, selection='stream', candles=htf_candles)
sigs_dec = _collect_signals(htf_swings, 'decisive', skip_first=True, selection='stream', candles=htf_candles)
sigs_b2 = _collect_signals(htf_swings, 'b2', skip_first=True, selection='stream', candles=htf_candles)
print(f'HTF signals: flip={len(sigs_flip)} dec={len(sigs_dec)} b2={len(sigs_b2)}')

if sigs_b2:
    s = sigs_b2[0]
    b = s['bar']
    entry = htf_candles[b]['close']
    sl = s['swing_start_px']
    d = s['dir']
    nc = len(htf_candles)
    print(f'b2 first: bar={b}/{nc} dir={d} entry={entry} sl={sl}')
    if d == 1:
        risk = entry - sl
        print(f'  long: sl < entry? {sl < entry}, risk={risk:.2f}, min_risk={0.0005*entry:.2f}')
    else:
        risk = sl - entry
        print(f'  short: sl > entry? {sl > entry}, risk={risk:.2f}, min_risk={0.0005*entry:.2f}')
else:
    print('No b2 signals')
    # Check if there are ANY signals at all from any break type
    for bt in ['flip', 'decisive', 'b2']:
        for s in sigs_flip[:3] if bt == 'flip' else sigs_dec[:3] if bt == 'decisive' else []:
            pass
    # Maybe check what signals look like from the raw swings
    print(f'Swings with breaks:')
    for i, sw in enumerate(htf_swings[:5]):
        breaks = sw.get('breaks', [])
        print(f'  swing[{i}] dir={sw["dir"]} breaks={len(breaks)}')
        for br in breaks[:2]:
            print(f'    break: idx={br.get("idx")} kind={br.get("kind")}')
