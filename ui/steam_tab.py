import tkinter as tk
from tkinter import ttk, messagebox
import os, subprocess
from core import steam, backup, disk, discovery, config_manager

class SteamTab(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg="#f5f5f5")
        self.app = app

        # ── info ──
        g = tk.LabelFrame(self, text="系统状态", bg="#f5f5f5",
                          font=("Microsoft YaHei", 9), padx=8, pady=4)
        g.pack(fill="x", padx=10, pady=(10, 4))
        self.lbl_disk = tk.Label(g, text="数据盘: 检测中...", bg="#f5f5f5", anchor="w")
        self.lbl_disk.pack(fill="x")
        self.lbl_steam = tk.Label(g, text="Steam: 检测中...", bg="#f5f5f5", anchor="w")
        self.lbl_steam.pack(fill="x")
        f = tk.Frame(g, bg="#f5f5f5"); f.pack(fill="x", pady=(2, 0))
        self.btn_discover = tk.Button(f, text="添加游戏", font=("Microsoft YaHei", 8),
                                      relief="flat", bg="#d0d0d0", padx=10,
                                      command=self._discover)
        self.btn_discover.pack(side="left")
        self.lbl_save = tk.Label(f, text="存档目录: 未配置", bg="#f5f5f5", anchor="w")
        self.lbl_save.pack(side="left", padx=10)

        # ── stored games ──
        sg = tk.LabelFrame(self, text="已配置的游戏", bg="#f5f5f5",
                           font=("Microsoft YaHei", 9), padx=8, pady=4)
        sg.pack(fill="x", padx=10, pady=4)

        cols = ("游戏", "存档类型", "备份数", "最近备份", "大小")
        self.game_tree = ttk.Treeview(sg, columns=cols, show="headings", height=3)
        for c, w in zip(cols, [140, 80, 60, 140, 80]):
            self.game_tree.heading(c, text=c); self.game_tree.column(c, width=w)
        self.game_tree.pack(side="left", fill="x", expand=True)
        self.game_tree.bind("<<TreeviewSelect>>", lambda e: self._refresh_history())

        gf = tk.Frame(sg, bg="#f5f5f5"); gf.pack(side="right", padx=4)
        tk.Button(gf, text="打开目录", font=("Microsoft YaHei", 8),
                  relief="flat", bg="white", command=self._open_backup_dir).pack(pady=2)
        tk.Button(gf, text="查看存档", font=("Microsoft YaHei", 8),
                  relief="flat", bg="white", command=self._open_save_dir).pack(pady=2)

        # ── actions ──
        ga = tk.LabelFrame(self, text="快捷操作", bg="#f5f5f5",
                           font=("Microsoft YaHei", 9), padx=8, pady=4)
        ga.pack(fill="x", padx=10, pady=4)
        self._action_btns = []

        def btn(text, cmd):
            b = tk.Button(ga, text=text, font=("Microsoft YaHei", 9),
                          relief="flat", bg="white", padx=14, pady=4,
                          command=cmd)
            self._action_btns.append(b)
            return b

        r1 = tk.Frame(ga, bg="#f5f5f5"); r1.pack(fill="x", pady=2)
        btn("备份存档", self._backup_saves).pack(side="left", padx=2)
        btn("恢复存档", self._restore_saves).pack(side="left", padx=2)
        r2 = tk.Frame(ga, bg="#f5f5f5"); r2.pack(fill="x", pady=2)
        btn("备份Steam凭证", self._backup_steam).pack(side="left", padx=2)
        btn("恢复Steam凭证", self._restore_steam).pack(side="left", padx=2)

        # ── progress ──
        self.pbar = ttk.Progressbar(self, mode="determinate", length=400)
        self.pbar.pack(fill="x", padx=10, pady=2); self.pbar.pack_forget()
        self.lbl_pct = tk.Label(self, text="", bg="#f5f5f5", fg="gray")
        self.lbl_pct.pack()

        # ── history ──
        gh = tk.LabelFrame(self, text="历史存档", bg="#f5f5f5",
                           font=("Microsoft YaHei", 9), padx=8, pady=4)
        gh.pack(fill="both", expand=True, padx=10, pady=4)
        hcols = ("时间", "大小")
        self.tree = ttk.Treeview(gh, columns=hcols, show="headings", height=5)
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

    def update_info(self):
        dd = self.app.data_drive; sp = self.app.steam_path
        games = config_manager.get_games()
        self.lbl_disk.config(text=f"数据盘: {dd} (已连接)" if dd else "数据盘: 未检测到",
                             fg="green" if dd else "red")
        self.lbl_steam.config(text=f"Steam: {sp}" if sp else "Steam: 未找到",
                              fg="green" if sp else "red")
        if games:
            self.lbl_save.config(
                text=f"已配置 {len(games)} 款游戏",
                fg="green")
            self.btn_discover.config(text="添加游戏")
        else:
            self.lbl_save.config(text="存档: 未配置（启动游戏后点[添加游戏]）", fg="red")
            self.btn_discover.config(text="添加游戏")
        self._refresh_game_list()

    # ── game list ───────────────────────────────────────────
    def _refresh_game_list(self):
        self.game_tree.delete(*self.game_tree.get_children())
        dd = self.app.data_drive
        games = sorted(config_manager.get_games(), key=lambda g: g["name"].lower())
        saves_root = os.path.join(dd, "GameDataKeeper", "Saves") if dd else ""
        for game in games:
            for sp in game.get("save_paths", []):
                sd = os.path.join(saves_root, game["backup_dir"], sp["name"]) if dd else ""
                zips = backup.list_all(sd) if dd and os.path.exists(sd) else []
                count = len(zips)
                last = zips[0]["time"] if zips else "暂无"
                total = sum(z["size"] for z in zips)
                self.game_tree.insert("", "end",
                    values=(game["name"], sp["name"], count, last,
                            f"{total/(1024*1024):.1f} MB" if total else "—"),
                    tags=(sd,))
        # 默认选中第一行
        if self.game_tree.get_children():
            self.game_tree.selection_set(self.game_tree.get_children()[0])
        self._refresh_history()

    def _open_backup_dir(self):
        sel = self.game_tree.selection()
        if sel:
            d = self.game_tree.item(sel[0], "tags")[0]
        else:
            dd = self.app.data_drive
            if not dd: return
            d = os.path.join(dd, "GameDataKeeper", "Saves")
            if not os.path.exists(d): os.makedirs(d, exist_ok=True)
        os.startfile(d)

    def _open_save_dir(self):
        games = config_manager.get_games()
        if not games:
            messagebox.showinfo("提示", "请先添加游戏（启动游戏后点[添加游戏]）"); return
        # 打开第一个游戏的存档目录
        p = games[0]["save_paths"][0]["path"]
        parent = os.path.dirname(p)
        if os.path.exists(parent):
            os.startfile(parent)
        else:
            messagebox.showinfo("提示", f"目录尚不存在:\n{parent}")

    # ── progress ────────────────────────────────────────────
    def _on_progress(self, done, total):
        pct = min(100, int(done * 100 / total))
        self.pbar.pack(fill="x", padx=10, pady=2); self.pbar["value"] = pct
        dm = done/(1024*1024); tm = total/(1024*1024)
        self.lbl_pct.config(text=f"{dm:.0f} MB / {tm:.0f} MB  ({pct}%)")
        if pct >= 100: self.pbar.pack_forget(); self.lbl_pct.config(text="完成")

    # ── helpers ──────────────────────────────────────────────
    def _check_game(self):
        if not config_manager.get_games():
            messagebox.showinfo("未配置", "请先启动游戏，然后点击 [添加游戏] 自动配置。")
            return False
        return True

    def _check_disk_steam(self):
        if not self.app.data_drive:
            messagebox.showinfo("数据盘未连接", "请插入数据盘后重试。")
            return False
        if not self.app.steam_path:
            messagebox.showinfo("Steam未找到", "请确保Steam已安装。")
            return False
        return True

    def _get_selected_game(self):
        """返回用户选中的游戏，未选择则默认第一个"""
        sel = self.game_tree.selection()
        if sel:
            game_name = self.game_tree.item(sel[0], "values")[0]
            for g in config_manager.get_games():
                if g["name"] == game_name:
                    return g
        games = config_manager.get_games()
        return games[0] if games else None

    def _confirm(self, title, msg):
        return messagebox.askyesno(title, msg)

    # ── operations ──────────────────────────────────────────
    def _backup_steam(self):
        if not self._check_disk_steam(): return
        if not self._confirm("确认", "备份 Steam 登录凭证到数据盘？"):
            self.app.set_status("已取消"); return
        dd=self.app.data_drive; sp=self.app.steam_path
        def done(_): self.app.set_status("Steam凭证已备份", "green")
        self.app.run_async(lambda: steam.backup(sp, dd),
                           on_done=done, status="正在备份 Steam 凭证...")

    def _restore_steam(self):
        if not self._check_disk_steam(): return
        dd=self.app.data_drive; sp=self.app.steam_path
        if steam.is_running():
            if not messagebox.askyesno("Steam 正在运行", "需要关闭Steam，是否继续？"):
                self.app.set_status("已取消"); return
            steam.kill()
        if not self._confirm("确认", "从数据盘恢复 Steam 登录凭证？\n将覆盖当前 Steam 登录状态。"):
            self.app.set_status("已取消"); return
        def done(_): self.app.set_status("Steam凭证已恢复", "green")
        self.app.run_async(lambda: (steam.restore(sp, dd), steam.launch(sp)),
                           on_done=done, status="正在恢复 Steam 凭证...")

    def _backup_saves(self):
        if not self._check_disk_steam() or not self._check_game(): return
        game = self._get_selected_game()
        if not game: return
        # 安全检查：源目录存在且有文件
        for sp in game.get("save_paths", []):
            p = sp["path"]
            if not os.path.exists(p):
                if not self._confirm("警告", f"存档目录不存在:\n{p}\n\n可能游戏尚未创建存档。\n仍要继续备份？"):
                    self.app.set_status("已取消"); return
            elif not os.listdir(p):
                if not self._confirm("警告", f"存档目录为空:\n{p}\n\n可能游戏尚未创建存档。\n仍要继续备份？"):
                    self.app.set_status("已取消"); return
        if not self._confirm("确认", f"备份 [ {game['name']} ] 的存档到数据盘？"):
            self.app.set_status("已取消"); return
        dd=self.app.data_drive; root=os.path.join(dd, "GameDataKeeper", "Saves")
        def task():
            for sp in game.get("save_paths", []):
                backup.backup(sp["path"], os.path.join(root, game["backup_dir"], sp["name"]),
                              on_progress=self._on_progress)
        def done(_): self.app.set_status(f"[{game['name']}] 存档已备份", "green")
        self.app.run_async(task, on_done=done, status="正在备份存档...")

    def _restore_saves(self):
        if not self._check_disk_steam() or not self._check_game(): return
        game = self._get_selected_game()
        if not game: return
        if not self._confirm("确认", f"从数据盘恢复 [ {game['name']} ] 的存档？\n将覆盖当前游戏存档！"):
            self.app.set_status("已取消"); return
        dd=self.app.data_drive; root=os.path.join(dd, "GameDataKeeper", "Saves")
        def task():
            for sp in game.get("save_paths", []):
                backup.restore(sp["path"], os.path.join(root, game["backup_dir"], sp["name"]),
                               on_progress=self._on_progress)
        def done(_): self.app.set_status(f"[{game['name']}] 存档已恢复", "green")
        self.app.run_async(task, on_done=done, status="正在恢复存档...")

    def _discover(self):
        g = discovery.detect_running()
        if g:
            if not messagebox.askyesno("确认", f"检测到: {g['folder']}\n{g['root']}\n\n搜索存档目录？"): return
            dirs = discovery.find_save_dirs(g["root"])
            if dirs:
                self._save_discovery(g, dirs)
                return
            messagebox.showwarning("未发现", "找到游戏进程但未添加游戏目录。\n请在弹出窗口中手动输入存档路径。")

        # 检测失败 → 诊断 + 手动输入
        diag = discovery.diag_processes()  # 返回当前可见进程列表
        msg = "未检测到正在运行的 Steam 游戏。\n\n"
        if diag:
            msg += "当前可见进程（前15个有路径的）:\n"
            msg += diag + "\n"
        msg += "请手动输入游戏存档路径\n（例如 Z:\\steam\\steamapps\\common\\The Scroll Of Taiwu\\SaveGames）:"
        path = self._ask_path(msg)
        if path:
            safe = os.path.basename(os.path.dirname(path))
            config_manager.add_game(safe, safe, [{"name": "手动指定", "path": path, "description": ""}])
            dd = self.app.data_drive
            if dd:
                os.makedirs(os.path.join(dd, "GameDataKeeper", "Saves", safe, "手动指定"), exist_ok=True)
            self.app.refresh_info()
            messagebox.showinfo("完成", f"已配置存档路径:\n{path}")

    def _save_discovery(self, game, dirs):
        paths = [{"name": d["name"], "path": d["path"], "description": "自动发现"} for d in dirs]
        config_manager.add_game(game["folder"], game["folder"], paths)
        dd = self.app.data_drive
        if dd:
            for d in dirs:
                os.makedirs(os.path.join(dd, "GameDataKeeper", "Saves",
                    game["folder"].replace(" ","_"), d["name"]), exist_ok=True)
        self.app.refresh_info()
        messagebox.showinfo("完成", f"已添加 {game['folder']}\n{len(dirs)} 个存档目录")

    def _ask_path(self, prompt):
        """弹窗让用户输入路径"""
        import tkinter.simpledialog as sd
        return sd.askstring("手动配置存档", prompt)

    def _refresh_history(self):
        self.tree.delete(*self.tree.get_children())
        dd = self.app.data_drive
        if not dd: return
        game = self._get_selected_game()
        if not game: return
        root = os.path.join(dd, "GameDataKeeper", "Saves", game["backup_dir"])
        if not os.path.exists(root): return
        for dn in sorted(os.listdir(root)):
            bd = os.path.join(root, dn)
            if os.path.isdir(bd):
                for z in backup.list_all(bd):
                    self.tree.insert("", "end",
                        values=(z["name"], f"{z['size']/(1024*1024):.1f} MB"),
                        tags=(os.path.join(bd, z["name"]),))

    def _restore_selected(self):
        sel = self.tree.selection()
        if not sel: messagebox.showinfo("提示", "请先选择一个备份"); return
        if not self._check_game(): return
        zip_path = self.tree.item(sel[0], "tags")[0]
        zip_name = self.tree.item(sel[0], "values")[0]
        # 通过 tags 中存储的路径反查游戏配置
        games = config_manager.get_games()
        target = None
        for g in games:
            for sp in g.get("save_paths", []):
                if zip_path.startswith(os.path.join(self.app.data_drive, "GameDataKeeper", "Saves", g["backup_dir"])):
                    target = sp["path"]; break
            if target: break
        if not target:
            messagebox.showinfo("错误", "无法确定恢复目标路径"); return

        def task():
            ok, info = backup.restore(target,
                os.path.dirname(zip_path), specific=zip_name, on_progress=self._on_progress)
            if ok: self.app.set_status("存档恢复完成", "green")
            else: self.app.set_status(f"恢复失败: {info}", "red")
        self.app.run_async(task, status="正在恢复...")
