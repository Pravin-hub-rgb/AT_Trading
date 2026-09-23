"""PRE-ENTRY FEATURE AUTOPSY + STRUCTURAL ALIGNMENT (2026-09-22).

The autopsy that found the biggest edge of the session: 125 of 500 king trades
had the forming 15m swing OPPOSED to the trade direction -- ALL 125 lost
(100% loss rate, -125R, zero winners in 3.7 years).

This harness reproduces the full autopsy (7 pre-entry features bucketed vs
trade outcome) so the other bot can verify every table in
docs/ANCHOR_BASIS_AUDIT.md section 3k.

Features measured (all causal, computable at entry bar close):
  1. swing age at entry     (bars from forming swing pivot to entry)
  2. running magnitude      (entry vs extreme since swing pivot, % of price)
  3. prev swing magnitude   (the swing before the generating one, %)
  4. entry candle body/range ratio
  5. entry candle close position within bar (0=low, 1=high)
  6. forming swing direction vs trade direction (the 100%-loser gate)
  7. risk as % of price (stop width)

Run:  python live_stuff/tests/exp_alignment_autopsy.py
Full-path gate results: run_experiment.py --group alignment
"""
import sys, bisect
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

from run_experiment import get_data, BP, EXPERIMENTS
import test_experiments_craze as craze


