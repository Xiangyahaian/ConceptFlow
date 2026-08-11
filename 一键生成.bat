@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================
echo   ConceptFlow - 概念资金流向视频
echo ============================================
echo.

where python >nul 2>nul
if errorlevel 1 (
  echo [错误] 未找到 python，请先安装 Python 3.10+ 并勾选 Add to PATH
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo [安装] 首次运行：创建虚拟环境并安装依赖…
  python -m venv .venv
  call .venv\Scripts\activate.bat
  python -m pip install -U pip
  pip install -r requirements.txt
) else (
  call .venv\Scripts\activate.bat
)

echo.
echo 开始拉取最新数据并渲染视频…
echo （2K@30fps 约 8-18 分钟；若今日数据未出，会询问是否用上一交易日）
echo.
python run.py %*
echo.
echo 成片按日期在: %cd%\output\YYYY-MM-DD\
pause
