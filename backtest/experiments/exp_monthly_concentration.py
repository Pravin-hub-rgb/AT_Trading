"""How much of each book's total actually sits in its best few months.

The owner looked at the monthly spread in the UI and said January 2023, October
and December look like they are carrying everything, and that the other years
look normal. That is the kind of observation that is either obviously true from
the chart or completely an illusion of the y-axis, so it is measured.

For each book: every month's net, sorted, so the top three months can be compared
against the whole. A book whose total rests on three months out of forty-four is
a different animal from one that earns steadily, and the two deserve different
sizing decisions even when both print a large total.

Output: monthly_concentration.md
"""
from __future__ import annotations

import io
import json
import datetime as dt
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tests"))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parents[1] / "backend"))

from experiment_registry import EXPERIMENTS, BP, ENGINE_DEFAULTS  # noqa: E402
from run_experiment import net_r, get_swings, get_data  # noqa: E402
from exp_tf_family import build_family_module  # noqa: E402

MD = HERE / "monthly_concentration.md"
BOOKS = ["fsent_champ_long_htffs", "fsent_champ_long_mcloff_htf15",
         "fsent_champ_long_htfesmcl4", "fsent_champ_long"]


def main() -> int:
    print("loading data ...", flush=True)
    data = get_data()
    sim = build_family_module()
    L = ["# Where the money actually sits, month by month", "",
         "IS era only (2023-01..2026-09). Net R after costs.", ""]
    blocks = []
    for name in BOOKS:
        cfg = EXPERIMENTS[name]
        params = {**(BP if cfg.get("use_bp", True) else ENGINE_DEFAULTS),
                  **(cfg.get("params") or {})}
        o = sim(data["c1h"], get_swings(data, cfg.get("swing") or "sw10"),
                data["c15"], data["sw15"], fine_ltf=data["fine"], **params)
        tr = [t for t in (o["ltf_trades"] if isinstance(o, dict) else o)
              if t.get("outcome") != "open"]
        tr.sort(key=lambda t: int(t["entry_ts"]))
        months = {}
        for t in tr:
            # Real calendar month. Bucketing by a fixed 2592000-second divisor
            # is not a month - it drifts against the calendar and produced
            # nonsense dates the first time this was run.
            key = int(t["entry_ts"])
            key = dt.datetime.utcfromtimestamp(key).strftime("%Y-%m")
            months.setdefault(key, []).append(net_r([t]))
        per = sorted(((k, sum(v)) for k, v in months.items()), key=lambda x: -x[1])
        total = sum(v for _k, v in per)
        blocks.append((name, per, total))
        print("%-34s months=%d total=%+.2f  top1=%.1f%% top3=%.1f%%"
              % (name, len(per), total,
                 100.0 * per[0][1] / total if total else 0,
                 100.0 * sum(v for _k, v in per[:3]) / total if total else 0), flush=True)

    L.append("## Concentration summary")
    L.append("")
    L.append("| book | months | total net R | best month | best 3 months |")
    L.append("|---|---:|---:|---:|---:|")
    for name, per, total in blocks:
        t1 = 100.0 * per[0][1] / total if total else 0
        t3 = 100.0 * sum(v for _k, v in per[:3]) / total if total else 0
        L.append("| `%s` | %d | %+.1f | %.1f%% | %.1f%% |" % (name, len(per), total, t1, t3))
    L.append("")
    for name, per, total in blocks:
        L.append("## `%s` - months sorted by net" % name)
        L.append("")
        L.append("| rank | month | net R |")
        L.append("|---:|---|---:|")
        for i, (k, v) in enumerate(per, 1):
            L.append("| %d | %s | %+.2f |" % (i, k, v))
        L.append("")
    io.open(MD, "w", encoding="utf-8").write("\n".join(L))
    print("\nwrote %s" % MD.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())