# ConceptFlow

**A-share concept-board main-force fund-flow → vertical short video**

一键拉取东方财富概念板块分时主力净流入，渲染 3Blue1Brown 风格竖屏短视频（2K），并自动配乐。

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

示例成片：[`examples/FundFlowOverlay_2026-08-10.mp4`](examples/FundFlowOverlay_2026-08-10.mp4)

---

## 需要准备

| 项目 | 说明 |
|------|------|
| OS | Windows 10/11（推荐），macOS / Linux 也可 |
| Python | **3.10+**（安装时勾选 Add to PATH） |
| FFmpeg | 命令行可运行 `ffmpeg` / `ffprobe` → [下载](https://ffmpeg.org/download.html) |
| 字体 | Windows：微软雅黑；macOS 可设 `FUND_FLOW_CN_FONT=PingFang SC` |

---

## 快速开始

### Windows（最简单）

1. Clone 本仓库并进入目录  
2. 双击 **`一键生成.bat`**（首次自动建虚拟环境并装依赖）  
3. 成片在 `output/<交易日>/FundFlowOverlay_<真实日期>_<时刻>.mp4`

### 命令行（全平台）

```bash
git clone https://github.com/Xiangyahaian/ConceptFlow.git
cd ConceptFlow

python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
# source .venv/bin/activate

pip install -r requirements.txt

# 先用不联网案例验证环境（约几分钟，低清更快可加 --ql）
python run.py --sample --ql --yes

# 拉最新交易日数据并出 2K 成片（默认 30fps）
python run.py --yes
```

---

## 常用命令

```bash
python run.py                 # 拉最新数据 → 2K 渲染 → 配乐
python run.py --sample        # 离线：内置 2026-08-10 案例
python run.py --yes           # 非今日数据时不询问
python run.py --ql            # 低清预览（调试用）
python run.py --smooth        # 60fps（更丝滑，更慢）
python run.py --no-bgm        # 不要背景音乐
python run.py --no-render     # 只更新数据，不渲染
python run.py --force-fetch   # 强制重新下载 API 数据
```

---

## 更换 BGM

当前使用的文件：`assets/bgm.mp3`

1. 打开 `assets/`（或双击 `切换BGM.bat`）  
2. 用你的 mp3 **覆盖** `bgm.mp3`  
3. 再运行 `python run.py`

备选歌曲可放在 `assets/bgm_library/`。

---

## 项目结构

```
ConceptFlow/
  run.py                 # 主入口
  boards.json            # 跟踪的约 36 个概念板块
  requirements.txt
  一键生成.bat            # Windows 一键
  assets/bgm.mp3         # 默认背景音乐
  scenes/                # Manim 场景
  src/                   # 拉数 / 打包 / 配乐 / 日期检查
  data/examples/         # 离线案例数据（--sample）
  examples/              # 示例成片
  output/                # 你的产出（按交易日分子目录，已 gitignore）
```

### 数据流

```
boards.json
  → 东财 fflow API
  → data/concept_fflow_major.json
  → Manim 竖屏动画（纵轴自适应）
  → ffmpeg 混入 BGM
  → output/<交易日>/FundFlowOverlay_<产出时刻>.mp4
```

若接口返回日期不是今天（周末/盘前/延迟），程序会询问是否使用上一交易日；加 `--yes` 可跳过。

---

## 输出说明

- **文件夹名**：数据对应的交易日，如 `output/2026-08-10/`  
- **文件名**：你本机产出时的真实日期+时刻，如 `FundFlowOverlay_2026-08-11_134500.mp4`  
- 默认分辨率：**1440×2560（竖屏 2K）@ 30fps**

---

## 修改跟踪板块

编辑根目录 `boards.json`（保留 `code` / `name` 字段）即可增删概念板。

---

## 常见问题

**拉数失败 / 连接断开**  
东财接口偶发拒连。多试几次或换网络；也可先 `python run.py --sample` 验证渲染链路。

**中文变方框**  
缺少中文字体。macOS 示例：

```bash
export FUND_FLOW_CN_FONT="PingFang SC"
python run.py --sample --ql --yes
```

**渲染慢**  
2K 正常需要一段时间。调试用 `--ql`；正式片用默认即可。

---

## 合规说明

数据来自东方财富公开行情接口，仅供学习与个人可视化。请勿高频爬取或商用转售。本项目不构成任何投资建议。

---

## License

[MIT](LICENSE)
