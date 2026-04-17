@echo off
REM Build the desktop app with PyInstaller in the local .venv
setlocal
if exist .venv\Scripts\activate.bat (
  call .venv\Scripts\activate.bat
) else (
  echo Local virtual environment .venv not found.
  exit /b 1
)
pyinstaller --noconfirm pak_map.spec
endlocal
