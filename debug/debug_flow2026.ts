import { readFileSync } from 'fs';
import { WalkerEngine } from './frontend/src/lib/flowline';
const lines = readFileSync('data/nifty_1min.csv','utf8').split('\n').slice(1);
const all = lines.filter(l=>l.includes('2026-08-25')).map(l=>{ const p=l.split(','); return {date:p[0], open:+p[2], high:+p[3], low:+p[4], close:+p[5]}});
const w = new WalkerEngine();
const pivots: any[] = [];
all.forEach((c,i)=> w.processBar(c as any, i).forEach(p=> pivots.push(p)));
console.log(pivots.filter(p=> p.time.includes('10:') && parseInt(p.time.split(':')[1])>=27 && parseInt(p.time.split(':')[1])<=35).map(p=> `${p.time} ${p.kind} ${p.px}`));
