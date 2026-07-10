"""游戏存档列表面板 — 已配置的游戏列表 + 打开目录/删除"""

import os
import tkinter as tk
from tkinter import ttk, messagebox

from shared import config_manager, backup as backup_engine


class SaveListPanel(tk.LabelFrame):
    """展示已配置游戏的存档列表"""

    def __init__(self, parent, app, *, on_select=None):
        super().__init__(parent, text="已配置的游戏", bg="#f5f5f5",
                         font=("Microsoft YaHei", 9), padx=8, pady=4)
        self.app = app
        self._on_select_cb = on_select

        cols = ("游戏", "存档类型", "备份数", "最近备份", "大小")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=3)
        for c, w in zip(cols, [140, 80, 60, 140, 80]):
            self.tree.heading(c, text=c)
            self.tree.column(c, width=w)
        self.tree.pack(side="left", fill="x", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        bf = tk.Frame(self, bg="#f5f5f5")
        bf.pack(side="right", padx=4)
        tk.Button(bf, text="打开目录", font=("Microsoft YaHei", 8),
                  relief="flat", bg="white", command=self.open_backup_dir).pack(pady=2)
        tk.Button(bf, text="查看存档", font=("Microsoft YaHei", 8),
                  relief="flat", bg="white", command=self.open_save_dir).pack(pady=2)
        tk.Button(bf, text="删除游戏", font=("Microsoft YaHei", 8),
                  relief="flat", bg="white", fg="red", command=self.delete_game).pack(pady=2)

    def _on_select(self, event):
        if self._on_select_cb:
            self._on_select_cb(self.get_selected_game())

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

    def get_selected_game(self) -> dict | None:
        sel = self.tree.selection()
        if sel:
            game_name = self.tree.item(sel[0], "values")[0]
            for g in config_manager.get_games():
                if g["name"] == game_name:
                    return g
        games = config_manager.get_games()
        return games[0] if games else None

    def open_backup_dir(self):
        sel = self.tree.selection()
        if sel:
            d = self.tree.item(sel[0], "tags")[0]
        else:
            dd = self.app.storage_root
            if not dd:
                return
            d = os.path.join(dd, "Saves")
            if not os.path.exists(d):
                os.makedirs(d, exist_ok=True)
        os.startfile(d)

    def open_save_dir(self):
        game = self.get_selected_game()
        if not game:
            messagebox.showinfo("提示", "请先在列表中选择一个游戏")
            return
        for sp in game.get("save_paths", []):
            parent = os.path.dirname(sp["path"])
            if os.path.exists(parent):
                os.startfile(parent)
                return
        messagebox.showinfo("提示", "存档目录尚不存在")

    def delete_game(self):
        game = self.get_selected_game()
        if not game:
            messagebox.showinfo("提示", "请先在列表中选择一个游戏")
            return
        if not messagebox.askyesno("确认删除", f"删除 [ {game['name']} ] 的配置？\n（不会删除已备份的存档文件）"):
            return
        config_manager.remove_game(game["backup_dir"])
        self.app.refresh_info()
        self.app.set_status(f"已删除 {game['name']}")
