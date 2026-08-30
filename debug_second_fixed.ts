import { readFileSync } from 'fs';
import { FirstSwingEngine } from './frontend/src/lib/firstswing';
import { computeFsV2Results, computeSecondSwingResults } from './frontend/src/lib/flowline';

const lines = readFileSync('data/nifty_1min.csv','utf8').split('\n').slice(1);
const candles = lines.filter(l=>l.trim()&&l.includes('2026-08-28')).map(l=>{
  const p=l.split(',');
  return {date: p[0], open:+p[2], high:+p[3], low:+p[4], close:+p[5]};
});
const fs1 = computeFsV2Results(candles);
console.log('fs1', JSON.stringify(fs1,null,2));
const second = computeSecondSwingResults(candles, fs1);
console.log('second FIXED', JSON.stringify(second,null,2));
// also test with relative cap
const relSecond = computeSecondSwingResults(candles, fs1, {timeCap: '09:41'});
console.log('second RELATIVE cap 09:41', JSON.stringify(relSecond,null,2));
