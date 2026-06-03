@echo off
cd /d "%~dp0"
python -m pip install -r requirements.txt
python image2_gui.py
pause
