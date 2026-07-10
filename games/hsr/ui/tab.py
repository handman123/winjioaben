"""崩坏:星穹铁道 Tab — 继承 BaseGameTab，声明崩铁特有配置"""

from games._base.base_tab import BaseGameTab
from games.hsr.core.manager import HsrCore


class HsrTab(BaseGameTab):
    GAME_NAME = "崩坏:星穹铁道"
    GAME_ID = "honkai_star_rail"
    SAVE_PATTERNS = ["SaveData", "ScreenShot"]
    SUPPORT_CREDENTIAL = True
    SUPPORT_DISCOVERY = False
    SUPPORT_PLATFORM = False

    def _create_core(self):
        return HsrCore(self.app)

    def get_extra_actions(self):
        return [("备份截图", self._placeholder_screenshots)]

    def _placeholder_screenshots(self):
        import tkinter.messagebox as messagebox
        messagebox.showinfo("提示", "截图备份功能开发中...")
