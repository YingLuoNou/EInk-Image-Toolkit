# 电子纸图像工具 (EInk-Image-Toolkit)

[Read this in English](./README.md)

一款功能强大、支持交互式操作的 GUI 图像处理软件，专为电子纸/墨水屏以及单片机（Arduino, ESP32, STM32 等）开发者设计，用于图像的预处理与 C 数组代码导出。

## ✨ 核心特性

* **交互式裁剪与变换**：支持鼠标拖拽平移、滚轮缩放的“所见即所得”实时预览。按住 `Shift` 键可锁定移动轴向，按住 `Ctrl` 键配合滚轮可进行超精细缩放微调。
* **丰富的抖动算法**：内置 Floyd-Steinberg、Atkinson（高对比度）、Stucki、Burkes、Sierra3、蓝噪（Blue Noise）等多种算法，在有限色彩的屏幕上榨干每一滴显示潜能。
* **实时图像增强**：直接在界面上调整饱和度、对比度、亮度以及 RGB 单通道参数。
* **一键导出 C 数组**：无缝生成 `.c` 数组文件，完美适配 GxEPD2 等驱动库，直接复制到你的嵌入式工程即可使用。
* **全格式调色板支持**：
    * 单色 (1-bit)、4 级灰度 (2-bit)、16 级灰度 (4-bit)
    * GxEPD2 专用打包格式 (6 色 E6、7 色 ACeP)
    * RGB332, RGB565, RGB888, ARGB8888 以及 4096 色 (12-bit)
* **硬件级扫描设置**：支持水平/垂直扫描模式切换、数据镜像 (X)、数据翻转 (Y) 以及高低位交换 (Swap Nibbles)，从容应对排线反接的特殊屏幕。
* **中英双语 UI**：支持在界面中一键无缝切换语言，且不会打断当前的处理进度。

## 🚀 环境要求

本项目使用 [uv](https://github.com/astral-sh/uv) 进行依赖管理。`uv` 是一个用 Rust 编写的极速 Python 包安装器。

如果你还没有安装 `uv`，可以通过以下命令安装：
```bash
# macOS 或 Linux:
curl -LsSf [https://astral.sh/uv/install.sh](https://astral.sh/uv/install.sh) | sh

# Windows (在 PowerShell 中运行):
powershell -ExecutionPolicy ByPass -c "irm [https://astral.sh/uv/install.ps1](https://astral.sh/uv/install.ps1) | iex"
🛠️ 安装与运行
克隆项目到本地：

Bash
git clone [https://github.com/yourusername/EInk-Image-Toolkit.git](https://github.com/yourusername/EInk-Image-Toolkit.git)
cd EInk-Image-Toolkit
使用 uv 添加依赖库：

Bash
uv add numpy pillow
启动程序：

Bash
uv run main.py
（注：如果你的主程序文件名不是 main.py，请自行替换为实际的文件名）。

🖱️ 画布交互指南
鼠标左键 + 拖拽：在裁剪框内自由移动图像。

鼠标滚轮：放大/缩小图像。

按住 Shift + 拖拽：锁定为纯水平或纯垂直方向移动（防手抖）。

按住 Ctrl + 滚轮：开启精细缩放模式（每次 2%），用于像素级完美对齐。

📄 开源协议
本项目基于 MIT 协议开源。