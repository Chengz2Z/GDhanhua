@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "ARCHIVE_TOOL=%SCRIPT_DIR%..\ArchiveTool.exe"
for %%I in ("%SCRIPT_DIR%.") do set "TARGET_DIR=%%~fI"
set "HAS_ARC="

if not exist "%ARCHIVE_TOOL%" (
    echo [ERROR] ArchiveTool.exe not found: %ARCHIVE_TOOL%
    pause
    exit /b 1
)

echo [INFO] Cleaning previous extracted files...
for /d %%D in ("%SCRIPT_DIR%*") do (
    if /I not "%%~xD"==".arc" (
        rd /s /q "%%~fD"
    )
)

for %%F in ("%SCRIPT_DIR%*") do (
    if /I not "%%~xF"==".bat" if /I not "%%~xF"==".arc" del /f /q "%%~fF"
)

for %%A in ("%SCRIPT_DIR%*.arc") do (
    set "HAS_ARC=1"
    echo [INFO] Extracting: %%~nxA
    "%ARCHIVE_TOOL%" "%%~fA" -extract "%TARGET_DIR%"
    if errorlevel 1 (
        echo [ERROR] Failed to extract: %%~nxA
        pause
        exit /b 1
    )
)

if not defined HAS_ARC (
    echo [ERROR] No .arc files found in: %SCRIPT_DIR%
    pause
    exit /b 1
)

echo [SUCCESS] Extraction completed in: %TARGET_DIR%
pause
