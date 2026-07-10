"""历史存档面板 — 备份历史列表 + 恢复选中"""

import os
import tkinter as tk
from tkinter import ttk, messagebox

from shared import config_manager, backup as backup_engine


class HistoryPanel(tk.LabelFrame):
    """展示选中游戏的备份历史"""

    def __init__(self, parent, app, *, on_restore=None):
        super().__init__(parent, text="历史存档", bg="#f5f5f5",
                         font=("Microsoft YaHei", 9), padx=8, pady=4)
        self.app = app
        self._on_restore_cb = on_restore

        hcols = ("时间", "大小")
        self.tree = ttk.Treeview(self, columns=hcols, show="headings", height=5)
        self.tree.heading("时间", text="时间")
        self.tree.heading("大小", text="大小")
        self.tree.column("时间", width=200)
        self.tree.column("大小", width=100)
        self.tree.pack(side="left", fill="both", expand=True)

        sb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        sb.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=sb.set)

        bf = tk.Frame(self, bg="#f5f5f5")
        bf.pack(side="right", padx=4)
        tk.Button(bf, text="恢复选中", font=("Microsoft YaHei", 8),
                  relief="flat", bg="white", command=self._on_restore).pack(pady=2)
        tk.Button(bf, text="刷新", font=("Microsoft YaHei", 8),
                  relief="flat", bg="white", command=lambda: self.refresh(self._current_game)).pack(pady=2)

        self._current_game = None

    def refresh(self, game: dict | None):
        """加载指定游戏的备份历史，game 为 None 时清空"""
        self._current_game = game
        self.tree.delete(*self.tree.get_children())
        if not game:
            return

        dd = self.app.storage_root
        if not dd:
            return

        root = os.path.join(dd, "Saves", game["backup_dir"])
        if not os.path.exists(root):
            return

        for dn in sorted(os.listdir(root)):
            bd = os.path.join(root, dn)
            if os.path.isdir(bd):
                for z in backup_engine.list_all(bd):
                    self.tree.insert("", "end",
                        values=(z["name"], f"{z['size']/(1024*1024):.1f} MB"),
                        tags=(os.path.join(bd, z["name"]),))

    def get_selected(self) -> tuple | None:
        """返回 (zip_path, zip_name) 或 None"""
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("提示", "请先选择一个备份")
            return None
        zip_path = self.tree.item(sel[0], "tags")[0]
        zip_name = self.tree.item(sel[0], "values")[0]
        return (zip_path, zip_name)

    def _on_restore(self):
        sel = self.get_selected()
        if sel and self._on_restore_cb:
            self._on_restore_cb(sel[0], sel[1])
