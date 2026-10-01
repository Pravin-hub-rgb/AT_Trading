"""Volume autopsy — does entry-time volume separate winners from losers?

Diagnostic only (trade-list buckets). Any promising gate must later go
path-true on champion/king/swingpause + OOS before it ships.

Features at entry bar (bar that CLOSED at entry_ts, i.e. last bar with ts <= entry_ts):
  vol        raw quote volume on that TF bar
  pct        trailing percentile of vol vs prior W bars (causal)
  rvol       vol / mean(prior W bars vol)  (relative volume)
  rvol_sum   sum(vol entry..entry+k) / sum(prior W) over next few bars (needs future — marked non-causal)
  win_vol    volume of the ENTRY candle only vs its own TF

Buckets: quintiles of each causal feature; also low/mid/high cuts.
Metrics: n / NET(gross R) / WR / R/t / avgW / avgL / PF / DD.

Run: python backtest/tests/exp_volume_autopsy.py
"""
import sys
import time
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backtest/tests"))

from src.btc.btc_config import load_btc_df
from src.btc.btc_routes import _compute_swings, _load_fine_1m
from src.btc.engines.htf_ltf.v18_streak_halt import simulate_htf_ltf_streak_halt
from src.walker import FlowCandle

INSTRUMENT = "BTCUSDT_BYBIT"
PARAMS = {
    "sl_buf_atr": 0.01,
    "ext_stop_r": 1.5,
    "mode": "b2_vs_flip_chop",
    "chop_thresh": 58.0,
    "cooldown_bars": 10,
    "max_consecutive_losses": 3,
}
ROLL_W = 96  # trailing window for percentile/rvol on 15m (~1 day); scaled per TF


def load_tf(tf):
    df = load_btc_df(tf, INSTRUMENT)
    candles, flow = [], []
    for row in df.itertuples():
        date = row.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        vol = float(getattr(row, "volume", 0.0) or 0.0)
        candles.append({
            "date": date,
            "ts": int(row.ts),
            "open": float(row.open),
            "high": float(row.high),
            "low": float(row.low),
            "close": float(row.close),
            "volume": vol,
        })
        flow.append(FlowCandle(date=date, open=float(row.open), high=float(row.high),
                               low=float(row.low), close=float(row.close)))
    return candles, flow


def build_vol_features(candles, roll_w):
    """Causal trailing features indexed by bar position."""
    n = len(candles)
    vols = [c.get("volume") or 0.0 for c in candles]
    # prefix sums for rolling mean
    pref = [0.0] * (n + 1)
    for i, v in enumerate(vols):
        pref[i + 1] = pref[i] + v

    pct = [50.0] * n
    rvol = [1.0] * n
    # rolling percentile via simple count of prior W values <= current (O(n*W) but W small)
    for i in range(n):
        lo = max(0, i - roll_w)
        if i - lo < 8:
            continue
        window = vols[lo:i]  # strictly prior bars (exclude current for causality of baseline)
        cur = vols[i]
        le = sum(1 for x in window if x <= cur)
        pct[i] = 100.0 * le / len(window)
        mean = (pref[i] - pref[lo]) / (i - lo)
        rvol[i] = (cur / mean) if mean > 0 else 1.0
    return {"vol": vols, "pct": pct, "rvol": rvol}


def ts_to_pos(ts, candles_by_ts, side="prev"):
    """Map entry_ts -> bar index whose close-time ts is <= entry (entry bar)."""
    # candles store open ts; entry is at bar close = open+step. Use searchsorted on open ts.
    return None  # filled by caller with bisect


