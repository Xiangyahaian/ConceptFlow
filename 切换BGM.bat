@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo ========================================
echo   更换背景音乐（最简单）
echo ========================================
echo.
echo   1. 马上会打开 assets 文件夹
echo   2. 把你的 mp3 粘贴进去
echo   3. 改名为 bgm.mp3 （覆盖原来的）
echo   4. 关掉窗口，再运行「一键生成」
echo.
pause

explorer "%~dp0assets"

echo.
echo 改好 bgm.mp3 之后，直接运行 一键生成.bat 就行。
pause
