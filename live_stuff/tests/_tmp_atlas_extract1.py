import json
from pathlib import Path

IS = json.loads(Path('live_stuff/tests/_thesis_htf_deep_atlas_is.json').read_text(encoding='utf-8'))
OOS = json.loads(Path('live_stuff/tests/_thesis_htf_deep_atlas_oos.json').read_text(encoding='utf-8'))

row = IS['variants']['champion_multi_sw10']['htf_rr3_cap16']

print('--- s69 nested structure (flip):')
f = row['s69_lane_compare']['flip']
for k, v in f.items():
    print('  ', k, ':', json.dumps(v, default=str)[:300])

print('--- s71 structure (flip):')
print(json.dumps(row['s71_sequence']['flip'], default=str)[:600])

print('--- s65 keys beyond by_lane_outcome:')
a = row['s65_anatomy']
for k, v in a.items():
    if k != 'by_lane_outcome':
        print('  ', k, ':', json.dumps(v, default=str)[:300])

print('--- s66 sl by_close_reason full h24:')
print(json.dumps(row['s66_reversion']['by_close_reason']['sl']['per_horizon'].get('h24'), default=str)[:700])
