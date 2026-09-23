"""Autopsy v5 — MULTI config at the flip-vs-b2 autopsy level + concurrency.

Fresh engine runs keep htf_regime / break_kind / swing_no (JSON stripped them).

  A. B2 vs FLIP vs both-direction match on MULTI (the cut we only did on CRAZE)
  B. break_kind (sweep/fresh/etc) x outcome
  C. Concurrency: quality of Nth open position (exp_mltf allows overlap)
  D. swing_no / age of parent swing — early vs late swings in a run
  E. Engine flags: halt_skip=2 (skip first post-halt trade), skip age 8-15, combo
Run: python -m live_stuff.tests.exp_autopsy5
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
from src.btc.btc_routes import _compute_swings, _load_fine_1m
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
        return dict(n=0, net=0, wr=0, dd=0, avg=0)
    net = sum(rs)
    wr = 100.0 * sum(1 for x in rs if x > 0) / n
    peak = cum = dd = 0.0
    for x in rs:
        cum += x
        peak = max(peak, cum)
        dd = max(dd, peak - cum)
    return dict(n=n, net=net, wr=wr, dd=dd, avg=net / max(n, 1))


def bucket(title, pairs, min_n=5):
    print(f"\n  --- {title} ---")
    print(f"  {'bucket':<32} {'n':>5} {'net':>8} {'WR%':>6} {'avg':>7} {'dd':>6}")
    for lab, rs in pairs:
        s = stats_of(rs)
        if s["n"] < min_n and lab != "all":
            continue
        print(f"  {lab:<32} {s['n']:>5} {s['net']:>+8.1f} {s['wr']:>6.1f} "
              f"{s['avg']:>+7.3f} {s['dd']:>6.1f}")


def annotate_concurrency(trades):
    """Mark each trade with how many others were open at its entry (by entry/exit ts)."""
    ivs = []
    for i, t in enumerate(trades):
        ets = d2ts(t.get("entry_date", ""))
        xts = d2ts(t.get("exit_date", ""))
        ivs.append((ets, xts, i))
    # sort by entry
    order = sorted(range(len(trades)), key=lambda i: ivs[i][0] or 0)
    conc_at_entry = [0] * len(trades)
    open_set = []  # list of (xts, idx)
    for i in order:
        ets, xts, _ = ivs[i]
        if ets is None:
            continue
        # drop expired
        open_set = [(xe, ix) for xe, ix in open_set if xe is None or xe > ets]
        # others open at this entry (exclude self)
        conc_at_entry[i] = len(open_set)
        if xts is not None:
            open_set.append((xts, i))
    for i, t in enumerate(trades):
        t["_conc"] = conc_at_entry[i]
        t["_r"] = float(t["r_multiple"])
        t["_ets"] = d2ts(t.get("entry_date", ""))
        t["_xts"] = d2ts(t.get("exit_date", ""))
        t["_regime"] = t.get("htf_regime") or "?"
        t["_kind"] = t.get("break_kind") or "?"
        t["_swing"] = t.get("swing_no")
    return trades


def regime_age(c1h, ets):
    """Causal 1h bars since chop>=58 flip (same proxy as v3)."""
    chop_th = 58.0
    # build once outside — handled by closure cache
    return None  # filled by caller


def build_age_series(c1h):
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

    def lookup(ets):
        if ets is None:
            return -1
        hi = bisect.bisect_left(ts_list, ets) - 1
        while hi >= 0 and ts_list[hi] + 3600 > ets:
            hi -= 1
        return age[hi] if hi >= 0 else -1

    return lookup


def cuts(trades, label, age_fn=None):
    rs_all = [t["_r"] for t in trades]
    print(f"\n{'='*80}\n  {label}  n={len(trades)}  net={sum(rs_all):+.1f}\n{'='*80}")

    # A regime
    pairs = []
    for reg in sorted(set(t["_regime"] for t in trades)):
        pairs.append((f"regime={reg}", [t["_r"] for t in trades if t["_regime"] == reg]))
    pairs.append(("regime=flip", [t["_r"] for t in trades if t["_regime"] == "flip"]))
    pairs.append(("regime=b2", [t["_r"] for t in trades if t["_regime"] == "b2"]))
    # cross dir x regime
    for reg in ("b2", "flip"):
        for d in ("long", "short"):
            sub = [t["_r"] for t in trades if t["_regime"] == reg and t["dir"] == d]
            pairs.append((f"{reg}x{d}", sub))
    # winners/losers by regime
    pairs.append(("flip winners", [t["_r"] for t in trades if t["_regime"] == "flip" and t["_r"] > 0]))
    pairs.append(("b2 winners", [t["_r"] for t in trades if t["_regime"] == "b2" and t["_r"] > 0]))
    bucket("A. HTF regime (real tags) x dir", pairs)

    # B break_kind
    pairs = [("all", rs_all)]
    for k in sorted(set(t["_kind"] for t in trades)):
        pairs.append((f"kind={k}", [t["_r"] for t in trades if t["_kind"] == k]))
        for reg in ("b2", "flip"):
            sub = [t["_r"] for t in trades if t["_kind"] == k and t["_regime"] == reg]
            if len(sub) >= 5:
                pairs.append((f"{k}x{reg}", sub))
    bucket("B. break_kind x regime", pairs)

    # C concurrency
    pairs = [("all", rs_all)]
    for c in sorted(set(t["_conc"] for t in trades)):
        pairs.append((f"conc_at_entry={c}", [t["_r"] for t in trades if t["_conc"] == c]))
    pairs.append(("conc>=1 (not first)", [t["_r"] for t in trades if t["_conc"] >= 1]))
    pairs.append(("conc=0 (first/free)", [t["_r"] for t in trades if t["_conc"] == 0]))
    # incremental: if we only took trades when conc==0
    pairs.append(("KEEP only conc=0", [t["_r"] for t in trades if t["_conc"] == 0]))
    pairs.append(("SKIP conc>=2", [t["_r"] for t in trades if t["_conc"] < 2]))
    pairs.append(("SKIP conc>=1", [t["_r"] for t in trades if t["_conc"] < 1]))
    bucket("C. Concurrency at entry (exp_mltf overlaps)", pairs, min_n=3)

    # D swing_no bands (swing index within continuous chain — proxy for run position)
    pairs = [("all", rs_all)]
    # swing_no may restart; use within-year? just bands
    for t in trades:
        t["_sb"] = None
        sn = t.get("_swing")
        if sn is None:
            continue
        # band by abs swing number mod? better: low/mid/high relative
        # use raw if small
    swings = [t["_swing"] for t in trades if t.get("_swing") is not None]
    if swings:
        # quartiles of observed swing_no
        ss = sorted(swings)
        q1 = ss[len(ss) // 4]
        q2 = ss[len(ss) // 2]
        q3 = ss[3 * len(ss) // 4]
        for t in trades:
            sn = t.get("_swing")
            if sn is None:
                t["_sb"] = "?"
            elif sn <= q1:
                t["_sb"] = f"low<={q1}"
            elif sn <= q2:
                t["_sb"] = f"q1-q2<={q2}"
            elif sn <= q3:
                t["_sb"] = f"q2-q3<={q3}"
            else:
                t["_sb"] = f"high>{q3}"
        for b in sorted(set(t["_sb"] for t in trades if t["_sb"] != "?")):
            pairs.append((f"swing {b}", [t["_r"] for t in trades if t.get("_sb") == b]))
    bucket("D. Parent swing_no bands", pairs)

    # E filters from prior findings + regime-aware
    def posthalt3(i):
        j = i - 1
        run = 0
        while j >= 0 and trades[j]["_r"] <= 0:
            run += 1
            j -= 1
        return run == 3

    pairs = [("all", rs_all)]
    # halt_skip=2 simulation: after 3 losses, skip NEXT AND the one after
    # online: track consec of taken; when consec hits 3, skip next 1 more than engine's 1
    # engine already skips 1 via halt_skip_next — trade list is POST-engine.
    # "skip first trade with run==3 before it" = skip first after engine halt = halt_skip=2 total
    kept = [t["_r"] for i, t in enumerate(trades) if not posthalt3(i)]
    pairs.append(("E1 halt_skip=2 (skip post-halt)", kept))
    if age_fn:
        for t in trades:
            t["_age"] = age_fn(t["_ets"])
        pairs.append(("E2 skip age 8-15", [t["_r"] for t in trades if not (8 <= t["_age"] <= 15)]))
        pairs.append(("E2 only age 0-7", [t["_r"] for t in trades if 0 <= t["_age"] <= 7]))
        pairs.append(("E3 halt2+skip_age", [
            t["_r"] for i, t in enumerate(trades)
            if not posthalt3(i) and not (8 <= t["_age"] <= 15)
        ]))
        pairs.append(("E4 halt2+age0-7", [
            t["_r"] for i, t in enumerate(trades)
            if not posthalt3(i) and 0 <= t["_age"] <= 7
        ]))
        # regime-aware age: only apply age gate on flip? 
        pairs.append(("E5 halt2+skip_age flip-only-gate", [
            t["_r"] for i, t in enumerate(trades)
            if not posthalt3(i) and not (
                t["_regime"] == "flip" and 8 <= t["_age"] <= 15
            )
        ]))
        # B2-only cut of stale? B2 stale was IS negative
        pairs.append(("E6 halt2+skip_age b2-only-gate", [
            t["_r"] for i, t in enumerate(trades)
            if not posthalt3(i) and not (
                t["_regime"] == "b2" and 8 <= t["_age"] <= 15
            )
        ]))
    # concurrency caps + halt
    pairs.append(("E7 halt2 + conc<2", [
        t["_r"] for i, t in enumerate(trades)
        if not posthalt3(i) and t["_conc"] < 2
    ]))
    pairs.append(("E8 halt2 + conc<1", [
        t["_r"] for i, t in enumerate(trades)
        if not posthalt3(i) and t["_conc"] < 1
    ]))
    # flip-only after halt
    pairs.append(("E9 skip halt2 trades that are flip", [
        t["_r"] for i, t in enumerate(trades)
        if not (posthalt3(i) and t["_regime"] == "flip")
    ]))
    pairs.append(("E10 skip halt2 trades that are b2", [
        t["_r"] for i, t in enumerate(trades)
        if not (posthalt3(i) and t["_regime"] == "b2")
    ]))
    bucket("E. Candidate filters (full net)", pairs, min_n=3)

    # regime sequential: first trade of parent window
    # group by parent interval approx: consecutive trades same regime+dir within 48h
    return {lab: stats_of(rs) for lab, rs in pairs}


def run_cfg(params, c1h, sw1h, c15, sw15, fine):
    sim = build_craze()
    r = sim(c1h, sw1h, c15, sw15, fine_ltf=fine, **params)
    return r["ltf_trades"] if isinstance(r, dict) else r


def main():
    t0 = time.time()
    print("=" * 100)
    print("  AUTOPSY v5 — multi regime tags + concurrency + engine-flag candidates")
    print("=" * 100)

    cfg = EXPERIMENTS["champion_multi_sw10"]
    base_params = {**BP, **cfg["params"]}
    base_params.setdefault("exp_partial_r", 0.0)

    # ---- IS full engine (for tags) ----
    (c15, f15), (c1h, f1h) = load_is_c()
    sw15 = _compute_swings(f15, "continuous", min_bars=SWING["min_bars_15m"])
    sw10 = _compute_swings(f1h, "continuous", min_bars=10)
    fine_is = _load_fine_1m(min(c1h[0]["ts"], c15[0]["ts"]),
                            max(c1h[-1]["ts"], c15[-1]["ts"]),
                            symbol=INSTRUMENT)
    age_is = build_age_series(c1h)

    trades_is = run_cfg(base_params, c1h, sw10, c15, sw15, fine_is)
    annotate_concurrency(trades_is)
    # sanity vs JSON
    print(f"IS fresh run: n={len(trades_is)} net={sum(t['_r'] for t in trades_is):+.1f}")
    print(f"  regimes: {Counter(t['_regime'] for t in trades_is)}")
    print(f"  kinds:   {Counter(t['_kind'] for t in trades_is)}")
    print(f"  conc:    {Counter(t['_conc'] for t in trades_is)}")

    res_is = cuts(trades_is, "IS 2023-2026", age_fn=age_is)

    # ---- OOS ----
    (c15o, f15o), (c1ho, f1ho) = load_unseen("15m"), load_unseen("1h")
    sw15o = _compute_swings(f15o, "continuous", min_bars=SWING["min_bars_15m"])
    sw10o = _compute_swings(f1ho, "continuous", min_bars=10)
    fineo = load_fine_unseen(c15o[0]["ts"], c15o[-1]["ts"])
    age_oos = build_age_series(c1ho)

    trades_oos = run_cfg(base_params, c1ho, sw10o, c15o, sw15o, fineo)
    annotate_concurrency(trades_oos)
    print(f"\nOOS fresh run: n={len(trades_oos)} net={sum(t['_r'] for t in trades_oos):+.1f}")
    print(f"  regimes: {Counter(t['_regime'] for t in trades_oos)}")
    print(f"  kinds:   {Counter(t['_kind'] for t in trades_oos)}")
    print(f"  conc:    {Counter(t['_conc'] for t in trades_oos)}")

    res_oos = cuts(trades_oos, "OOS 2021-2022", age_fn=age_oos)

    # paired E filters
    print("\n" + "#" * 90)
    print("#  PAIRED E-filters")
    print("#" * 90)
    b_is = res_is.get("all", res_is.get("all"))
    # 'all' key
    base_is = next((v for k, v in res_is.items() if k == "all"), None)
    base_oos = next((v for k, v in res_oos.items() if k == "all"), None)
    if not base_is:
        # find first
        base_is = {"net": sum(t["_r"] for t in trades_is)}
        base_oos = {"net": sum(t["_r"] for t in trades_oos)}
    bi = base_is["net"] if "net" in base_is else sum(t["_r"] for t in trades_is)
    bo = base_oos["net"] if "net" in base_oos else sum(t["_r"] for t in trades_oos)
    # actually use explicit
    bi = sum(t["_r"] for t in trades_is)
    bo = sum(t["_r"] for t in trades_oos)
    print(f"  BASE IS={bi:+.1f} OOS={bo:+.1f}")
    keys = [k for k in res_is if k in res_oos and k != "all"]
    print(f"  {'filter':<40} {'dIS':>8} {'dOOS':>8} {'verdict':>12}")
    for k in keys:
        di = res_is[k]["net"] - bi
        do = res_oos[k]["net"] - bo
        v = "BOTH_UP" if di >= -3 and do >= 5 else \
            "OOS_UP" if do >= 8 and di >= -15 else \
            "IS_UP_OOS_OK" if di >= 15 and do >= -3 else "no"
        if v != "no" or abs(do) >= 8 or abs(di) >= 15:
            print(f"  {k:<40} {di:>+8.1f} {do:>+8.1f} {v:>12}")

    # utcsat quick: concurrency + regime only
    print("\n" + "#" * 90)
    print("#  utcsat IS regime/conc sanity")
    print("#" * 90)
    u_params = {**BP, **EXPERIMENTS["utcsat_multi_sw10"]["params"]}
    u_params.setdefault("exp_partial_r", 0.0)
    trades_u = run_cfg(u_params, c1h, sw10, c15, sw15, fine_is)
    annotate_concurrency(trades_u)
    print(f"utcsat n={len(trades_u)} net={sum(t['_r'] for t in trades_u):+.1f}")
    for reg in ("b2", "flip"):
        sub = [t["_r"] for t in trades_u if t["_regime"] == reg]
        print(f"  regime={reg}: n={len(sub)} net={sum(sub):+.1f} "
              f"WR={100*sum(1 for x in sub if x>0)/max(len(sub),1):.1f}%")
    for c in range(0, 4):
        sub = [t["_r"] for t in trades_u if t["_conc"] == c]
        if sub:
            print(f"  conc={c}: n={len(sub)} net={sum(sub):+.1f} "
                  f"WR={100*sum(1 for x in sub if x>0)/len(sub):.1f}%")

    print("\n(done %.0fs)" % (time.time() - t0))


if __name__ == "__main__":
    main()
