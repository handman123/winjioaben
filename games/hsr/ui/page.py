"""HsrPage — 占位，功能待开发"""

import tkinter as tk

from games._base.page import Page
from games.hsr.core.manager import HsrCore


class HsrPage(Page):
    GAME_NAME = "崩坏:星穹铁道"
    GAME_ID = "honkai_star_rail"

    def _make_core(self):
        return HsrCore(self.app)

    def _build(self):
        tk.Label(self, text="崩坏:星穹铁道 — 功能开发中", fg="gray",
                 bg="#f5f5f5", font=("Microsoft YaHei", 12)).place(x=60, y=80)
