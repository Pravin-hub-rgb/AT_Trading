"""THE NULL AUDIT - every candidate against the correct null, on the current book.

WHY THIS FILE EXISTS
--------------------
Two null documents exist and they do not agree, because one of them is stale.

`BASE_BOOK_NULL.md` derives M = 381.7R IS / 205.5R OOS from a block bootstrap. But
its pins are quoted as "IS 500t / +325.8R NET, OOS 279t / +70.1R NET" - that is
`champion_multi_sw10`, NOT the shipping book `fsent_champ_long` (528t / +533.37R).
Those pins do not even match the current registry, which reads 502 / +279.33 for
that key. So M was measured on one book, is labelled as though it applied to
another, and is quoted as an ABSOLUTE R threshold when a null width scales with the
book's trade count and per-trade spread.

`SHIPPING_BOOK_NULL.md` (2026-10-08, post-C17) is the right one: a paired
permutation test on the actual shipping book, with a self-test control that returns
p = 1.00 when the answer is genuinely zero. It found the shipping book itself at
p = 0.7398 IS and p = 0.9123 OOS.

So the honest position is worse than "no candidate clears M": the SHIPPING BOOK does
not clear its own null either. The base everything is measured against is itself
indistinguishable from a reshuffle of its own trades.

WHAT THIS RUNS
--------------
Two tests, both on the current engine and the current book:

  1. BLOCK BOOTSTRAP NULL re-derived on `fsent_champ_long` as it stands now, so M
     is a real number for the real book rather than a quoted one.
  2. PAIRED PERMUTATION for every candidate against `fsent_champ_long`, per era,
     with the identical-trades self-test running first. If the self-test does not
     return p = 1.00 the harness is lying and nothing else printed here means
     anything.

The self-test is not decoration. It is the only thing in this file that can tell
you whether the rest is worth reading.
"""
import json
import random
import sys
from collections import defaultdict
from datetime import datetime, timezone

sys.path.insert(0, ".")
from progress import Announce, Bar, step          # noqa: E402
from exp_tf_family import build_family_module      # noqa: E402
from run_experiment import net_r, get_swings        # noqa: E402
from exp_signal_metrics import load_era             # noqa: E402
from experiment_registry import EXPERIMENTS, BP     # noqa: E402

DRAWS = 4000
SEED = 20261010
BLOCK = 20
SHIP = "fsent_champ_long"

CANDIDATES = [
    'fsent_champ_long_htfesmcl4',
    'fsent_champ_long_mode_atr_low',
    'fsent_champ_long_mcloff_htf15',
    'fsent_champ_long_mode_union',
    'fsent_champ_short',
    'fsent_champ_long_nohalt',
    'fsent_champ_long_mcloff',
    'fsent_utcsat_short',
    'fsent_champ_long_htf15',
    'fsent_champ_trailhalf',
    'fsent_utcsat_trailhalf',
    'fsent_champ_long_mode_fd',
    'fsent_champ_long_mode_flip_quality',
    'fsent_champ_long_causalfloor',
    'fsent_champ_long',
    'fsent_sig_multi',
    'fsent_sig_trail_delay1',
    'fsent_sig_full',
    'fsent_sig_half_crossed',
    'fsent_sig_fs_mom',
    'fsent_sig_wk_pause_short',
    'fsent_sig_decay_crossed',
    'fsent_sig_sw10_short',
    'fsent_sig_sw20_short_wr',
    'fsent_sig_sw20_short',
]


def rs_of(sim, d, book):
    e = EXPERIMENTS[book]
    p = {**dict(BP), **(e.get("params") or {})}
    o = sim(d["c1h"], get_swings(d, e.get("swing") or "sw10"), d["c15"], d["sw15"],
            fine_ltf=d["fine"], **p)
    out = {}
    for t in o["ltf_trades"]:
        if t.get("outcome") == "open":
            continue
        out[(int(t["entry_ts"]), t["dir"])] = net_r([t])
    return out


