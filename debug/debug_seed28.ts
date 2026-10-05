import { readFileSync } from 'fs';
import { FirstSwingEngine } from './frontend/src/lib/firstswing';
const lines = readFileSync('data/nifty_1min.csv','utf8').split('\n').slice(1);
const candles = lines.filter(l=>l.includes('2026-08-28')).map(l=>{const p=l.split(','); return {date:p[0], open:+p[2], high:+p[3], low:+p[4], close:+p[5]}});
const eng = new FirstSwingEngine();
const seedIdx = 13; // 09:28
const seedC = candles[seedIdx];
console.log('seed', seedC);
eng.resetWithCandle(seedC, seedIdx);
for(let i=seedIdx+1;i<candles.length;i++){
  eng.processBar(candles[i], i);
  console.log(candles[i].date.slice(11,16)+' marks '+JSON.stringify(eng.breakMarks)+' dir '+eng.dir+' armed '+ (eng as any).armed+' declared '+eng.declared+ ' start '+eng.startTime+' end '+eng.candTime);
  if(eng.declared){ console.log('declared at',candles[i].date, eng.breakMarks, eng.startTime, eng.startPx, eng.endTime, eng.endPx); break;}
  if(i>seedIdx+12) break;
}
