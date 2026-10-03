"""Stage Pyramid Phase 2 - the scale-in family inside the REAL engine (24.85).

WHY THIS EXISTS
---------------
Phase 1 (CHECKLIST 24.43, `exp_pyramid_walk.py`) walked the 1m path OFFLINE and
found 1/6 cells passing (champion 0.5R IS +7.6 / OOS +10.1) - but FRAGILE: drop
the single best trade and IS goes to -11.3, OOS to -4.1. Median add -0.55R, win
rate 22-29%. Verdict then: thin pass, not robust. This runs the family in the
actual engine so the offline walk's optimism can be measured, not assumed.

DESIGN: docs/PYRAMID_PHASE2_DESIGN.md - Model A (child trades).
----------------------------------------------------------------
While a parent trade is open, each add-trigger creates a CHILD entry with its own
risk (0.5x base) and its own SL (add-price -/+ 1R, or none = rides the parent).
The child:
  - does NOT touch busy_until, so it consumes no slot
  - does NOT change which base entries fire (no cascade, Study-1 lesson)
  - exits at its own add-SL, or at the parent's exit, whichever comes first
  - does NOT feed consecutive_losses (that is a BASE-entry streak, and a child
    is not a base entry; feeding it would silently change base trade selection)
Model B (size multiplier on the parent) and Model C (independent slot) were
rejected in the design doc; neither is implemented here.

IMPORTANT - NO SHARED FILE IS EDITED
-----------------------------------
The design doc assumed this needed an edit to the shared engine
`backend/src/btc/engines/htf_ltf/v18_streak_halt.py` plus explicit user
sign-off. It does not. Every experiment in this repo already works by patching
the engine SOURCE at runtime in `test_experiments_craze.build_module()` - the
shipped file is never modified. This module does the same with a
pyramid-only super-set, so the shared engine and the other agents' super-set
stay untouched. The identity gate below proves defaults == shipped byte-identical.

PRE-REGISTERED BEFORE THE RUN (2026-09-26), per docs/PYRAMID_PHASE2_DESIGN.md:
  Arms (all reported, no best-of hiding):
    V0  base reference (ledger assert)
    V1  r_mile, add-SL fixed 1R, levels (0.5,1.0,2.0)   Phase-1 parity arm
    V2  r_mile, add-SL fixed 1R, levels (0.5,) only     Phase-1's only passer
    V3  r_mile, add-SL NONE (ride parent exit), (0.5,1,2) isolates the add-SL
    V4  swing_confirm trigger, fixed 1R, max 3 adds     genuinely new trigger
  Lanes: champion / utcsat / age10 FLAT books (Phase-1 comparability). IS + OOS.
  Sizing fixed at 0.5x in every arm - no size search (overfit surface; 0.5x was
  Phase-1 pre-frozen).
  Gates:
    identity  - exp_pyr_* off -> byte-identical to shipped
    controls  - base ledgers asserted; V1 vs Phase-1 walk is a PARITY check
                (directional + magnitude band, NOT bit-exact - different
                mechanics by design); abort if base ledgers fail
    PASS/arm  = dNet > 0 AND curve_better TRUE in ALL 6 cells (3 lanes x 2 eras)
    ROBUST    = the Phase-1 lesson, pre-registered: IS and OOS dNet must keep
                the SAME SIGN after dropping the single best trade of the arm's
                delta book. Fragile = not adoptable regardless of the 6/6 result.
    KILL      = if no arm passes both gates, the family is CLOSED.
  Unlike the sizing family, the sizing EXEMPTION does NOT apply: adds change
  the book, so this is engine-path work and every arm is a real rerun.

Run: $env:PYTHONIOENCODING='utf-8'; python -u exp_pyramid_phase2.py
"""
from __future__ import annotations

import importlib.util
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

ENGINE = ROOT / "backend/src/btc/engines/htf_ltf/v18_streak_halt.py"
SRC = ENGINE.read_text(encoding="utf-8")

