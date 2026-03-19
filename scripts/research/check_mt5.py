"""Quick MT5 status check."""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import MetaTrader5 as mt5
from datetime import datetime, timedelta, timezone

path = r'C:\Users\johns\AppData\Roaming\MetaTrader 5\terminal64.exe'
if not mt5.initialize(path=path):
    print(f'MT5 init failed: {mt5.last_error()}')
    sys.exit(1)

info = mt5.account_info()
print(f'Account: {info.login}')
print(f'Balance: ${info.balance:,.2f}')
print(f'Equity: ${info.equity:,.2f}')
print(f'Profit: ${info.profit:,.2f}')
print(f'Open positions: {mt5.positions_total()}')

# Show open positions
positions = mt5.positions_get()
if positions:
    for p in positions:
        print(f'  {p.symbol} {"BUY" if p.type==0 else "SELL"} {p.volume} lots | magic={p.magic} | profit=${p.profit:.2f}')

# Recent deals
now = datetime.now(timezone.utc)
deals = mt5.history_deals_get(now - timedelta(days=3), now)
if deals:
    print(f'\nDeals last 3 days: {len(deals)}')
    for d in list(deals)[-8:]:
        t = datetime.fromtimestamp(d.time, tz=timezone.utc)
        dtype = "BUY" if d.type == 0 else "SELL" if d.type == 1 else f"type={d.type}"
        print(f'  {t.strftime("%m/%d %H:%M")} | magic={d.magic} | {dtype} | {d.volume} lots | ${d.profit:.2f}')
else:
    print('\nNo deals in last 3 days')

mt5.shutdown()
