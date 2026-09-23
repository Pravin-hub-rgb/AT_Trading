"""Validate deep-autopsy findings as filters + MFE/MAE path giveback.

Part 1 — Path autopsy (fine 1m): MFE, MAE, giveback for winners/losers
Part 2 — Trade-list filters tested on IS + OOS with proper sequential sim:
         F1  posthalt: skip entry when previous K taken trades all lost
         F2  regime-age: skip when age in 8..15 (stale mid)
         F3  after-win-only: only enter if previous taken trade won (or first)
         F4  gap-window: only enter when gap since prev entry in sweet spot
         F5  direction streak: skip after N same-dir losses
         F6+ combos of the above
Any cut must improve BOTH IS and OOS net (and ideally OOS/IS).
"""
import sys, json, math, time, bisect, calendar
from pathlib import Path
from datetime import datetime
from collections import defaultdict, Counter

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

from replay_harness import load_candles, INSTRUMENT
from engine.v18_params import SWING, get_v18_params, V18_ENGINE
from src.btc.btc_routes import _load_fine_1m, _compute_swings
from test_experiments_craze import build_module as build_craze, load_candles as load_is_c
from test_4_new_concepts import load_unseen, load_fine_1m as load_fine_unseen
from experiment_registry import EXPERIMENTS, BP

_P = dict(get_v18_params(INSTRUMENT)); _P.update(V18_ENGINE)


def d2ts(s):
    if not s:
        return None
    try:
        dt = datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S")
        return calendar.timegm(dt.timetuple()) - (5 * 3600 + 30 * 60)
    except Exception:
        return None


def enrich_age(trades, c1h):
    """Attach causal regime-age (1h bars since chop>=58 flip) using chop proxy."""
    # Use the engine's actual chop if available — approximate with rolling chop like autopsy2
    chop_th = 58.0

    def chop_at(i):
        if i < 14:
            return 50.0
        bars = c1h[i - 13:i + 1]
        hi = max(b["high"] for b in bars)
        lo = min(b["low"] for b in bars)
        if hi <= lo:
            return 50.0
        sum_tr = 0.0
        pc = bars[0]["close"]
        for b in bars:
            h, l, cl = b["high"], b["low"], b["close"]
            sum_tr += max(h - l, abs(h - pc), abs(l - pc))
            pc = cl
        rng = hi - lo
        if sum_tr <= 0 or rng <= 0:
            return 50.0
        return 100.0 * math.log10(sum_tr / rng) / math.log10(14)

    chop = [50.0] * len(c1h)
    for i in range(14, len(c1h)):
        chop[i] = chop_at(i)
    regime = [1 if ch >= chop_th else 0 for ch in chop]
    age = [999] * len(c1h)
    last = 0
    for i in range(1, len(c1h)):
        if regime[i] != regime[i - 1]:
            last = i
        age[i] = i - last

    ts_list = [c["ts"] for c in c1h]
    out = []
    for t in trades:
        ets = d2ts(t.get("entry_date", ""))
        meta = dict(t)
        meta["_ets"] = ets
        if ets is None:
            meta["_age"] = -1
            out.append(meta)
            continue
        # causal: last 1h bar fully closed before entry
        # bar closes at ts+3600
        hi = bisect.bisect_left(ts_list, ets) - 1
        # walk back so c1h[hi].ts + 3600 <= ets
        while hi >= 0 and ts_list[hi] + 3600 > ets:
            hi -= 1
        meta["_age"] = age[hi] if hi >= 0 else -1
        out.append(meta)
    return out


def stats(rs, label):
    n = len(rs)
    if n == 0:
        return dict(label=label, n=0, net=0, wr=0, avg=0, dd=0)
    net = sum(rs)
    wr = 100.0 * sum(1 for x in rs if x > 0) / n
    dd = 0.0
    peak = cum = 0.0
    for x in rs:
        cum += x
        peak = max(peak, cum)
        dd = max(dd, peak - cum)
    return dict(label=label, n=n, net=net, wr=wr, avg=net / n, dd=dd)


