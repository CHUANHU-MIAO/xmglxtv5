@echo off
chcp 65001 >nul
echo ============================================
echo  Estimate Studio 构建脚本
echo ============================================
echo.

:: 检查 PyInstaller
where pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到 PyInstaller，请先安装:
    echo   pip install pyinstaller
    pause
    exit /b 1
)

:: 检查 Inno Setup 编译器
set ISCC_PATH="D:\Inno Setup 6\ISCC.exe"
if not exist %ISCC_PATH% (
    set ISCC_PATH="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
)
if not exist %ISCC_PATH% (
    set ISCC_PATH="C:\Program Files\Inno Setup 6\ISCC.exe"
)
if not exist %ISCC_PATH% (
    echo [警告] 未找到 Inno Setup 编译器 (ISCC.exe)
    echo 请安装 Inno Setup: https://jrsoftware.org/isinfo.php
    echo 将跳过生成安装包步骤
    set SKIP_ISS=1
)

echo [1/3] 清理旧构建...
rmdir /s /q dist 2>nul
rmdir /s /q build 2>nul
rmdir /s /q installer 2>nul
del /q *.spec 2>nul

echo [2/3] 使用 PyInstaller 打包桌面端...
echo.

:: 打包 GUI 版本（有窗口）
pyinstaller --onedir --windowed --noconfirm ^
    --name "EstimateStudio" ^
    --add-data "..\web;web" ^
    --add-data "..\core;core" ^
    --add-data "..\app.py;." ^
    --add-data "..\config.py;." ^
    --add-data "..\license_manager.py;." ^
    --add-data "desktop_templates;desktop\desktop_templates" ^
    --add-data "license.txt;." ^
    --icon "app.ico" ^
    --hidden-import "web" ^
    --hidden-import "web.app" ^
    --hidden-import "web.config" ^
    --hidden-import "web.models" ^
    --hidden-import "web.extensions" ^
    --hidden-import "web.blueprints" ^
    --hidden-import "web.blueprints.auth" ^
    --hidden-import "web.blueprints.projects" ^
    --hidden-import "web.blueprints.admin" ^
    --hidden-import "web.blueprints.files" ^
    --hidden-import "web.blueprints.estimation" ^
    --hidden-import "web.services" ^
    --hidden-import "web.services.project_service" ^
    --hidden-import "desktop" ^
    --hidden-import "desktop.main_window" ^
    --hidden-import "desktop.subscription" ^
    --hidden-import "desktop.first_run_config" ^
    --hidden-import "flask" ^
    --hidden-import "flask_sqlalchemy" ^
    --hidden-import "flask_login" ^
    --hidden-import "flask_wtf" ^
    --hidden-import "werkzeug" ^
    --hidden-import "sqlalchemy" ^
    --hidden-import "jinja2" ^
    --hidden-import "cryptography" ^
    --hidden-import "openpyxl" ^
    --hidden-import "dateutil" ^
    --hidden-import "lxml" ^
    --hidden-import "PIL" ^
    --collect-all "PySide6" ^
    desktop_app.py

if %errorlevel% neq 0 (
    echo [错误] PyInstaller 打包失败
    pause
    exit /b 1
)

echo.
echo [3/3] 使用 Inno Setup 生成安装包...

if "%SKIP_ISS%"=="1" (
    echo [跳过] 未找到 Inno Setup，请手动运行 setup.iss
) else (
    %ISCC_PATH% setup.iss
    if %errorlevel% neq 0 (
        echo [警告] Inno Setup 编译失败，请检查 setup.iss 配置
    ) else (
        echo.
        echo ============================================
        echo  构建成功！安装包位于: installer\ 目录
        echo ============================================
    )
)

pause
