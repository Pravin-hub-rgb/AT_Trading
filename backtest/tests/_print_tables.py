import json
from pathlib import Path

base = Path(__file__).resolve().parent

sd = json.loads((base / "_skip_decisive_ship_results.json").read_text(encoding="utf-8"))
print("=== SKIP_DECISIVE COMPARISON ===")
for scope in ("is", "oos"):
    print(f" {scope.upper()}")
    for k, arms in sd[scope]["configs"].items():
        for a, m in arms.items():
            print(
                f"   {k[:22]:22} {a:16} n={m['n']:3d} "
                f"net={m['net']:+7.1f} d={m['dNet']:+7.1f} "
                f"dyr={m['dNet_yr']:+6.1f} wr={m['wr']:5.1f} "
                f"dd={m['dd_net']:+6.1f} ship={m.get('ship','?')}"
            )

sz = json.loads((base / "_cohort_sizing_results_is.json").read_text(encoding="utf-8"))
print("=== COHORT SIZING ===")
for scope in ("is", "oos"):
    print(f" {scope.upper()}")
    for k, maps in sz[scope]["configs"].items():
        for name, s in maps.items():
            print(
                f"   {k[:22]:22} {name:14} base={s['baseline_net']:+7.1f} "
                f"w={s['weighted_net']:+7.1f} d={s['delta_net']:+7.1f} "
                f"dyr={s['dNet_yr']:+6.1f} id={s['identity_ok']}"
            )

tr = json.loads((base / "_trail_slower_results_is.json").read_text(encoding="utf-8"))
keep = {"baseline", "delay_r_0.5", "delay_r_1.0", "delay_r_1.5", "delay_r_2.0",
        "skip_n_1", "skip_n_2", "skip_n_3", "half", "half+delay1"}
print("=== TRAIL SLOWER/WIDER ===")
for scope in ("is", "oos"):
    print(f" {scope.upper()}")
    for k, arms in tr[scope]["configs"].items():
        for a, m in arms.items():
            if a in keep:
                print(
                    f"   {k[:22]:22} {a:14} n={m['n']:3d} "
                    f"net={m['net']:+7.1f} d={m['dNet']:+7.1f} "
                    f"dyr={m['dNet_yr']:+6.1f} wr={m['wr']:5.1f} "
                    f"dd={m['dd_net']:+6.1f} id={m.get('identity_ok','?')}"
                )
