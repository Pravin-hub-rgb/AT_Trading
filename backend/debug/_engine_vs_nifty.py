"""DEEP ENGINE AUDIT: BTC continuous chain vs Nifty per-day chain.

Same SwingEngine core classes — the question is whether the wrapping
(continuous vs per-day reseed) produces different swing/mark structure.

1) Bar-by-bar trace: the CONTINUOUS-chain engine instance that produced
   swing #21 (10-Jan) — it starts at bar 904 (= swing #20 end 903 + 1, the
   exact stitch compute_btc_swings uses).
2) Nifty whole-day chain on the SAME 10-Jan day (per-day reseed) — dump all.
3) Engine-vs-engine diff: first N=40 swings per day, same segments?
"""
import sys
import warnings

import pandas as pd

warnings.filterwarnings("ignore")
sys.path.insert(0, ".")

from src.btc.btc_config import load_btc_df  # noqa: E402
from src.firstswing import SwingEngine, compute_swing_results  # noqa: E402
from src.walker import FlowCandle  # noqa: E402
from src.btc.btc_swing import compute_btc_swings  # noqa: E402

OPTS = {"minBars": 50, "sustainBars": 7, "b2GapBars": 1, "timeCap": "00:00"}

df = load_btc_df("15m")
flow = [
    FlowCandle(date=x.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
               open=float(x.open), high=float(x.high),
               low=float(x.low), close=float(x.close))
    for x in df.itertuples()
]
out = []
P = out.append
P(f"candles={len(flow)}  {flow[0].date} -> {flow[-1].date}")


def hhmm(c):
    return c.date[11:16] if len(c.date) >= 16 else c.date


# ── 1) BAR-BY-BAR TRACE of the continuous-chain swing #21 engine ─────────────
P("")
P("=" * 78)
P("1) CONTINUOUS CHAIN — swing #21 engine trace (stitch bar 904, 15:30+)")
P("=" * 78)

btc_sws = compute_btc_swings(flow, opts=OPTS, max_swings=200)
# show swings #18..#22 to see the chain + stitching
for s in btc_sws:
    if 18 <= s.get("swing_index", -1) <= 22:
        seg = s["seg"]
        P(f"swing#{s['swing_index']} {s['dir']} seg=#{seg['start_idx']} "
          f"{hhmm(flow[seg['start_idx']])} {seg['start_px']} -> "
          f"#{seg['end_idx']} {hhmm(flow[seg['end_idx']])} {seg['end_px']} "
          f"kind={s['kind']} break_kind={s['break_kind']} conf=#{s['confirmed_at_idx']}")
        for b in s["breaks"]:
            P(f"    mark {b['kind']} {b['dir']} @#{b['idx']} {hhmm(flow[b['idx']])} px={round(b['px'],2)}")

# find swing #20 end to compute the TRUE stitch bar for #21
s20 = next(s for s in btc_sws if s.get("swing_index") == 20)
stitch = int(s20["seg"]["end_idx"]) + 1
s21 = next(s for s in btc_sws if s.get("swing_index") == 21)
P("")
P(f"-> swing #20 end_idx={s20['seg']['end_idx']}; swing #21 engine STARTS at bar {stitch} "
  f"({hhmm(flow[stitch])})  [stitch = prev end + 1]")

# replay EXACTLY like compute_btc_swings: fresh engine + defer_same_bar_arm (idx>0)
eng = SwingEngine(OPTS)
eng.defer_same_bar_arm = True
lo = stitch
hi = int(s21["seg"]["end_idx"]) + 12
for pos in range(lo, hi):
    c = flow[pos]
    before = len(eng.break_marks)
    wl = eng.walker
    eng.process_bar(c, pos)
    seals = []
    if hasattr(wl, "bar_out"):
        seals = [p for p in (wl.bar_out or []) if p.sealed]
    new_marks = eng.break_marks[before:]
    tag = ""
    if new_marks:
        tag = "  >>> " + " | ".join(f"{m.kind} {m.dir} @{m.idx} px={m.px}" for m in new_marks)
    if seals:
        tag += "  [seal: " + " ".join(f"{p.kind} px={p.px}" for p in seals) + "]"
    if new_marks or seals or hhmm(c) in ("15:30", "15:45", "16:00", "16:15", "17:00", "19:00", "20:30", "23:15"):
        P(f"  {hhmm(c)} idx={pos} h={c.high:.2f} l={c.low:.2f} "
          f"dir={eng.dir} lock={eng.locked} armed={eng.armed} "
          f"declared={eng.declared} start={eng.start_idx} "
          f"e_hi_prev={eng.e_hi_prev.px:.2f} e_lo_prev={eng.e_lo_prev.px:.2f}{tag}")
P("  ...")
P("  FINAL marks for swing #21 (engine replay):")
for m in eng.break_marks:
    P(f"    {m.kind} {m.dir} @#{m.idx} {hhmm(flow[m.idx])} px={m.px}")
