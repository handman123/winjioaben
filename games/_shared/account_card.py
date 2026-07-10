"""AccountCard — 多账号管理卡片，原神/崩铁共用"""

import tkinter as tk
from tkinter import ttk, messagebox

from games._base.card import Card


class AccountCard(Card):
    def __init__(self, parent, app, account_manager, *,
                 on_save=None, on_switch=None, on_update=None,
                 on_rename=None, on_delete=None):
        super().__init__(parent, "账号管理")
        self.app = app
        self._mgr = account_manager
        self._cb = {"save": on_save, "switch": on_switch, "update": on_update,
                    "rename": on_rename, "delete": on_delete}

        cols = ("账号名", "最近更新")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=3)
        self.tree.heading("账号名", text="账号名")
        self.tree.heading("最近更新", text="最近更新")
        self.tree.column("账号名", width=150)
        self.tree.column("最近更新", width=160)
        self.tree.pack(side="left", fill="x", expand=True)

        bf = tk.Frame(self, bg="#f5f5f5"); bf.pack(side="right", padx=4)
        for label, key in [("保存当前账号", "save"), ("切换到此账号", "switch"),
                           ("更新此账号", "update"), ("重命名", "rename"),
                           ("删除账号", "delete")]:
            tk.Button(bf, text=label, font=("Microsoft YaHei", 8),
                      relief="flat", bg="white", padx=4, pady=2, width=12,
                      command=self._make_handler(key)).pack(pady=1)

    def _make_handler(self, key):
        cb = self._cb.get(key)
        if not cb:
            return lambda: None
        if key in ("switch", "update", "rename", "delete"):
            return lambda: cb(self._selected())
        return cb

    def _selected(self) -> str | None:
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("提示", "请先选择账号")
            return None
        return self.tree.item(sel[0], "values")[0]

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        for acc in self._mgr.list_accounts():
            self.tree.insert("", "end",
                values=(acc["name"], acc.get("updated_at", acc.get("created_at", ""))))
