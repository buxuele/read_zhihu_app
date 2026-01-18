@echo off
setlocal enabledelayedexpansion

REM 用法检查
if "%~1"=="" (
    echo 用法: emo 文件名.py
    exit /b 1
)

set "FILE=%~1"

if not exist "%FILE%" (
    echo 文件不存在: %FILE%
    exit /b 1
)

REM 使用 PowerShell 删除 emoji（核心逻辑）
powershell -NoProfile -Command ^
    "$p='%FILE%';" ^
    "$t=Get-Content -Raw -Encoding UTF8 $p;" ^
    "$t=[regex]::Replace($t,'[\p{So}\p{Cs}]','');" ^
    "Set-Content -Encoding UTF8 $p $t"

echo 已清理 emoji: %FILE%
