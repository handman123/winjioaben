"""GenshinPage — 原神：InfoCard + AccountCard"""

import os
import tkinter.messagebox as messagebox

from games._base.page import Page
from games.genshin.ui.info_card import InfoCard
from games._shared.account_card import AccountCard
from games.genshin.core.manager import GenshinCore
from utils.exceptions import GameDataKeeperError, AccountExistsError


class GenshinPage(Page):
    GAME_NAME = "原神"
    GAME_ID = "genshin_impact"

    def _make_core(self):
        return GenshinCore(self.app)

    def _build(self):
        self.info = self.add_card(InfoCard(self, self.app, self.core))
        self.account = self.add_card(AccountCard(self, self.app, self.core,
            on_save=self._on_save,
            on_switch=self._on_switch,
            on_rename=self._on_rename,
            on_delete=self._on_delete))

    # ── 账号操作 ──────────────────────────────────────

    def _on_save(self):
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

    def _on_switch(self, name):
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

    def _on_rename(self, name):
        if not name: return
        nn = self._prompt_name(f"将 [{name}] 重命名为:")
        if not nn: return
        try: self.core.rename_account(name, nn); self.app.set_status(f"[{name}] → [{nn}]", "green"); self.account.refresh()
        except GameDataKeeperError as e: messagebox.showerror("失败", str(e))

    def _on_delete(self, name):
        if not name: return
        if not self._confirm("确认", f"删除 [{name}]？不可撤销。"): return
        try: self.core.delete_account(name); self.app.set_status(f"[{name}] 已删除", "green"); self.account.refresh()
        except GameDataKeeperError as e: messagebox.showerror("失败", str(e))
