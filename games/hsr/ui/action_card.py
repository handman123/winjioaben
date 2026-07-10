"""崩铁操作按钮卡片"""

import tkinter as tk

from games._base.card import Card


class ActionCard(Card):
    def __init__(self, parent, *, on_backup_saves, on_restore_saves):
        super().__init__(parent, "快捷操作")

        def btn(text, cmd):
            return tk.Button(self, text=text, font=("Microsoft YaHei", 9),
                             relief="flat", bg="white", padx=14, pady=4, command=cmd)

        r1 = tk.Frame(self, bg="#f5f5f5"); r1.pack(fill="x", pady=2)
        btn("备份存档", on_backup_saves).pack(side="left", padx=2)
        btn("恢复存档", on_restore_saves).pack(side="left", padx=2)
