"""GenshinPage — 组合: StatusCard + AccountCard + ActionCard + HistoryCard"""

import os
import tkinter.messagebox as messagebox

from games._base.page import Page
from games.genshin.ui.status_card import StatusCard
from games.genshin.ui.action_card import ActionCard
from games.genshin.ui.history_card import HistoryCard
from games._shared.account_card import AccountCard
from games.genshin.core.manager import GenshinCore
from shared import config_manager
from shared.exceptions import GameDataKeeperError, AccountExistsError


class GenshinPage(Page):
    GAME_NAME = "原神"
    GAME_ID = "genshin_impact"

    def _make_core(self):
        return GenshinCore(self.app)

    def _build(self):
        self.status = self.add_card(StatusCard(self, self.app))
        self.account = self.add_card(AccountCard(self, self.app, self.core,
            on_save=self._on_save_account,
            on_switch=self._on_switch_account,
            on_update=self._on_update_account,
            on_rename=self._on_rename_account,
            on_delete=self._on_delete_account))
        self.actions = self.add_card(ActionCard(self,
            on_backup_saves=self._on_backup_saves,
            on_restore_saves=self._on_restore_saves,
            on_save_account=self._on_save_account,
            on_switch_account=self._on_switch_account))
        self.history = self.add_card(HistoryCard(self, self.app, on_restore=self._on_restore_history),
                                     fill="both", expand=True)

    def refresh(self):
        super().refresh()
        games = config_manager.get_games()
        g = games[0] if games else None
        self.history.load(g)

    # ── 存档 ──────────────────────────────────────

    def _current_game(self):
        games = config_manager.get_games()
        return games[0] if games else None

    def _on_backup_saves(self):
        g = self._current_game()
        if not g: return
        if not self._confirm("确认", f"备份 [{g['name']}] 的存档？"): return
        def task():
            try: self._do_backup_saves(g); return True
            except GameDataKeeperError as e: return e
        def done(r):
            if r is True: self.app.set_status("存档已备份", "green"); self.history.load(g)
            elif isinstance(r, Exception): messagebox.showerror("失败", str(r))
        self.app.run_async(task, on_done=done, status="正在备份...")

    def _on_restore_saves(self):
        g = self._current_game()
        if not g: return
        if not self._confirm("确认", f"恢复 [{g['name']}] 的存档？\n将覆盖当前存档！"): return
        def task():
            try: self._do_restore_saves(g); return True
            except GameDataKeeperError as e: return e
        def done(r):
            if r is True: self.app.set_status("存档已恢复", "green")
            elif isinstance(r, Exception): messagebox.showerror("失败", str(r))
        self.app.run_async(task, on_done=done, status="正在恢复...")

    def _on_restore_history(self, zip_path):
        g = self._current_game()
        if not g: return
        target = None
        for gm in config_manager.get_games():
            for sp in gm.get("save_paths", []):
                if zip_path.startswith(os.path.join(self.app.storage_root, "Saves", gm["backup_dir"])):
                    target = sp["path"]; break
        if not target: messagebox.showinfo("错误", "无法确定恢复目标"); return
        def task():
            try: self._do_restore_zip(target, os.path.dirname(zip_path), os.path.basename(zip_path))
            except GameDataKeeperError: pass
        self.app.run_async(task, status="正在恢复...")

    # ── 账号 ──────────────────────────────────────

    def _on_save_account(self):
        name = self._prompt_name("新账号名称:")
        if not name: return
        def task():
            try: return self._do_backup_credential(name)
            except GameDataKeeperError as e: return e
        def done(r):
            if isinstance(r, GameDataKeeperError):
                if isinstance(r, AccountExistsError):
                    if messagebox.askyesno("已存在", f"[{name}] 已存在，覆盖？"):
                        self.app.run_async(
                            task=lambda: self.core.overwrite_credential(name),
                            on_done=lambda rr: self._on_overwrite(rr, name),
                            status="正在更新...")
                    else: self.app.set_status("已取消")
                else: messagebox.showerror("失败", str(r))
            else: self.app.set_status(f"[{name}] 已保存", "green"); self.account.refresh()
        self.app.run_async(task, on_done=done, status="正在保存...")

    def _on_overwrite(self, result, name):
        if isinstance(result, Exception): messagebox.showerror("失败", str(result))
        else: self.app.set_status(f"[{name}] 已更新", "green"); self.account.refresh()

    def _on_switch_account(self, name):
        if not name: return
        if not self._confirm("确认", f"切换到 [{name}]？\n当前登录状态将被覆盖。"): return
        if self.core.is_platform_running():
            if not messagebox.askyesno("游戏运行中", "需要关闭游戏，是否继续？"): return
            self.core.kill_platform()
        def task():
            try: return self._do_restore_credential(name)
            except GameDataKeeperError as e: return e
        def done(r):
            if isinstance(r, Exception): messagebox.showerror("失败", str(r))
            else: self.app.set_status(f"已切换到 [{name}]", "green")
        self.app.run_async(task, on_done=done, status="正在切换...")

    def _on_update_account(self, name):
        if not name: return
        if not self._confirm("确认", f"用当前登录覆盖 [{name}]？"): return
        self.app.run_async(
            task=lambda: self.core.overwrite_credential(name),
            on_done=lambda r: self._on_overwrite(r, name), status="正在更新...")

    def _on_rename_account(self, name):
        if not name: return
        nn = self._prompt_name(f"将 [{name}] 重命名为:")
        if not nn: return
        try: self.core.rename_account(name, nn); self.app.set_status(f"[{name}] → [{nn}]", "green"); self.account.refresh()
        except GameDataKeeperError as e: messagebox.showerror("失败", str(e))

    def _on_delete_account(self, name):
        if not name: return
        if not self._confirm("确认", f"删除 [{name}]？不可撤销。"): return
        try: self.core.delete_account(name); self.app.set_status(f"[{name}] 已删除", "green"); self.account.refresh()
        except GameDataKeeperError as e: messagebox.showerror("失败", str(e))
