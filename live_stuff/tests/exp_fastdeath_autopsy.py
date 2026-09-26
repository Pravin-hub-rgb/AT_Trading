"""Phase 1: fast-death PRE-ENTRY autopsy.

Goal: find causal entry-time features that separate trades dying in <12 bars
from the rest. Ceiling (post-filter skip <12 bars) = +100R on anchor per
LOSS_AUTOPSY.md §LA3 — need a pre-entry proxy, not the post-filter itself.

Features (all known at entry bar close, no lookahead):
  - regime (flip/b2/decisive use)
  - break_kind (B2/FLIP/DEC)
  - hour-of-day UTC, weekday
  - chop15 at entry, atr% at entry
  - 15m rvol (trailing 96), volume percentile
  - swing age of generating 15m swing
  - running mag % since swing pivot
  - entry risk as % of price
  - leg pullback R (same as A4 gate calc)
  - window age hours (wage)
  - ext_r at entry (how extended from HTF anchor)

Bucket: fast death (bars_held < 12) vs slow (>= 12).
Print n, R, avgR, WR, and delta vs overall for each feature bin.

Run: python live_stuff/tests/exp_fastdeath_autopsy.py
"""
import sys
import time
import bisect
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

from run_experiment import get_data, BP, net_r
import test_experiments_craze as craze
from experiment_registry import EXPERIMENTS


def bucket_table(name, rows, key_fn, bins):
    print(f"\n  -- {name} --", flush=True)
    print(f"  {'bin':<16} {'n':>4} {'fast':>5} {'fast%':>6} {'R_fast':>8} "
          f"{'R_slow':>8} {'avgR_f':>7} {'avgR_s':>7} {'delta':>7}", flush=True)
    for b in bins:
        sub = [r for r in rows if key_fn(r) == b]
        if not sub:
            print(f"  {b:<16} n=0", flush=True)
            continue
        fast = [r for r in sub if r["fast"]]
        slow = [r for r in sub if not r["fast"]]
        rf = sum(r["r"] for r in fast)
        rs = sum(r["r"] for r in slow)
        arf = rf / len(fast) if fast else 0.0
        ars = rs / len(slow) if slow else 0.0
        # delta = how much more/less profitable fast deaths are here vs baseline
        print(f"  {b:<16} {len(sub):4d} {len(fast):5d} "
              f"{100.0*len(fast)/len(sub):5.1f}% {rf:+8.1f} {rs:+8.1f} "
              f"{arf:+7.3f} {ars:+7.3f} {arf-ars:+7.3f}", flush=True)


