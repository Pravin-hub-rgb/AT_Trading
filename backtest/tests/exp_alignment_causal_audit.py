"""HOSTILE LOOKAHEAD AUDIT — D3 structural alignment (2026-09-23).

Suspicion: exp_require_dir_match / exp_max_swing_age select the LAST swing
with seg.start_idx <= entry bar from the FULL precomputed chain, without
requiring confirmed_at_idx <= entry. Final dir/start_idx may be unknown live
(FLIP can rewrite both before chop/sustain confirmation).

Checks (no registry pins — this is an audit, not a reproduction):
  A. How many champion entries use an UNCONFIRMED forming swing?
  B. Does dir/age change if we only use confirmed_at_idx <= i?
  C. Re-bucket dir-match and age under causal labels — does 125/125 survive?
  D. Path-true gate: same as patch but require confirmed_at_idx <= i.

Run: python backtest/tests/exp_alignment_causal_audit.py
"""
import sys
import bisect
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from run_experiment import get_data, BP, EXPERIMENTS
import test_experiments_craze as craze


def last_swing_at(swings, i, require_confirmed=False):
    """Replicate the patch selector; optionally only swings known by bar i."""
    gen = None
    gen_si = -1
    for si, s in enumerate(swings):
        seg = s.get("seg") or {}
        gsi = int(seg.get("start_idx", -1))
        if not (0 <= gsi <= i):
            continue
        if require_confirmed:
            conf = int(s.get("confirmed_at_idx", -1))
            if conf < 0 or conf > i:
                continue
        gen = s
        gen_si = si
    return gen, gen_si


def swing_meta(s):
    if s is None:
        return None, -1, False
    seg = s.get("seg") or {}
    gsi = int(seg.get("start_idx", -1))
    gdir = 1 if s.get("dir") == "up" else -1
    conf = int(s.get("confirmed_at_idx", -1))
    return gdir, gsi, conf


def bucket_print(title, rows, key_fn, bins):
    print(f"\n--- {title} ---")
    for b in bins:
        lst = [r for r in rows if key_fn(r) == b]
        if not lst:
            print(f"  {b:<14} n=0")
            continue
        n = len(lst)
        rs = [r["r"] for r in lst]
        wr = 100.0 * sum(1 for x in rs if x > 0) / n
        print(f"  {b:<14} n={n:4d}  R={sum(rs):+8.1f}  avg={sum(rs)/n:+6.3f}  WR={wr:5.1f}%")


