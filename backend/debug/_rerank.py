"""Reorder + relabel btcMaster.ts presets by stream-mode NET R ranking."""
import io
import re

p = "frontend/src/lib/btcMaster.ts"
s = io.open(p, encoding="utf-8").read()

# new ranks by key (from debug/_summary_stream.json, own-TF NET R)
RANK = {
    "decisive50": 1, "flip50": 2, "flip30": 3, "sniper": 4,
    "flip1h20": 5, "decisive1h30": 6, "flip1h20t": 7, "flip_bias": 8,
    "flip1h30": 9, "baseline": 10, "flip_quality": 11, "trail_max_r": 12,
}
NET = {
    "decisive50": "+128.4", "flip50": "+113.9", "flip30": "+94.9",
    "sniper": "+80.3", "flip1h20": "+62.2", "decisive1h30": "+61.1",
    "flip1h20t": "+37.3", "flip_bias": "+21.9", "flip1h30": "+11.1",
    "baseline": "-3.7", "flip_quality": "-118.6", "trail_max_r": "-151.4",
}

# extract preset blocks
blocks: dict[str, str] = {}
order = []
for m in re.finditer(r'  \{\n    value: "([a-z0-9_]+)",', s):
    key = m.group(1)
    start = m.start() - 2  # include the "  {" line
    # find the matching end: next "  },\n" at same level
    end = s.find("  },\n", m.end())
    if end < 0:
        end = len(s)
    else:
        end += len("  },\n")
    blocks[key] = s[start:end]
    order.append(key)

# build new ordered array with updated labels
new_blocks = []
for key, rank in sorted(RANK.items(), key=lambda x: x[1]):
    b = blocks[key]
    # update label: replace "#N " prefix with new rank, ensure TF is present
    old_label = re.search(r'label: "([^"]+)"', b).group(1)
    tf = re.search(r'\u00b7 (\S+)$', old_label)
    tf_str = tf.group(1) if tf else ""
    # strip old rank prefix
    base_label = re.sub(r'^#\d+\s+', '', old_label)
    if not base_label.endswith(tf_str):
        base_label += f" \u00b7 {tf_str}"
    new_label = f"#{rank} {base_label}"
    b = re.sub(r'label: "[^"]+"', f'label: "{new_label}"', b, count=1)
    # update hint: prepend NET R
    b = re.sub(
        r'(hint: "[^"]+?)(?:\. \+[\d.]+R NET[^\"]*)?"',
        lambda m, k=key: m.group(1) + f". NET {NET[k]}R (stream, 1m fills).",
        b, count=1,
    )
    new_blocks.append(b)

new_array = "export const BTC_MASTER_MODES: BtcMasterMode[] = [\n" + "\n".join(new_blocks) + "\n];\n\n"

# rebuild the file: header + interface + new array + default
hdr_end = s.find("export const BTC_MASTER_MODES")
header = s[:hdr_end]
default_m = re.search(r'export const BTC_MASTER_DEFAULT = "[^"]+";', s)
default = default_m.group(0) if default_m else 'export const BTC_MASTER_DEFAULT = "decisive50";'

new_file = header + new_array + "\n" + default + "\n"
io.open(p, "w", encoding="utf-8", newline="\n").write(new_file)

# report
final_labels = re.findall(r'label: "([^"]+)"', new_file)
for lbl in final_labels:
    print(" ", lbl)
print("DONE —", len(final_labels), "presets reordered")
