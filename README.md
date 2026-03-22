# 墨水屏/电子纸图像工具 (EInk-Image-Toolkit)

[中文说明 (Chinese)](./readmeCN.md)

A powerful, interactive GUI application designed specifically for preparing, processing, and exporting images for E-Paper / E-Ink displays and microcontrollers (Arduino, ESP32, STM32, etc.).

## ✨ Key Features

* **Interactive Cropping & Transforming**: Visually crop, pan, and zoom images with a real-time WYSIWYG (What You See Is What You Get) preview. Supports Shift-key axis locking and Ctrl-key fine zooming.
* **Advanced Dithering Algorithms**: Includes Floyd-Steinberg, Atkinson, Stucki, Burkes, Sierra3, and Blue Noise dithering to maximize the visual quality on low-color displays.
* **Real-time Image Enhancement**: Adjust saturation, contrast, brightness, and RGB channels directly within the app.
* **C Array Export**: Seamlessly generate `.c` array files ready to be pasted into your embedded projects.
* **Broad Format Support**: 
    * 1-bit (Monochrome), 2-bit (4-Grayscale), 4-bit (16-Grayscale)
    * GxEPD2 Packed formats (6-color E6, 7-color ACeP)
    * RGB332, RGB565, RGB888, ARGB8888, and 12-bit (4096 colors)
* **Hardware Scan Modes**: Configure horizontal/vertical scanning, data mirroring, flipping, and nibble swapping to match your specific screen's hardware wiring.
* **Bilingual UI**: Switch seamlessly between English and Chinese on the fly without losing your current progress.

## 🚀 Prerequisites

This project uses [uv](https://github.com/astral-sh/uv), an extremely fast Python package installer and resolver written in Rust. 

If you don't have `uv` installed, you can install it via:
```bash
# On macOS and Linux.
curl -LsSf https://astral.sh/uv/install.sh | sh

# On Windows.
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```
🛠️ Installation & Usage
Clone the repository:

```Bash
git clone https://github.com/yingluonou/EInk-Image-Toolkit.git
cd EInk-Image-Toolkit
```
Add dependencies using uv:

```Bash
uv sync
```
Run the application:

```Bash
uv run main.py
```
(Note: Replace main.py with the actual filename of your script if it is different).

🖱️ Interactive Controls
Left Click + Drag: Pan the image inside the crop box.

Scroll Wheel: Zoom in and out.

Shift + Drag: Lock dragging to horizontal or vertical axis.

Ctrl + Scroll Wheel: Fine-tune zooming for pixel-perfect adjustments.

📄 License
This project is licensed under the MIT License.
