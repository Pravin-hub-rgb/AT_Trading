#!/usr/bin/env python
p = r'live_stuff/live_loop.py'
with open(p, 'r') as f:
    lines = f.readlines()

# Fix lines 1694-1703 (1-indexed) = indices 1693-1702
fixed_block = [
    '                    try:\n',
    '                        from persistence.trade_store import update_trade_qty\n',
    '                        update_trade_qty(self.db, trade_id, actual_qty)\n',
    '                    except Exception:\n',
    '                        pass\n',
    '                    if self._tg:\n',
    '                        self._tg.trade_entry(direction, entry_price, sl_price, qty_str,\n',
    '                                             risk_inr, risk_usdt, rate)\n',
    '                    return\n',
    '                if state == "flat":\n',
]

# Replace lines 1694-1703 (indices 1693-1702)
lines[1693:1703] = fixed_block

with open(p, 'w') as f:
    f.writelines(lines)

print('FIXED - indentation corrected')
# Verify
with open(p, 'r') as f:
    vlines = f.readlines()
for i in range(1693, 1704):
    print(f'{i+1}: {vlines[i].rstrip()}')