@echo off
cd /d "%~dp0"
if not exist venv\Scripts\python.exe goto noenv

echo.
echo [1/3] Installo gli strumenti di costruzione...
venv\Scripts\python.exe -m pip install -r requirements-build.txt
if errorlevel 1 goto errore

echo.
echo [2/3] Costruisco il programma con PyInstaller...
venv\Scripts\python.exe -m PyInstaller --noconfirm --clean NOVAstitch.spec
if errorlevel 1 goto errore

echo.
echo [3/3] Creo l'installer con Inno Setup...
rem Cerca ISCC.exe in qualunque cartella "Inno Setup *" (6, 7, ...): vince la piu' recente.
set "ISCC="
set "PF86=%ProgramFiles(x86)%"
for /d %%D in ("%PF86%\Inno Setup*" "%ProgramFiles%\Inno Setup*" "%LocalAppData%\Programs\Inno Setup*") do if exist "%%~D\ISCC.exe" set "ISCC=%%~D\ISCC.exe"
if not defined ISCC goto noinno
echo Uso: %ISCC%
"%ISCC%" installer.iss
if errorlevel 1 goto errore

echo.
echo FATTO. L'installer e' nella cartella installer_output
pause
exit /b 0

:noenv
echo Ambiente non trovato. Lancia prima installa_ambiente.bat
pause
exit /b 1

:noinno
echo.
echo Il programma e' pronto in dist\NOVAstitch ma non trovo Inno Setup.
echo Apri installer.iss con Inno Setup e premi Compila, oppure scrivimi dove si trova ISCC.exe.
pause
exit /b 1

:errore
echo.
echo ERRORE: la costruzione si e' fermata. Leggi i messaggi qui sopra.
pause
exit /b 1
