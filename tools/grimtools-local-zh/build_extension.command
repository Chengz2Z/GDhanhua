#!/bin/bash

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

printf '%s\n' "============================================================"
printf '%s\n' " GrimTools Local Chinese Extension Builder"
printf '%s\n\n' "============================================================"

if command -v python3 >/dev/null 2>&1; then
    python_command=python3
elif command -v python >/dev/null 2>&1; then
    python_command=python
else
    printf '%s\n' "[ERROR] Python 3 was not found."
    build_exit_code=1
fi

if [ -n "${python_command:-}" ]; then
    "$python_command" "$SCRIPT_DIR/build_extension.py"
    build_exit_code=$?
fi

printf '\n'
if [ "$build_exit_code" -eq 0 ]; then
    printf '%s\n' "[SUCCESS] Chromium and Safari extension files were generated."
    printf '%s\n' "[NEXT] Reload the extension, then refresh GrimTools."
else
    printf '%s\n' "[FAILED] Build did not finish. Check the errors above."
fi

if [ -t 0 ]; then
    printf '\nPress any key to continue . . .'
    IFS= read -r -n 1 _
    printf '\n'
fi

exit "$build_exit_code"
