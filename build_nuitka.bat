@echo off
title Build - Tracker By Eaurah (Nuitka - moins de faux positifs)
cd /d "%~dp0"
echo.
echo  === Compilation du Tracker By Eaurah (Nuitka) ===
echo.
echo  Premiere fois : telechargement d'un compilateur C, c'est long (5-10 min).
echo.
echo  [1/2] Installation des dependances...
python -m pip install --upgrade nuitka requests
echo.
echo  [2/2] Compilation...
python -m nuitka --standalone --assume-yes-for-downloads --include-data-files=index.html=index.html --output-filename=TrackerByEaurah.exe --company-name="Eaurah (G_F_)" --product-name="Tracker By Eaurah" --file-version=1.0.0.0 --product-version=1.0.0.0 --file-description="Tracker Valorant temps reel" --copyright="Dev by Eaurah (G_F_)" server.py
echo.
if exist "server.dist\TrackerByEaurah.exe" (
  echo  === TERMINE ! ===
  echo  L'application : server.dist\  --  renomme le dossier en TrackerByEaurah
  echo  POUR PUBLIER : zippe TOUT le dossier, pas juste l'exe.
) else (
  echo  !!! La compilation a echoue, regarde les erreurs ci-dessus.
)
echo.
pause
