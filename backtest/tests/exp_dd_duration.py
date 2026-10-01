"""P92 - HOW LONG IS THE ACCOUNT UNDER WATER? The number that decides
whether 37.3R is survivable.

FROM THE BRIEF, SPACE BUNNY'S P91
    "37.3R over 278 days is the wrong headline for a shipping decision.
     What matters is how long the account is under water and how many
     trades it takes to get back."

AND IT IS A NUMBER THIS PROGRAMME PROMISED AND DID NOT DELIVER
    CHAMP_ROBUST_P83.md states, in its own limitations: "Recovery time after
    the max drawdown is not reported... and that number matters more than
    the depth to anyone holding the bot." It was left out because the
    harness computed peak and trough but never exercised the recovery loop.
    This is that loop.

WHY IT IS A MEASUREMENT, NOT A CANDIDATE
    Nothing is selected. No trade is added, removed or re-scored. The output
    is a description of the champion's realised path, and it produces no
    dNet. It cannot be adopted and nothing in production changes.

THE ANSWER AN OWNER ACTUALLY NEEDS
    Not "how deep" - 37.3R is known. The three questions are:

      1. HOW LONG is the account below its previous equity high, in
         calendar days and in trades? Not just the worst episode - the
         distribution, because a single number hides whether 278 days is
         typical or rare.
      2. HOW MANY TRADES to recover from the worst episode?
      3. Does that hold up when the tail is removed? S3/P91 established
         this book's net is tail-concentrated (the top 5% carries well
         over 100% of net), so every duration figure is reported on the
         full book AND with the top 5% of trades removed. If the book's
         duration is entirely a property of a handful of winners, that is
         the first thing an owner should know.

METHOD
    Walk the realised R sequence in time order. Track the running peak.
    An "underwater episode" runs from the peak until equity first regains
    it. Depth is peak minus trough; length is measured in calendar days
    between the peak bar and the recovery bar, and in the number of trades
    inside that span. Episodes that never recover within the sample are
    reported as OPEN, not silently dropped - a book that ends underwater is
    a different fact from one that recovered.

    Duration is also reported across a block bootstrap, because a single
    path is a single draw and P63 established that the deck-relative null
    is what tells you whether a duration is unusual.
"""
import random
import sys
from datetime import datetime, timezone
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

DAY = 86400
DRAWS = 4000
SEED = 20261005
BLOCKS = (10, 20, 40)
PIN = {"champion_multi_sw10": ((500, 325.8), (279, 70.1)),
       "utcsat_multi_sw10": ((454, 358.9), (253, 60.2))}


def net_of(tr):
    rs = [float(t["r_multiple"]) for t in tr]
    c2, _ = _trade_costs(tr, _g["fee_pct"], 0.0,
                         _g["entry_slip_pct"], _g["exit_slip_pct"])
    return sum(rs) - c2 - fund(tr)


def episodes(tr):
    """Every underwater episode: (peak_i, trough_i, recover_i or None,
    depth, days, n_trades).  Days are calendar between the peak trade and
    the recovery trade, or between peak and the end of the sample."""
    eq = pk = 0.0
    pk_i = 0
    trough = 0.0
    out = []
    open_at = None          # [peak_i, trough_i, recovery_i or None]
    for i, t in enumerate(tr):
        eq += float(t["r_multiple"])
        if eq >= pk:
            if open_at is not None:
                a, b, c = open_at[0], open_at[1], i
                days = ((int(tr[i]["entry_ts"]) - int(tr[a]["entry_ts"]))
                        / DAY)
                out.append((a, b, i, pk - trough, days, i - a))
                open_at = None
            pk = eq
            pk_i = i
            trough = 0.0
        else:
            d = pk - eq
            if open_at is None:
                open_at = [pk_i, i, None]
            if d > trough:
                trough = d
                open_at[1] = i
    if open_at is not None:
        a, b = open_at[0], open_at[1]
        days = (int(tr[-1]["entry_ts"]) - int(tr[a]["entry_ts"])) / DAY
        out.append((a, b, None, pk - trough, days, len(tr) - 1 - a))
    return out


def pct(vals, q):
    if not vals:
        return 0.0
    s = sorted(vals)
    return s[min(len(s) - 1, int(q * len(s)))]


