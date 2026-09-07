import json
from pathlib import Path

# Find latest per-bias files
import glob
per_bias_files = list(Path("backend").glob("sweep_all_*_20260905_212247.json"))
per_bias_files = [f for f in per_bias_files if "best" not in f.name]
print("per-bias files:", [f.name for f in per_bias_files])

best_per_bias = {}
for f in per_bias_files:
    data = json.loads(f.read_text())
    best = data[0]
    bias = best["bias_mode"]
    best_per_bias[bias] = best
    print(bias, best["total_r"], best["cfg"])

# Also read overall best
best_all_path = Path("backend/sweep_all_best_20260905_212247.json")
if best_all_path.exists():
    data = json.loads(best_all_path.read_text())
    print("\nOverall top 3:")
    for r in data[:3]:
        print(r["bias_mode"], r["total_r"], r["cfg"])

# Generate new biasPresets.ts
out_lines = []
out_lines.append("// Auto-generated per-bias best presets - do not edit manually, run sweep_all_bias.py")
out_lines.append("import type { BacktestParams } from \"./api\";")
out_lines.append("export const BIAS_PRESETS: Record<string, Partial<BacktestParams>> = {")
for bias, best in sorted(best_per_bias.items()):
    cfg = best["cfg"]
    gap_pct_str = f"{cfg['gap_pct']*100:.2f}".rstrip("0").rstrip(".")
    out_lines.append(f"  \"{bias}\": {{")
    out_lines.append(f"    sl_mode: \"{cfg['sl_mode']}\",")
    out_lines.append(f"    execution: \"1min\",")
    out_lines.append(f"    rr_target: {cfg['rr_target']},")
    out_lines.append(f"    min_sl_pts: {cfg['min_sl_pts']},")
    out_lines.append(f"    breakeven_r: {cfg['breakeven_r']},")
    out_lines.append(f"    gap_pct: \"{gap_pct_str}\",")
    out_lines.append(f"    ft_fail_enabled: {str(cfg['ft_fail_enabled']).lower()},")
    out_lines.append(f"    max_entries: {cfg['max_entries']},")
    out_lines.append(f"    entry_cutoff: \"{cfg['entry_cutoff']}\",")
    out_lines.append(f"    second_trade_after: \"{cfg['second_trade_after']}\",")
    out_lines.append(f"    swing_traverse: true,")
    out_lines.append(f"    need_opp_swing: true,")
    out_lines.append(f"    trailing: \"off\",")
    out_lines.append(f"    entry_method: \"pivot_break\",")
    out_lines.append(f"  }}, // R{best['total_r']:+.2f} WR{best['win_rate']}% PF{best['pf']} trades{best['trades']}")
out_lines.append("};")
out_lines.append("")
out_lines.append("export const BIAS_PRESETS_META: Record<string, {total_R:number, win_rate:number, pf:number, trades:number}> = {")
for bias, best in sorted(best_per_bias.items()):
    out_lines.append(f"  \"{bias}\": {{ total_R: {best['total_r']}, win_rate: {best['win_rate']}, pf: {best['pf']}, trades: {best['trades']} }},")
out_lines.append("};")

out_path = Path("frontend/src/lib/biasPresets.ts")
out_path.write_text("\n".join(out_lines))
print(f"\nWrote {out_path} with {len(best_per_bias)} biases")
print(out_path.read_text()[:4000])
