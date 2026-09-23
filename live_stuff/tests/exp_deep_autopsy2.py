"""DEEP AUTOPSY v2 — novel cuts we have NOT done yet.

Angles (none previously tested):
  A. Regime age at entry — bars since last window/regime switch (fresh vs stale)
  B. Giveback anatomy — peak R vs exit R; is the trail leaving money on winners
  C. HTF window productivity — which 1h windows bleed vs pay (window-level, not trade)
  D. Sequential dependence — P(win | prev win/loss), streak market state
  E. Near-miss — trades that reached +1.5R then died to ~0/-1
  F. Post-halt edge — performance of the trade(s) right after a 3-loss halt
  G. R-distribution shape — bimodality, gap between scratch and runner
  H. Pre-entry expansion — bars/range immediately before the signal bar
  I. Time-since-last-trade clustering
  J. Long-hold vs quick winners — does trail exit winners too early?

Run on champion_multi IS trades (JSON) + fresh OOS to validate any pattern.
Any cut that separates must be checked for transfer before believing it.
"""
import sys, json, math, time
from pathlib import Path
from collections import defaultdict, Counter

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

from replay_harness import load_candles, INSTRUMENT
from engine.v18_params import SWING, get_v18_params, V18_ENGINE
from src.btc.btc_routes import _load_fine_1m, _compute_swings, _trade_costs
from test_experiments_craze import build_module as build_craze
from test_4_new_concepts import load_unseen, load_fine_1m as load_fine_unseen
from experiment_registry import EXPERIMENTS, BP

_P = dict(get_v18_params(INSTRUMENT)); _P.update(V18_ENGINE)


def bucket_stats(items, key_fn, min_n=8):
    """items: list of (r, meta). group by key_fn(meta) -> stats."""
    groups = defaultdict(list)
    for r, meta in items:
        groups[key_fn(meta)].append(r)
    rows = []
    for k, rs in sorted(groups.items(), key=lambda x: str(x[0])):
        n = len(rs)
        if n < min_n: continue
        net = sum(rs)
        wins = sum(1 for x in rs if x > 0)
        dd = 0; peak = 0; cum = 0
        for x in rs:
            cum += x; peak = max(peak, cum); dd = max(dd, peak - cum)
        rows.append((k, n, net, 100.0 * wins / n, net / n, dd))
    return rows


def show(title, rows, fmt_k=str):
    print(f"\n  --- {title} ---")
    print(f"  {'bucket':>16} {'n':>5} {'net':>8} {'WR%':>6} {'R/tr':>7} {'dd':>6}")
    for k, n, net, wr, rpt, dd in rows:
        flag = " <<<" if net > 0 and n >= 15 else (" x" if net < 0 else "")
        print(f"  {fmt_k(k):>16} {n:>5} {net:>+8.1f} {wr:>6.1f} {rpt:>+7.3f} {dd:>6.1f}{flag}")


def corr(xs, ys):
    n = len(xs)
    if n < 10: return 0.0
    mx = sum(xs) / n; my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if dx == 0 or dy == 0: return 0.0
    return num / (dx * dy)


def load_is(key="champion_multi_sw10"):
    p = ROOT / "live_stuff/tests" / f"_exp_{key}_results.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    return data["trades"], data["results"]


