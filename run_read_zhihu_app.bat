@echo off

:: 切换到项目文件夹
cd /d "C:\Users\Administrator\Work\read_zhihu_app"

:: 激活虚拟环境
call .\read_venv\Scripts\activate.bat


:: 使用 pyw， 在后台运行，静默启动 
start /B pythonw app.pyw

:: 把此文件 复制到
:: C:\Users\Administrator\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup

