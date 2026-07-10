"""
BaseGameTab — 通用游戏 Tab 基础设施。

不再规定面板布局。每个子类自行在 _build_ui() 中组合需要的面板。
基类提供：进度条、异常处理、通用操作 helper 方法。
"""

import os
import tkinter as tk
from tkinter import ttk, messagebox

from shared import disk, config_manager, backup as backup_engine
from shared.exceptions import GameDataKeeperError


class BaseGameTab(tk.Frame):
    """通用游戏 Tab 基础设施 — 子类必须覆盖 GAME_NAME / _build_ui"""

    # ── 子类必须覆盖 ──
    GAME_NAME: str = ""
    GAME_ID: str = ""

    # ── 子类可选覆盖 ──
    SAVE_PATTERNS: list = []
    SUPPORT_CREDENTIAL: bool = False
    SUPPORT_DISCOVERY: bool = True
    SUPPORT_PLATFORM: bool = False

    def __init__(self, parent, app):
        super().__init__(parent, bg="#f5f5f5")
        self.app = app
        self.core = self._create_core()
        self._build_ui()
        self._build_progress()
        self.update_info()

    def _create_core(self):
        from games._base.base_core import BaseGameCore
        return BaseGameCore(self.app)

    # ── 子类必须覆盖 ───────────────────────────────────

    def _build_ui(self):
        """子类实现：组合 StatusPanel / SaveListPanel / AccountPanel 等"""
        raise NotImplementedError("子类必须实现 _build_ui()")

    # ── 进度条（通用）───────────────────────────────────

    def _build_progress(self):
        self.pbar = ttk.Progressbar(self, mode="determinate", length=400)
        self.pbar.pack(fill="x", padx=10, pady=2)
        self.pbar.pack_forget()
        self.lbl_pct = tk.Label(self, text="", bg="#f5f5f5", fg="gray")
        self.lbl_pct.pack()

    def _on_progress(self, done, total):
        pct = min(100, int(done * 100 / total))
        self.pbar.pack(fill="x", padx=10, pady=2)
        self.pbar["value"] = pct
        dm = done / (1024 * 1024)
        tm = total / (1024 * 1024)
        self.lbl_pct.config(text=f"{dm:.0f} MB / {tm:.0f} MB  ({pct}%)")
        if pct >= 100:
            self.pbar.pack_forget()
            self.lbl_pct.config(text="完成")

    # ── 通用操作 Helper（子类调用）────────────────────

    def _do_backup_saves(self, game: dict) -> bool:
        """备份游戏存档。返回 True 成功，失败抛异常。"""
        self.core.backup_saves(game, on_progress=self._on_progress)
        return True

    def _do_restore_saves(self, game: dict, specific_zip=None) -> bool:
        """恢复游戏存档。返回 True 成功，失败抛异常。"""
        self.core.restore_saves(game, specific_zip=specific_zip,
                                on_progress=self._on_progress)
        return True

    def _do_restore_from_zip(self, target_path: str, zip_dir: str,
                              zip_name: str) -> bool:
        """从指定 zip 恢复存档"""
        backup_engine.restore(target_path, zip_dir, specific=zip_name,
                              on_progress=self._on_progress)
        return True

    def _do_backup_credential(self, account_name: str = None) -> list:
        """备份凭证。支持可选 account_name（多账号场景）"""
        if account_name:
            return self.core.backup_credential(account_name)
        return self.core.backup_credential()

    def _do_restore_credential(self, account_name: str = None) -> list:
        """恢复凭证。支持可选 account_name（多账号场景）"""
        if account_name:
            return self.core.restore_credential(account_name)
        return self.core.restore_credential()

    # ── 工具方法 ─────────────────────────────────────

    def update_info(self):
        """子类覆盖以刷新所有面板"""
        pass

    def _confirm(self, title: str, msg: str) -> bool:
        return messagebox.askyesno(title, msg)

    def _ask_path(self, prompt: str) -> str | None:
        import tkinter.simpledialog as sd
        return sd.askstring("手动配置存档", prompt)

    def _prompt_account_name(self, prompt: str = "请输入账号名称:") -> str | None:
        import tkinter.simpledialog as sd
        return sd.askstring("账号名称", prompt)

    def _check_game(self) -> bool:
        if not config_manager.get_games():
            messagebox.showinfo("未配置", "请先启动游戏，然后点击 [添加游戏] 自动配置。")
            return False
        return True

    def _check_storage(self) -> bool:
        if self.SUPPORT_PLATFORM and not self.core.find_platform_path():
            messagebox.showinfo(f"{self.GAME_NAME}未找到",
                                f"请确保{self.GAME_NAME}已安装。")
            return False
        return True

    def _validate_save_paths(self, game: dict) -> list[str]:
        """验证存档路径，返回问题列表"""
        issues = []
        for sp in game.get("save_paths", []):
            p = sp["path"]
            if not os.path.exists(p):
                issues.append(f"目录不存在: {p}")
            elif not os.listdir(p):
                issues.append(f"目录为空: {p}")
        return issues

    # ── 钩子 ─────────────────────────────────────────

    def get_extra_actions(self) -> list:
        return []