def print_rows(rows):
    print(f"  {'filter':<42} {'n':>5} {'net':>8} {'WR%':>6} {'avg':>7} {'dd':>6}")
    for r in rows:
        print(f"  {r['label']:<42} {r['n']:>5} {r['net']:>+8.1f} {r['wr']:>6.1f} {r['avg']:>+7.3f} {r['dd']:>6.1f}")


# ---------- sequential filters ----------

def sim_filters(trades_e, ages=None):
    """trades_e: enriched list with _r, _ets. Returns list of (label, r_list)."""
    rs = [m["_r"] for m in trades_e]
    n = len(rs)
    out = []

    out.append(("BASE", list(rs)))

    # F1 posthalt: skip trade when previous K taken trades all lost (on ORIGINAL sequence first,
    # then re-sim on kept)
    for K in (2, 3, 4):
        kept = []
        consec = 0
        for m in trades_e:
            if consec >= K:
                # skip — do not update consec (still in drought until a taken trade wins)
                # actually: skip means we don't take it; drought continues only if we don't count it.
                # Model A: skip exactly the trades where last K *original* taken were losses;
                # after skip, those K losses still count (market still bad until something wins).
                # We don't take, so consec stays K until we take a winner — but we never take.
                # Deadlock. Correct model: skip one trade after K losses, then reset counter
                # (cooldown-like single skip), OR skip while consec>=K but force-reset after skip count.
                # Match autopsy F: "after exactly K straight losses" using original sequence:
                pass
        # autopsy definition: skip i if previous K ORIGINAL trades all lost
        kept = [m["_r"] for i, m in enumerate(trades_e)
                if i < K or all(trades_e[i - K + j]["_r"] <= 0 for j in range(K))]
        # wait: "exactly K" means r[i-K] > 0 if i>K. Autopsy used run==K before i.
        kept2 = []
        for i, m in enumerate(trades_e):
            j = i - 1
            run = 0
            while j >= 0 and trades_e[j]["_r"] <= 0:
                run += 1
                j -= 1
            if run == K:
                continue  # skip
            kept2.append(m["_r"])
        out.append((f"F1_posthalt_skip K={K} (orig-seq)", kept2))

        # Model B: online — track consec of KEPT trades; if consec>=K, skip (don't count);
        # after skipping M=1 such candidate, allow next (or force trade after K+1 skip)
        for skip_mode in ("skip1", "skip_until_win"):
            kept = []
            consec = 0
            skipped_pending = 0
            for m in trades_e:
                if consec >= K:
                    if skip_mode == "skip1":
                        # skip exactly one candidate then re-arm
                        consec = 0  # treat as cooldown break
                        skipped_pending = 1
                        # reset: after skipping 1, subsequent trades allowed with consec=0
                        continue
                    else:
                        # skip until we would need a win — but we skip so never win → deadlock
                        # skip until K more original candidates pass, then reset
                        skipped_pending += 1
                        if skipped_pending >= 1:
                            consec = 0
                            skipped_pending = 0
                        continue
                kept.append(m["_r"])
                if m["_r"] <= 0:
                    consec += 1
                else:
                    consec = 0
            out.append((f"F1_{skip_mode} K={K} (online)", kept))

    # F2 regime-age skip (stale mid 8..15) — uses _age on enriched trades
    if any(m.get("_age", -1) >= 0 for m in trades_e):
        for lo, hi in [(8, 15), (8, 99), (7, 15), (8, 20)]:
            kept = [m["_r"] for m in trades_e if not (lo <= m.get("_age", -1) <= hi)]
            out.append((f"F2_skip_age[{lo},{hi}]", kept))
            kept = [m["_r"] for m in trades_e if lo <= m.get("_age", -1) <= hi]
            out.append((f"F2_only_age[{lo},{hi}]", kept))
        kept = [m["_r"] for m in trades_e if 0 <= m.get("_age", -1) <= 7]
        out.append(("F2_only_age[0,7] fresh<=7", kept))
        kept = [m["_r"] for m in trades_e if m.get("_age", -1) < 8 or m.get("_age", -1) >= 16]
        out.append(("F2_cut_age[8,15]", kept))

    # F3 after-win only (online on original sequence for eligibility)
    # take trade i if i==0 or trades[i-1] > 0  (original prev)
    kept = [m["_r"] for i, m in enumerate(trades_e) if i == 0 or trades_e[i - 1]["_r"] > 0]
    out.append(("F3_after_win_only (orig prev)", kept))
    # online on kept: only if last KEPT won
    kept = []
    for i, m in enumerate(trades_e):
        if not kept or kept[-1] > 0:
            kept.append(m["_r"])
    out.append(("F3_after_win_only (kept prev)", kept))
    # not after 2+ losses (orig)
    kept = []
    for i, m in enumerate(trades_e):
        streak = 0
        j = i - 1
        while j >= 0 and trades_e[j]["_r"] <= 0:
            streak += 1
            j -= 1
        if streak >= 2:
            continue
        kept.append(m["_r"])
    out.append(("F3_skip_after_2+losses (orig)", kept))

    # F4 gap windows (need _ets)
    gaps = []
    prev = None
    for m in trades_e:
        if m.get("_ets") and prev:
            gaps.append((m["_ets"] - prev) / 3600.0)
        else:
            gaps.append(None)
        if m.get("_ets"):
            prev = m["_ets"]
    for name, pred in [
        ("F4_keep_gap_2-8h", lambda g: g is not None and 2 <= g < 8),
        ("F4_keep_gap_0.5-24h", lambda g: g is not None and 0.5 <= g < 24),
        ("F4_skip_gap_1-3d", lambda g: g is None or not (24 <= g < 72)),
        ("F4_skip_gap_gt24h", lambda g: g is None or g < 24),
        ("F4_skip_gap_gt48h", lambda g: g is None or g < 48),
    ]:
        kept = [trades_e[i]["_r"] for i, g in enumerate(gaps) if pred(g)]
        out.append((name, kept))

    # F5 direction streak: skip when last K trades all same dir and all losses
    for K in (2, 3):
        kept = []
        for i, m in enumerate(trades_e):
            d = m.get("dir")
            ok = True
            if i >= K:
                prevs = trades_e[i - K:i]
                if all(p["_r"] <= 0 and p.get("dir") == d for p in prevs):
                    ok = False
            if ok:
                kept.append(m["_r"])
        out.append((f"F5_skip_{K}same-dir-losses", kept))

    return out


