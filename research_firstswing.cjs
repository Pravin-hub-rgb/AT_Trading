// TEMP research: flow-first-swing vs window-classifier across all days
const fs = require("fs");
const L = fs.readFileSync("data/nifty_5min.csv", "utf8").split("\n").slice(1);
const days = new Map();
for (const ln of L) {
  const p = ln.split(",");
  if (p.length < 7) continue;
  const d = p[0].slice(0, 10);
  if (!days.has(d)) days.set(d, []);
  days.get(d).push({ t: p[0].slice(11, 16), o: +p[2], h: +p[3], l: +p[4], c: +p[5] });
}
let tot=0,noFlip=0,earlyF=0,lateF=0,agree=0,dis=0;
const mags=[],earlyMags=[],disEx=[],timeBuckets={"<0930":0,"0930-45":0,"0945-10":0,">10":0};
for (const [d,bars] of days) {
  if (bars.length < 20) continue;
  tot++;
  const win=bars.filter(b=>b.t<"09:45"); const w=win.length?win:[bars[0]];
  let hiI=0,loI=0; w.forEach((b,i)=>{ if(b.h>w[hiI].h)hiI=i; if(b.l<w[loI].l)loI=i; });
  let wd;
  if(hiI>loI)wd="buying"; else if(hiI<loI)wd="selling";
  else { const net=w[w.length-1].c-w[0].o; wd=net>0?"buying":net<0?"selling":(w[0].c>=w[0].o?"buying":"selling"); }
  const b0=bars[0];
  let dir=b0.c>=b0.o?1:-1;
  let stamp=dir===1?b0.h:b0.l;
  let seedExt=stamp;
  let pHi=bars[0].h,pLo=bars[0].l;
  let flip=null;
  for(let i=1;i<bars.length;i++){
    const b=bars[i]; const g=b.c>=b.o;
    const seq=[[g?b.l:b.h,true],[g?b.h:b.l,false]];
    for(const [sv,isLow] of seq){
      if(flip)break;
      if(isLow){
        if(dir===-1){ if(sv<stamp)stamp=sv; }
        else if(sv<pLo){ flip={t:b.t,to:"down"}; }
      } else {
        if(dir===1){ if(sv>stamp)stamp=sv; }
        else if(sv>pHi){ flip={t:b.t,to:"up"}; }
      }
    }
    pHi=b.h; pLo=b.l;
    if(flip)break;
  }
  if(!flip){noFlip++;continue;}
  const fd=flip.to==="down"?"buying":"selling";
  const mag=Math.abs(stamp-seedExt);
  mags.push(mag);
  const t=flip.t;
  if(t<"09:45"){earlyF++;earlyMags.push(mag);}else{lateF++;}
  if(t<"09:30")timeBuckets["<0930"]++;
  else if(t<"09:45")timeBuckets["0930-45"]++;
  else if(t<"10:00")timeBuckets["0945-10"]++;
  else timeBuckets[">10"]++;
  if(fd===wd)agree++;else{dis++;if(disEx.length<12)disEx.push(d+" win="+wd+" flow="+fd+" flip@"+t+" mag="+mag.toFixed(1));}
}
console.log("total days:",tot);
console.log("flip <09:45:",earlyF,"� 09:45-10:00:",timeBuckets["0945-10"],"� >10:00:",timeBuckets[">10"],"� <09:30:",timeBuckets["<0930"],"� 09:30-45:",timeBuckets["0930-45"]);
console.log("no-flip all day:",noFlip);
const ms=mags.slice().sort((a,b)=>a-b);
function q(p){return ms[Math.floor(ms.length*p)].toFixed(1)}
console.log("magnitude � median:",q(0.5),"� p25:",q(0.25),"� p75:",q(0.75),"� min:",ms[0].toFixed(1),"� max:",ms[ms.length-1].toFixed(1));
const em=earlyMags.slice().sort((a,b)=>a-b);
if(em.length){const eq=(p)=>em[Math.floor(em.length*p)].toFixed(1);console.log("EARLY(<9:45) n="+em.length,"� median-mag:",eq(0.5),"� under10pts:",em.filter(x=>x<10).length,"� under20pts:",em.filter(x=>x<20).length);}
console.log("direction agree:",agree,"� disagree:",dis,"("+(100*dis/Math.max(agree+dis,1)).toFixed(1)+"%)");
console.log("disagreement samples:");
disEx.forEach(x=>console.log("  "+x));
