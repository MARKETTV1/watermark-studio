import tkinter as tk
from tkinter import ttk, filedialog, colorchooser, messagebox, font
from PIL import Image, ImageDraw, ImageFont, ImageTk, ImageFilter
import os
import math
import json


CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".watermark_config.json")

# ── default settings ──────────────────────────────────────────────
DEFAULTS = {
    "watermark_text": "© My Watermark",
    "font_size": 48,
    "opacity": 128,
    "color": "#FFFFFF",
    "position": "bottom-right",
    "padding": 30,
    "angle": 0,
    "shadow": True,
    "repeat": False,
    "repeat_gap": 200,
}


def load_config():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {**DEFAULTS, **data}
    except Exception:
        pass
    return dict(DEFAULTS)


def save_config(cfg):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# ── watermark engine ──────────────────────────────────────────────
def apply_watermark(img: Image.Image, cfg: dict) -> Image.Image:
    result = img.convert("RGBA")
    w, h = result.size

    # parse color + opacity
    hex_col = cfg["color"].lstrip("#")
    r, g, b = tuple(int(hex_col[i:i+2], 16) for i in (0, 2, 4))
    alpha = int(cfg["opacity"])

    # try to load a nice font
    font_obj = None
    font_size = int(cfg["font_size"])
    for fname in ["arialbd.ttf", "arial.ttf", "calibrib.ttf", "calibri.ttf",
                  "segoeui.ttf", "tahoma.ttf", "verdana.ttf"]:
        try:
            font_obj = ImageFont.truetype(fname, font_size)
            break
        except Exception:
            pass
    if font_obj is None:
        font_obj = ImageFont.load_default()

    text = cfg["watermark_text"]

    def make_text_layer(size, pos_offset=(0, 0)):
        layer = Image.new("RGBA", size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer)
        bbox = draw.textbbox((0, 0), text, font=font_obj)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        return layer, draw, tw, th

    pad = int(cfg["padding"])
    angle = int(cfg["angle"])

    if cfg.get("repeat"):
        gap = int(cfg.get("repeat_gap", 200))
        overlay = Image.new("RGBA", result.size, (0, 0, 0, 0))
        draw_ov = ImageDraw.Draw(overlay)
        for y in range(-h, h * 2, gap):
            for x in range(-w, w * 2, gap):
                if cfg.get("shadow"):
                    draw_ov.text((x + 2, y + 2), text, font=font_obj,
                                 fill=(0, 0, 0, alpha // 2))
                draw_ov.text((x, y), text, font=font_obj,
                             fill=(r, g, b, alpha))
        if angle != 0:
            overlay = overlay.rotate(angle, expand=False)
        result = Image.alpha_composite(result, overlay)
    else:
        # single placement
        tmp_layer = Image.new("RGBA", result.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(tmp_layer)
        bbox = draw.textbbox((0, 0), text, font=font_obj)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]

        pos_key = cfg["position"]
        if pos_key == "top-left":
            x, y = pad, pad
        elif pos_key == "top-center":
            x, y = (w - tw) // 2, pad
        elif pos_key == "top-right":
            x, y = w - tw - pad, pad
        elif pos_key == "center":
            x, y = (w - tw) // 2, (h - th) // 2
        elif pos_key == "bottom-left":
            x, y = pad, h - th - pad
        elif pos_key == "bottom-center":
            x, y = (w - tw) // 2, h - th - pad
        elif pos_key == "bottom-right":
            x, y = w - tw - pad, h - th - pad
        else:
            x, y = w - tw - pad, h - th - pad

        if cfg.get("shadow"):
            draw.text((x + 2, y + 2), text, font=font_obj,
                      fill=(0, 0, 0, alpha // 2))
        draw.text((x, y), text, font=font_obj, fill=(r, g, b, alpha))

        if angle != 0:
            txt_crop = tmp_layer.crop((x - 10, y - 10, x + tw + 10, y + th + 10))
            txt_rot = txt_crop.rotate(angle, expand=True)
            tmp_layer = Image.new("RGBA", result.size, (0, 0, 0, 0))
            tmp_layer.paste(txt_rot, (x - 10, y - 10))

        result = Image.alpha_composite(result, tmp_layer)

    return result.convert("RGB")


# ── main GUI ──────────────────────────────────────────────────────
class WatermarkApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.cfg = load_config()
        self.source_image: Image.Image | None = None
        self.preview_photo = None
        self.output_files = []

        self.title("🖼️  Watermark Studio")
        self.geometry("1100x720")
        self.minsize(900, 600)
        self.configure(bg="#0F0F13")
        self._apply_style()
        self._build_ui()
        self._refresh_preview()

    # ── style ──────────────────────────────────────────────────────
    def _apply_style(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        bg = "#0F0F13"
        panel = "#1A1A23"
        accent = "#6C63FF"
        text_col = "#E8E8F0"
        style.configure(".", background=bg, foreground=text_col,
                        fieldbackground=panel, bordercolor="#2A2A3A",
                        troughcolor=panel, font=("Segoe UI", 10))
        style.configure("TFrame", background=bg)
        style.configure("Panel.TFrame", background=panel)
        style.configure("TLabel", background=bg, foreground=text_col)
        style.configure("Panel.TLabel", background=panel, foreground=text_col)
        style.configure("TButton", background=accent, foreground="white",
                        relief="flat", borderwidth=0, padding=(12, 6))
        style.map("TButton",
                  background=[("active", "#7C74FF"), ("pressed", "#5A52EE")])
        style.configure("Ghost.TButton", background=panel, foreground=text_col)
        style.map("Ghost.TButton",
                  background=[("active", "#2A2A3A"), ("pressed", "#1A1A2A")])
        style.configure("TEntry", fieldbackground="#1A1A23",
                        foreground=text_col, insertcolor=text_col,
                        bordercolor="#2A2A3A", relief="flat")
        style.configure("TScale", background=bg, troughcolor=panel,
                        sliderlength=18, sliderrelief="flat")
        style.configure("TCombobox", fieldbackground=panel,
                        foreground=text_col, background=panel,
                        selectbackground=accent, selectforeground="white")
        style.map("TCombobox",
                  fieldbackground=[("readonly", panel)],
                  selectbackground=[("readonly", panel)])
        style.configure("TCheckbutton", background=panel, foreground=text_col)
        style.map("TCheckbutton",
                  background=[("active", panel)],
                  indicatorcolor=[("selected", accent), ("!selected", "#2A2A3A")])

    # ── build UI ───────────────────────────────────────────────────
    def _build_ui(self):
        # Header
        hdr = tk.Frame(self, bg="#0F0F13", pady=12)
        hdr.pack(fill="x", padx=20)
        tk.Label(hdr, text="Watermark Studio",
                 bg="#0F0F13", fg="#6C63FF",
                 font=("Segoe UI", 22, "bold")).pack(side="left")
        tk.Label(hdr, text="  — Add your personal stamp to any image",
                 bg="#0F0F13", fg="#555566",
                 font=("Segoe UI", 11)).pack(side="left", pady=4)

        # Main layout
        main = tk.Frame(self, bg="#0F0F13")
        main.pack(fill="both", expand=True, padx=20, pady=(0, 16))
        main.columnconfigure(0, weight=0)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(0, weight=1)

        self._build_sidebar(main)
        self._build_preview_panel(main)

    def _build_sidebar(self, parent):
        sb = tk.Frame(parent, bg="#1A1A23", width=300,
                      highlightthickness=1, highlightbackground="#2A2A3A")
        sb.grid(row=0, column=0, sticky="ns", padx=(0, 12))
        sb.pack_propagate(False)

        # scroll canvas inside sidebar
        canvas = tk.Canvas(sb, bg="#1A1A23", bd=0,
                           highlightthickness=0, width=280)
        sb_scroll = ttk.Scrollbar(sb, orient="vertical",
                                  command=canvas.yview)
        canvas.configure(yscrollcommand=sb_scroll.set)
        sb_scroll.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        inner = tk.Frame(canvas, bg="#1A1A23")
        win_id = canvas.create_window((0, 0), window=inner, anchor="nw")

        def on_resize(e):
            canvas.itemconfig(win_id, width=e.width)
        canvas.bind("<Configure>", on_resize)

        def on_frame_configure(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
        inner.bind("<Configure>", on_frame_configure)

        p = 16
        # ─── Section: Image ───────────────────────────────────────
        self._section(inner, "📁  Image")
        ttk.Button(inner, text="Choose Image…",
                   command=self._choose_image).pack(
            fill="x", padx=p, pady=(0, 4))
        ttk.Button(inner, text="Batch Folder…", style="Ghost.TButton",
                   command=self._batch_folder).pack(
            fill="x", padx=p, pady=(0, 12))

        # ─── Section: Watermark Text ──────────────────────────────
        self._section(inner, "✏️  Watermark Text")
        self._wm_text_var = tk.StringVar(value=self.cfg["watermark_text"])
        entry = ttk.Entry(inner, textvariable=self._wm_text_var)
        entry.pack(fill="x", padx=p, pady=(0, 12))
        self._wm_text_var.trace_add("write", lambda *_: self._refresh_preview())

        # ─── Section: Appearance ──────────────────────────────────
        self._section(inner, "🎨  Appearance")

        # Color
        tk.Label(inner, text="Color", bg="#1A1A23", fg="#888899",
                 font=("Segoe UI", 9)).pack(anchor="w", padx=p)
        color_row = tk.Frame(inner, bg="#1A1A23")
        color_row.pack(fill="x", padx=p, pady=(2, 8))
        self._color_btn = tk.Button(color_row, bg=self.cfg["color"],
                                    width=4, relief="flat", cursor="hand2",
                                    command=self._pick_color)
        self._color_btn.pack(side="left", padx=(0, 8))
        self._color_label = tk.Label(color_row, text=self.cfg["color"],
                                     bg="#1A1A23", fg="#E8E8F0",
                                     font=("Consolas", 10))
        self._color_label.pack(side="left")

        # Font size
        self._font_size_var = tk.IntVar(value=self.cfg["font_size"])
        self._slider(inner, "Font Size", self._font_size_var, 12, 200)

        # Opacity
        self._opacity_var = tk.IntVar(value=self.cfg["opacity"])
        self._slider(inner, "Opacity", self._opacity_var, 0, 255)

        # Angle
        self._angle_var = tk.IntVar(value=self.cfg["angle"])
        self._slider(inner, "Angle", self._angle_var, -180, 180)

        # ─── Section: Position ────────────────────────────────────
        self._section(inner, "📍  Position")
        positions = ["top-left", "top-center", "top-right",
                     "center",
                     "bottom-left", "bottom-center", "bottom-right"]
        self._pos_var = tk.StringVar(value=self.cfg["position"])
        pos_combo = ttk.Combobox(inner, textvariable=self._pos_var,
                                 values=positions, state="readonly")
        pos_combo.pack(fill="x", padx=p, pady=(0, 6))
        self._pos_var.trace_add("write", lambda *_: self._refresh_preview())

        self._padding_var = tk.IntVar(value=self.cfg["padding"])
        self._slider(inner, "Padding", self._padding_var, 0, 150)

        # ─── Section: Effects ─────────────────────────────────────
        self._section(inner, "✨  Effects")
        self._shadow_var = tk.BooleanVar(value=self.cfg["shadow"])
        ttk.Checkbutton(inner, text="Drop Shadow",
                        variable=self._shadow_var,
                        command=self._refresh_preview).pack(
            anchor="w", padx=p, pady=(0, 4))

        self._repeat_var = tk.BooleanVar(value=self.cfg["repeat"])
        ttk.Checkbutton(inner, text="Repeat (Tile)",
                        variable=self._repeat_var,
                        command=self._refresh_preview).pack(
            anchor="w", padx=p, pady=(0, 4))

        self._gap_var = tk.IntVar(value=self.cfg.get("repeat_gap", 200))
        self._slider(inner, "Tile Gap", self._gap_var, 50, 400)

        # ─── Save button ──────────────────────────────────────────
        tk.Frame(inner, bg="#1A1A23", height=16).pack()
        ttk.Button(inner, text="💾  Save Image",
                   command=self._save_image).pack(
            fill="x", padx=p, pady=(0, 4))
        ttk.Button(inner, text="🔄  Reset Settings", style="Ghost.TButton",
                   command=self._reset).pack(
            fill="x", padx=p, pady=(0, 20))

    def _section(self, parent, title):
        f = tk.Frame(parent, bg="#1A1A23")
        f.pack(fill="x", padx=12, pady=(14, 4))
        tk.Label(f, text=title, bg="#1A1A23", fg="#6C63FF",
                 font=("Segoe UI", 10, "bold")).pack(side="left")
        tk.Frame(f, bg="#2A2A3A", height=1).pack(
            side="left", fill="x", expand=True, padx=(8, 0), pady=6)

    def _slider(self, parent, label, var, from_, to_):
        row = tk.Frame(parent, bg="#1A1A23")
        row.pack(fill="x", padx=16, pady=(0, 6))
        tk.Label(row, text=label, bg="#1A1A23", fg="#888899",
                 font=("Segoe UI", 9), width=10, anchor="w").pack(side="left")
        val_lbl = tk.Label(row, textvariable=var, bg="#1A1A23",
                           fg="#E8E8F0", font=("Consolas", 9), width=5)
        val_lbl.pack(side="right")
        sl = ttk.Scale(row, from_=from_, to=to_, variable=var,
                       orient="horizontal",
                       command=lambda _: (var.set(int(float(var.get()))),
                                          self._refresh_preview()))
        sl.pack(side="left", fill="x", expand=True, padx=(4, 4))

    def _build_preview_panel(self, parent):
        pnl = tk.Frame(parent, bg="#0F0F13")
        pnl.grid(row=0, column=1, sticky="nsew")
        pnl.rowconfigure(0, weight=1)
        pnl.columnconfigure(0, weight=1)

        tk.Label(pnl, text="Preview", bg="#0F0F13", fg="#444455",
                 font=("Segoe UI", 9)).pack(anchor="nw")

        self._canvas = tk.Canvas(pnl, bg="#111118",
                                 highlightthickness=1,
                                 highlightbackground="#2A2A3A",
                                 cursor="crosshair")
        self._canvas.pack(fill="both", expand=True)
        self._canvas.bind("<Configure>", lambda _: self._refresh_preview())

        # status bar
        self._status = tk.StringVar(value="Open an image to begin…")
        tk.Label(pnl, textvariable=self._status,
                 bg="#0F0F13", fg="#555566",
                 font=("Segoe UI", 9), anchor="w").pack(
            fill="x", pady=(4, 0))

    # ── helpers ────────────────────────────────────────────────────
    def _current_cfg(self):
        return {
            "watermark_text": self._wm_text_var.get(),
            "font_size": self._font_size_var.get(),
            "opacity": self._opacity_var.get(),
            "color": self.cfg["color"],
            "position": self._pos_var.get(),
            "padding": self._padding_var.get(),
            "angle": self._angle_var.get(),
            "shadow": self._shadow_var.get(),
            "repeat": self._repeat_var.get(),
            "repeat_gap": self._gap_var.get(),
        }

    def _refresh_preview(self):
        c = self._canvas
        cw, ch = c.winfo_width(), c.winfo_height()
        if cw < 10 or ch < 10:
            return
        c.delete("all")

        if self.source_image is None:
            # placeholder
            c.create_text(cw // 2, ch // 2,
                          text="🖼️\n\nDrag & drop or click\n'Choose Image'",
                          fill="#333344", font=("Segoe UI", 14),
                          justify="center")
            return

        cfg = self._current_cfg()
        try:
            watermarked = apply_watermark(self.source_image, cfg)
        except Exception as e:
            c.create_text(cw // 2, ch // 2, text=f"Error:\n{e}",
                          fill="#FF6666", font=("Segoe UI", 11))
            return

        # fit to canvas
        iw, ih = watermarked.size
        scale = min(cw / iw, ch / ih, 1.0)
        nw, nh = int(iw * scale), int(ih * scale)
        preview = watermarked.resize((nw, nh), Image.LANCZOS)
        self.preview_photo = ImageTk.PhotoImage(preview)
        x0 = (cw - nw) // 2
        y0 = (ch - nh) // 2
        c.create_image(x0, y0, anchor="nw", image=self.preview_photo)

        # info
        self._status.set(
            f"{iw} × {ih} px  |  Scale: {scale*100:.0f}%  "
            f"|  Text: \"{cfg['watermark_text']}\"  "
            f"|  Opacity: {cfg['opacity']}/255"
        )

    def _pick_color(self):
        col = colorchooser.askcolor(color=self.cfg["color"], title="Pick color")[1]
        if col:
            self.cfg["color"] = col
            self._color_btn.configure(bg=col)
            self._color_label.configure(text=col)
            self._refresh_preview()

    def _choose_image(self):
        path = filedialog.askopenfilename(
            title="Choose Image",
            filetypes=[("Images", "*.jpg *.jpeg *.png *.bmp *.webp *.tiff"),
                       ("All files", "*.*")])
        if path:
            self._load_image(path)

    def _load_image(self, path):
        try:
            self.source_image = Image.open(path).convert("RGBA")
            self._status.set(f"Loaded: {os.path.basename(path)}")
            self._refresh_preview()
        except Exception as e:
            messagebox.showerror("Error", f"Cannot open image:\n{e}")

    def _batch_folder(self):
        folder = filedialog.askdirectory(title="Select Folder with Images")
        if not folder:
            return
        out_dir = os.path.join(folder, "watermarked")
        os.makedirs(out_dir, exist_ok=True)
        cfg = self._current_cfg()
        exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tiff"}
        files = [f for f in os.listdir(folder)
                 if os.path.splitext(f)[1].lower() in exts]
        if not files:
            messagebox.showinfo("Batch", "No images found in folder.")
            return
        done = 0
        for fname in files:
            try:
                img = Image.open(os.path.join(folder, fname)).convert("RGBA")
                result = apply_watermark(img, cfg)
                base, _ = os.path.splitext(fname)
                result.save(os.path.join(out_dir, base + "_wm.jpg"),
                            "JPEG", quality=95)
                done += 1
            except Exception:
                pass
        messagebox.showinfo(
            "Batch Done",
            f"✅ {done}/{len(files)} images saved to:\n{out_dir}")

    def _save_image(self):
        if self.source_image is None:
            messagebox.showwarning("No Image", "Please open an image first.")
            return
        path = filedialog.asksaveasfilename(
            title="Save As",
            defaultextension=".jpg",
            filetypes=[("JPEG", "*.jpg"), ("PNG", "*.png"),
                       ("All files", "*.*")])
        if not path:
            return
        cfg = self._current_cfg()
        try:
            result = apply_watermark(self.source_image, cfg)
            ext = os.path.splitext(path)[1].lower()
            if ext == ".png":
                result.save(path, "PNG")
            else:
                result.save(path, "JPEG", quality=95)
            save_config(cfg)
            messagebox.showinfo("Saved", f"✅ Image saved!\n{path}")
        except Exception as e:
            messagebox.showerror("Error", f"Could not save:\n{e}")

    def _reset(self):
        self.cfg = dict(DEFAULTS)
        self._wm_text_var.set(DEFAULTS["watermark_text"])
        self._font_size_var.set(DEFAULTS["font_size"])
        self._opacity_var.set(DEFAULTS["opacity"])
        self._angle_var.set(DEFAULTS["angle"])
        self._padding_var.set(DEFAULTS["padding"])
        self._pos_var.set(DEFAULTS["position"])
        self._shadow_var.set(DEFAULTS["shadow"])
        self._repeat_var.set(DEFAULTS["repeat"])
        self._gap_var.set(DEFAULTS["repeat_gap"])
        self.cfg["color"] = DEFAULTS["color"]
        self._color_btn.configure(bg=DEFAULTS["color"])
        self._color_label.configure(text=DEFAULTS["color"])
        self._refresh_preview()


if __name__ == "__main__":
    app = WatermarkApp()
    app.mainloop()