def combo_filters(trades_e, ages=None):
    """Combos that looked good individually."""
    out = []

    def age_ok(m, lo=8, hi=15):
        a = m.get("_age", -1)
        return not (lo <= a <= hi)

    def posthalt_orig(m, i, K=3):
        j = i - 1
        run = 0
        while j >= 0 and trades_e[j]["_r"] <= 0:
            run += 1
            j -= 1
        return run == K

    # C1: cut stale age + posthalt K=3
    kept = [m["_r"] for i, m in enumerate(trades_e)
            if (ages is None or age_ok(m)) and not posthalt_orig(m, i, 3)]
    out.append(("C1_cut_age[8,15] + posthalt3", kept))

    # C2: after-win + cut age
    kept = []
    for i, m in enumerate(trades_e):
        if ages is not None and not age_ok(m):
            continue
        if i > 0 and trades_e[i - 1]["_r"] <= 0:
            continue
        kept.append(m["_r"])
    out.append(("C2_after_win + cut_age[8,15]", kept))

    # C3: skip after 2+ losses + cut age
    kept = []
    for i, m in enumerate(trades_e):
        if ages is not None and not age_ok(m):
            continue
        streak = 0
        j = i - 1
        while j >= 0 and trades_e[j]["_r"] <= 0:
            streak += 1
            j -= 1
        if streak >= 2:
            continue
        kept.append(m["_r"])
    out.append(("C3_skip_after2loss + cut_age", kept))

    # C4: skip gap>72h only (simple, keeps most)
    prev = None
    kept = []
    for m in trades_e:
        g = None
        if m.get("_ets") and prev:
            g = (m["_ets"] - prev) / 3600.0
        if m.get("_ets"):
            prev = m["_ets"]
        if g is not None and g >= 72:
            continue
        kept.append(m["_r"])
    out.append(("C4_skip_gap>=72h", kept))

    # C5: posthalt3 + skip_gap>=72
    kept = []
    prev = None
    for i, m in enumerate(trades_e):
        g = None
        if m.get("_ets") and prev:
            g = (m["_ets"] - prev) / 3600.0
        if m.get("_ets"):
            prev = m["_ets"]
        if g is not None and g >= 72:
            continue
        if posthalt_orig(m, i, 3):
            continue
        kept.append(m["_r"])
    out.append(("C5_posthalt3 + skip_gap>=72", kept))

    # C6: age0-7 only + posthalt3
    if ages is not None:
        kept = [m["_r"] for i, m in enumerate(trades_e)
                if 0 <= m.get("_age", -1) <= 7 and not posthalt_orig(m, i, 3)]
        out.append(("C6_age[0,7] + posthalt3", kept))

    # C7: after-win + skip gap>=72
    kept = []
    prev = None
    for i, m in enumerate(trades_e):
        g = None
        if m.get("_ets") and prev:
            g = (m["_ets"] - prev) / 3600.0
        if m.get("_ets"):
            prev = m["_ets"]
        if g is not None and g >= 72:
            continue
        if i > 0 and trades_e[i - 1]["_r"] <= 0:
            continue
        kept.append(m["_r"])
    out.append(("C7_after_win + skip_gap>=72", kept))

    # C8: E[R after win] gate — take trade only if prev won OR (prev lost and age fresh<=7)
    if ages is not None:
        kept = []
        for i, m in enumerate(trades_e):
            a = m.get("_age", -1)
            if i == 0:
                kept.append(m["_r"]); continue
            prev_win = trades_e[i - 1]["_r"] > 0
            if prev_win or (0 <= a <= 7):
                kept.append(m["_r"])
        out.append(("C8_after_win OR age_fresh", kept))

    return out


