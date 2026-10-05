import { readFileSync } from 'fs';
import { FirstSwingEngine } from './frontend/src/lib/firstswing';
const lines = readFileSync('data/nifty_1min.csv','utf8').split('\n').slice(1);
const all = lines.filter(l=>l.trim()&&l.includes('2025-08-25')).map(l=>{ const p=l.split(','); return {date:p[0], open:+p[2], high:+p[3], low:+p[4], close:+p[5]}});
const eng1 = new FirstSwingEngine();
all.forEach((c,i)=> eng1.processBar(c as any, i));
const endIdx = eng1.endIdx;
console.log('first end', endIdx, all[endIdx]?.date, eng1.endPx);
const seedIdx = endIdx + 1;
const eng2 = new FirstSwingEngine();
const seedC = all[seedIdx];
eng2.resetWithCandle(seedC as any, seedIdx);
for(let i=seedIdx+1;i<all.length;i++){
  const c = all[i];
  eng2.processBar(c as any, i);
  if(c.date.includes('10:29')||c.date.includes('10:30')||c.date.includes('10:31')||c.date.includes('10:32')){
    const eLoPrev = (eng2 as any).eLoPrev.px;
    const eHiPrev = (eng2 as any).eHiPrev.px;
    const eLoPivPrev = (eng2 as any).eLoPivotPrev.px;
    const eHiPivPrev = (eng2 as any).eHiPivotPrev.px;
    const armed = (eng2 as any).armed;
    const state = (eng2 as any).state;
    console.log(`${c.date.slice(11,16)} H${c.high} L${c.low} eLoPrev${eLoPrev} eLoPivPrev${eLoPivPrev} eHiPrev${eHiPrev} eHiPivPrev${eHiPivPrev} armed${armed} state${state} dir${eng2.dir} marks${JSON.stringify(eng2.breakMarks)}`);
  }
  if(c.date.includes('10:33')) break;
}
