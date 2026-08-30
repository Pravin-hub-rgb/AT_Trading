import re

with open('src/intraday.py', 'r') as f:
    content = f.read()

# 1. Add ft_fail_enabled to DEFAULT_CFG
old = '"sl_pivot_buffer": 1.0,  # buffer in absolute points for prev_pivot SL mode\n}'
new = '"sl_pivot_buffer": 1.0,  # buffer in absolute points for prev_pivot SL mode\n    "ft_fail_enabled": True,  # early exit when close goes beyond dom_level within 2 bars (S5:98)\n}'
content = content.replace(old, new)

# 2. Update ft_fail checks to use ft_fail_enabled
# We need to add ft_fail_enabled check to all 4 ft_fail conditions
# The trade dict has cfg available via closure, so we check cfg["ft_fail_enabled"]

# Pattern for 1m mode long (line ~704)
content = content.replace(
    'if not t["validated"] and i <= t["validate_until"] and cur["close"] < t["dom_low"]:\n                            _close_trade(t, i, cur["close"], "ft_fail")',
    'if cfg["ft_fail_enabled"] and not t["validated"] and i <= t["validate_until"] and cur["close"] < t["dom_low"]:\n                            _close_trade(t, i, cur["close"], "ft_fail")'
)

# Pattern for 1m mode short (line ~708)
content = content.replace(
    'if not t["validated"] and i <= t["validate_until"] and cur["close"] > t["dom_high"]:\n                            _close_trade(t, i, cur["close"], "ft_fail")',
    'if cfg["ft_fail_enabled"] and not t["validated"] and i <= t["validate_until"] and cur["close"] > t["dom_high"]:\n                            _close_trade(t, i, cur["close"], "ft_fail")'
)

# Pattern for 5min mode long (line ~719)
content = content.replace(
    'elif not t["validated"] and i <= t["validate_until"] and cur["close"] < t["dom_low"]:\n                        # follow-through never arrived',
    'elif cfg["ft_fail_enabled"] and not t["validated"] and i <= t["validate_until"] and cur["close"] < t["dom_low"]:\n                        # follow-through never arrived'
)

# Pattern for 5min mode short (line ~730)
content = content.replace(
    'elif not t["validated"] and i <= t["validate_until"] and cur["close"] > t["dom_high"]:\n                        _close_trade(t, i, cur["close"], "ft_fail")',
    'elif cfg["ft_fail_enabled"] and not t["validated"] and i <= t["validate_until"] and cur["close"] > t["dom_high"]:\n                        _close_trade(t, i, cur["close"], "ft_fail")'
)

with open('src/intraday.py', 'w') as f:
    f.write(content)

print("Patched successfully")

# Verify
with open('src/intraday.py', 'r') as f:
    c = f.read()
if 'ft_fail_enabled' in c:
    print("ft_fail_enabled found in file")
else:
    print("ERROR: ft_fail_enabled NOT found!")
