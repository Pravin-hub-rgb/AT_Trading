import { readFileSync } from 'fs';
import { FirstSwingEngine } from './frontend/src/lib/firstswing';
const lines = readFileSync('data/nifty_1min.csv','utf8').split('\n').slice(1);
const candles = lines.filter(l=>l.includes('2026-08-28')).map(l=>{const p=l.split(','); return {date:p[0], open:+p[2], high:+p[3], low:+p[4], close:+p[5]}});
for(const seedIdx of [12,13,14]){
  const eng = new FirstSwingEngine();
  eng.resetWithCandle(candles[seedIdx], seedIdx);
  console.log('--- seed idx '+seedIdx+' '+candles[seedIdx].date.slice(11,16)+' H '+candles[seedIdx].high+' L '+candles[seedIdx].low);
  for(let i=seedIdx+1;i<seedIdx+10;i++){
    eng.processBar(candles[i], i);
    if(eng.breakMarks.length) console.log('  '+candles[i].date.slice(11,16)+' marks '+JSON.stringify(eng.breakMarks)+' declared '+eng.declared);
    if(eng.declared) break;
  }
}
