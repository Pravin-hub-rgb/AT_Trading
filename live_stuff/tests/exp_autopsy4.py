"""Autopsy v4 — correct path-order MAE surgery (the real test of dead-trade early exit).

S3 rule (causal): while MFE has never reached +1R, if price touches -0.5R adverse → exit -0.5R.
If MFE reaches +1R first, trade runs full base path (trail/SL as normal).

Also:
  S3b: same but threshold -0.75R
  S3c: same but MFE gate +0.75R
  S3d: exit -0.5 if never reached +0.5R (stricter dead)
  BE:  after MFE>=+1R, exit at entry when returned (classic BE) — full path order
  H:   half-SL always at -0.5 (for comparison — known to kill dipped winners)

Prints winner-kill cost vs loser-save for each rule.
Run: python -m live_stuff.tests.exp_autopsy4
"""
import sys, json, math, time, bisect, calendar
from pathlib import Path
from datetime import datetime

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
    return dict(n=n, net=net, wr=wr, dd=dd, avg=net / n)


def print_rows(title, named):
    print(f"\n  --- {title} ---")
    print(f"  {'rule':<36} {'n':>5} {'net':>8} {'dnet':>8} {'WR%':>6} {'avg':>7} {'dd':>6}")
    base = named[0][1]
    for lab, s in named:
        d = s["net"] - base["net"]
        print(f"  {lab:<36} {s['n']:>5} {s['net']:>+8.1f} {d:>+8.1f} "
              f"{s['wr']:>6.1f} {s['avg']:>+7.3f} {s['dd']:>6.1f}")


def simulate_rules(trades, fine, label):
    """Path-order simulation of exit rules. Returns named stats list."""
    if not fine:
        print(f"  [{label}] no fine data — skip")
        return []
    fts = [f["ts"] for f in fine]
    # pre-index
    rules = {
        "S0_base": [],
        "H_halfSL_always": [],
        "S3_dead_-0.5_before_1R": [],
        "S3b_dead_-0.75_before_1R": [],
        "S3c_dead_-0.5_before_0.75R": [],
        "S3d_dead_-0.5_before_0.5R": [],
        "S3e_dead_-0.35_before_1R": [],
        "BE_after_1R": [],
        "S3+BE": [],
        "S3e+BE": [],
    }
    # diagnostics
    diag = dict(killed_winners=0, killed_win_r=0.0, saved_losers=0, saved_r=0.0,
                be_hits=0, be_cost=0.0, no_fine=0)

    for t in trades:
        r = float(t["r_multiple"])
        ets = d2ts(t.get("entry_date", ""))
        xts = d2ts(t.get("exit_date", ""))
        if ets is None or xts is None:
            for k in rules:
                rules[k].append(r)
            continue
        i0 = bisect.bisect_left(fts, ets)
        i1 = bisect.bisect_right(fts, xts)
        path = fine[i0:i1]
        if not path:
            diag["no_fine"] += 1
            for k in rules:
                rules[k].append(r)
            continue

        entry = float(t["entry_price"])
        sl = float(t.get("sl") or entry)
        risk = abs(entry - sl)
        if risk <= 0:
            for k in rules:
                rules[k].append(r)
            continue
        d = 1 if t.get("dir") == "long" else -1

        def fav_adv(f):
            h, lo = float(f["high"]), float(f["low"])
            if d == 1:
                return (h - entry) / risk, (entry - lo) / risk
            return (entry - lo) / risk, (h - entry) / risk

        # Walk once, compute all path-dependent exits
        # Track first-touch times (bar index) for levels
        mfe = 0.0
        touch = {  # first bar index where adverse level hit while condition on MFE
            # we record when adverse hits X, and what mfe was at that moment
        }
        # For each rule (stop_level, mfe_gate): exit -stop if first time adv>=stop and mfe < gate
        stop_rules = [
            ("S3_dead_-0.5_before_1R", 0.5, 1.0),
            ("S3b_dead_-0.75_before_1R", 0.75, 1.0),
            ("S3c_dead_-0.5_before_0.75R", 0.5, 0.75),
            ("S3d_dead_-0.5_before_0.5R", 0.5, 0.5),
            ("S3e_dead_-0.35_before_1R", 0.35, 1.0),
        ]
        stop_exit = {name: None for name, _, _ in stop_rules}
        half_exit = None
        be_exit = None
        mfe = 0.0
        seen_mfe1 = False
        for bi, f in enumerate(path):
            fav, adv = fav_adv(f)
            prev_mfe = mfe
            # Does this bar touch stop while prev_mfe < gate?
            for name, stop, gate in stop_rules:
                if stop_exit[name] is None and adv >= stop and prev_mfe < gate:
                    # if this bar also reaches fav making prev become >=gate within bar,
                    # intra-bar ordering unknown — use conservative: require
                    # prev_mfe < gate AND fav < gate (bar didn't also reach gate)
                    # OR accept touch if prev_mfe < gate (optimistic for dead)
                    # Conservative for claiming edge: if bar's fav would reach gate,
                    # skip (uncertain ordering)
                    if prev_mfe < gate:
                        stop_exit[name] = bi
            if half_exit is None and adv >= 0.5:
                half_exit = bi
            mfe = max(mfe, fav)
            if mfe >= 1.0 and not seen_mfe1:
                seen_mfe1 = True
            if be_exit is None and seen_mfe1:
                if d == 1 and float(f["low"]) <= entry:
                    be_exit = bi
                if d == -1 and float(f["high"]) >= entry:
                    be_exit = bi

        # Assign exits: if stop fired BEFORE natural exit, use stop R
        # (approx stop R = -stop_level; real fill may be slightly worse with slip)
        base_r = r
        rules["S0_base"].append(base_r)

        # half SL
        if half_exit is not None:
            rules["H_halfSL_always"].append(-0.5)
        else:
            rules["H_halfSL_always"].append(base_r)

        for name, stop, gate in stop_rules:
            if stop_exit[name] is not None:
                rules[name].append(-stop)
            else:
                rules[name].append(base_r)

        # BE
        if be_exit is not None:
            # exited at entry → r≈0; but if natural was better/worse, BE caps
            # if natural exit was after BE at better price, BE would have cut it to 0
            rules["BE_after_1R"].append(0.0)
            be_applied = True
        else:
            rules["BE_after_1R"].append(base_r)
            be_applied = False

        # S3+BE: dead stop first; if not dead, BE may apply
        def combo(stop_name, stop):
            if stop_exit[stop_name] is not None:
                return -stop
            if be_exit is not None:
                return 0.0
            return base_r

        rules["S3+BE"].append(combo("S3_dead_-0.5_before_1R", 0.5))
        rules["S3e+BE"].append(combo("S3e_dead_-0.35_before_1R", 0.35))

        # diagnostics for S3
        if stop_exit["S3_dead_-0.5_before_1R"] is not None:
            if base_r > 0:
                diag["killed_winners"] += 1
                diag["killed_win_r"] += base_r
            else:
                diag["saved_losers"] += 1
                diag["saved_r"] += (-0.5 - base_r)  # positive if base < -0.5
        if be_exit is not None and stop_exit["S3_dead_-0.5_before_1R"] is None:
            diag["be_hits"] += 1
            diag["be_cost"] += 0.0 - base_r  # positive if BE cuts a winner

    named = [(k, stats_of(v)) for k, v in rules.items()]
    print_rows(f"Surgery path-order — {label}", named)
    print(f"  diag[{label}]: S3 killed_winners={diag['killed_winners']} "
          f"(was {diag['killed_win_r']:+.1f}R)  "
          f"saved_losers={diag['saved_losers']} "
          f"(+{diag['saved_r']:.1f}R)  "
          f"BE_hits_no_dead={diag['be_hits']} "
          f"(BE would cut {diag['be_cost']:+.1f}R from those)  "
          f"no_fine={diag['no_fine']}")
    return named