def annotate(trades, feats15, c15, feats1h, c1h, feats5, c5):
    import bisect
    ts15 = [c["ts"] for c in c15]
    ts1h = [c["ts"] for c in c1h]
    ts5 = [c["ts"] for c in c5]

    def bar_at(ts_list, entry_ts, step):
        # entry bar: open_ts + step == entry_ts approximately (entry at close of bar
        # whose open is entry_ts - step). Find i with ts15[i] <= entry_ts - 0, prefer
        # bar whose close (= open+step) is the entry instant.
        target = entry_ts  # entry fires at bar close; bar open = entry_ts - step
        i = bisect.bisect_right(ts_list, target - step)
        # i-1 is last open <= target-step; that bar closes at open+step <= target
        # Prefer the bar that closes exactly at target if aligned
        if i - 1 >= 0 and ts_list[i - 1] + step == target:
            return i - 1
        # else last bar open < target (partially through next?) — use i-1
        return i - 1

    for t in trades:
        ets = int(t["entry_ts"])
        t["_r"] = float(t["r_multiple"])
        t["_win"] = t["_r"] > 0
        i15 = bar_at(ts15, ets, 900)
        i1h = bar_at(ts1h, ets, 3600)
        i5 = bar_at(ts5, ets, 300)
        t["_i15"] = i15
        t["_i1h"] = i1h
        t["_i5"] = i5
        if 0 <= i15 < len(c15):
            t["_v15"] = feats15["vol"][i15]
            t["_p15"] = feats15["pct"][i15]
            t["_rv15"] = feats15["rvol"][i15]
        else:
            t["_v15"] = t["_p15"] = t["_rv15"] = None
        if 0 <= i1h < len(c1h):
            t["_v1h"] = feats1h["vol"][i1h]
            t["_p1h"] = feats1h["pct"][i1h]
            t["_rv1h"] = feats1h["rvol"][i1h]
        else:
            t["_v1h"] = t["_p1h"] = t["_rv1h"] = None
        if 0 <= i5 < len(c5):
            t["_v5"] = feats5["vol"][i5]
            t["_p5"] = feats5["pct"][i5]
            t["_rv5"] = feats5["rvol"][i5]
        else:
            t["_v5"] = t["_p5"] = t["_rv5"] = None
        # next 4 bars volume sum on 15m (non-causal, for structure only)
        if 0 <= i15:
            s = 0.0
            for k in range(i15, min(i15 + 4, len(c15))):
                s += c15[k].get("volume") or 0.0
            t["_v15_next4"] = s
        else:
            t["_v15_next4"] = None
    return trades


def stats(rs):
    n = len(rs)
    if n == 0:
        return dict(n=0, net=0.0, wr=0.0, rpt=0.0, avgw=0.0, avgl=0.0, pf=0.0, dd=0.0)
    wins = [x for x in rs if x > 0]
    losses = [x for x in rs if x <= 0]
    net = sum(rs)
    peak = cum = dd = 0.0
    for x in rs:
        cum += x
        peak = max(peak, cum)
        dd = max(dd, peak - cum)
    pw = sum(wins)
    pl = abs(sum(losses))
    return dict(
        n=n,
        net=net,
        wr=100.0 * len(wins) / n,
        rpt=net / n,
        avgw=(pw / len(wins)) if wins else 0.0,
        avgl=(pl / len(losses)) if losses else 0.0,
        pf=(pw / pl) if pl > 0 else float("inf"),
        dd=dd,
    )


def show_table(title, rows, min_n=3):
    print(f"\n  === {title} ===")
    print(f"  {'bucket':<36} {'n':>4} {'NET':>8} {'WR%':>6} {'R/t':>7} "
          f"{'avgW':>7} {'avgL':>7} {'PF':>6} {'DD':>6}")
    for lab, rs in rows:
        s = stats(rs)
        if s["n"] == 0:
            continue
        if s["n"] < min_n and not lab.startswith("ALL"):
            continue
        pf = s["pf"]
        pf_s = f"{pf:6.2f}" if pf != float("inf") else "   inf"
        print(f"  {lab:<36} {s['n']:>4} {s['net']:>+8.1f} {s['wr']:>6.1f} "
              f"{s['rpt']:>+7.3f} {s['avgw']:>+7.2f} {s['avgl']:>+7.2f} "
              f"{pf_s} {s['dd']:>6.1f}")


def quintile_cut(vals, n_q=5):
    xs = sorted(v for v in vals if v is not None)
    if not xs:
        return []
    cuts = []
    for k in range(1, n_q):
        idx = int(len(xs) * k / n_q)
        cuts.append(xs[min(idx, len(xs) - 1)])
    return cuts


def bucket_by_cuts(trades, getv, cuts, labels):
    groups = defaultdict(list)
    for t in trades:
        v = getv(t)
        if v is None:
            continue
        b = 0
        for c in cuts:
            if v > c:
                b += 1
        groups[b].append(t["_r"])
    out = []
    for i, lab in enumerate(labels):
        out.append((lab, groups.get(i, [])))
    return out