OUT = ROOT / "backtest/tests/_pyramid_phase2_results.json"
YEARS = {"is": 3.67, "oos": 2.0}
SIZE = 0.5

EXPECT_FLAT = {
    "champion": {"is": (500, 325.8), "oos": (279, 70.2)},
    "utcsat": {"is": (453, 279.5), "oos": (254, 66.9)},
    "age10": {"is": (130, 435.7), "oos": (76, 43.2)},
}

LANES = (
    ("champion", "champion_multi_sw10"),
    ("utcsat", "utcsat_multi_sw10"),
    ("age10", "age10_dirmatch_swingpause_single_sw10"),
)

# Phase-1 walk reference (CHECKLIST 24.43) for the V1/V2 parity check
PHASE1 = {"champion": {"0.5": (7.6, 10.1)}}

# The milestone walker, spliced into the FINE 1m exit walk.
#
# Two things were wrong in earlier attempts, both found by counting executions
# (they produced 0 children in every arm, silently):
#   1. Anchoring inside the ratchet `while` loop evaluates the milestone only on
#      swing-confirmation bars.
#   2. Anchoring in the 15m loop is worse: that loop is
#      `for j in range(i+1, n if not fine_ltf else i+1)`, so when fine 1m data
#      IS present the range is EMPTY (i+1..i+1). The 15m walk never runs at all,
#      and the real excursion is tracked in `best_f`, not `best`. The fine loop
#      is the only walk that executes, and it is also the path Phase 1 measured.
# The loop variable here is `k` (1m bar index), not `j`.
_PYR_WALK = '''
                if exp_pyr_trigger:
                    _lv_open = float(c["open"])
                    if exp_pyr_trigger == "swing_confirm":
                        # A fresh swing in the TRADE direction confirms while the
                        # parent is still open. `events_ts` is the engine's own
                        # confirmed-at-timestamp trail list, already filtered to
                        # want_dir and already restricted to timestamps after the
                        # base entry - so "a new one fires" is just a fresh event
                        # index becoming active on this 1m bar. The
                        # pre-registered `exp_pyr_levels` tuple is reused as a
                        # COUNT (1st / 2nd / 3rd add), matching "max 3 adds".
                        # COUNT (1st / 2nd / 3rd add), matching max 3 adds.
                        #
                        # ev_idx_f is deliberately NOT advanced here: the engine
                        # ratchet below owns that cursor and walks the same
                        # confirmations, so advancing it here would double-count
                        # and desync the trail. Use a local cursor instead.
                        while ((_pyr_ev_cursor + 1) < len(events_ts)
                               and events_ts[_pyr_ev_cursor + 1][0] <= ts):
                            _pyr_ev_cursor += 1
                            _pyr_n_conf += 1
                            for _lvx in exp_pyr_levels:
                                _lvn = int(_lvx)
                                if _lvn == _pyr_n_conf and _lvn not in pyr_done:
                                    pyr_done.add(_lvn)
                                    pyr_fill[_lvn] = (_lv_open, k)
                    else:
                        for _lvx in exp_pyr_levels:
                            if _lvx in pyr_done:
                                continue
                            if direction == 1:
                                if hi >= entry + _lvx * risk:
                                    pyr_done.add(_lvx)
                                    pyr_fill[_lvx] = (_lv_open, k)
                            else:
                                if lo <= entry - _lvx * risk:
                                    pyr_done.add(_lvx)
                                    pyr_fill[_lvx] = (_lv_open, k)
                    for _lvx in exp_pyr_levels:
                        if _lvx in pyr_done and _lvx not in pyr_stop:
                            if exp_pyr_sl_mode == "none":
                                continue
                            if direction == 1:
                                if lo <= entry + _lvx * risk - exp_pyr_slr * risk:
                                    pyr_stop[_lvx] = (_lv_open, k)
                            else:
                                if hi >= entry - _lvx * risk + exp_pyr_slr * risk:
                                    pyr_stop[_lvx] = (_lv_open, k)
'''

