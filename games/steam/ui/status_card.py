"""Steam 系统状态卡片"""

import tkinter as tk

from games._base.card import Card
from games.steam.core import steam_config


class StatusCard(Card):
    def __init__(self, parent, app, *, on_discover=None):
        super().__init__(parent, "系统状态")
        self.app = app
        self._on_discover = on_discover

        self.lbl_disk = tk.Label(self, text="存档目录: 检测中...", bg="#f5f5f5", anchor="w")
        self.lbl_disk.pack(fill="x")

        self.lbl_steam = tk.Label(self, text="Steam: 检测中...", bg="#f5f5f5", anchor="w")
        self.lbl_steam.pack(fill="x")

        bar = tk.Frame(self, bg="#f5f5f5")
        bar.pack(fill="x", pady=(2, 0))
        if on_discover:
            self.btn_discover = tk.Button(bar, text="添加游戏",
                                          font=("Microsoft YaHei", 8),
                                          relief="flat", bg="#d0d0d0", padx=10,
                                          command=on_discover)
            self.btn_discover.pack(side="left")
        self.lbl_count = tk.Label(bar, text="存档: 未配置", bg="#f5f5f5", anchor="w")
        self.lbl_count.pack(side="left", padx=10)

    def set_platform(self, text: str):
        self.lbl_steam.config(text=text, fg="green" if ":" in text else "red")

    def refresh(self):
        dd = self.app.storage_root
        self.lbl_disk.config(
            text=f"存档目录: {dd} (已连接)" if dd else "存档目录: 未检测到",
            fg="green" if dd else "red")
        games = steam_config.get_games()
        if games:
            self.lbl_count.config(text=f"已配置 {len(games)} 款游戏", fg="green")
        else:
            self.lbl_count.config(text="存档: 未配置（启动游戏后点[添加游戏]）", fg="red")
