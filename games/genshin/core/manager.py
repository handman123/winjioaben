"""原神 Core — 占位实现"""

from games._base.base_core import BaseGameCore


class GenshinCore(BaseGameCore):
    GAME_ID = "genshin_impact"
    GAME_NAME = "原神"

    # 原神非 Steam 游戏，通过注册表查找路径
    def find_platform_path(self):
        # TODO: 实现原神安装路径检测
        return None

    def detect_running(self):
        # TODO: 实现原神进程检测
        return None

    def backup_credential(self):
        # TODO: 实现原神账号凭证备份
        raise NotImplementedError("原神凭证备份尚未实现")

    def restore_credential(self):
        # TODO: 实现原神账号凭证恢复
        raise NotImplementedError("原神凭证恢复尚未实现")
