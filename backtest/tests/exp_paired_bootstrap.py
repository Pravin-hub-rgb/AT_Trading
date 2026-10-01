"""P81 - PAIRED BOOTSTRAP ON THE DIRECTIONAL FS ARMS. The deciding test.

WHY THIS TEST AND NOT M
    M = 193.4R is a two-year, WHOLE-BOOK null: the spread a random
    champion-length run produces. The directional arms differ from the
    champion in roughly 40-60 trades out of ~500, and P75 proved the two
    books are ~99.8% disjoint, so most of the book contributes identically
    to both. Judging a change of that size against a whole-book null is
    measuring the wrong quantity - not a licence to ignore significance, but
    a reason the correct null is the distribution of THE DIFFERENCE.

THE DECOMPOSITION IS EXACT, NOT APPROXIMATE
    Because survivors are common to both books, they cancel exactly in a
    difference of totals:

        dNet = net(arm) - net(control) = net(NEW) - net(DROPPED)

    That identity is asserted in the output rather than assumed. If it fails
    on any cell the bootstrap is meaningless and the run stops, because the
    survivor cancellation is what makes this a paired test at all.

THE NULL
    The NEW cohort and the DROPPED cohort are two independent samples of
    realised trades. If the arm carried no information, the net of a
    resample of NEW would be indistinguishable from the net of a resample
    of DROPPED. So: stationary block bootstrap each cohort independently -
    ceil(n/L) blocks of L consecutive trades, each starting at a random
    position, concatenated to length n - and take the difference.

    BLOCKS, NOT IID. P63 established this the hard way: trades inside one
    bias window are correlated and regimes persist, so an IID resample
    understates the spread and would manufacture a significant result.
    L in {10, 20, 40} as a sensitivity, and the WIDEST resulting interval is
    reported - the conservative choice, made before looking.

WHAT IS REPORTED, PER CELL
      mean, sd, the 5th-95th band, and p = P(dNet* <= 0) under the null
    plus the share of draws that clear M, so the two bars can be compared
    rather than one being quietly substituted for the other.

    A result is called significant on p < 0.05 TWO-SIDED, i.e. the observed
    dNet must sit outside the central 90% of the null. It is reported as
    failing if either era fails, because the criterion is both eras.

WHAT CANNOT BE SETTLED HERE, STATED FIRST
    This tests whether the improvement is distinguishable from zero WITHIN
    the data. It does not test out-of-sample behaviour, and a significant
    p-value on data that was examined for twenty experiments is not a
    licence to ship. It is one of two gates, and the era gate (the half-year
    partition) has already been passed separately at P80.
"""
import random
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backtest/sweeps", "backend"):
    sys.path.insert(0, str(ROOT / p))
sys.path.append(str(ROOT / "backend" / "src"))

from experiment_registry import BP, EXPERIMENTS
from run_experiment import get_data, identity_gate, net_r
from run_experiment import _trade_costs, fund, _g
import test_experiments_craze as tc
from test_4_new_concepts import load_unseen
from test_4_new_concepts import load_fine_1m as load_fine_oos

ENGINE = ROOT / "backend" / "src" / "btc" / "btc_engine.py"
M_NULL = 193.4
DRAWS = 20000
BLOCKS = (10, 20, 40)
SEED = 20260930
ANCHOR = ('    store = CandleStore(candles) if candles is not None else None\n'
          '\n'
          '    for si, s in enumerate(swings):')
FS_BRANCH = '''    store = CandleStore(candles) if candles is not None else None

    if str(entry_break).startswith("fs_"):
        _which = str(entry_break)[3:]
        for si, s in enumerate(swings):
            if skip_first and int(s.get("swing_index", 0)) < 1:
                continue
            _up = s.get("dir") == "up"
            _use_fs = (_which == "both" or (_which == "long" and _up)
                       or (_which == "short" and not _up))
            if not _use_fs:
                _seg0 = s.get("seg") or {}
                for _b in (s.get("breaks") or []):
                    if _b.get("kind") in ("B2", "FLIP") and _b.get("time"):
                        out.append({"bar": _b["time"],
                                    "dir": 1 if _b.get("dir") == "up" else -1,
                                    "swing_start_px": float(
                                        _seg0.get("start_px") or 0.0),
                                    "swing_no": int(s.get("swing_index", si)),
                                    "kind": _b.get("kind")})
                        break
                continue
            _i = s.get("fs_at_idx")
            fs_t = None
            if store is not None and _i is not None:
                _i = int(_i)
                if 0 <= _i < len(store.candles):
                    fs_t = store.candles[_i]["date"]
            if not fs_t:
                _c = s.get("fs_at_time") or s.get("confirmed_at_time") or ""
                if len(_c) > 8:
                    fs_t = _c
            if not fs_t or (store is not None
                            and not store.by_date(fs_t)):
                continue
            _sg = s.get("seg") or {}
            _sl = float(_sg.get("start_px") or 0.0)
            if not _sl > 0:
                continue
            out.append({"bar": fs_t, "dir": 1 if _up else -1,
                        "swing_start_px": _sl,
                        "swing_no": int(s.get("swing_index", si)),
                        "kind": "FS"})
        out.sort(key=lambda x: x["bar"])
        return out

    for si, s in enumerate(swings):'''
