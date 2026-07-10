"""Steam Tab — 组合: StatusPanel + SaveListPanel + ActionBar + HistoryPanel"""

import os
import tkinter.messagebox as messagebox

from games._base.base_tab import BaseGameTab
from games._base.panels import StatusPanel, SaveListPanel, ActionBar, HistoryPanel
from games.steam.core import SteamCore
from shared import config_manager
from shared.exceptions import GameDataKeeperError


class SteamTab(BaseGameTab):
    GAME_NAME = "Steam"
    GAME_ID = "steam"
    SUPPORT_CREDENTIAL = True
    SUPPORT_DISCOVERY = True
    SUPPORT_PLATFORM = True

    def _create_core(self):
        return SteamCore(self.app)

    # ── 面板组合 ──────────────────────────────────────

    def _build_ui(self):
        # 1. 系统状态（含 Steam 路径 + 发现按钮）
        self.status = StatusPanel(self, self.app,
            platform_label=self._platform_status(),
            show_discovery=True,
            on_discover=self._on_discover)
        self.status.pack(fill="x", padx=10, pady=(10, 4))

        # 2. 游戏存档列表
        self.save_list = SaveListPanel(self, self.app,
            on_select=self._on_game_select)
        self.save_list.pack(fill="x", padx=10, pady=4)

        # 3. 操作按钮
        self.actions = ActionBar(self, actions=[
            {"label": "备份存档", "callback": self._on_backup_saves, "row": 0},
            {"label": "恢复存档", "callback": self._on_restore_saves, "row": 0},
            {"label": "备份Steam凭证", "callback": self._on_backup_credential, "row": 1},
            {"label": "恢复Steam凭证", "callback": self._on_restore_credential, "row": 1},
        ])
        self.actions.pack(fill="x", padx=10, pady=4)

        # 4. 历史存档
        self.history = HistoryPanel(self, self.app,
            on_restore=self._on_restore_history)
        self.history.pack(fill="both", expand=True, padx=10, pady=4)

    # ── 刷新 ──────────────────────────────────────────

    def update_info(self):
        self.status.lbl_disk.config(
            text=f"存档目录: {self.app.storage_root} (已连接)"
            if self.app.storage_root else "存档目录: 未检测到",
            fg="green" if self.app.storage_root else "red")
        self.status._platform_label = self._platform_status()
        sp = self.core.find_platform_path()
        self.status.lbl_platform.config(
            text=f"Steam: {sp}" if sp else "Steam: 未找到",
            fg="green" if sp else "red")
        games = config_manager.get_games()
        if games:
            self.status.lbl_save.config(text=f"已配置 {len(games)} 款游戏", fg="green")
        else:
            self.status.lbl_save.config(text="存档: 未配置（启动游戏后点[添加游戏]）", fg="red")
        self.save_list.refresh()
        self._on_game_select(self.save_list.get_selected_game())

    def _platform_status(self) -> str:
        sp = self.core.find_platform_path()
        return f"Steam: {sp}" if sp else "Steam: 未找到"

    def _on_game_select(self, game):
        self.history.refresh(game)

    # ── 存档备份/恢复 ─────────────────────────────────

    def _on_backup_saves(self):
        game = self.save_list.get_selected_game()
        if not game or not self._check_storage() or not self._check_game():
            return
        issues = self._validate_save_paths(game)
        if issues:
            msg = "\n".join(issues) + "\n\n仍要继续备份？"
            if not self._confirm("警告", msg):
                self.app.set_status("已取消"); return
        if not self._confirm("确认", f"备份 [ {game['name']} ] 的存档到存档目录？"):
            self.app.set_status("已取消"); return

        def task():
            try: self._do_backup_saves(game); return True
            except GameDataKeeperError as e: return e
        def done(r):
            if r is True:
                self.app.set_status(f"[{game['name']}] 存档已备份", "green")
                self.save_list.refresh()
                self.history.refresh(game)
            elif isinstance(r, GameDataKeeperError):
                messagebox.showerror("备份失败", str(r))
        self.app.run_async(task, on_done=done, status="正在备份存档...")

    def _on_restore_saves(self):
        game = self.save_list.get_selected_game()
        if not game or not self._check_storage() or not self._check_game():
            return
        if not self._confirm("确认",
                             f"从存档目录恢复 [ {game['name']} ] 的存档？\n将覆盖当前游戏存档！"):
            self.app.set_status("已取消"); return

        def task():
            try: self._do_restore_saves(game); return True
            except GameDataKeeperError as e: return e
        def done(r):
            if r is True: self.app.set_status(f"[{game['name']}] 存档已恢复", "green")
            elif isinstance(r, GameDataKeeperError): messagebox.showerror("恢复失败", str(r))
        self.app.run_async(task, on_done=done, status="正在恢复存档...")

    def _on_restore_history(self, zip_path, zip_name):
        """从历史面板恢复"""
        game = self.save_list.get_selected_game()
        if not game: return
        # 反查目标路径
        target = None
        for g in config_manager.get_games():
            for sp in g.get("save_paths", []):
                if zip_path.startswith(os.path.join(self.app.storage_root, "Saves", g["backup_dir"])):
                    target = sp["path"]; break
            if target: break
        if not target:
            messagebox.showinfo("错误", "无法确定恢复目标路径"); return

        def task():
            try: self._do_restore_from_zip(target, os.path.dirname(zip_path), zip_name)
            except GameDataKeeperError: pass
        self.app.run_async(task, status="正在恢复...")

    # ── Steam 凭证 ────────────────────────────────────

    def _on_backup_credential(self):
        if not self._check_storage(): return
        if not self._confirm("确认", "备份 Steam 登录凭证到存档目录？"):
            self.app.set_status("已取消"); return
        def task():
            try: return self._do_backup_credential()
            except GameDataKeeperError as e: return e
        def done(r):
            if isinstance(r, Exception): messagebox.showerror("备份失败", str(r))
            else: self.app.set_status("Steam凭证已备份", "green")
        self.app.run_async(task, on_done=done, status="正在备份 Steam 凭证...")

    def _on_restore_credential(self):
        if not self._check_storage(): return
        if self.core.is_platform_running():
            if not messagebox.askyesno("Steam 正在运行", "需要关闭Steam，是否继续？"):
                self.app.set_status("已取消"); return
            self.core.kill_platform()
        if not self._confirm("确认", "从存档目录恢复 Steam 登录凭证？\n将覆盖当前 Steam 登录状态。"):
            self.app.set_status("已取消"); return
        def task():
            try:
                r = self._do_restore_credential()
                self.core.launch_platform()
                return r
            except GameDataKeeperError as e: return e
        def done(r):
            if isinstance(r, Exception): messagebox.showerror("恢复失败", str(r))
            else: self.app.set_status("Steam凭证已恢复", "green")
        self.app.run_async(task, on_done=done, status="正在恢复 Steam 凭证...")

    # ── 游戏发现 ──────────────────────────────────────

    def _on_discover(self):
        g = self.core.detect_running()
        if g:
            if not messagebox.askyesno("确认", f"检测到: {g['folder']}\n{g['root']}\n\n搜索存档目录？"):
                return
            dirs = self.core.find_save_dirs(g["root"])
            if dirs:
                paths = [{"name": d["name"], "path": d["path"], "description": "自动发现"} for d in dirs]
                config_manager.add_game(g["folder"], g["folder"], paths)
                dd = self.app.storage_root
                if dd:
                    for d in dirs:
                        os.makedirs(os.path.join(dd, "Saves",
                            g["folder"].replace(" ", "_"), d["name"]), exist_ok=True)
                self.app.refresh_info()
                messagebox.showinfo("完成", f"已添加 {g['folder']}\n{len(dirs)} 个存档目录")
                return
            messagebox.showwarning("未发现", "找到游戏进程但未发现存档目录。\n请在弹出窗口中手动输入存档路径。")

        diag = self.core.diag_processes() if hasattr(self.core, 'diag_processes') else ""
        msg = "未检测到正在运行的 Steam 游戏。\n\n"
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
