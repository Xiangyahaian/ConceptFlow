#!/bin/bash
# ConceptFlow — macOS 双击运行（或在终端执行 ./一键生成.command）
set -e
cd "$(dirname "$0")"

echo "============================================"
echo "  ConceptFlow - 概念资金流向视频 (macOS)"
echo "============================================"
echo

# Prefer python3
if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "[错误] 未找到 Python。请先安装："
  echo "  brew install python"
  echo "或从 https://www.python.org/downloads/ 安装 3.10+"
  read -r -p "按回车退出…"
  exit 1
fi

if ! command -v ffmpeg >/dev/null 2>&1 || ! command -v ffprobe >/dev/null 2>&1; then
  echo "[错误] 未找到 ffmpeg/ffprobe。"
  echo "请先安装 Homebrew，然后执行："
  echo "  brew install ffmpeg"
  read -r -p "按回车退出…"
  exit 1
fi

# Chinese font for Manim on macOS
export FUND_FLOW_CN_FONT="${FUND_FLOW_CN_FONT:-PingFang SC}"

if [ ! -x ".venv/bin/python" ]; then
  echo "[安装] 首次运行：创建虚拟环境并安装依赖…"
  "$PY" -m venv .venv
  # shellcheck disable=SC1091
  source .venv/bin/activate
  python -m pip install -U pip
  # Manim on macOS sometimes needs these via brew; pip still installs manim
  pip install -r requirements.txt
else
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

echo
echo "开始拉取最新数据并渲染…"
echo "（2K@30fps 约 8–18 分钟；可用 --sample --ql 先试跑）"
echo
python run.py "$@"
echo
echo "成片目录: $(pwd)/output/<交易日>/"
read -r -p "按回车关闭…"