P("  vs SWING #21 actual marks from the chain:")
for b in s21["breaks"]:
    P(f"    {b['kind']} {b['dir']} @#{b['idx']} {hhmm(flow[b['idx']])} px={round(b['px'],2)}")
P("")
P(f"  NOTE: engine's confirmed_at_idx={eng.confirmed_at_idx} start_idx={eng.start_idx} "
  f"end_idx={eng.end_idx} dir={eng.dir}")

# ── 2) NIFTY PER-DAY CHAIN on 10-Jan (fresh reseed, same opts) ───────────────
P("")
P("=" * 78)
P("2) NIFTY per-day chain on 10-Jan-2025 (compute_swing_results, whole)")
P("=" * 78)
nifty = compute_swing_results(flow, opts=dict(OPTS), swing_count="whole")
P(f"total nifty swings across ALL days: {len(nifty)}")
for s in nifty:
    if s.get("day") == "2025-01-10":
        seg = s["seg"]
        st = hhmm(flow[seg["start_idx"]]) if 0 <= seg["start_idx"] < len(flow) else "?"
        en = hhmm(flow[seg["end_idx"]]) if 0 <= seg["end_idx"] < len(flow) else "?"
        P(f"  swing#{s['swing_index']} {s['dir']} {s['kind']}/{s['break_kind']} "
          f"start=#{seg['start_idx']} {st} {seg['start_px']} "
          f"end=#{seg['end_idx']} {en} {seg['end_px']} "
          f"conf=#{s['confirmed_at_idx']}")
        for b in s["breaks"]:
            bi = int(b["idx"])
            bt = hhmm(flow[bi]) if 0 <= bi < len(flow) else "?"
            P(f"      mark {b['kind']} {b['dir']} @#{bi} {bt} px={round(b['px'], 2)}")

# ── 3) ENGINE-vs-ENGINE diff: continuous vs per-day, first 30 days ───────────
P("")
P("=" * 78)
P("3) BTC continuous vs Nifty per-day — segment-span match on first 30 days")
P("=" * 78)
from collections import defaultdict  # noqa: E402


def seg_row(tag, s):
    seg = s["seg"] if isinstance(s, dict) else s.seg
    d0 = seg["start_idx"] if isinstance(seg, dict) else seg.start_idx
    d1 = seg["end_idx"] if isinstance(seg, dict) else seg.end_idx
    return (tag, flow[d0].date[:10], d0, d1,
            s["dir"] if isinstance(s, dict) else s.dir,
            s["kind"] if isinstance(s, dict) else s.kind,
            s["break_kind"] if isinstance(s, dict) else s.break_kind)


bt = [seg_row("BTC", s) for s in btc_sws]
nf = [seg_row("NIF", s) for s in nifty]
P(f"BTC swings total: {len(bt)} | Nifty swings total: {len(nf)}")


def buckets(rows):
    d = defaultdict(list)
    for r in rows:
        d[r[1]].append(r)
    return d


bt_d, nf_d = buckets(bt), buckets(nf)
match = mismatch = only_bt = only_nf = 0
for day in sorted(set(bt_d) | set(nf_d))[:30]:
    b = sorted(bt_d.get(day, []), key=lambda r: r[2])
    n = sorted(nf_d.get(day, []), key=lambda r: r[2])
    spans_b = [(r[2], r[3]) for r in b]
    spans_n = [(r[2], r[3]) for r in n]
    if not b:
        only_nf += 1
        P(f"  {day}: only in NIFTY {spans_n}")
        continue
    if not n:
        only_bt += 1
        P(f"  {day}: only in BTC {spans_b}")
        continue
    if spans_b == spans_n:
        match += 1
        seq_b = [(r[4], r[5], r[6]) for r in b]
        seq_n = [(r[4], r[5], r[6]) for r in n]
        extra = " identical" if seq_b == seq_n else " (dir/kind/break differ)"
        P(f"  {day}: SAME segments ({len(b)} swings){extra}")
    else:
        mismatch += 1
        P(f"  {day}: DIFFERENT  BTC={spans_b}  NIF={spans_n}")

P("")
P(f"SUMMARY (first 30 days): SAME segments={match}, DIFFERENT={mismatch}, "
  f"only-BTC={only_bt}, only-NIF={only_nf}")

with open("debug/_engine_audit_out.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out) + "\n")
print("WROTE debug/_engine_audit_out.txt")
P("  FINAL marks for swing #21 (engine replay):")
for m in eng.break_marks:
    P(f"    {m.kind} {m.dir} @#{m.idx} {hhmm(flow[m.idx])} px={m.px}")
P("  vs SWING #21 actual marks from the chain:")
for b in s21["breaks"]:
    P(f"    {b['kind']} {b['dir']} @#{b['idx']} {hhmm(flow[b['idx']])} px={round(b['px'],2)}")