"""崩铁系统状态卡片"""

import tkinter as tk

from games._base.card import Card
from shared import config_manager


class StatusCard(Card):
    def __init__(self, parent, app):
        super().__init__(parent, "系统状态")
        self.app = app
        self.lbl_disk = tk.Label(self, text="存档目录: 检测中...", bg="#f5f5f5", anchor="w")
        self.lbl_disk.pack(fill="x")
        self.lbl_count = tk.Label(self, text="暂未配置游戏存档", bg="#f5f5f5", anchor="w", fg="gray")
        self.lbl_count.pack(fill="x", pady=(2, 0))

    def refresh(self):
        dd = self.app.storage_root
        self.lbl_disk.config(
            text=f"存档目录: {dd} (已连接)" if dd else "存档目录: 未检测到",
            fg="green" if dd else "red")
        games = config_manager.get_games()
        if games:
            self.lbl_count.config(text=f"已配置 {len(games)} 款游戏", fg="green")
        else:
            self.lbl_count.config(text="暂未配置游戏存档", fg="gray")