def mae_mfe_path(trades, c15, fine, label):
    """Compute MFE/MAE on fine path for each trade."""
    # index fine by ts
    if not fine:
        print(f"  [{label}] no fine data")
        return
    fts = [f["ts"] for f in fine]
    results = []
    for t in trades:
        ets = d2ts(t.get("entry_date", ""))
        xts = d2ts(t.get("exit_date", ""))
        if ets is None or xts is None:
            continue
        i0 = bisect.bisect_left(fts, ets)
        i1 = bisect.bisect_right(fts, xts)
        if i1 <= i0:
            continue
        entry = float(t["entry_price"])
        sl = float(t.get("sl") or entry)
        risk = abs(entry - sl)
        if risk <= 0:
            continue
        d = 1 if t.get("dir") == "long" else -1
        mfe = 0.0
        mae = 0.0
        for f in fine[i0:i1]:
            h, lo = float(f["high"]), float(f["low"])
            up = (h - entry) * d / risk
            dn = (entry - lo) * d / risk  # favorable if positive for... wait
            # MAE = adverse: for long, (entry-lo)/risk; for short, (h-entry)/risk
            adv = ((entry - lo) if d == 1 else (h - entry)) / risk
            fav = ((h - entry) if d == 1 else (entry - lo)) / risk
            mfe = max(mfe, fav)
            mae = min(mae, -abs(adv) if adv > 0 else 0.0) if False else min(mae, -max(adv, 0.0))
        r = float(t["r_multiple"])
        results.append((r, mfe, mae, t))

    wins = [(r, mfe, mae, t) for r, mfe, mae, t in results if r > 0]
    losses = [(r, mfe, mae, t) for r, mfe, mae, t in results if r <= 0]
    print(f"\n  --- MFE/MAE path ({label}) ---")
    print(f"  n={len(results)}")
    if wins:
        gb = [mfe - r for r, mfe, mae, t in wins]
        print(f"  WINNERS n={len(wins)}  avgMFE={sum(m for _,m,_,_ in wins)/len(wins):.2f}  "
              f"avgR={sum(r for r,_,_,_ in wins)/len(wins):.2f}  "
              f"avgGiveback={sum(gb)/len(gb):.2f}  "
              f"totalLeft={sum(gb):.1f}R")
        big = [(r, mfe) for r, mfe, _, _ in wins if mfe >= 3]
        if big:
            print(f"  MFE>=3R: n={len(big)}  avgMFE={sum(m for _,m in big)/len(big):.2f}  "
                  f"avgExitR={sum(r for r,_ in big)/len(big):.2f}  "
                  f"left={sum(m-r for r,m in big):.1f}R")
    if losses:
        # losers that had MFE>=1 before dying
        almost = [(r, mfe) for r, mfe, mae, t in losses if mfe >= 1.0]
        underwater = [mae for r, mfe, mae, t in losses]
        print(f"  LOSERS n={len(losses)}  avgMFE={sum(m for _,m,_,_ in losses)/len(losses):.2f}  "
              f"avgMAE={sum(mae for _,_,mae,_ in losses)/len(losses):.2f}")
        print(f"  losers with MFE>=1R before death: n={len(almost)}  "
              f"sumMFE={sum(m for _,m in almost):.1f}R  avgMFE={sum(m for _,m in almost)/max(len(almost),1):.2f}")
        mfe2 = [(r, mfe) for r, mfe, _, _ in losses if mfe >= 2.0]
        print(f"  losers with MFE>=2R: n={len(mfe2)}  sumMFE={sum(m for _,m in mfe2):.1f}R")

        # giveback on winners by hold time
        for name, pred in [("hold<=24", lambda t: int(t.get("bars_held") or 0) <= 24),
                           ("hold24-96", lambda t: 24 < int(t.get("bars_held") or 0) <= 96),
                           ("hold>96", lambda t: int(t.get("bars_held") or 0) > 96)]:
            sub = [(r, mfe) for r, mfe, mae, t in wins if pred(t)]
            if sub:
                print(f"  winners {name}: n={len(sub)} avgMFE={sum(m for _,m in sub)/len(sub):.2f} "
                      f"avgR={sum(r for r,_ in sub)/len(sub):.2f} left={sum(m-r for r,m in sub):.1f}R")