def main():
    data = get_data()
    sim = craze.build_module()
    params = {**BP, **EXPERIMENTS["champion_multi_sw10"]["params"]}
    batch = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                fine_ltf=data["fine"], **params)["ltf_trades"]
    print(f"champion trades: {len(batch)}")

    c15 = data["c15"]
    ts15 = [int(c["ts"]) for c in c15]
    sw15 = data["sw15"]

    # Index swings by index for swing_no lookup
    by_index = {int(s.get("swing_index", i)): s for i, s in enumerate(sw15)}

    rows = []
    unconfirmed = 0
    conf_mismatch_dir = 0
    conf_mismatch_age = 0
    no_gen = 0

    for t in batch:
        E = int(t["entry_ts"])
        e_idx = bisect.bisect_left(ts15, E)
        r = float(t["r_multiple"])
        d = 1 if t["dir"] == "long" else -1

        # Non-causal (current patch / autopsy): last start_idx <= i
        raw, raw_si = last_swing_at(sw15, e_idx, require_confirmed=False)
        # Causal: only swings with confirmed_at_idx <= i
        conf, conf_si = last_swing_at(sw15, e_idx, require_confirmed=True)

        if raw is None:
            no_gen += 1
            continue

        raw_dir, raw_start, raw_conf = swing_meta(raw)
        conf_dir, conf_start, conf_conf = swing_meta(conf)

        raw_unconf = raw_conf < 0 or raw_conf > e_idx
        if raw_unconf:
            unconfirmed += 1

        raw_age = e_idx - raw_start if raw_start >= 0 else -1
        conf_age = e_idx - conf_start if conf is not None and conf_start >= 0 else -1

        raw_match = raw_dir == d
        conf_match = (conf is not None and conf_dir == d)

        if raw_match != conf_match:
            conf_mismatch_dir += 1
        if conf is not None and raw_age != conf_age:
            conf_mismatch_age += 1

        # signal swing_no (generating swing from the engine)
        sno = t.get("swing_no")
        sn = by_index.get(int(sno)) if sno is not None else None
        sn_dir, sn_start, sn_conf = swing_meta(sn)
        sn_unconf = sn is not None and (sn_conf < 0 or sn_conf > e_idx)

        rows.append({
            "r": r,
            "d": d,
            "e_idx": e_idx,
            "raw_dir": raw_dir,
            "raw_start": raw_start,
            "raw_conf": raw_conf,
            "raw_age": raw_age,
            "raw_match": raw_match,
            "raw_unconf": raw_unconf,
            "conf_dir": conf_dir if conf is not None else 0,
            "conf_start": conf_start,
            "conf_age": conf_age,
            "conf_match": conf_match,
            "conf_exists": conf is not None,
            "sn_dir": sn_dir if sn is not None else 0,
            "sn_unconf": sn_unconf,
            "sn_match": (sn is not None and sn_dir == d),
        })

    n = len(rows)
    print(f"\n=== A. UNCONFIRMED FORMING SWING (raw selector) ===")
    print(f"  entries: {n}")
    print(f"  raw gen swing NOT confirmed at entry (confirmed_at > i): {unconfirmed} ({100.0*unconfirmed/max(n,1):.1f}%)")
    print(f"  no gen swing: {no_gen}")
    print(f"  signal swing_no unconfirmed at entry: {sum(1 for r in rows if r['sn_unconf'])} "
          f"({100.0*sum(1 for r in rows if r['sn_unconf'])/max(n,1):.1f}%)")

    print(f"\n=== B. RAW vs CAUSAL (confirmed_at_idx <= i) LABEL DRIFT ===")
    print(f"  dir-match label changes: {conf_mismatch_dir} ({100.0*conf_mismatch_dir/max(n,1):.1f}%)")
    print(f"  age value changes:       {conf_mismatch_age} ({100.0*conf_mismatch_age/max(n,1):.1f}%)")
    print(f"  causal gen missing:      {sum(1 for r in rows if not r['conf_exists'])}")

    # Age buckets raw vs causal
    def age_band(a):
        if a < 0:
            return "z:none"
        if a <= 10:
            return "a:0-10"
        if a <= 25:
            return "b:11-25"
        if a <= 50:
            return "c:26-50"
        return "d:51+"

    bucket_print("C1. dir match — RAW (current finding)",
                 rows, lambda r: "MATCH" if r["raw_match"] else "OPPOSED",
                 ["MATCH", "OPPOSED"])
    bucket_print("C2. dir match — CAUSAL (confirmed only)",
                 rows, lambda r: ("MATCH" if r["conf_match"] else
                                  ("OPPOSED" if r["conf_exists"] else "NO_SWING")),
                 ["MATCH", "OPPOSED", "NO_SWING"])
    bucket_print("C3. age — RAW",
                 rows, lambda r: age_band(r["raw_age"]),
                 ["a:0-10", "b:11-25", "c:26-50", "d:51+", "z:none"])
    bucket_print("C4. age — CAUSAL (confirmed only)",
                 rows, lambda r: age_band(r["conf_age"]),
                 ["a:0-10", "b:11-25", "c:26-50", "d:51+", "z:none"])

    # Strict: only trades whose RAW gen was unconfirmed — what does causal say?
    unconf_rows = [r for r in rows if r["raw_unconf"]]
    if unconf_rows:
        bucket_print("C5. subset where RAW used UNCONFIRMED swing — causal dir",
                     unconf_rows,
                     lambda r: ("MATCH" if r["conf_match"] else
                                ("OPPOSED" if r["conf_exists"] else "NO_SWING")),
                     ["MATCH", "OPPOSED", "NO_SWING"])

    # Opposed under raw: how many of those had unconfirmed gen?
    opp = [r for r in rows if not r["raw_match"]]
    opp_unconf = sum(1 for r in opp if r["raw_unconf"])
    print(f"\n=== KEY: raw OPPOSED n={len(opp)}; of those unconfirmed gen={opp_unconf}")
    if opp:
        print(f"  raw opposed R={sum(r['r'] for r in opp):+.1f} "
              f"WR={100.0*sum(1 for r in opp if r['r']>0)/len(opp):.1f}%")
    opp_c = [r for r in rows if r["conf_exists"] and not r["conf_match"]]
    if opp_c:
        print(f"  causal opposed n={len(opp_c)} R={sum(r['r'] for r in opp_c):+.1f} "
              f"WR={100.0*sum(1 for r in opp_c if r['r']>0)/len(opp_c):.1f}%")

    # ---- D) path-true gate: patch selector + confirmed_at <= i ----
    print("\n=== D. PATH-TRUE GATE PREVIEW (confirmed only) on champion trade list ===")
    # Trade-level: drop trades whose causal dir opposes (and age>25 etc)
    # This is NOT full-path (paths reshape) — upper/lower bound only.
    kept_dm = [r for r in rows if r["conf_match"] or not r["conf_exists"]]
    # If no causal swing, current patch uses raw; keep raw_match in that case
    kept_dm = []
    for r in rows:
        if not r["conf_exists"]:
            kept_dm.append(r)  # fall back to raw behavior
        elif r["conf_match"]:
            kept_dm.append(r)
    kept_dm25 = [r for r in kept_dm if r["conf_age"] < 0 or r["conf_age"] <= 25]
    kept_dm10 = [r for r in kept_dm if r["conf_age"] >= 0 and r["conf_age"] <= 10]
    # age10 only when causal age known
    kept_dm10_strict = [r for r in kept_dm if 0 <= r["conf_age"] <= 10]

    base_n = len(rows)
    base_r = sum(r["r"] for r in rows)
    for tag, ks in [
        ("base (champion)", rows),
        ("causal dirmatch (trade-list)", kept_dm),
        ("causal dirmatch+age25", kept_dm25),
        ("causal dirmatch+age10 (incl unknown age kept)", kept_dm10),
        ("causal dirmatch+age10 (age known only)", kept_dm10_strict),
    ]:
        rs = [r["r"] for r in ks]
        wr = 100.0 * sum(1 for x in rs if x > 0) / max(len(rs), 1)
        print(f"  {tag:<42} n={len(ks):>3}  R={sum(rs):+8.1f}  WR={wr:5.1f}%  "
              f"(dR={sum(rs)-base_r:+.1f})")

    print("\nNOTE: trade-list deltas are NOT path-true; full-path retest required.")
    print("done")


if __name__ == "__main__":
    main()
