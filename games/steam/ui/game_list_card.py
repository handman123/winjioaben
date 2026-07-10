"""Steam 游戏存档列表卡片"""

import os
import tkinter as tk
from tkinter import ttk, messagebox

from games._base.card import Card
from shared import config_manager, backup as backup_engine


class GameListCard(Card):
    def __init__(self, parent, app, *, on_select=None):
        super().__init__(parent, "已配置的游戏")
        self.app = app
        self._on_select = on_select

        cols = ("游戏", "存档类型", "备份数", "最近备份", "大小")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=3)
        for c, w in zip(cols, [140, 80, 60, 140, 80]):
            self.tree.heading(c, text=c)
            self.tree.column(c, width=w)
        self.tree.pack(side="left", fill="x", expand=True)
        self.tree.bind("<<TreeviewSelect>>", lambda e: self._emit_select())

        bf = tk.Frame(self, bg="#f5f5f5")
        bf.pack(side="right", padx=4)
        tk.Button(bf, text="打开目录", font=("Microsoft YaHei", 8),
                  relief="flat", bg="white", command=self._open_dir).pack(pady=2)
        tk.Button(bf, text="查看存档", font=("Microsoft YaHei", 8),
                  relief="flat", bg="white", command=self._open_save).pack(pady=2)
        tk.Button(bf, text="删除游戏", font=("Microsoft YaHei", 8),
                  relief="flat", bg="white", fg="red", command=self._delete).pack(pady=2)

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        dd = self.app.storage_root
        games = sorted(config_manager.get_games(), key=lambda g: g["name"].lower())
        saves_root = os.path.join(dd, "Saves") if dd else ""
        for game in games:
            for sp in game.get("save_paths", []):
                sd = os.path.join(saves_root, game["backup_dir"], sp["name"]) if dd else ""
                zips = backup_engine.list_all(sd) if dd and os.path.exists(sd) else []
                count = len(zips)
                last = zips[0]["time"] if zips else "暂无"
                total = sum(z["size"] for z in zips)
                self.tree.insert("", "end",
                    values=(game["name"], sp["name"], count, last,
                            f"{total/(1024*1024):.1f} MB" if total else "—"),
                    tags=(sd,))
        if self.tree.get_children():
            self.tree.selection_set(self.tree.get_children()[0])

    def get_selected(self) -> dict | None:
        sel = self.tree.selection()
        if sel:
            name = self.tree.item(sel[0], "values")[0]
            for g in config_manager.get_games():
                if g["name"] == name:
                    return g
        games = config_manager.get_games()
        return games[0] if games else None

    def _emit_select(self):
        if self._on_select:
            self._on_select(self.get_selected())

    def _open_dir(self):
        sel = self.tree.selection()
        d = self.tree.item(sel[0], "tags")[0] if sel else os.path.join(
            self.app.storage_root or "", "Saves")
        if os.path.exists(d):
            os.startfile(d)

    def _open_save(self):
        g = self.get_selected()
        if not g:
            messagebox.showinfo("提示", "请先选择游戏")
            return
        for sp in g.get("save_paths", []):
            p = os.path.dirname(sp["path"])
            if os.path.exists(p):
                os.startfile(p)
                return
        messagebox.showinfo("提示", "存档目录尚不存在")

    def _delete(self):
        g = self.get_selected()
        if not g:
            messagebox.showinfo("提示", "请先选择游戏")
            return
        if messagebox.askyesno("确认", f"删除 [{g['name']}] 的配置？"):
            config_manager.remove_game(g["backup_dir"])
            self.app.refresh()
            self.app.set_status(f"已删除 {g['name']}")