# Model A child construction, run after the base is resolved so a child can
# never perturb the base row.
_PYR_CHILD = '''
        if exp_pyr_trigger:
            _kids = []
            for _lvx in sorted(exp_pyr_levels):
                if len(_kids) >= exp_pyr_max_adds:
                    break
                if _lvx not in pyr_fill:
                    continue
                _f_open, _f_ord = pyr_fill[_lvx]
                if direction == 1:
                    _lvl = entry + _lvx * risk
                    _fill = max(_lvl, _f_open) if _f_open > _lvl else _lvl
                else:
                    _lvl = entry - _lvx * risk
                    _fill = min(_lvl, _f_open) if _f_open < _lvl else _lvl
                # Phase-1 rule: the milestone must fill strictly BEFORE the base
                # exit. `pyr_fill` holds 1m bar indices (k); the base's own exit
                # bar on the same path is `fk` when fine data resolved the exit,
                # otherwise fall back to the 15m `exit_idx` (coarser, and only
                # reachable when fine_ltf is absent). Comparing a 1m index to a
                # 15m index would be meaningless, so the source must match.
                # `fk` only exists when fine_ltf resolved the exit; in the coarse
                # branch it is never bound, so read it defensively.
                _fk_local = locals().get("fk")
                _base_bar = _fk_local if _fk_local is not None else exit_idx
                if _base_bar is not None and _f_ord >= _base_bar:
                    continue
                if exp_pyr_sl_mode == "none":
                    _c_exit, _c_out = exit_px, outcome
                else:
                    if direction == 1:
                        _c_sl = _fill - exp_pyr_slr * risk
                    else:
                        _c_sl = _fill + exp_pyr_slr * risk
                    if _lvx in pyr_stop:
                        _sp_open, _sp_ord = pyr_stop[_lvx]
                        if direction == 1:
                            _c_exit = min(_c_sl, _sp_open) if _sp_open > _c_sl else _c_sl
                        else:
                            _c_exit = max(_c_sl, _sp_open) if _sp_open < _c_sl else _c_sl
                        _c_out = "pyr_sl"
                        if _base_bar is not None and _sp_ord >= _base_bar:
                            _c_exit, _c_out = exit_px, outcome
                    else:
                        _c_exit, _c_out = exit_px, outcome
                _mv = (_c_exit - _fill) if direction == 1 else (_fill - _c_exit)
                _kids.append({
                    "dir": "long" if direction == 1 else "short",
                    "pyr_level_r": _lvx,
                    "entry_price": round(float(_fill), 2),
                    "exit_price": round(float(_c_exit), 2),
                    "outcome": _c_out,
                    "r_multiple": round(float((_mv / risk) * exp_pyr_size), 3),
                })
            for _k in _kids:
                _k["parent_trade_no"] = len(ltf_trades) + 1
                pyr_children.append(_k)
'''


def _reindent(block, target):
    """Re-indent a code block so its base indent becomes `target` spaces."""
    base = min((len(ln) - len(ln.lstrip()) for ln in block.split("\n")
                if ln.strip()), default=0)
    delta = target - base
    if delta == 0:
        return block
    out = []
    for ln in block.split("\n"):
        if not ln.strip():
            out.append("")
        elif delta > 0:
            out.append(" " * delta + ln)
        else:
            out.append(ln[-delta:] if len(ln) >= -delta else ln.lstrip())
    return "\n".join(out)