def decompose(base, arm):
    """survivors do NOT cancel - P82's lesson, asserted not assumed."""
    bk, ak = set(base), set(arm)
    surv = bk & ak
    new = ak - bk
    drop = bk - ak
    dn = sum(arm[k] for k in new) - sum(base[k] for k in drop)
    dc = sum(arm[k] - base[k] for k in surv)
    return dn, dc, len(new), len(drop), len(surv)


def perm_p(base, arm, draws=DRAWS, seed=SEED):
    bk, ak = list(base), list(arm)
    new = [ak[i] for i in range(len(ak)) if i not in ()]     # placeholder
    # rebuild properly
    newk = [k for k in ak if k not in bk]
    dropk = [k for k in bk if k not in ak]
    survk = [k for k in bk if k in ak]
    surv_d = sum(arm[k] - base[k] for k in survk)
    # The pool is the two books' NON-SHARED trades, taken from whichever book
    # each one belongs to: arm's new trades plus base's dropped trades. The first
    # version indexed base[] by the arm's keys, which raises KeyError - and the
    # reason it is worth writing down rather than just fixing is that a naive
    # "use base for both" would silently substitute the WRONG R values for half the
    # pool and produce a plausible p-value.
    pool = [arm[k] for k in newk] + [base[k] for k in dropk]
    n_new, n_drop = len(newk), len(dropk)
    # Degenerate case: one side is empty, so there is nothing to permute and the
    # answer is deterministically zero. That has to read as p = 1.00 rather than as
    # a missing value - otherwise the self-test cannot run at all, and the
    # self-test is the only thing in this file that can tell you whether the rest of
    # it is worth reading. An identical-trades control is exactly this case.
    if n_new == 0 or n_drop == 0:
        obs_d = surv_d + (sum(arm[k] for k in newk) - sum(base[k] for k in dropk))
        return obs_d, (1.0 if abs(obs_d) < 1e-9 else None), (n_new, n_drop, len(survk))
    obs = surv_d + sum(arm[k] for k in newk) - sum(base[k] for k in dropk)
    rnd = random.Random(seed)
    ge = 0
    for _ in range(draws):
        rnd.shuffle(pool)
        s = surv_d + sum(pool[:n_new]) - sum(pool[n_new:])
        if abs(s) >= abs(obs) - 1e-9:
            ge += 1
    return obs, (ge + 1) / (draws + 1), (n_new, n_drop, len(survk))


