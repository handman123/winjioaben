"""HsrPage — 组合: StatusCard + ActionCard + HistoryCard
AccountCard 待 HsrCore 实现 SupportsMultiAccount 后加入。
"""

import os
import tkinter.messagebox as messagebox

from games._base.page import Page
from games.hsr.ui.status_card import StatusCard
from games.hsr.ui.action_card import ActionCard
from games.hsr.ui.history_card import HistoryCard
from games.hsr.core.manager import HsrCore
from shared import config_manager
from shared.exceptions import GameDataKeeperError


class HsrPage(Page):
    GAME_NAME = "崩坏:星穹铁道"
    GAME_ID = "honkai_star_rail"

    def _make_core(self):
        return HsrCore(self.app)

    def _build(self):
        self.status = self.add_card(StatusCard(self, self.app))
        self.actions = self.add_card(ActionCard(self,
            on_backup_saves=self._on_backup_saves,
            on_restore_saves=self._on_restore_saves))
        self.history = self.add_card(HistoryCard(self, self.app, on_restore=self._on_restore_history),
                                     fill="both", expand=True)

    def refresh(self):
        super().refresh()
        games = config_manager.get_games()
        g = games[0] if games else None
        self.history.load(g)

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
