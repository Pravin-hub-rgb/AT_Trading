"""DIAGNOSTIC v2: link trades to swings BY TIME, not by index.

swing_no and swing_index are different counters, and fs_at_time carries only
HH:MM. But fs_at_idx is an index into the 1h candles, so a swing's FS moment is
candles_1h[fs_at_idx].ts. For each booked entry, the swing that confirms it is
the first swing in the SAME direction whose FS lands at or after the entry -
which is exactly the relationship method/FS_TIME_GEOMETRY.md measured as "FS always
lands after the entry".

Read-only. The engine is not modified.
"""
import sys, json, pathlib
from collections import defaultdict
R=pathlib.Path(r"c:\Users\Pravin\Desktop\main\AT_Trading")
for s in ("backtest/tests","backtest","backend"): sys.path.insert(0,str(R/s))
sys.path.insert(0,str(R))
import exp_equity_quality as E
import run_experiment as re_
from src.btc.btc_routes import _trade_costs
BASE=dict(re_.BP); BASE.update(mode="atr_high",atr_high_thresh=0.65,atr_low_thresh=0.35,
 sl_buf_atr=0.01,chop_thresh=58.0,cooldown_bars=8,max_consecutive_losses=3,
 ext_stop_r=3.0,exp_partial_r=0.0,exp_persist=7,window_end="exit",pivot_rule="leg",exp_mltf=True)
sim=re_.build_module()
def sweep(scope):
    data=E.load_scope(scope); c1h=data["c1h"]; sw=data["sw10"]
    out=sim(data["c1h"],data["sw10"],data["c15"],data["sw15"],fine_ltf=data["fine"],**BASE)
    tr=out["ltf_trades"]; _trade_costs(tr,0.055,2,0.005,0.01,0.01)
    # FS moments: (ts, dir, swing, break_kind, had_b2_before_fs)
    fs=[]
    for s in sw:
        i=int(s.get("fs_at_idx",-1))
        if 0<=i<len(c1h): fs.append((int(c1h[i]["ts"]), 1 if s.get("dir")=="up" else -1, s))
    fs.sort(key=lambda x:x[0])
    rows=[]
    for t in tr:
        if t.get("outcome")=="open": continue
        et=int(t.get("entry_ts") or 0); xt=int(t.get("exit_ts") or 0)
        td=1 if t.get("dir")=="long" else -1
        cand=[f for f in fs if f[0]>=et and f[1]==td]
        if not cand: rows.append({"linked":0}); continue
        fts,_,s=cand[0]
        # did THIS swing produce a break at/before our entry? (B2/FLIP in its breaks)
        brk=[b for b in (s.get("breaks") or []) if int(b.get("idx",-1))>=0]
        bk_at_or_before=any(int(b.get("idx",-1)) is not None for b in brk)
        rows.append({"linked":1,
          "r":float(t.get("r_multiple",0.0))-float(t.get("cost_r",0.0)),
          "same_dir":1, "gap_h":(fts-et)/3600.0,
          "open_at_fs":1 if xt>fts else 0,
          "bk":t.get("break_kind"),
          "swing_bk":s.get("break_kind"),
          "n_breaks":len(brk)})
    return rows
def rep(name,sel):
    n=len(sel)
    if not n: print("  %-32s n=   0"%name); return
    r=sum(x["r"] for x in sel)
    print("  %-32s n=%4d  net %+8.2fR  R/trade %+.3f"%(name,n,r,r/n))
ALL={}
for scope in ("is","oos"):
    rows=sweep(scope)
    L=[x for x in rows if x["linked"]]
    print("=== %s: %d closed trades, %d linked to a confirming swing ==="%(scope.upper(),len(rows),len(L)))
    print("  -- FS DIRECTION (vs entry) --")
    rep("FS same direction",[x for x in L if x["same_dir"]])
    print("  -- FS TIME GAP --")
    for lo,hi,nm in ((0,4,"gap 0-4h"),(4,12,"gap 4-12h"),(12,24,"gap 12-24h"),(24,1e9,"gap 24h+")):
        rep(nm,[x for x in L if lo<=x["gap_h"]<hi])
    print("  -- STILL OPEN AT FS --")
    rep("still open at FS",[x for x in L if x["open_at_fs"]])
    rep("already closed by FS",[x for x in L if not x["open_at_fs"]])
    print("  -- OPEN-AT-FS x GAP --")
    for lo,hi,gn in ((0,12,"gap<12h"),(12,1e9,"gap>=12h")):
        rep("open, %s"%gn,[x for x in L if x["open_at_fs"] and lo<=x["gap_h"]<hi])
        rep("closed, %s"%gn,[x for x in L if not x["open_at_fs"] and lo<=x["gap_h"]<hi])
    print("  -- ENTRY BREAK KIND --")
    for bk in ("B2","FLIP"):
        rep("entry %s"%bk,[x for x in L if x["bk"]==bk])
    ALL[scope]=rows
    print()
(R/"backtest"/"tests"/"_fs_diagnostic_results.json").write_text(
    json.dumps({k:{"n":len(v),"linked":sum(1 for x in v if x["linked"])} for k,v in ALL.items()},indent=1),encoding="utf-8")
