"""原神 Tab — 继承 BaseGameTab，声明原神特有配置"""

from games._base.base_tab import BaseGameTab
from games.genshin.core.manager import GenshinCore


class GenshinTab(BaseGameTab):
    GAME_NAME = "原神"
    GAME_ID = "genshin_impact"
    SAVE_PATTERNS = ["SaveData", "ScreenShot"]
    SUPPORT_CREDENTIAL = True
    SUPPORT_DISCOVERY = False
    SUPPORT_PLATFORM = False

    def _create_core(self):
        return GenshinCore(self.app)

    def get_extra_actions(self):
        return [("备份截图", self._placeholder_screenshots)]

    def _placeholder_screenshots(self):
        import tkinter.messagebox as messagebox
        messagebox.showinfo("提示", "截图备份功能开发中...")
