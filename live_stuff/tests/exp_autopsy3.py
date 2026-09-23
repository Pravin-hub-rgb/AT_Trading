"""Autopsy v3 — structural cuts we still haven't done.

  W. HTF-window sequential: trade index within a window streak, first vs later,
     after-win inside window, after-loss inside window  (the flip-vs-b2 level cut)
  X. After-win causality: can we KNOW prev outcome before next entry?
     (single-position => prev must have exited; check timestamp overlaps)
  Y. MAE early-exit path sim: exit at -0.5R if MFE never reached +X
     (surgery on the 163 trail-losers / almost-dead trades)
  Z. Trail-loser autopsy: outcome=trail & r<=0 — path profile vs hard SL
  F2. Fixed regime-age filter (was silently skipped in validate)

Run: python -m live_stuff.tests.exp_autopsy3
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
from src.btc.btc_routes import _compute_swings
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


def stats_of(rs):
    n = len(rs)
    if n == 0:
        return 0, 0, 0, 0
    net = sum(rs)
    wr = 100.0 * sum(1 for x in rs if x > 0) / n
    peak = cum = dd = 0.0
    for x in rs:
        cum += x
        peak = max(peak, cum)
        dd = max(dd, peak - cum)
    return n, net, wr, dd


def print_bucket(title, rows):
    print(f"\n  --- {title} ---")
    print(f"  {'bucket':<28} {'n':>5} {'net':>8} {'WR%':>6} {'avg':>7} {'dd':>6}")
    for lab, rs in rows:
        n, net, wr, dd = stats_of(rs)
        if n == 0:
            continue
        print(f"  {lab:<28} {n:>5} {net:>+8.1f} {wr:>6.1f} {net/n:>+7.3f} {dd:>6.1f}")


def enrich_base(trades):
    out = []
    for t in trades:
        m = dict(t)
        m["_r"] = float(t["r_multiple"])
        m["_ets"] = d2ts(t.get("entry_date", ""))
        m["_xts"] = d2ts(t.get("exit_date", ""))
        out.append(m)
    return out


def window_streaks(metas, gap_h=48.0):
    """Group consecutive-in-time trades into streaks (proxy for live window / regime run).
    New streak if gap >= gap_h OR direction flips after a loss (heuristic).
    Primary rule: gap only — keep it simple and causal.
    """
    streaks = []
    cur = []
    prev_exit = None
    for m in metas:
        if cur and m["_ets"] is not None and prev_exit is not None:
            gap = (m["_ets"] - prev_exit) / 3600.0
            if gap >= gap_h:
                streaks.append(cur)
                cur = []
        cur.append(m)
        if m["_xts"] is not None:
            prev_exit = m["_xts"]
        elif m["_ets"] is not None:
            prev_exit = m["_ets"]
    if cur:
        streaks.append(cur)
    # annotate index within streak + prev outcomes within streak
    for si, st in enumerate(streaks):
        for i, m in enumerate(st):
            m["_sid"] = si
            m["_sidx"] = i  # 0 = first in streak
            m["_sprev_r"] = st[i - 1]["_r"] if i > 0 else None
            m["_swins_before"] = sum(1 for j in range(i) if st[j]["_r"] > 0)
            m["_slosses_before"] = sum(1 for j in range(i) if st[j]["_r"] <= 0)
    return streaks


def cut_window(seqs, label):
    rows = []
    rows.append(("all", [m["_r"] for m in seqs]))
    rows.append(("streak_idx=0 first", [m["_r"] for m in seqs if m["_sidx"] == 0]))
    rows.append(("streak_idx=1", [m["_r"] for m in seqs if m["_sidx"] == 1]))
    rows.append(("streak_idx=2", [m["_r"] for m in seqs if m["_sidx"] == 2]))
    rows.append(("streak_idx>=3", [m["_r"] for m in seqs if m["_sidx"] >= 3]))
    rows.append(("prev_in_streak WIN", [m["_r"] for m in seqs if m["_sprev_r"] is not None and m["_sprev_r"] > 0]))
    rows.append(("prev_in_streak LOSS", [m["_r"] for m in seqs if m["_sprev_r"] is not None and m["_sprev_r"] <= 0]))
    rows.append(("first+afterWIN only", [m["_r"] for m in seqs if m["_sprev_r"] is None or m["_sprev_r"] > 0]))
    rows.append(("skip if >=2 losses before", [m["_r"] for m in seqs if m["_slosses_before"] < 2]))
    rows.append(("skip if >=1 loss before", [m["_r"] for m in seqs if m["_slosses_before"] < 1]))
    rows.append(("wins_before>=1", [m["_r"] for m in seqs if m["_swins_before"] >= 1]))
    print_bucket(f"W. Window-streak sequential — {label}", rows)

    # streak-level: net per streak, length distribution
    by_streak = defaultdict(list)
    for m in seqs:
        by_streak[m["_sid"]].append(m["_r"])
    lens = [len(v) for v in by_streak.values()]
    nets = [sum(v) for v in by_streak.values()]
    print(f"  streaks={len(by_streak)}  avg_len={sum(lens)/max(len(lens),1):.2f}  "
          f"max_len={max(lens) if lens else 0}  "
          f"streak_net: avg={sum(nets)/max(len(nets),1):+.2f}  "
          f"pos={sum(1 for x in nets if x>0)}/{len(nets)}")
    # first trade of streak vs rest
    first = [sum(v[:1]) for v in by_streak.values()]
    rest = [sum(v[1:]) for v in by_streak.values() if len(v) > 1]
    print(f"  first-trade-of-streak: n={len(first)} net={sum(first):+.1f} avg={sum(first)/max(len(first),1):+.2f}")
    print(f"  rest-of-streak:        n={len(rest)} net={sum(rest):+.1f} avg={sum(rest)/max(len(rest),1):+.2f}")


def causality_after_win(metas, label):
    """If single-position, next entry ts >= prev exit ts. Count violations.
    Also: prev OUTCOME is known only after exit — if entry before exit, leak.
    """
    # sort by entry
    srt = sorted([m for m in metas if m["_ets"] is not None], key=lambda m: m["_ets"])
    viol = 0
    known = 0
    unknown = 0
    for a, b in zip(srt, srt[1:]):
        # prev trade for b is the previous by ENTRY, which may not be a's exit if a opened later
        # proper: last trade by EXIT before b's entry
        pass
    # find for each trade the previous trade that fully exited before its entry
    by_exit = sorted([m for m in metas if m["_xts"] is not None], key=lambda m: m["_xts"])
    leak = 0
    ok_prev = 0
    no_prev = 0
    after_win_known = []
    for m in srt:
        # previous completed trade
        prev = None
        for p in by_exit:
            if p["_xts"] <= m["_ets"]:
                prev = p
            else:
                break
        if prev is None:
            no_prev += 1
            m["_prev_completed_r"] = None
        else:
            ok_prev += 1
            m["_prev_completed_r"] = prev["_r"]
        # overlapping: any trade open at m's entry (entered before, exited after)
        # single-position engine => should be 0
    # overlap check using entry/exit intervals
    overlaps = 0
    for i in range(len(srt)):
        for j in range(i + 1, len(srt)):
            a, b = srt[i], srt[j]
            if a["_xts"] is None or b["_xts"] is None:
                continue
            if a["_ets"] < b["_xts"] and b["_ets"] < a["_xts"]:
                overlaps += 1
            if b["_ets"] >= a["_xts"]:
                break  # sorted by entry — further j all enter later; still could overlap a if a long
    # simpler full overlap count
    overlaps = 0
    for i, a in enumerate(srt):
        for b in srt[i + 1:]:
            if a["_xts"] and b["_xts"] and a["_ets"] < b["_xts"] and b["_ets"] < a["_xts"]:
                overlaps += 1
    print(f"\n  --- X. After-win causality — {label} ---")
    print(f"  trades={len(srt)}  prev_completed_found={ok_prev}  no_prev={no_prev}  "
          f"entry-overlaps={overlaps} (want 0 for single-pos)")
    # E[R] using prev COMPLETED (causal) vs prev by entry (possibly leaky)
    causal = [(m["_r"], m["_prev_completed_r"]) for m in srt if m.get("_prev_completed_r") is not None]
    aw = [r for r, pr in causal if pr > 0]
    al = [r for r, pr in causal if pr <= 0]
    print(f"  causal prev-completed: afterWIN n={len(aw)} net={sum(aw):+.1f} avg={sum(aw)/max(len(aw),1):+.3f}")
    print(f"                         afterLOSS n={len(al)} net={sum(al):+.1f} avg={sum(al)/max(len(al),1):+.3f}")
    # filter: only after win (causal)
    kept = [m["_r"] for m in srt if m.get("_prev_completed_r") is None or m["_prev_completed_r"] > 0]
    n, net, wr, dd = stats_of(kept)
    print(f"  F3c_after_win_completed_or_first: n={n} net={net:+.1f} WR={wr:.1f}% DD={dd:.1f}")
    return srt


def mae_surgery(metas, fine, label):
    """Path sim: for each trade compute MFE/MAE; test early exits.
    Rules:
      S1  exit at -0.5R hard (ignore path) — kills all -1R at -0.5 (half the loss) but
          also cuts winners that dip first — need path order.
      S2  exit at -0.5R ONLY if MFE never reached +1R before that -0.5 touch
      S3  exit at breakeven after MFE>=+1R when price returns to entry (classic BE)
      S4  exit at -0.35R if still no +0.5R after N fine bars (time stop on dead trades)
    Uses fine path sequential — causal.
    """
    if not fine:
        print(f"  [{label}] no fine — skip surgery")
        return
    fts = [f["ts"] for f in fine]
    print(f"\n  --- Y/Z. MAE surgery + trail-loser path — {label} ---")

    trail_losers = []
    sl_losers = []
    winners = []
    surg = {k: [] for k in ["S0_base", "S1_half_sl_path", "S2_be_after_1R", "S3_dead_time"]}
    surg_trail_only = {k: [] for k in ["S0_base", "S2_be_after_1R"]}

    for m in metas:
        ets, xts = m["_ets"], m["_xts"]
        r = m["_r"]
        if ets is None or xts is None:
            for k in surg:
                surg[k].append(r)
            continue
        i0 = bisect.bisect_left(fts, ets)
        i1 = bisect.bisect_right(fts, xts)
        if i1 <= i0:
            for k in surg:
                surg[k].append(r)
            continue
        entry = float(m["entry_price"])
        sl = float(m.get("sl") or entry)
        risk = abs(entry - sl)
        if risk <= 0:
            for k in surg:
                surg[k].append(r)
            continue
        d = 1 if m.get("dir") == "long" else -1

        mfe = 0.0
        mae_touch_be = False  # price returned to entry after MFE>=1
        be_hit = False
        dead_hit = False  # hit -0.5 without ever +1
        half_sl = False    # hit -0.5 at all (path-aware: we always would with half SL)
        exit_r_S1 = None
        exit_r_S2 = None
        exit_r_S3 = None
        exit_r_S4 = None
        path_bars = fine[i0:i1]
        n_fine = len(path_bars)

        # simulate
        # S1: hard stop at -0.5R (replace -1R) — first touch
        # S2: BE after +1R — when MFE>=1 and price crosses entry again, exit ~0 + costs
        # S3: if reach -0.5R while mfe<1, exit there (early dead); else run base
        for bi, f in enumerate(path_bars):
            h, lo = float(f["high"]), float(f["low"])
            fav_up = ((h - entry) if d == 1 else (entry - lo)) / risk
            fav_dn = ((entry - lo) if d == 1 else (h - entry)) / risk  # adverse progress
            mfe = max(mfe, fav_up)
            # adverse touch levels
            # for long: adverse = (entry-lo)/risk; for short: (h-entry)/risk
            adv = fav_dn
            # S1 half SL at -0.5
            if exit_r_S1 is None and adv >= 0.5:
                exit_r_S1 = -0.5
            # S3 dead early: -0.5 before +1
            if exit_r_S4 is None and adv >= 0.5 and mfe < 1.0:
                exit_r_S4 = -0.5
            # S2 BE: after mfe>=1, price back to entry (adv such that close<=entry for long)
            if not be_hit and mfe >= 1.0:
                # touch entry from above
                if d == 1 and lo <= entry:
                    be_hit = True
                    exit_r_S2 = 0.0
                if d == -1 and h >= entry:
                    be_hit = True
                    exit_r_S2 = 0.0

            if exit_r_S1 is not None and exit_r_S2 is not None and exit_r_S4 is not None:
                # continue only if need mfe for stats — can break if all set
                if exit_r_S1 is not None and exit_r_S4 is not None and (be_hit or True):
                    pass

        # For trades where path didn't trigger early exit, use base r
        # S1: if half SL touched before natural exit, r = min(r, -0.5) — actually
        # if natural was -1 (sl), half gives -0.5; if natural was winner that dipped
        # -0.5 first then won, half SL would have exited at -0.5 (lost winner).
        # Need first-touch order: did -0.5 touch happen BEFORE the conditions of base exit?
        # Approximate: if exit_r_S1 set AND (r < 0 or mfe < 1): if the trade ever touched -0.5
        # before finishing positive without dipping... For winners that never touch -0.5, S1=r.
        # For losers -1, S1=-0.5. For winners that touch -0.5 first, S1=-0.5 (bad).
        # Detect: winner with adverse>=0.5 sometime — approx mae.
        # Recompute mae
        mae = 0.0
        mfe2 = 0.0
        touched_be_after_1r = False
        mfe_reached_1_before_adv_half = False
        adv_half_before_mfe1 = False
        seen_mfe1 = False
        for f in path_bars:
            h, lo = float(f["high"]), float(f["low"])
            if d == 1:
                fav = (h - entry) / risk
                adv = (entry - lo) / risk
            else:
                fav = (entry - lo) / risk
                adv = (h - entry) / risk
            mfe2 = max(mfe2, fav)
            mae = min(mae, -max(adv, 0.0) if False else mae)
            mae = min(mae, -adv)  # negative adverse
            if mfe2 >= 1.0:
                seen_mfe1 = True
            if adv >= 0.5 and not seen_mfe1:
                adv_half_before_mfe1 = True
            if seen_mfe1 and not adv_half_before_mfe1:
                # check BE touch after mfe1 — approximated at end via be_hit above
                pass

        # S1: always half the initial risk if we re-place SL at -0.5 from start
        # -> any trade that ever touches -0.5 exits at -0.5; trades that don't touch keep r
        # touch -0.5: for losers with r~-1 always yes (unless gap). for winners dipping: yes if mae<=-0.5
        touches_half = (mae <= -0.5) or (r <= -0.5)
        if touches_half:
            # if winner dipped to -0.5 before winning, half SL exits -0.5
            if r > 0:
                s1 = -0.5  # killed winner
            else:
                s1 = max(r, -0.5)  # -1 -> -0.5
        else:
            s1 = r
        # Actually for r>0 winners that never touch -0.5, s1=r. touches_half false. good.
        # For r>0 that dipped -0.5, s1=-0.5. good.
        # For r<0, if r>=-0.5 already, max(r,-0.5)=r; if r<-0.5, -0.5. good enough.

        # S2: BE after +1R — need path: if mfe>=1 and price returned to entry, exit~0;
        # else base r. Approximate BE return: mfe>=1 and (r < mfe) and mae >= -0.05 after?
        # Better use be_hit from first loop — recompute cleanly
        be_hit = False
        mfe_p = 0.0
        seen1 = False
        for f in path_bars:
            h, lo = float(f["high"]), float(f["low"])
            if d == 1:
                fav = (h - entry) / risk
                # return to entry after being above
                if seen1 and lo <= entry:
                    be_hit = True
                    break
                if fav >= 1.0:
                    seen1 = True
            else:
                fav = (entry - lo) / risk
                if seen1 and h >= entry:
                    be_hit = True
                    break
                if fav >= 1.0:
                    seen1 = True
        if be_hit:
            s2 = 0.0  # ignore costs for surgery estimate
        else:
            s2 = r

        # S4: dead early exit at -0.5 if never reached +1 before touching -0.5
        # if adv_half_before_mfe1 or (r<=-0.5 and mfe2<1): s4=-0.5 else if winner s4=r else s4=r
        if mfe2 < 1.0 and r <= -0.5:
            s4 = -0.5  # dead trades stop early at half loss (they never got to +1)
        elif mfe2 < 1.0 and r > -0.5 and r <= 0:
            s4 = r  # already better than -0.5? rare
        else:
            s4 = r  # had mfe>=1 — full base (or BE handled separately)
        # tighter: if mfe never reached 1, cap loss at -0.5
        if mfe2 < 1.0 and r < -0.5:
            s4 = -0.5

        surg["S0_base"].append(r)
        surg["S1_half_sl_path"].append(s1)
        surg["S2_be_after_1R"].append(s2)
        surg["S3_dead_time"].append(s4)

        oc = m.get("outcome", "?")
        if r <= 0 and oc == "trail":
            trail_losers.append((r, mfe2, mae, m))
        if r <= 0 and oc == "sl":
            sl_losers.append((r, mfe2, mae, m))
        if r > 0:
            winners.append((r, mfe2, mae, m))

    print_bucket(f"Surgery — {label}", list(surg.items()))

    # trail losers vs sl losers
    def _agg(arr, name):
        if not arr:
            return
        rs = [x[0] for x in arr]
        mfes = [x[1] for x in arr]
        maes = [x[2] for x in arr]
        print(f"  {name}: n={len(arr)}  netR={sum(rs):+.1f}  "
              f"avgMFE={sum(mfes)/len(mfes):.2f}  avgMAE={sum(maes)/len(maes):.2f}  "
              f"avgR={sum(rs)/len(rs):+.2f}")

    print(f"\n  --- Z. Loser split by outcome — {label} ---")
    _agg(trail_losers, "trail-losers")
    _agg(sl_losers, "sl-losers  ")
    if winners:
        print(f"  winners:     n={len(winners)}  netR={sum(x[0] for x in winners):+.1f}  "
              f"avgMFE={sum(x[1] for x in winners)/len(winners):.2f}  "
              f"avgMAE={sum(x[2] for x in winners)/len(winners):.2f}  "
              f"avgR={sum(x[0] for x in winners)/len(winners):+.2f}")
        # winners that dipped -0.5 first (would die to half SL)
        dipped = [x for x in winners if x[2] <= -0.5]
        print(f"  winners that touched -0.5R first: n={len(dipped)}  "
              f"netR={sum(x[0] for x in dipped):+.1f}  (half-SL kills these)")

    # trail losers with MFE>=1 — they BE-hit then trailed to loss?
    tl_alive = [x for x in trail_losers if x[1] >= 1.0]
    tl_dead = [x for x in trail_losers if x[1] < 1.0]
    print(f"  trail-losers MFE>=1: n={len(tl_alive)} netR={sum(x[0] for x in tl_alive):+.1f} "
          f"(BE would have saved ~0)")
    print(f"  trail-losers MFE<1:  n={len(tl_dead)} netR={sum(x[0] for x in tl_dead):+.1f} "
          f"(dead before +1 — half-SL saves)")
    # half-SL savings estimate on trail-losers
    save = sum(max(x[0], -0.5) - x[0] for x in trail_losers)
    save_sl = sum(max(x[0], -0.5) - x[0] for x in sl_losers)
    print(f"  half-SL would recover: trail-losers +{save:.1f}R  sl-losers +{save_sl:.1f}R  "
          f"total +{save+save_sl:.1f}R  BUT kills dipped winners "
          f"(see above)")


def f2_age(metas, c1h, label):
    """Regime-age filter with causal chop proxy (same as validate)."""
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

    for m in metas:
        ets = m["_ets"]
        if ets is None:
            m["_age"] = -1
            continue
        hi = bisect.bisect_left(ts_list, ets) - 1
        while hi >= 0 and ts_list[hi] + 3600 > ets:
            hi -= 1
        m["_age"] = age[hi] if hi >= 0 else -1

    rows = [
        ("all", [m["_r"] for m in metas]),
        ("age 0-2 fresh", [m["_r"] for m in metas if 0 <= m["_age"] <= 2]),
        ("age 3-7", [m["_r"] for m in metas if 3 <= m["_age"] <= 7]),
        ("age 8-15 stale-mid", [m["_r"] for m in metas if 8 <= m["_age"] <= 15]),
        ("age 16+ old", [m["_r"] for m in metas if m["_age"] >= 16]),
        ("skip age 8-15", [m["_r"] for m in metas if not (8 <= m["_age"] <= 15)]),
        ("only age 0-7", [m["_r"] for m in metas if 0 <= m["_age"] <= 7]),
        ("only age 0-7 + posthalt3", [
            m["_r"] for i, m in enumerate(metas)
            if 0 <= m["_age"] <= 7 and not (
                i >= 3 and all(metas[i - k]["_r"] <= 0 for k in range(1, 4))
                and (i < 4 or metas[i - 4]["_r"] > 0)
            )
        ]),
    ]
    # posthalt3: skip when exactly 3 straight losses before (original seq)
    kept_ph = []
    for i, m in enumerate(metas):
        j = i - 1
        run = 0
        while j >= 0 and metas[j]["_r"] <= 0:
            run += 1
            j -= 1
        if run == 3:
            continue
        kept_ph.append(m["_r"])
    rows.append(("posthalt3 only (ref)", kept_ph))
    print_bucket(f"F2. Regime age (fixed) — {label}", rows)


def combined_best(metas, c1h, label):
    """posthalt3 + age0-7 + streak after-win — print combo nets."""
    # annotate age
    f2_age(metas, c1h, label)  # sets _age, prints
    window_streaks(metas, gap_h=48.0)

    def posthalt3(i):
        j = i - 1
        run = 0
        while j >= 0 and metas[j]["_r"] <= 0:
            run += 1
            j -= 1
        return run == 3

    combos = []
    # posthalt3
    combos.append(("posthalt3", [m["_r"] for i, m in enumerate(metas) if not posthalt3(i)]))
    # age skip
    combos.append(("skip_age8-15", [m["_r"] for m in metas if not (8 <= m.get("_age", -1) <= 15)]))
    # both
    combos.append(("posthalt3+skip_age8-15", [
        m["_r"] for i, m in enumerate(metas)
        if not posthalt3(i) and not (8 <= m.get("_age", -1) <= 15)
    ]))
    # streak after-win completed
    combos.append(("streak_afterWIN_or_first", [
        m["_r"] for m in metas if m["_sprev_r"] is None or m["_sprev_r"] > 0
    ]))
    # all three (streak afterwin + posthalt + age)
    combos.append(("ALL3", [
        m["_r"] for i, m in enumerate(metas)
        if (m["_sprev_r"] is None or m["_sprev_r"] > 0)
        and not posthalt3(i)
        and not (8 <= m.get("_age", -1) <= 15)
    ]))
    # skip first-in-streak after long gap already in afterwin
    # half: posthalt + afterwin streak
    combos.append(("posthalt3+streak_afterWIN", [
        m["_r"] for i, m in enumerate(metas)
        if not posthalt3(i) and (m["_sprev_r"] is None or m["_sprev_r"] > 0)
    ]))
    print_bucket(f"COMBOS — {label}", combos)


def main():
    t0 = time.time()
    print("=" * 100)
    print("  AUTOPSY v3 — window sequential, causality, MAE surgery, F2 fixed")
    print("=" * 100)

    # ---- IS ----
    p = ROOT / "live_stuff/tests/_exp_champion_multi_sw10_results.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    m_is = enrich_base(data["trades"])
    (c15, f15), (c1h, f1h) = load_is_c()
    # IS fine
    try:
        fine_is = load_fine_unseen(c15[0]["ts"], c15[-1]["ts"])
    except Exception:
        fine_is = None

    print("\n" + "#" * 90)
    print("#  IS 2023-2026 champion_multi")
    print("#" * 90)
    seq_is = window_streaks(list(m_is), gap_h=48.0)
    flat_is = [m for st in seq_is for m in st]
    # re-sort flat by entry for later cuts (streak annotation preserved)
    cut_window(flat_is, "IS")
    causality_after_win(flat_is, "IS")
    mae_surgery(flat_is, fine_is, "IS")
    combined_best(flat_is, c1h, "IS")

    # ---- OOS ----
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
    m_oos = enrich_base(trades_oos)

    print("\n" + "#" * 90)
    print("#  TRUE OOS 2021-2022 champion_multi")
    print("#" * 90)
    seq_oos = window_streaks(list(m_oos), gap_h=48.0)
    flat_oos = [m for st in seq_oos for m in st]
    cut_window(flat_oos, "OOS")
    causality_after_win(flat_oos, "OOS")
    mae_surgery(flat_oos, fineo, "OOS")
    combined_best(flat_oos, c1ho, "OOS")

    # paired summary for combos
    print("\n" + "#" * 90)
    print("#  PAIRED COMBOS (want dIS>=0 and dOOS>=+5)")
    print("#" * 90)

    def combo_nets(metas, c1h):
        # ensure age + streak
        # age
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
        for m in metas:
            ets = m["_ets"]
            if ets is None:
                m["_age"] = -1
                continue
            hi = bisect.bisect_left(ts_list, ets) - 1
            while hi >= 0 and ts_list[hi] + 3600 > ets:
                hi -= 1
            m["_age"] = age[hi] if hi >= 0 else -1
        window_streaks(metas, gap_h=48.0)

        def posthalt3(i):
            j = i - 1
            run = 0
            while j >= 0 and metas[j]["_r"] <= 0:
                run += 1
                j -= 1
            return run == 3

        out = {}
        out["BASE"] = [m["_r"] for m in metas]
        out["posthalt3"] = [m["_r"] for i, m in enumerate(metas) if not posthalt3(i)]
        out["skip_age8-15"] = [m["_r"] for m in metas if not (8 <= m.get("_age", -1) <= 15)]
        out["age0-7"] = [m["_r"] for m in metas if 0 <= m.get("_age", -1) <= 7]
        out["ph3+age"] = [m["_r"] for i, m in enumerate(metas)
                          if not posthalt3(i) and not (8 <= m.get("_age", -1) <= 15)]
        out["streak_afterWIN"] = [m["_r"] for m in metas
                                  if m["_sprev_r"] is None or m["_sprev_r"] > 0]
        out["ph3+afterWIN"] = [m["_r"] for i, m in enumerate(metas)
                               if not posthalt3(i) and (m["_sprev_r"] is None or m["_sprev_r"] > 0)]
        out["ALL3"] = [m["_r"] for i, m in enumerate(metas)
                       if not posthalt3(i)
                       and not (8 <= m.get("_age", -1) <= 15)
                       and (m["_sprev_r"] is None or m["_sprev_r"] > 0)]
        # first-in-streak only
        out["streak_first_only"] = [m["_r"] for m in metas if m["_sidx"] == 0]
        out["streak_not_late"] = [m["_r"] for m in metas if m["_sidx"] <= 1]
        return {k: stats_of(v) for k, v in out.items()}

    # need flat with age — re-enrich from originals to be safe
    m_is2 = enrich_base(data["trades"])
    # preserve order = entry order (JSON should already be)
    m_oos2 = enrich_base(trades_oos)
    A = combo_nets(m_is2, c1h)
    B = combo_nets(m_oos2, c1ho)
    bn_is = A["BASE"][1]
    bn_oos = B["BASE"][1]
    print(f"  BASE IS={bn_is:+.1f} OOS={bn_oos:+.1f} OOS/IS={100*bn_oos/bn_is:.0f}%")
    print(f"  {'combo':<22} {'nIS':>5} {'dIS':>8} {'nOOS':>5} {'dOOS':>7} {'OOS/IS':>7} {'verdict':>10}")
    for k in A:
        if k == "BASE" or k not in B:
            continue
        n1, net1, _, _ = A[k]
        n2, net2, _, _ = B[k]
        di, do = net1 - bn_is, net2 - bn_oos
        ratio = 100 * net2 / net1 if net1 > 0 else -999
        v = ""
        if di >= -5 and do >= 5:
            v = "BOTH_UP"
        elif do >= 8 and di >= -15:
            v = "OOS_UP"
        elif di >= 15 and do >= -3:
            v = "IS_UP_OOS_OK"
        else:
            v = "no"
        if v != "no" or abs(do) >= 8:
            print(f"  {k:<22} {n1:>5} {di:>+8.1f} {n2:>5} {do:>+7.1f} {ratio:>6.0f}% {v:>10}")

    print("\n(done %.0fs)" % (time.time() - t0))


if __name__ == "__main__":
    main()
