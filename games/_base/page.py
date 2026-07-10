"""Page 基类 — Tab 页面容器，纯框架：卡片管理 + 进度条 + 工具方法"""

import os
import tkinter as tk
from tkinter import ttk, messagebox

from games._base.card import Card
from shared import backup as backup_engine
from shared.exceptions import GameDataKeeperError


class Page(tk.Frame):
    """游戏 Tab 页基类 — 子类在 _build() 中通过 add_card() 组合卡片"""

    GAME_NAME: str = ""
    GAME_ID: str = ""

    def __init__(self, parent, app):
        super().__init__(parent, bg="#f5f5f5")
        self.app = app
        self.core = self._make_core()
        self._cards: list[Card] = []
        self._build()
        self._build_progress()
        self.refresh()

    # ── 子类必须覆盖 ────────────────────────────────

    def _make_core(self):
        from games._base.base_core import BaseGameCore
        return BaseGameCore(self.app)

    def _build(self):
        """子类实现：通过 self.add_card(...) 组合页面"""
        raise NotImplementedError

    # ── 卡片管理 ────────────────────────────────────

    def add_card(self, card: Card, **pack_opts) -> Card:
        opts = {"fill": "x", "padx": 10, "pady": 4}
        opts.update(pack_opts)
        card.pack(**opts)
        self._cards.append(card)
        return card

    # ── 进度条 ──────────────────────────────────────

    def _build_progress(self):
        self.pbar = ttk.Progressbar(self, mode="determinate", length=400)
        self.pbar.pack(fill="x", padx=10, pady=2)
        self.pbar.pack_forget()
        self.lbl_pct = tk.Label(self, text="", bg="#f5f5f5", fg="gray")
        self.lbl_pct.pack()

    def _on_progress(self, done, total):
        pct = min(100, int(done * 100 / total)) if total else 0
        self.pbar.pack(fill="x", padx=10, pady=2)
        self.pbar["value"] = pct
        dm = done / (1024 * 1024)
        tm = total / (1024 * 1024)
        self.lbl_pct.config(text=f"{dm:.0f} MB / {tm:.0f} MB  ({pct}%)")
        if pct >= 100:
            self.pbar.pack_forget()
            self.lbl_pct.config(text="完成")

    # ── 刷新 ────────────────────────────────────────

    def refresh(self):
        for card in self._cards:
            card.refresh()

    def update_info(self):
        """main_window 兼容别名"""
        self.refresh()

    # ── core 操作 wiring ────────────────────────────

    def _do_backup_saves(self, game: dict):
        self.core.backup_saves(game, on_progress=self._on_progress)

    def _do_restore_saves(self, game: dict, specific_zip=None):
        self.core.restore_saves(game, specific_zip=specific_zip,
                                on_progress=self._on_progress)

    def _do_restore_zip(self, target: str, zip_dir: str, zip_name: str):
        backup_engine.restore(target, zip_dir, specific=zip_name,
                              on_progress=self._on_progress)

    def _do_backup_credential(self, account_name: str = None):
        if account_name:
            return self.core.backup_credential(account_name)
        return self.core.backup_credential()

    def _do_restore_credential(self, account_name: str = None):
        if account_name:
            return self.core.restore_credential(account_name)
        return self.core.restore_credential()

    # ── 工具方法 ────────────────────────────────────

    def _confirm(self, title: str, msg: str) -> bool:
        return messagebox.askyesno(title, msg)

    def _ask_path(self, prompt: str) -> str | None:
        import tkinter.simpledialog as sd
        return sd.askstring("手动配置存档", prompt)

    def _prompt_name(self, prompt: str = "请输入名称:") -> str | None:
        import tkinter.simpledialog as sd
        return sd.askstring("输入", prompt)

    def _validate_save_paths(self, game: dict) -> list[str]:
        issues = []
        for sp in game.get("save_paths", []):
            p = sp["path"]
            if not os.path.exists(p):
                issues.append(f"目录不存在: {p}")
            elif not os.listdir(p):
                issues.append(f"目录为空: {p}")
        return issues
