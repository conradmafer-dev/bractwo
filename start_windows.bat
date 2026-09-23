@echo off
setlocal
cd /d "%~dp0"
set "GAME_HOST=127.0.0.1"
if /I "%~1"=="lan" set "GAME_HOST=0.0.0.0"
if not exist ".venv\Scripts\python.exe" (
  py -3 -m venv .venv
  if errorlevel 1 goto missingpython
)
".venv\Scripts\python.exe" -m pip install -r server\requirements.txt
if errorlevel 1 goto installerror
echo.
echo Bractwo - Pogranicze - http://127.0.0.1:8080
echo Pozostaw to okno otwarte. Zatrzymanie serwera: Ctrl+C.
".venv\Scripts\python.exe" server\server.py --host "%GAME_HOST%" --port 8080 --db data\world.sqlite3
pause
exit /b
:missingpython
echo Zainstaluj Python 3.11 lub nowszy z python.org wraz z launcherem py.
pause
exit /b 1
:installerror
echo Nie udalo sie zainstalowac zaleznosci. Sprawdz polaczenie z internetem.
pause
exit /b 1
