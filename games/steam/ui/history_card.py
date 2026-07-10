"""Steam 历史存档卡片"""

import os
import tkinter as tk
from tkinter import ttk, messagebox

from games._base.card import Card
from utils import backup as backup_engine


class HistoryCard(Card):
    def __init__(self, parent, app, *, on_restore=None):
        super().__init__(parent, "历史存档")
        self.app = app
        self._on_restore = on_restore
        self._game = None

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

        bf = tk.Frame(self, bg="#f5f5f5"); bf.pack(side="right", padx=4)
        tk.Button(bf, text="恢复选中", font=("Microsoft YaHei", 8),
                  relief="flat", bg="white", command=self._restore).pack(pady=2)
        tk.Button(bf, text="刷新", font=("Microsoft YaHei", 8),
                  relief="flat", bg="white", command=self.refresh).pack(pady=2)

    def load(self, game: dict | None):
        self._game = game
        self.refresh()

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        if not self._game:
            return
        dd = self.app.storage_root
        if not dd:
            return
        root = os.path.join(dd, "Saves", self._game["backup_dir"])
        if not os.path.exists(root):
            return
        for dn in sorted(os.listdir(root)):
            bd = os.path.join(root, dn)
            if os.path.isdir(bd):
                for z in backup_engine.list_all(bd):
                    self.tree.insert("", "end",
                        values=(z["name"], f"{z['size']/(1024*1024):.1f} MB"),
                        tags=(os.path.join(bd, z["name"]),))

    def _restore(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("提示", "请先选择一条记录")
            return
        if self._on_restore:
            self._on_restore(self.tree.item(sel[0], "tags")[0])
