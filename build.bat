@echo off
setlocal

@REM Configure ENABLE_DESC to control whether affix summaries are kept.
@REM ENABLE_DESC=1 keeps summaries; ENABLE_DESC=0 removes them.
set "ENABLE_DESC=1"

set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%" >nul
if errorlevel 1 (
    echo [ERROR] Failed to enter project directory: %SCRIPT_DIR%
    exit /b 1
)

set "OUTPUT_DIR=%SCRIPT_DIR%out"
set "OUTPUT_FILE=%OUTPUT_DIR%\Text_ZH.arc"
set "STRIPPED_SOURCE_DIR=%OUTPUT_DIR%\_build\Text_ZH"
set "SOURCE_DIR=%SCRIPT_DIR%Text_ZH"

if /I "%~1"=="no-desc" (
    set "ENABLE_DESC=0"
) else if /I "%~1"=="with-desc" (
    set "ENABLE_DESC=1"
) else if /I "%~1"=="-h" (
    goto :help
) else if /I "%~1"=="--help" (
    goto :help
) else if not "%~1"=="" (
    echo [ERROR] Unknown build mode: %~1
    echo.
    goto :help
)

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

if /I "%ENABLE_DESC%"=="0" (
    set "SOURCE_DIR=%STRIPPED_SOURCE_DIR%"
    echo [INFO] Preparing build source without affix notes...
    if exist "%STRIPPED_SOURCE_DIR%" (
        rd /s /q "%STRIPPED_SOURCE_DIR%"
        if exist "%STRIPPED_SOURCE_DIR%" (
            echo [ERROR] Failed to remove previous build source: %STRIPPED_SOURCE_DIR%
            pause
            exit /b 1
        )
    )
    if not exist "%OUTPUT_DIR%\_build" (
        mkdir "%OUTPUT_DIR%\_build"
        if errorlevel 1 (
            echo [ERROR] Failed to create build temp directory: %OUTPUT_DIR%\_build
            pause
            exit /b 1
        )
    )
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Copy-Item -LiteralPath '%SCRIPT_DIR%Text_ZH' -Destination '%OUTPUT_DIR%\_build' -Recurse -Force"
    if errorlevel 1 (
        echo [ERROR] Failed to copy build source into: %STRIPPED_SOURCE_DIR%
        pause
        exit /b 1
    )
    if not exist "%STRIPPED_SOURCE_DIR%\tags_items.txt" (
        echo [ERROR] Build source was not created correctly: %STRIPPED_SOURCE_DIR%
        pause
        exit /b 1
    )
    powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%scripts\prepare-build.ps1" -TargetDir "%STRIPPED_SOURCE_DIR%" -StripAffixNotes
    if errorlevel 1 (
        echo [ERROR] Failed to prepare stripped build source.
        pause
        exit /b 1
    )
)

echo [INFO] Starting build...
"%SCRIPT_DIR%ArchiveTool.exe" "%OUTPUT_FILE%" -update . "%SOURCE_DIR%" 6

if errorlevel 1 (
    echo [ERROR] Build failed. Please check the output above.
    pause
    exit /b 1
)

echo [INFO] ENABLE_DESC="%ENABLE_DESC%"
echo [SUCCESS] Build completed. Output file: %OUTPUT_FILE%
pause
exit /b 0

:help
echo Usage:
echo   build.bat
echo   build.bat with-desc
echo   build.bat no-desc
echo.
echo Default switch in script:
echo   set ENABLE_DESC=1  Keep affix notes in parentheses.
echo   set ENABLE_DESC=0  Remove affix notes when double-clicking the script.
echo.
echo Command-line arguments override ENABLE_DESC:
echo   with-desc  Keep affix notes in parentheses.
echo   no-desc    Remove trailing parenthesized notes from tagPrefix/tagSuffix entries before packing.
pause
exit /b 1