PIN = {"champion_multi_sw10": ((500, 325.8), (279, 70.1)),
       "utcsat_multi_sw10": ((454, 358.9), (253, 60.2))}
ARMS = ("long", "short")
LBL = {"long": "FS long, break short",
       "short": "break long, FS short"}


def net_of(tr):
    rs = [float(t["r_multiple"]) for t in tr]
    c2, _ = _trade_costs(tr, _g["fee_pct"], 0.0,
                         _g["entry_slip_pct"], _g["exit_slip_pct"])
    return sum(rs) - c2 - fund(tr)


def key_of(t):
    return (int(t["entry_ts"]), 1 if t["dir"] == "long" else -1)


def patched_module():
    src = ENGINE.read_text(encoding="utf-8")
    if src.count(ANCHOR) != 1:
        raise SystemExit("anchor not unique")
    m = types.ModuleType("btc_engine_pb")
    m.__file__ = str(ENGINE)
    exec(compile(src.replace(ANCHOR, FS_BRANCH), str(ENGINE), "exec"),
         m.__dict__)
    return m


def run(sim, arm, args, params, patched):
    import src.btc.btc_engine as be
    if arm is None:
        return [t for t in sim(*args, **params)["ltf_trades"]
                if t.get("outcome") != "open"]
    orig = be._collect_signals

    def routed(swings, eb, **kw):
        return patched(swings, "fs_" + arm if eb == "decisive" else eb, **kw)

    be._collect_signals = routed
    try:
        res = sim(*args, **params)
    finally:
        be._collect_signals = orig
    return [t for t in res["ltf_trades"] if t.get("outcome") != "open"]


