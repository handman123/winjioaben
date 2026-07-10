"""新游戏 Page 模板 — 继承 Page，通过 add_card() 组合卡片"""

import os
import tkinter.messagebox as messagebox

from games._base.page import Page
from games._base.template.core.manager import NewGameCore
from shared import config_manager
from shared.exceptions import GameDataKeeperError


# TODO: 在 games/<your_game>/ui/ 下创建 status_card.py, action_card.py, history_card.py
# 每个卡片继承 games._base.card.Card

class NewGamePage(Page):
    GAME_NAME = "新游戏"
    GAME_ID = "new_game"

    def _make_core(self):
        return NewGameCore(self.app)

    def _build(self):
        # TODO: 替换为实际的卡片类
        # self.add_card(StatusCard(self, self.app))
        # self.add_card(ActionCard(self, on_backup_saves=..., on_restore_saves=...))
        # self.add_card(HistoryCard(self, self.app, on_restore=...), fill="both", expand=True)
        pass

    def refresh(self):
        super().refresh()

    def _current_game(self):
        games = config_manager.get_games()
        return games[0] if games else None
