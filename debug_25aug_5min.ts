import { readFileSync } from 'fs';
import { FirstSwingEngine } from './frontend/src/lib/firstswing';
const lines5 = readFileSync('data/nifty_5min.csv','utf8').split('\n').slice(1);
const all5 = lines5.filter(l=>l.trim()&&l.includes('2025-08-25')).map(l=>{ const p=l.split(','); return {date:p[0], open:+p[2], high:+p[3], low:+p[4], close:+p[5]}});
console.log('5min candles', all5.length);
all5.forEach(c=> console.log(c.date, c.high, c.low));
const eng = new FirstSwingEngine();
all5.forEach((c,i)=> eng.processBar(c as any, i));
console.log('5min first swing', eng.dir, eng.startTime, eng.startPx, eng.endTime, eng.endPx, eng.confirmedAtTime, eng.breakMarks);

const lines1 = readFileSync('data/nifty_1min.csv','utf8').split('\n').slice(1);
const all1 = lines1.filter(l=>l.trim()&&l.includes('2025-08-25')).map(l=>{ const p=l.split(','); return {date:p[0], open:+p[2], high:+p[3], low:+p[4], close:+p[5]}});
const eng1 = new FirstSwingEngine();
all1.forEach((c,i)=> eng1.processBar(c as any, i));
console.log('1min first swing', eng1.dir, eng1.startTime, eng1.startPx, eng1.endTime, eng1.endPx, eng1.confirmedAtTime, eng1.breakMarks);