def enrich(trades, c1h, c15, sw1h, sw15):
    """Attach per-trade context: regime age, window id, pre-expansion, peak proxy."""
    # index 15m bars by ts
    idx15 = {c["ts"]: i for i, c in enumerate(c15)}
    idx1h = {c["ts"]: i for i, c in enumerate(c1h)}
    # chop series on 1h (simple recompute from closes/highs/lows for regime-switch tracking)
    # We track window membership via entry inside an HTF trade window is hard without
    # re-running engine; instead use chop-of-last-closed-1h vs thresh as regime proxy,
    # and count bars since regime last flipped relative to chop_thresh=58.
    chop_th = 58.0
    def chop_at_1h(i):
        if i < 14: return 50.0
        bars = c1h[i-13:i+1]  # last closed when used at i (we'll call with closed index)
        trs = []
        hi = max(b["high"] for b in bars); lo = min(b["low"] for b in bars)
        if hi <= lo: return 50.0
        sum_tr = 0.0
        pc = bars[0]["close"]  # simplified; good enough for regime-age buckets
        for b in bars:
            h, l, cl = b["high"], b["low"], b["close"]
            tr = max(h - l, abs(h - pc), abs(l - pc))
            sum_tr += tr; pc = cl
        rng = hi - lo
        if sum_tr <= 0 or rng <= 0: return 50.0
        import math as _m
        return 100.0 * _m.log10(sum_tr / rng) / _m.log10(14)

    # precompute chop per 1h bar (closed = index i uses bars up to i)
    chop_series = [50.0] * len(c1h)
    for i in range(14, len(c1h)):
        chop_series[i] = chop_at_1h(i)

    # map regime state per 1h bar: 1 = chop (B2 windows), 0 = trend (FLIP)
    regime = [1 if ch >= chop_th else 0 for ch in chop_series]

    # bars since regime switch (in 1h bars), known at close of bar i
    age1h = [999] * len(c1h)
    last = 0
    for i in range(1, len(c1h)):
        if regime[i] != regime[i-1]:
            last = i
        age1h[i] = i - last

    # map entry ts -> 1h index (bar with ts <= entry, using closed bar before entry)
    def h_index_before(ts):
        # find rightmost 1h bar with ts <= entry_ts; for causal, use bar that closed before entry
        lo, hi = 0, len(c1h) - 1
        ans = 0
        while lo <= hi:
            mid = (lo + hi) // 2
            if c1h[mid]["ts"] <= ts:
                ans = mid; lo = mid + 1
            else:
                hi = mid - 1
        return ans

    enriched = []
    for t in trades:
        ets = None
        # parse entry date to ts — dates are IST strings; engine trades have entry_price etc.
        # Use exit_date/entry_date string -> we'll match via ts if present else skip age
        ed = t.get("entry_date", "")
        xd = t.get("exit_date", "")
        # build ts from date string (IST) : timestamp naive
        def d2ts(s):
            if not s: return None
            from datetime import datetime
            try:
                dt = datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S")
                # CSV ts = IST wall as if UTC-minus-offset already applied in loader;
                # candle ts matches the same convention as date strings in JSON
                # JSON dates come from engine using candle["date"] which equals IST display
                # candle["ts"] = true UTC epoch - 5:30. So date string "YYYY-MM-DD HH:MM"
                # maps to: parse as UTC then subtract 5:30? Actually loader:
                # ts = (timestamp.astype int64 // 1e9) - IST_OFFSET, and date = timestamp.strftime
                # where timestamp is read as naive IST. So date "2021-01-01 05:30" <-> ts = epoch(IST naive as UTC) - 5:30
                # Simpler: reconstruct epoch as if date were UTC then subtract offset.
                import calendar
                epoch_as_utc = calendar.timegm(dt.timetuple())
                return epoch_as_utc - (5 * 3600 + 30 * 60)
            except Exception:
                return None

        ets = d2ts(ed)
        xts = d2ts(xd)
        meta = dict(t)
        if ets is not None:
            hi = h_index_before(ets)
            # causal: last CLOSED 1h bar is the one strictly before entry's 1h bucket
            # approximate: bar hi if its ts+3600 <= ets else hi-1
            if hi < len(c1h) and c1h[hi]["ts"] + 3600 > ets and hi > 0:
                hi = hi - 1
            hi = max(0, min(hi, len(c1h) - 1))
            meta["_regime_age_1h"] = age1h[hi]
            meta["_regime"] = regime[hi]
            meta["_chop"] = chop_series[hi]
            # pre-expansion: last 4 closed 1h bars true range sum / atr proxy
            if hi >= 4:
                window = c1h[hi-3:hi+1]
                tr_sum = 0.0
                pc = c1h[hi-4]["close"]
                for b in window:
                    h, l, cl = b["high"], b["low"], b["close"]
                    tr_sum += max(h - l, abs(h - pc), abs(l - pc)); pc = cl
                meta["_pre_tr4"] = tr_sum
                # consecutive same-direction closes in those 4 bars
                dirn = sum(1 for a, b in zip(window, window[1:])
                           if (b["close"] > a["close"]) == (t.get("dir") == "long"))
                meta["_pre_aligned"] = dirn
            else:
                meta["_pre_tr4"] = 0.0; meta["_pre_aligned"] = 0
        else:
            meta["_regime_age_1h"] = -1; meta["_regime"] = -1
            meta["_chop"] = -1; meta["_pre_tr4"] = 0; meta["_pre_aligned"] = 0

        # bars held
        meta["_bars"] = int(t.get("bars_held") or 0)
        # window proxy: hour of entry rounded — for window productivity use entry date hour+day
        meta["_win_key"] = (ed[:13] if ed else "?")  # year-month-hour-ish: YYYY-MM-DD HH
        # better window: 16-day HTF windows unknown without engine; use 1h entry bucket ts//3600
        if ets is not None:
            meta["_hbucket"] = ets // 3600
        else:
            meta["_hbucket"] = -1
        # seq: filled later
        meta["_r"] = float(t["r_multiple"])
        enriched.append(meta)
    return enriched


