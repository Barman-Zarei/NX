@echo off
rem Run this on a real Windows 7 SP1 machine from the folder with nx-media-tool-cli\ and nx-media-tool\ (from the CI artifact).
rem It writes win7-report.txt: send that file to the maintainer. Nothing here has been run on Windows 7 yet.
set R=%~dp0win7-report.txt
echo NX Media Tool Windows 7 smoke test > "%R%"
ver >> "%R%"
echo arch=%PROCESSOR_ARCHITECTURE% >> "%R%"
echo hello> "%TEMP%\nx-test.iso"
rem sha256 of the string "hello\r\n" is computed by certutil; the CLI is then asked to verify it
certutil -hashfile "%TEMP%\nx-test.iso" SHA256 > "%TEMP%\nx-h.txt" 2>&1
for /f "skip=1 tokens=1" %%h in (%TEMP%\nx-h.txt) do (echo %%h  nx-test.iso> "%TEMP%\nx-test.iso.sha256" & goto :done)
:done
"%~dp0nx-media-tool-cli\nx-media-tool-cli.exe" "%TEMP%\nx-test.iso" "%TEMP%\nx-test.iso.sha256" >> "%R%" 2>&1
echo cli_exit=%ERRORLEVEL% >> "%R%"
"%~dp0nx-media-tool\nx-media-tool.exe" --selftest "%TEMP%\nx-selftest.txt"
echo gui_exit=%ERRORLEVEL% >> "%R%"
if exist "%TEMP%\nx-selftest.txt" (type "%TEMP%\nx-selftest.txt" >> "%R%") else (echo selftest file missing >> "%R%")
echo Report written to %R%
