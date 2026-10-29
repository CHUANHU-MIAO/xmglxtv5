@echo off
chcp 65001 >nul
setlocal
title 鑫奥项目管理系统
rem 便携启动脚本：使用相对路径，克隆到任意机器/任意目录均可运行
cd /d "%~dp0"

echo ============================================
echo   鑫奥项目管理系统 - 启动中
echo   目录: %cd%
echo ============================================

rem ---- 1. 检查 Python ----
where python >nul 2>nul
if errorlevel 1 (
    echo [错误] 未找到 python，请先安装 Python 3.9+ 并加入 PATH。
    goto :fail
)

rem ---- 2. 虚拟环境：不存在则自动创建并装依赖 ----
if not exist "venv\Scripts\python.exe" (
    echo [提示] 未找到虚拟环境，正在创建 venv ...
    python -m venv venv
    if errorlevel 1 goto :fail
    echo [提示] 正在安装依赖（首次较慢）...
    call venv\Scripts\activate.bat
    python -m pip install --upgrade pip >nul 2>nul
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [错误] 依赖安装失败，请检查网络后重试。
        goto :fail
    )
) else (
    call venv\Scripts\activate.bat
)

rem ---- 3. 检查授权文件（license.key 与机器绑定，不随仓库分发）----
if not exist "license.key" (
    echo.
    echo [错误] 未找到 license.key
    echo        授权文件与本机硬件绑定，需向管理员索取对应本机的 license.key
    echo        并放到: %cd%\license.key
    goto :fail
)

rem ---- 4. 启动 ----
echo.
echo [启动] http://0.0.0.0:5005  （默认端口 5005，可用 set PORT=xxxx 修改）
echo.
python app.py

:fail
echo.
pause