def boot_durations(tr, draws, rnd):
    """Stationary block bootstrap; return the worst-episode duration
    distribution, in calendar days."""
    rs = [float(t["r_multiple"]) for t in tr]
    ts = [int(t["entry_ts"]) for t in tr]
    m = len(rs)
    worst = []
    for _ in range(draws):
        seq, st = [], []
        while len(seq) < m:
            L = min(BLOCKS[rnd.randrange(len(BLOCKS))], m)
            s = rnd.randrange(0, m - L + 1)
            for k in range(L):
                seq.append(rs[s + k])
                st.append(ts[s + k])
        eq = pk = 0.0
        pk_t = st[0]
        worstd = 0.0
        for i, x in enumerate(seq):
            eq += x
            if eq >= pk:
                pk = eq
                pk_t = st[i]
            else:
                dd_days = (st[i] - pk_t) / DAY
                if dd_days > worstd:
                    worstd = dd_days
        worst.append(worstd)
    return worst


def main():
    print("=" * 100)
    print("  P92  HOW LONG IS THE ACCOUNT UNDER WATER?")
    print("=" * 100)
    print("  P83 reported depth (37.3R) and its own limitations section said")
    print("  recovery time was the number that matters more and was never")
    print("  computed. This is that. Nothing is selected; no dNet.")
    print("  Reported on the full book AND with the top 5% of trades removed.\n")

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

    books = {}
    for name in ("champion_multi_sw10", "utcsat_multi_sw10"):
        params = {**BP, **EXPERIMENTS[name]["params"]}
        for i, scope in enumerate(("is", "oos")):
            tr = [t for t in tc.build_module()(
                *src[scope], **params)["ltf_trades"]
                if t.get("outcome") != "open"]
            if (abs(len(tr) - PIN[name][i][0]) > 2
                    or abs(net_r(tr) - PIN[name][i][1]) > 1.5):
                print("  CONTROL FAILED %s %s - STOP" % (name, scope))
                return
            books[(name, scope)] = tr

    for name in ("champion_multi_sw10", "utcsat_multi_sw10"):
        print("  " + "=" * 98)
        print("  LANE: %s" % name)
        for scope in ("is", "oos"):
            tr = books[(name, scope)]
            eps = episodes(tr)
            open_eps = [e for e in eps if e[2] is None]
            dd_days = [e[4] for e in eps]
            worst = max(eps, key=lambda e: e[3]) if eps else None
            print("  --- [%s]  %d trades, net %+.1fR, %d underwater episodes"
                  " (%d still open)"
                  % (scope.upper(), len(tr), net_of(tr), len(eps),
                     len(open_eps)))
            if eps:
                print("      episode depth:  median %.1fR   p90 %.1fR   "
                      "worst %.1fR"
                      % (pct([e[3] for e in eps], 0.5),
                         pct([e[3] for e in eps], 0.9),
                         max(e[3] for e in eps)))
                print("      episode DAYS:   median %.0f   p90 %.0f   "
                      "worst %.0f"
                      % (pct(dd_days, 0.5), pct(dd_days, 0.9), max(dd_days)))
                print("      episode TRADES: median %.0f   worst %.0f"
                      % (pct([e[5] for e in eps], 0.5),
                         max(e[5] for e in eps)))
            if worst:
                print("      worst episode: %.1fR deep over %.0f calendar "
                      "days / %d trades%s"
                      % (worst[3], worst[4], worst[5],
                         "  [NEVER RECOVERED in sample]" if worst[2] is None
                         else ""))
            # tail sensitivity: remove the top 5% of trades by R
            keep = [t for t in tr
                    if float(t["r_multiple"])
                    <= pct([float(x["r_multiple"]) for x in tr], 0.95)]
            if keep and len(keep) < len(tr):
                e2 = episodes(keep)
                w2 = max(e2, key=lambda e: e[3]) if e2 else None
                print("      top-5%% removed (%d trades, net %+.1fR): worst "
                      "episode %s"
                      % (len(keep), net_of(keep),
                         ("%.1fR over %.0f days" % (w2[3], w2[4])) if w2
                         else "none"))
            rnd = random.Random(SEED)
            w = boot_durations(tr, DRAWS, rnd)
            print("      block bootstrap of worst-episode duration: "
                  "median %.0f days, p90 %.0f days"
                  % (pct(w, 0.5), pct(w, 0.9)))
            print()
    print("  This is a description of the champion's realised path.")
    print("  Nothing adopted; production unchanged.")


if __name__ == "__main__":
    main()