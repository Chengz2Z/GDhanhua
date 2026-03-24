@echo off
setlocal

set "OUTPUT_DIR=.\out"
set "OUTPUT_FILE=%OUTPUT_DIR%\Text_ZH.arc"

if not exist "%OUTPUT_DIR%" (
    echo [INFO] Output directory does not exist. Creating: %OUTPUT_DIR%
    mkdir "%OUTPUT_DIR%"
    if errorlevel 1 (
        echo [ERROR] Failed to create output directory: %OUTPUT_DIR%
        exit /b 1
    )
)

if exist "%OUTPUT_FILE%" (
    echo [INFO] Removing existing output file: %OUTPUT_FILE%
    del /f /q "%OUTPUT_FILE%"
    if exist "%OUTPUT_FILE%" (
        echo [ERROR] Failed to remove existing output file: %OUTPUT_FILE%
        pause
        exit /b 1
    )
)

echo [INFO] Starting build...
ArchiveTool.exe "%OUTPUT_FILE%" -update . .\Text_ZH 6

if errorlevel 1 (
    echo [ERROR] Build failed. Please check the output above.
    pause
    exit /b 1
)

echo [SUCCESS] Build completed. Output file: %OUTPUT_FILE%
pause
