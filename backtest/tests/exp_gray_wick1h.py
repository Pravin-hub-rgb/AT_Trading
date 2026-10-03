"""GRAY-MODE re-test of Stage B's REAL wick gate (1h plane) + path-true + cost reconciliation.

THE BUG THIS EXISTS TO FIX (forensic, 2026-09-27)
=================================================
Stage B (exp_bleed_autopsy) qualified wick_atr12@short<=6.03 using the Z1
1h feature plane: 12 CLOSED 1h bars ending at j = last 1h bar closed by
cutoff = entry_ts + 900, divided by ATR14 of the 1h TR series
(exp_regime_structure_autopsy.compute_features -> build_arrays(data["c1h"])),
bucket Q1 = lo <= v < hi with edge 6.026 read from _regime_structure_is.json.
Flag counts: is/champion 74, is/utcsat 62, oos/champion 35, oos/utcsat 36;
cohort sumNet -28.06 / -25.67 / -19.78 / -23.77; removal dNet +28.1/+25.7/
+19.8/+23.8 (POST-PROCESS, PASS 4/4).

But BOTH follow-up harnesses silently tested a DIFFERENT predicate on the
15m plane (exp_wick_short_pathtrue INJECT and exp_cascade_tax_test copy:
candles_ltf, atr15, window = 12 CLOSED 15m bars INCLUDING the entry bar,
threshold 6.03 on the RAW unrounded ratio). That 15m cohort is a different
set (111/92/63/55 removed; gray flagged 112/100/30/64/61/18) with OPPOSITE
cohort sign (is/champion gray raw +6.7 vs Stage B -28.1 net). The celebrated
"-78.6R cascade tax" (+28.1 post-process vs -50.5 path-true) therefore
conflated a cohort swap with a cascade. exp_wick_short_pathtrue's docstring
claim "identical to Stage B section 5.3" is FALSE.

So the standing verdict "gray does NOT rescue the wick gate" (ee8a42b,
5c50917) was measured on the wrong gate. This run asks the real question.

PRE-REGISTERED BEFORE THE RUN (2026-09-27)
------------------------------------------
PREDICATE (frozen, replicated not re-tuned):
  short only; cutoff = entry_ts + 900; j = last 1h bar with ts <= cutoff-3600;
  flag impossible if j < 50; v = round((sum up_wick + sum low_wick over 1h
  bars j-11..j) / ATR14(j), 3); flag iff -1e9 <= v < 6.026 (bucket_of
  semantics, edge read from _regime_structure_is.json at runtime).
  Single-source: the SAME Python flagger drives the engine injection (module
  global _w1h_gray) and every offline control.

ARMS (all reported, no best-of, nothing retuned after the run):
  A. REF: shipped engine, 6 cells (champion/utcsat/age10 x IS/OOS) must
     reproduce BYBIT_BASE or abort.
  B. PARITY: offline 1h flags on the ref ledgers must reproduce Stage B's
     qualifier counts AND sumNet (4 cells) or abort - this proves the
     replicated predicate is the same gate Stage B found.
  C. IDENTITY: gray module with _W1H=0 and skip module with _W1H=0 must
     reproduce the shipped trade list (is/champion).
  D. GRAY arm: engine gray mode (cooldown untouched, streak preserved via
     exp_gray_streak=True - the a3ca96b design), all 6 cells. Report harness
     dNet, LIVE dNet (kept-only book = what the user's no-fill rule actually
     realizes), cascade_term = harness_dNet + raw_gray (must be 0.00),
     seq_identical (must be 6/6), kept%, avg, maxDD, curve_better.
  E. PATH-TRUE skip arm (same predicate, pre-mutation continue), all 6 cells:
     completes the post-process / gray / path-true triangle ON ONE COHORT -
     the first honest measure of the cascade tax of the real gate.
     No directional prediction for path-true (the old -78.6 was cohort-mixed).
  F. RECONCILE the old 15m verdict under live accounting WITHOUT a rerun:
     offline replication of the 15m predicate (engine atr15 formula + the
     exp_sl_fine_cascade sl-width secondary branch) must reproduce n_gray
     112/100/30/64/61/18 from _sl_fine_cascade.json or section F is skipped
     (pre-registered fallback: bounded by n_gray x top-n per-trade costs).
     Then live_dNet_15m = harness_dNet + sum of costs of the gray rows
     (cost_i = r_i - net_r([t])), because a gray fill is never placed, so
     fees/slip/funding are never paid. Verdict impact assessed against the
     G-RULE (all cells positive).

PREDICTIONS:
  P1 (B): flag counts + sumNet match Stage B exactly.
  P2 (D): live dNet(gray) == Stage B post-process dNet (+28.1/+25.7/+19.8/
     +23.8, tol 0.2R) in the 4 Stage B cells, cascade_term 0.00, seq 6/6 -
     mechanism: a seq-identical gray books exactly the post-process book.
     If P2 holds, per the user's stated protocol the adoption ruling goes to
     the user; nothing is adopted here.
  P3 (E): exploratory - the real cohort's cascade tax is reported as measured.
  P4 (F): OOS cells of the 15m cohort stay negative under live accounting
     (cost relief <= n_gray x per-trade cost, far below 78R), so the old
     "15m gate dead" verdict stands under ANY accounting; IS cells may flip.

Run: $env:PYTHONIOENCODING='utf-8'; python -u exp_gray_wick1h.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

OUT = ROOT / "backtest/tests/_gray_wick1h.json"
Z1_JSON = ROOT / "backtest/tests/_regime_structure_is.json"
SLFINE_JSON = ROOT / "backtest/tests/_sl_fine_cascade.json"

BYBIT_BASE = {
    "champion": {"is": (500, 325.8), "oos": (279, 70.2)},
    "utcsat": {"is": (453, 279.5), "oos": (254, 66.9)},
    "age10": {"is": (130, 435.7), "oos": (76, 43.2)},
}
LANES = (
    ("champion", "champion_multi_sw10"),
    ("utcsat", "utcsat_multi_sw10"),
    ("age10", "age10_dirmatch_swingpause_single_sw10"),
)
# Stage B qualifiers (exp_bleed_autopsy _bleed_autopsy_results.json)
STAGEB = {
    "is/champion": (74, -28.056934599080492, 28.1),
    "is/utcsat": (62, -25.67355552906787, 25.7),
    "oos/champion": (35, -19.780510224801763, 19.8),
    "oos/utcsat": (36, -23.774610405016276, 23.8),
}
# exp_sl_fine_cascade gray n_gray (15m predicate, post-cooldown-fix)
SLFINE_NGRAY = {
    "is/champion": 112, "is/utcsat": 100, "is/age10": 30,
    "oos/champion": 64, "oos/utcsat": 61, "oos/age10": 18,
}
SLFINE_DNET = {
    "is/champion": -6.702, "is/utcsat": -7.044, "is/age10": -24.47,
    "oos/champion": -77.997, "oos/utcsat": -78.093, "oos/age10": -32.195,
}
YEARS = {"is": 3.67, "oos": 2.0}


# ---------------------------------------------------------------- flaggers
def make_flagger_1h(c1h, edge_lo, edge_hi):
    """Stage B Z1-plane wick_atr12 Q1 predicate - single source of truth.

    Mirrors exp_regime_structure_autopsy.compute_features exactly:
    j = last 1h bar CLOSED by cutoff (ts <= cutoff-3600), j>=50 required,
    ATR14 on 1h TR (Wilder tr), wick window = 12 bars ending at j inclusive,
    value rounded to 3dp, bucket_of = lo <= v < hi.
    """
    import bisect
    n = len(c1h)
    ts = [int(c["ts"]) for c in c1h]
    hi = [float(c["high"]) for c in c1h]
    lo = [float(c["low"]) for c in c1h]
    op = [float(c["open"]) for c in c1h]
    cl = [float(c["close"]) for c in c1h]
    tr = [hi[0] - lo[0]] if n else []
    for i in range(1, n):
        tr.append(max(hi[i] - lo[i], abs(hi[i] - cl[i - 1]), abs(lo[i] - cl[i - 1])))

    def flag(cutoff):
        j = bisect.bisect_right(ts, cutoff - 3600) - 1
        if j < 50:
            return False
        a = sum(tr[j - 13:j + 1]) / 14.0
        if not a:
            return False
        start = j - 12 + 1
        if start < 1:
            return False
        us = lw = 0.0
        for k in range(start, j + 1):
            us += hi[k] - max(op[k], cl[k])
            lw += min(op[k], cl[k]) - lo[k]
        v = round((us + lw) / a, 3)
        return edge_lo <= v < edge_hi

    return flag


def flag_ref_1h(trades, flag):
    """Offline flags on a finished ledger: short + predicate(entry_ts+900)."""
    out = []
    for t in trades:
        if t.get("dir") != "short":
            continue
        if flag(int(t["entry_ts"]) + 900):
            out.append(t)
    return out


def make_flagger_15m(c15):
    """Offline replication of the 15m engine predicate (exp_sl_fine_cascade).

    atr15[i] = mean(tr_l[max(0,i-13):i+1]) with Wilder tr on 15m; window =
    12 bars ending at the entry bar inclusive; raw (unrounded) <= 6.03.
    Plus the exp_sl_fine_cascade secondary sl-width branch
    (exp_gray_lo=0.01, exp_gray_hi=99.0): slw < 0.01 or slw > 99.
    """
    WICK_MAX, LB = 6.03, 12
    n = len(c15)
    hi = [float(c["high"]) for c in c15]
    lo = [float(c["low"]) for c in c15]
    cl = [float(c["close"]) for c in c15]
    tr = [0.0] * n
    for i in range(n):
        if i == 0:
            tr[i] = hi[i] - lo[i]
        else:
            pc = cl[i - 1]
            tr[i] = max(hi[i] - lo[i], abs(hi[i] - pc), abs(lo[i] - pc))
    atr = [0.0] * n
    for i in range(n):
        s = max(0, i - 13)
        atr[i] = sum(tr[s:i + 1]) / (i - s + 1)

    def flag(t):
        if t.get("dir") != "short":
            return False
        i = int(t.get("entry_idx"))
        wick = False
        if 0 <= i < n and i >= LB and atr[i] > 0:
            us = ls = 0.0
            for k in range(i - LB + 1, i + 1):
                o_, h_, l_, c_ = (float(c15[k]["open"]), hi[k], lo[k], cl[k])
                us += h_ - max(o_, c_)
                ls += min(o_, c_) - l_
            wick = (us + ls) / atr[i] <= WICK_MAX
        if wick:
            return True
        e = float(t["entry_price"]); s_ = float(t["sl"])
        slw = abs(e - s_) / e * 100.0 if e else 0.0
        return slw < 0.01 or slw > 99.0

    return flag


# ---------------------------------------------------------------- engines
def build_module(mode):
    """Craze super-set + gray (mode='gray') or skip (mode='skip') patch.

    Gray patch = exp_sl_fine_cascade's scaffold (cooldown untouched, streak
    preserved by exp_gray_streak) with the trigger swapped from the 15m wick
    to the shared 1h flagger. Book records r_multiple=0 + is_gray +
    r_multiple_raw for the cascade guard.
    """
    import test_experiments_craze as tc
    cap = {}
    orig = tc._load_module

    def spy(text, name):
        cap["text"] = text
        return orig(text, name)

    tc._load_module = spy
    try:
        tc.build_module()
    finally:
        tc._load_module = orig
    s = cap["text"]

    t1 = "    *,\n"
    assert s.count(t1) == 1, "sig star"
    if mode == "gray":
        s = s.replace(t1, t1 + "    _W1H=0.0,\n    exp_gray_streak=True,\n")
    else:
        s = s.replace(t1, t1 + "    _W1H=0.0,\n")

    a = "        if i < 0 or i>=n-1: continue\n"
    assert s.count(a) == 1, "wick anchor"
    inj = (
        "        _isgray=False\n"
        "        if _W1H>0 and int(sig[\"dir\"])!=1"
        " and _w1h_gray(int(candles_ltf[i][\"ts\"])+900):\n"
    )
    if mode == "gray":
        inj += "            _isgray=True\n"
    else:
        inj += "            continue\n"
    s = s.replace(a, a + inj)

    if mode == "gray":
        st = "        if max_consecutive_losses > 0:\n"
        assert s.count(st) == 1, "streak"
        s = s.replace(st, "        if max_consecutive_losses > 0"
                          " and not (_isgray and not exp_gray_streak):\n")
        bk = "            \"r_multiple\": round(float(r_multiple),3),\n"
        assert s.count(bk) == 1, "book"
        s = s.replace(bk,
                      "            \"r_multiple\": round(0.0 if _isgray"
                      " else float(r_multiple),3),\n"
                      "            \"is_gray\": bool(_isgray),\n"
                      "            \"r_multiple_raw\": round(float(r_multiple),3),\n")

    import importlib.util
    p = ROOT / f"backtest/tests/_w1h_{mode}_tmp.py"
    p.write_text(s, encoding="utf-8")
    spec = importlib.util.spec_from_file_location(f"w1h_{mode}", str(p))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main():
    t0 = time.time()
    print("=" * 100, flush=True)
    print("  GRAY vs PATH-TRUE vs POST-PROCESS: Stage B's REAL wick gate (1h plane)", flush=True)
    print("=" * 100, flush=True)

    from exp_sizing_combo import run as sim_fn
    from exp_cross_instrument_transfer import load_bybit
    from exp_equity_quality import equity_quality, arm_scores, curve_better
    from experiment_registry import BP, EXPERIMENTS
    from run_experiment import net_r

    z1 = json.loads(Z1_JSON.read_text(encoding="utf-8"))
    edges = z1["features"]["wick_atr12"]["edges"]
    e_lo, e_hi = float(edges[0][0]), float(edges[0][1])
    print(f"predicate: short, 1h-plane wick_atr12 Q1 bucket [{e_lo:g}, {e_hi:g})",
          flush=True)

    gmod = build_module("gray")
    smod = build_module("skip")
    payload = {
        "stage": "gray_wick1h",
        "predicate": {"plane": "1h", "window_bars": 12, "cutoff": "entry_ts+900",
                      "atr": "ATR14-1h", "bucket": [e_lo, e_hi],
                      "source": "_regime_structure_is.json"},
        "pre_registered": "see exp_gray_wick1h.py docstring P1-P4",
        "controls": {}, "parity": {}, "gray": {}, "skip": {},
        "reconcile_15m": {},
    }
    abort = False

    def run(mod, data, params, **flags):
        return sim_fn(mod.simulate_htf_ltf_streak_halt, data, params, **flags)

    for scope in ("is", "oos"):
        print(f"\n=== [{scope.upper()}] ===", flush=True)
        data = load_bybit(scope, gmod.simulate_htf_ltf_streak_halt)
        flag1h = make_flagger_1h(data["c1h"], e_lo, e_hi)
        gmod._w1h_gray = flag1h
        smod._w1h_gray = flag1h
        for name, key in LANES:
            params = {**BP, **EXPERIMENTS[key]["params"]}
            cell = f"{scope}/{name}"

            # --- A: ref control
            ref = sim_fn(gmod.simulate_htf_ltf_streak_halt, data, params, _W1H=0.0)
            exp_n, exp_net = BYBIT_BASE[name][scope]
            n_ref, net_ref = len(ref), net_r(ref)
            ok = n_ref == exp_n and abs(net_ref - exp_net) < 0.5
            payload["controls"][f"{cell}/ref"] = {"n": n_ref, "net": round(net_ref, 2),
                                                  "ok": bool(ok)}
            print(f"  {cell} ref n={n_ref} net={net_ref:+.1f} "
                  f"[{'OK' if ok else 'CONTROL FAIL'}]", flush=True)
            abort |= not ok

            # --- C: identity of the second module too (skip, off)
            skoff = run(smod, data, params, _W1H=0.0)
            same = ([t["entry_ts"] for t in skoff] == [t["entry_ts"] for t in ref]
                    and round(net_r(skoff), 6) == round(net_r(ref), 6))
            payload["controls"][f"{cell}/skip_off_identity"] = bool(same)
            if name == "champion":
                print(f"  {cell} skip-OFF identity: "
                      f"{'IDENTICAL' if same else 'MISMATCH'}", flush=True)
            abort |= not same

            # --- B: Stage B parity (offline 1h flags on ref)
            fl = flag_ref_1h(ref, flag1h)
            sum_net = sum(net_r([t]) for t in fl)
            rec = {"n": len(fl), "sum_net": round(sum_net, 6)}
            if cell in STAGEB:
                sb_n, sb_net, sb_d = STAGEB[cell]
                rec["stageb_n"] = sb_n
                rec["stageb_sum_net"] = sb_net
                rec["match"] = (len(fl) == sb_n
                                and abs(sum_net - sb_net) < 0.005)
                if not rec["match"]:
                    abort = True
            payload["parity"][cell] = rec
            print(f"    parity {cell}: flagged {len(fl)} sumNet {sum_net:+.4f} "
                  f"{'OK' if rec.get('match', True) else 'STAGEB MISMATCH'}",
                  flush=True)

            # --- D: gray arm
            gray = run(gmod, data, params, _W1H=1.0, exp_gray_streak=True)
            gset = sorted(int(t["entry_ts"]) for t in gray if t.get("is_gray"))
            fset = sorted(int(t["entry_ts"]) for t in fl)
            seq_same = ([(t["entry_ts"], t["exit_ts"]) for t in ref]
                        == [(t["entry_ts"], t["exit_ts"]) for t in gray])
            raw_gray = sum(float(t.get("r_multiple_raw") or 0.0)
                           for t in gray if t.get("is_gray"))
            kept = [t for t in gray if not t.get("is_gray")]
            qb, qg = equity_quality(ref, YEARS[scope]), equity_quality(gray, YEARS[scope])
            qk = equity_quality(kept, YEARS[scope])
            d_harness = round(qg["net"] - qb["net"], 3)
            d_live = round(qk["net"] - qb["net"], 3)
            cfk = curve_better(arm_scores(qk, qb))
            grec = {
                "n_gray": len(gset),
                "flag_set_match_offline": gset == fset,
                "seq_identical": seq_same,
                "harness_d_net": d_harness,
                "raw_r_forgiven": round(raw_gray, 3),
                "cascade_term": round(d_harness + raw_gray, 3),
                "live_d_net": d_live,
                "live_d_max_dd": round(qb["max_dd"] - qk["max_dd"], 3),
                "kept_pct": round(100.0 * qk["n"] / max(1, qb["n"]), 2),
                "avg_ref": round(qb["net"] / max(1, qb["n"]), 4),
                "avg_live": round(qk["net"] / max(1, qk["n"]), 4),
                "curve_better": bool(cfk),
            }
            if cell in STAGEB:
                grec["stageb_postprocess_dnet"] = STAGEB[cell][2]
                grec["p2_match"] = abs(d_live - STAGEB[cell][2]) <= 0.2
            payload["gray"][cell] = grec
            if not grec["flag_set_match_offline"]:
                abort = True
            print(f"    GRAY {cell}: gray={len(gset)} harness_dNet={d_harness:+.1f} "
                  f"live_dNet={d_live:+.1f} casc={grec['cascade_term']:+.2f} "
                  f"seqID={seq_same} setMatch={grec['flag_set_match_offline']}"
                  + (f" vs StageB {grec.get('stageb_postprocess_dnet'):+.1f}"
                     f" p2={'OK' if grec.get('p2_match') else 'MISS'}"
                     if cell in STAGEB else ""),
                  flush=True)

            # --- E: path-true skip arm
            skip = run(smod, data, params, _W1H=1.0)
            qb2 = equity_quality(ref, YEARS[scope])
            qs = equity_quality(skip, YEARS[scope])
            cfs = curve_better(arm_scores(qs, qb2))
            srec = {
                "n": len(skip), "removed": n_ref - len(skip),
                "net": round(net_r(skip), 2),
                "d_net": round(qs["net"] - qb2["net"], 3),
                "d_max_dd": round(qb2["max_dd"] - qs["max_dd"], 3),
                "avg": round(net_r(skip) / max(1, len(skip)), 4),
                "base_avg": round(net_r(ref) / max(1, n_ref), 4),
                "curve_better": bool(cfs),
            }
            payload["skip"][cell] = srec
            print(f"    SKIP {cell}: removed {srec['removed']} "
                  f"dNet={srec['d_net']:+.1f} dDD={srec['d_max_dd']:+.1f} "
                  f"avg {srec['base_avg']:+.3f}->{srec['avg']:+.3f} "
                  f"curve={cfs}", flush=True)

    if abort:
        print("\nABORT: control/parity failure - verdicts void", flush=True)
        payload["aborted"] = True
        OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {OUT}", flush=True)
        return

    # ---------------------------------------------------------- F: reconcile
    print("\n=== F: RECONCILE OLD 15m VERDICT UNDER LIVE ACCOUNTING ===", flush=True)
    slf = json.loads(SLFINE_JSON.read_text(encoding="utf-8"))
    for scope in ("is", "oos"):
        data = load_bybit(scope, gmod.simulate_htf_ltf_streak_halt)
        gmod._w1h_gray = make_flagger_1h(data["c1h"], e_lo, e_hi)
        flag15 = make_flagger_15m(data["c15"])
        for name, key in LANES:
            params = {**BP, **EXPERIMENTS[key]["params"]}
            cell = f"{scope}/{name}"
            ref = sim_fn(gmod.simulate_htf_ltf_streak_halt, data, params, _W1H=0.0)
            fl15 = [t for t in ref if flag15(t)]
            exp_ng = SLFINE_NGRAY[cell]
            parity = len(fl15) == exp_ng
            harness_d = SLFINE_DNET[cell]
            live_d = round(-sum(net_r([t]) for t in fl15), 3)
            cost_sum = round(sum(float(t.get("r_multiple") or 0.0) - net_r([t])
                                 for t in fl15), 3)
            all_costs = sorted((float(t.get("r_multiple") or 0.0) - net_r([t])
                                for t in ref), reverse=True)
            bound = round(harness_d + sum(all_costs[:exp_ng]), 3)
            payload["reconcile_15m"][cell] = {
                "parity_ok": bool(parity), "n": len(fl15), "n_expected": exp_ng,
                "harness_d_net": harness_d,
                "cost_relief": cost_sum,
                "live_d_net": live_d,
                "bound_live_d_net": bound,
                "live_positive": bool(live_d > 0),
            }
            print(f"  {cell}: n {len(fl15)}/{exp_ng} "
                  f"{'OK' if parity else 'PARITY FAIL'}  harness {harness_d:+.1f} "
                  f"+ costs {cost_sum:+.1f} = live {live_d:+.1f}"
                  f" (top-n bound {bound:+.1f})", flush=True)
            if not parity:
                payload["reconcile_15m"][cell]["note"] = "pre-registered fallback: bound only"

    # ---------------------------------------------------------- verdicts
    gr = payload["gray"]
    all_cells = list(gr)
    p2_cells = [c for c in all_cells if "p2_match" in gr[c]]
    payload["verdicts"] = {
        "p1_stageb_parity": all(payload["parity"][c].get("match", True)
                                for c in STAGEB),
        "gray_seq_identical": sum(1 for v in gr.values() if v["seq_identical"]),
        "gray_cascade_free": all(v["cascade_term"] == 0.0 for v in gr.values()),
        "gray_flag_sets_match": all(v["flag_set_match_offline"] for v in gr.values()),
        "p2_live_eq_postprocess": {
            c: gr[c].get("p2_match") for c in p2_cells},
        "g_rule_all6": all(
            gr[c]["kept_pct"] >= 55.0 and gr[c]["live_d_net"] > 0
            and gr[c]["avg_live"] >= gr[c]["avg_ref"]
            and gr[c]["live_d_max_dd"] >= 0 for c in all_cells),
        "g_rule_stageb4": all(
            gr[c]["kept_pct"] >= 55.0 and gr[c]["live_d_net"] > 0
            and gr[c]["avg_live"] >= gr[c]["avg_ref"]
            and gr[c]["live_d_max_dd"] >= 0 for c in p2_cells),
        "reconcile_parity": all(v["parity_ok"]
                                for v in payload["reconcile_15m"].values()),
        "old_15m_oos_negative": all(
            payload["reconcile_15m"][c]["live_d_net"] < 0
            for c in ("oos/champion", "oos/utcsat", "oos/age10")),
    }
    print("\n=== VERDICTS ===", flush=True)
    print(json.dumps(payload["verdicts"], indent=1), flush=True)
    payload["elapsed_sec"] = round(time.time() - t0, 2)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT} ({payload['elapsed_sec']}s)", flush=True)


if __name__ == "__main__":
    main()