def bucket_fixed(trades, getv, edges, labels):
    """edges: list of (lo, hi) inclusive-lo exclusive-hi; None = open."""
    groups = defaultdict(list)
    for t in trades:
        v = getv(t)
        if v is None:
            continue
        for i, (lo, hi) in enumerate(edges):
            if (lo is None or v >= lo) and (hi is None or v < hi):
                groups[i].append(t["_r"])
                break
    return [(labels[i], groups.get(i, [])) for i in range(len(labels))]


def main():
    t0 = time.time()
    print("=" * 100)
    print("  VOLUME AUTOPSY — entry-time volume buckets on baseline trade list")
    print("=" * 100)

    print("\n[load] 15m / 1h / 5m ...", flush=True)
    c15, f15 = load_tf("15m")
    c1h, f1h = load_tf("1h")
    c5, f5 = load_tf("5m")
    print(f"  15m={len(c15)}  1h={len(c1h)}  5m={len(c5)}  ({time.time()-t0:.0f}s)")

    print("[swings] + baseline sim ...", flush=True)
    sw15 = _compute_swings(f15, "continuous", min_bars=50)
    sw1h = _compute_swings(f1h, "continuous", min_bars=20)
    fine = _load_fine_1m(
        min(c1h[0]["ts"], c15[0]["ts"]),
        max(c1h[-1]["ts"], c15[-1]["ts"]),
        symbol=INSTRUMENT,
    )
    tr = simulate_htf_ltf_streak_halt(
        c1h, sw1h, c15, sw15,
        fine_ltf=fine,
        sl_buf_atr=PARAMS["sl_buf_atr"],
        ext_stop_r=PARAMS["ext_stop_r"],
        mode=PARAMS["mode"],
        chop_thresh=PARAMS["chop_thresh"],
        cooldown_bars=PARAMS["cooldown_bars"],
        max_consecutive_losses=PARAMS["max_consecutive_losses"],
    )["ltf_trades"]
    print(f"  baseline trades={len(tr)}  ({time.time()-t0:.0f}s)")

    print("[features] causal trailing vol percentile / rvol ...", flush=True)
    # windows scaled: 15m ~96 (1d), 1h ~24 (1d), 5m ~288 (1d)
    f15v = build_vol_features(c15, 96)
    f1hv = build_vol_features(c1h, 24)
    f5v = build_vol_features(c5, 288)
    annotate(tr, f15v, c15, f1hv, c1h, f5v, c5)

    base_all = [t["_r"] for t in tr]
    s_all = stats(base_all)
    print(f"\n  ALL: n={s_all['n']} NET={s_all['net']:+.1f} WR={s_all['wr']:.1f}% "
          f"R/t={s_all['rpt']:+.3f} PF={s_all['pf']:.2f} DD={s_all['dd']:.1f}")

    # Winner vs loser raw volume medians
    w = [t for t in tr if t["_win"]]
    l = [t for t in tr if not t["_win"]]
    def med(xs):
        xs = sorted(x for x in xs if x is not None)
        if not xs:
            return float("nan")
        m = len(xs) // 2
        return xs[m] if len(xs) % 2 else 0.5 * (xs[m - 1] + xs[m])
    print(f"\n  Winner median 15m vol: {med([t['_v15'] for t in w]):.1f}  "
          f"loser: {med([t['_v15'] for t in l]):.1f}")
    print(f"  Winner median 15m pct: {med([t['_p15'] for t in w]):.1f}  "
          f"loser: {med([t['_p15'] for t in l]):.1f}")
    print(f"  Winner median 15m rvol:{med([t['_rv15'] for t in w]):.2f}  "
          f"loser: {med([t['_rv15'] for t in l]):.2f}")
    print(f"  Winner median 1h  rvol:{med([t['_rv1h'] for t in w]):.2f}  "
          f"loser: {med([t['_rv1h'] for t in l]):.2f}")
    print(f"  Winner median 5m  rvol:{med([t['_rv5'] for t in w]):.2f}  "
          f"loser: {med([t['_rv5'] for t in l]):.2f}")

    # --- 15m percentile quintiles ---
    vals = [t["_p15"] for t in tr if t["_p15"] is not None]
    cuts = quintile_cut(vals, 5)
    labels = [f"pct15 Q{i+1} (<= {cuts[i]:.0f})" if i < len(cuts) else f"pct15 Q{i+1}"
              for i in range(5)]
    # rebuild labels properly
    labels = []
    prev = None
    for i in range(5):
        hi = cuts[i] if i < len(cuts) else None
        if prev is None and hi is not None:
            labels.append(f"pct15 Q{i+1} [{0:.0f},{hi:.0f})")
        elif hi is not None:
            labels.append(f"pct15 Q{i+1} [{prev:.0f},{hi:.0f})")
        else:
            labels.append(f"pct15 Q{i+1} [{prev:.0f},100]")
        prev = hi
    show_table("15m volume PERCENTILE quintiles (causal trailing 96)",
               bucket_by_cuts(tr, lambda t: t["_p15"], cuts, labels))

    # --- 15m rvol cuts ---
    show_table(
        "15m RVOL = vol / mean(prior 96)",
        bucket_fixed(
            tr,
            lambda t: t["_rv15"],
            [(None, 0.5), (0.5, 0.75), (0.75, 1.0), (1.0, 1.5), (1.5, 2.0), (2.0, None)],
            ["rvol <0.50", "0.50-0.75", "0.75-1.00", "1.00-1.50", "1.50-2.00", ">=2.00"],
        ),
    )

    # --- 1h rvol ---
    show_table(
        "1h RVOL = vol / mean(prior 24)",
        bucket_fixed(
            tr,
            lambda t: t["_rv1h"],
            [(None, 0.5), (0.5, 0.75), (0.75, 1.0), (1.0, 1.5), (1.5, 2.0), (2.0, None)],
            ["rvol1h <0.50", "0.50-0.75", "0.75-1.00", "1.00-1.50", "1.50-2.00", ">=2.00"],
        ),
    )

    # --- 1h percentile ---
    vals1h = [t["_p1h"] for t in tr if t["_p1h"] is not None]
    cuts1h = quintile_cut(vals1h, 5)
    labels1h = [f"pct1h Q{i+1}" for i in range(5)]
    show_table("1h volume PERCENTILE quintiles (trailing 24)",
               bucket_by_cuts(tr, lambda t: t["_p1h"], cuts1h, labels1h))

    # --- 5m rvol (entry candle micro) ---
    show_table(
        "5m RVOL = vol / mean(prior 288)",
        bucket_fixed(
            tr,
            lambda t: t["_rv5"],
            [(None, 0.5), (0.5, 0.75), (0.75, 1.0), (1.0, 1.5), (1.5, 2.0), (2.0, None)],
            ["rvol5m <0.50", "0.50-0.75", "0.75-1.00", "1.00-1.50", "1.50-2.00", ">=2.00"],
        ),
    )

    # --- absolute 15m vol quintiles ---
    vals_v = [t["_v15"] for t in tr if t["_v15"] is not None]
    cuts_v = quintile_cut(vals_v, 5)
    labels_v = [f"abs15 Q{i+1}" for i in range(5)]
    show_table("15m ABSOLUTE volume quintiles",
               bucket_by_cuts(tr, lambda t: t["_v15"], cuts_v, labels_v))

    # --- low volume + direction / kind cross ---
    print("\n  --- cross: low 15m rvol (<0.75) x kind ---", flush=True)
    for kind in ("B2", "FLIP"):
        sub = [t for t in tr if t.get("break_kind") == kind]
        lo = [t["_r"] for t in sub if t["_rv15"] is not None and t["_rv15"] < 0.75]
        hi = [t["_r"] for t in sub if t["_rv15"] is not None and t["_rv15"] >= 0.75]
        sl, sh = stats(lo), stats(hi)
        print(f"  {kind:5s} low-rvol  n={sl['n']:3d} NET={sl['net']:+7.1f} WR={sl['wr']:5.1f}%  | "
              f"hi-rvol n={sh['n']:3d} NET={sh['net']:+7.1f} WR={sh['wr']:5.1f}%")

    print("\n  --- cross: low 15m pct (<25) x direction ---", flush=True)
    for d in ("long", "short"):
        sub = [t for t in tr if t.get("dir") == d]
        lo = [t["_r"] for t in sub if t["_p15"] is not None and t["_p15"] < 25]
        hi = [t["_r"] for t in sub if t["_p15"] is not None and t["_p15"] >= 25]
        sl, sh = stats(lo), stats(hi)
        print(f"  {d:5s} low-pct   n={sl['n']:3d} NET={sl['net']:+7.1f} WR={sl['wr']:5.1f}%  | "
              f"rest n={sh['n']:3d} NET={sh['net']:+7.1f} WR={sh['wr']:5.1f}%")

    # --- next-4-bar 15m volume (non-causal structure) ---
    show_table(
        "NEXT 4 bars 15m vol sum quintiles (NON-CAUSAL structure)",
        bucket_by_cuts(
            tr,
            lambda t: t["_v15_next4"],
            quintile_cut([t["_v15_next4"] for t in tr if t["_v15_next4"] is not None], 5),
            [f"next4 Q{i+1}" for i in range(5)],
        ),
    )

    # --- hold-time x volume interaction ---
    print("\n  --- hold buckets x 15m rvol ---", flush=True)
    for lab, lo, hi in [("fast <12 bars", 0, 12), ("mid 12-48", 12, 48), ("slow >=48", 48, 10**9)]:
        sub = [t for t in tr if lo <= int(t.get("bars_held") or 0) < hi]
        for vlab, pred in [
            ("rvol<0.75", lambda t: t["_rv15"] is not None and t["_rv15"] < 0.75),
            ("rvol>=0.75", lambda t: t["_rv15"] is not None and t["_rv15"] >= 0.75),
        ]:
            rs = [t["_r"] for t in sub if pred(t)]
            s = stats(rs)
            if s["n"]:
                print(f"  {lab:<14} {vlab:<12} n={s['n']:3d} NET={s['net']:+7.1f} "
                      f"WR={s['wr']:5.1f}% R/t={s['rpt']:+.3f}")

    # --- year stability on the candidate cuts ---
    def year_of(t):
        return str(t.get("entry_date") or "")[:4]

    def year_table(title, preds):
        """preds: list of (label, predicate) — print year x pred NET/n."""
        years = sorted({year_of(t) for t in tr})
        print(f"\n  === {title} (year x pred) ===")
        hdr = f"  {'year':<6}"
        for lab, _ in preds:
            hdr += f" | {lab:>22}"
        print(hdr)
        for y in years:
            yt = [t for t in tr if year_of(t) == y]
            line = f"  {y:<6}"
            for lab, pred in preds:
                rs = [t["_r"] for t in yt if pred(t)]
                s = stats(rs)
                if s["n"] == 0:
                    line += f" | {'-':>22}"
                else:
                    line += f" | n={s['n']:3d} {s['net']:+7.1f} WR{s['wr']:4.0f}%"
            print(line)
        # all-years aggregate
        line = f"  {'ALL':<6}"
        for lab, pred in preds:
            rs = [t["_r"] for t in tr if pred(t)]
            s = stats(rs)
            line += f" | n={s['n']:3d} {s['net']:+7.1f} WR{s['wr']:4.0f}%"
        print(line)

    year_table(
        "B2 x 15m rvol",
        [
            ("B2 rvol<0.75", lambda t: t.get("break_kind") == "B2" and t["_rv15"] is not None and t["_rv15"] < 0.75),
            ("B2 rvol>=0.75", lambda t: t.get("break_kind") == "B2" and t["_rv15"] is not None and t["_rv15"] >= 0.75),
            ("FLIP rvol<0.75", lambda t: t.get("break_kind") == "FLIP" and t["_rv15"] is not None and t["_rv15"] < 0.75),
            ("FLIP rvol>=0.75", lambda t: t.get("break_kind") == "FLIP" and t["_rv15"] is not None and t["_rv15"] >= 0.75),
        ],
    )
    year_table(
        "skip candidates: pct15 Q1 / rvol15>=2 / abs15 Q5",
        [
            ("pct15<15 (Q1)", lambda t: t["_p15"] is not None and t["_p15"] < 15),
            ("rvol15>=2.0", lambda t: t["_rv15"] is not None and t["_rv15"] >= 2.0),
            ("short+pct<25", lambda t: t.get("dir") == "short" and t["_p15"] is not None and t["_p15"] < 25),
            ("1h rvol>=1.5", lambda t: t["_rv1h"] is not None and t["_rv1h"] >= 1.5),
        ],
    )

    # feature coverage
    miss = sum(1 for t in tr if t["_p15"] is None)
    print(f"\n  coverage: missing 15m vol feature: {miss}/{len(tr)}")
    print(f"(done in {time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
