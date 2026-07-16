@echo off
chcp 65001 >nul
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -m streamlit run app.py
  goto :check
)
where py >nul 2>&1
if %errorlevel%==0 (
  py -m streamlit run app.py
) else (
  python -m streamlit run app.py
)
:check
if errorlevel 1 (
  echo.
  echo 起動できませんでした。README.md の初回セットアップを確認してください。
  pause
)
