"""Card 基类 — 所有功能卡片的根，纯框架"""

import tkinter as tk


class Card(tk.LabelFrame):
    """功能卡片基类"""

    def __init__(self, parent, title: str, **kwargs):
        super().__init__(parent, text=title, bg="#f5f5f5",
                         font=("Microsoft YaHei", 9), padx=8, pady=4, **kwargs)

    def refresh(self):
        """子类覆盖"""
        pass
