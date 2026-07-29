@echo off
setlocal
chcp 65001 >nul
pushd "%~dp0"

echo ============================================================
echo  GrimTools Local Chinese Extension Builder
echo ============================================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python was not found in PATH.
    set "build_exit_code=1"
    goto finish
)

python "%~dp0build_extension.py"
set "build_exit_code=%errorlevel%"

:finish
echo.
if "%build_exit_code%"=="0" (
    echo [SUCCESS] Extension files were generated.
    echo [NEXT] Reload the extension, then refresh GrimTools.
) else (
    echo [FAILED] Build did not finish. Check the errors above.
)
echo.
pause

popd
exit /b %build_exit_code%
