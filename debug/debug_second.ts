import { readFileSync } from 'fs';
import { FirstSwingEngine } from './frontend/src/lib/firstswing';
import { FsV2Engine, computeFsV2Results, computeSecondSwingResults } from './frontend/src/lib/flowline';

const lines = readFileSync('data/nifty_1min.csv','utf8').split('\n').slice(1);
const candles = lines.filter(l=>l.trim()&&l.includes('2026-08-28')).map(l=>{
  const p=l.split(',');
  return {date: p[0], open:+p[2], high:+p[3], low:+p[4], close:+p[5]};
});
console.log('candles', candles.length);
const fs1 = computeFsV2Results(candles);
console.log('fs1', JSON.stringify(fs1,null,2));
const second = computeSecondSwingResults(candles, fs1);
console.log('second', JSON.stringify(second,null,2));

// also test with FirstSwingEngine directly for second swing seeded at 09:27
async function testManual(){
  // find fs1 details
  const eng1 = new FirstSwingEngine();
  candles.forEach((c,i)=> eng1.processBar(c as any,i));
  console.log('eng1 declared', eng1.declared, eng1.dir, eng1.startTime, eng1.startPx, eng1.endTime, eng1.endPx, eng1.confirmedAtTime, eng1.breakMarks);
  
  // Now second swing manual using FsV2Engine reset as current computeSecondSwingResults does
  const fs1Seg = fs1[0]?.seg;
  const fs1Conf = fs1[0]?.confIdx;
  console.log('fs1Seg',fs1Seg,'conf',fs1Conf);
  if(fs1Seg){
    const eng2 = new FsV2Engine();
    eng2.reset(fs1Seg.endPx, fs1Seg.endIdx, candles[fs1Seg.endIdx].date.slice(11,16));
    const after = candles.map((c,i)=>({c,i})).filter(x=> x.i > fs1Conf);
    console.log('after length', after.length, 'first after', after[0]?.c.date, 'seed', fs1Seg.endPx, fs1Seg.endIdx);
    for(const it of after){
      eng2.processBar(it.c as any, it.i);
      if(eng2.declared) console.log('FsV2 eng2 declared at', it.c.date, eng2.dir, eng2.startIdx, eng2.startPx, eng2.endIdx, eng2.endPx, eng2.breakMarks);
    }
    console.log('FsV2 eng2 final', eng2.declared, eng2.dir, eng2.startTime, eng2.startPx, eng2.endTime, eng2.endPx, eng2.confirmedAtTime, eng2.breakMarks);
  }

  // manual using FirstSwingEngine reset if existed? We need to test what would happen if we use FirstSwingEngine with reset seeded at 09:27 and feed from 09:28
  // Since FirstSwingEngine has no reset, simulate by creating new engine and manually setting seed via processing seed bar?
  // We'll try to emulate reset by directly setting private fields via any
  const seedPx = fs1Seg!.endPx;
  const seedIdx = fs1Seg!.endIdx;
  const seedTime = candles[seedIdx].date.slice(11,16);
  console.log('seed',seedPx,seedIdx,seedTime);
  // Create new FirstSwingEngine and try to mimic reset by processing seed as first bar then subsequent
  // But we need proper reset method - for now test by feeding from 09:28 with walker fresh but with seed extremes
  // We'll hack: create engine, set barsSeen=1 etc.
  const { WalkerEngine } = await import('./frontend/src/lib/flowline');
  const eng3 = new FirstSwingEngine();
  // hack reset
  (eng3 as any).walker = new WalkerEngine();
  (eng3 as any).barsSeen = 1;
  (eng3 as any).t = seedTime;
  (eng3 as any).gIdx = seedIdx;
  (eng3 as any).eHi = {px: seedPx, idx: seedIdx, time: seedTime};
  (eng3 as any).eLo = {px: seedPx, idx: seedIdx, time: seedTime};
  (eng3 as any).eHiPrev = {px: seedPx, idx: seedIdx, time: seedTime};
  (eng3 as any).eLoPrev = {px: seedPx, idx: seedIdx, time: seedTime};
  (eng3 as any).eHiPivot = {px: seedPx, idx: seedIdx, time: seedTime};
  (eng3 as any).eLoPivot = {px: seedPx, idx: seedIdx, time: seedTime};
  (eng3 as any).eHiPivotPrev = {px: seedPx, idx: seedIdx, time: seedTime};
  (eng3 as any).eLoPivotPrev = {px: seedPx, idx: seedIdx, time: seedTime};
  (eng3 as any).armed = false;
  (eng3 as any).state = 'watch';
  (eng3 as any).dir = null;
  (eng3 as any).dirConfirmed = false;
  (eng3 as any).breakMarks = [];
  // feed from seedIdx+1
  for(let i=seedIdx+1;i<candles.length;i++){
    const c=candles[i];
    eng3.processBar(c as any,i);
    if(eng3.declared){
      console.log('FirstSwing eng3 declared at', c.date, eng3.dir, eng3.startTime, eng3.startPx, eng3.endTime, eng3.endPx, eng3.breakMarks, 'source',eng3.confirmSource);
      break;
    }
  }
  if(!eng3.declared) console.log('FirstSwing eng3 NOT declared, state', (eng3 as any).state, eng3.dir, (eng3 as any).armed, eng3.breakMarks);
  // also detailed trace
  console.log('--- detailed trace for eng3 ---');
  const eng4 = new FirstSwingEngine();
  (eng4 as any).walker = new WalkerEngine();
  (eng4 as any).barsSeen = 1;
  (eng4 as any).t = seedTime;
  (eng4 as any).gIdx = seedIdx;
  (eng4 as any).eHi = {px: seedPx, idx: seedIdx, time: seedTime};
  (eng4 as any).eLo = {px: seedPx, idx: seedIdx, time: seedTime};
  (eng4 as any).eHiPrev = {px: seedPx, idx: seedIdx, time: seedTime};
  (eng4 as any).eLoPrev = {px: seedPx, idx: seedIdx, time: seedTime};
  (eng4 as any).eHiPivot = {px: seedPx, idx: seedIdx, time: seedTime};
  (eng4 as any).eLoPivot = {px: seedPx, idx: seedIdx, time: seedTime};
  (eng4 as any).eHiPivotPrev = {px: seedPx, idx: seedIdx, time: seedTime};
  (eng4 as any).eLoPivotPrev = {px: seedPx, idx: seedIdx, time: seedTime};
  (eng4 as any).armed = false;
  (eng4 as any).state = 'watch';
  (eng4 as any).dir = null;
  (eng4 as any).dirConfirmed = false;
  (eng4 as any).breakMarks = [];
  for(let i=seedIdx+1;i<candles.length;i++){
    const c=candles[i];
    const before = {state:(eng4 as any).state, dir:eng4.dir, armed:(eng4 as any).armed, confirmed:(eng4 as any).dirConfirmed};
    eng4.processBar(c as any,i);
    const after = {state:(eng4 as any).state, dir:eng4.dir, armed:(eng4 as any).armed, confirmed:(eng4 as any).dirConfirmed, declared:eng4.declared};
    console.log(`${c.date.slice(11,16)} idx=${i} H=${c.high} L=${c.low} before=${JSON.stringify(before)} after=${JSON.stringify(after)} marks=${JSON.stringify(eng4.breakMarks)} cand=${eng4.candTime}@${eng4.candPx} source=${eng4.confirmSource}`);
    if(eng4.declared) break;
    if(i>seedIdx+20) break;
  }
}
testManual();