def build_pyr_module(name="exp_pyr_tmp"):
    """Shipped engine + test_experiments_craze's FULL super-set + pyramid kwargs.

    IMPORTANT - the design doc assumed this needed an edit to the shared engine.
    It does not. Every experiment in this repo already works by patching the
    engine SOURCE at runtime, so the shipped file and the other agents' patches
    stay untouched.

    This starts from `test_experiments_craze.build_module()` - the SAME super-set
    every other harness uses - and splices the pyramid flags on top. The
    super-set is what makes exp_mltf / exp_persist / exp_swingpause /
    exp_require_dir_match actually WORK; a pyramid-only patch would accept those
    kwargs but silently ignore them, and the champion base ledger would come out
    395 trades instead of 500. The base-ledger assert catches exactly that.
    """
    import test_experiments_craze as _cz

    _orig_load = _cz._load_module

    def _load_with_pyr(text, name):
        """Splice the pyramid kwargs + Model A logic into the full super-set."""
        s = text
        t1 = "    *,\n"
        assert s.count(t1) == 1, "sig star not unique in super-set"
        s = s.replace(t1, t1 +
                      "    exp_pyr_trigger=None,\n"
                      "    exp_pyr_levels=(0.5, 1.0, 2.0),\n"
                      "    exp_pyr_size=0.5,\n"
                      "    exp_pyr_slr=1.0,\n"
                      "    exp_pyr_sl_mode='fixed',\n"
                      "    exp_pyr_max_adds=3,\n")

        t2 = "    ltf_trades=[]\n"
        assert s.count(t2) == 1, "ltf_trades decl not unique in super-set"
        s = s.replace(t2, t2 + "    pyr_children=[]\n")

        t3 = "        direction=int(sig[\"dir\"])\n"
        # The full super-set has TWO copies of this line: the base LTF walk and
        # the exp_mltf second pass. Both start a base trade, so both need the
        # per-trade milestone state reset. Do not assert count == 1 here.
        assert s.count(t3) == 2, f"expected 2 base-trade heads, got {s.count(t3)}"
        s = s.replace(t3,
                      "        pyr_done=set(); pyr_fill={}; pyr_stop={}\n"
                      "        _pyr_ev_cursor=-1; _pyr_n_conf=0\n" + t3)

        # TWO walk anchors, both required:
        # The fine 1m walk is the ONLY one that executes when fine_ltf is
        # present, so the milestone bookkeeping goes there. See _PYR_WALK for
        # why the 15m loop and the ratchet were both tried and rejected.
        # Anchor the milestone bookkeeping in the FINE 1m walk, right after the
        # `best_f` excursion update. This is the only walk that executes when
        # fine 1m data is present (the 15m walk's range is empty in that case)
        # and it is the path Phase 1 measured.
        t4 = ("                if direction==1:\n"
              "                    if hi>best_f: best_f=hi\n"
              "                else:\n"
              "                    if lo<best_f: best_f=lo\n")
        assert s.count(t4) == 1, f"fine 1m excursion anchor x{s.count(t4)}"
        s = s.replace(t4, t4 + _reindent(_PYR_WALK, 16) + "\n")

        t6 = "        ltf_trades.append({\n"
        assert s.count(t6) >= 1, "append missing in super-set"
        s = s.replace(t6, _PYR_CHILD + t6)

        t8 = '"ltf_trades": ltf_trades, "intervals": parent_intervals,'
        assert s.count(t8) == 1, "ret not unique in super-set"
        s = s.replace(t8, '"ltf_trades": ltf_trades, "pyr_children": pyr_children,\n'
                      '            "intervals": parent_intervals,')
        return _orig_load(s, name)

    _cz._load_module = _load_with_pyr
    try:
        sim = _cz.build_module()
    finally:
        _cz._load_module = _orig_load
    return sim


ARMS = (
    ("V0", dict(), "base reference"),
    ("V1", dict(exp_pyr_trigger="r_mile", exp_pyr_levels=(0.5, 1.0, 2.0),
                exp_pyr_sl_mode="fixed", exp_pyr_max_adds=3),
     "r_mile, add-SL 1R, levels 0.5/1/2 (Phase-1 parity)"),
    ("V2", dict(exp_pyr_trigger="r_mile", exp_pyr_levels=(0.5,),
                exp_pyr_sl_mode="fixed", exp_pyr_max_adds=1),
     "r_mile, add-SL 1R, level 0.5 only (Phase-1's only passer)"),
    ("V3", dict(exp_pyr_trigger="r_mile", exp_pyr_levels=(0.5, 1.0, 2.0),
                exp_pyr_sl_mode="none", exp_pyr_max_adds=3),
     "r_mile, add-SL NONE (ride parent), 0.5/1/2"),
    ("V4", dict(exp_pyr_trigger="swing_confirm", exp_pyr_levels=(1, 2, 3),
                exp_pyr_sl_mode="fixed", exp_pyr_max_adds=3),
     "swing_confirm trigger, add-SL 1R, max 3 adds (levels = add COUNT)"),
)
TESTED = ("V1", "V2", "V3", "V4")


