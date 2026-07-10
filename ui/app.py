import tkinter as tk
from tkinter import ttk, messagebox
import threading
import os, sys

# Ensure core/ is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import disk, steam, backup, discovery, config_manager
from ui.steam_tab import SteamTab
from ui.placeholder_tab import PlaceholderTab

TITLE = "GameDataKeeper v2.0 - 云电脑游戏数据持久化助手"
SIZE = "740x560"

class App:
    def __init__(self, root):
        self.root = root
        self.root.title(TITLE)
        self.root.geometry(SIZE)
        self.root.minsize(600, 450)
        self.root.configure(bg="#f5f5f5")

        self.data_drive = disk.find()
        if self.data_drive:
            config_manager.set_data_drive(self.data_drive)
        self.steam_path = steam.find_path()
        self.game_cfg = config_manager.get_games()

        self._build_tabbar()
        self._build_statusbar()

    # ── tab bar ─────────────────────────────────────────────
    def _build_tabbar(self):
        bar = tk.Frame(self.root, bg="#e6e6e6", height=36)
        bar.pack(fill="x", side="top")
        bar.pack_propagate(False)

        self.tab_btns = {}
        self.tab_frames = {}
        container = tk.Frame(self.root, bg="#f5f5f5")
        container.pack(fill="both", expand=True, side="top")

        def make_tab(name, frame_class, *args):
            btn = tk.Button(bar, text=name, font=("Microsoft YaHei", 10),
                            relief="flat", bd=0, padx=20, pady=6,
                            bg="#dcdcdc", fg="black", cursor="hand2",
                            command=lambda n=name: self._switch_tab(n))
            btn.pack(side="left")
            self.tab_btns[name] = btn
            frm = frame_class(container, self, *args)
            self.tab_frames[name] = frm
            return frm

        self.steam_page = make_tab("Steam", SteamTab)
        make_tab("原神", PlaceholderTab, "原神", "原神账号凭证备份与恢复\n游戏截图备份")
        make_tab("崩坏:星穹铁道", PlaceholderTab, "崩坏:星穹铁道", "崩铁账号凭证备份与恢复\n游戏截图备份")
        self._switch_tab("Steam")

    def _switch_tab(self, name):
        for n, b in self.tab_btns.items():
            b.configure(bg="#dcdcdc" if n != name else "#ffffff")
        for n, f in self.tab_frames.items():
            f.pack_forget()
        self.tab_frames[name].pack(fill="both", expand=True)

    # ── status bar ──────────────────────────────────────────
    def _build_statusbar(self):
        sb = tk.Frame(self.root, bg="#e0e0e0", height=28)
        sb.pack(fill="x", side="bottom")
        sb.pack_propagate(False)
        self.status_var = tk.StringVar(value="就绪")
        tk.Label(sb, textvariable=self.status_var, bg="#e0e0e0",
                 fg="gray", anchor="w", padx=8).pack(side="left")
        self.progress = ttk.Progressbar(sb, mode="indeterminate", length=120)
        self.progress.pack(side="right", padx=8)

    def set_status(self, text, color="gray"):
        self.status_var.set(text)

    def show_progress(self):
        self.progress.pack(side="right", padx=8)
        self.progress.start(10)

    def hide_progress(self):
        self.progress.stop()
        self.progress.pack_forget()

    def run_async(self, task, on_done=None, status="处理中..."):
        """Run task in background thread to keep UI responsive."""
        self.set_status(status, "blue")
        self.show_progress()

        def wrapper():
            try:
                result = task()
            except Exception as e:
                result = e
            self.root.after(0, lambda: self._on_task_done(result, on_done))

        threading.Thread(target=wrapper, daemon=True).start()

    def _on_task_done(self, result, on_done):
        self.hide_progress()
        if isinstance(result, Exception):
            messagebox.showerror("错误", str(result))
            self.set_status(f"错误: {result}", "red")
        elif on_done:
            on_done(result)
        self.refresh_info()

    def refresh_info(self):
        self.data_drive = disk.find()
        if self.data_drive:
            config_manager.set_data_drive(self.data_drive)
        self.steam_path = steam.find_path()
        self.game_cfg = config_manager.get_games()
        if hasattr(self, 'steam_page'):
            self.steam_page.update_info()
