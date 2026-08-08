@echo off
rem Copyright 2026 Chengz2Z
rem
rem Licensed under the Apache License, Version 2.0 (the "License");
rem you may not use this file except in compliance with the License.
rem You may obtain a copy of the License at
rem
rem     http://www.apache.org/licenses/LICENSE-2.0
rem
rem Unless required by applicable law or agreed to in writing, software
rem distributed under the License is distributed on an "AS IS" BASIS,
rem WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
rem See the License for the specific language governing permissions and
rem limitations under the License.
rem
rem Author: Chengz2Z

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
