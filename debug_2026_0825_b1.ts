import { readFileSync } from 'fs';
import { computeFsV2Results } from './frontend/src/lib/flowline';
const lines = readFileSync('data/nifty_1min.csv','utf8').split('\n').slice(1);
const all = lines.filter(l=>l.includes('2026-08-25')).map(l=>{ const p=l.split(','); return {date:p[0], open:+p[2], high:+p[3], low:+p[4], close:+p[5]}});
const res = computeFsV2Results(all);
console.log(JSON.stringify(res[0].breaks,null,2));
console.log('seg', res[0].seg, 'conf', res[0].confIdx, all[res[0].confIdx]?.date);
all.slice(0,80).forEach((c,i)=> {
  if(c.date.includes('09:2')||c.date.includes('10:2')||c.date.includes('10:3'))
    console.log(i, c.date.slice(11,16), 'H',c.high,'L',c.low);
});
