import sys, bisect, json
from pathlib import Path
ROOT = Path(r'c:\Users\Pravin\Desktop\main\AT_Trading')
sys.path.insert(0, str(ROOT / 'backtest/tests'))
sys.path.insert(0, str(ROOT / 'backtest'))
sys.path.insert(0, str(ROOT / 'backend'))
from run_experiment import get_data, BP, EXPERIMENTS, fund
from src.btc.btc_routes import _trade_costs
import test_experiments_craze as craze

def causal_chain(full_chain, slice_lo_full, slice_hi_full):
    out = []
    for si, s in enumerate(full_chain):
        seg = s.get('seg') or {}
        c_idx = s.get('confirmed_at_idx')
        c_idx = int(c_idx) if c_idx is not None else 10 ** 9
        s_idx = int(seg.get('start_idx', 10 ** 9))
        if s_idx > slice_hi_full:
            break
        if s_idx < slice_lo_full:
            continue
        e_idx = int(seg.get('end_idx', -1))
        c = dict(s)
        newseg = dict(seg)
        newseg['start_idx'] = s_idx - slice_lo_full
        nb = []
        for b in (s.get('breaks') or []):
            bi = int(b['idx'])
            if slice_lo_full <= bi <= slice_hi_full:
                b2 = dict(b)
                b2['idx'] = bi - slice_lo_full
                nb.append(b2)
        c['breaks'] = nb
        c['swing_index'] = len(out)
        if c_idx <= slice_hi_full:
            newseg['end_idx'] = (e_idx - slice_lo_full) if e_idx >= 0 else -1
            c['seg'] = newseg
            c['confirmed_at_idx'] = c_idx - slice_lo_full
            c['confirmed_at_time'] = (s.get('confirmed_at_time', '') or '')[:19]
            c['forming'] = False
        else:
            clamped = min(max(e_idx, s_idx), slice_hi_full) if e_idx >= 0 else slice_hi_full
            newseg['end_idx'] = clamped - slice_lo_full
            c['seg'] = newseg
            c.pop('confirmed_at_idx', None)
            c.pop('confirmed_at_time', None)
            c['forming'] = True
        out.append(c)
    return out

data = get_data()
sim = craze.build_module()
c15 = data['c15']
ts15 = [int(c['ts']) for c in c15]
params = {**BP, **EXPERIMENTS['champion_multi_sw10']['params']}
batch = sim(data['c1h'], data['sw10'], data['c15'], data['sw15'], fine_ltf=data['fine'], **params)['ltf_trades']
rs = [float(t['r_multiple']) for t in batch]
c2, _ = _trade_costs(batch, 0.055, 0.0, 0.005, 0.01)
batch_net = sum(rs) - c2 - fund(batch)
repro_idx = set()
for i, t in enumerate(batch):
    E = int(t['entry_ts'])
    if E - ts15[0] < 30 * 86400:
        continue
    hi_ts = E + 2 * 900
    lo = max(0, bisect.bisect_left(ts15, E - 30 * 86400))
    hi = min(len(c15) - 1, bisect.bisect_right(ts15, hi_ts) - 1)
    if hi - lo < 300:
        continue
    sl15 = c15[lo:hi + 1]
    chain15 = causal_chain(data['sw15'], lo, hi)
    r = sim(data['c1h'], data['sw10'], sl15, chain15, fine_ltf=data['fine'], **params)
    if any(x['dir'] == t['dir'] and E <= int(x['entry_ts']) <= hi_ts for x in r['ltf_trades']):
        repro_idx.add(i)
    if (i + 1) % 100 == 0:
        print('  %d/%d repro=%d' % (i + 1, len(batch), len(repro_idx)), flush=True)

repro_rs = [rs[i] for i in sorted(repro_idx)]
repro_tr = [batch[i] for i in sorted(repro_idx)]
c2r, _ = _trade_costs(repro_tr, 0.055, 0.0, 0.005, 0.01)
repro_net = sum(repro_rs) - c2r - fund(repro_tr)
n_elig = len([t for t in batch if int(t['entry_ts']) - ts15[0] >= 30*86400])
print('REPRO: %d/%d (%.1f%%)' % (len(repro_idx), n_elig, 100.0*len(repro_idx)/max(1,n_elig)))
print('BATCH NET: %+.1f (%d trades)' % (batch_net, len(batch)))
print('LIVE-EXPECTED NET: %+.1f (%d trades)' % (repro_net, len(repro_tr)))
print('DECLARATION-LAG COST: %+.1fR' % (batch_net - repro_net))
json.dump({'repro_idx': sorted(repro_idx), 'batch_net': batch_net, 'repro_net': repro_net},
          open(str(ROOT / 'backtest/tests/_onepass_v2_result.json'), 'w'))
