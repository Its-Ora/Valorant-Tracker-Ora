@echo off
title Build - Tracker By Eaurah (PyInstaller)
cd /d "%~dp0"
echo.
echo  === Compilation du Tracker By Eaurah (PyInstaller) ===
echo.
echo  [1/2] Installation des dependances...
python -m pip install --upgrade pyinstaller requests
echo.
echo  [2/2] Compilation...
python -m PyInstaller --noconfirm --clean --onedir --console --name "TrackerByEaurah" --add-data "index.html;." --version-file "version_info.txt" server.py
echo.
if exist "dist\TrackerByEaurah\TrackerByEaurah.exe" (
  echo  === TERMINE ! ===
  echo  L'application : dist\TrackerByEaurah\  --  zippe TOUT le dossier pour publier.
) else (
  echo  !!! La compilation a echoue, regarde les erreurs ci-dessus.
)
echo.
pause
