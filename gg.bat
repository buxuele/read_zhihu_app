:: 文件名：git-sync-push.bat
chcp 65001 > nul

:: 确保当前分支是 main
git branch -M main

:: 获取远程仓库的最新信息
git fetch origin

:: 检查本地 main 分支是否落后于远程 main 分支
for /f %%i in ('git rev-list --count main..origin/main') do set COMMITS=%%i

:: 如果远程有新提交（COMMITS > 0），则拉取最新代码
if %COMMITS% GTR 0 (
    echo 检测到远程有 %COMMITS% 个新提交，正在拉取最新代码...
    git pull origin main
    if errorlevel 1 (
        echo 错误：拉取代码失败，可能是冲突！请手动解决冲突后重试。
        pause
        exit /b 1
    )
) else (
    echo 本地代码已是最新，无需拉取。
)

:: 显示当前的 Git 状态
git status

:: 将当前目录下的所有更改添加到 Git 的暂存区
git add .

:: 提示用户输入提交信息
set /p message="Enter commit message: "

:: 使用用户输入的提交信息来提交暂存区的更改
git commit -m "%message%"

:: 将本地的提交推送到远程仓库
git push origin main

:: 显示执行 git push 后的 Git 状态
git status

:: 提示操作完成
echo 代码已提交并推送完成！