def main():
    t0 = time.time()
    print("=" * 100)
    print("  AUTOPSY VALIDATION — filters + MFE/MAE path")
    print("=" * 100)

    # IS
    p = ROOT / "live_stuff/tests/_exp_champion_multi_sw10_results.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    trades_is = data["trades"]
    (c15, f15), (c1h, f1h) = load_is_c()
    e_is = enrich_age(trades_is, c1h)
    for m in e_is:
        m["_r"] = float(m["r_multiple"])

    rows_is = sim_filters(e_is) + combo_filters(e_is)
    print("\n" + "#" * 90)
    print("#  IS 2023-2026")
    print("#" * 90)
    print_rows([stats(rs, lab) for lab, rs in rows_is])

    # OOS fresh
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
    e_oos = enrich_age(trades_oos, c1ho)
    for m in e_oos:
        m["_r"] = float(m["r_multiple"])

    rows_oos = sim_filters(e_oos) + combo_filters(e_oos)
    print("\n" + "#" * 90)
    print("#  TRUE OOS 2021-2022")
    print("#" * 90)
    print_rows([stats(rs, lab) for lab, rs in rows_oos])

    # paired comparison
    print("\n" + "#" * 90)
    print("#  PAIRED (same filter label) — want net_is AND net_oos both up vs BASE")
    print("#" * 90)
    d_is = {lab: stats(rs, lab) for lab, rs in rows_is}
    d_oos = {lab: stats(rs, lab) for lab, rs in rows_oos}
    base_is = d_is["BASE"]["net"]
    base_oos = d_oos["BASE"]["net"]
    print(f"  BASE IS={base_is:+.1f}  OOS={base_oos:+.1f}  OOS/IS={100*base_oos/max(base_is,1e-9):.0f}%")
    print(f"  {'filter':<42} {'dIS':>8} {'dOOS':>8} {'OOS%':>6} {'verdict':>10}")
    for lab in d_is:
        if lab not in d_oos or lab == "BASE":
            continue
        a, b = d_is[lab], d_oos[lab]
        di = a["net"] - base_is
        do = b["net"] - base_oos
        ratio = 100 * b["net"] / max(a["net"], 1e-9) if a["net"] > 0 else -999
        # keep only if improves or neutral IS and clearly helps OOS, or big IS with OOS not worse
        verdict = ""
        if di >= -5 and do >= 5:
            verdict = "BOTH_UP"
        elif do >= 10 and di >= -20:
            verdict = "OOS_UP"
        elif di >= 20 and do >= -5:
            verdict = "IS_UP_OOS_OK"
        else:
            verdict = "no"
        if verdict != "no" or abs(do) >= 10:
            print(f"  {lab:<42} {di:>+8.1f} {do:>+8.1f} {ratio:>5.0f}% {verdict:>10}")

    # MFE path
    print("\n" + "#" * 90)
    print("#  MFE/MAE PATH")
    print("#" * 90)
    fine_is = load_fine_unseen(c15[0]["ts"], c15[-1]["ts"])  # same loader works on any range?
    # careful: load_fine_unseen may be for unseen path only — check
    try:
        mae_mfe_path(trades_is, c15, fine_is, "IS")
    except Exception as e:
        print(f"  IS path error: {e}")
        # fallback: _load_fine_1m from btc_routes
        try:
            fine_is2 = _load_fine_1m(c15[0]["ts"], c15[-1]["ts"])
            mae_mfe_path(trades_is, c15, fine_is2, "IS")
        except Exception as e2:
            print(f"  IS fallback error: {e2}")
    mae_mfe_path(trades_oos, c15o, fineo, "OOS")

    # also utcsat IS from json if exists
    pu = ROOT / "live_stuff/tests/_exp_utcsat_multi_sw10_results.json"
    if pu.exists():
        du = json.loads(pu.read_text(encoding="utf-8"))
        e_u = enrich_age(du["trades"], c1h)
        for m in e_u:
            m["_r"] = float(m["r_multiple"])
        rows_u = sim_filters(e_u) + combo_filters(e_u)
        print("\n" + "#" * 90)
        print("#  utcsat_multi IS (sanity — patterns should hold)")
        print("#" * 90)
        base_u = next(stats(rs, l) for l, rs in rows_u if l == "BASE")
        print(f"  BASE utcsat IS net={base_u['net']:+.1f}")
        d_u = {lab: stats(rs, lab) for lab, rs in rows_u}
        for lab, rs in rows_u:
            if lab in d_is:
                di = d_u[lab]["net"] - base_u["net"]
                if abs(di) >= 5 or lab == "BASE":
                    print(f"  {lab:<42} net={d_u[lab]['net']:+.1f}  d={di:+.1f}")

    print("\n(done %.0fs)" % (time.time() - t0))


if __name__ == "__main__":
    main()