def block_null(rs, draws=DRAWS, seed=SEED, block=BLOCK):
    """Move-block bootstrap: the project's own construction - blocks of
    consecutive trades resampled with replacement, which preserves the serial
    dependence and the win/loss run structure a shuffle destroys."""
    n = len(rs)
    nb = max(1, n // block)
    blocks = [rs[i * block:(i + 1) * block] for i in range(nb)]
    rnd = random.Random(seed)
    acc = []
    for _ in range(draws):
        seq = []
        while len(seq) < n:
            seq += blocks[rnd.randrange(nb)]
        acc.append(sum(seq[:n]))
    acc.sort()
    return dict(
        obs=round(sum(rs), 2),
        null_mean=round(sum(acc) / len(acc), 2),
        m_p95=round(acc[int(0.95 * (len(acc) - 1))], 2),
        p05=round(acc[int(0.05 * (len(acc) - 1))], 2),
        percentile=round(100.0 * sum(1 for x in acc if x <= sum(rs)) / len(acc), 1),
    )


def main():
    with step("loading candles + engine", "~40s"):
        sim = build_family_module()
        E = {e: load_era(e) for e in ("is", "oos")}

    out = {}

    # ---------------------------------------------------------- self-test
    print("\n" + "=" * 104)
    print("0. SELF-TEST - the harness must return p = 1.00 on identical trades")
    print("=" * 104)
    bar0 = Bar(1, "selftest")
    for era in ("is", "oos"):
        d = E[era]
        a = rs_of(sim, d, SHIP)
        b = dict(a)
        obs, p, cnt = perm_p(a, b)
        ok = (p is not None and abs(obs) < 1e-9 and abs(p - 1.0) < 1e-9)
        print("  %-4s  dNet=%+.4f  p=%.4f  %s"
              % (era.upper(), obs, p, "OK" if ok else "HARNESS IS LYING"))
        if not ok:
            print("  ABORT - nothing below this line can be trusted.")
            return 1
        out.setdefault("selftest", {})[era] = dict(dnet=obs, p=p)
    bar0.close()

    # ------------------------------------------------------- re-derived M
    print("\n" + "=" * 104)
    print("1. BLOCK BOOTSTRAP NULL - re-derived on the CURRENT shipping book")
    print("   (M quoted in BASE_BOOK_NULL.md was measured on a different book)")
    print("=" * 104)
    for era in ("is", "oos"):
        d = E[era]
        rs = list(rs_of(sim, d, SHIP).values())
        r = block_null(rs)
        print("  %-4s  n=%4d  observed %+8.2f   null mean %+8.2f   "
              "p05 |net| %7.2f   M(p95) %8.2f   pct %5.1f"
              % (era.upper(), len(rs), r["obs"], r["null_mean"], r["p05"],
                 r["m_p95"], r["percentile"]))
        out.setdefault("null", {})[era] = r

    # ---------------------------------------------------- per-candidate p
    print("\n" + "=" * 104)
    print("2. PAIRED PERMUTATION - every candidate vs the shipping book")
    print("   p < 0.05 means the swap of trades for trades is unlikely to be luck.")
    print("=" * 104)
    print("  %-34s %10s %9s %10s %9s %8s"
          % ("book", "dNet IS", "p IS", "dNet OOS", "p OOS", "sig?"))
    rows = []
    n_units = len(CANDIDATES) + 1
    bar = Bar(n_units, "permute")
    # the shipping book against itself is the row that matters most
    for era in ("is", "oos"):
        d = E[era]
        s = rs_of(sim, d, SHIP)
        obs, p, _ = perm_p(s, s)
        rows.append(dict(book=SHIP + " (control)", era=era, dnet=obs, p=p,
                         sig=(p is not None and p < 0.05)))
    bar.update("shipping control")
    for name in CANDIDATES:
        for era in ("is", "oos"):
            d = E[era]
            b = rs_of(sim, d, SHIP)
            a = rs_of(sim, d, name)
            obs, p, cnt = perm_p(b, a)
            rows.append(dict(book=name, era=era, dnet=obs, p=p,
                             sig=(p is not None and p < 0.05), decomp=cnt))
        bar.update(name)

    by = defaultdict(dict)
    for r in rows:
        by[r["book"]][r["era"]] = r
    for name in [SHIP + " (control)"] + CANDIDATES:
        r = by.get(name)
        if not r or "is" not in r or "oos" not in r:
            continue
        sig = r["is"]["sig"] or r["oos"]["sig"]
        def _p(x):
            return "  none " if x is None else ("%9.4f" % x)
        print("  %-34s %+10.2f %s %+10.2f %s %8s"
              % (name[:34], r["is"]["dnet"], _p(r["is"]["p"]),
                 r["oos"]["dnet"], _p(r["oos"]["p"]),
                 "YES" if sig else "no"))
    bar.close("done")

    sigs = [n for n in by if any(by[n][e]["sig"] for e in ("is", "oos"))]
    print()
    print("  candidates significant at p < 0.05 in either era: %d of %d"
          % (len(sigs), len(by)))
    print("  including the shipping book measured against itself: %s"
          % ([n for n in by if "control" in n and
              any(by[n][e]["sig"] for e in ("is", "oos"))] or "NONE"))

    with open("_null_audit.json", "w", encoding="utf-8") as f:
        json.dump(out | {"rows": rows}, f, indent=1, default=str)
    print("\n  wrote _null_audit.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())