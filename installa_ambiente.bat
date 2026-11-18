@echo off
cd /d "%~dp0"
echo.
echo === NOVAstitch: creazione dell'ambiente Python ===
echo.
where python >nul 2>nul
if errorlevel 1 (
  echo ERRORE: Python non trovato.
  echo Installalo da python.org e spunta Add python.exe to PATH.
  echo.
  pause
  exit /b 1
)
if exist venv (
  echo ERRORE: esiste gia una cartella venv.
  echo Cancellala a mano e rilancia questo file.
  echo.
  pause
  exit /b 1
)
python --version
python -m venv venv
if errorlevel 1 (
  echo ERRORE nella creazione dell'ambiente.
  pause
  exit /b 1
)
venv\Scripts\python.exe -m pip install --upgrade pip
venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (
  echo ERRORE nell'installazione dei pacchetti. Controlla la connessione a internet.
  pause
  exit /b 1
)
echo.
echo FATTO. Ora usa avvia_NOVAstitch.bat
echo.
pause