def main():
    t0 = time.time()
    print("=" * 100)
    print("  FAST-DEATH PRE-ENTRY AUTOPSY — separate bars_held<12 from rest")
    print("=" * 100)

    data = get_data()
    sim = craze.build_module()
    c15, sw15, c1h, sw10 = data["c15"], data["sw15"], data["c1h"], data["sw10"]
    fine = data["fine"]

    # Champion multi (production) — the trade list we care about
    params = {**BP, **EXPERIMENTS["champion_multi_sw10"]["params"]}
    params.setdefault("exp_partial_r", 0.0)
    batch = sim(c1h, sw10, c15, sw15, fine_ltf=fine, **params)["ltf_trades"]
    print(f"champion_multi_sw10: {len(batch)} trades", flush=True)

    ts15 = [int(c["ts"]) for c in c15]
    cl15 = [float(c["close"]) for c in c15]
    hi15 = [float(c["high"]) for c in c15]
    lo15 = [float(c["low"]) for c in c15]
    # volume rvol trailing
    vol15 = [float(c.get("volume") or 0.0) for c in c15]
    rvol = [1.0] * len(c15)
    for i in range(1, len(c15)):
        w = vol15[max(0, i - 96):i]
        avg = sum(w) / len(w) if w else 0.0
        rvol[i] = vol15[i] / avg if avg > 0 else 1.0

    # chop15 / atr% — recompute simply (chop uses rolling; atr from range)
    # Use atr% = (rolling 14 high-low avg) / close * 100
    atrp = [0.0] * len(c15)
    for i in range(14, len(c15)):
        rng = sum(hi15[i - 13:i + 1][j] - lo15[i - 13:i + 1][j] for j in range(14)) / 14
        atrp[i] = 100.0 * rng / cl15[i] if cl15[i] > 0 else 0.0

    # swing age: find generating 15m swing by start_idx
    sw15_list = sw15

    # HTF for wage/ext/leg
    ts1h = [int(c["ts"]) for c in c1h]
    hi1h = [float(c["high"]) for c in c1h]
    lo1h = [float(c["low"]) for c in c1h]

    # Build parent intervals from this run's htf trades (causal join)
    def make_ivs(htf_list):
        iv = [(int(t["entry_ts"]), int(t["exit_ts"]),
               1 if t["dir"] == "long" else -1,
               float(t["entry_price"]), float(t["sl"]))
              for t in htf_list if t.get("outcome") != "open"]
        iv.sort()
        return iv, [w[0] for w in iv]

    # We need htf trades from the same sim call — re-run capturing full out
    full_out = sim(c1h, sw10, c15, sw15, fine_ltf=fine, **params)
    htf_flip, htf_b2 = full_out["htf_trades"], full_out.get("htf_trades_b2", [])
    ivf, sf = make_ivs(htf_flip)
    ivb, sb = make_ivs(htf_b2)

    rows = []
    for t in batch:
        E = int(t["entry_ts"])
        e_idx = bisect.bisect_left(ts15, E)
        if e_idx < 0 or e_idx >= len(ts15):
            continue
        entry = float(t["entry_price"])
        d = 1 if t["dir"] == "long" else -1
        r = float(t["r_multiple"])
        bars = int(t.get("bars_held") or 0)
        fast = bars < 12
        use = t.get("htf_regime", "flip")

        # wage: age of parent window at entry
        iv, st = (ivf, sf) if use == "flip" else (ivb, sb)
        j = bisect.bisect_right(st, E) - 1
        wage_h = None
        ext_r = None
        pb_r = None
        if 0 <= j < len(iv) and iv[j][0] < E <= iv[j][1]:
            anc0 = iv[j][0]
            wage_h = (E - anc0) / 3600.0
            pe, psl = iv[j][3], iv[j][4]
            hr = abs(pe - psl)
            if hr > 0:
                ext_r = (entry - pe) * iv[j][2] / hr
                # leg anchor: walk back same dir
                _j = j
                while _j > 0 and iv[_j - 1][2] == iv[j][2]:
                    _j -= 1
                anc = iv[_j][0]
                li = bisect.bisect_right(ts1h, anc)
                hi_i = bisect.bisect_right(ts1h, E)
                if hi_i > li:
                    if d == 1:
                        seg_h = max(hi1h[li:hi_i])
                        pb_r = (seg_h - entry) / hr
                    else:
                        seg_l = min(lo1h[li:hi_i])
                        pb_r = (entry - seg_l) / hr

        # swing age of generating 15m swing
        gen_age = None
        for s in sw15_list:
            seg = s.get("seg") or {}
            si = int(seg.get("start_idx", -1))
            if 0 <= si <= e_idx:
                gen_age = e_idx - si  # not exact but close; pivot at start
                # use confirmed pivot if available
                if "pivot_idx" in seg:
                    gen_age = e_idx - int(seg["pivot_idx"])

        hour = (E % 86400) // 3600
        weekday = (E // 86400) % 7  # 0=Thu in unix? actually epoch was Thu
        # unix day 0 = Thursday; we'll label generically

        # running mag
        if d == 1:
            ext_since = min(lo15[max(0, e_idx - 48):e_idx + 1])
            mag = (entry - ext_since) / entry * 100 if entry else 0
        else:
            ext_since = max(hi15[max(0, e_idx - 48):e_idx + 1])
            mag = (ext_since - entry) / entry * 100 if entry else 0

        risk_pct = abs(entry - float(t["sl"])) / entry * 100 if entry else 0

        rows.append({
            "r": r, "fast": fast, "bars": bars,
            "use": use, "kind": t.get("break_kind", "?"),
            "hour": hour, "wd": weekday,
            "chop15": 50.0,  # placeholder — not loaded; skip chop for now
            "atrp": atrp[e_idx] if e_idx < len(atrp) else 0,
            "rvol": rvol[e_idx] if e_idx < len(rvol) else 1.0,
            "age": gen_age,
            "mag": mag, "risk": risk_pct,
            "wage_h": wage_h, "ext_r": ext_r, "pb_r": pb_r,
            "kind_dir": (t.get("break_kind", ""), d),
        })

    n = len(rows)
    nfast = sum(1 for r in rows if r["fast"])
    rfast = sum(r["r"] for r in rows if r["fast"])
    rslow = sum(r["r"] for r in rows if not r["fast"])
    print(f"\n  OVERALL: n={n} fast(<12)={nfast} ({100.0*nfast/n:.1f}%) "
          f"R_fast={rfast:+.1f} R_slow={rslow:+.1f} "
          f"avgR_f={rfast/max(nfast,1):+.3f} avgR_s={rslow/max(n-nfast,1):+.3f}",
          flush=True)

    bucket_table("1. regime use", rows, lambda r: r["use"],
                 ["flip", "b2", "decisive"])
    bucket_table("2. break kind", rows, lambda r: r["kind"],
                 sorted(set(r["kind"] for r in rows)))
    bucket_table("3. hour UTC", rows,
                 lambda r: "a:0-6" if r["hour"] < 6 else "b:6-12" if r["hour"] < 12
                 else "c:12-18" if r["hour"] < 18 else "d:18-24",
                 ["a:0-6", "b:6-12", "c:12-18", "d:18-24"])
    bucket_table("4. atr% at entry", rows,
                 lambda r: "a:<0.3" if r["atrp"] < 0.3 else "b:0.3-0.5"
                 if r["atrp"] < 0.5 else "c:0.5-0.8" if r["atrp"] < 0.8 else "d:0.8+",
                 ["a:<0.3", "b:0.3-0.5", "c:0.5-0.8", "d:0.8+"])
    bucket_table("5. rvol15 at entry", rows,
                 lambda r: "a:<0.5" if r["rvol"] < 0.5 else "b:0.5-1.0"
                 if r["rvol"] < 1.0 else "c:1.0-2.0" if r["rvol"] < 2.0 else "d:2.0+",
                 ["a:<0.5", "b:0.5-1.0", "c:1.0-2.0", "d:2.0+"])
    bucket_table("6. swing age bars", rows,
                 lambda r: ("a:0-10" if (r["age"] or 0) <= 10 else
                            "b:11-25" if (r["age"] or 0) <= 25 else
                            "c:26-50" if (r["age"] or 0) <= 50 else "d:51+")
                 if r["age"] is not None else "z:none",
                 ["a:0-10", "b:11-25", "c:26-50", "d:51+", "z:none"])
    bucket_table("7. running mag %", rows,
                 lambda r: ("a:<0.5" if r["mag"] < 0.5 else "b:0.5-1"
                 if r["mag"] < 1 else "c:1-2" if r["mag"] < 2 else "d:2+"),
                 ["a:<0.5", "b:0.5-1", "c:1-2", "d:2+"])
    bucket_table("8. risk % of price", rows,
                 lambda r: ("a:<0.5" if r["risk"] < 0.5 else "b:0.5-1"
                 if r["risk"] < 1 else "c:1-2" if r["risk"] < 2 else "d:2+"),
                 ["a:<0.5", "b:0.5-1", "c:1-2", "d:2+"])
    bucket_table("9. wage hours", rows,
                 lambda r: ("a:<6" if (r["wage_h"] or 0) < 6 else
                            "b:6-12" if (r["wage_h"] or 0) < 12 else
                            "c:12-24" if (r["wage_h"] or 0) < 24 else
                            "d:24-48" if (r["wage_h"] or 0) < 48 else "e:48+")
                 if r["wage_h"] is not None else "z:none",
                 ["a:<6", "b:6-12", "c:12-24", "d:24-48", "e:48+", "z:none"])
    bucket_table("10. ext_r at entry", rows,
                 lambda r: ("a:<0" if (r["ext_r"] or 0) < 0 else
                            "b:0-0.5" if (r["ext_r"] or 0) < 0.5 else
                            "c:0.5-1" if (r["ext_r"] or 0) < 1 else
                            "d:1-1.5" if (r["ext_r"] or 0) < 1.5 else "e:1.5+")
                 if r["ext_r"] is not None else "z:none",
                 ["a:<0", "b:0-0.5", "c:0.5-1", "d:1-1.5", "e:1.5+", "z:none"])
    bucket_table("11. pullback R off leg", rows,
                 lambda r: ("a:<0.5" if (r["pb_r"] or 0) < 0.5 else
                            "b:0.5-1.5" if (r["pb_r"] or 0) < 1.5 else
                            "c:1.5-3" if (r["pb_r"] or 0) < 3 else "d:3+")
                 if r["pb_r"] is not None else "z:none",
                 ["a:<0.5", "b:0.5-1.5", "c:1.5-3", "d:3+", "z:none"])

    # Combined: high wage + mid ext (the known death zone candidates)
    print("\n  -- COMBO: wage>=12 AND ext>=0.5 --", flush=True)
    combo = [r for r in rows if r["wage_h"] is not None and r["wage_h"] >= 12
             and r["ext_r"] is not None and r["ext_r"] >= 0.5]
    if combo:
        cf = [r for r in combo if r["fast"]]
        cs = [r for r in combo if not r["fast"]]
        print(f"    n={len(combo)} fast={len(cf)} "
              f"R_f={sum(r['r'] for r in cf):+.1f} "
              f"R_s={sum(r['r'] for r in cs):+.1f}", flush=True)

    print(f"\n(done in {time.time()-t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
