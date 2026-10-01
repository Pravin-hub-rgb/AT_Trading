"""Issue #10 diagnostic: 30d rolling window / cold-start warmup vs full-history chains.

Tests (sequential, one experiment at a time conceptually, single run):
  A) Cold-start depth: PSE fed only last N days, match vs full-history chain tail
  B) Live seed depth: seed with limit=2000 bars (~20.8d 15m) then continuous feed
  C) Continuous windowed sim: full-history swings + 30d trimmed candles (M6/L3)
  D) Trade reproduction: baseline full vs live-style (seed + window) for recent trades

Run: python backtest/tests/exp_issue10_window.py
"""
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backtest/tests"))

from persistence.database import Database
from src.btc.btc_swing import compute_btc_swings
from src.live.persistent_swing import PersistentSwingEngine
from src.walker import FlowCandle
from src.btc.btc_config import load_btc_df
from src.btc.engines.htf_ltf.v18_streak_halt import simulate_htf_ltf_streak_halt
from engine.v18_params import SWING, get_v18_params

DAY = 86400
BAR15 = 900
INSTRUMENT = "BTCUSDT_BYBIT"


def load_tf(tf):
    df = load_btc_df(tf, INSTRUMENT)
    candles, flow = [], []
    for row in df.itertuples():
        date = row.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        candles.append({
            "date": date, "ts": int(row.ts),
            "open": float(row.open), "high": float(row.high),
            "low": float(row.low), "close": float(row.close),
        })
        flow.append(FlowCandle(date=date, open=float(row.open), high=float(row.high),
                               low=float(row.low), close=float(row.close)))
    return candles, flow


def swing_key(s):
    seg = s.get("seg") or {}
    # Index-free key: dir + pivots + confirm time (works for BT and PSE)
    return (
        s.get("dir"),
        round(float(seg.get("start_px") or 0), 2),
        round(float(seg.get("end_px") or 0), 2),
        str(s.get("confirmed_at_time") or ""),
    )


def pse_chain(flow, min_bars, time_cap="00:00"):
    db = Database(os.path.join(tempfile.mkdtemp(prefix="i10_"), "s.db"))
    db.connect()
    db.create_tables()
    eng = PersistentSwingEngine("15m", db, {"minBars": min_bars, "timeCap": time_cap})
    out = []
    for i, c in enumerate(flow):
        r = eng.process_bar(c, i)
        if r:
            out.append(r)
    return out


def match_tail(full, cold, min_keep=5):
    """Match cold-chain swings against full-history chain by confirm-time key."""
    if not full or not cold:
        return 0, 0, None
    full_by_ct = {}
    for i, s in enumerate(full):
        t = str((s.get("confirmed_at_time") or "")[:19])
        if t:
            full_by_ct[t] = i
    matched = 0
    considered = 0
    first_miss = None
    for s in cold:
        ct = str((s.get("confirmed_at_time") or "")[:19])
        if ct and ct in full_by_ct:
            considered += 1
            fi = full_by_ct[ct]
            if fi < len(full) and swing_key(full[fi]) == swing_key(s):
                matched += 1
            elif first_miss is None:
                first_miss = (ct, swing_key(full[fi]) if fi < len(full) else None, swing_key(s))
    if considered == 0:
        # Fallback: sequential after aligning by dir+px only (no time fields)
        n = min(len(full), len(cold))
        for i in range(n):
            considered += 1
            kf = (full[i].get("dir"),
                  round(float((full[i].get("seg") or {}).get("start_px") or 0), 2),
                  round(float((full[i].get("seg") or {}).get("end_px") or 0), 2))
            kc = (cold[i].get("dir"),
                  round(float((cold[i].get("seg") or {}).get("start_px") or 0), 2),
                  round(float((cold[i].get("seg") or {}).get("end_px") or 0), 2))
            if kf == kc:
                matched += 1
            elif first_miss is None:
                first_miss = (i, kf, kc)
    return matched, considered, first_miss


def run_sim(c15, sw15, c1h, sw1h, v18):
    return simulate_htf_ltf_streak_halt(
        c1h, sw1h, c15, sw15,
        fine_ltf=[],
        sl_buf_atr=v18["sl_buf_atr"],
        ext_stop_r=v18["ext_stop_r"],
        mode=v18["mode"],
        chop_thresh=v18["chop_thresh"],
        cooldown_bars=v18["cooldown_bars"],
        max_consecutive_losses=v18["max_consecutive_losses"],
    )["ltf_trades"]


