import { readFileSync } from 'fs';
import { FirstSwingEngine } from './frontend/src/lib/firstswing';
const lines5 = readFileSync('data/nifty_5min.csv','utf8').split('\n').slice(1);
const all5 = lines5.filter(l=>l.trim()&&l.includes('2025-08-25')).map(l=>{ const p=l.split(','); return {date:p[0], open:+p[2], high:+p[3], low:+p[4], close:+p[5]}});
const eng1 = new FirstSwingEngine();
all5.forEach((c,i)=> eng1.processBar(c as any, i));
console.log('5min first', eng1.dir, eng1.startTime, eng1.endTime, eng1.breakMarks, eng1.confirmedAtTime);
const endIdx = eng1.endIdx;
const seedIdx = endIdx + 1;
console.log('seed', all5[seedIdx]?.date);
const eng2 = new FirstSwingEngine();
for(let i=seedIdx;i<all5.length;i++){
  eng2.processBar(all5[i] as any, i);
  if(all5[i].date.includes('10:30')||all5[i].date.includes('10:31')||all5[i].date.includes('10:35')){
    console.log(`${all5[i].date.slice(11,16)} marks${JSON.stringify(eng2.breakMarks)} dir${eng2.dir} armed${(eng2 as any).armed}`);
  }
}
console.log('5min second', eng2.dir, eng2.startTime, eng2.endTime, eng2.breakMarks, eng2.confirmedAtTime);
