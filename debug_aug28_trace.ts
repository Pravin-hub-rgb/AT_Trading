import { readFileSync } from "fs";
import { FirstSwingEngine } from "./frontend/src/lib/firstswing";

const lines = readFileSync("data/nifty_1min.csv", "utf8").split("\n").slice(1);
const candles = lines
  .map((l) => l.split(","))
  .filter((p) => p.length >= 7 && p[0].startsWith("2026-08-28"))
  .map((p) => ({
    date: p[0],
    open: +p[2],
    high: +p[3],
    low: +p[4],
    close: +p[5],
  }));

// Patch processBar to log state
const origProcessBar = FirstSwingEngine.prototype.processBar;
const origStep = (FirstSwingEngine.prototype as any).step.bind(FirstSwingEngine.prototype);
const origLock = (FirstSwingEngine.prototype as any).lock.bind(FirstSwingEngine.prototype);
const origFlip = (FirstSwingEngine.prototype as any).flip.bind(FirstSwingEngine.prototype);
const origConfirm = (FirstSwingEngine.prototype as any).confirm.bind(FirstSwingEngine.prototype);
const origCheckChop = (FirstSwingEngine.prototype as any).checkChop.bind(FirstSwingEngine.prototype);

let globalIdx = 0;
(FirstSwingEngine.prototype as any).processBar = function(c: any, gIdx: number) {
  const t = c.date.slice(11, 16);
  const beforeCap = t < "09:29";
  const declared = this.declared;
  const state = this.state;
  const dir = this.dir;
  const dirConfirmed = this.dirConfirmed;
  const sameSide = this.sameSideBreaks;
  
  origProcessBar.call(this, c, gIdx);
  
  if (t >= "09:15" && t <= "09:35") {
    const eHiP = (this as any).eHiPivotPrev;
    const eLoP = (this as any).eLoPivotPrev;
    const upBreak = c.high > eHiP.px;
    const downBreak = c.low < eLoP.px;
    console.log(
      `${t} idx=${gIdx} H=${c.high.toFixed(2)} L=${c.low.toFixed(2)} ` +
      `state=${state} dir=${dir} confirmed=${dirConfirmed} sameSide=${sameSide} ` +
      `eHiP=${eHiP.px.toFixed(2)}@${eHiP.time} eLoP=${eLoP.px.toFixed(2)}@${eLoP.time} ` +
      `upBreak=${upBreak} downBreak=${downBreak} ` +
      `declared=${this.declared}${this.declared ? " src="+this.confirmSource : ""}`
    );
  }
};

const engine = new FirstSwingEngine();
for (let i = 0; i < candles.length; i++) {
  engine.processBar(candles[i], i);
}

console.log("\nFinal declared:", engine.declared);
if (engine.declared) {
  console.log("  dir:", engine.dir);
  console.log("  start:", engine.startTime, engine.startPx);
  console.log("  end:", engine.endTime, engine.endPx);
  console.log("  source:", engine.confirmSource);
  console.log("  confirmedAt:", engine.confirmedAtTime);
}
