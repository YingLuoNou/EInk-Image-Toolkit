import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import numpy as np
from PIL import Image, ImageTk, ImageEnhance
import threading
import os

# ==========================================
# 1. 核心抖动逻辑类
# ==========================================

class EPaperDitheringTool:
    def __init__(self):
        self.palettes = {
            'bw': [(0, 0, 0), (255, 255, 255)],
            '4gray': [(0, 0, 0), (85, 85, 85), (170, 170, 170), (255, 255, 255)],
            '16gray': [(i*17, i*17, i*17) for i in range(16)],
            '6color': [(0, 0, 0), (255, 255, 255), (0, 255, 0), (0, 0, 255), (255, 0, 0), (255, 255, 0)],
            '7color': [(0, 0, 0), (255, 255, 255), (0, 255, 0), (0, 0, 255), (255, 0, 0), (255, 255, 0), (255, 128, 0)]
        }
        
        self.kernel_fs = [(1,0,7/16), (-1,1,3/16), (0,1,5/16), (1,1,1/16)]
        self.kernel_atkinson = [(1,0,1/8), (2,0,1/8), (-1,1,1/8), (0,1,1/8), (1,1,1/8), (0,2,1/8)]
        self.kernel_stucki = [(1,0,8/42),(2,0,4/42),(-2,1,2/42),(-1,1,4/42),(0,1,8/42),(1,1,4/42),(2,1,2/42),(-2,2,1/42),(-1,2,2/42),(0,2,4/42),(1,2,2/42),(2,2,1/42)]
        self.kernel_burkes = [(1,0,8/32),(2,0,4/32),(-2,1,2/32),(-1,1,4/32),(0,1,8/32),(1,1,4/32),(2,1,2/32)]
        self.kernel_sierra = [(1,0,5/32),(2,0,3/32),(-2,1,2/32),(-1,1,4/32),(0,1,5/32),(1,1,4/32),(2,1,2/32),(-1,2,2/32),(0,2,3/32),(1,2,2/32)]
        
        self.kernels = {
            "Floyd-Steinberg": self.kernel_fs,
            "Atkinson": self.kernel_atkinson,
            "Stucki": self.kernel_stucki,
            "Burkes": self.kernel_burkes,
            "Sierra3": self.kernel_sierra
        }

    def enhance_image(self, img, brightness=1.0, contrast=1.0, saturation=1.0, r_fac=1.0, g_fac=1.0, b_fac=1.0):
        if saturation != 1.0: img = ImageEnhance.Color(img).enhance(saturation)
        if brightness != 1.0: img = ImageEnhance.Brightness(img).enhance(brightness)
        if contrast != 1.0: img = ImageEnhance.Contrast(img).enhance(contrast)
        
        if r_fac != 1.0 or g_fac != 1.0 or b_fac != 1.0:
            bands = img.split()
            if len(bands) >= 3:
                r, g, b = bands[0], bands[1], bands[2]
                if r_fac != 1.0: r = r.point(lambda i: min(255, int(i * r_fac)))
                if g_fac != 1.0: g = g.point(lambda i: min(255, int(i * g_fac)))
                if b_fac != 1.0: b = b.point(lambda i: min(255, int(i * b_fac)))
                img = Image.merge('RGBA' if len(bands)==4 else 'RGB', (r, g, b, bands[3] if len(bands)==4 else None)[:len(bands)])
        return img

    def color_distance(self, c1, c2):
        return (int(c1[0])-int(c2[0]))**2 + (int(c1[1])-int(c2[1]))**2 + (int(c1[2])-int(c2[2]))**2
    
    def find_nearest_color(self, pixel, colors):
        nearest = colors[0]
        min_dist = self.color_distance(pixel, colors[0])
        for c in colors[1:]:
            d = self.color_distance(pixel, c)
            if d < min_dist: min_dist = d; nearest = c
        return nearest

    def apply_error_diffusion(self, img_arr, colors, kernel_name='Floyd-Steinberg'):
        h, w = img_arr.shape[:2]
        res = img_arr.copy().astype(np.float32)
        weights = self.kernels.get(kernel_name, self.kernel_fs)
        
        for y in range(h):
            for x in range(w):
                old = res[y, x].copy()
                nearest = self.find_nearest_color(old, colors)
                res[y, x] = nearest
                err = old - nearest
                for dx, dy, wt in weights:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < w and 0 <= ny < h:
                        res[ny, nx] = np.clip(res[ny, nx] + err * wt, 0, 255)
        return res.astype(np.uint8)

    def apply_no_dithering(self, img_arr, colors):
        h, w = img_arr.shape[:2]
        res = np.zeros_like(img_arr)
        for y in range(h):
            for x in range(w):
                res[y, x] = self.find_nearest_color(img_arr[y, x], colors)
        return res
    
    def apply_blue_noise(self, img_arr, colors):
        h, w = img_arr.shape[:2]
        res = img_arr.copy()
        noise = np.random.randint(-50, 50, (h, w, 3))
        noisy_img = np.clip(res.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        for y in range(h):
            for x in range(w):
                res[y, x] = self.find_nearest_color(noisy_img[y, x], colors)
        return res

    def simulate_rgb332(self, img_arr):
        h, w = img_arr.shape[:2]
        res = np.zeros_like(img_arr)
        for y in range(h):
            for x in range(w):
                r, g, b = img_arr[y, x]
                res[y, x] = [(r&0xE0), (g&0xE0), (b&0xC0)]
        return res
    
    def simulate_rgb565(self, img_arr):
        h, w = img_arr.shape[:2]
        res = np.zeros_like(img_arr)
        for y in range(h):
            for x in range(w):
                r, g, b = img_arr[y, x]
                res[y, x] = [(r&0xF8), (g&0xFC), (b&0xF8)]
        return res
    
    def simulate_4096(self, img_arr):
        h, w = img_arr.shape[:2]
        res = np.zeros_like(img_arr)
        for y in range(h):
            for x in range(w):
                r, g, b = img_arr[y, x]
                res[y, x] = [(r&0xF0), (g&0xF0), (b&0xF0)]
        return res

# ==========================================
# 2. 图像转换与导出逻辑
# ==========================================

class ImageToCArrayConverter:
    def __init__(self):
        self.dither_tool = EPaperDitheringTool()
        self.palette_6c_map = [
            ((0, 0, 0),       0x0), 
            ((255, 255, 255), 0x1), 
            ((0, 255, 0),     0x2), 
            ((0, 0, 255),     0x3), 
            ((255, 0, 0),     0x4), 
            ((255, 255, 0),   0x5)  
        ]
        self.palette_7c_map = self.palette_6c_map + [((255, 128, 0), 0x6)]

    def get_palette_by_format(self, fmt_str):
        if "1-bit" in fmt_str or "单色" in fmt_str: return 'bw'
        if "2-bit" in fmt_str or "4灰" in fmt_str: return '4gray'
        if "4-bit" in fmt_str or "16灰" in fmt_str: return '16gray'
        if "6-Color" in fmt_str: return '6color' 
        if "7-Color" in fmt_str: return '7color' 
        return None 

    def _get_index_from_map(self, pixel, mapping):
        min_d = float('inf')
        index = 0x1
        r, g, b = int(pixel[0]), int(pixel[1]), int(pixel[2])
        for (pr, pg, pb), idx in mapping:
            d = (r-pr)**2 + (g-pg)**2 + (b-pb)**2
            if d < min_d: min_d = d; index = idx
            if d == 0: break
        return index

    def _process_scan_order(self, arr, scan_mode, mirror_x, mirror_y):
        if mirror_x: arr = np.fliplr(arr)
        if mirror_y: arr = np.flipud(arr)
        h, w = arr.shape[:2]
        if scan_mode == 1: 
            if len(arr.shape) == 3: arr = np.transpose(arr, (1, 0, 2))
            else: arr = np.transpose(arr)
            return arr, h, w
        return arr, w, h

    def convert_and_export(self, img_arr, fmt, scan_mode, mx, my, swap, name):
        arr, w, h = self._process_scan_order(img_arr, scan_mode, mx, my)
        data_bytes = []
        desc = fmt
        r, g, b = arr[...,0], arr[...,1], arr[...,2]
        
        if "6-Color" in fmt or "7-Color" in fmt:
            flat = arr.reshape(-1, 3)
            target_map = self.palette_6c_map if "6-Color" in fmt else self.palette_7c_map
            indices = [self._get_index_from_map(p, target_map) for p in flat]
            if "Packed" in fmt:
                if swap: desc += " [SWAP]"
                for i in range(0, len(indices), 2):
                    p1 = indices[i]
                    p2 = indices[i+1] if i+1 < len(indices) else 0x1
                    val = (p2 << 4) | (p1 & 0x0F) if swap else (p1 << 4) | (p2 & 0x0F)
                    data_bytes.append(val)
            else:
                data_bytes = indices

        elif "RGB332" in fmt:
            val = ((r.astype(np.uint16) >> 5) << 5) | ((g.astype(np.uint16) >> 5) << 2) | (b.astype(np.uint16) >> 6)
            data_bytes = val.flatten().tolist()
            
        elif "1-bit" in fmt or "单色" in fmt:
            gray = np.dot(arr[...,:3], [0.299, 0.587, 0.114])
            binary = (gray > 127).astype(np.uint8)
            flat = binary.flatten()
            pad = (8 - len(flat)%8)%8
            if pad: flat = np.pad(flat, (0, pad), 'constant')
            data_bytes = np.packbits(flat).tolist()

        elif "2-bit" in fmt or "4灰" in fmt:
            gray = np.dot(arr[...,:3], [0.299, 0.587, 0.114])
            g4 = (gray / 255.0 * 3).astype(np.uint8).flatten()
            for i in range(0, len(g4), 4):
                val = 0
                for j in range(4):
                    if i+j < len(g4): val |= (g4[i+j] << (6 - 2*j))
                data_bytes.append(val)
        
        elif "4-bit" in fmt or "16灰" in fmt:
            gray = np.dot(arr[...,:3], [0.299, 0.587, 0.114])
            g16 = (gray / 255.0 * 15).astype(np.uint8).flatten()
            if "Packed" in fmt:
                 for i in range(0, len(g16), 2):
                    p1 = g16[i]; p2 = g16[i+1] if i+1 < len(g16) else 0
                    data_bytes.append((p1 << 4) | (p2 & 0x0F))
            else: data_bytes = g16.tolist()

        elif "RGB565" in fmt:
            val = ((r.astype(np.uint16) & 0xF8) << 8) | ((g.astype(np.uint16) & 0xFC) << 3) | (b.astype(np.uint16) >> 3)
            for v in val.flatten():
                data_bytes.append((v >> 8) & 0xFF)
                data_bytes.append(v & 0xFF)

        elif "RGB888" in fmt:
            for i in range(len(r.flatten())):
                data_bytes.append(r.flatten()[i])
                data_bytes.append(g.flatten()[i])
                data_bytes.append(b.flatten()[i])

        elif "ARGB8888" in fmt:
             for i in range(len(r.flatten())):
                data_bytes.append(b.flatten()[i])
                data_bytes.append(g.flatten()[i])
                data_bytes.append(r.flatten()[i])
                data_bytes.append(0xFF)
        
        elif "12-bit" in fmt or "4096" in fmt:
            val = ((r.astype(np.uint16) >> 4) << 8) | ((g.astype(np.uint16) >> 4) << 4) | (b.astype(np.uint16) >> 4)
            for v in val.flatten():
                data_bytes.append((v >> 8) & 0xFF)
                data_bytes.append(v & 0xFF)

        return self._generate_c_code(data_bytes, w, h, name, desc), w, h

    def _generate_c_code(self, data, width, height, name, desc):
        c_code = f"// {desc}\n// Size: {width}x{height}\nconst unsigned char {name}[] = {{\n"
        for i in range(0, len(data), 16):
            c_code += "    " + ", ".join([f"0x{b:02X}" for b in data[i:i+16]]) + ",\n"
        return c_code.rstrip(",\n") + "\n};\n"
    
    def save_c_array_to_file(self, c_array, filename):
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(c_array)

# ==========================================
# 3. GUI 界面类
# ==========================================

class EPaperGUI:
    def __init__(self, root):
        self.root = root
        self.root.geometry("1550x950")
        
        self.style = ttk.Style()
        self.style.configure('.', font=('Microsoft YaHei UI', 10))
        self.style.configure('TLabelframe.Label', font=('Microsoft YaHei UI', 11, 'bold'))
        
        self.dither_tool = EPaperDitheringTool()
        self.converter = ImageToCArrayConverter()
        
        # --- 国际化 (i18n) 字典 ---
        self.lang = 'zh'  # 默认中文
        self.T = {
            'zh': {
                'title': "电子纸图像工具 v7.5 (多语言 & 交互裁剪版)",
                'btn_lang': "🌐 English",
                'f1': "1. 图像加载与预处理",
                'btn_load': "📁 加载图片",
                'btn_rot_ccw': "⟲ 左转90°", 'btn_rot_cw': "⟳ 右转90°",
                'btn_flip_h': "↔ 水平翻转", 'btn_flip_v': "↕ 垂直翻转",
                'lbl_unsel': "未选择",
                'f2': "2. 图像增强",
                'sat': "饱和度", 'ct': "对比", 'br': "亮度", 'r': "红R", 'g': "绿G", 'b': "蓝B",
                'btn_reset': "重置参数",
                'f3': "3. 硬件扫描与位序(导出用)",
                'lbl_mode': "模式:",
                'modes': ["1.水平 (Standard)","2.垂直","3.数据水平字节垂直","4.数据垂直字节水平"],
                'chk_mx': "数据镜像(X)", 'chk_my': "数据翻转(Y)", 'chk_swap': "交换高低位 (Swap Nibbles)",
                'f4': "4. 尺寸与算法设置",
                'lbl_dither': "抖动算法:",
                'dithers': ["Floyd-Steinberg", "Atkinson (高对比度)", "Stucki (高清晰度)", "Burkes (均衡)", "Sierra3 (平滑)", "Blue Noise (随机)", "不使用抖动 (Nearest)"],
                'lbl_tw': "目标宽:", 'lbl_th': "高:",
                'btn_fit': "🔍 居中铺满",
                'f5': "5. 导出格式 (自动决定调色板)",
                'fmts': ["GxEPD2 6-Color (Packed E6专用)", "GxEPD2 7-Color (Packed ACeP)", "GxEPD2 7-Color (Standard 1px/byte)", "RGB332 (256色)", "单色 (1-bit)", "4灰 (2-bit)", "16灰 (4-bit)", "4096色 (12-bit)", "16位真彩色 (RGB565)", "24位真彩色 (RGB888)", "32位真彩色 (ARGB8888)"],
                'btn_prev': "⚡ 生成预览", 'btn_exp': "💾 导出C数组",
                'lbl_ready': "就绪",
                'fo': "交互式裁剪 [按住Shift：水平/垂直锁定 | 按住Ctrl+滚轮：精细微调缩放]",
                'fp': "导出预览 (所见即所得)",
                'exp_area': "导出区域:",
                'msg_proc': "处理中...", 'msg_done': "完成:",
                'err_num': "参数必须是数字", 'err_img': "请先加载图片！",
                't_warn': "提示", 't_err': "错误", 't_succ': "成功", 'msg_save': "保存完毕\n"
            },
            'en': {
                'title': "E-Paper Image Tool v7.5 (Bilingual & Interactive)",
                'btn_lang': "🌐 中文",
                'f1': "1. Load & Transform",
                'btn_load': "📁 Load Image",
                'btn_rot_ccw': "⟲ Rotate CCW", 'btn_rot_cw': "⟳ Rotate CW",
                'btn_flip_h': "↔ Flip Horiz", 'btn_flip_v': "↕ Flip Vert",
                'lbl_unsel': "No file selected",
                'f2': "2. Enhancements",
                'sat': "Saturate", 'ct': "Contrast", 'br': "Bright", 'r': "Red(R)", 'g': "Green(G)", 'b': "Blue(B)",
                'btn_reset': "Reset Params",
                'f3': "3. Hardware Scan Mode",
                'lbl_mode': "Mode:",
                'modes': ["1. Horizontal (Std)", "2. Vertical", "3. Data H / Byte V", "4. Data V / Byte H"],
                'chk_mx': "Mirror Data(X)", 'chk_my': "Flip Data(Y)", 'chk_swap': "Swap Nibbles",
                'f4': "4. Size & Dithering",
                'lbl_dither': "Algorithm:",
                'dithers': ["Floyd-Steinberg", "Atkinson (High Contrast)", "Stucki (High Detail)", "Burkes (Balanced)", "Sierra3 (Smooth)", "Blue Noise (Random)", "None (Nearest)"],
                'lbl_tw': "Target W:", 'lbl_th': "H:",
                'btn_fit': "🔍 Center Fit",
                'f5': "5. Export Format",
                'fmts': ["GxEPD2 6-Color (Packed E6)", "GxEPD2 7-Color (Packed ACeP)", "GxEPD2 7-Color (Std 1px/byte)", "RGB332 (256 Colors)", "Monochrome (1-bit)", "4-Grayscale (2-bit)", "16-Grayscale (4-bit)", "4096 Colors (12-bit)", "16-bit TrueColor (RGB565)", "24-bit TrueColor (RGB888)", "32-bit TrueColor (ARGB8888)"],
                'btn_prev': "⚡ Gen Preview", 'btn_exp': "💾 Export C Array",
                'lbl_ready': "Ready",
                'fo': "Interactive Crop [Shift: Lock Axis | Ctrl+Wheel: Fine Zoom]",
                'fp': "Export Preview (WYSIWYG)",
                'exp_area': "Export Area:",
                'msg_proc': "Processing...", 'msg_done': "Done:",
                'err_num': "Parameters must be numbers.", 'err_img': "Please load an image first!",
                't_warn': "Warning", 't_err': "Error", 't_succ': "Success", 'msg_save': "Saved Successfully\n"
            }
        }
        
        self.current_original_image = None
        self.dithered_cache = None
        self.last_dither_params = None
        self.preview_image_cache = None
        self.param_entries = {}
        self.ui_labels = {}
        
        # 交互裁剪状态变量
        self.img_scale = 1.0
        self.img_tx = 0
        self.img_ty = 0
        self.disp_scale = 1.0
        self._drag_start_x = 0
        self._drag_start_y = 0
        self._orig_img_tx = 0
        self._orig_img_ty = 0
        self._drag_axis = None  
        self.is_dragging = False
        self._resize_timer = None
        self._zoom_timer = None
        
        self._setup_ui()
        self._apply_language() # 初始化应用语言
        
    def _setup_ui(self):
        main_paned = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, sashwidth=6, bg='#f0f0f0')
        main_paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        control = ttk.Frame(main_paned, width=380)
        main_paned.add(control, minsize=380)
        
        # 顶部语言切换栏
        top_bar = ttk.Frame(control)
        top_bar.pack(fill=tk.X, pady=(0, 5))
        self.btn_lang = ttk.Button(top_bar, command=self.toggle_lang)
        self.btn_lang.pack(side=tk.RIGHT)
        
        # 1. 加载与预处理
        self.f1 = ttk.LabelFrame(control, padding=10)
        self.f1.pack(fill=tk.X, pady=5)
        self.btn_load = ttk.Button(self.f1, command=self.load_image)
        self.btn_load.pack(fill=tk.X, pady=(0, 5))
        
        f1_btns = ttk.Frame(self.f1)
        f1_btns.pack(fill=tk.X, pady=5)
        f1_btns.columnconfigure(0, weight=1)
        f1_btns.columnconfigure(1, weight=1)
        
        self.btn_rot_ccw = ttk.Button(f1_btns, command=lambda: self.transform_orig("ccw"))
        self.btn_rot_ccw.grid(row=0, column=0, padx=2, pady=2, sticky="ew")
        self.btn_rot_cw = ttk.Button(f1_btns, command=lambda: self.transform_orig("cw"))
        self.btn_rot_cw.grid(row=0, column=1, padx=2, pady=2, sticky="ew")
        self.btn_flip_h = ttk.Button(f1_btns, command=lambda: self.transform_orig("flip_h"))
        self.btn_flip_h.grid(row=1, column=0, padx=2, pady=2, sticky="ew")
        self.btn_flip_v = ttk.Button(f1_btns, command=lambda: self.transform_orig("flip_v"))
        self.btn_flip_v.grid(row=1, column=1, padx=2, pady=2, sticky="ew")
        
        self.lbl_path = ttk.Label(self.f1, wraplength=300, foreground="gray")
        self.lbl_path.pack(pady=5)
        
        # 2. 增强
        self.f2 = ttk.LabelFrame(control, padding=10)
        self.f2.pack(fill=tk.X, pady=5)
        self._create_sliders(self.f2)
        
        # 3. 扫描
        self.f3 = ttk.LabelFrame(control, padding=10)
        self.f3.pack(fill=tk.X, pady=5)
        self.lbl_mode = ttk.Label(self.f3)
        self.lbl_mode.pack(anchor="w")
        self.cb_scan = ttk.Combobox(self.f3, state="readonly")
        self.cb_scan.pack(fill=tk.X)
        fd = ttk.Frame(self.f3); fd.pack(fill=tk.X, pady=5)
        self.var_mx = tk.BooleanVar(); self.var_my = tk.BooleanVar()
        self.var_swap = tk.BooleanVar(value=False)
        self.chk_mx = ttk.Checkbutton(fd, variable=self.var_mx)
        self.chk_mx.pack(side=tk.LEFT)
        self.chk_my = ttk.Checkbutton(fd, variable=self.var_my)
        self.chk_my.pack(side=tk.LEFT, padx=10)
        self.chk_swap = ttk.Checkbutton(self.f3, variable=self.var_swap)
        self.chk_swap.pack(anchor="w", pady=2)

        # 4. 算法设置
        self.f4 = ttk.LabelFrame(control, padding=10)
        self.f4.pack(fill=tk.X, pady=5)
        
        self.lbl_dither = ttk.Label(self.f4)
        self.lbl_dither.pack(anchor="w")
        self.cb_method = ttk.Combobox(self.f4, state="readonly")
        self.cb_method.pack(fill=tk.X, pady=(0, 5))
        
        fd2 = ttk.Frame(self.f4); fd2.pack(fill=tk.X, pady=5)
        self.lbl_tw = ttk.Label(fd2)
        self.lbl_tw.pack(side=tk.LEFT)
        self.ent_w = ttk.Entry(fd2, width=5); self.ent_w.insert(0,"800"); self.ent_w.pack(side=tk.LEFT, padx=2)
        self.lbl_th = ttk.Label(fd2)
        self.lbl_th.pack(side=tk.LEFT)
        self.ent_h = ttk.Entry(fd2, width=5); self.ent_h.insert(0,"480"); self.ent_h.pack(side=tk.LEFT, padx=2)
        
        self.ent_w.bind('<KeyRelease>', lambda e: self._update_canvas_orig())
        self.ent_h.bind('<KeyRelease>', lambda e: self._update_canvas_orig())

        self.btn_fit = ttk.Button(fd2, command=self.fit_image_to_crop)
        self.btn_fit.pack(side=tk.RIGHT, padx=5)
        
        # 5. 格式
        self.f5 = ttk.LabelFrame(control, padding=10)
        self.f5.pack(fill=tk.X)
        self.cb_fmt = ttk.Combobox(self.f5, state="readonly", height=12)
        self.cb_fmt.pack(fill=tk.X, pady=5)
        
        self.btn_prev = ttk.Button(self.f5, command=self.run_preview)
        self.btn_prev.pack(fill=tk.X, pady=5)
        self.btn_save = ttk.Button(self.f5, command=self.save_file, state="disabled")
        self.btn_save.pack(fill=tk.X)
        
        self.lbl_status = ttk.Label(control, foreground="blue")
        self.lbl_status.pack(side=tk.BOTTOM, pady=10)
        
        # 预览区
        prev = ttk.Frame(main_paned); main_paned.add(prev, stretch="always")
        split = tk.PanedWindow(prev, orient=tk.HORIZONTAL, bg="#ccc"); split.pack(fill=tk.BOTH, expand=True)
        
        self.fo = ttk.LabelFrame(split, padding=0)
        split.add(self.fo, stretch="always")
        
        self.cv_orig = tk.Canvas(self.fo, bg="#2b2b2b", cursor="fleur", highlightthickness=0)
        self.cv_orig.pack(fill=tk.BOTH, expand=True)
        
        self.cv_orig.bind("<ButtonPress-1>", self._on_drag_start)
        self.cv_orig.bind("<B1-Motion>", self._on_drag_motion)
        self.cv_orig.bind("<ButtonRelease-1>", self._on_drag_end)
        self.cv_orig.bind("<MouseWheel>", self._on_zoom)
        self.cv_orig.bind("<Button-4>", self._on_zoom)
        self.cv_orig.bind("<Button-5>", self._on_zoom)
        self.cv_orig.bind("<Configure>", lambda e: self._on_resize())

        self.fp = ttk.LabelFrame(split, padding=0); split.add(self.fp, stretch="always")
        self.cv_proc = tk.Label(self.fp, bg="#e0e0e0"); self.cv_proc.pack(fill=tk.BOTH, expand=True)
        self.cv_proc.bind("<Configure>", lambda e: self._on_resize())

    def _create_sliders(self, p):
        def mk(txt_key, vname, d=1.0, to=2.0):
            f = ttk.Frame(p); f.pack(fill=tk.X, pady=1)
            lbl = ttk.Label(f, width=9)
            lbl.pack(side=tk.LEFT)
            self.ui_labels[txt_key] = lbl
            var = tk.DoubleVar(value=d); setattr(self, vname, var)
            ent = ttk.Entry(f, width=5); ent.pack(side=tk.RIGHT); ent.insert(0,f"{d:.1f}")
            self.param_entries[vname] = ent
            s = ttk.Scale(f, from_=0 if 'r' in txt_key or 'g' in txt_key or 'b' in txt_key else 0.5, to=to, variable=var)
            s.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
            s.configure(command=lambda v: [ent.delete(0,tk.END), ent.insert(0,f"{float(v):.2f}")])
            ent.bind('<Return>', lambda e: var.set(float(ent.get())))
            
        mk('sat', "v_sat", 1.0, 3.0)
        mk('ct', "v_ct"); mk('br', "v_br"); mk('r', "v_r"); mk('g', "v_g"); mk('b', "v_b")
        
        self.btn_reset = ttk.Button(p, command=self.reset_params)
        self.btn_reset.pack(fill=tk.X, pady=2)

    # --- i18n 多语言热切换逻辑 ---
    def toggle_lang(self):
        self.lang = 'en' if self.lang == 'zh' else 'zh'
        self._apply_language()

    def _apply_language(self):
        L = self.T[self.lang]
        self.root.title(L['title'])
        self.btn_lang.config(text=L['btn_lang'])
        
        self.f1.config(text=L['f1'])
        self.btn_load.config(text=L['btn_load'])
        self.btn_rot_ccw.config(text=L['btn_rot_ccw'])
        self.btn_rot_cw.config(text=L['btn_rot_cw'])
        self.btn_flip_h.config(text=L['btn_flip_h'])
        self.btn_flip_v.config(text=L['btn_flip_v'])
        
        # 更新状态文本
        if self.lbl_path.cget("text") in [self.T['zh']['lbl_unsel'], self.T['en']['lbl_unsel']]:
            self.lbl_path.config(text=L['lbl_unsel'])
            
        self.f2.config(text=L['f2'])
        for key, lbl in self.ui_labels.items():
            lbl.config(text=L[key])
        self.btn_reset.config(text=L['btn_reset'])
        
        self.f3.config(text=L['f3'])
        self.lbl_mode.config(text=L['lbl_mode'])
        
        idx = self.cb_scan.current()
        self.cb_scan.config(values=L['modes'])
        self.cb_scan.current(max(0, idx))
        
        self.chk_mx.config(text=L['chk_mx'])
        self.chk_my.config(text=L['chk_my'])
        self.chk_swap.config(text=L['chk_swap'])
        
        self.f4.config(text=L['f4'])
        self.lbl_dither.config(text=L['lbl_dither'])
        
        idx = self.cb_method.current()
        self.cb_method.config(values=L['dithers'])
        self.cb_method.current(max(0, idx))
        
        self.lbl_tw.config(text=L['lbl_tw'])
        self.lbl_th.config(text=L['lbl_th'])
        self.btn_fit.config(text=L['btn_fit'])
        
        self.f5.config(text=L['f5'])
        idx = self.cb_fmt.current()
        self.cb_fmt.config(values=L['fmts'])
        self.cb_fmt.current(max(0, idx))
        
        self.btn_prev.config(text=L['btn_prev'])
        self.btn_save.config(text=L['btn_exp'])
        
        if self.lbl_status.cget("text") in [self.T['zh']['lbl_ready'], self.T['en']['lbl_ready']]:
            self.lbl_status.config(text=L['lbl_ready'])
            
        self.fo.config(text=L['fo'])
        self.fp.config(text=L['fp'])
        
        self._update_canvas_orig(fast=True)

    def reset_params(self):
        for k in ["v_sat", "v_ct", "v_br", "v_r", "v_g", "v_b"]:
            getattr(self, k).set(1.0)
            self.param_entries[k].delete(0, tk.END); self.param_entries[k].insert(0,"1.0")

    def load_image(self):
        p = filedialog.askopenfilename(); 
        if not p: return
        self.lbl_path.config(text=os.path.basename(p))
        self.current_original_image = Image.open(p).convert('RGB')
        self.dithered_cache = None; self.last_dither_params = None
        self.fit_image_to_crop()

    def transform_orig(self, mode):
        if not self.current_original_image:
            messagebox.showwarning(self.T[self.lang]['t_warn'], self.T[self.lang]['err_img'])
            return
            
        if mode == "cw":
            self.current_original_image = self.current_original_image.transpose(Image.ROTATE_270)
        elif mode == "ccw":
            self.current_original_image = self.current_original_image.transpose(Image.ROTATE_90)
        elif mode == "flip_h":
            self.current_original_image = self.current_original_image.transpose(Image.FLIP_LEFT_RIGHT)
        elif mode == "flip_v":
            self.current_original_image = self.current_original_image.transpose(Image.FLIP_TOP_BOTTOM)
            
        self.dithered_cache = None
        self.last_dither_params = None
        self.fit_image_to_crop()

    def fit_image_to_crop(self):
        if not self.current_original_image: return
        self.img_tx = 0
        self.img_ty = 0
        try:
            tw, th = int(self.ent_w.get()), int(self.ent_h.get())
        except:
            tw, th = 800, 480
        iw, ih = self.current_original_image.size
        self.img_scale = max(tw / iw, th / ih)
        self._update_canvas_orig(fast=False)

    def _on_drag_start(self, event):
        self._drag_start_x = event.x
        self._drag_start_y = event.y
        self._orig_img_tx = self.img_tx
        self._orig_img_ty = self.img_ty
        self._drag_axis = None  
        self.cv_orig.focus_set()
        self.is_dragging = True

    def _on_drag_motion(self, event):
        if not self.current_original_image or not self.is_dragging: return
        tot_dx = event.x - self._drag_start_x
        tot_dy = event.y - self._drag_start_y
        
        if self.disp_scale > 0:
            is_shift_held = bool(event.state & 0x0001)
            if is_shift_held:
                if self._drag_axis is None:
                    if abs(tot_dx) > 3 or abs(tot_dy) > 3:
                        self._drag_axis = 'x' if abs(tot_dx) > abs(tot_dy) else 'y'
                
                if self._drag_axis == 'x':
                    self.img_tx = self._orig_img_tx + (tot_dx / self.disp_scale)
                    self.img_ty = self._orig_img_ty
                elif self._drag_axis == 'y':
                    self.img_tx = self._orig_img_tx
                    self.img_ty = self._orig_img_ty + (tot_dy / self.disp_scale)
            else:
                self._drag_axis = None
                self.img_tx = self._orig_img_tx + (tot_dx / self.disp_scale)
                self.img_ty = self._orig_img_ty + (tot_dy / self.disp_scale)

            self._update_canvas_orig(fast=True)

    def _on_drag_end(self, event):
        self.is_dragging = False
        self._drag_axis = None
        self._update_canvas_orig(fast=False)

    def _on_zoom(self, event):
        if not self.current_original_image: return
        
        if hasattr(event, 'delta') and event.delta != 0:
            zoom_in = event.delta > 0
        else:
            zoom_in = event.num == 4

        is_ctrl_held = bool(event.state & 0x0004)
        zoom_factor = 1.02 if zoom_in else 0.9804 if is_ctrl_held else (1.1 if zoom_in else 0.909)

        self.img_scale *= zoom_factor
        self._update_canvas_orig(fast=True)
        
        if self._zoom_timer: self.root.after_cancel(self._zoom_timer)
        self._zoom_timer = self.root.after(300, lambda: self._update_canvas_orig(fast=False))

    def _on_resize(self):
        if self._resize_timer: self.root.after_cancel(self._resize_timer)
        self._resize_timer = self.root.after(100, self._refresh_ui)

    def _refresh_ui(self):
        self._update_canvas_orig()
        if self.preview_image_cache: 
            self._show_preview(self.preview_image_cache, self.cv_proc)

    def _update_canvas_orig(self, fast=False):
        if not self.current_original_image: return
        cw, ch = self.cv_orig.winfo_width(), self.cv_orig.winfo_height()
        if cw < 10 or ch < 10: return

        try: tw, th = int(self.ent_w.get()), int(self.ent_h.get())
        except: tw, th = 800, 480

        margin = 30
        self.disp_scale = min((cw - margin * 2) / tw, (ch - margin * 2) / th)

        cx, cy = cw / 2, ch / 2
        box_w, box_h = tw * self.disp_scale, th * self.disp_scale
        
        left, top = cx - box_w / 2, cy - box_h / 2
        right, bottom = cx + box_w / 2, cy + box_h / 2

        iw, ih = self.current_original_image.size
        draw_w = int(iw * self.img_scale * self.disp_scale)
        draw_h = int(ih * self.img_scale * self.disp_scale)
        
        draw_x = cx + self.img_tx * self.disp_scale
        draw_y = cy + self.img_ty * self.disp_scale

        resample_method = Image.NEAREST if fast else Image.LANCZOS
        img_disp = self.current_original_image.resize((max(1, draw_w), max(1, draw_h)), resample_method)
        self.tk_orig_img = ImageTk.PhotoImage(img_disp)

        self.cv_orig.delete("all")
        self.cv_orig.create_image(draw_x, draw_y, image=self.tk_orig_img, anchor=tk.CENTER)
        self.cv_orig.create_rectangle(0, 0, cw, top, fill="#111", outline="", stipple="gray50")
        self.cv_orig.create_rectangle(0, bottom, cw, ch, fill="#111", outline="", stipple="gray50")
        self.cv_orig.create_rectangle(0, top, left, bottom, fill="#111", outline="", stipple="gray50")
        self.cv_orig.create_rectangle(right, top, cw, bottom, fill="#111", outline="", stipple="gray50")
        self.cv_orig.create_rectangle(left, top, right, bottom, outline="#ff3333", width=2, dash=(5, 5))
        
        txt_area = f"{self.T[self.lang]['exp_area']} {tw} x {th}"
        self.cv_orig.create_text(left, top - 12, text=txt_area, fill="#ff3333", anchor="w", font=("", 9, "bold"))

    def _show_preview(self, img, lbl):
        w, h = lbl.winfo_width(), lbl.winfo_height()
        if w<10 or h<10: return
        scale = min(w/img.width, h/img.height) * 0.95
        nw, nh = max(1, int(img.width*scale)), max(1, int(img.height*scale))
        tk_img = ImageTk.PhotoImage(img.resize((nw, nh), Image.NEAREST if scale>1 else Image.LANCZOS))
        lbl.config(image=tk_img); lbl.image = tk_img

    def run_preview(self):
        if not self.current_original_image: return
        self.lbl_status.config(text=self.T[self.lang]['msg_proc'])
        
        try:
            for vname, ent in self.param_entries.items():
                getattr(self, vname).set(float(ent.get()))
        except ValueError:
            messagebox.showerror(self.T[self.lang]['t_err'], self.T[self.lang]['err_num'])
            return

        self.root.update()
        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self):
        try:
            tw, th = int(self.ent_w.get()), int(self.ent_h.get())
            fmt = self.cb_fmt.get()
            method_str = self.cb_method.get().split()[0]
            enh_params = (self.v_br.get(), self.v_ct.get(), self.v_sat.get(), self.v_r.get(), self.v_g.get(), self.v_b.get())
            
            target_palette_key = self.converter.get_palette_by_format(fmt)
            current_params = (enh_params, tw, th, method_str, target_palette_key, self.img_scale, self.img_tx, self.img_ty)
            
            if self.dithered_cache is not None and current_params == self.last_dither_params:
                processed_arr = self.dithered_cache
            else:
                img = self.current_original_image.copy()
                iw, ih = img.size
                
                scaled_w, scaled_h = int(iw * self.img_scale), int(ih * self.img_scale)
                img_scaled = img.resize((max(1, scaled_w), max(1, scaled_h)), Image.LANCZOS)
                
                final_canvas = Image.new("RGB", (tw, th), (255, 255, 255))
                paste_x = int(tw / 2 + self.img_tx - scaled_w / 2)
                paste_y = int(th / 2 + self.img_ty - scaled_h / 2)
                final_canvas.paste(img_scaled, (paste_x, paste_y))
                
                img_enhanced = self.dither_tool.enhance_image(final_canvas, *enh_params)
                arr = np.array(img_enhanced)
                
                if target_palette_key is not None:
                    pal = self.dither_tool.palettes[target_palette_key]
                    if "None" in method_str or "不使用" in method_str:
                        processed_arr = self.dither_tool.apply_no_dithering(arr, pal)
                    elif "Blue" in method_str:
                        processed_arr = self.dither_tool.apply_blue_noise(arr, pal)
                    else:
                        processed_arr = self.dither_tool.apply_error_diffusion(arr, pal, method_str)
                else:
                    processed_arr = arr
                
                self.dithered_cache = processed_arr; self.last_dither_params = current_params

            self.current_processed_array = processed_arr
            preview_arr = processed_arr.copy()
            if "RGB332" in fmt: preview_arr = self.dither_tool.simulate_rgb332(preview_arr)
            elif "RGB565" in fmt: preview_arr = self.dither_tool.simulate_rgb565(preview_arr)
            elif "4096" in fmt or "12-bit" in fmt: preview_arr = self.dither_tool.simulate_4096(preview_arr)
            
            self.preview_image_cache = Image.fromarray(preview_arr)
            self.root.after(0, self._done)
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror(self.T[self.lang]['t_err'], str(e)))

    def _done(self):
        self._refresh_ui(); self.btn_save.config(state="normal")
        h, w = self.current_processed_array.shape[:2]
        self.lbl_status.config(text=f"{self.T[self.lang]['msg_done']} {w}x{h}")

    def save_file(self):
        p = filedialog.asksaveasfilename(defaultextension=".c", filetypes=[("C Source", "*.c")])
        if not p: return
        try:
            name = os.path.splitext(os.path.basename(p))[0].replace(" ","_")
            if name[0].isdigit(): name="_"+name
            fmt = self.cb_fmt.get()
            mode = self.cb_scan.current()
            mx, my = self.var_mx.get(), self.var_my.get()
            swap = self.var_swap.get()
            code, w, h = self.converter.convert_and_export(
                self.current_processed_array, fmt, mode, mx, my, swap, name
            )
            self.converter.save_c_array_to_file(code, p)
            messagebox.showinfo(self.T[self.lang]['t_succ'], f"{self.T[self.lang]['msg_save']}{w}x{h}\n{fmt}")
        except Exception as e:
            messagebox.showerror(self.T[self.lang]['t_err'], str(e))

if __name__ == "__main__":
    root = tk.Tk()
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except: pass
    app = EPaperGUI(root)
    root.mainloop()