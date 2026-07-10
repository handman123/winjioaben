"""崩坏:星穹铁道 Tab — 组合: StatusPanel + SaveListPanel + ActionBar + HistoryPanel
账号管理待 HsrCore 实现 SupportsMultiAccount 后加入。
"""

import os
import tkinter.messagebox as messagebox

from games._base.base_tab import BaseGameTab
from games._base.panels import StatusPanel, SaveListPanel, ActionBar, HistoryPanel
from games.hsr.core.manager import HsrCore
from shared import config_manager
from shared.exceptions import GameDataKeeperError


class HsrTab(BaseGameTab):
    GAME_NAME = "崩坏:星穹铁道"
    GAME_ID = "honkai_star_rail"
    SAVE_PATTERNS = ["SaveData", "ScreenShot"]
    SUPPORT_CREDENTIAL = False
    SUPPORT_DISCOVERY = False
    SUPPORT_PLATFORM = False

    def _create_core(self):
        return HsrCore(self.app)

    def _build_ui(self):
        # 1. 系统状态
        self.status = StatusPanel(self, self.app)
        self.status.pack(fill="x", padx=10, pady=(10, 4))

        # 2. 游戏存档列表
        self.save_list = SaveListPanel(self, self.app,
            on_select=self._on_game_select)
        self.save_list.pack(fill="x", padx=10, pady=4)

        # 3. 操作按钮
        self.actions = ActionBar(self, actions=[
            {"label": "备份存档", "callback": self._on_backup_saves, "row": 0},
            {"label": "恢复存档", "callback": self._on_restore_saves, "row": 0},
        ])
        self.actions.pack(fill="x", padx=10, pady=4)

        # 4. 历史存档
        self.history = HistoryPanel(self, self.app,
            on_restore=self._on_restore_history)
        self.history.pack(fill="both", expand=True, padx=10, pady=4)

    def update_info(self):
        dd = self.app.storage_root
        self.status.lbl_disk.config(
            text=f"存档目录: {dd} (已连接)" if dd else "存档目录: 未检测到",
            fg="green" if dd else "red")
        games = config_manager.get_games()
        self.status.lbl_save.config(
            text=f"已配置 {len(games)} 款游戏" if games else "暂未配置游戏存档",
            fg="green" if games else "gray")
        self.save_list.refresh()
        self._on_game_select(self.save_list.get_selected_game())

    def _on_game_select(self, game):
        self.history.refresh(game)

    # ── 存档备份/恢复 ─────────────────────────────────

    def _on_backup_saves(self):
        game = self.save_list.get_selected_game()
        if not game or not self._check_game():
            return
        issues = self._validate_save_paths(game)
        if issues:
            if not self._confirm("警告", "\n".join(issues) + "\n\n仍要继续备份？"):
                self.app.set_status("已取消"); return
        if not self._confirm("确认", f"备份 [ {game['name']} ] 的存档到存档目录？"):
            self.app.set_status("已取消"); return

        def task():
            try: self._do_backup_saves(game); return True
            except GameDataKeeperError as e: return e
        def done(r):
            if r is True:
                self.app.set_status("存档已备份", "green")
                self.save_list.refresh(); self.history.refresh(game)
            elif isinstance(r, GameDataKeeperError):
                messagebox.showerror("备份失败", str(r))
        self.app.run_async(task, on_done=done, status="正在备份存档...")

    def _on_restore_saves(self):
        game = self.save_list.get_selected_game()
        if not game or not self._check_game():
            return
        if not self._confirm("确认", f"恢复 [ {game['name']} ] 的存档？\n将覆盖当前游戏存档！"):
            self.app.set_status("已取消"); return

        def task():
            try: self._do_restore_saves(game); return True
            except GameDataKeeperError as e: return e
        def done(r):
            if r is True: self.app.set_status("存档已恢复", "green")
            elif isinstance(r, GameDataKeeperError): messagebox.showerror("恢复失败", str(r))
        self.app.run_async(task, on_done=done, status="正在恢复存档...")

    def _on_restore_history(self, zip_path, zip_name):
        game = self.save_list.get_selected_game()
        if not game: return
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
