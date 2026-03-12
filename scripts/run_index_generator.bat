@echo off
cd /d C:\Users\johns\projects\tradememory-protocol
call .venv\Scripts\activate.bat
python scripts\generate_index.py
