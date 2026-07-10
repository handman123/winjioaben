"""账号管理面板 — 多用户凭证列表（原神/崩铁共用）"""

import tkinter as tk
from tkinter import ttk, messagebox


class AccountPanel(tk.LabelFrame):
    """展示已保存的账号列表，支持保存/切换/更新/重命名/删除"""

    def __init__(self, parent, app, core, *,
                 on_save=None, on_switch=None, on_update=None,
                 on_rename=None, on_delete=None):
        super().__init__(parent, text="账号管理", bg="#f5f5f5",
                         font=("Microsoft YaHei", 9), padx=8, pady=4)
        self.app = app
        self.core = core
        self._callbacks = {
            "save": on_save, "switch": on_switch, "update": on_update,
            "rename": on_rename, "delete": on_delete,
        }

        cols = ("账号名", "最近更新")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=3)
        self.tree.heading("账号名", text="账号名")
        self.tree.heading("最近更新", text="最近更新")
        self.tree.column("账号名", width=150)
        self.tree.column("最近更新", width=160)
        self.tree.pack(side="left", fill="x", expand=True)

        bf = tk.Frame(self, bg="#f5f5f5")
        bf.pack(side="right", padx=4)

        def abtn(text, key):
            return tk.Button(bf, text=text, font=("Microsoft YaHei", 8),
                             relief="flat", bg="white", padx=4, pady=2,
                             width=12, command=self._make_handler(key))

        abtn("保存当前账号", "save").pack(pady=1)
        abtn("切换到此账号", "switch").pack(pady=1)
        abtn("更新此账号", "update").pack(pady=1)
        abtn("重命名", "rename").pack(pady=1)
        abtn("删除账号", "delete").pack(pady=1)

    def _make_handler(self, key: str):
        cb = self._callbacks.get(key)
        if not cb:
            return lambda: None

        if key in ("switch", "update", "rename", "delete"):
            return lambda: cb(self.get_selected())
        return cb  # save 不需要选中

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        for acc in self.core.list_accounts():
            self.tree.insert("", "end",
                values=(acc["name"], acc.get("updated_at", acc.get("created_at", ""))))

    def get_selected(self) -> str | None:
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("提示", "请先在账号列表中选择一个账号")
            return None
        return self.tree.item(sel[0], "values")[0]
