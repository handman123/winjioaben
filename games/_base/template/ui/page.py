"""新游戏 Page 模板 — 继承 Page，通过 add_card() 组合卡片

每个 Content 自己的 core/ 调 shared/config_manager 读写 config/<game>.json
每个 Content 自己的 ui/ 定义卡片（继承 games._base.card.Card）
"""

from games._base.page import Page
from games._base.template.core.manager import NewGameCore


class NewGamePage(Page):
    GAME_NAME = "新游戏"
    GAME_ID = "new_game"

    def _make_core(self):
        return NewGameCore(self.app)

    def _build(self):
        # TODO: 替换为实际的卡片
        # self.add_card(StatusCard(self, self.app))
        # self.add_card(ActionBar(self))
        # self.add_card(HistoryCard(self, self.app, backup_dir=...), fill="both", expand=True)
        pass
