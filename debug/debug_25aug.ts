import { readFileSync } from 'fs';
import { FirstSwingEngine } from './frontend/src/lib/firstswing';
const lines = readFileSync('data/nifty_1min.csv','utf8').split('\n').slice(1);
const all = lines.filter(l=>l.trim()&&l.includes('2025-08-25')).map(l=>{ const p=l.split(','); return {date:p[0], open:+p[2], high:+p[3], low:+p[4], close:+p[5]}});
const startIdx = all.findIndex(c=>c.date.includes('09:28:00'));
const candles = all.slice(startIdx);
console.log('feeding from', candles[0].date);
const eng = new FirstSwingEngine();
candles.forEach((c,i)=>{
  const gIdx = startIdx + i;
  eng.processBar(c as any, gIdx);
  if(c.date.includes('10:2')||c.date.includes('10:3')){
    console.log(`${c.date.slice(11,16)} H${c.high} L${c.low} | B1? marks${JSON.stringify(eng.breakMarks)} dir${eng.dir} armed${(eng as any).armed} eLoPivot${(eng as any).eLoPivot?.px} eHiPivot${(eng as any).eHiPivot?.px} decl${eng.declared}`);
  }
  if(eng.declared && c.date.includes('10:3')){
    console.log('declared at', c.date, eng.breakMarks);
  }
});
console.log('final', eng.breakMarks, eng.dir, eng.startTime, eng.endTime, eng.declared);
