"""原神 Tab — 多账号凭证管理 + 游戏存档备份"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

from games._base.base_tab import BaseGameTab
from games.genshin.core.manager import GenshinCore
from shared.exceptions import GameDataKeeperError, AccountNotFoundError, AccountExistsError


class GenshinTab(BaseGameTab):
    GAME_NAME = "原神"
    GAME_ID = "genshin_impact"
    SAVE_PATTERNS = ["SaveData", "ScreenShot"]
    SUPPORT_CREDENTIAL = True
    SUPPORT_DISCOVERY = False
    SUPPORT_PLATFORM = False

    def _create_core(self):
        return GenshinCore(self.app)

    # ── UI 构建（覆盖：在状态面板后插入账号面板）────────

    def _build_ui(self):
        self._build_status_panel()
        self._build_account_panel()    # ← 新增
        self._build_game_list()
        self._build_action_bar()
        self._build_history_panel()
        self._build_progress()

    def _build_account_panel(self):
        """账号管理区"""
        ag = tk.LabelFrame(self, text="账号管理", bg="#f5f5f5",
                           font=("Microsoft YaHei", 9), padx=8, pady=4)
        ag.pack(fill="x", padx=10, pady=4)

        cols = ("账号名", "最近更新")
        self.account_tree = ttk.Treeview(ag, columns=cols, show="headings", height=3)
        self.account_tree.heading("账号名", text="账号名")
        self.account_tree.heading("最近更新", text="最近更新")
        self.account_tree.column("账号名", width=150)
        self.account_tree.column("最近更新", width=160)
        self.account_tree.pack(side="left", fill="x", expand=True)

        # 右侧按钮
        bf = tk.Frame(ag, bg="#f5f5f5")
        bf.pack(side="right", padx=4)

        def abtn(text, cmd):
            return tk.Button(bf, text=text, font=("Microsoft YaHei", 8),
                             relief="flat", bg="white", padx=4, pady=2,
                             width=12, command=cmd)

        abtn("保存当前账号", self._on_save_account).pack(pady=1)
        abtn("切换到此账号", self._on_switch_account).pack(pady=1)
        abtn("更新此账号", self._on_update_account).pack(pady=1)
        abtn("重命名", self._on_rename_account).pack(pady=1)
        abtn("删除账号", self._on_delete_account).pack(pady=1)

    # ── 刷新 ──

    def update_info(self):
        """刷新状态 + 游戏列表 + 账号列表"""
        super().update_info()
        self._refresh_account_list()

    def _refresh_account_list(self):
        self.account_tree.delete(*self.account_tree.get_children())
        for acc in self.core.list_accounts():
            self.account_tree.insert("", "end",
                values=(acc["name"], acc.get("updated_at", acc.get("created_at", ""))))

    # ── 账号操作 ──

    def _get_selected_account(self) -> str | None:
        sel = self.account_tree.selection()
        if not sel:
            return None
        return self.account_tree.item(sel[0], "values")[0]

    def _on_save_account(self):
        """保存当前登录为新的账号"""
        name = self._prompt_account_name("请输入新账号名称:")
        if not name:
            return
        self.app.run_async(
            task=lambda: self.core.backup_credential(name),
            on_done=lambda r: self._on_account_saved(r, name),
            status="正在保存账号凭证..."
        )

    def _on_account_saved(self, result, name):
        if isinstance(result, GameDataKeeperError):
            if isinstance(result, AccountExistsError):
                if messagebox.askyesno("账号已存在",
                                       f"[{name}] 已存在，是否覆盖更新？"):
                    self.app.run_async(
                        task=lambda: self.core.overwrite_credential(name),
                        on_done=lambda r: self._on_account_overwritten(r, name),
                        status="正在更新账号凭证..."
                    )
                else:
                    self.app.set_status("已取消")
            else:
                messagebox.showerror("保存失败", str(result))
        else:
            self.app.set_status(f"账号 [{name}] 已保存 ({result} 项)", "green")
            self._refresh_account_list()

    def _on_account_overwritten(self, result, name):
        if isinstance(result, Exception):
            messagebox.showerror("更新失败", str(result))
        else:
            self.app.set_status(f"账号 [{name}] 已更新", "green")
            self._refresh_account_list()

    def _on_switch_account(self):
        """切换到选中的账号"""
        name = self._get_selected_account()
        if not name:
            messagebox.showinfo("提示", "请先选择要切换的账号")
            return
        if not self._confirm("确认切换", f"将切换到账号 [{name}]，当前登录状态将被覆盖。\n\n是否继续？"):
            self.app.set_status("已取消")
            return

        # 检查游戏是否在运行
        if self.core.is_platform_running():
            if not messagebox.askyesno("游戏正在运行", "原神正在运行，需要先关闭。是否继续？"):
                self.app.set_status("已取消")
                return
            self.core.kill_platform()

        self.app.run_async(
            task=lambda: self.core.restore_credential(name),
            on_done=lambda r: self._on_account_switched(r, name),
            status=f"正在切换到 [{name}]..."
        )

    def _on_account_switched(self, result, name):
        if isinstance(result, Exception):
            messagebox.showerror("切换失败", str(result))
        else:
            self.app.set_status(f"已切换到 [{name}]，启动原神即可自动登录", "green")
            self._refresh_account_list()

    def _on_update_account(self):
        """覆盖更新已选中的账号"""
        name = self._get_selected_account()
        if not name:
            messagebox.showinfo("提示", "请先选择要更新的账号")
            return
        if not self._confirm("确认更新", f"将用当前登录状态覆盖 [{name}] 的凭证。\n\n是否继续？"):
            self.app.set_status("已取消")
            return
        self.app.run_async(
            task=lambda: self.core.overwrite_credential(name),
            on_done=lambda r: self._on_account_overwritten(r, name),
            status=f"正在更新 [{name}]..."
        )

    def _on_rename_account(self):
        """重命名账号"""
        old_name = self._get_selected_account()
        if not old_name:
            messagebox.showinfo("提示", "请先选择要重命名的账号")
            return
        new_name = self._prompt_account_name(f"将 [{old_name}] 重命名为:")
        if not new_name:
            return
        try:
            self.core.rename_account(old_name, new_name)
            self.app.set_status(f"[{old_name}] → [{new_name}]", "green")
            self._refresh_account_list()
        except GameDataKeeperError as e:
            messagebox.showerror("重命名失败", str(e))

    def _on_delete_account(self):
        """删除账号"""
        name = self._get_selected_account()
        if not name:
            messagebox.showinfo("提示", "请先选择要删除的账号")
            return
        if not self._confirm("确认删除", f"删除账号 [{name}] 的凭证？\n此操作不可撤销。"):
            self.app.set_status("已取消")
            return
        try:
            self.core.delete_account(name)
            self.app.set_status(f"账号 [{name}] 已删除", "green")
            self._refresh_account_list()
        except GameDataKeeperError as e:
            messagebox.showerror("删除失败", str(e))

    # ── 覆盖基类凭证操作（多账号版本）────

    def _on_backup_credential(self):
        """备份凭证 → 保存当前登录为账号"""
        self._on_save_account()

    def _on_restore_credential(self):
        """恢复凭证 → 切换到已保存的账号"""
        self._on_switch_account()

    # ── 覆盖凭证状态检查（原神不需要平台安装）──

    def _check_storage(self):
        # 原神不需要检查平台路径，只检查存储
        return True

    # ── 辅助方法 ──

    def _prompt_account_name(self, prompt: str) -> str | None:
        """弹窗输入账号名"""
        import tkinter.simpledialog as sd
        return sd.askstring("账号名称", prompt)

    def get_extra_actions(self) -> list:
        return []
