import { readFileSync } from 'fs';
import { FirstSwingEngine } from './frontend/src/lib/firstswing';
const lines = readFileSync('data/nifty_1min.csv','utf8').split('\n').slice(1);
const all = lines.filter(l=>l.trim()&&l.includes('2025-08-25')).map(l=>{ const p=l.split(','); return {date:p[0], open:+p[2], high:+p[3], low:+p[4], close:+p[5]}});
const seedIdx = all.findIndex(c=>c.date.includes('10:27:00'));
console.log('seed', all[seedIdx]?.date, all[seedIdx]);
const eng = new FirstSwingEngine();
for(let i=seedIdx;i<all.length;i++){
  eng.processBar(all[i] as any, i);
  if(all[i].date.includes('10:2')||all[i].date.includes('10:3')||all[i].date.includes('10:4')){
    console.log(`${all[i].date.slice(11,16)} H${all[i].high} L${all[i].low} marks${JSON.stringify(eng.breakMarks)} dir${eng.dir} armed${(eng as any).armed} decl${eng.declared}`);
  }
  if(all[i].date.includes('10:35')) break;
}
console.log('final', eng.breakMarks);
