@echo off
setlocal EnableDelayedExpansion

echo Activating virtual environment...
:: 激活虚拟环境
call .\read_venv\Scripts\activate.bat

echo Script execution completed
python app.py

:: Start a new command prompt with the activated virtual environment
cmd /k

