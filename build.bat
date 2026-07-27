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

if /I "%~1"=="release" (
    goto :release
) else if "%~1"=="" (
    goto :release
) else if /I "%~1"=="no-desc" (
    set "ENABLE_DESC=0"
) else if /I "%~1"=="with-desc" (
    set "ENABLE_DESC=1"
) else if /I "%~1"=="-h" (
    goto :help
) else if /I "%~1"=="--help" (
    goto :help
) else (
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

:release
echo [INFO] Starting release build...

set "NAME_WITH_DESC=有简述版"
set "NAME_NO_DESC=无简述版"
REM set "NAME_WITH_DESC=with_desc"
REM set "NAME_NO_DESC=no_desc"

REM Step 1: Build with description
echo [INFO] Building with description...
set "ENABLE_DESC=1"
set "OUTPUT_FILE=%OUTPUT_DIR%\arc_%NAME_WITH_DESC%\Text_ZH.arc"
set "SOURCE_DIR=%SCRIPT_DIR%Text_ZH"
if not exist "%OUTPUT_DIR%\arc_%NAME_WITH_DESC%" (
    mkdir "%OUTPUT_DIR%\arc_%NAME_WITH_DESC%"
)
if exist "%OUTPUT_FILE%" (
    del /f /q "%OUTPUT_FILE%"
)
"%SCRIPT_DIR%ArchiveTool.exe" "%OUTPUT_FILE%" -update . "%SOURCE_DIR%" 6
if errorlevel 1 (
    echo [ERROR] Build with description failed.
    pause
    exit /b 1
)
echo [SUCCESS] Built with description: %OUTPUT_FILE%

REM Step 2: Copy source files to set_with_desc
echo [INFO] Copying source files to set_with_desc...
set "SET_DIR=%OUTPUT_DIR%\set_%NAME_WITH_DESC%\Text_ZH"
if not exist "%OUTPUT_DIR%\set_%NAME_WITH_DESC%" (
    mkdir "%OUTPUT_DIR%\set_%NAME_WITH_DESC%"
)
if exist "%SET_DIR%" (
    rd /s /q "%SET_DIR%"
)
powershell -NoProfile -ExecutionPolicy Bypass -Command "Copy-Item -LiteralPath '%SCRIPT_DIR%Text_ZH' -Destination '%OUTPUT_DIR%\set_%NAME_WITH_DESC%' -Recurse -Force"
if errorlevel 1 (
    echo [ERROR] Failed to copy source files.
    pause
    exit /b 1
)
echo [SUCCESS] Copied source files to: %SET_DIR%

REM Step 3: Build without description
echo [INFO] Building without description...
set "ENABLE_DESC=0"
set "OUTPUT_FILE=%OUTPUT_DIR%\arc_%NAME_NO_DESC%\Text_ZH.arc"
set "STRIPPED_SOURCE_DIR=%OUTPUT_DIR%\_build\Text_ZH"
set "SOURCE_DIR=%STRIPPED_SOURCE_DIR%"
if not exist "%OUTPUT_DIR%\arc_%NAME_NO_DESC%" (
    mkdir "%OUTPUT_DIR%\arc_%NAME_NO_DESC%"
)
if exist "%OUTPUT_FILE%" (
    del /f /q "%OUTPUT_FILE%"
)
REM Prepare stripped source
if exist "%STRIPPED_SOURCE_DIR%" (
    rd /s /q "%STRIPPED_SOURCE_DIR%"
)
if not exist "%OUTPUT_DIR%\_build" (
    mkdir "%OUTPUT_DIR%\_build"
)
powershell -NoProfile -ExecutionPolicy Bypass -Command "Copy-Item -LiteralPath '%SCRIPT_DIR%Text_ZH' -Destination '%OUTPUT_DIR%\_build' -Recurse -Force"
if errorlevel 1 (
    echo [ERROR] Failed to copy source for stripping.
    pause
    exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%scripts\prepare-build.ps1" -TargetDir "%STRIPPED_SOURCE_DIR%" -StripAffixNotes
if errorlevel 1 (
    echo [ERROR] Failed to prepare stripped build source.
    pause
    exit /b 1
)
"%SCRIPT_DIR%ArchiveTool.exe" "%OUTPUT_FILE%" -update . "%SOURCE_DIR%" 6
if errorlevel 1 (
    echo [ERROR] Build without description failed.
    pause
    exit /b 1
)
echo [SUCCESS] Built without description: %OUTPUT_FILE%

REM Step 4: Move stripped source to set_no_desc
echo [INFO] Moving stripped source to set_no_desc...
set "SET_DIR=%OUTPUT_DIR%\set_%NAME_NO_DESC%\Text_ZH"
if not exist "%OUTPUT_DIR%\set_%NAME_NO_DESC%" (
    mkdir "%OUTPUT_DIR%\set_%NAME_NO_DESC%"
)
if exist "%SET_DIR%" (
    rd /s /q "%SET_DIR%"
)
move "%STRIPPED_SOURCE_DIR%" "%SET_DIR%"
if errorlevel 1 (
    echo [ERROR] Failed to move stripped source.
    pause
    exit /b 1
)
echo [SUCCESS] Moved stripped source to: %SET_DIR%

REM Step 5: Clean up temporary build directory
if exist "%OUTPUT_DIR%\_build" (
    rd /s /q "%OUTPUT_DIR%\_build"
)

echo [INFO] Release build completed.
pause
exit /b 0

:help
echo Usage:
echo   build.bat                (default: release)
echo   build.bat release        Build all versions for release.
echo   build.bat with-desc      Build with affix notes.
echo   build.bat no-desc        Build without affix notes.
echo.
echo Default switch in script:
echo   set ENABLE_DESC=1  Keep affix notes in parentheses.
echo   set ENABLE_DESC=0  Remove affix notes when double-clicking the script.
echo.
echo Command-line arguments override ENABLE_DESC:
echo   release    Build all versions for release (default).
echo   with-desc  Keep affix notes in parentheses.
echo   no-desc    Remove trailing parenthesized notes from tagPrefix/tagSuffix entries before packing.
pause
exit /b 1
