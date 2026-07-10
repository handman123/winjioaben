"""
BaseGameCore — 通用游戏业务逻辑基类。

子类只需覆盖 detect_running() 等平台特定方法，
通用的备份/恢复/列表逻辑由基类提供。
"""

import os

from utils import backup as backup_engine
from utils import disk
from utils.exceptions import GameDataKeeperError


class BaseGameCore:
    """通用游戏业务逻辑"""

    # ── 子类可选覆盖 ──
    GAME_ID: str = ""           # 唯一标识
    GAME_NAME: str = ""         # 显示名称
    SAVE_PATTERNS: list = []    # 存档目录匹配模式

    def __init__(self, app):
        self.app = app

    # ── 通用方法 ──

    def backup_saves(self, game: dict, on_progress=None) -> dict:
        """备份游戏所有存档路径，返回每个路径的备份结果"""
        dd = disk.get_root()
        root = os.path.join(dd, "Saves")
        results = {}
        for sp in game.get("save_paths", []):
            dest = os.path.join(root, game["backup_dir"], sp["name"])
            info = backup_engine.backup(sp["path"], dest, on_progress=on_progress)
            results[sp["name"]] = info
        return results

    def restore_saves(self, game: dict, specific_zip=None, on_progress=None) -> dict:
        """恢复游戏所有存档路径"""
        dd = disk.get_root()
        root = os.path.join(dd, "Saves")
        results = {}
        for sp in game.get("save_paths", []):
            src = os.path.join(root, game["backup_dir"], sp["name"])
            info = backup_engine.restore(sp["path"], src, specific=specific_zip,
                                         on_progress=on_progress)
            results[sp["name"]] = info
        return results

    def list_backups(self, game: dict) -> dict[str, list]:
        """列出游戏所有存档路径的备份"""
        dd = disk.get_root()
        if not dd:
            return {}
        root = os.path.join(dd, "Saves", game["backup_dir"])
        if not os.path.exists(root):
            return {}
        result = {}
        for dn in sorted(os.listdir(root)):
            bd = os.path.join(root, dn)
            if os.path.isdir(bd):
                result[dn] = backup_engine.list_all(bd)
        return result

    def validate_save_paths(self, game: dict) -> list[str]:
        """验证存档路径，返回问题描述列表"""
        issues = []
        for sp in game.get("save_paths", []):
            p = sp["path"]
            if not os.path.exists(p):
                issues.append(f"目录不存在: {p}")
            elif not os.listdir(p):
                issues.append(f"目录为空: {p}")
        return issues

    # ── 子类必须覆盖的钩子 ──

    def detect_running(self) -> dict | None:
        """检测正在运行的游戏进程，返回 {folder, root, exe} 或 None"""
        return None

    def backup_credential(self) -> list:
        """备份平台凭证，返回已备份项列表"""
        raise NotImplementedError("子类需实现 backup_credential")

    def restore_credential(self) -> list:
        """恢复平台凭证，返回已恢复项列表"""
        raise NotImplementedError("子类需实现 restore_credential")

    def launch_platform(self):
        """启动平台客户端（如 Steam）"""
        pass

    def is_platform_running(self) -> bool:
        """检查平台是否正在运行"""
        return False

    def kill_platform(self):
        """强制关闭平台"""
        pass

    def find_platform_path(self) -> str | None:
        """查找平台安装路径"""
        return None