def cut_A_regime_age(trades_e, label):
    rows = bucket_stats(
        [(m["_r"], m) for m in trades_e if m.get("_regime_age_1h", -1) >= 0],
        lambda m: ("fresh0-2" if m["_regime_age_1h"] <= 2 else
                   "mid3-7" if m["_regime_age_1h"] <= 7 else
                   "stale8-15" if m["_regime_age_1h"] <= 15 else "old16+"))
    show(f"A. Regime age (1h bars since B2/FLIP switch) — {label}", rows)

    rows2 = bucket_stats(
        [(m["_r"], m) for m in trades_e if m.get("_regime", -1) >= 0],
        lambda m: f"chop(B2) age{m['_regime_age_1h']}" if m["_regime"] == 1 else f"trend(FLIP) age{m['_regime_age_1h']}",
        min_n=10)
    # coarser
    rows2 = bucket_stats(
        [(m["_r"], m) for m in trades_e if m.get("_regime", -1) >= 0],
        lambda m: ("B2 fresh" if m["_regime"] == 1 and m["_regime_age_1h"] <= 3 else
                   "B2 stale" if m["_regime"] == 1 else
                   "FLIP fresh" if m["_regime_age_1h"] <= 3 else "FLIP stale"))
    show(f"A2. Regime x freshness — {label}", rows2)


