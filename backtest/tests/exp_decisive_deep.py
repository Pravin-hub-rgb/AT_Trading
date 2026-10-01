"""Deep-dive: regime=decisive trades (mode=atr_high -> ATR%>0.65 at entry).

Path-true skip_decisive was the only BOTH_UP filter:
  champion: dIS 0 (no decisive on IS), dOOS +24.5
  utcsat:  dIS 0, dOOS +12.2

Questions:
  1. What do decisive trades look like (WR, R, yearly) on OOS?
  2. Is the edge just "remove losers" or path cascade?
  3. ATR% threshold sensitivity (0.55/0.65/0.75) - is 0.65 curve-fit?
  4. Does skip_decisive ever fire on IS with different swing chains?

Run: python -m backtest.tests.exp_decisive_deep
"""
import sys, time
from pathlib import Path
from collections import defaultdict, Counter

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from replay_harness import load_candles, INSTRUMENT
from engine.v18_params import SWING, get_v18_params, V18_ENGINE
from src.btc.btc_routes import _compute_swings, _load_fine_1m
from test_experiments_craze import build_module as build_craze, stats, show
from test_4_new_concepts import load_unseen, load_fine_1m as load_fine_unseen
from experiment_registry import EXPERIMENTS, BP

_P = dict(get_v18_params(INSTRUMENT)); _P.update(V18_ENGINE)


def run(sim, c1h, sw, c15, sw15, fine, params, **flags):
    r = sim(c1h, sw, c15, sw15, fine_ltf=fine, **{**params, **flags})
    return r["ltf_trades"] if isinstance(r, dict) else r


def net(tr):
    return sum(float(t["r_multiple"]) for t in tr)


def describe(rs, label):
    if not rs:
        print(f"  {label}: empty")
        return
    n = len(rs)
    wr = 100 * sum(1 for x in rs if x > 0) / n
    print(f"  {label}: n={n} net={sum(rs):+.1f} WR={wr:.1f}% "
          f"avg={sum(rs)/n:+.3f} min={min(rs):+.2f} max={max(rs):+.2f}")


def yearly(tr):
    py = defaultdict(float)
    for t in tr:
        py[(t.get("exit_date") or "")[:4]] += float(t["r_multiple"])
    return dict(py)


