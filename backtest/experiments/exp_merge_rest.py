"""Join the five-book and eight-book halves of the T1-T4 battery.

The thirteen multi books are split across two passes because T1 is a two-axis
grid and serialising all thirteen in one process runs for hours. The halves land
in separate files so the second pass cannot silently replace the first - which
it did the first time this was attempted, leaving a five-book file under a
thirteen-book label.

This script refuses to merge a pair that is not five plus eight. A merge that
produces thirteen books when it was handed twenty, or eight when it was handed
five, is a harness bug and should stop the run rather than produce a confident
number.
"""

import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

ALL5 = [
    "fsent_champ_long_mcloff_htf15",
    "fsent_champ_long_htf15_tskip6",
    "fsent_champ_long_htffs",
    "fsent_champ_long_htf15_htffs",
    "fsent_champ_long_htfesmcl4",
]
REST8 = [
    "fsent_sig_multi_acc",
    "fsent_champ_long_htf15",
    "fsent_champ_long_mcloff",
    "fsent_champ_long_causalfloor",
    "fsent_champ_long_mode_chop",
    "fsent_champ_long_biasmom05",
    "fsent_sig_multi_htffs",
    "fsent_sig_multi",
]


def main():
    ok = True
    for which in ("t1", "t2", "t3", "t4"):
        pa = os.path.join(HERE, "four_techniques_%s.json" % which)
        pb = os.path.join(HERE, "four_techniques_%s_rest.json" % which)
        if not (os.path.exists(pa) and os.path.exists(pb)):
            print("%s : MISSING half, skipped" % which)
            ok = False
            continue
        a = json.load(io.open(pa, encoding="utf-8")).get(which, {})
        b = json.load(io.open(pb, encoding="utf-8")).get(which, {})

        if sorted(a.keys()) != sorted(ALL5):
            print("%s : first half is not the five books -> %s" % (which, sorted(a.keys())))
            ok = False
        if sorted(b.keys()) != sorted(REST8):
            print("%s : second half is not the eight books -> %s" % (which, sorted(b.keys())))
            ok = False

        merged = dict(a)
        overlap = set(a) & set(b)
        if overlap:
            print("%s : %d books in BOTH halves -> refusing" % (which, len(overlap)))
            ok = False
        merged.update(b)

        if len(merged) != 13:
            print("%s : merged to %d books, expected 13" % (which, len(merged)))
            ok = False

        out = os.path.join(HERE, "four_techniques_all13_%s.json" % which)
        with io.open(out, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({which: merged}, indent=1))
        print("%s : merged %d + %d = %d books -> %s"
              % (which, len(a), len(b), len(merged), os.path.basename(out)))

    print("\n%s" % ("all four merged cleanly" if ok else "PROBLEMS ABOVE - do not trust these files"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())