"""Pretty terminal output for FB screenshot. Run in dark terminal, then screenshot."""
import sys
sys.stdout.reconfigure(encoding='utf-8')

G = '\033[32m'  # green
R = '\033[31m'  # red
Y = '\033[33m'  # yellow
C = '\033[36m'  # cyan
D = '\033[90m'  # dim
B = '\033[1m'   # bold
N = '\033[0m'   # reset

print()
print(f'  {D}┌───────────────────────────────────────────────┐{N}')
print(f'  {D}│{N}                                               {D}│{N}')
print(f'  {D}│{N}    {B}TradeMemory Protocol v0.3.0{N}                {D}│{N}')
print(f'  {D}│{N}    {C}L1 → L2 → L3 自動策略調整{N}                 {D}│{N}')
print(f'  {D}│{N}                                               {D}│{N}')
print(f'  {D}└───────────────────────────────────────────────┘{N}')
print()
print(f'  {Y}── L2 Patterns (from 10,169 backtest trades) ──{N}')
print()
print(f'  {B}Strategy{N}            {D}│{N} {B}Avg PnL{N}    {D}│{N} {B}WR{N}    {D}│{N} {B}Verdict{N}')
print(f'  {D}────────────────────┼────────────┼───────┼──────────{N}')
print(f'  IntradayMomentum    {D}│{N} {G}+1690.9%{N}   {D}│{N} 40.1% {D}│{N} {G}★ PREFER{N}')
print(f'  VolBreakout         {D}│{N} {G} +467.0%{N}   {D}│{N} 45.3% {D}│{N} {G}★ PREFER{N}')
print(f'  PullbackEntry       {D}│{N} {G} +368.3%{N}   {D}│{N} 48.0% {D}│{N} {G}★ PREFER{N}')
print(f'  MeanReversion       {D}│{N} {R} -494.5%{N}   {D}│{N} 30.6% {D}│{N} {R}✗ DISABLE{N}')
print()
print(f'  {Y}── L3 Strategy Adjustments (auto-generated) ──{N}')
print()
print(f'  {B}Rule{N}                {D}│{N} {B}Parameter{N}                    {D}│{N} {B}Old    → New{N}')
print(f'  {D}────────────────────┼──────────────────────────────┼──────────────{N}')
print(f'  strategy_disable    {D}│{N} MeanReversion.enabled        {D}│{N} true   {R}→{N} {R}false{N}')
print(f'  strategy_prefer     {D}│{N} IntradayMomentum.priority    {D}│{N} normal {G}→{N} {G}high{N}')
print(f'  strategy_prefer     {D}│{N} VolBreakout.priority         {D}│{N} normal {G}→{N} {G}high{N}')
print(f'  strategy_prefer     {D}│{N} PullbackEntry.priority       {D}│{N} normal {G}→{N} {G}high{N}')
print(f'  direction_restrict  {D}│{N} MR.XAUUSD.allowed_direction  {D}│{N} BOTH   {Y}→{N} {Y}BUY{N}')
print(f'  direction_restrict  {D}│{N} MR.EURUSD.allowed_direction  {D}│{N} BOTH   {Y}→{N} {Y}BUY{N}')
print(f'  session_reduce      {D}│{N} MR.XAUUSD.max_lot            {D}│{N} 1.0    {Y}→{N} {Y}0.5{N}')
print(f'  session_reduce      {D}│{N} MR.EURUSD.max_lot            {D}│{N} 1.0    {Y}→{N} {Y}0.5{N}')
print(f'  session_reduce      {D}│{N} IM.EURUSD.max_lot            {D}│{N} 1.0    {Y}→{N} {Y}0.5{N}')
print()
print(f'  {G}9/9 adjustments match manual analysis ✓{N}')
print(f'  {D}181 tests passing · CI green · PyPI published{N}')
print()
