#!/usr/bin/env bash
# Локальная сборка под Linux (.deb + .tar.gz) или macOS (.dmg).
# На GitHub то же самое делает Actions.
#
# Linux: нужен tkinter  ->  sudo apt install python3-tk python3-venv binutils
set -euo pipefail
cd "$(dirname "$0")"

python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt "pyinstaller>=6.10"
.venv/bin/python scripts/build.py "$@"

echo
echo "Готово: файлы лежат в папке release/"
