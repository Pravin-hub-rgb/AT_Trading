import { readFileSync } from 'fs';
import { FirstSwingEngine } from './frontend/src/lib/firstswing';

const lines = readFileSync('data/nifty_1min.csv','utf8').split('\n').slice(1);
const all = lines.filter(l=>l.trim()&&l.includes('2026-08-28')).map(l=>{ const p=l.split(','); return {date:p[0], open:+p[2], high:+p[3], low:+p[4], close:+p[5]}});
const startIdx = all.findIndex(c=>c.date.includes('09:28:00'));
const candles = all.slice(startIdx); // from 09:28 onward
console.log('feeding from', candles[0].date, 'count', candles.length);
const eng = new FirstSwingEngine();
candles.forEach((c,i)=>{
  const gIdx = startIdx + i;
  eng.processBar(c as any, gIdx);
  const eHiPrev = (eng as any).eHiPrev.px.toFixed(2);
  const eLoPrev = (eng as any).eLoPrev.px.toFixed(2);
  const upB = c.high > (eng as any).eHiPrev.px;
  const dnB = c.low < (eng as any).eLoPrev.px;
  console.log(`${c.date.slice(11,16)} H${c.high} L${c.low} C${c.close} | eHiPrev${eHiPrev} eLoPrev${eLoPrev} upB${upB} dnB${dnB} | state${(eng as any).state} dir${eng.dir} armed${(eng as any).armed} conf${(eng as any).dirConfirmed} marks${JSON.stringify(eng.breakMarks)} decl${eng.declared} src${eng.confirmSource}`);
  if(eng.declared){
    console.log('DECLARED at', c.date, eng.dir, eng.startTime, eng.startPx, eng.endTime, eng.endPx, eng.confirmSource);
  }
});
if(!eng.declared) console.log('not declared', eng.dir, eng.breakMarks);
