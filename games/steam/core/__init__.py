"""Steam 模块 — 业务逻辑适配层"""

from games._base.base_core import BaseGameCore
from games.steam.core import credential, discovery


class SteamCore(BaseGameCore):
    GAME_ID = "steam"
    GAME_NAME = "Steam"

    def find_platform_path(self):
        return credential.find_path()

    def is_platform_running(self):
        return credential.is_running()

    def kill_platform(self):
        credential.kill()

    def launch_platform(self):
        sp = self.find_platform_path()
        if sp:
            credential.launch(sp)

    def backup_credential(self):
        sp = self.find_platform_path()
        dd = self.app.storage_root
        return credential.backup(sp, dd)

    def restore_credential(self):
        sp = self.find_platform_path()
        dd = self.app.storage_root
        return credential.restore(sp, dd)

    def detect_running(self):
        return discovery.detect_running()

    def find_save_dirs(self, game_root):
        return discovery.find_save_dirs(game_root)

    def diag_processes(self):
        return discovery.diag_processes()