def main():
    t0 = time.time()
    print("=" * 100)
    print("  DECISIVE REGIME DEEP-DIVE (mode=atr_high -> use=decisive when ATR%>thresh)")
    print("=" * 100)

    (c15, f15), (c1h, f1h) = load_candles()
    sw15 = _compute_swings(f15, "continuous", min_bars=SWING["min_bars_15m"])
    sw10 = _compute_swings(f1h, "continuous", min_bars=10)
    fine_is = _load_fine_1m(min(c1h[0]["ts"], c15[0]["ts"]),
                            max(c1h[-1]["ts"], c15[-1]["ts"]), symbol=INSTRUMENT)

    (c15o, f15o), (c1ho, f1ho) = load_unseen("15m"), load_unseen("1h")
    sw15o = _compute_swings(f15o, "continuous", min_bars=SWING["min_bars_15m"])
    sw10o = _compute_swings(f1ho, "continuous", min_bars=10)
    fineo = load_fine_unseen(c15o[0]["ts"], c15o[-1]["ts"])

    sim = build_craze()
    keys = ["champion_multi_sw10", "utcsat_multi_sw10"]

    # ---- 1) trade breakdown by regime ----
    print("\n--- 1) regime x outcome (baseline, no filters) ---")
    for key in keys:
        params = {**BP, **EXPERIMENTS[key]["params"]}
        params.setdefault("exp_partial_r", 0.0)
        for tag, args in [
            ("IS", (c1h, sw10, c15, sw15, fine_is)),
            ("OOS", (c1ho, sw10o, c15o, sw15o, fineo)),
        ]:
            tr = run(sim, *args, params)
            by = defaultdict(list)
            for t in tr:
                by[t.get("htf_regime") or "?"].append(float(t["r_multiple"]))
            print(f"\n  {key} {tag}  regimes={ {k: len(v) for k,v in by.items()} }")
            for reg in sorted(by):
                describe(by[reg], f"    regime={reg}")
            py = yearly([t for t in tr if (t.get("htf_regime") or "") == "decisive"])
            if py:
                print(f"    decisive yearly: {py}")

    # ---- 2) pure filter (no path cascade) vs path-true engine skip ----
    print("\n--- 2) pure filter vs path-true engine skip (skip_decisive) ---")
    for key in keys:
        params = {**BP, **EXPERIMENTS[key]["params"]}
        params.setdefault("exp_partial_r", 0.0)
        print(f"\n  {key}")
        for tag, args in [
            ("IS", (c1h, sw10, c15, sw15, fine_is)),
            ("OOS", (c1ho, sw10o, c15o, sw15o, fineo)),
        ]:
            tr0 = run(sim, *args, params)
            pure = [t for t in tr0 if (t.get("htf_regime") or "") != "decisive"]
            tr1 = run(sim, *args, params, exp_skip_decisive=1)
            b, p, e = net(tr0), net(pure), net(tr1)
            print(f"    {tag}: base={b:+.1f} pure_filter={p:+.1f} (d={p-b:+.1f})  "
                  f"engine={e:+.1f} (d={e-b:+.1f})  "
                  f"n {len(tr0)}->{len(pure)}->{len(tr1)}")

    # ---- 3) ATR threshold sensitivity (engine flag via atr_high_thresh) ----
    print("\n--- 3) atr_high_thresh sensitivity (engine path-true, skip_decisive on) ---")
    print("    (thresh higher -> fewer decisive signals -> weaker filter)")
    for key in keys:
        base_p = {**BP, **EXPERIMENTS[key]["params"]}
        base_p.setdefault("exp_partial_r", 0.0)
        print(f"\n  {key}")
        print(f"    {'thresh':>6} {'IS n':>5} {'IS':>8} {'dIS':>7} "
              f"{'OOS n':>6} {'OOS':>8} {'dOOS':>7}")
        b_is = b_oos = None
        for th in (0.55, 0.60, 0.65, 0.70, 0.75, 0.85):
            params = {**base_p, "atr_high_thresh": th}
            tis = run(sim, c1h, sw10, c15, sw15, fine_is, params, exp_skip_decisive=1)
            tos = run(sim, c1ho, sw10o, c15o, sw15o, fineo, params, exp_skip_decisive=1)
            # also baseline at same thresh (no skip) for fair delta
            tis0 = run(sim, c1h, sw10, c15, sw15, fine_is, params)
            tos0 = run(sim, c1ho, sw10o, c15o, sw15o, fineo, params)
            ni, no = net(tis), net(tos)
            di = ni - net(tis0)
            do = no - net(tos0)
            if b_is is None:
                b_is, b_oos = ni, no
            print(f"    {th:>6.2f} {len(tis):>5} {ni:>+8.1f} {di:>+7.1f} "
                  f"{len(tos):>6} {no:>+8.1f} {do:>+7.1f}")

    # ---- 4) sw20 IS: does decisive ever appear? ----
    print("\n--- 4) sw20 IS - does decisive ever appear without sw10? ---")
    sw20 = _compute_swings(f1h, "continuous", min_bars=20)
    params = {**BP, **EXPERIMENTS["champion_multi_sw10"]["params"]}
    params.setdefault("exp_partial_r", 0.0)
    # sw20 + no mltf for closer to shipped
    params2 = {k: v for k, v in params.items() if k != "exp_mltf"}
    tr = run(sim, c1h, sw20, c15, sw15, fine_is, params)
    regs = Counter(t.get("htf_regime") for t in tr)
    print(f"  champion sw10 IS regimes: {Counter(t.get('htf_regime') for t in run(sim, c1h, sw10, c15, sw15, fine_is, params))}")
    print(f"  champion sw20 IS regimes: {regs}")

    # also try mode that uses chop for decisive (decisive_vs_flip_chop) just to
    # confirm atr_high never hits 0.65 on IS - print ATR% distribution at entries
    print("\n--- 5) ATR% at IS/OOS entry bars (why IS has 0 decisive) ---")
    # reuse engine atr via simple 14-bar ATR% on 15m
    def atrp_series(c15):
        out = []
        for i in range(len(c15)):
            if i < 14:
                out.append(0.0)
                continue
            bars = c15[i - 13:i + 1]
            hi = max(float(b["high"]) for b in bars)
            lo = min(float(b["low"]) for b in bars)
            cl = float(c15[i]["close"])
            trs = hi - lo  # range proxy matching engine atr15 mean range
            # engine uses mean of true ranges roughly - use same range/price*100
            out.append(100.0 * trs / cl if cl else 0.0)
        return out

    # engine atr15 is mean of (h-l) over 14 bars /price? check: atrp = atr/close*100?
    # v18: atr_pct built differently - approximate with hi-lo mean /close
    for tag, c in [("IS", c15), ("OOS", c15o)]:
        atrps = []
        # map entry bars
        pass

    # Use engine's own atr via a dry run that prints - simpler: count how many
    # 15m bars have atrp>0.65 using same formula as engine (_atr_pct_15m if exists)
    try:
        from src.btc.engines.htf_ltf.v18_streak_halt import _atr_pct_15m
        for tag, c in [("IS", c15), ("OOS", c15o)]:
            ap = _atr_pct_15m(c)
            n65 = sum(1 for x in ap if x > 0.65)
            n55 = sum(1 for x in ap if x > 0.55)
            print(f"  {tag}: bars={len(ap)} atrp>0.65={n65} ({100*n65/len(ap):.1f}%) "
                  f"atrp>0.55={n55} ({100*n55/len(ap):.1f}%) "
                  f"max={max(ap):.3f} p99={sorted(ap)[int(0.99*len(ap))]:.3f}")
    except Exception as e:
        print(f"  atr_pct helper missing: {e}")
        # manual
        def manual_atrp(c15):
            out = []
            for i in range(len(c15)):
                if i < 13:
                    out.append(0.0); continue
                s = 0.0
                for j in range(i - 13, i + 1):
                    h, l = float(c15[j]["high"]), float(c15[j]["low"])
                    pc = float(c15[j - 1]["close"]) if j > 0 else float(c15[j]["close"])
                    tr = max(h - l, abs(h - pc), abs(l - pc))
                    s += tr
                atr = s / 14
                cl = float(c15[i]["close"])
                out.append(atr / cl if cl else 0.0)
            return out
        for tag, c in [("IS", c15), ("OOS", c15o)]:
            ap = manual_atrp(c)
            n65 = sum(1 for x in ap if x > 0.65)
            print(f"  {tag}: bars={len(ap)} atrp>0.65={n65} max={max(ap):.3f} "
                  f"p99={sorted(ap)[int(0.99*len(ap))]:.3f}")

    print("\n(done %.0fs)" % (time.time() - t0))


if __name__ == "__main__":
    main()