def cut_B_giveback(trades, label):
    """For winners we only have exit R — need peak. Without path, use outcome=bars:
    approximate giveback via: winners with high bars_held may have given back.
    True peak needs fine walk — approximate with: exit_price vs entry and outcome trail.
    Better proxy: for trail winners, R vs max possible if we had high water.
    We'll compute distribution of winner R and bars to see shape."""
    wins = [(float(t["r_multiple"]), t) for t in trades if float(t["r_multiple"]) > 0]
    losses = [(float(t["r_multiple"]), t) for t in trades if float(t["r_multiple"]) <= 0]
    rs = sorted((r for r, _ in wins), reverse=True)
    print(f"\n  --- B. Winner R shape — {label} ---")
    print(f"  winners={len(rs)}  top1={rs[0]:.1f}  p50={rs[len(rs)//2]:.2f}  p75={rs[int(len(rs)*.25)]:.2f}  p90={rs[int(len(rs)*.1)]:.2f}")
    # bimodality: count in bins
    bins = [0, 0.5, 1, 2, 3, 5, 8, 12, 20, 50, 1000]
    labels = ["0-0.5", "0.5-1", "1-2", "2-3", "3-5", "5-8", "8-12", "12-20", "20-50", "50+"]
    cnt = [0] * (len(bins) - 1)
    for r in rs:
        for i in range(len(bins) - 1):
            if bins[i] <= r < bins[i+1]:
                cnt[i] += 1; break
    for lab, c in zip(labels, cnt):
        print(f"  {lab:>8}: {c:>4}  {'#' * min(c, 60)}")

    # bars held vs R for winners
    xs = [int(t.get("bars_held") or 0) for _, t in wins]
    ys = [r for r, _ in wins]
    print(f"  corr(bars_held, R|win) = {corr(xs, ys):+.3f}")
    # quick winners (<=24 bars = 6h)
    quick = [r for r, t in wins if int(t.get("bars_held") or 0) <= 24]
    mid = [r for r, t in wins if 24 < int(t.get("bars_held") or 0) <= 96]
    slow = [r for r, t in wins if int(t.get("bars_held") or 0) > 96]
    for name, arr in [("quick<=6h", quick), ("mid6-24h", mid), ("run>24h", slow)]:
        if arr:
            print(f"  {name:10} n={len(arr):>3}  sum={sum(arr):+7.1f}  avg={sum(arr)/len(arr):+.2f}")

    # outcome mix
    oc = Counter(t.get("outcome", "?") for _, t in wins)
    print(f"  winner outcomes: {dict(oc)}")
    ocL = Counter(t.get("outcome", "?") for _, t in losses)
    print(f"  loser outcomes:  {dict(ocL)}")


def cut_C_window_prod(trades_e, label, topn=12):
    """Cluster by 1h bucket of entry — productivity of nearby entries.
    Real HTF windows last days; bucket by day instead for 'window-day'."""
    by_day = defaultdict(list)
    for m in trades_e:
        d = (m.get("entry_date") or "")[:10]
        by_day[d].append(m["_r"])
    # only days with >=2 trades (window-days)
    multi = {d: rs for d, rs in by_day.items() if len(rs) >= 2}
    rows = bucket_stats(
        [(sum(rs), {"d": d, "n": len(rs)}) for d, rs in multi.items()],
        lambda m: f"{m['n']}t/day",
        min_n=5)
    show(f"C. Entry-day clusters (proxy for HTF window productivity) — {label}", rows)

    # worst / best days
    day_net = {d: sum(rs) for d, rs in by_day.items() if len(rs) >= 3}
    if day_net:
        srt = sorted(day_net.items(), key=lambda x: x[1])
        print(f"  worst 3+ trade days: " + ", ".join(f"{d}:{v:+.1f}" for d, v in srt[:5]))
        print(f"  best  3+ trade days: " + ", ".join(f"{d}:{v:+.1f}" for d, v in srt[-5:]))


def cut_D_sequential(trades, label):
    rs = [float(t["r_multiple"]) for t in trades]
    # transition matrix
    ww = wl = lw = ll = 0
    for a, b in zip(rs, rs[1:]):
        pa, pb = a > 0, b > 0
        if pa and pb: ww += 1
        elif pa and not pb: wl += 1
        elif not pa and pb: lw += 1
        else: ll += 1
    p_ww = ww / max(ww + wl, 1)
    p_lw = lw / max(lw + ll, 1)
    print(f"\n  --- D. Sequential dependence — {label} ---")
    print(f"  P(win|prev win)  = {p_ww:.3f}  ({ww}W->{'W'}, {wl}W->{'L'})")
    print(f"  P(win|prev loss) = {p_lw:.3f}  ({lw}L->{'W'}, {ll}L->{'L'})")
    # expected under independence = overall WR
    wr = sum(1 for x in rs if x > 0) / max(len(rs), 1)
    print(f"  overall WR        = {wr:.3f}   delta_after_win={p_ww-wr:+.3f}  delta_after_loss={p_lw-wr:+.3f}")

    # net after win vs after loss
    after_w = [rs[i+1] for i in range(len(rs)-1) if rs[i] > 0]
    after_l = [rs[i+1] for i in range(len(rs)-1) if rs[i] <= 0]
    print(f"  E[R|after win]  = {sum(after_w)/max(len(after_w),1):+.3f}  n={len(after_w)}")
    print(f"  E[R|after loss] = {sum(after_l)/max(len(after_l),1):+.3f}  n={len(after_l)}")


