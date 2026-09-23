"""Autopsy v6 — adaptive break_kind selection + decisive regime + confirmation meta.

Findings to test as CAUSAL rules (not era-hardcode):
  K1. kind-performance gate: trade FLIP only if last W FLIP-kind trades were
      net-positive (rolling); same for B2. Causal adaptation to which kind works NOW.
  K2. kind momentum: trade the kind that won more over last W trades of each kind.
  D.  regime=decisive: what is it, does it appear on IS, skip?
  M.  confirmation meta: after a win, next trade of SAME kind only?
  N.  combine with halt2 (best BOTH_UP filter).

Also print kind x conc x prev-win cubes for structure.
Run: python -m live_stuff.tests.exp_autopsy6
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


def bucket(title, pairs, min_n=4):
    print(f"\n  --- {title} ---")
    print(f"  {'bucket':<44} {'n':>5} {'net':>8} {'WR%':>6} {'avg':>7} {'dd':>6}")
    for lab, rs in pairs:
        s = stats_of(rs)
        if s["n"] < min_n and not lab.startswith("all"):
            continue
        print(f"  {lab:<44} {s['n']:>5} {s['net']:>+8.1f} {s['wr']:>6.1f} "
              f"{s['avg']:>+7.3f} {s['dd']:>6.1f}")


def annotate(trades):
    for i, t in enumerate(trades):
        t["_r"] = float(t["r_multiple"])
        t["_kind"] = t.get("break_kind") or "?"
        t["_regime"] = t.get("htf_regime") or "?"
        t["_ets"] = d2ts(t.get("entry_date", ""))
        t["_xts"] = d2ts(t.get("exit_date", ""))
        t["_dir"] = t.get("dir")
    # concurrency
    order = sorted(range(len(trades)), key=lambda i: trades[i]["_ets"] or 0)
    conc = [0] * len(trades)
    open_set = []
    for i in order:
        ets, xts = trades[i]["_ets"], trades[i]["_xts"]
        if ets is None:
            continue
        open_set = [(xe, ix) for xe, ix in open_set if xe is None or xe > ets]
        conc[i] = len(open_set)
        if xts is not None:
            open_set.append((xts, i))
    for i, t in enumerate(trades):
        t["_conc"] = conc[i]
    # prev outcome (by entry order)
    for i, t in enumerate(trades):
        t["_prev_r"] = trades[i - 1]["_r"] if i > 0 else None
    # posthalt3
    for i, t in enumerate(trades):
        j = i - 1
        run = 0
        while j >= 0 and trades[j]["_r"] <= 0:
            run += 1
            j -= 1
        t["_run_before"] = run
        t["_posthalt3"] = (run == 3)
    return trades


def kind_windows(trades, W):
    """For each trade, rolling stats of SAME kind over previous W same-kind trades.
    Causal: only uses trades strictly before current index.
    Returns list of (keep_bool, net_if_kinda) helpers.
    """
    # running history per kind
    hist = {"FLIP": [], "B2": [], "?": []}
    decisions = []
    for i, t in enumerate(trades):
        k = t["_kind"]
        h = hist.get(k, [])
        # decide based on history BEFORE this trade
        if len(h) < 5:
            # not enough history — default keep
            decisions.append(True)
        else:
            window = h[-W:]
            net = sum(window)
            # trade this kind only if its recent window is net-positive
            decisions.append(net > 0)
        h.append(t["_r"])
        hist[k] = h
    return decisions


def kind_compare_gate(trades, W):
    """Keep trade only if SAME kind's last W net >= OTHER kind's last W net.
    If insufficient history, keep.
    """
    hist = {"FLIP": [], "B2": [], "?": []}
    decisions = []
    for t in trades:
        k = t["_kind"]
        other = "B2" if k == "FLIP" else "FLIP" if k == "B2" else None
        h = hist.get(k, [])
        ho = hist.get(other, []) if other else []
        if len(h) < 8 or len(ho) < 8:
            decisions.append(True)
        else:
            net_k = sum(h[-W:])
            net_o = sum(ho[-W:])
            decisions.append(net_k >= net_o)
        hist[k] = hist.get(k, []) + [t["_r"]]
        if other:
            # other's history already maintained via its own trades
            pass
    return decisions


def kind_momentum_gate(trades, W):
    """Keep if same kind's last W WR is better than other's (with min samples)."""
    hist = {"FLIP": [], "B2": [], "?": []}
    decisions = []
    for t in trades:
        k = t["_kind"]
        other = "B2" if k == "FLIP" else "FLIP" if k == "B2" else None
        h = hist.get(k, [])
        ho = hist.get(other, []) if other else []
        if len(h) < 8 or len(ho) < 8:
            decisions.append(True)
        else:
            wk = sum(1 for x in h[-W:] if x > 0) / W
            wo = sum(1 for x in ho[-W:] if x > 0) / W
            decisions.append(wk >= wo)
        hist[k] = hist.get(k, []) + [t["_r"]]
    return decisions


def apply_named(trades, label):
    rs = [t["_r"] for t in trades]
    pairs = [("all", rs)]

    # K gates
    for W in (10, 15, 20):
        dec = kind_windows(trades, W)
        kept = [t["_r"] for t, ok in zip(trades, dec) if ok]
        pairs.append((f"K1 kind_positive W={W}", kept))
        dec = kind_compare_gate(trades, W)
        kept = [t["_r"] for t, ok in zip(trades, dec) if ok]
        pairs.append((f"K2 kind_beats_other W={W}", kept))
        dec = kind_momentum_gate(trades, W)
        kept = [t["_r"] for t, ok in zip(trades, dec) if ok]
        pairs.append((f"K3 kind_WR_ge_other W={W}", kept))

    # pure kind cuts (reference — not causal adaptive, era truth)
    pairs.append(("REF only FLIP kind", [t["_r"] for t in trades if t["_kind"] == "FLIP"]))
    pairs.append(("REF only B2 kind", [t["_r"] for t in trades if t["_kind"] == "B2"]))

    # D decisive
    pairs.append(("D skip regime=decisive", [t["_r"] for t in trades if t["_regime"] != "decisive"]))
    pairs.append(("D only regime=decisive", [t["_r"] for t in trades if t["_regime"] == "decisive"]))
    for reg in sorted(set(t["_regime"] for t in trades)):
        pairs.append((f"regime={reg}", [t["_r"] for t in trades if t["_regime"] == reg]))

    # M confirmation meta
    pairs.append(("M1 after_win only", [t["_r"] for t in trades if t["_prev_r"] is None or t["_prev_r"] > 0]))
    pairs.append(("M2 after_win same kind", [
        t["_r"] for i, t in enumerate(trades)
        if t["_prev_r"] is None or (t["_prev_r"] > 0 and trades[i - 1]["_kind"] == t["_kind"])
    ]))
    # after win, allow only if kind matches winner's kind; after loss allow any
    pairs.append(("M3 after_win_samekind else any", [
        t["_r"] for i, t in enumerate(trades)
        if t["_prev_r"] is None or t["_prev_r"] <= 0 or trades[i - 1]["_kind"] == t["_kind"]
    ]))
    # skip FLIP after FLIP loss (streak same kind losses)
    def kind_run_loss(i):
        k = trades[i]["_kind"]
        j = i - 1
        run = 0
        while j >= 0 and trades[j]["_kind"] == k and trades[j]["_r"] <= 0:
            run += 1
            j -= 1
        return run
    for K in (2, 3):
        pairs.append((f"M4 skip {K}+ same-kind losses", [
            t["_r"] for i, t in enumerate(trades) if kind_run_loss(i) < K
        ]))

    # N combos with halt2
    def keep_halt2(t):
        return not t["_posthalt3"]
    pairs.append(("N0 halt2", [t["_r"] for t in trades if keep_halt2(t)]))
    for W in (10, 15):
        dec = kind_windows(trades, W)
        pairs.append((f"N1 halt2 + K1 W={W}", [
            t["_r"] for t, ok in zip(trades, dec) if ok and keep_halt2(t)
        ]))
        dec = kind_momentum_gate(trades, W)
        pairs.append((f"N2 halt2 + K3 W={W}", [
            t["_r"] for t, ok in zip(trades, dec) if ok and keep_halt2(t)
        ]))
    pairs.append(("N3 halt2 + skip decisive", [
        t["_r"] for t in trades if keep_halt2(t) and t["_regime"] != "decisive"
    ]))
    # M4-2 + halt2
    pairs.append(("N4 halt2 + skip 2 same-kind losses", [
        t["_r"] for i, t in enumerate(trades)
        if keep_halt2(t) and kind_run_loss(i) < 2
    ]))
    # K1 W=15 + skip decisive + halt2
    dec = kind_windows(trades, 15)
    pairs.append(("N5 halt2 + K1W15 + skip decisive", [
        t["_r"] for t, ok in zip(trades, dec)
        if ok and keep_halt2(t) and t["_regime"] != "decisive"
    ]))
    # M3 + halt2
    pairs.append(("N6 halt2 + M3", [
        t["_r"] for i, t in enumerate(trades)
        if keep_halt2(t) and (
            t["_prev_r"] is None or t["_prev_r"] <= 0 or trades[i - 1]["_kind"] == t["_kind"]
        )
    ]))
    # skip FLIP when K1 says FLIP bad, skip B2 when B2 bad — with warmup keep
    # already K1

    # kind x conc
    for k in ("FLIP", "B2"):
        for c in (0, 1):
            if c == 0:
                sub = [t["_r"] for t in trades if t["_kind"] == k and t["_conc"] == 0]
                pairs.append((f"{k}xconc0", sub))
            else:
                sub = [t["_r"] for t in trades if t["_kind"] == k and t["_conc"] >= 1]
                pairs.append((f"{k}xconc>=1", sub))

    bucket(f"Filters — {label}", pairs)
    return {lab: stats_of(rs) for lab, rs in pairs}


def main():
    t0 = time.time()
    print("=" * 100)
    print("  AUTOPSY v6 — adaptive kind gates + decisive + confirmation meta")
    print("=" * 100)

    cfg = EXPERIMENTS["champion_multi_sw10"]
    base_params = {**BP, **cfg["params"]}
    base_params.setdefault("exp_partial_r", 0.0)

    # IS
    (c15, f15), (c1h, f1h) = load_is_c()
    sw15 = _compute_swings(f15, "continuous", min_bars=SWING["min_bars_15m"])
    sw10 = _compute_swings(f1h, "continuous", min_bars=10)
    fine_is = _load_fine_1m(min(c1h[0]["ts"], c15[0]["ts"]),
                            max(c1h[-1]["ts"], c15[-1]["ts"]), symbol=INSTRUMENT)
    sim = build_craze()
    r = sim(c1h, sw10, c15, sw15, fine_ltf=fine_is, **base_params)
    trades_is = annotate(r["ltf_trades"] if isinstance(r, dict) else r)
    print(f"IS n={len(trades_is)} net={sum(t['_r'] for t in trades_is):+.1f} "
          f"regimes={Counter(t['_regime'] for t in trades_is)}")
    res_is = apply_named(trades_is, "IS")

    # OOS
    (c15o, f15o), (c1ho, f1ho) = load_unseen("15m"), load_unseen("1h")
    sw15o = _compute_swings(f15o, "continuous", min_bars=SWING["min_bars_15m"])
    sw10o = _compute_swings(f1ho, "continuous", min_bars=10)
    fineo = load_fine_unseen(c15o[0]["ts"], c15o[-1]["ts"])
    r = sim(c1ho, sw10o, c15o, sw15o, fine_ltf=fineo, **base_params)
    trades_oos = annotate(r["ltf_trades"] if isinstance(r, dict) else r)
    print(f"\nOOS n={len(trades_oos)} net={sum(t['_r'] for t in trades_oos):+.1f} "
          f"regimes={Counter(t['_regime'] for t in trades_oos)}")
    res_oos = apply_named(trades_oos, "OOS")

    bi = sum(t["_r"] for t in trades_is)
    bo = sum(t["_r"] for t in trades_oos)
    print("\n" + "#" * 90)
    print("#  PAIRED")
    print("#" * 90)
    print(f"  BASE IS={bi:+.1f} OOS={bo:+.1f} OOS/IS={100*bo/bi:.0f}%")
    print(f"  {'filter':<44} {'nIS':>5} {'dIS':>8} {'nOOS':>5} {'dOOS':>7} {'OOS%':>6} {'verdict':>12}")
    for k in res_is:
        if k not in res_oos or k == "all":
            continue
        a, b = res_is[k], res_oos[k]
        di, do = a["net"] - bi, b["net"] - bo
        ratio = 100 * b["net"] / a["net"] if a["net"] > 0 else -999
        v = "BOTH_UP" if di >= -3 and do >= 5 else \
            "OOS_UP" if do >= 8 and di >= -15 else \
            "IS_UP_OOS_OK" if di >= 15 and do >= -3 else "no"
        if v != "no" or abs(do) >= 10 or abs(di) >= 20:
            print(f"  {k:<44} {a['n']:>5} {di:>+8.1f} {b['n']:>5} {do:>+7.1f} "
                  f"{ratio:>5.0f}% {v:>12}")

    # utcsat sanity for K1 best
    print("\n" + "#" * 90)
    print("#  utcsat IS — K/N gates")
    print("#" * 90)
    u_params = {**BP, **EXPERIMENTS["utcsat_multi_sw10"]["params"]}
    u_params.setdefault("exp_partial_r", 0.0)
    r = sim(c1h, sw10, c15, sw15, fine_ltf=fine_is, **u_params)
    trades_u = annotate(r["ltf_trades"] if isinstance(r, dict) else r)
    res_u = apply_named(trades_u, "utcsat_IS")
    bu = sum(t["_r"] for t in trades_u)
    print(f"  utcsat BASE={bu:+.1f}")
    for k in res_is:
        if k in res_u and k != "all":
            d = res_u[k]["net"] - bu
            if abs(d) >= 5 or k in ("all",):
                print(f"  {k:<44} net={res_u[k]['net']:+.1f}  d={d:+.1f}")

    print("\n(done %.0fs)" % (time.time() - t0))


if __name__ == "__main__":
    main()
