"""主窗口 — Tab 栏 + 状态栏 + 异步任务调度"""

import tkinter as tk
from tkinter import messagebox
import threading

from app.tab_registry import TabRegistry
from app.status_bar import StatusBar
from shared import disk, config_manager


TITLE = "GameDataKeeper v2.0 - 云电脑游戏数据持久化助手"
SIZE = "740x560"


class App:
    def __init__(self, root):
        self.root = root
        self.root.title(TITLE)
        self.root.geometry(SIZE)
        self.root.minsize(600, 450)
        self.root.configure(bg="#f5f5f5")

        # 初始化存档目录
        ok, missing = disk.validate()
        if not ok:
            msg = "存档目录不完整，缺少:\n" + "\n".join(f"  {m}" for m in missing)
            msg += "\n\n是否自动修复（创建缺失目录）？"
            if messagebox.askyesno("目录修复", msg):
                disk.ensure()
            else:
                messagebox.showerror("错误", "存档目录不完整，程序无法运行。")
                self.root.destroy()
                return

        self.storage_root = disk.get_root()
        self.game_cfg = config_manager.get_games()

        self._ensure_registry()
        self._build_tabbar()
        self._build_statusbar()

    def _ensure_registry(self):
        """确保 Tab 已注册（在模块导入时自动完成）"""
        # 导入 games 模块触发 register() 调用
        import games  # noqa: F401

    # ── tab bar ─────────────────────────────────────────────

    def _build_tabbar(self):
        bar = tk.Frame(self.root, bg="#e6e6e6", height=36)
        bar.pack(fill="x", side="top")
        bar.pack_propagate(False)

        self.tab_btns = {}
        self.tab_frames = {}
        container = tk.Frame(self.root, bg="#f5f5f5")
        container.pack(fill="both", expand=True, side="top")

        tabs = TabRegistry.get_all()
        if not tabs:
            # 兜底：如果没有任何注册，创建一个占位提示
            tk.Label(container, text="没有可用的游戏模块", fg="gray",
                     bg="#f5f5f5", font=("Microsoft YaHei", 12)).pack(expand=True)
            return

        for entry in tabs:
            self._make_tab(bar, container, entry.name, entry.tab_class)

        # 默认激活第一个 Tab
        first_name = tabs[0].name
        self._switch_tab(first_name)

    def _make_tab(self, bar, container, name, frame_class):
        btn = tk.Button(bar, text=name, font=("Microsoft YaHei", 10),
                        relief="flat", bd=0, padx=20, pady=6,
                        bg="#dcdcdc", fg="black", cursor="hand2",
                        command=lambda n=name: self._switch_tab(n))
        btn.pack(side="left")
        self.tab_btns[name] = btn
        frm = frame_class(container, self)
        self.tab_frames[name] = frm

    def _switch_tab(self, name):
        for n, b in self.tab_btns.items():
            b.configure(bg="#dcdcdc" if n != name else "#ffffff")
        for n, f in self.tab_frames.items():
            f.pack_forget()
        self.tab_frames[name].pack(fill="both", expand=True)

    # ── status bar ──────────────────────────────────────────

    def _build_statusbar(self):
        self._status_bar = StatusBar(self.root)
        self._status_bar.pack(fill="x", side="bottom")

    def set_status(self, text, color="gray"):
        self._status_bar.set_status(text)

    def show_progress(self):
        self._status_bar.show_progress()

    def hide_progress(self):
        self._status_bar.hide_progress()

    # ── async ───────────────────────────────────────────────

    def run_async(self, task, on_done=None, status="处理中..."):
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
        self.storage_root = disk.get_root()
        self.game_cfg = config_manager.get_games()
        for name, frame in self.tab_frames.items():
            if hasattr(frame, 'update_info'):
                frame.update_info()