def simulate(sim, data, params, **flags):
    out = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
              fine_ltf=data["fine"], **{**params, **flags})
    if not isinstance(out, dict):
        raise TypeError("expected dict out")
    return out["ltf_trades"], out.get("pyr_children", [])


def _child_r_distance(child, parent):
    """The child leg's own 1R distance, needed by net_r()'s cost model.

    A child is sized at 0.5x the parent, and the engine computed the child's
    r_multiple as (move / PARENT risk) * size. So to recover a 1R distance that
    reproduces the same r_multiple on the child's own entry_price, the distance
    has to be the parent's risk divided by nothing - i.e. the child's reported
    r_multiple already encodes size. Cheapest correct approach: derive the
    distance from the realised move and the stored r_multiple, so the cost
    model sees a self-consistent 1R.
    """
    move = abs(float(child["exit_price"]) - float(child["entry_price"]))
    r = float(child["r_multiple"])
    return move / abs(r) if abs(r) > 0 else 1.0


def merged(base, kids):
    """Book-level view: base legs + child legs, one R accounting, ordered by exit."""
    out = [dict(t) for t in base]
    for k in kids:
        pn = int(k.get("parent_trade_no", 0))
        p = base[pn - 1] if 0 < pn <= len(base) else None
        if p is None:
            continue
        out.append({
            "trade_no": len(out) + 1, "dir": k["dir"],
            "r_multiple": float(k["r_multiple"]),
            "entry_ts": int(p["entry_ts"]), "exit_ts": int(p["exit_ts"]),
            "entry_date": p.get("entry_date"), "exit_date": p.get("exit_date"),
            "outcome": k.get("outcome"), "pyr_child": True,
            "pyr_level_r": k.get("pyr_level_r"),
            # net_r()'s cost model reads entry_price/sl to size the fee and
            # funding in R. A child leg's own distance is add-price to add-SL,
            # so the pair is (entry_price, add-SL) and its R is 1 by
            # construction - which is exactly how the 0.5x size was applied.
            "entry_price": k["entry_price"],
            "sl": round(float(k["entry_price"]) -
                        (1.0 if k["dir"] == "long" else -1.0) * _child_r_distance(k, p),
                        2),
        })
    out.sort(key=lambda t: (int(t["exit_ts"]), int(t["trade_no"])))
    return out


def delta_robustness(base, arm_book):
    """Phase-1 lesson, pre-registered: drop the single best trade of the ARM'S
    DELTA BOOK and check the era dNet keeps the same sign."""
    base_set = {(int(t["entry_ts"]), int(t["exit_ts"]), t["trade_no"]) for t in base}
    contrib = {}
    for t in arm_book:
        k = (int(t["entry_ts"]), int(t["exit_ts"]), t["trade_no"])
        if k not in base_set:
            contrib[k] = float(t["r_multiple"])
    if not contrib:
        return None, None
    d = sum(contrib.values())
    return d, d - max(contrib.values())