def cut_E_nearmiss(trades, label):
    """Winners clustered near 0 and mid-size winners — who almost died.
    Without path: use trail outcome winners with R < 0.5 as 'barely escaped'
    and R in 0.5-2 as 'small'. Compare their bars_held vs big winners."""
    rows_data = []
    for t in trades:
        r = float(t["r_multiple"])
        b = int(t.get("bars_held") or 0)
        if r > 0:
            grp = "scratch0-0.5" if r < 0.5 else "small0.5-2" if r < 2 else "run2+"
        else:
            grp = "loss"
        rows_data.append((r, {"g": grp, "b": b}))
    rows = bucket_stats(rows_data, lambda m: m["g"])
    show(f"E. Outcome classes — {label}", rows)
    # bars by class
    for g in ["scratch0-0.5", "small0.5-2", "run2+", "loss"]:
        bs = [m["b"] for r, m in rows_data if m["g"] == g]
        if bs:
            print(f"    {g:14} avg_bars={sum(bs)/len(bs):.0f}  n={len(bs)}")


def cut_F_posthalt(trades, label, halt=3):
    """Index of trades that start a new 'sequence' after `halt` consecutive losses."""
    rs = [float(t["r_multiple"]) for t in trades]
    post = []
    run = 0
    for i, r in enumerate(rs):
        if r <= 0:
            run += 1
        else:
            run = 0
        # the trade AFTER run reaches halt: i.e. when previous halt trades all lost
        if i >= halt and all(rs[i-halt+j] <= 0 for j in range(halt)):
            # this trade is the first after a completed losing streak of >= halt
            # only count when we just hit exactly the streak (transition)
            if i == halt or rs[i-1-halt] > 0 if i > halt else True:
                post.append((r, {"i": i}))
    # cleaner: positions where count of consecutive losses before i equals halt
    post = []
    for i in range(len(rs)):
        j = i - 1; run = 0
        while j >= 0 and rs[j] <= 0:
            run += 1; j -= 1
        if run == halt:
            post.append(rs[i])
    base = [rs[i] for i in range(len(rs))]
    print(f"\n  --- F. Post-halt (after exactly {halt} straight losses) — {label} ---")
    print(f"  n={len(post)}  net={sum(post):+.1f}  WR={100*sum(1 for x in post if x>0)/max(len(post),1):.1f}%  avg={sum(post)/max(len(post),1):+.3f}")
    print(f"  baseline all: n={len(base)}  net={sum(base):+.1f}  WR={100*sum(1 for x in base if x>0)/max(len(base),1):.1f}%  avg={sum(base)/max(len(base),1):+.3f}")


def cut_H_preexpansion(trades_e, label):
    rows = bucket_stats(
        [(m["_r"], m) for m in trades_e if m.get("_pre_tr4", 0) > 0],
        lambda m: ("exp-low" if m["_pre_tr4"] < 0.02 else
                   "exp-mid" if m["_pre_tr4"] < 0.05 else
                   "exp-high" if m["_pre_tr4"] < 0.09 else "exp-blowoff"))
    show(f"H. Pre-entry 4h true-range sum (expansion) — {label}", rows)

    rows = bucket_stats(
        [(m["_r"], m) for m in trades_e if m.get("_pre_aligned", -1) >= 0],
        lambda m: f"aligned{m['_pre_aligned']}/4")
    show(f"H2. Pre-entry bars aligned with trade dir — {label}", rows)


