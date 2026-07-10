"""崩坏:星穹铁道 Core — 占位实现"""

from games._base.base_core import BaseGameCore


class HsrCore(BaseGameCore):
    GAME_ID = "honkai_star_rail"
    GAME_NAME = "崩坏:星穹铁道"

    def find_platform_path(self):
        # TODO: 实现崩铁安装路径检测
        return None

    def detect_running(self):
        # TODO: 实现崩铁进程检测
        return None

    def backup_credential(self):
        # TODO: 实现崩铁账号凭证备份
        raise NotImplementedError("崩铁凭证备份尚未实现")

    def restore_credential(self):
        # TODO: 实现崩铁账号凭证恢复
        raise NotImplementedError("崩铁凭证恢复尚未实现")
