import { readFileSync } from 'fs';
import { FirstSwingEngine } from './frontend/src/lib/firstswing';
import { computeFsV2Results, computeSecondSwingResults } from './frontend/src/lib/flowline';
const lines = readFileSync('data/nifty_1min.csv','utf8').split('\n').slice(1);
const all = lines.filter(l=>l.includes('2026-08-25')).map(l=>{ const p=l.split(','); return {date:p[0], open:+p[2], high:+p[3], low:+p[4], close:+p[5]}});
const res = computeFsV2Results(all);
console.log('first', res.map(r=> ({breaks:r.breaks, seg:r.seg, conf:r.confIdx, time:all[r.confIdx]?.date})));
const second = computeSecondSwingResults(all, res);
console.log('second', second.map(r=> ({breaks:r.breaks, seg:r.seg, conf:r.confIdx, time:all[r.confIdx]?.date})));
