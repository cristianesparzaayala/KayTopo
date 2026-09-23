@echo off
setlocal
cd /d "%~dp0\.."

set "APP_VERSION=0.1.2-alpha"
set "VERSION_INFO=0.1.2.0"
if not "%~1"=="" set "APP_VERSION=%~1"
if not "%~2"=="" set "VERSION_INFO=%~2"

echo [KayTopo] Compilando ejecutable portable...
call scripts\BUILD_WINDOWS.bat --no-pause
if errorlevel 1 goto :fail

set "ISCC="
where ISCC.exe >nul 2>nul
if not errorlevel 1 set "ISCC=ISCC.exe"

if not defined ISCC if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%ProgramFiles%\Inno Setup 7\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 7\ISCC.exe"

if not defined ISCC (
  echo.
  echo ERROR: No se encontro Inno Setup Compiler ^(ISCC.exe^).
  echo Instala Inno Setup y vuelve a ejecutar este script.
  echo https://jrsoftware.org/isinfo.php
  goto :fail
)

echo [KayTopo] Generando instalador %APP_VERSION%...
"%ISCC%" /Qp "/DMyAppVersion=%APP_VERSION%" "/DMyVersionInfo=%VERSION_INFO%" installer\KayTopo.iss
if errorlevel 1 goto :fail

echo.
echo LISTO:
echo   Portable:  dist\KayTopo.exe
echo   Instalador: dist\KayTopo_Setup_v%APP_VERSION%.exe
pause
exit /b 0

:fail
echo.
echo ERROR: no se pudo generar el instalador.
pause
exit /b 1