def main():
    data = get_data()
    sim = craze.build_module()
    params = {**BP, **EXPERIMENTS["champion_multi_sw10"]["params"]}
    batch = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                fine_ltf=data["fine"], **params)["ltf_trades"]
    print("batch: %d trades (champion_multi_sw10)" % len(batch))

    c15 = data["c15"]
    ts15 = [int(c["ts"]) for c in c15]
    lo15 = [float(c["low"]) for c in c15]
    hi15 = [float(c["high"]) for c in c15]
    cl15 = [float(c["close"]) for c in c15]
    op15 = [float(c["open"]) for c in c15]
    sw15 = data["sw15"]

    results = []
    for t in batch:
        E = int(t["entry_ts"])
        e_idx = bisect.bisect_left(ts15, E)
        entry = float(t["entry_price"])
        d = 1 if t["dir"] == "long" else -1
        r = float(t["r_multiple"])

        gen_sw = None
        gen_si = -1
        for si, s in enumerate(sw15):
            s_idx = int((s.get("seg") or {}).get("start_idx", -1))
            if 0 <= s_idx <= e_idx:
                gen_sw = s
                gen_si = si
        if gen_sw is None:
            continue
        gseg = gen_sw.get("seg") or {}
        g_start_idx = int(gseg.get("start_idx", 0))
        g_dir = 1 if gen_sw.get("dir") == "up" else -1

        age = e_idx - g_start_idx
        if d == 1:
            run_ext = min(lo15[g_start_idx:e_idx + 1])
            mag = (entry - run_ext) / entry * 100
        else:
            run_ext = max(hi15[g_start_idx:e_idx + 1])
            mag = (run_ext - entry) / entry * 100
        if gen_si >= 1:
            pseg = sw15[gen_si - 1].get("seg") or {}
            prev_mag = abs(float(pseg.get("end_px", 0) or 0) -
                           float(pseg.get("start_px", 0) or 0)) / entry * 100
        else:
            prev_mag = 0
        body = abs(cl15[e_idx] - op15[e_idx])
        rng = hi15[e_idx] - lo15[e_idx]
        results.append({"r": r, "age": e_idx - g_start_idx, "mag": mag,
                        "prev_mag": prev_mag,
                        "body": body / rng if rng > 0 else 0,
                        "close_pos": (cl15[e_idx] - lo15[e_idx]) / rng if rng > 0 else 0.5,
                        "match": g_dir == d,
                        "risk": abs(entry - float(t["sl"])) / entry * 100})

    def bucket_print(name, key_fn, bins):
        bk = defaultdict(list)
        for res in results:
            bk[key_fn(res)].append(res["r"])
        print("  -- %s --" % name)
        for b in bins:
            lst = bk.get(b, [])
            if not lst:
                print("    %-12s n=0" % b)
                continue
            n = len(lst); s = sum(lst)
            big = sum(x for x in lst if 2.0 <= x)
            wr = 100.0 * len([x for x in lst if 0 < x]) / n
            lr = 100.0 * len([x for x in lst if x < 0]) / n
            print("    %-12s n=%4d  R=%+8.1f  avg=%+6.3f  WR=%5.1f%%  loss=%5.1f%%  bigWin=%+7.1f"
                  % (b, n, s, s / n, wr, lr, big))
        print("")

    print("=== PRE-ENTRY FEATURE AUTOPSY (champion_multi_sw10) ===")
    print("")
    bucket_print("1. swing AGE at entry (bars from pivot to entry)",
                 lambda r: ("a:0-10" if r["age"] <= 10 else "b:11-25" if r["age"] <= 25
                            else "c:26-50" if r["age"] <= 50 else "d:51+"),
                 ["a:0-10", "b:11-25", "c:26-50", "d:51+"])
    bucket_print("2. running MAGNITUDE at entry (pct of price)",
                 lambda r: ("a:0-.5" if r["mag"] < 0.5 else "b:.5-1" if r["mag"] < 1.0
                            else "c:1-2" if r["mag"] < 2.0 else "d:2-4" if r["mag"] < 4.0 else "e:4+"),
                 ["a:0-.5", "b:.5-1", "c:1-2", "d:2-4", "e:4+"])
    bucket_print("3. PREV swing magnitude (pct)",
                 lambda r: ("a:0-.5" if r["prev_mag"] < 0.5 else "b:.5-1" if r["prev_mag"] < 1.0
                            else "c:1-2" if r["prev_mag"] < 2.0 else "d:2+"),
                 ["a:0-.5", "b:.5-1", "c:1-2", "d:2+"])
    bucket_print("4. entry candle BODY/RANGE",
                 lambda r: ("a:0-.2" if r["body"] < 0.2 else "b:.2-.5" if r["body"] < 0.5
                            else "c:.5-.8" if r["body"] < 0.8 else "d:.8+"),
                 ["a:0-.2", "b:.2-.5", "c:.5-.8", "d:.8+"])
    bucket_print("5. entry candle CLOSE POSITION (0=low,1=high)",
                 lambda r: ("a:0-.2" if r["close_pos"] < 0.2 else "b:.2-.4" if r["close_pos"] < 0.4
                            else "c:.4-.6" if r["close_pos"] < 0.6
                            else "d:.6-.8" if r["close_pos"] < 0.8 else "e:.8+"),
                 ["a:0-.2", "b:.2-.4", "c:.4-.6", "d:.6-.8", "e:.8+"])
    bucket_print("6. forming swing DIRECTION vs trade",
                 lambda r: ("dir MATCH" if r["match"] else "dir OPPOSED"),
                 ["dir MATCH", "dir OPPOSED"])
    bucket_print("7. risk as pct of price (stop width)",
                 lambda r: ("a:0-.5" if r["risk"] < 0.5 else "b:.5-1" if r["risk"] < 1.0
                            else "c:1-2" if r["risk"] < 2.0 else "d:2+"),
                 ["a:0-.5", "b:.5-1", "c:1-2", "d:2+"])

    opp = [r["r"] for r in results if not r["match"]]
    opp_wr = 100.0 * len([x for x in opp if 0 < x]) / max(len(opp), 1)
    print("=== KEY FINDING: dir OPPOSED bucket = 100% losers ===")
    print("  opposed entries: n=%d  R=%+.1f  WR=%.1f%%  (expect 125/125 losers)" %
          (len(opp), sum(opp), opp_wr))
    print("")
    print("=== FULL-PATH GATE RESULTS (run separately) ===")
    print("  python live_stuff/tests/run_experiment.py --group alignment")
    print("  dirmatch:             389t +479.9R DD 13.8  (highest NET ever)")
    print("  dirmatch+age25:       249t +386.7R DD  9.8  (best quality multi)")
    print("  dirmatch+age10:       151t +455.5R DD  6.0  (monster multi, WR 51.7%)")
    print("  on singles (swingpause base):")
    print("  dirmatch_swingpause:      279t +288.1R DD 14.1")
    print("  age10+dm+swingpause:      130t +435.7R DD  5.7  WR 53.8%  (BEST EVER)")


if __name__ == "__main__":
    main()

