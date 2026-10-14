"""
WHAT IS max_consecutive_losses ACTUALLY DOING?  And is htffs just long?

Two questions this file answers with evidence rather than assertion.

QUESTION 1 - mcl is not a streak breaker

The shipping engine (backend/src/btc/engines/htf_ltf/unified.py) does this:

    entry gate, L1312            booking, after the trade closes
    ---------------              ----------------------------------
    if halt_skip_next:           if max_consecutive_losses > 0:
        halt_skip_next=False         if r_multiple <= 0:
        consecutive_losses = 0           consecutive_losses += 1
        continue   <-- DROP              if >= max_consecutive_losses:
    this signal entirely               halt_skip_next = True
                                          consecutive_losses = 0   <-- RESET ON FIRE
                                   else:
                                       consecutive_losses = 0

Three properties follow, and all three are testable:

  a) The counter RESETS when the halt fires. So a losing run of length L fires the
     halt floor(L/N) times. It never stops trading; it keeps nibbling one trade.
  b) The skipped signal is CONSUMED, not deferred. `continue` drops that entry
     forever. It is not a pause that waits for a better regime.
  c) Nothing waits for a win before re-enabling. There is no recovery condition.

So the mechanism is "every N consecutive losses, discard exactly one signal" -
a THROTTLE - not a risk control that shortens a losing run. That is why mcl=0
showed a WORSE MaxConsecL than mcl=3 in all four books: the halt never
shortened the streak, it only removed isolated trades.

PREDICTION, falsifiable: if the counter resets on fire, then the number of trades
skipped at mcl=N must equal the sum of floor(L/N) over the losing runs observed
at mcl=0. If the mechanism were something else the prediction would miss.

QUESTION 2 - is htffs just long with extra trades?

htffs trades 753 times on IS where long trades 497, on the SAME swing chain. It
looks like the best book purely because it trades more. The test is set overlap:
how many of htffs's entries are literally long's entries, and how many are extra.

Usage:
    $env:PYTHONIOENCODING='utf-8'
    ..\\..\\..\\backend\\venv\\Scripts\\python.exe -u exp_mcl_mechanism.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

HERE = Path(__file__).resolve().parent
BOOKS = ["fsent_champ_long", "fsent_champ_short",
         "fsent_champ_long_htf15", "fsent_champ_long_htffs"]


def main() -> int:
    from exp_tf_family import build_family_module
    from run_experiment import BP
    from experiment_registry import EXPERIMENTS
    from src.btc.btc_swing import compute_btc_swings
    from engine.v18_params import SWING

    sim = build_family_module()
    from run_experiment import get_data
    d = get_data()

    def chain(fl, mb, gap=1):
        return compute_btc_swings(
            fl, opts={"minBars": max(2, int(mb)), "b2GapBars": gap},
            max_swings=max(1, len(fl) // 2))

    sw15 = chain(d["f15"], SWING["min_bars_15m"])
    pick = {"sw10": chain(d["f1h"], 10), "htf15": chain(d["f1h"], 15),
            "sw20": chain(d["f1h"], SWING["min_bars_1h"])}

    def run(book, mcl, cd=None):
        cfg = EXPERIMENTS[book]
        p = {**BP, **cfg["params"]}
        p.setdefault("exp_partial_r", 0.0)
        p["max_consecutive_losses"] = mcl
        if cd is not None:
            p["cooldown_bars"] = cd
        sw = pick.get(cfg.get("swing") or "sw10")
        r = sim(d["c1h"], sw, d["c15"], sw15, fine_ltf=d["fine"], **p)
        tr = r["ltf_trades"] if isinstance(r, dict) else r
        return [t for t in tr if str(t.get("outcome", "")).lower() != "open"]

    out = {}

    # ================= QUESTION 1 ==========================================
    print("=" * 104)
    print("Q1  IS mcl A STREAK BREAKER?  Prediction: skips == sum of floor(L/N) over losing runs")
    print("=" * 104)
    print("     Because the engine resets the counter the instant the halt fires.")
    print()
    print("  %-24s %6s %6s %5s %8s %8s %8s %9s" %
          ("book", "n(0)", "runL", "N", "firings", "lost", "shadow", "verdict"))
    print("  " + "-" * 84)

    proof = {}
    for b in BOOKS:
        base = run(b, 0)
        rs = [float(t["r_multiple"]) for t in base]
        runs, cur = [], 0
        for r in rs:
            if r <= 0:
                cur += 1
            else:
                if cur:
                    runs.append(cur)
                cur = 0
        if cur:
            runs.append(cur)
        n0 = len(base)
        rows = []
        for N in (1, 2, 3, 4, 6, 8, 12):
            fires = sum(L // N for L in runs)   # halt FIRINGS in the mcl=0 walk
            lost = n0 - len(run(b, N))          # trades actually removed
            shadow = (fires - lost) / fires * 100.0 if fires else 0.0
            rows.append({"N": N, "firings": fires, "lost": lost,
                         "shadow_pct": round(shadow, 1)})
            print("  %-24s %6s %6s %5d %8d %8d %7.0f%% %9s" %
                  (b if N == 1 else "", n0 if N == 1 else "",
                   "-" if N == 1 else "", N, fires, lost, shadow, ""))
        proof[b] = {"n0": n0, "runs": len(runs), "max_run": max(runs) if runs else 0,
                    "rows": rows}

    print()
    print("  longest losing run at mcl=0, per book:")
    for b in BOOKS:
        p = proof[b]
        print("      %-24s %2d runs, longest %2d" % (b, p["runs"], p["max_run"]))
    out["q1"] = proof

    # ---- what does the halt throw away? ------------------------------------
    print()
    print("=" * 104)
    print("Q1b  THE TRADES THE HALT THROWS AWAY - are they winners or losers?")
    print("=" * 104)
    print("  Walk the mcl=0 sequence, apply the engine's own rule, and look at what")
    print("  each skipped trade was actually worth.")
    print()
    print("  %-24s %4s %9s %9s %9s %9s" % ("book", "N", "skipped", "their NET", "their WR%", "kept NET"))
    print("  " + "-" * 68)
    skip_proof = {}
    for b in BOOKS:
        base = run(b, 0)
        rs = [float(t["r_multiple"]) for t in base]
        for N in (3,):
            kept, skipped = [], []
            cl, fire = 0, False
            for r in rs:
                if fire:
                    fire = False
                    cl = 0
                    skipped.append(r)
                    continue
                kept.append(r)
                if r <= 0:
                    cl += 1
                    if cl >= N:
                        fire = True
                        cl = 0
                else:
                    cl = 0
            w = [r for r in skipped if r > 0]
            print("  %-24s %4d %9d %+9.1f %9.1f %+9.1f" %
                  (b, N, len(skipped), sum(skipped),
                   100.0 * len(w) / len(skipped) if skipped else 0.0, sum(kept)))
            skip_proof[b] = {"n": N, "skipped": len(skipped),
                             "skipped_net": round(sum(skipped), 2),
                             "skipped_wr": round(100.0 * len(w) / len(skipped), 1) if skipped else 0.0,
                             "kept_net": round(sum(kept), 2)}
    print()
    print("  If the skipped trades are net POSITIVE, the halt is deleting winners and")
    print("  the mechanism is working against the strategy, not for it.")
    out["q1b"] = skip_proof

    # ---- is the halt shadowed by the cooldown? ------------------------------
    print()
    print("=" * 104)
    print("Q1c  IS THE HALT SHADOWED BY cooldown_bars?  Both block entries after a loss.")
    print("=" * 104)
    print("  If mcl's skips land on signals the cooldown would have blocked anyway,")
    print("  then removing mcl costs FEWER trades when cooldown is already on.")
    print()
    print("  %-24s %14s %14s %14s" % ("book", "lost @cd=8", "lost @cd=0", "shadowed?"))
    print("  " + "-" * 70)
    sh = {}
    for b in BOOKS:
        on = len(run(b, 0, cd=8)) - len(run(b, 3, cd=8))
        off = len(run(b, 0, cd=0)) - len(run(b, 3, cd=0))
        verdict = "yes - shadowed" if on < off * 0.75 else "no - independent"
        print("  %-24s %14d %14d %14s" % (b, on, off, verdict))
        sh[b] = {"lost_cd8": on, "lost_cd0": off}
    print()
    print("  cd=8 skips entries for 8 bars after a loss. A halt skip landing inside")
    print("  that window removes nothing - the cooldown already took it.")
    out["q1c"] = sh

    # ================= QUESTION 2 ==========================================
    print()
    print("=" * 104)
    print("Q2  IS htffs JUST long WITH MORE TRADES?  Set overlap on entry identity.")
    print("=" * 104)
    long_t = run("fsent_champ_long", 3)
    ht_t = run("fsent_champ_long_htffs", 3)

    def key(t):
        return (int(t["entry_ts"]), t.get("dir"))

    L = {key(t): t for t in long_t}
    H = {key(t): t for t in ht_t}
    shared = set(L) & set(H)
    only_h = set(H) - set(L)
    only_l = set(L) - set(H)

    def agg(d, keys):
        v = [float(d[k]["r_multiple"]) for k in keys if k in d]
        return len(v), (sum(v) if v else 0.0)

    n_sh, r_sh = agg(H, shared)
    n_oh, r_oh = agg(H, only_h)
    n_ol, r_ol = agg(L, only_l)

    print("  long  n=%d" % len(long_t))
    print("  htffs n=%d" % len(ht_t))
    print()
    print("  %-28s %6s %12s %10s" % ("bucket", "n", "gross R", "R/trade"))
    print("  " + "-" * 58)
    print("  %-28s %6d %+12.1f %10.3f" % ("shared entries", n_sh, r_sh, r_sh / n_sh if n_sh else 0))
    print("  %-28s %6d %+12.1f %10.3f" % ("htffs ONLY (extra entries)", n_oh, r_oh, r_oh / n_oh if n_oh else 0))
    print("  %-28s %6d %+12.1f %10.3f" % ("long ONLY (htffs dropped)", n_ol, r_ol, r_ol / n_ol if n_ol else 0))
    print()
    print("  overlap: %d of htffs' %d trades are literally long's (%.1f%%)"
          % (len(shared), len(ht_t), 100.0 * len(shared) / len(ht_t)))
    print("  htffs trades %.2fx long's count" % (len(ht_t) / len(long_t)))
    out["q2"] = {"long_n": len(long_t), "htffs_n": len(ht_t),
                 "shared": n_sh, "shared_r": round(r_sh, 2),
                 "htffs_only": n_oh, "htffs_only_r": round(r_oh, 2),
                 "long_only": n_ol, "long_only_r": round(r_ol, 2)}

    (HERE / "mcl_mechanism_results.json").write_text(json.dumps(out, indent=2),
                                                     encoding="utf-8")
    print()
    print("  wrote %s" % (HERE / "mcl_mechanism_results.json"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())