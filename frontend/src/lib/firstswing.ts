// DEPRECATED — Single source of truth is backend/src/firstswing.py
// This file is kept as a stub so legacy debug scripts (fsdebug*.ts, fsv2.test.ts)
// still type-check. Production code (page.tsx) now fetches via POST /api/swings/first_second.
// Do not import SwingEngine from here — use backend.
export class SwingEngine {
  // stub properties to satisfy legacy scripts
  [key: string]: any;
  dir: any = null;
  locked: any = false;
  declared: any = false;
  candTime: any = "";
  endTime: any = "";
  endPx: any = 0;
  confirmedAtTime: any = "";
  confirmSource: any = null;
  startTime: any = "";
  startPx: any = 0;
  candPx: any = 0;
  breakMarks: any[] = [];
  confirmedAtIdx: any = -1;
  lastConfirmHit: any = null;
  startIdx: any = -1;
  endIdx: any = -1;
  constructor(..._args: any[]) {}
  processBar(..._args: any[]) {}
  debugPools() { return {} as any; }
}
export const FirstSwingEngine = SwingEngine;
export type FsBreakMark = { idx: number; time: string; kind: "B1" | "B2" | "FLIP"; dir: "up" | "down"; px: number };
export type FlowSegment = { dir: "B" | "S"; startIdx: number; startPx: number; endIdx: number; endPx: number };
export type FsV2Result = any;
export function computeSwingResults(..._args: any[]): any[] { return []; }
export function computeFsV2Results(..._args: any[]): any[] { return []; }
export function computeFsV2Declared(..._args: any[]): any[] { return []; }
