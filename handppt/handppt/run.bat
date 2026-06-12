@echo off
chcp 65001 >nul
title 手势 + 语音 PPT 控制器 (演讲稿模式)

echo ============================================
echo   手势 + 语音 PPT 控制器
echo   演讲稿模式 - 一键启动
echo ============================================
echo.

:: 切换到脚本所在目录
cd /d "%~dp0"

:: 设置 Python 路径（如果系统找不到 python，尝试常见安装路径）
set PYTHON_CMD=python
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    for %%p in (
        "C:\Python312\python.exe"
        "C:\Python311\python.exe"
        "C:\Program Files\Python312\python.exe"
        "C:\Program Files\Python311\python.exe"
        "C:\Program Files\Python313\python.exe"
        "C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python312\python.exe"
        "C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python311\python.exe"
    ) do (
        if exist "%%~p" (
            set PYTHON_CMD="%%~p"
            goto :found_python
        )
    )
    echo [错误] 未找到 Python，请确保 Python 已安装并加入 PATH
    pause
    exit /b 1
)
:found_python

echo [信息] 使用 Python: %PYTHON_CMD%
%PYTHON_CMD% --version

echo.
echo [信息] 检查 OpenAI 依赖...
%PYTHON_CMD% -c "import openai" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [信息] 安装 OpenAI SDK...
    %PYTHON_CMD% -m pip install openai>=1.0.0
)

echo.
echo [信息] 启动程序...
echo [提示] 请关注任务栏 - 将弹出 PPT 文件选择对话框
echo [提示] 选择 PPTX 后，将打开演讲稿设置面板
echo [提示] 可用方向键/鼠标滚轮手动滚动演讲稿
echo.
echo 按任意键开始...
pause >nul

%PYTHON_CMD% main.py

echo.
echo 程序已退出。
pause