"""
BaseGameTab — 通用游戏 Tab UI 基类。

组合通用子组件（状态面板、游戏列表、操作栏、历史存档、进度条），
子类只需声明游戏元信息并选择性覆盖钩子方法。
"""

import os
import tkinter as tk
from tkinter import ttk, messagebox

from shared import disk, config_manager, backup as backup_engine
from shared.exceptions import GameDataKeeperError


class BaseGameTab(tk.Frame):
    """通用游戏 Tab — 子类必须覆盖 GAME_NAME / GAME_ID"""

    # ── 子类必须覆盖 ──
    GAME_NAME: str = ""                # Tab 显示名称
    GAME_ID: str = ""                  # 唯一标识

    # ── 子类可选覆盖 ──
    SAVE_PATTERNS: list = []           # 存档目录匹配模式
    SUPPORT_CREDENTIAL: bool = False   # 是否支持凭证备份
    SUPPORT_DISCOVERY: bool = True     # 是否支持进程发现
    SUPPORT_PLATFORM: bool = False     # 是否有平台客户端（如 Steam）

    def __init__(self, parent, app):
        super().__init__(parent, bg="#f5f5f5")
        self.app = app
        self.core = self._create_core()
        self._build_ui()
        self.update_info()

    def _create_core(self):
        """子类覆盖：返回对应的 BaseGameCore 实例"""
        from games._base.base_core import BaseGameCore
        return BaseGameCore(self.app)

    # ── UI 构建（子类不应覆盖）────────────────────────

    def _build_ui(self):
        self._build_status_panel()
        self._build_game_list()
        self._build_action_bar()
        self._build_history_panel()
        self._build_progress()

    def _build_status_panel(self):
        """系统状态区"""
        g = tk.LabelFrame(self, text="系统状态", bg="#f5f5f5",
                          font=("Microsoft YaHei", 9), padx=8, pady=4)
        g.pack(fill="x", padx=10, pady=(10, 4))

        self.lbl_disk = tk.Label(g, text="存档目录: 检测中...", bg="#f5f5f5", anchor="w")
        self.lbl_disk.pack(fill="x")

        self.lbl_platform = tk.Label(g, text="", bg="#f5f5f5", anchor="w")
        if self.SUPPORT_PLATFORM:
            self.lbl_platform.pack(fill="x")

        f = tk.Frame(g, bg="#f5f5f5")
        f.pack(fill="x", pady=(2, 0))

        if self.SUPPORT_DISCOVERY:
            self.btn_discover = tk.Button(f, text="添加游戏", font=("Microsoft YaHei", 8),
                                          relief="flat", bg="#d0d0d0", padx=10,
                                          command=self._on_discover)
            self.btn_discover.pack(side="left")

        self.lbl_save = tk.Label(f, text="存档: 未配置", bg="#f5f5f5", anchor="w")
        self.lbl_save.pack(side="left", padx=10)

    def _build_game_list(self):
        """已配置的游戏列表"""
        sg = tk.LabelFrame(self, text="已配置的游戏", bg="#f5f5f5",
                           font=("Microsoft YaHei", 9), padx=8, pady=4)
        sg.pack(fill="x", padx=10, pady=4)

        cols = ("游戏", "存档类型", "备份数", "最近备份", "大小")
        self.game_tree = ttk.Treeview(sg, columns=cols, show="headings", height=3)
        for c, w in zip(cols, [140, 80, 60, 140, 80]):
            self.game_tree.heading(c, text=c)
            self.game_tree.column(c, width=w)
        self.game_tree.pack(side="left", fill="x", expand=True)
        self.game_tree.bind("<<TreeviewSelect>>", lambda e: self._refresh_history())

        gf = tk.Frame(sg, bg="#f5f5f5")
        gf.pack(side="right", padx=4)
        tk.Button(gf, text="打开目录", font=("Microsoft YaHei", 8),
                  relief="flat", bg="white", command=self._open_backup_dir).pack(pady=2)
        tk.Button(gf, text="查看存档", font=("Microsoft YaHei", 8),
                  relief="flat", bg="white", command=self._open_save_dir).pack(pady=2)
        tk.Button(gf, text="删除游戏", font=("Microsoft YaHei", 8),
                  relief="flat", bg="white", fg="red", command=self._delete_game).pack(pady=2)

    def _build_action_bar(self):
        """快捷操作区"""
        ga = tk.LabelFrame(self, text="快捷操作", bg="#f5f5f5",
                           font=("Microsoft YaHei", 9), padx=8, pady=4)
        ga.pack(fill="x", padx=10, pady=4)

        def btn(text, cmd):
            return tk.Button(ga, text=text, font=("Microsoft YaHei", 9),
                             relief="flat", bg="white", padx=14, pady=4, command=cmd)

        r1 = tk.Frame(ga, bg="#f5f5f5")
        r1.pack(fill="x", pady=2)
        btn("备份存档", self._on_backup_saves).pack(side="left", padx=2)
        btn("恢复存档", self._on_restore_saves).pack(side="left", padx=2)

        if self.SUPPORT_CREDENTIAL:
            r2 = tk.Frame(ga, bg="#f5f5f5")
            r2.pack(fill="x", pady=2)
            btn("备份凭证", self._on_backup_credential).pack(side="left", padx=2)
            btn("恢复凭证", self._on_restore_credential).pack(side="left", padx=2)

        # 子类扩展按钮
        extra = self.get_extra_actions()
        if extra:
            re = tk.Frame(ga, bg="#f5f5f5")
            re.pack(fill="x", pady=2)
            for label, cmd in extra:
                btn(label, cmd).pack(side="left", padx=2)

    def _build_history_panel(self):
        """历史存档区"""
        gh = tk.LabelFrame(self, text="历史存档", bg="#f5f5f5",
                           font=("Microsoft YaHei", 9), padx=8, pady=4)
        gh.pack(fill="both", expand=True, padx=10, pady=4)

        hcols = ("时间", "大小")
        self.tree = ttk.Treeview(gh, columns=hcols, show="headings", height=5)
        self.tree.heading("时间", text="时间")
        self.tree.heading("大小", text="大小")
        self.tree.column("时间", width=200)
        self.tree.column("大小", width=100)
        self.tree.pack(side="left", fill="both", expand=True)

        sb = ttk.Scrollbar(gh, orient="vertical", command=self.tree.yview)
        sb.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=sb.set)

        bf = tk.Frame(gh, bg="#f5f5f5")
        bf.pack(side="right", padx=4)
        tk.Button(bf, text="恢复选中", font=("Microsoft YaHei", 8),
                  relief="flat", bg="white", command=self._on_restore_selected).pack(pady=2)
        tk.Button(bf, text="刷新", font=("Microsoft YaHei", 8),
                  relief="flat", bg="white", command=self._refresh_history).pack(pady=2)

    def _build_progress(self):
        """进度条"""
        self.pbar = ttk.Progressbar(self, mode="determinate", length=400)
        self.pbar.pack(fill="x", padx=10, pady=2)
        self.pbar.pack_forget()
        self.lbl_pct = tk.Label(self, text="", bg="#f5f5f5", fg="gray")
        self.lbl_pct.pack()

    # ── 信息刷新 ──

    def update_info(self):
        """刷新所有状态显示"""
        dd = self.app.storage_root
        games = config_manager.get_games()

        self.lbl_disk.config(
            text=f"存档目录: {dd} (已连接)" if dd else "存档目录: 未检测到",
            fg="green" if dd else "red")

        if self.SUPPORT_PLATFORM:
            pp = self.core.find_platform_path()
            self.lbl_platform.config(
                text=f"{self.GAME_NAME}: {pp}" if pp else f"{self.GAME_NAME}: 未找到",
                fg="green" if pp else "red")

        if games:
            self.lbl_save.config(text=f"已配置 {len(games)} 款游戏", fg="green")
        else:
            self.lbl_save.config(text="存档: 未配置（启动游戏后点[添加游戏]）", fg="red")

        self._refresh_game_list()

    # ── 游戏列表 ──

    def _refresh_game_list(self):
        self.game_tree.delete(*self.game_tree.get_children())
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
                self.game_tree.insert("", "end",
                    values=(game["name"], sp["name"], count, last,
                            f"{total/(1024*1024):.1f} MB" if total else "—"),
                    tags=(sd,))

        if self.game_tree.get_children():
            self.game_tree.selection_set(self.game_tree.get_children()[0])
        self._refresh_history()

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

    def _open_backup_dir(self):
        sel = self.game_tree.selection()
        if sel:
            d = self.game_tree.item(sel[0], "tags")[0]
        else:
            dd = self.app.storage_root
            if not dd:
                return
            d = os.path.join(dd, "Saves")
            if not os.path.exists(d):
                os.makedirs(d, exist_ok=True)
        os.startfile(d)

    def _open_save_dir(self):
        game = self._get_selected_game()
        if not game:
            messagebox.showinfo("提示", "请先在已配置的游戏列表中选择一个游戏")
            return
        for sp in game.get("save_paths", []):
            parent = os.path.dirname(sp["path"])
            if os.path.exists(parent):
                os.startfile(parent)
                return
        messagebox.showinfo("提示", "存档目录尚不存在")

    def _delete_game(self):
        game = self._get_selected_game()
        if not game:
            messagebox.showinfo("提示", "请先在已配置的游戏列表中选择一个游戏")
            return
        if not self._confirm("确认删除", f"删除 [ {game['name']} ] 的配置？\n（不会删除已备份的存档文件）"):
            return
        config_manager.remove_game(game["backup_dir"])
        self.app.refresh_info()
        self.app.set_status(f"已删除 {game['name']}")

    # ── 进度条 ──

    def _on_progress(self, done, total):
        pct = min(100, int(done * 100 / total))
        self.pbar.pack(fill="x", padx=10, pady=2)
        self.pbar["value"] = pct
        dm = done / (1024 * 1024)
        tm = total / (1024 * 1024)
        self.lbl_pct.config(text=f"{dm:.0f} MB / {tm:.0f} MB  ({pct}%)")
        if pct >= 100:
            self.pbar.pack_forget()
            self.lbl_pct.config(text="完成")

    # ── 操作 ──

    def _on_backup_saves(self):
        if not self._check_storage() or not self._check_game():
            return
        game = self._get_selected_game()
        if not game:
            return

        # 安全检查
        for sp in game.get("save_paths", []):
            p = sp["path"]
            if not os.path.exists(p):
                if not self._confirm("警告", f"存档目录不存在:\n{p}\n\n可能游戏尚未创建存档。\n仍要继续备份？"):
                    self.app.set_status("已取消")
                    return
            elif not os.listdir(p):
                if not self._confirm("警告", f"存档目录为空:\n{p}\n\n可能游戏尚未创建存档。\n仍要继续备份？"):
                    self.app.set_status("已取消")
                    return

        if not self._confirm("确认", f"备份 [ {game['name']} ] 的存档到存档目录？"):
            self.app.set_status("已取消")
            return

        def task():
            try:
                self.core.backup_saves(game, on_progress=self._on_progress)
                return True
            except GameDataKeeperError as e:
                return e

        def done(result):
            if result is True:
                self.app.set_status(f"[{game['name']}] 存档已备份", "green")
                self._refresh_game_list()
            elif isinstance(result, GameDataKeeperError):
                messagebox.showerror("备份失败", str(result))
                self.app.set_status(f"备份失败: {result}", "red")

        self.app.run_async(task, on_done=done, status="正在备份存档...")

    def _on_restore_saves(self):
        if not self._check_storage() or not self._check_game():
            return
        game = self._get_selected_game()
        if not game:
            return
        if not self._confirm("确认", f"从存档目录恢复 [ {game['name']} ] 的存档？\n将覆盖当前游戏存档！"):
            self.app.set_status("已取消")
            return

        def task():
            try:
                self.core.restore_saves(game, on_progress=self._on_progress)
                return True
            except GameDataKeeperError as e:
                return e

        def done(result):
            if result is True:
                self.app.set_status(f"[{game['name']}] 存档已恢复", "green")
            elif isinstance(result, GameDataKeeperError):
                messagebox.showerror("恢复失败", str(result))

        self.app.run_async(task, on_done=done, status="正在恢复存档...")

    def _on_backup_credential(self):
        if not self._check_storage():
            return
        if not self._confirm("确认", f"备份 {self.GAME_NAME} 凭证到存档目录？"):
            self.app.set_status("已取消")
            return

        def task():
            try:
                return self.core.backup_credential()
            except GameDataKeeperError as e:
                return e

        def done(result):
            if isinstance(result, GameDataKeeperError):
                messagebox.showerror("备份失败", str(result))
            else:
                self.app.set_status(f"{self.GAME_NAME}凭证已备份", "green")

        self.app.run_async(task, on_done=done, status=f"正在备份 {self.GAME_NAME} 凭证...")

    def _on_restore_credential(self):
        if not self._check_storage():
            return

        if self.core.is_platform_running():
            if not messagebox.askyesno(f"{self.GAME_NAME} 正在运行",
                                       f"需要关闭{self.GAME_NAME}，是否继续？"):
                self.app.set_status("已取消")
                return
            self.core.kill_platform()

        if not self._confirm("确认", f"从存档目录恢复 {self.GAME_NAME} 凭证？\n将覆盖当前登录状态。"):
            self.app.set_status("已取消")
            return

        def task():
            try:
                result = self.core.restore_credential()
                self.core.launch_platform()
                return result
            except GameDataKeeperError as e:
                return e

        def done(result):
            if isinstance(result, GameDataKeeperError):
                messagebox.showerror("恢复失败", str(result))
            else:
                self.app.set_status(f"{self.GAME_NAME}凭证已恢复", "green")

        self.app.run_async(task, on_done=done, status=f"正在恢复 {self.GAME_NAME} 凭证...")

    def _on_discover(self):
        g = self.core.detect_running()
        if g:
            if not messagebox.askyesno("确认", f"检测到: {g['folder']}\n{g['root']}\n\n搜索存档目录？"):
                return
            dirs = self.core.find_save_dirs(g["root"])
            if dirs:
                self._save_discovery(g, dirs)
                return
            messagebox.showwarning("未发现", "找到游戏进程但未发现存档目录。\n请在弹出窗口中手动输入存档路径。")

        # 检测失败 → 手动输入
        diag = self.core.diag_processes() if hasattr(self.core, 'diag_processes') else ""
        msg = "未检测到正在运行的游戏。\n\n"
        if diag:
            msg += "当前可见进程（前15个有路径的）:\n" + diag + "\n"
        msg += "请手动输入游戏存档路径:"
        path = self._ask_path(msg)
        if path:
            safe = os.path.basename(os.path.dirname(path))
            config_manager.add_game(safe, safe, [{"name": "手动指定", "path": path, "description": ""}])
            dd = self.app.storage_root
            if dd:
                os.makedirs(os.path.join(dd, "Saves", safe, "手动指定"), exist_ok=True)
            self.app.refresh_info()
            messagebox.showinfo("完成", f"已配置存档路径:\n{path}")

    def _save_discovery(self, game, dirs):
        paths = [{"name": d["name"], "path": d["path"], "description": "自动发现"} for d in dirs]
        config_manager.add_game(game["folder"], game["folder"], paths)
        dd = self.app.storage_root
        if dd:
            for d in dirs:
                os.makedirs(os.path.join(dd, "Saves",
                    game["folder"].replace(" ", "_"), d["name"]), exist_ok=True)
        self.app.refresh_info()
        messagebox.showinfo("完成", f"已添加 {game['folder']}\n{len(dirs)} 个存档目录")

    # ── 历史存档 ──

    def _refresh_history(self):
        self.tree.delete(*self.tree.get_children())
        dd = self.app.storage_root
        if not dd:
            return
        game = self._get_selected_game()
        if not game:
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

    def _on_restore_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("提示", "请先选择一个备份")
            return
        if not self._check_game():
            return
        zip_path = self.tree.item(sel[0], "tags")[0]
        zip_name = self.tree.item(sel[0], "values")[0]

        # 反查目标路径
        games = config_manager.get_games()
        target = None
        for g in games:
            for sp in g.get("save_paths", []):
                if zip_path.startswith(os.path.join(self.app.storage_root, "Saves", g["backup_dir"])):
                    target = sp["path"]
                    break
            if target:
                break
        if not target:
            messagebox.showinfo("错误", "无法确定恢复目标路径")
            return

        def task():
            try:
                import shutil
                backup_engine.restore(target, os.path.dirname(zip_path),
                                      specific=zip_name, on_progress=self._on_progress)
                self.app.set_status("存档恢复完成", "green")
            except GameDataKeeperError as e:
                self.app.set_status(f"恢复失败: {e}", "red")

        self.app.run_async(task, status="正在恢复...")

    # ── 工具方法 ──

    def _check_game(self):
        if not config_manager.get_games():
            messagebox.showinfo("未配置", "请先启动游戏，然后点击 [添加游戏] 自动配置。")
            return False
        return True

    def _check_storage(self):
        if self.SUPPORT_PLATFORM and not self.core.find_platform_path():
            messagebox.showinfo(f"{self.GAME_NAME}未找到", f"请确保{self.GAME_NAME}已安装。")
            return False
        return True

    def _confirm(self, title, msg):
        return messagebox.askyesno(title, msg)

    def _ask_path(self, prompt):
        import tkinter.simpledialog as sd
        return sd.askstring("手动配置存档", prompt)

    # ── 子类可覆盖的钩子 ──

    def get_extra_actions(self) -> list:
        """子类覆盖：返回 [(label, callback), ...] 额外操作按钮"""
        return []
