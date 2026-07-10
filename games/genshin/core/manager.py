"""原神 Core — 凭证管理 + 多账号切换"""

import os
import subprocess

from games._base.base_core import BaseGameCore
from games.genshin.core import credential
from utils.exceptions import AccountNotFoundError, AccountExistsError
from games._base.supports_accounts import SupportsMultiAccount


class GenshinCore(BaseGameCore, SupportsMultiAccount):
    GAME_ID = "genshin_impact"
    GAME_NAME = "原神"

    # ── 平台检测 ──

    def find_platform_path(self) -> str | None:
        """通过注册表查找原神安装路径"""
        try:
            import winreg
            for k in [r"SOFTWARE\miHoYo\原神", r"SOFTWARE\miHoYo\Genshin Impact"]:
                try:
                    key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, k)
                    p, _ = winreg.QueryValueEx(key, "InstallPath")
                    winreg.CloseKey(key)
                    if os.path.exists(p):
                        return p
                except OSError:
                    continue
        except ImportError:
            pass
        # 常见安装路径兜底
        for dp in [r"C:\Program Files\Genshin Impact", r"C:\Program Files\原神",
                   r"D:\Program Files\Genshin Impact", r"D:\Program Files\原神"]:
            if os.path.exists(dp):
                return dp
        return None

    def detect_running(self) -> dict | None:
        """检测原神是否正在运行"""
        exe_names = ["YuanShen.exe", "GenshinImpact.exe"]
        try:
            r = subprocess.run(["tasklist", "/FI", "IMAGENAME eq YuanShen.exe"],
                               capture_output=True, text=True)
            if "YuanShen.exe" in r.stdout.lower():
                return {"folder": "原神", "root": "", "exe": "YuanShen.exe"}
            r2 = subprocess.run(["tasklist", "/FI", "IMAGENAME eq GenshinImpact.exe"],
                                capture_output=True, text=True)
            if "GenshinImpact.exe" in r2.stdout.lower():
                return {"folder": "Genshin Impact", "root": "", "exe": "GenshinImpact.exe"}
        except Exception:
            pass
        return None

    def is_platform_running(self) -> bool:
        return self.detect_running() is not None

    def kill_platform(self):
        for exe in ["YuanShen.exe", "GenshinImpact.exe"]:
            subprocess.run(["taskkill", "/F", "/IM", exe], capture_output=True)

    # ── 凭证管理（多账号） ──

    def list_accounts(self) -> list[dict]:
        """列出所有已保存的账号"""
        return credential.list_accounts(self.app.storage_root)

    def backup_credential(self, account_name: str = None) -> int:
        """保存当前登录凭证为指定账号名"""
        if not account_name:
            raise ValueError("必须提供账号名")
        return credential.save_account(self.app.storage_root, account_name)

    def overwrite_credential(self, account_name: str) -> int:
        """覆盖更新已有账号凭证"""
        return credential.overwrite_account(self.app.storage_root, account_name)

    def restore_credential(self, account_name: str = None) -> int:
        """从指定账号恢复凭证"""
        if not account_name:
            raise ValueError("必须提供账号名")
        return credential.restore_account(self.app.storage_root, account_name)

    def delete_account(self, account_name: str):
        """删除指定账号"""
        credential.delete_account(self.app.storage_root, account_name)

    def rename_account(self, old_name: str, new_name: str):
        """重命名账号"""
        credential.rename_account(self.app.storage_root, old_name, new_name)
