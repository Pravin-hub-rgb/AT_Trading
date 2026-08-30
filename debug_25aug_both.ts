import { readFileSync } from 'fs';
import { FirstSwingEngine } from './frontend/src/lib/firstswing';
import { computeFsV2Results, computeSecondSwingResults } from './frontend/src/lib/flowline';
const lines = readFileSync('data/nifty_1min.csv','utf8').split('\n').slice(1);
const all = lines.filter(l=>l.includes('2025-08-25')).map(l=>{ const p=l.split(','); return {date:p[0], open:+p[2], high:+p[3], low:+p[4], close:+p[5]}});
const res = computeFsV2Results(all);
console.log('FIRST SWING 1min 25-Aug');
res.forEach(r=> console.log(`  B1/B2 ${JSON.stringify(r.breaks)} dir ${r.dir} seg ${r.seg?.startIdx}@${r.seg?.startPx} -> ${r.seg?.endIdx}@${r.seg?.endPx} FS@${r.confIdx} ${all[r.confIdx]?.date}`));
const second = computeSecondSwingResults(all, res);
console.log('SECOND SWING 1min 25-Aug (from 09:44 seed, since 1st ends 09:43)');
second.forEach(r=> console.log(`  B1/B2 ${JSON.stringify(r.breaks)} dir ${r.dir} seg ${r.seg?.startIdx}@${r.seg?.startPx} -> ${r.seg?.endIdx}@${r.seg?.endPx} FS@${r.confIdx} ${all[r.confIdx]?.date}`));

// Also test from 10:27 as second swing start (if 1st were at 10:26)
const eng = new FirstSwingEngine();
const startIdx = all.findIndex(c=>c.date.includes('10:27:00'));
console.log(`\nFEED FROM 10:27 as new 09:15 (your 10:26→10:27 case)`);
for(let i=startIdx;i<all.length;i++){
  eng.processBar(all[i] as any, i);
  if(all[i].date.includes('10:31')||all[i].date.includes('10:30')){
    console.log(`${all[i].date.slice(11,16)} marks ${JSON.stringify(eng.breakMarks)} dir ${eng.dir} decl ${eng.declared}`);
  }
  if(all[i].date.includes('10:35')) break;
}
console.log('from 10:27 B1/B2', eng.breakMarks, eng.dir, eng.startTime, eng.endTime);
