@echo off
setlocal enabledelayedexpansion
rem NX APP TRANSLATOR - Windows 7 self-test. Double-click. Takes ~1 minute. Writes RESULT.txt next to this file.
cd /d "%~dp0"
set R=%~dp0RESULT.txt
set A=x86
if /i "%PROCESSOR_ARCHITECTURE%"=="AMD64" set A=x64
if /i "%PROCESSOR_ARCHITEW6432%"=="AMD64" set A=x64
echo NX APP TRANSLATOR Windows self-test> "%R%"
ver>> "%R%"
echo arch tested: %A%>> "%R%"
set FAILS=0

echo. >> "%R%" & echo [1] shim probe (real nxshim7.dll, genuine Windows 7 fallbacks) >> "%R%"
pushd %A%
probe.exe >> "%R%" 2>&1
if errorlevel 1 (set /a FAILS+=1 & echo RESULT-1: FAIL>> "%R%") else (echo RESULT-1: PASS>> "%R%")

echo. >> "%R%" & echo [2] original program that needs Windows 8+ APIs (EXPECTED TO FAIL on Windows 7 - this shows the problem) >> "%R%"
echo.
echo NOTE: on Windows 7 a Windows error window ("entry point not found") may appear now. This is EXPECTED - click OK.
hello_original.exe >> "%R%" 2>&1
if errorlevel 1 (echo RESULT-2: failed as expected on this OS>> "%R%") else (echo RESULT-2: ran OK (this Windows already has those APIs - normal on Windows 8/10/11)>> "%R%")

echo. >> "%R%" & echo [3] translated program installed by the native installer (EXPECTED TO PASS) >> "%R%"
set D=%TEMP%\nxat_selftest_hello
hello-setup.exe --silent --dir "%D%"
if not exist "%D%\hello.exe" (set /a FAILS+=1 & echo RESULT-3: FAIL - installer did not install>> "%R%") else (
  "%D%\hello.exe" >> "%R%" 2>&1
  if errorlevel 1 (set /a FAILS+=1 & echo RESULT-3: FAIL - translated program did not run>> "%R%") else (echo RESULT-3: PASS>> "%R%")
  "%D%\uninstall.exe" --uninstall "%D%" --silent
)
popd
echo. >> "%R%"
if %FAILS%==0 (echo OVERALL: PASS>> "%R%") else (echo OVERALL: FAIL ^(%FAILS% test^(s^)^) - please send RESULT.txt back>> "%R%")
type "%R%"
echo.
pause
