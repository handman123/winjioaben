"""原神系统信息卡片 — 数据盘 + 凭证位置 + 游戏路径"""

import os
import tkinter as tk

from games._base.card import Card


class InfoCard(Card):
    def __init__(self, parent, app, core):
        super().__init__(parent, "系统信息")
        self.app = app
        self.core = core

        # 数据盘
        self.lbl_disk = tk.Label(self, text="数据盘: 检测中...", bg="#f5f5f5", anchor="w")
        self.lbl_disk.pack(fill="x")

        # 凭证位置 + 打开目录
        row_cred = tk.Frame(self, bg="#f5f5f5"); row_cred.pack(fill="x")
        self.lbl_cred = tk.Label(row_cred, text="凭证位置: ...", bg="#f5f5f5", anchor="w")
        self.lbl_cred.pack(side="left")
        tk.Button(row_cred, text="打开凭证目录", font=("Microsoft YaHei", 8),
                  relief="flat", bg="white", padx=6,
                  command=self._open_cred_dir).pack(side="right")

        # 游戏路径 + 手动指定
        row_path = tk.Frame(self, bg="#f5f5f5"); row_path.pack(fill="x", pady=(4, 0))
        self.lbl_path = tk.Label(row_path, text="游戏路径: 检测中...", bg="#f5f5f5", anchor="w")
        self.lbl_path.pack(side="left")
        tk.Button(row_path, text="手动指定", font=("Microsoft YaHei", 8),
                  relief="flat", bg="white", padx=6,
                  command=self._pick_path).pack(side="right")

    def refresh(self):
        dd = self.app.storage_root
        self.lbl_disk.config(
            text=f"数据盘: {dd} (已连接)" if dd else "数据盘: 未检测到",
            fg="green" if dd else "red")

        cred_dir = os.path.join(dd, "Genshin") if dd else ""
        self.lbl_cred.config(text=f"凭证位置: {cred_dir}" if dd else "凭证位置: —")

        from games.genshin.core import genshin_config
        gp = genshin_config.get_game_path()
        if not gp:
            gp = self.core.find_platform_path()
            if gp:
                genshin_config.set_game_path(gp)
        if gp and os.path.exists(gp):
            self.lbl_path.config(text=f"游戏路径: {gp} (已检测)", fg="green")
        elif gp:
            self.lbl_path.config(text=f"游戏路径: {gp} (未找到)", fg="red")
        else:
            self.lbl_path.config(text="游戏路径: 未检测到", fg="red")

    def _open_cred_dir(self):
        dd = self.app.storage_root
        if dd:
            d = os.path.join(dd, "Genshin")
            os.makedirs(d, exist_ok=True)
            os.startfile(d)

    def _pick_path(self):
        from tkinter import filedialog
        p = filedialog.askdirectory(title="选择原神安装目录")
        if p:
            from games.genshin.core import genshin_config
            genshin_config.set_game_path(p)
            self.refresh()