def paired(named_is, named_oos):
    if not named_is or not named_oos:
        return
    dis = {k: s for k, s in named_is}
    doos = {k: s for k, s in named_oos}
    b_is = dis["S0_base"]["net"]
    b_oos = doos["S0_base"]["net"]
    print(f"\n  --- PAIRED vs base (IS {b_is:+.1f} / OOS {b_oos:+.1f}) ---")
    print(f"  {'rule':<36} {'dIS':>8} {'dOOS':>8} {'verdict':>12}")
    for k in dis:
        if k == "S0_base" or k not in doos:
            continue
        di = dis[k]["net"] - b_is
        do = doos[k]["net"] - b_oos
        v = "BOTH_UP" if di >= -5 and do >= 5 else \
            "OOS_UP" if do >= 8 and di >= -20 else \
            "IS_UP" if di >= 15 and do >= -5 else "no"
        if v != "no" or abs(do) >= 10 or abs(di) >= 15:
            print(f"  {k:<36} {di:>+8.1f} {do:>+8.1f} {v:>12}")


def main():
    t0 = time.time()
    print("=" * 100)
    print("  AUTOPSY v4 — path-order MAE surgery")
    print("=" * 100)

    # IS
    p = ROOT / "live_stuff/tests/_exp_champion_multi_sw10_results.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    trades_is = data["trades"]
    (c15, f15), (c1h, f1h) = load_is_c()
    fine_is = _load_fine_1m(min(c1h[0]["ts"], c15[0]["ts"]),
                            max(c1h[-1]["ts"], c15[-1]["ts"]),
                            symbol=INSTRUMENT)
    print(f"IS fine bars: {len(fine_is)}")
    print("\n" + "#" * 90)
    print("#  IS 2023-2026")
    print("#" * 90)
    named_is = simulate_rules(trades_is, fine_is, "IS")

    # OOS
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
    print(f"OOS fine bars: {len(fineo)}")
    print("\n" + "#" * 90)
    print("#  TRUE OOS 2021-2022")
    print("#" * 90)
    named_oos = simulate_rules(trades_oos, fineo, "OOS")

    paired(named_is, named_oos)

    # utcsat IS quick check of best rule
    pu = ROOT / "live_stuff/tests/_exp_utcsat_multi_sw10_results.json"
    if pu.exists() and named_is:
        du = json.loads(pu.read_text(encoding="utf-8"))
        print("\n" + "#" * 90)
        print("#  utcsat_multi IS (sanity)")
        print("#" * 90)
        named_u = simulate_rules(du["trades"], fine_is, "utcsat_IS")

    print("\n(done %.0fs)" % (time.time() - t0))


if __name__ == "__main__":
    main()
