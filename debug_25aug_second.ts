import { readFileSync } from 'fs';
import { FirstSwingEngine } from './frontend/src/lib/firstswing';
const lines = readFileSync('data/nifty_1min.csv','utf8').split('\n').slice(1);
const all = lines.filter(l=>l.trim()&&l.includes('2025-08-25')).map(l=>{ const p=l.split(','); return {date:p[0], open:+p[2], high:+p[3], low:+p[4], close:+p[5]}});
const eng1 = new FirstSwingEngine();
all.forEach((c,i)=> eng1.processBar(c as any, i));
console.log('first swing', eng1.dir, eng1.startTime, eng1.startPx, eng1.endTime, eng1.endPx, eng1.confirmedAtTime, eng1.breakMarks);
const endIdx = eng1.endIdx;
console.log('endIdx', endIdx, all[endIdx]?.date);
const seedIdx = endIdx + 1;
console.log('seedIdx', seedIdx, all[seedIdx]?.date);
const eng2 = new FirstSwingEngine();
const seedC = all[seedIdx];
eng2.resetWithCandle(seedC as any, seedIdx);
for(let i=seedIdx+1;i<all.length;i++){
  const c = all[i];
  eng2.processBar(c as any, i);
  if(c.date.includes('10:2')||c.date.includes('10:3')){
    console.log(`${c.date.slice(11,16)} H${c.high} L${c.low} marks${JSON.stringify(eng2.breakMarks)} dir${eng2.dir} armed${(eng2 as any).armed} eLoPivot${(eng2 as any).eLoPivot?.px} eHiPivot${(eng2 as any).eHiPivot?.px} decl${eng2.declared}`);
  }
  if(eng2.declared && c.date.includes('10:3')){
    // break
  }
}
console.log('second swing', eng2.dir, eng2.startTime, eng2.startPx, eng2.endTime, eng2.endPx, eng2.confirmedAtTime, eng2.breakMarks);

// also test feeding from 09:28 vs from endIdx
const eng3 = new FirstSwingEngine();
const start28 = all.findIndex(c=>c.date.includes('09:28:00'));
console.log('--- feed from 09:28 inclusive as first bar ---');
all.slice(start28).forEach((c,i)=>{
  const gIdx = start28 + i;
  eng3.processBar(c as any, gIdx);
});
console.log('feed from 09:28', eng3.dir, eng3.startTime, eng3.endTime, eng3.breakMarks);

// also test second swing with feed from seed inclusive (no reset, just process from seed)
const eng4 = new FirstSwingEngine();
for(let i=seedIdx;i<all.length;i++){
  eng4.processBar(all[i] as any, i);
  if(all[i].date.includes('10:3') && eng4.breakMarks.length){
    console.log(`feed inclusive ${all[i].date.slice(11,16)} marks${JSON.stringify(eng4.breakMarks)}`);
  }
}
console.log('feed inclusive second', eng4.dir, eng4.startTime, eng4.endTime, eng4.breakMarks);