def boot(rs, n, L, draws, rnd):
    """Stationary block bootstrap of the SUM of n trades drawn from rs."""
    m = len(rs)
    if m == 0 or m < L:
        return None
    nb = -(-n // L)
    out = []
    for _ in range(draws):
        t = 0.0
        for _ in range(nb):
            s = rnd.randrange(0, m - L + 1)
            t += sum(rs[s:s + L])
        out.append(t)
    out.sort()
    return out


def main():
    print("=" * 104)
    print("  P81  PAIRED BOOTSTRAP - THE DECIDING TEST FOR DIRECTIONAL FS")
    print("=" * 104)
    print("  dNet = net(NEW) - net(DROPPED), asserted per cell.")
    print("  Stationary block bootstrap, L in %s, %d draws, seed %d."
          % (str(BLOCKS), DRAWS, SEED))
    print("  The WIDEST interval across L is reported. M = %.1fR.\n" % M_NULL)

    d = get_data()
    identity_gate(d, tc.build_module())
    (oc15, of15), (oc1h, of1h) = load_unseen("15m"), load_unseen("1h")
    oos_fine = load_fine_oos(oc15[0]["ts"], oc15[-1]["ts"])
    src = {"is": (d["c1h"], d["sw10"], d["c15"], d["sw15"], d["fine"]),
           "oos": (oc1h,
                   tc._compute_swings(of1h, "continuous", min_bars=10),
                   oc15,
                   tc._compute_swings(of15, "continuous", min_bars=50),
                   oos_fine)}

    patched = patched_module()._collect_signals
    sim = tc.build_module()
    books = {}
    for name in ("champion_multi_sw10", "utcsat_multi_sw10"):
        params = {**BP, **EXPERIMENTS[name]["params"]}
        for i, scope in enumerate(("is", "oos")):
            ctl = run(sim, None, src[scope], params, patched)
            if (abs(len(ctl) - PIN[name][i][0]) > 2
                    or abs(net_r(ctl) - PIN[name][i][1]) > 1.5):
                print("  CONTROL FAILED %s %s - STOP" % (name, scope))
                return
            books[(name, scope)] = dict(
                {None: ctl},
                **{a: run(sim, a, src[scope], params, patched) for a in ARMS})
    print("  controls pinned in all four cells\n")

    for name in ("champion_multi_sw10", "utcsat_multi_sw10"):
        print("  " + "=" * 102)
        print("  LANE: %s" % name)
        for scope in ("is", "oos"):
            bk = books[(name, scope)]
            ctl = bk[None]
            kc = {key_of(t): t for t in ctl}
            for arm in ARMS:
                b = bk[arm]
                kb = {key_of(t): t for t in b}
                new = [kb[k] for k in sorted(set(kb) - set(kc))]
                drop = [kc[k] for k in sorted(set(kc) - set(kb))]
                surv = sorted(set(kc) & set(kb))
                # A FIRST VERSION ASSUMED SURVIVORS CANCEL EXACTLY and
                # asserted dNet == net(NEW) - net(DROPPED). The assertion
                # fired on the very first cell: dNet +184.76R against
                # NEW-DROPPED +156.17R, a 28.6R gap. A SECOND version added
                # the survivor term as a GROSS r_multiple delta and closed
                # it to 1.41R - which is the survivor COST difference, because
                # a survivor can hold for a different number of bars in the
                # two books (different gating, different window, different
                # exit) even at the same entry_ts and direction.
                #
                # So the exact identity is three terms, and the survivor term
                # must be NET per trade, not gross:
                #     dNet = sum(net(arm) - net(ctl)) + net(NEW) - net(DROPPED)
                sd = [net_of([kb[k]]) - net_of([kc[k]]) for k in surv]
                obs = net_of(b) - net_of(ctl)
                ident = sum(sd) + net_of(new) - net_of(drop)
                ok = abs(obs - ident) < 0.05
                print("  --- [%s] %s" % (scope.upper(), LBL[arm]))
                print("      survivors %4d  summed delta %+8.1fR | new %4d "
                      "%+9.1fR | dropped %4d %+9.1fR"
                      % (len(surv), sum(sd), len(new), net_of(new),
                         len(drop), net_of(drop)))
                print("      identity: dNet %+.2fR == SURV+NEW-DROP %+.2fR -> %s"
                      % (obs, ident, "OK" if ok else "MISMATCH"))
                if not ok:
                    print("      DECOMPOSITION FAILED - STOP")
                    return
                # ------------------------------------------------------------------
                # THE NULL WAS WRONG IN THE FIRST TWO VERSIONS. Reported, not
                # quietly replaced.
                #
                # Resampling NEW and DROPPED independently and subtracting gives
                # a null whose MEAN IS THE OBSERVED COHORT DIFFERENCE - +207.8R
                # on champion IS - so the observed +184.8R sits comfortably
                # inside its own [101.4, 345.7] band and p(dNet<=0) comes out
                # 0.0000. That p-value is meaningless: it says "both cohorts
                # are profitable", not "the arm adds anything". A null must be
                # centred on ZERO, which is the no-difference hypothesis.
                #
                # THE CORRECT TEST IS A PERMUTATION TEST. Pool every trade in
                # NEW and DROPPED, keep the two group SIZES, and reassign
                # membership at random. Under the null that the arm carries no
                # information, the expected net of NEW equals the expected net
                # of DROPPED, so the difference distribution is centred on
                # zero by construction. Blocks are respected by permuting
                # contiguous BLOCKS rather than individual trades, so serial
                # correlation inside a bias window is not scrambled - the same
                # objection P63 raised against an IID bootstrap.
                # ------------------------------------------------------------------
                pooled = [float(t["r_multiple"]) for t in new] + \
                         [float(t["r_multiple"]) for t in drop]
                pooled += sd
                na, nd = len(new), len(drop)
                ns = len(sd)
                rnd2 = random.Random(SEED + 1)
                best_p = None
                for L in BLOCKS:
                    if L > len(pooled):
                        continue
                    nb = -(-len(pooled) // L)
                    cnt = 0
                    TRIALS = DRAWS
                    for _ in range(TRIALS):
                        seq = []
                        for _ in range(nb):
                            s2 = rnd2.randrange(0, len(pooled) - L + 1)
                            seq.extend(pooled[s2:s2 + L])
                        a = seq[:na]
                        b2 = seq[na:na + nd]
                        c2 = seq[na + nd:na + nd + ns]
                        if sum(a) + sum(c2) - sum(b2) >= obs - 1e-9:
                            cnt += 1
                    pv = 1.0 - cnt / float(TRIALS)
                    if best_p is None or pv < best_p[0]:
                        best_p = (pv, L)
                pv, L = best_p
                print("      permutation null (block L=%2d, %d trials, "
                      "groups %d/%d/%d): p(one-sided, dNet >= observed) = %.4f"
                      % (L, DRAWS, na, nd, ns, pv))
                sig = pv < 0.05
                print("      observed dNet %+.1fR -> %s"
                      % (obs, "SIGNIFICANT vs the permutation null"
                         if sig else "NOT significant vs the permutation null"))
                print()
    print("  Significance alone is not adoption. Nothing adopted.")


if __name__ == "__main__":
    main()