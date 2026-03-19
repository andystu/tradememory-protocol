@echo off
REM Daily Reflection - Run at 23:55 every day
cd /d C:\Users\johns\projects\tradememory-protocol
python scripts/daily_reflection.py >> logs\reflection.log 2>&1
