"""新游戏 Tab — 模板实现

TODO: 修改以下内容：
  1. GAME_NAME / GAME_ID → 你的游戏名称和唯一 ID
  2. SUPPORT_* 标志位       → 根据游戏特性调整
  3. get_extra_actions()  → 添加游戏特有的操作按钮
"""

from games._base.base_tab import BaseGameTab
from games._base.template.core.manager import NewGameCore


class NewGameTab(BaseGameTab):
    # ── 必须修改 ──
    GAME_NAME = "新游戏"
    GAME_ID = "new_game"

    # ── 按需修改 ──
    SAVE_PATTERNS = []             # 存档目录匹配模式
    SUPPORT_CREDENTIAL = False     # 是否支持凭证备份
    SUPPORT_DISCOVERY = True       # 是否支持进程发现
    SUPPORT_PLATFORM = False       # 是否有平台客户端

    def _create_core(self):
        return NewGameCore(self.app)

    # def get_extra_actions(self):
    #     """添加游戏特有的操作按钮"""
    #     return [("额外操作", self._on_extra)]
    #
    # def _on_extra(self):
    #     pass