def cut_I_spacing(trades, label):
    """Time between consecutive entries — overcrowding."""
    from datetime import datetime
    def d2ts(s):
        if not s: return None
        try:
            import calendar
            dt = datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S")
            return calendar.timegm(dt.timetuple()) - (5*3600+30*60)
        except Exception:
            return None
    gaps = []
    prev = None
    items = []
    for t in trades:
        ts = d2ts(t.get("entry_date", ""))
        r = float(t["r_multiple"])
        if ts is not None and prev is not None:
            gaps.append((ts - prev) / 3600.0)
            items.append((r, {"gap_h": (ts - prev) / 3600.0}))
        if ts is not None:
            prev = ts
    rows = bucket_stats(items, lambda m: ("gap<2h" if m["gap_h"] < 2 else
                                          "2-8h" if m["gap_h"] < 8 else
                                          "8-24h" if m["gap_h"] < 24 else
                                          "1-3d" if m["gap_h"] < 72 else "3d+"))
    show(f"I. Gap since previous entry — {label}", rows)


def cut_J_hold_profile(trades, label):
    print(f"\n  --- J. Hold-time x outcome — {label} ---")
    for t in trades:
        pass
    rows = bucket_stats(
        [(float(t["r_multiple"]), t) for t in trades],
        lambda t: ("<=6h" if int(t.get("bars_held") or 0) <= 24 else
                   "6-24h" if int(t.get("bars_held") or 0) <= 96 else
                   "1-4d" if int(t.get("bars_held") or 0) <= 384 else ">4d"))
    show("J. Bars-held buckets (all trades)", rows)


def main():
    t0 = time.time()
    print("=" * 100)
    print("  DEEP AUTOPSY v2 — novel cuts")
    print("=" * 100)

    # ---- IS ----
    trades_is, res_is = load_is("champion_multi_sw10")
    # need candles for enrichment — load IS candles (cached path)
    from test_experiments_craze import load_candles as load_is_c
    (c15, f15), (c1h, f1h) = load_is_c()
    # only need first N years context — full is fine
    e_is = enrich(trades_is, c1h, c15, None, None)

    print("\n" + "#" * 90)
    print("#  IS 2023-2026 — champion_multi_sw10")
    print("#" * 90)
    cut_A_regime_age(e_is, "IS")
    cut_B_giveback(trades_is, "IS")
    cut_C_window_prod(e_is, "IS")
    cut_D_sequential(trades_is, "IS")
    cut_E_nearmiss(trades_is, "IS")
    cut_F_posthalt(trades_is, "IS")
    cut_H_preexpansion(e_is, "IS")
    cut_I_spacing(trades_is, "IS")
    cut_J_hold_profile(trades_is, "IS")

    # ---- OOS validate ----
    print("\n" + "#" * 90)
    print("#  TRUE OOS 2021-2022 — fresh run")
    print("#" * 90)
    sim = build_craze()
    (c15o, f15o), (c1ho, f1ho) = load_unseen("15m"), load_unseen("1h")
    sw15o = _compute_swings(f15o, "continuous", min_bars=SWING["min_bars_15m"])
    sw1ho = _compute_swings(f1ho, "continuous", min_bars=10)
    fineo = load_fine_unseen(c15o[0]["ts"], c15o[-1]["ts"])
    cfg = EXPERIMENTS["champion_multi_sw10"]
    params = {**BP, **cfg["params"]}
    params.setdefault("exp_partial_r", 0.0)
    r = sim(c1ho, sw1ho, c15o, sw15o, fine_ltf=fineo, **params)
    trades_oos = r["ltf_trades"] if isinstance(r, dict) else r
    e_oos = enrich(trades_oos, c1ho, c15o, None, None)

    cut_A_regime_age(e_oos, "OOS")
    cut_B_giveback(trades_oos, "OOS")
    cut_C_window_prod(e_oos, "OOS")
    cut_D_sequential(trades_oos, "OOS")
    cut_E_nearmiss(trades_oos, "OOS")
    cut_F_posthalt(trades_oos, "OOS")
    cut_H_preexpansion(e_oos, "OOS")
    cut_I_spacing(trades_oos, "OOS")
    cut_J_hold_profile(trades_oos, "OOS")

    print("\n(done %.0fs)" % (time.time() - t0))


if __name__ == "__main__":
    main()
