"""原神 Tab — 组合: StatusPanel + AccountPanel + SaveListPanel + ActionBar + HistoryPanel"""

import os
import tkinter.messagebox as messagebox

from games._base.base_tab import BaseGameTab
from games._base.panels import StatusPanel, SaveListPanel, ActionBar, HistoryPanel, AccountPanel
from games.genshin.core.manager import GenshinCore
from shared import config_manager
from shared.exceptions import GameDataKeeperError, AccountExistsError


class GenshinTab(BaseGameTab):
    GAME_NAME = "原神"
    GAME_ID = "genshin_impact"
    SAVE_PATTERNS = ["SaveData", "ScreenShot"]
    SUPPORT_CREDENTIAL = True
    SUPPORT_DISCOVERY = False
    SUPPORT_PLATFORM = False

    def _create_core(self):
        return GenshinCore(self.app)

    # ── 面板组合 ──────────────────────────────────────

    def _build_ui(self):
        # 1. 系统状态（无平台/无发现按钮）
        self.status = StatusPanel(self, self.app)
        self.status.pack(fill="x", padx=10, pady=(10, 4))

        # 2. 账号管理（core 实现 SupportsMultiAccount 接口）
        self.account = AccountPanel(self, self.app, self.core,
            on_save=self._on_save_account,
            on_switch=self._on_switch_account,
            on_update=self._on_update_account,
            on_rename=self._on_rename_account,
            on_delete=self._on_delete_account)
        self.account.pack(fill="x", padx=10, pady=4)

        # 3. 游戏存档列表
        self.save_list = SaveListPanel(self, self.app,
            on_select=self._on_game_select)
        self.save_list.pack(fill="x", padx=10, pady=4)

        # 4. 操作按钮
        self.actions = ActionBar(self, actions=[
            {"label": "备份存档", "callback": self._on_backup_saves, "row": 0},
            {"label": "恢复存档", "callback": self._on_restore_saves, "row": 0},
            {"label": "保存当前账号", "callback": self._on_save_account, "row": 1},
            {"label": "切换账号", "callback": self._on_switch_account, "row": 1},
        ])
        self.actions.pack(fill="x", padx=10, pady=4)

        # 5. 历史存档
        self.history = HistoryPanel(self, self.app,
            on_restore=self._on_restore_history)
        self.history.pack(fill="both", expand=True, padx=10, pady=4)

    # ── 刷新 ──────────────────────────────────────────

    def update_info(self):
        dd = self.app.storage_root
        self.status.lbl_disk.config(
            text=f"存档目录: {dd} (已连接)" if dd else "存档目录: 未检测到",
            fg="green" if dd else "red")
        games = config_manager.get_games()
        if games:
            self.status.lbl_save.config(text=f"已配置 {len(games)} 款游戏", fg="green")
        else:
            self.status.lbl_save.config(text="暂未配置游戏存档", fg="gray")
        self.account.refresh()
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

    # ── 账号管理 ──────────────────────────────────────

    def _on_save_account(self):
        name = self._prompt_account_name("请输入新账号名称:")
        if not name: return
        self.app.run_async(
            task=lambda: self._do_backup_credential(name),
            on_done=lambda r: self._on_account_saved(r, name),
            status="正在保存账号凭证..."
        )

    def _on_account_saved(self, result, name):
        if isinstance(result, GameDataKeeperError):
            if isinstance(result, AccountExistsError):
                if messagebox.askyesno("账号已存在", f"[{name}] 已存在，是否覆盖更新？"):
                    self.app.run_async(
                        task=lambda: self.core.overwrite_credential(name),
                        on_done=lambda r: self._on_account_overwritten(r, name),
                        status="正在更新账号凭证...")
                else: self.app.set_status("已取消")
            else: messagebox.showerror("保存失败", str(result))
        else:
            self.app.set_status(f"账号 [{name}] 已保存", "green")
            self.account.refresh()

    def _on_account_overwritten(self, result, name):
        if isinstance(result, Exception):
            messagebox.showerror("更新失败", str(result))
        else:
            self.app.set_status(f"账号 [{name}] 已更新", "green")
            self.account.refresh()

    def _on_switch_account(self, name):
        if not name: return
        if not self._confirm("确认切换", f"将切换到账号 [{name}]，当前登录状态将被覆盖。\n\n是否继续？"):
            self.app.set_status("已取消"); return
        if self.core.is_platform_running():
            if not messagebox.askyesno("游戏正在运行", "原神正在运行，需要先关闭。是否继续？"):
                self.app.set_status("已取消"); return
            self.core.kill_platform()

        def task():
            try: return self._do_restore_credential(name)
            except GameDataKeeperError as e: return e
        def done(r):
            if isinstance(r, Exception): messagebox.showerror("切换失败", str(r))
            else: self.app.set_status(f"已切换到 [{name}]，启动原神即可自动登录", "green")
        self.app.run_async(task, on_done=done, status=f"正在切换到 [{name}]...")

    def _on_update_account(self, name):
        if not name: return
        if not self._confirm("确认更新", f"将用当前登录状态覆盖 [{name}] 的凭证。\n\n是否继续？"):
            self.app.set_status("已取消"); return
        self.app.run_async(
            task=lambda: self.core.overwrite_credential(name),
            on_done=lambda r: self._on_account_overwritten(r, name),
            status=f"正在更新 [{name}]...")

    def _on_rename_account(self, name):
        if not name: return
        new_name = self._prompt_account_name(f"将 [{name}] 重命名为:")
        if not new_name: return
        try:
            self.core.rename_account(name, new_name)
            self.app.set_status(f"[{name}] → [{new_name}]", "green")
            self.account.refresh()
        except GameDataKeeperError as e:
            messagebox.showerror("重命名失败", str(e))

    def _on_delete_account(self, name):
        if not name: return
        if not self._confirm("确认删除", f"删除账号 [{name}] 的凭证？\n此操作不可撤销。"):
            self.app.set_status("已取消"); return
        try:
            self.core.delete_account(name)
            self.app.set_status(f"账号 [{name}] 已删除", "green")
            self.account.refresh()
        except GameDataKeeperError as e:
            messagebox.showerror("删除失败", str(e))
