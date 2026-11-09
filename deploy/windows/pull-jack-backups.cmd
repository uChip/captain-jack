@echo off
rem Pull Captain Jack's data backups from the Pi to this desktop.
rem docs/specification.md section 4.17, "Backups". One-time setup is there.
rem
rem Copy this file to DEST (below), edit HOST if you reach the Pi by another
rem name, and schedule THAT copy - editing the repo copy would block pulls.
rem DEST must not be inside the repo clone: memory.md is private.
rem
rem The key below can only run one command on the Pi (set in its
rem authorized_keys): send ~/jack-data/backups as a tar stream. Snapshots
rem pile up here (the Pi keeps 30); they are tiny.
setlocal
set HOST=parrot-v2-0.local
set KEY=%USERPROFILE%\.ssh\jack_backup_pull
set DEST=E:\captain-jack-backups
set LOG=%DEST%\pull-log.txt

if not exist "%DEST%" mkdir "%DEST%"
ssh -T -i "%KEY%" -o BatchMode=yes -o ConnectTimeout=15 chips@%HOST% > "%DEST%\latest.tar" 2>> "%LOG%"
if errorlevel 1 (
    echo %date% %time% FAILED: no connection - Pi off or unreachable? >> "%LOG%"
    exit /b 1
)
tar -xf "%DEST%\latest.tar" -C "%DEST%" 2>> "%LOG%"
if errorlevel 1 (
    echo %date% %time% FAILED: archive would not unpack >> "%LOG%"
    exit /b 1
)
echo %date% %time% OK >> "%LOG%"