def trade_key(t):
    return (t.get("dir"), int(t.get("entry_ts") or 0))


def main():
    t0 = time.time()
    print("=" * 90)
    print("  ISSUE #10 DIAG — cold-start depth / live seed / 30d window sim")
    print("=" * 90)

    print("\n[load] 15m + 1h ...", flush=True)
    c15, f15 = load_tf("15m")
    c1h, f1h = load_tf("1h")
    min15 = int(SWING["min_bars_15m"])
    v18 = get_v18_params(INSTRUMENT)
    end_ts = c15[-1]["ts"]
    print(f"  15m={len(c15)}  1h={len(c1h)}  {c15[0]['date']} -> {c15[-1]['date']}  minBars15={min15}")

    # ---- full-history reference ----
    print("\n[A] full-history swings + baseline sim ...", flush=True)
    sw15_full = compute_btc_swings(f15, opts={"minBars": min15}, max_swings=len(f15) // 2)
    sw1h_full = compute_btc_swings(f1h, opts={"minBars": int(SWING["min_bars_1h"])},
                                   max_swings=len(f1h) // 2)
    baseline = run_sim(c15, sw15_full, c1h, sw1h_full, v18)
    print(f"  full swings: 15m={len(sw15_full)}  1h={len(sw1h_full)}  baseline trades={len(baseline)}  ({time.time()-t0:.0f}s)")

    # ---- A) cold-start depth sweep ----
    print("\n[A] cold-start depth sweep (PSE only last N days, match vs full tail) ...", flush=True)
    depths = [7, 14, 21, 30, 45, 60, 90]
    for d in depths:
        n = min(len(f15), d * 96)
        cold_flow = f15[-n:]
        cold = pse_chain(cold_flow, min15)
        t_lo = c15[-n]["date"]
        full_tail = [s for s in sw15_full
                     if str((s.get("confirmed_at_time") or "")[:19]) >= t_lo]
        m, c, fm = match_tail(full_tail, cold)
        rate = (100.0 * m / c) if c else 0.0
        flag = "OK" if c and m == c else ("PARTIAL" if c and m > 0.8 * c else "MISS")
        print(f"  seed {d:3d}d ({n:5d} bars): cold={len(cold):4d} full_tail={len(full_tail):4d} "
              f"match={m}/{c} ({rate:5.1f}%) {flag}", flush=True)
        if fm and flag != "OK":
            print(f"           first_miss: {fm[0]}", flush=True)

    # ---- B) live seed depth (limit=2000 bars) ----
    print("\n[B] live seed depth: 15m limit=2000 (~20.8d), 1h limit=500 (~20.8d) ...", flush=True)
    seed15 = min(len(f15), 2000)
    seed1h = min(len(f1h), 500)
    cold15 = pse_chain(f15[-seed15:], min15)
    t_lo = c15[-seed15]["date"]
    full_tail15 = [s for s in sw15_full
                   if str((s.get("confirmed_at_time") or "")[:19]) >= t_lo]
    m, c, fm = match_tail(full_tail15, cold15)
    print(f"  15m seed {seed15} bars: cold={len(cold15)} full_tail={len(full_tail15)} match={m}/{c} "
          f"({100.0*m/c if c else 0:.1f}%)", flush=True)
    cold1h = pse_chain(f1h[-seed1h:], int(SWING["min_bars_1h"]))
    t_lo1h = c1h[-seed1h]["date"]
    full_tail1h = [s for s in sw1h_full
                   if str((s.get("confirmed_at_time") or "")[:19]) >= t_lo1h]
    m1, c1, _ = match_tail(full_tail1h, cold1h)
    print(f"  1h  seed {seed1h} bars: cold={len(cold1h)} full_tail={len(full_tail1h)} match={m1}/{c1} "
          f"({100.0*m1/c1 if c1 else 0:.1f}%)", flush=True)

    # ---- C) continuous live path: seed then keep feeding (simulates production) ----
    print("\n[C] continuous live path: feed ALL bars through PSE from start (parity check) ...", flush=True)
    live_cont = pse_chain(f15, min15)
    m, c, fm = match_tail(sw15_full, live_cont)
    print(f"  continuous PSE vs full compute_btc_swings: match={m}/{c} ({100.0*m/c if c else 0:.1f}%)", flush=True)
    if fm:
        print(f"  first_miss: {fm[0]}", flush=True)

    # ---- D) window trim + full swings (M6/L3): simulate recent period with 30d window ----
    print("\n[D] 30d window sim vs full-history sim (same full swings, trimmed candles) ...", flush=True)
    recent_cut = end_ts - 60 * DAY
    base_recent = [t for t in baseline if int(t["entry_ts"]) >= recent_cut]
    print(f"  baseline trades in last 60d: {len(base_recent)}", flush=True)

    cut15 = end_ts - 30 * DAY
    cut1h = end_ts - 20 * DAY
    w15 = [c for c in c15 if c["ts"] >= cut15]
    w1h = [c for c in c1h if c["ts"] >= cut1h]

    def rebase_swings(swings, window, full15=None, full1h=None, is_1h=False):
        """L3 rebase: map swing indices into `window` positions.

        PSE swings carry start_time/end_time. BT swings only have indices into
        the full list — resolve those via full_candles[ idx ].date.
        """
        if not window or not swings:
            return list(swings or [])
        date_to_pos = {c["date"]: i for i, c in enumerate(window)}
        w0, w1 = window[0]["date"], window[-1]["date"]
        n = len(window)
        full = full1h if is_1h else full15

        def full_date(idx):
            if full is not None and idx is not None and 0 <= int(idx) < len(full):
                return full[int(idx)]["date"]
            return ""

        out = []
        for s in swings:
            s2 = dict(s)
            seg = dict(s.get("seg") or {})
            st = str(seg.get("start_time") or "") or full_date(seg.get("start_idx"))
            if st:
                if st in date_to_pos:
                    seg["start_idx"] = date_to_pos[st]
                elif st < w0:
                    seg["start_idx"] = 0
                elif st > w1:
                    continue
                else:
                    seg["start_idx"] = 0
            if seg.get("start_idx") is None:
                continue
            # normalize start_idx to int in-window
            si = int(seg.get("start_idx"))
            if not (0 <= si < n):
                if si < 0:
                    seg["start_idx"] = 0
                else:
                    seg["start_idx"] = n - 1

            et = str(seg.get("end_time") or "") or full_date(seg.get("end_idx"))
            if et:
                if et in date_to_pos:
                    seg["end_idx"] = date_to_pos[et]
                elif et < w0:
                    seg["end_idx"] = -1
                else:
                    seg["end_idx"] = n - 1
            elif seg.get("end_idx") is not None:
                ei = int(seg["end_idx"])
                if not (0 <= ei < n):
                    seg["end_idx"] = n - 1 if ei >= n else -1

            ct = s.get("confirmed_at_time")
            if ct:
                ct = str(ct)[:19]
                if ct in date_to_pos:
                    s2["confirmed_at_idx"] = date_to_pos[ct]
            # BT confirmed_at_idx is full-space — map via date if needed
            elif s.get("confirmed_at_idx") is not None:
                cfi = s.get("confirmed_at_idx")
                cdate = full_date(cfi)
                if cdate and cdate in date_to_pos:
                    s2["confirmed_at_idx"] = date_to_pos[cdate]

            ft = s.get("fs_at_time")
            if ft:
                ft = str(ft)[:19]
                if ft in date_to_pos:
                    s2["fs_at_idx"] = date_to_pos[ft]
            elif s.get("fs_at_idx") is not None:
                fdate = full_date(s.get("fs_at_idx"))
                if fdate and fdate in date_to_pos:
                    s2["fs_at_idx"] = date_to_pos[fdate]

            nb = []
            for b in s.get("breaks") or []:
                bt = str(b.get("time") or "")
                if not bt:
                    bt = full_date(b.get("idx"))
                if bt and bt in date_to_pos:
                    b2 = dict(b)
                    b2["idx"] = date_to_pos[bt]
                    b2["time"] = bt
                    nb.append(b2)
            s2["breaks"] = nb
            s2["seg"] = seg
            out.append(s2)
        return out

    # D1: naive — full swings + trimmed candles (broken L3)
    sw_naive = run_sim(w15, sw15_full, w1h, sw1h_full, v18)
    base_in_trim = [t for t in baseline if int(t["entry_ts"]) >= cut15]
    base_keys = {trade_key(t) for t in base_in_trim}
    naive_keys = {trade_key(t) for t in sw_naive}
    hit = len(base_keys & naive_keys)
    print(f"  NAIVE (full swings + trimmed candles): {len(naive_keys)} trades, "
          f"reproduced={hit}/{len(base_keys)} ({100.0*hit/len(base_keys) if base_keys else 0:.1f}%)", flush=True)

    # D2: L3 rebase — remap swing indices into window space
    sw15_r = rebase_swings(sw15_full, w15, full15=c15, full1h=c1h, is_1h=False)
    sw1h_r = rebase_swings(sw1h_full, w1h, full15=c15, full1h=c1h, is_1h=True)
    sw_re = run_sim(w15, sw15_r, w1h, sw1h_r, v18)
    re_keys = {trade_key(t) for t in sw_re}
    hit2 = len(base_keys & re_keys)
    print(f"  REBASED (L3 fix): 15m sw {len(sw15_r)}/{len(sw15_full)}  1h sw {len(sw1h_r)}/{len(sw1h_full)}", flush=True)
    print(f"  REBASED sim: {len(re_keys)} trades, "
          f"reproduced={hit2}/{len(base_keys)} ({100.0*hit2/len(base_keys) if base_keys else 0:.1f}%)", flush=True)
    only_base = sorted(base_keys - re_keys)
    only_re = sorted(re_keys - base_keys)
    if only_base:
        print(f"  still MISSED ({len(only_base)}):", flush=True)
        for d, ts in only_base[:15]:
            print(f"    {time.strftime('%Y-%m-%d %H:%M', time.gmtime(ts))} {d}", flush=True)
    if only_re:
        print(f"  EXTRA ({len(only_re)}):", flush=True)
        for d, ts in only_re[:10]:
            print(f"    {time.strftime('%Y-%m-%d %H:%M', time.gmtime(ts))} {d}", flush=True)

    # ---- E) replay-harness style: cold rebuild per entry (worst case) on last 10 baseline trades ----
    print("\n[E] replay-style cold rebuild (last 10 baseline trades, 35d/25d fetch + 30d/20d window) ...",
          flush=True)
    recent10 = [t for t in baseline if int(t["entry_ts"]) >= end_ts - 90 * DAY][-10:]
    rep = 0
    for t in recent10:
        E = int(t["entry_ts"])
        d = t["dir"]
        f15w = [c for c in c15 if E - 35 * DAY <= c["ts"] <= E]
        f1h_w = [c for c in c1h if E - 25 * DAY <= c["ts"] <= E]
        if not f15w or not f1h_w:
            print(f"    {time.strftime('%Y-%m-%d %H:%M', time.gmtime(E))} {d}  [no-data]", flush=True)
            continue
        # rebuild swings cold on fetch window
        fl15 = []
        for c in f15w:
            fl15.append(FlowCandle(date=c["date"], open=c["open"], high=c["high"],
                                   low=c["low"], close=c["close"]))
        fl1h = []
        for c in f1h_w:
            fl1h.append(FlowCandle(date=c["date"], open=c["open"], high=c["high"],
                                   low=c["low"], close=c["close"]))
        s15c = pse_chain(fl15, min15)
        s1hc = pse_chain(fl1h, int(SWING["min_bars_1h"]))
        w15e = [c for c in f15w if c["ts"] >= E - 30 * DAY]
        w1he = [c for c in f1h_w if c["ts"] >= E - 20 * DAY]
        tr = run_sim(w15e, s15c, w1he, s1hc, v18)
        hit = any(x["dir"] == d and abs(int(x["entry_ts"]) - E) <= BAR15 for x in tr)
        if hit:
            rep += 1
        print(f"    {time.strftime('%Y-%m-%d %H:%M', time.gmtime(E))} {d}  "
              f"{'HIT' if hit else 'MISS'}  cold_sw={len(s15c)}/{len(s1hc)} sim={len(tr)}", flush=True)
    print(f"  replay-style: {rep}/{len(recent10)} reproduced", flush=True)

    print(f"\n(done in {time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
