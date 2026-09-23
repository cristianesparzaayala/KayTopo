@echo off
setlocal
cd /d "%~dp0\.."

set "NO_PAUSE="
if /I "%~1"=="--no-pause" set "NO_PAUSE=1"

echo [KayTopo] Creando entorno de compilacion...
if not exist .venv-build\Scripts\python.exe (
  py -m venv .venv-build
  if errorlevel 1 goto :fail
)
call .venv-build\Scripts\activate.bat
python -m pip install --upgrade pip
if errorlevel 1 goto :fail
pip install -r requirements-dev.txt
if errorlevel 1 goto :fail

echo [KayTopo] Ejecutando pruebas...
python -m pytest -q
if errorlevel 1 goto :fail

echo [KayTopo] Generando KayTopo.exe...
pyinstaller --noconfirm --clean KayTopo.spec
if errorlevel 1 goto :fail

echo.
echo LISTO: dist\KayTopo.exe
if not defined NO_PAUSE pause
exit /b 0

:fail
echo.
echo ERROR: la compilacion o las pruebas fallaron.
if not defined NO_PAUSE pause
exit /b 1
