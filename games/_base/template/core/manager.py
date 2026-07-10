"""新游戏 Core — 模板实现

TODO: 实现以下方法：
  - find_platform_path()  → 检测平台安装路径
  - detect_running()      → 检测游戏是否在运行
  - backup_credential()   → 备份账号凭证
  - restore_credential()  → 恢复账号凭证
"""

from games._base.base_core import BaseGameCore


class NewGameCore(BaseGameCore):
    GAME_ID = "new_game"
    GAME_NAME = "新游戏"

    # 如果你的游戏有存档目录命名规则，在这里定义
    # SAVE_PATTERNS = ["SaveData", "ScreenShot"]

    def find_platform_path(self):
        # TODO: 实现平台路径检测
        return None

    def detect_running(self):
        # TODO: 实现进程检测
        return None

    def backup_credential(self):
        # TODO: 实现凭证备份
        raise NotImplementedError("凭证备份尚未实现")

    def restore_credential(self):
        # TODO: 实现凭证恢复
        raise NotImplementedError("凭证恢复尚未实现")
