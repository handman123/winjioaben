"""Steam Tab — 继承 BaseGameTab，声明 Steam 特有的配置"""

from games._base.base_tab import BaseGameTab
from games.steam.core import SteamCore


class SteamTab(BaseGameTab):
    GAME_NAME = "Steam"
    GAME_ID = "steam"
    SUPPORT_CREDENTIAL = True
    SUPPORT_DISCOVERY = True
    SUPPORT_PLATFORM = True

    def _create_core(self):
        return SteamCore(self.app)
