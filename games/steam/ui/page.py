"""SteamPage — 组合: StatusCard + GameListCard + ActionCard + HistoryCard"""

import os
import tkinter.messagebox as messagebox

from games._base.page import Page
from games.steam.ui.status_card import StatusCard
from games.steam.ui.game_list_card import GameListCard
from games.steam.ui.action_card import ActionCard
from games.steam.ui.history_card import HistoryCard
from games.steam.core import SteamCore
from shared import config_manager
from shared.exceptions import GameDataKeeperError


class SteamPage(Page):
    GAME_NAME = "Steam"
    GAME_ID = "steam"

    def _make_core(self):
        return SteamCore(self.app)

    def _build(self):
        self.status = self.add_card(StatusCard(self, self.app, on_discover=self._on_discover))
        self.game_list = self.add_card(GameListCard(self, self.app, on_select=self._on_game_select))
        self.actions = self.add_card(ActionCard(self,
            on_backup_saves=self._on_backup_saves,
            on_restore_saves=self._on_restore_saves,
            on_backup_cred=self._on_backup_cred,
            on_restore_cred=self._on_restore_cred))
        self.history = self.add_card(HistoryCard(self, self.app, on_restore=self._on_restore_history),
                                     fill="both", expand=True)

    def refresh(self):
        super().refresh()

    def _on_game_select(self, game):
        self.history.load(game)

    # ── 存档 ──────────────────────────────────────

    def _on_backup_saves(self):
        g = self.game_list.get_selected()
        if not g:
            return
        issues = self._validate_save_paths(g)
        if issues and not self._confirm("警告", "\n".join(issues) + "\n\n仍要继续？"):
            return
        if not self._confirm("确认", f"备份 [{g['name']}] 的存档？"):
            return

        def task():
            try: self._do_backup_saves(g); return True
            except GameDataKeeperError as e: return e
        def done(r):
            if r is True:
                self.app.set_status("存档已备份", "green")
                self.game_list.refresh(); self.history.load(g)
            elif isinstance(r, Exception): messagebox.showerror("失败", str(r))
        self.app.run_async(task, on_done=done, status="正在备份...")

    def _on_restore_saves(self):
        g = self.game_list.get_selected()
        if not g:
            return
        if not self._confirm("确认", f"恢复 [{g['name']}] 的存档？\n将覆盖当前存档！"):
            return

        def task():
            try: self._do_restore_saves(g); return True
            except GameDataKeeperError as e: return e
        def done(r):
            if r is True: self.app.set_status("存档已恢复", "green")
            elif isinstance(r, Exception): messagebox.showerror("失败", str(r))
        self.app.run_async(task, on_done=done, status="正在恢复...")

    def _on_restore_history(self, zip_path):
        g = self.game_list.get_selected()
        if not g:
            return
        target = None
        for gm in config_manager.get_games():
            for sp in gm.get("save_paths", []):
                if zip_path.startswith(os.path.join(self.app.storage_root, "Saves", gm["backup_dir"])):
                    target = sp["path"]; break
        if not target:
            messagebox.showinfo("错误", "无法确定恢复目标"); return

        def task():
            try: self._do_restore_zip(target, os.path.dirname(zip_path),
                                       os.path.basename(zip_path))
            except GameDataKeeperError: pass
        self.app.run_async(task, status="正在恢复...")

    # ── Steam 凭证 ────────────────────────────────

    def _on_backup_cred(self):
        if not self.core.find_platform_path():
            messagebox.showinfo("提示", "Steam 未安装"); return
        if not self._confirm("确认", "备份 Steam 凭证？"):
            return

        def task():
            try: return self._do_backup_credential()
            except GameDataKeeperError as e: return e
        def done(r):
            if isinstance(r, Exception): messagebox.showerror("失败", str(r))
            else: self.app.set_status("Steam凭证已备份", "green")
        self.app.run_async(task, on_done=done, status="正在备份...")

    def _on_restore_cred(self):
        if not self.core.find_platform_path():
            return
        if self.core.is_platform_running():
            if not messagebox.askyesno("Steam 正在运行", "需要关闭 Steam，是否继续？"):
                return
            self.core.kill_platform()
        if not self._confirm("确认", "恢复 Steam 凭证？\n将覆盖当前登录状态。"):
            return

        def task():
            try:
                r = self._do_restore_credential()
                self.core.launch_platform()
                return r
            except GameDataKeeperError as e: return e
        def done(r):
            if isinstance(r, Exception): messagebox.showerror("失败", str(r))
            else: self.app.set_status("Steam凭证已恢复", "green")
        self.app.run_async(task, on_done=done, status="正在恢复...")

    # ── 发现 ──────────────────────────────────────

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
                        os.makedirs(os.path.join(dd, "Saves", g["folder"].replace(" ", "_"), d["name"]),
                                    exist_ok=True)
                self.app.refresh()
                messagebox.showinfo("完成", f"已添加 {g['folder']}\n{len(dirs)} 个存档目录")
                return
            messagebox.showwarning("未发现", "找到进程但未发现存档目录")

        diag = self.core.diag_processes() if hasattr(self.core, 'diag_processes') else ""
        msg = "未检测到运行中的 Steam 游戏。\n\n"
        if diag:
            msg += "当前进程:\n" + diag + "\n"
        msg += "请手动输入存档路径:"
        path = self._ask_path(msg)
        if path:
            safe = os.path.basename(os.path.dirname(path))
            config_manager.add_game(safe, safe, [{"name": "手动指定", "path": path, "description": ""}])
            dd = self.app.storage_root
            if dd:
                os.makedirs(os.path.join(dd, "Saves", safe, "手动指定"), exist_ok=True)
            self.app.refresh()
            messagebox.showinfo("完成", f"已配置: {path}")
