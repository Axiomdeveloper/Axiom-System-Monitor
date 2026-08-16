#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Axiom System Monitor - مانیتور حرفه‌ای سیستم
یک برنامه مانیتورینگ سیستم با رابط کاربری کاملاً فارسی و راست‌چین.

اجرا:
    python main.py

تکنولوژی‌ها: Python, Tkinter, ttk, psutil
"""

import platform
import socket
import time
import tkinter as tk
from collections import deque
from datetime import datetime
from tkinter import font as tkfont
from tkinter import messagebox, ttk

try:
    import psutil
except ImportError:
    raise SystemExit(
        "کتابخانه psutil نصب نیست.\n"
        "لطفاً با دستور زیر آن را نصب کنید:\n"
        "pip install -r requirements.txt"
    )

APP_NAME_FA = "Axiom System Monitor"
APP_SUBTITLE_FA = "مانیتور حرفه‌ای سیستم"

# ---------------------------------------------------------------------------
# رنگ‌بندی (Dark Mode) و تنظیمات ظاهری
# ---------------------------------------------------------------------------
DARK = {
    "bg": "#0f1420",
    "bg_alt": "#131a2a",
    "card": "#171f33",
    "card_hover": "#1c2540",
    "border": "#232d47",
    "accent": "#6d8cff",
    "accent_soft": "#2a3560",
    "text": "#e7ebf7",
    "text_dim": "#8b93ab",
    "success": "#39d98a",
    "warning": "#ffb454",
    "danger": "#ff6b6b",
    "cpu": "#6d8cff",
    "ram": "#39d98a",
    "net_down": "#ffb454",
    "net_up": "#ff6b9d",
}

LIGHT = {
    "bg": "#f2f4f9",
    "bg_alt": "#e7eaf3",
    "card": "#ffffff",
    "card_hover": "#eef1fb",
    "border": "#dde1ee",
    "accent": "#3b5bdb",
    "accent_soft": "#dbe4ff",
    "text": "#1b2233",
    "text_dim": "#6b7280",
    "success": "#12b76a",
    "warning": "#f79009",
    "danger": "#e03131",
    "cpu": "#3b5bdb",
    "ram": "#12b76a",
    "net_down": "#f79009",
    "net_up": "#e8449e",
}

NOT_AVAILABLE = "در دسترس نیست"
DATA_ERROR = "اطلاعات قابل دریافت نیست"

PREFERRED_FONTS = ["Vazirmatn", "Vazir", "Tahoma", "B Nazanin", "Segoe UI", "Arial"]


def human_bytes(n):
    """تبدیل بایت به واحد خوانا"""
    try:
        n = float(n)
    except (TypeError, ValueError):
        return NOT_AVAILABLE
    for unit in ["B", "KB", "MB", "GB", "TB", "PB"]:
        if n < 1024.0:
            return f"{n:.1f} {unit}"
        n /= 1024.0
    return f"{n:.1f} EB"


def human_speed(bytes_per_sec):
    return human_bytes(bytes_per_sec) + "/s"


def human_uptime(seconds):
    try:
        seconds = int(seconds)
    except (TypeError, ValueError):
        return NOT_AVAILABLE
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    parts = []
    if days:
        parts.append(f"{days} روز")
    if hours:
        parts.append(f"{hours} ساعت")
    parts.append(f"{minutes} دقیقه")
    return " و ".join(parts)


def safe_call(func, default=None):
    """اجرای امن یک تابع؛ در صورت خطا مقدار پیش‌فرض برمی‌گرداند"""
    try:
        return func()
    except Exception:
        return default


# ---------------------------------------------------------------------------
# ویجت نمودار زنده و سبک (Canvas ساده - بدون کتابخانه اضافی)
# ---------------------------------------------------------------------------
class LiveLineChart(tk.Canvas):
    def __init__(self, master, colors, line_color, max_points=60, y_max=100,
                 unit="%", height=110, **kwargs):
        super().__init__(master, height=height, highlightthickness=0,
                          bg=colors["card"], **kwargs)
        self.colors = colors
        self.line_color = line_color
        self.max_points = max_points
        self.y_max = y_max
        self.unit = unit
        self.data = deque([0] * max_points, maxlen=max_points)
        self.bind("<Configure>", lambda e: self.redraw())

    def set_colors(self, colors):
        self.colors = colors
        self.configure(bg=colors["card"])

    def push(self, value):
        try:
            value = float(value)
        except (TypeError, ValueError):
            value = 0
        if self.y_max and value > self.y_max:
            # مقیاس پویا برای نمودارهایی مثل شبکه
            self.y_max = value * 1.2
        self.data.append(value)
        self.redraw()

    def redraw(self):
        self.delete("all")
        w = self.winfo_width() or 300
        h = self.winfo_height() or 110
        pad = 6
        # خطوط راهنما
        for i in range(1, 4):
            y = pad + (h - 2 * pad) * i / 4
            self.create_line(pad, y, w - pad, y, fill=self.colors["border"], width=1)

        n = len(self.data)
        if n < 2:
            return
        y_max = max(self.y_max, max(self.data) if self.data else 1, 1)
        step_x = (w - 2 * pad) / (n - 1)
        points = []
        for i, val in enumerate(self.data):
            x = pad + i * step_x
            ratio = min(val / y_max, 1.0) if y_max else 0
            y = h - pad - ratio * (h - 2 * pad)
            points.extend([x, y])

        if len(points) >= 4:
            self.create_line(*points, fill=self.line_color, width=2, smooth=True)
            # ناحیه زیر نمودار
            fill_points = [pad, h - pad] + points + [w - pad, h - pad]
            self.create_polygon(*fill_points, fill=self.line_color, stipple="gray25",
                                 outline="")

        last_val = self.data[-1]
        label = f"{last_val:.0f}{self.unit}" if self.unit == "%" else human_speed(last_val)
        self.create_text(w - pad - 4, pad + 8, text=label, anchor="e",
                          fill=self.colors["text"], font=("Vazirmatn", 9))


# ---------------------------------------------------------------------------
# کارت اطلاعاتی
# ---------------------------------------------------------------------------
class InfoCard(tk.Frame):
    def __init__(self, master, colors, title, base_font, **kwargs):
        super().__init__(master, bg=colors["card"], highlightbackground=colors["border"],
                          highlightthickness=1, **kwargs)
        self.colors = colors
        self.base_font = base_font
        self.title_lbl = tk.Label(self, text=title, bg=colors["card"], fg=colors["text_dim"],
                                   font=(base_font, 11, "bold"), anchor="e", justify="right")
        self.title_lbl.pack(fill="x", padx=14, pady=(12, 2))
        self.body = tk.Frame(self, bg=colors["card"])
        self.body.pack(fill="both", expand=True, padx=14, pady=(0, 12))

    def set_colors(self, colors):
        self.colors = colors
        self.configure(bg=colors["card"], highlightbackground=colors["border"])
        self.title_lbl.configure(bg=colors["card"], fg=colors["text_dim"])
        self.body.configure(bg=colors["card"])


def stat_row(parent, colors, base_font, label_text, value_text, value_color=None):
    """یک ردیف «برچسب / مقدار» برای داخل کارت‌ها"""
    row = tk.Frame(parent, bg=colors["card"])
    row.pack(fill="x", pady=3)
    lbl = tk.Label(row, text=label_text, bg=colors["card"], fg=colors["text_dim"],
                    font=(base_font, 10), anchor="e", justify="right")
    lbl.pack(side="right")
    val = tk.Label(row, text=value_text, bg=colors["card"],
                    fg=value_color or colors["text"], font=(base_font, 10, "bold"),
                    anchor="w", justify="left")
    val.pack(side="left")
    return val


# ---------------------------------------------------------------------------
# برنامه اصلی
# ---------------------------------------------------------------------------
class AxiomSystemMonitor(tk.Tk):
    def __init__(self):
        super().__init__()
        self.dark_mode = True
        self.colors = DARK
        self.update_interval_ms = 1500
        self.after_id = None
        self.font_warning_shown = False

        self.section_visibility = {
            "cpu": tk.BooleanVar(value=True),
            "ram": tk.BooleanVar(value=True),
            "disk": tk.BooleanVar(value=True),
            "net": tk.BooleanVar(value=True),
            "charts": tk.BooleanVar(value=True),
        }

        self._detect_font()
        self._setup_window()
        self._prepare_counters()
        self._build_ui()
        self._schedule_update()

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    # ------------------------------------------------------------------
    # راه‌اندازی اولیه
    # ------------------------------------------------------------------
    def _detect_font(self):
        available = set(tkfont.families())
        self.base_font = None
        for name in PREFERRED_FONTS:
            if name in available:
                self.base_font = name
                break
        if self.base_font is None:
            self.base_font = "TkDefaultFont"
            self.font_warning_shown = True
        else:
            self.font_warning_shown = (self.base_font != "Vazirmatn")

    def _setup_window(self):
        self.title(f"{APP_NAME_FA} | {APP_SUBTITLE_FA}")
        self.geometry("1180x760")
        self.minsize(980, 640)
        self.configure(bg=self.colors["bg"])
        default_font = tkfont.nametofont("TkDefaultFont")
        default_font.configure(family=self.base_font, size=10)
        self.option_add("*Font", default_font)

        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        self.style = style
        self._apply_ttk_style()

    def _apply_ttk_style(self):
        c = self.colors
        s = self.style
        s.configure("TFrame", background=c["bg"])
        s.configure("Card.TFrame", background=c["card"])
        s.configure("TNotebook", background=c["bg"], borderwidth=0)
        s.configure("TNotebook.Tab", background=c["card"], foreground=c["text"],
                    padding=(18, 10), font=(self.base_font, 10, "bold"))
        s.map("TNotebook.Tab",
              background=[("selected", c["accent"])],
              foreground=[("selected", "#ffffff")])

        s.configure("Treeview", background=c["card"], fieldbackground=c["card"],
                    foreground=c["text"], rowheight=26, borderwidth=0,
                    font=(self.base_font, 10))
        s.configure("Treeview.Heading", background=c["bg_alt"], foreground=c["text_dim"],
                    font=(self.base_font, 10, "bold"), relief="flat")
        s.map("Treeview", background=[("selected", c["accent_soft"])],
              foreground=[("selected", c["text"])])

        s.configure("Horizontal.TProgressbar", troughcolor=c["bg_alt"],
                    background=c["accent"], bordercolor=c["bg_alt"],
                    lightcolor=c["accent"], darkcolor=c["accent"])

        s.configure("TScale", background=c["bg"], troughcolor=c["bg_alt"])
        s.configure("TCheckbutton", background=c["bg"], foreground=c["text"],
                    font=(self.base_font, 10))
        s.map("TCheckbutton", background=[("active", c["bg"])])

        s.configure("Accent.TButton", background=c["accent"], foreground="#ffffff",
                    font=(self.base_font, 10, "bold"), padding=(14, 8), borderwidth=0)
        s.map("Accent.TButton", background=[("active", c["accent"])])

        s.configure("Danger.TButton", background=c["danger"], foreground="#ffffff",
                    font=(self.base_font, 10, "bold"), padding=(14, 8), borderwidth=0)
        s.map("Danger.TButton", background=[("active", c["danger"])])

        s.configure("Ghost.TButton", background=c["card"], foreground=c["text"],
                    font=(self.base_font, 10), padding=(12, 7), borderwidth=1)

    def _prepare_counters(self):
        self._last_net = safe_call(psutil.net_io_counters)
        self._last_disk_io = safe_call(psutil.disk_io_counters)
        self._last_time = time.time()
        safe_call(lambda: psutil.cpu_percent(interval=None))
        self._proc_cache = {}

    # ------------------------------------------------------------------
    # ساخت رابط کاربری
    # ------------------------------------------------------------------
    def _build_ui(self):
        c = self.colors
        self._build_header()

        if self.font_warning_shown:
            self._build_font_warning_banner()

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=16, pady=(4, 12))

        self.tab_dashboard = tk.Frame(self.notebook, bg=c["bg"])
        self.tab_processes = tk.Frame(self.notebook, bg=c["bg"])
        self.tab_sysinfo = tk.Frame(self.notebook, bg=c["bg"])
        self.tab_settings = tk.Frame(self.notebook, bg=c["bg"])

        self.notebook.add(self.tab_dashboard, text="داشبورد")
        self.notebook.add(self.tab_processes, text="پردازش‌ها")
        self.notebook.add(self.tab_sysinfo, text="اطلاعات سیستم")
        self.notebook.add(self.tab_settings, text="تنظیمات")

        self._build_dashboard_tab()
        self._build_processes_tab()
        self._build_sysinfo_tab()
        self._build_settings_tab()

        self._build_statusbar()

    def _build_header(self):
        c = self.colors
        self.header = tk.Frame(self, bg=c["bg"])
        self.header.pack(fill="x", padx=16, pady=(14, 6))

        title_box = tk.Frame(self.header, bg=c["bg"])
        title_box.pack(side="right")
        tk.Label(title_box, text=APP_NAME_FA, bg=c["bg"], fg=c["text"],
                 font=(self.base_font, 18, "bold"), anchor="e").pack(anchor="e")
        tk.Label(title_box, text=APP_SUBTITLE_FA, bg=c["bg"], fg=c["accent"],
                 font=(self.base_font, 11), anchor="e").pack(anchor="e")

        self.status_pill = tk.Label(self.header, text="در حال بررسی...", bg=c["card"],
                                     fg=c["text"], font=(self.base_font, 10, "bold"),
                                     padx=14, pady=8)
        self.status_pill.pack(side="left")

    def _build_font_warning_banner(self):
        c = self.colors
        banner = tk.Frame(self, bg=c["warning"])
        banner.pack(fill="x", padx=16, pady=(0, 6))
        msg = (
            "فونت وزیرمتن (Vazirmatn) روی سیستم شما یافت نشد؛ برنامه از فونت جایگزین "
            f"«{self.base_font}» استفاده می‌کند. برای بهترین نمایش، فونت وزیرمتن را طبق "
            "راهنمای فایل README نصب کنید و برنامه را دوباره اجرا نمایید."
        )
        tk.Label(banner, text=msg, bg=c["warning"], fg="#2b1a00",
                 font=(self.base_font, 9, "bold"), anchor="e", justify="right",
                 wraplength=1100).pack(fill="x", padx=10, pady=6)

    def _build_statusbar(self):
        c = self.colors
        self.statusbar = tk.Label(self, text="", bg=c["bg_alt"], fg=c["text_dim"],
                                   font=(self.base_font, 9), anchor="e", padx=12, pady=6)
        self.statusbar.pack(fill="x", side="bottom")

    # -- تب داشبورد ------------------------------------------------------
    def _build_dashboard_tab(self):
        c = self.colors
        tab = self.tab_dashboard
        tab.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="col")

        # کارت وضعیت و امتیاز
        top_row = tk.Frame(tab, bg=c["bg"])
        top_row.grid(row=0, column=0, columnspan=4, sticky="ew", pady=(0, 12))
        top_row.grid_columnconfigure((0, 1), weight=1)

        self.card_status = InfoCard(top_row, c, "وضعیت سیستم", self.base_font)
        self.card_status.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        self.lbl_status_value = tk.Label(self.card_status.body, text="در حال بررسی...",
                                          bg=c["card"], fg=c["text"],
                                          font=(self.base_font, 16, "bold"),
                                          anchor="e", justify="right")
        self.lbl_status_value.pack(anchor="e", pady=4)
        self.lbl_status_detail = tk.Label(self.card_status.body, text="", bg=c["card"],
                                           fg=c["text_dim"], font=(self.base_font, 9),
                                           anchor="e", justify="right", wraplength=380)
        self.lbl_status_detail.pack(anchor="e")

        self.card_score = InfoCard(top_row, c, "امتیاز سیستم", self.base_font)
        self.card_score.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.lbl_score_value = tk.Label(self.card_score.body, text="-- از ۱۰۰",
                                         bg=c["card"], fg=c["accent"],
                                         font=(self.base_font, 18, "bold"),
                                         anchor="e", justify="right")
        self.lbl_score_value.pack(anchor="e", pady=2)
        self.lbl_score_label = tk.Label(self.card_score.body, text="", bg=c["card"],
                                         fg=c["text_dim"], font=(self.base_font, 10, "bold"),
                                         anchor="e", justify="right")
        self.lbl_score_label.pack(anchor="e")
        tk.Label(self.card_score.body,
                 text="این یک بنچمارک دقیق نیست و فقط وضعیت کلی سیستم را نشان می‌دهد.",
                 bg=c["card"], fg=c["text_dim"], font=(self.base_font, 8),
                 anchor="e", justify="right", wraplength=380).pack(anchor="e", pady=(6, 0))

        # کارت‌های CPU / RAM / Disk / Network
        self.card_cpu = InfoCard(tab, c, "پردازنده", self.base_font)
        self.card_cpu.grid(row=1, column=0, sticky="nsew", padx=6, pady=6)
        self.val_cpu_usage = stat_row(self.card_cpu.body, c, self.base_font, "استفاده:", "--%",
                                       c["cpu"])
        self.val_cpu_freq = stat_row(self.card_cpu.body, c, self.base_font, "فرکانس:", "--")
        self.val_cpu_cores = stat_row(self.card_cpu.body, c, self.base_font, "هسته فیزیکی:", "--")
        self.val_cpu_threads = stat_row(self.card_cpu.body, c, self.base_font, "رشته منطقی:", "--")

        self.card_ram = InfoCard(tab, c, "حافظه رم", self.base_font)
        self.card_ram.grid(row=1, column=1, sticky="nsew", padx=6, pady=6)
        self.val_ram_usage = stat_row(self.card_ram.body, c, self.base_font, "استفاده:", "--%",
                                       c["ram"])
        self.val_ram_used = stat_row(self.card_ram.body, c, self.base_font, "مصرف شده:", "--")
        self.val_ram_free = stat_row(self.card_ram.body, c, self.base_font, "آزاد:", "--")
        self.val_ram_total = stat_row(self.card_ram.body, c, self.base_font, "کل:", "--")

        self.card_disk = InfoCard(tab, c, "حافظه ذخیره‌سازی", self.base_font)
        self.card_disk.grid(row=1, column=2, sticky="nsew", padx=6, pady=6)
        self.val_disk_usage = stat_row(self.card_disk.body, c, self.base_font, "استفاده:", "--%")
        self.val_disk_free = stat_row(self.card_disk.body, c, self.base_font, "فضای خالی:", "--")
        self.val_disk_total = stat_row(self.card_disk.body, c, self.base_font, "حجم کل:", "--")
        self.val_disk_read = stat_row(self.card_disk.body, c, self.base_font, "سرعت خواندن:", "--")
        self.val_disk_write = stat_row(self.card_disk.body, c, self.base_font, "سرعت نوشتن:", "--")

        self.card_net = InfoCard(tab, c, "شبکه", self.base_font)
        self.card_net.grid(row=1, column=3, sticky="nsew", padx=6, pady=6)
        self.val_net_down = stat_row(self.card_net.body, c, self.base_font, "دانلود:", "--",
                                      c["net_down"])
        self.val_net_up = stat_row(self.card_net.body, c, self.base_font, "آپلود:", "--",
                                    c["net_up"])
        self.val_net_total_down = stat_row(self.card_net.body, c, self.base_font,
                                            "کل دریافتی:", "--")
        self.val_net_total_up = stat_row(self.card_net.body, c, self.base_font,
                                          "کل ارسالی:", "--")

        self.dashboard_cards = [self.card_cpu, self.card_ram, self.card_disk, self.card_net]

        # نمودارهای زنده
        self.charts_frame = tk.Frame(tab, bg=c["bg"])
        self.charts_frame.grid(row=2, column=0, columnspan=4, sticky="nsew", pady=(6, 0))
        self.charts_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self.chart_cpu = self._chart_card(self.charts_frame, "روند CPU", c["cpu"], 0, "%", 100)
        self.chart_ram = self._chart_card(self.charts_frame, "روند RAM", c["ram"], 1, "%", 100)
        self.chart_net = self._chart_card(self.charts_frame, "روند شبکه (دانلود)",
                                           c["net_down"], 2, "", 1024 * 1024)

    def _chart_card(self, parent, title, color, col, unit, y_max):
        c = self.colors
        card = InfoCard(parent, c, title, self.base_font)
        card.grid(row=0, column=col, sticky="nsew", padx=6, pady=6)
        chart = LiveLineChart(card.body, c, color, unit=unit, y_max=y_max)
        chart.pack(fill="both", expand=True)
        card.chart = chart
        self.dashboard_cards.append(card)
        return card

    # -- تب پردازش‌ها -----------------------------------------------------
    def _build_processes_tab(self):
        c = self.colors
        tab = self.tab_processes
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)

        toolbar = tk.Frame(tab, bg=c["bg"])
        toolbar.grid(row=0, column=0, sticky="ew", pady=(4, 8))

        self.btn_kill = ttk.Button(toolbar, text="پایان دادن پردازش", style="Danger.TButton",
                                    command=self.kill_selected_process)
        self.btn_kill.pack(side="left", padx=(0, 6))

        self.btn_refresh_proc = ttk.Button(toolbar, text="بروزرسانی", style="Ghost.TButton",
                                            command=self.refresh_processes)
        self.btn_refresh_proc.pack(side="left")

        search_box = tk.Frame(toolbar, bg=c["bg"])
        search_box.pack(side="right")
        tk.Label(search_box, text="جستجو:", bg=c["bg"], fg=c["text_dim"],
                 font=(self.base_font, 10)).pack(side="right", padx=(0, 6))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self.refresh_processes())
        self.entry_search = tk.Entry(search_box, textvariable=self.search_var,
                                      bg=c["card"], fg=c["text"], insertbackground=c["text"],
                                      relief="flat", justify="right",
                                      font=(self.base_font, 10), width=24)
        self.entry_search.pack(side="right", ipady=4)

        columns = ("name", "pid", "cpu", "ram")
        headers = {"name": "نام برنامه", "pid": "شناسه پردازش",
                   "cpu": "مصرف CPU", "ram": "مصرف RAM"}
        self.proc_tree = ttk.Treeview(tab, columns=columns, show="headings", selectmode="browse")
        for col in columns:
            self.proc_tree.heading(col, text=headers[col],
                                    command=lambda cc=col: self.sort_processes(cc))
            self.proc_tree.column(col, anchor="e", width=180 if col == "name" else 130)
        self.proc_tree.grid(row=1, column=0, sticky="nsew")

        scroll = ttk.Scrollbar(tab, orient="vertical", command=self.proc_tree.yview)
        self.proc_tree.configure(yscrollcommand=scroll.set)
        scroll.grid(row=1, column=1, sticky="ns")

        self.sort_column = "cpu"
        self.sort_reverse = True

    # -- تب اطلاعات سیستم --------------------------------------------------
    def _build_sysinfo_tab(self):
        c = self.colors
        tab = self.tab_sysinfo
        card = InfoCard(tab, c, "اطلاعات کلی سیستم", self.base_font)
        card.pack(fill="both", expand=True, padx=4, pady=8)

        self.sysinfo_rows = {}
        fields = [
            ("os", "سیستم عامل"),
            ("os_version", "نسخه سیستم عامل"),
            ("hostname", "نام کامپیوتر"),
            ("arch", "معماری سیستم"),
            ("uptime", "زمان روشن بودن سیستم"),
            ("cpu_model", "مدل پردازنده"),
            ("cpu_cores", "تعداد هسته/رشته"),
            ("ram_total", "مقدار کل RAM"),
            ("python_ver", "نسخه پایتون"),
            ("boot_time", "زمان آخرین روشن شدن"),
        ]
        for key, label in fields:
            self.sysinfo_rows[key] = stat_row(card.body, c, self.base_font, label + ":", "--")

        self.dashboard_cards.append(card)
        self._populate_static_sysinfo()

    def _populate_static_sysinfo(self):
        self.sysinfo_rows["os"].configure(
            text=safe_call(lambda: platform.system(), NOT_AVAILABLE))
        self.sysinfo_rows["os_version"].configure(
            text=safe_call(lambda: platform.version(), NOT_AVAILABLE))
        self.sysinfo_rows["hostname"].configure(
            text=safe_call(socket.gethostname, NOT_AVAILABLE))
        self.sysinfo_rows["arch"].configure(
            text=safe_call(lambda: platform.machine(), NOT_AVAILABLE))
        self.sysinfo_rows["cpu_model"].configure(
            text=safe_call(lambda: platform.processor(), NOT_AVAILABLE) or NOT_AVAILABLE)
        cores = safe_call(lambda: psutil.cpu_count(logical=False))
        threads = safe_call(lambda: psutil.cpu_count(logical=True))
        self.sysinfo_rows["cpu_cores"].configure(
            text=f"{cores or '؟'} / {threads or '؟'}")
        total_ram = safe_call(lambda: psutil.virtual_memory().total)
        self.sysinfo_rows["ram_total"].configure(
            text=human_bytes(total_ram) if total_ram else NOT_AVAILABLE)
        self.sysinfo_rows["python_ver"].configure(text=platform.python_version())
        boot_ts = safe_call(psutil.boot_time)
        if boot_ts:
            self.sysinfo_rows["boot_time"].configure(
                text=datetime.fromtimestamp(boot_ts).strftime("%Y-%m-%d %H:%M:%S"))
        else:
            self.sysinfo_rows["boot_time"].configure(text=NOT_AVAILABLE)

    # -- تب تنظیمات --------------------------------------------------------
    def _build_settings_tab(self):
        c = self.colors
        tab = self.tab_settings
        card = InfoCard(tab, c, "تنظیمات برنامه", self.base_font)
        card.pack(fill="both", expand=True, padx=4, pady=8)
        body = card.body

        # سرعت بروزرسانی
        row1 = tk.Frame(body, bg=c["card"])
        row1.pack(fill="x", pady=10)
        tk.Label(row1, text="سرعت بروزرسانی اطلاعات (ثانیه):", bg=c["card"], fg=c["text"],
                 font=(self.base_font, 10, "bold"), anchor="e").pack(anchor="e")
        self.interval_var = tk.DoubleVar(value=self.update_interval_ms / 1000)
        self.interval_lbl = tk.Label(row1, text=f"{self.interval_var.get():.1f} ثانیه",
                                      bg=c["card"], fg=c["accent"], font=(self.base_font, 9))
        self.interval_lbl.pack(anchor="e")
        scale = ttk.Scale(row1, from_=0.5, to=5.0, variable=self.interval_var,
                           command=self._on_interval_change, orient="horizontal")
        scale.pack(fill="x", pady=(4, 0))

        # حالت تاریک/روشن
        row2 = tk.Frame(body, bg=c["card"])
        row2.pack(fill="x", pady=10)
        self.dark_mode_var = tk.BooleanVar(value=self.dark_mode)
        chk_theme = ttk.Checkbutton(row2, text="حالت تاریک (Dark Mode)",
                                     variable=self.dark_mode_var, command=self.toggle_theme)
        chk_theme.pack(anchor="e")

        # نمایش/مخفی‌سازی بخش‌ها
        row3 = tk.Frame(body, bg=c["card"])
        row3.pack(fill="x", pady=10)
        tk.Label(row3, text="نمایش یا مخفی کردن بخش‌های داشبورد:", bg=c["card"], fg=c["text"],
                 font=(self.base_font, 10, "bold"), anchor="e").pack(anchor="e", pady=(0, 6))
        labels = {"cpu": "پردازنده", "ram": "حافظه رم", "disk": "ذخیره‌سازی",
                  "net": "شبکه", "charts": "نمودارهای زنده"}
        for key, var in self.section_visibility.items():
            ttk.Checkbutton(row3, text=labels[key], variable=var,
                             command=self.apply_section_visibility).pack(anchor="e")

    def _on_interval_change(self, _value):
        self.interval_lbl.configure(text=f"{self.interval_var.get():.1f} ثانیه")
        self.update_interval_ms = int(self.interval_var.get() * 1000)

    def apply_section_visibility(self):
        mapping = {
            "cpu": self.card_cpu, "ram": self.card_ram,
            "disk": self.card_disk, "net": self.card_net,
        }
        for key, card in mapping.items():
            if self.section_visibility[key].get():
                card.grid()
            else:
                card.grid_remove()
        if self.section_visibility["charts"].get():
            self.charts_frame.grid()
        else:
            self.charts_frame.grid_remove()

    # ------------------------------------------------------------------
    # تغییر حالت تاریک/روشن
    # ------------------------------------------------------------------
    def toggle_theme(self):
        self.dark_mode = self.dark_mode_var.get()
        self.colors = DARK if self.dark_mode else LIGHT
        c = self.colors
        self.configure(bg=c["bg"])
        self._apply_ttk_style()
        self.header.configure(bg=c["bg"])
        for w in self.header.winfo_children():
            self._recolor_widget_tree(w, c)
        self.statusbar.configure(bg=c["bg_alt"], fg=c["text_dim"])
        for tab in (self.tab_dashboard, self.tab_processes, self.tab_sysinfo, self.tab_settings):
            tab.configure(bg=c["bg"])
            self._recolor_widget_tree(tab, c)
        for card in self.dashboard_cards:
            card.set_colors(c)
            self._recolor_widget_tree(card.body, c)
            if hasattr(card, "chart"):
                card.chart.set_colors(c)
        self.entry_search.configure(bg=c["card"], fg=c["text"], insertbackground=c["text"])

    def _recolor_widget_tree(self, widget, c):
        """تلاش برای بروزرسانی رنگ همه فرزندان یک ویجت (best-effort)"""
        try:
            cur_bg = widget.cget("bg")
            if cur_bg in (DARK["bg"], LIGHT["bg"]):
                widget.configure(bg=c["bg"])
            elif cur_bg in (DARK["card"], LIGHT["card"]):
                widget.configure(bg=c["card"])
            if "fg" in widget.keys():
                cur_fg = widget.cget("fg")
                if cur_fg in (DARK["text_dim"], LIGHT["text_dim"]):
                    widget.configure(fg=c["text_dim"])
        except tk.TclError:
            pass
        for child in widget.winfo_children():
            self._recolor_widget_tree(child, c)

    # ------------------------------------------------------------------
    # چرخه بروزرسانی زنده (بدون Freeze شدن رابط کاربری)
    # ------------------------------------------------------------------
    def _schedule_update(self):
        self.refresh_dashboard()
        self.refresh_processes()
        self.after_id = self.after(self.update_interval_ms, self._schedule_update)

    def refresh_dashboard(self):
        c = self.colors
        now = time.time()
        elapsed = max(now - self._last_time, 0.001)

        # CPU
        cpu_percent = safe_call(lambda: psutil.cpu_percent(interval=None))
        cpu_freq = safe_call(psutil.cpu_freq)
        cores = safe_call(lambda: psutil.cpu_count(logical=False))
        threads = safe_call(lambda: psutil.cpu_count(logical=True))

        if cpu_percent is not None:
            self.val_cpu_usage.configure(text=f"{cpu_percent:.0f}%")
            self.chart_cpu.chart.push(cpu_percent)
        else:
            self.val_cpu_usage.configure(text=DATA_ERROR)

        self.val_cpu_freq.configure(
            text=f"{cpu_freq.current / 1000:.1f} GHz" if cpu_freq else NOT_AVAILABLE)
        self.val_cpu_cores.configure(text=str(cores) if cores else NOT_AVAILABLE)
        self.val_cpu_threads.configure(text=str(threads) if threads else NOT_AVAILABLE)

        # RAM
        vmem = safe_call(psutil.virtual_memory)
        if vmem:
            self.val_ram_usage.configure(text=f"{vmem.percent:.0f}%")
            self.val_ram_used.configure(text=human_bytes(vmem.used))
            self.val_ram_free.configure(text=human_bytes(vmem.available))
            self.val_ram_total.configure(text=human_bytes(vmem.total))
            self.chart_ram.chart.push(vmem.percent)
            ram_percent = vmem.percent
        else:
            for lbl in (self.val_ram_usage, self.val_ram_used, self.val_ram_free,
                        self.val_ram_total):
                lbl.configure(text=DATA_ERROR)
            ram_percent = 0

        # Disk
        disk = safe_call(lambda: psutil.disk_usage("/"))
        disk_io = safe_call(psutil.disk_io_counters)
        if disk:
            self.val_disk_usage.configure(text=f"{disk.percent:.0f}%")
            self.val_disk_free.configure(text=human_bytes(disk.free))
            self.val_disk_total.configure(text=human_bytes(disk.total))
        else:
            for lbl in (self.val_disk_usage, self.val_disk_free, self.val_disk_total):
                lbl.configure(text=DATA_ERROR)

        if disk_io and self._last_disk_io:
            read_speed = (disk_io.read_bytes - self._last_disk_io.read_bytes) / elapsed
            write_speed = (disk_io.write_bytes - self._last_disk_io.write_bytes) / elapsed
            self.val_disk_read.configure(text=human_speed(max(read_speed, 0)))
            self.val_disk_write.configure(text=human_speed(max(write_speed, 0)))
        else:
            self.val_disk_read.configure(text=NOT_AVAILABLE)
            self.val_disk_write.configure(text=NOT_AVAILABLE)
        self._last_disk_io = disk_io

        # Network
        net = safe_call(psutil.net_io_counters)
        if net and self._last_net:
            down_speed = (net.bytes_recv - self._last_net.bytes_recv) / elapsed
            up_speed = (net.bytes_sent - self._last_net.bytes_sent) / elapsed
            down_speed = max(down_speed, 0)
            up_speed = max(up_speed, 0)
            self.val_net_down.configure(text=human_speed(down_speed))
            self.val_net_up.configure(text=human_speed(up_speed))
            self.val_net_total_down.configure(text=human_bytes(net.bytes_recv))
            self.val_net_total_up.configure(text=human_bytes(net.bytes_sent))
            self.chart_net.chart.push(down_speed)
        else:
            for lbl in (self.val_net_down, self.val_net_up, self.val_net_total_down,
                        self.val_net_total_up):
                lbl.configure(text=DATA_ERROR)
        self._last_net = net
        self._last_time = now

        # وضعیت کلی و امتیاز سیستم
        self._update_status_and_score(cpu_percent or 0, ram_percent,
                                       disk.percent if disk else 0)

        self.statusbar.configure(
            text=f"آخرین بروزرسانی: {datetime.now().strftime('%H:%M:%S')}")

    def _update_status_and_score(self, cpu_p, ram_p, disk_p):
        c = self.colors
        pressure = max(cpu_p, ram_p, disk_p * 0.5)
        if pressure < 60:
            self.status_pill.configure(text="✓ سالم", bg=c["success"], fg="#062b17")
            self.lbl_status_value.configure(text="✓ سالم", fg=c["success"])
            self.lbl_status_detail.configure(text="سیستم در وضعیت عادی و پایدار قرار دارد.")
        elif pressure < 85:
            self.status_pill.configure(text="⚠ فشار متوسط", bg=c["warning"], fg="#2b1a00")
            self.lbl_status_value.configure(text="⚠ فشار متوسط", fg=c["warning"])
            self.lbl_status_detail.configure(
                text="مصرف منابع سیستم بالاتر از حد عادی است.")
        else:
            self.status_pill.configure(text="⚠ فشار زیاد روی سیستم", bg=c["danger"], fg="#2b0808")
            self.lbl_status_value.configure(text="⚠ فشار زیاد روی سیستم", fg=c["danger"])
            self.lbl_status_detail.configure(
                text="سیستم تحت فشار زیادی است؛ برنامه‌های غیرضروری را ببندید.")

        score = max(0, round(100 - pressure))
        self.lbl_score_value.configure(text=f"{score} از ۱۰۰")
        if score >= 85:
            grade, color = "عالی", c["success"]
        elif score >= 65:
            grade, color = "خوب", c["accent"]
        elif score >= 40:
            grade, color = "متوسط", c["warning"]
        else:
            grade, color = "ضعیف", c["danger"]
        self.lbl_score_label.configure(text=grade, fg=color)
        self.lbl_score_value.configure(fg=color)

    # ------------------------------------------------------------------
    # مدیریت پردازش‌ها
    # ------------------------------------------------------------------
    SENSITIVE_NAMES = {
        "system", "systemd", "kernel_task", "winlogon.exe", "csrss.exe",
        "wininit.exe", "services.exe", "smss.exe", "svchost.exe",
        "explorer.exe", "launchd", "init",
    }

    def refresh_processes(self):
        query = self.search_var.get().strip().lower()
        rows = []
        current_pids = set(safe_call(psutil.pids, []))

        # حذف پردازش‌های از بین رفته از حافظه موقت
        for pid in list(self._proc_cache.keys()):
            if pid not in current_pids:
                del self._proc_cache[pid]

        for pid in current_pids:
            proc = self._proc_cache.get(pid)
            if proc is None:
                proc = safe_call(lambda p=pid: psutil.Process(p))
                if proc is None:
                    continue
                # فراخوانی اول فقط برای ثبت نقطه پایه CPU لازم است
                safe_call(lambda: proc.cpu_percent(interval=None))
                self._proc_cache[pid] = proc
                continue  # مقدار دقیق CPU در چرخه بعدی محاسبه می‌شود

            try:
                name = proc.name() or NOT_AVAILABLE
                if query and query not in name.lower():
                    continue
                cpu = proc.cpu_percent(interval=None) or 0.0
                ram = proc.memory_percent() or 0.0
                rows.append((name, pid, cpu, ram))
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        reverse = self.sort_reverse
        key_index = {"name": 0, "pid": 1, "cpu": 2, "ram": 3}[self.sort_column]
        rows.sort(key=lambda r: (r[key_index] if not isinstance(r[key_index], str)
                                  else r[key_index].lower()), reverse=reverse)

        self.proc_tree.delete(*self.proc_tree.get_children())
        for name, pid, cpu, ram in rows[:400]:
            self.proc_tree.insert("", "end", iid=str(pid), values=(
                name, pid, f"{cpu:.1f}%", f"{ram:.1f}%"))

    def sort_processes(self, column):
        if self.sort_column == column:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = column
            self.sort_reverse = True
        self.refresh_processes()

    def kill_selected_process(self):
        selection = self.proc_tree.selection()
        if not selection:
            messagebox.showinfo(APP_NAME_FA, "لطفاً ابتدا یک پردازش را انتخاب کنید.")
            return
        pid = int(selection[0])
        values = self.proc_tree.item(selection[0], "values")
        name = values[0] if values else "این برنامه"

        if name.lower() in self.SENSITIVE_NAMES:
            proceed = messagebox.askyesno(
                "هشدار: پردازش حساس سیستم",
                f"«{name}» یک پردازش حساس سیستمی است و بستن آن ممکن است باعث "
                "ناپایداری یا خاموش شدن سیستم شود.\n\n"
                "آیا با وجود این هشدار مطمئن هستید که می‌خواهید ادامه دهید؟",
                icon="warning")
        else:
            proceed = messagebox.askyesno(
                APP_NAME_FA,
                f"آیا مطمئن هستید که می‌خواهید «{name}» (شناسه {pid}) را ببندید؟")

        if not proceed:
            return

        try:
            target = psutil.Process(pid)
            target.terminate()
            try:
                target.wait(timeout=2)
            except psutil.TimeoutExpired:
                target.kill()
            messagebox.showinfo(APP_NAME_FA, f"«{name}» با موفقیت بسته شد.")
        except psutil.NoSuchProcess:
            messagebox.showwarning(APP_NAME_FA, "این پردازش دیگر وجود ندارد.")
        except psutil.AccessDenied:
            messagebox.showerror(
                APP_NAME_FA,
                "دسترسی کافی برای بستن این پردازش وجود ندارد.\n"
                "برنامه را با دسترسی مدیر (Administrator/root) اجرا کنید.")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(APP_NAME_FA, f"خطا در بستن پردازش:\n{exc}")
        finally:
            self.refresh_processes()

    # ------------------------------------------------------------------
    # خروج تمیز از برنامه
    # ------------------------------------------------------------------
    def on_close(self):
        if self.after_id is not None:
            try:
                self.after_cancel(self.after_id)
            except Exception:
                pass
        self.destroy()


def main():
    app = AxiomSystemMonitor()
    app.mainloop()


if __name__ == "__main__":
    main()
