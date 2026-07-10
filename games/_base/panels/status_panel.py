"""系统状态面板 — 存档目录 + 平台路径 + 游戏数"""

import tkinter as tk

from shared import disk, config_manager


class StatusPanel(tk.LabelFrame):
    """显示存档目录和平台状态"""

    def __init__(self, parent, app, *,
                 platform_label: str = "",
                 show_discovery: bool = False,
                 on_discover=None):
        super().__init__(parent, text="系统状态", bg="#f5f5f5",
                         font=("Microsoft YaHei", 9), padx=8, pady=4)
        self.app = app
        self._show_discovery = show_discovery

        self.lbl_disk = tk.Label(self, text="存档目录: 检测中...", bg="#f5f5f5", anchor="w")
        self.lbl_disk.pack(fill="x")

        self.lbl_platform = tk.Label(self, text="", bg="#f5f5f5", anchor="w")
        if platform_label:
            self.lbl_platform.pack(fill="x")

        bottom = tk.Frame(self, bg="#f5f5f5")
        bottom.pack(fill="x", pady=(2, 0))

        if show_discovery and on_discover:
            self.btn_discover = tk.Button(bottom, text="添加游戏",
                                          font=("Microsoft YaHei", 8),
                                          relief="flat", bg="#d0d0d0", padx=10,
                                          command=on_discover)
            self.btn_discover.pack(side="left")

        self.lbl_save = tk.Label(bottom, text="存档: 未配置", bg="#f5f5f5", anchor="w")
        self.lbl_save.pack(side="left", padx=10)

        self._platform_label = platform_label

    def refresh(self):
        dd = self.app.storage_root
        games = config_manager.get_games()

        self.lbl_disk.config(
            text=f"存档目录: {dd} (已连接)" if dd else "存档目录: 未检测到",
            fg="green" if dd else "red")

        if self._platform_label:
            pp = self._platform_label
            self.lbl_platform.config(text=pp, fg="green" if ":" in pp else "red")

        if games:
            self.lbl_save.config(text=f"已配置 {len(games)} 款游戏", fg="green")
        else:
            msg = "存档: 未配置" if self._show_discovery else "暂无游戏配置"
            self.lbl_save.config(text=msg, fg="red" if self._show_discovery else "gray")