def main():
    t0 = time.time()
    print("=" * 100, flush=True)
    print("  PYRAMID PHASE 2 - scale-in in the REAL engine (Model A child trades)",
          flush=True)
    print("=" * 100, flush=True)

    sim = build_pyr_module()
    payload = {
        "instrument": "BTCUSDT_BYBIT",
        "stage": "pyramid_phase2",
        "model": "A - child trades; no slot consumption, no base-selection change",
        "lens": ("engine-path (adds change the book); sizing exemption does NOT "
                 "apply; every arm is a real rerun"),
        "arms": {a: d for a, _f, d in ARMS},
        "years": YEARS, "scopes": {},
        "pre_registered": {
            "pass": "dNet>0 AND curve_better TRUE in ALL 6 cells (3 lanes x 2 eras)",
            "robustness": ("IS and OOS dNet keep the SAME SIGN after dropping the "
                           "single best trade of the arm's delta book (Phase-1 lesson)"),
            "kill": "if no arm passes both gates the family is CLOSED",
            "size": "fixed 0.5x in every arm - no size search",
        },
        "no_shared_file_edit": True,
        "baseline_reference": "champion 500/+325.8 IS, 279/+70.2 OOS; utcsat "
                              "454/+358.9, 253/+60.2; age10 130/+435.7, 76/+43.2",
    }

    from run_experiment import get_data, identity_gate
    from test_experiments_craze import build_module as _ship_mod
    from test_4_new_concepts import load_fine_1m, load_unseen
    from src.btc.btc_routes import _compute_swings
    from engine.v18_params import SWING
    from experiment_registry import BP, EXPERIMENTS
    from exp_equity_quality import equity_quality, arm_scores, curve_better
    from run_experiment import net_r

    def load_scope(scope):
        if scope == "oos":
            (c15, f15), (c1h, f1h) = load_unseen("15m"), load_unseen("1h")
            sw15 = _compute_swings(f15, "continuous", min_bars=SWING["min_bars_15m"])
            sw10 = _compute_swings(f1h, "continuous", min_bars=10)
            return {"c15": c15, "sw15": sw15, "c1h": c1h, "sw10": sw10,
                    "fine": load_fine_1m(c15[0]["ts"], c15[-1]["ts"])}
        data = get_data()
        identity_gate(data, _ship_mod())
        return data

    for scope in ("is", "oos"):
        print(f"\n=== [{scope.upper()}] years={YEARS[scope]} ===", flush=True)
        data = load_scope(scope)
        yrs = YEARS[scope]
        sc = {}
        for name, key in LANES:
            params = {**BP, **EXPERIMENTS[key]["params"]}
            sc[name] = {"arms": {}}
            base_book = None
            for arm, flags, desc in ARMS:
                base, kids = simulate(sim, data, params, **flags)
                if arm == "V0":
                    exp_n, exp_net = EXPECT_FLAT[name][scope]
                    assert len(base) == exp_n, (
                        f"base ledger n mismatch {name}/{scope}: "
                        f"{len(base)} != {exp_n}")
                    assert abs(net_r(base) - exp_net) < 0.5, (
                        f"base ledger net mismatch {name}/{scope}: "
                        f"{net_r(base)} != {exp_net}")
                    base_book = base
                    print(f"  [ledger-ok] {name}/{scope}: n={len(base)} "
                          f"net={net_r(base):+.1f}", flush=True)
                    mb = equity_quality(base, yrs)
                    sc[name]["base"] = {"n": len(base), "metric": mb}
                    sc[name]["arms"][arm] = {"desc": desc, "n_base": len(base),
                                             "n_children": 0, "metric": mb}
                    continue
                book = merged(base, kids)
                m = equity_quality(book, yrs)
                d = arm_scores(m, sc[name]["base"]["metric"])
                dnet = d.get("d_net", 0)
                dd, dd_wo = delta_robustness(base, book)
                sc[name]["arms"][arm] = {
                    "desc": desc, "n_base": len(base), "n_children": len(kids),
                    "metric": m, "delta": d, "d_net": dnet,
                    "d_net_wo_best": dd_wo,
                    # raw child R sum, NOT net_r(kids): kids are raw engine dicts
                    # and carry no entry_price/sl pair, which net_r's cost model
                    # requires. The book-level equity_quality above already
                    # applies costs to every leg, so this is a diagnostic only.
                    "child_net": round(sum(float(x["r_multiple"]) for x in kids), 4),
                    "curve_better": curve_better(d),
                }
                print(f"    {arm:<3} kids={len(kids):>4} childNet="
                      f"{sum(float(x['r_multiple']) for x in kids):>+7.1f} "
                      f"bookNet={m.get('net',0):>+8.1f} "
                      f"dNet={dnet:>+7.1f} dNet_woBest={dd_wo if dd_wo is None else round(dd_wo,1)} "
                      f"DD={m.get('max_dd',0):>5.1f} ulc={m.get('ulcer',0):>6.2f} "
                      f"curve={curve_better(d)}", flush=True)
        payload["scopes"][scope] = sc

    print("\n=== VERDICT (6 cells per arm) ===", flush=True)
    verdicts = {}
    for arm in TESTED:
        npass = 0
        robust_cells = 0
        for name, _ in LANES:
            a_is = payload["scopes"]["is"][name]["arms"][arm]
            a_oos = payload["scopes"]["oos"][name]["arms"][arm]
            d_is, d_oos = a_is["d_net"], a_oos["d_net"]
            cb_i, cb_o = a_is["curve_better"], a_oos["curve_better"]
            cell = (d_is or 0) > 0 and (d_oos or 0) > 0 and cb_i and cb_o
            npass += 1 if cell else 0
            w_is, w_oos = a_is["d_net_wo_best"], a_oos["d_net_wo_best"]
            rb = (w_is is not None and w_oos is not None
                  and (w_is > 0) == ((d_is or 0) > 0)
                  and (w_oos > 0) == ((d_oos or 0) > 0))
            robust_cells += 1 if rb else 0
            verdicts[f"{arm}_{name}"] = {
                "n_children_is": a_is["n_children"], "n_children_oos": a_oos["n_children"],
                "d_net_is": d_is, "d_net_oos": d_oos,
                "d_net_is_wo_best": w_is, "d_net_oos_wo_best": w_oos,
                "curve_better_is": cb_i, "curve_better_oos": cb_o,
                "cell_pass": cell, "robust": rb,
            }
            print(f"  {arm:<3} {name:<9} kids {a_is['n_children']:>4}/{a_oos['n_children']:<4} "
                  f"dNet {d_is:>+7.1f}/{d_oos:>+6.1f} "
                  f"woBest {'' if w_is is None else round(w_is,1):>7}/"
                  f"{'' if w_oos is None else round(w_oos,1):<6} "
                  f"curve {int(cb_i)}/{int(cb_o)} cell={cell} robust={rb}", flush=True)
        verdicts[arm] = {"cells_passed": npass, "robust_cells": robust_cells,
                         "pass_6": npass == 6, "robust_all": robust_cells == 3}
        print(f"  -> {arm}: {npass}/6 cells, robust {robust_cells}/3 lanes", flush=True)

    payload["verdicts"] = verdicts
    payload["pass_6"] = {a: verdicts[a]["pass_6"] for a in TESTED}
    payload["robust_all"] = {a: verdicts[a]["robust_all"] for a in TESTED}
    both = [a for a in TESTED if verdicts[a]["pass_6"] and verdicts[a]["robust_all"]]
    payload["arms_passing_both_gates"] = both
    payload["family_closed"] = not both
    payload["elapsed_sec"] = round(time.time() - t0, 2)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print("\n" + "=" * 100, flush=True)
    for arm in TESTED:
        v = verdicts[arm]
        print(f"  {arm:<3} 6/6={v['pass_6']!s:<5} robust={v['robust_all']!s:<5} "
              f"cells={v['cells_passed']}/6", flush=True)
    print("=" * 100, flush=True)
    print(f"  ARMS PASSING BOTH GATES: {both if both else 'NONE'}", flush=True)
    print(f"  FAMILY: {'CLOSED' if not both else 'still open - NOT adopted'}", flush=True)
    print(f"wrote {OUT} ({payload['elapsed_sec']}s)", flush=True)


if __name__ == "__main__":
    main()
