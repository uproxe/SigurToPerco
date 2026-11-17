@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
rem Локальная сборка exe под Windows. На GitHub то же самое делает Actions.

set "PY="
where py >nul 2>nul && set "PY=py"
if not defined PY (
    where python >nul 2>nul && set "PY=python"
)
if not defined PY (
    echo Python не найден. Установите Python 3.10+ с python.org, отметив "Add python.exe to PATH".
    pause
    exit /b 1
)

echo [1/2] Библиотеки...
%PY% -m pip install --upgrade pip >nul
%PY% -m pip install -r requirements.txt "pyinstaller>=6.10" || goto :fail

echo [2/2] Сборка...
%PY% scripts\build.py || goto :fail

echo.
echo Готово: файл лежит в папке release
pause
exit /b 0

:fail
echo.
echo Сборка не удалась - смотрите сообщения выше.
pause
exit /b 1
