import tkinter as tk
from tkinter import ttk, messagebox
import os, threading
from core import steam, backup, disk, discovery, config_manager

class SteamTab(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg="#f5f5f5")
        self.app = app

        # ── info group ──
        g = tk.LabelFrame(self, text="系统状态", bg="#f5f5f5",
                          font=("Microsoft YaHei", 9), padx=8, pady=4)
        g.pack(fill="x", padx=10, pady=(10, 4))

        self.lbl_disk = tk.Label(g, text="数据盘: 检测中...", bg="#f5f5f5", anchor="w")
        self.lbl_disk.pack(fill="x")
        self.lbl_steam = tk.Label(g, text="Steam: 检测中...", bg="#f5f5f5", anchor="w")
        self.lbl_steam.pack(fill="x")
        f = tk.Frame(g, bg="#f5f5f5")
        f.pack(fill="x", pady=(2, 0))
        self.btn_discover = tk.Button(f, text="发现存档", font=("Microsoft YaHei", 8),
                                      relief="flat", bg="#d0d0d0", padx=10,
                                      command=self._discover)
        self.btn_discover.pack(side="left")
        self.lbl_save = tk.Label(f, text="存档目录: 未配置", bg="#f5f5f5", anchor="w")
        self.lbl_save.pack(side="left", padx=10)

        # ── actions ──
        ga = tk.LabelFrame(self, text="快捷操作", bg="#f5f5f5",
                           font=("Microsoft YaHei", 9), padx=8, pady=4)
        ga.pack(fill="x", padx=10, pady=4)
        self._action_btns = []

        def btn(text, cmd):
            b = tk.Button(ga, text=text, font=("Microsoft YaHei", 9),
                          relief="flat", bg="white", padx=14, pady=4,
                          command=lambda: self.app.run_async(cmd, status=text+"..."))
            self._action_btns.append(b)
            return b

        r1 = tk.Frame(ga, bg="#f5f5f5"); r1.pack(fill="x", pady=2)
        btn("备份全部", self._backup_all).pack(side="left", padx=2)
        btn("恢复全部", self._restore_all).pack(side="left", padx=2)
        btn("备份存档", self._backup_saves).pack(side="left", padx=2)

        r2 = tk.Frame(ga, bg="#f5f5f5"); r2.pack(fill="x", pady=2)
        btn("备份Steam凭证", self._backup_steam).pack(side="left", padx=2)
        btn("恢复Steam凭证", self._restore_steam).pack(side="left", padx=2)
        btn("恢复最新存档", self._restore_saves).pack(side="left", padx=2)

        # ── progress ──
        self.pbar = ttk.Progressbar(self, mode="determinate", length=400)
        self.pbar.pack(fill="x", padx=10, pady=2)
        self.pbar.pack_forget()
        self.lbl_pct = tk.Label(self, text="", bg="#f5f5f5", fg="gray")
        self.lbl_pct.pack()

        # ── history ──
        gh = tk.LabelFrame(self, text="存档历史", bg="#f5f5f5",
                           font=("Microsoft YaHei", 9), padx=8, pady=4)
        gh.pack(fill="both", expand=True, padx=10, pady=4)

        cols = ("时间", "大小")
        self.tree = ttk.Treeview(gh, columns=cols, show="headings", height=6)
        self.tree.heading("时间", text="时间"); self.tree.heading("大小", text="大小")
        self.tree.column("时间", width=200); self.tree.column("大小", width=100)
        self.tree.pack(side="left", fill="both", expand=True)

        sb = ttk.Scrollbar(gh, orient="vertical", command=self.tree.yview)
        sb.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=sb.set)

        bf = tk.Frame(gh, bg="#f5f5f5"); bf.pack(side="right", padx=4)
        tk.Button(bf, text="恢复选中", font=("Microsoft YaHei", 8),
                  relief="flat", bg="white", command=self._restore_selected).pack(pady=2)
        tk.Button(bf, text="刷新", font=("Microsoft YaHei", 8),
                  relief="flat", bg="white", command=self._refresh_history).pack(pady=2)

        self.update_info()

    # ── info ────────────────────────────────────────────────
    def update_info(self):
        dd = self.app.data_drive
        sp = self.app.steam_path
        gc = config_manager.get_game()

        self.lbl_disk.config(text=f"数据盘: {dd} (已连接)" if dd else "数据盘: 未检测到",
                             fg="green" if dd else "red")
        self.lbl_steam.config(text=f"Steam: {sp}" if sp else "Steam: 未找到",
                              fg="green" if sp else "red")

        if gc and gc.get("save_paths"):
            p = gc["save_paths"][0]["path"]
            exists = os.path.exists(p)
            self.lbl_save.config(
                text=f"存档: {p} ({'存在' if exists else '尚未创建'})",
                fg="green" if exists else "darkorange")
            self.btn_discover.config(text="重新发现")
        else:
            self.lbl_save.config(text="存档: 未配置（启动游戏后点[发现存档]）", fg="red")
            self.btn_discover.config(text="发现存档")
        self._refresh_history()

    # ── progress callback ───────────────────────────────────
    def _on_progress(self, done, total):
        pct = min(100, int(done * 100 / total))
        self.pbar.pack(fill="x", padx=10, pady=2)
        self.pbar["value"] = pct
        dm = done / (1024*1024); tm = total / (1024*1024)
        self.lbl_pct.config(text=f"{dm:.0f} MB / {tm:.0f} MB  ({pct}%)")
        if pct >= 100:
            self.pbar.pack_forget()
            self.lbl_pct.config(text="完成")

    # ── operations ──────────────────────────────────────────
    def _backup_all(self):
        dd = self.app.data_drive; sp = self.app.steam_path
        if not dd or not sp: return "数据盘或Steam不可用"
        steam.backup(sp, dd)
        self._backup_saves()
        self.app.set_status("全部备份完成", "green")

    def _restore_all(self):
        dd = self.app.data_drive; sp = self.app.steam_path
        if not dd or not sp: return "数据盘或Steam不可用"
        if steam.is_running():
            if not messagebox.askyesno("Steam 正在运行", "需要关闭Steam，是否继续？"):
                self.app.set_status("已取消")
                return "已取消"
            steam.kill()
        steam.restore(sp, dd)
        steam.launch(sp)
        self._restore_saves()
        self.app.set_status("全部恢复完成", "green")

    def _backup_steam(self):
        dd = self.app.data_drive; sp = self.app.steam_path
        if not dd or not sp: return "数据盘或Steam不可用"
        steam.backup(sp, dd)
        self.app.set_status("Steam凭证已备份", "green")

    def _restore_steam(self):
        dd = self.app.data_drive; sp = self.app.steam_path
        if not dd or not sp: return "数据盘或Steam不可用"
        if steam.is_running():
            if not messagebox.askyesno("Steam 正在运行", "需要关闭Steam，是否继续？"):
                self.app.set_status("已取消")
                return "已取消"
            steam.kill()
        steam.restore(sp, dd)
        steam.launch(sp)
        self.app.set_status("Steam凭证已恢复", "green")

    def _backup_saves(self):
        dd = self.app.data_drive; gc = config_manager.get_game()
        if not dd or not gc: return "数据盘或游戏未配置"
        root = os.path.join(dd, "GameDataKeeper", "Saves")
        for sp in gc.get("save_paths", []):
            bd = os.path.join(root, gc["backup_dir"], sp["name"])
            ok, info = backup.backup(sp["path"], bd, on_progress=self._on_progress)
        self._refresh_history()
        self.app.set_status("游戏存档已备份", "green")

    def _restore_saves(self):
        dd = self.app.data_drive; gc = config_manager.get_game()
        if not dd or not gc: return "数据盘或游戏未配置"
        root = os.path.join(dd, "GameDataKeeper", "Saves")
        for sp in gc.get("save_paths", []):
            bd = os.path.join(root, gc["backup_dir"], sp["name"])
            ok, info = backup.restore(sp["path"], bd, on_progress=self._on_progress)
        self.app.set_status("游戏存档已恢复", "green")

    def _discover(self):
        g = discovery.detect_running()
        if not g:
            messagebox.showinfo("未检测到游戏", "请先启动Steam游戏，再点击[发现存档]")
            return
        r = messagebox.askyesno("确认", f"检测到: {g['folder']}\n{g['root']}\n\n搜索存档目录？")
        if not r: return
        dirs = discovery.find_save_dirs(g["root"])
        if not dirs:
            messagebox.showwarning("未发现", "未找到存档目录")
            return
        paths = [{"name": d["name"], "path": d["path"],
                  "description": f"自动发现"} for d in dirs]
        config_manager.set_game(g["folder"], g["folder"], paths)
        # Create backup dirs on data disk
        dd = self.app.data_drive
        if dd:
            for d in dirs:
                bd = os.path.join(dd, "GameDataKeeper", "Saves",
                    g["folder"].replace(" ","_"), d["name"])
                os.makedirs(bd, exist_ok=True)
        self.app.refresh_info()
        messagebox.showinfo("完成", f"已配置 {g['folder']}\n{g['folder'].replace(' ','_')}")

    def _refresh_history(self):
        self.tree.delete(*self.tree.get_children())
        dd = self.app.data_drive; gc = config_manager.get_game()
        if not dd or not gc: return
        root = os.path.join(dd, "GameDataKeeper", "Saves", gc["backup_dir"])
        if not os.path.exists(root): return
        for dn in os.listdir(root):
            bd = os.path.join(root, dn)
            if os.path.isdir(bd):
                for z in backup.list_all(bd):
                    mb = z["size"] / (1024*1024)
                    self.tree.insert("", "end", values=(z["name"], f"{mb:.1f} MB"),
                                     tags=(os.path.join(bd, z["name"]),))

    def _restore_selected(self):
        sel = self.tree.selection()
        if not sel: messagebox.showinfo("提示", "请先选择一个备份"); return
        item = self.tree.item(sel[0])
        zip_path = self.tree.item(sel[0], "tags")[0]
        zip_name = item["values"][0]
        bd = os.path.dirname(zip_path)
        gc = config_manager.get_game()
        if not gc: return
        sp = gc["save_paths"][0]["path"]

        def task():
            ok, info = backup.restore(sp, bd, specific=zip_name, on_progress=self._on_progress)
            if ok:
                self.app.set_status("存档恢复完成", "green")
            else:
                self.app.set_status(f"恢复失败: {info}", "red")
        self.app.run_async(task, status="正在恢复...")
