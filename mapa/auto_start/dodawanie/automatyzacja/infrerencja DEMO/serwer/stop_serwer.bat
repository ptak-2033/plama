@echo off
setlocal ENABLEDELAYEDEXPANSION
set ROOT=%~dp0
set CFG=%ROOT%konfiguracje.txt
set MAPA=%ROOT%mapa_dane.txt

for /f "usebackq tokens=1,* delims==" %%A in ("%CFG%") do (
  set k=%%A
  set v=%%B
  set k=!k: =!
  set k=!k:-=_!
  if /I "!k!"=="port"  set PORT=%%B
  if /I "!k!"=="host"  set HOST=%%B
)
if "%HOST%"=="" set HOST=127.0.0.1
if "%PORT%"=="" (
  echo [ERR] Brak 'port' w konfiguracje.txt
  goto :offwrite
)

echo [INFO] host=%HOST% port=%PORT%
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":%PORT% .*LISTENING"') do set PID=%%P

if not "%PID%"=="" (
  echo [KILL] PID=%PID% nasluchujacy na :%PORT%
  taskkill /PID %PID% /T /F >nul 2>nul
) else (
  echo [INFO] Nic nie nasluchuje na :%PORT% (moze juz wylaczone).
)

:offwrite
echo [MAPA] proces=off → "%MAPA%"
powershell -NoLogo -NoProfile -Command ^
  "if (Test-Path '%MAPA%') { $c=Get-Content '%MAPA%' -Raw; if ($c -match '^proces=') {$c=$c -replace '^proces=.*','proces=off'} else {$c=$c.TrimEnd()+\"`nproces=off`n\"}; Set-Content '%MAPA%' $c -Encoding UTF8 } else { Set-Content '%MAPA%' 'proces=off' -Encoding UTF8 }"
echo [OK] Done.
endlocal
