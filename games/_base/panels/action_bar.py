"""操作按钮栏 — 可配置的操作按钮组合"""

import tkinter as tk


class ActionBar(tk.LabelFrame):
    """快捷操作按钮栏，每行最多 2 个按钮"""

    def __init__(self, parent, actions: list[dict] = None):
        """
        actions: [{"label": "备份存档", "callback": fn, "row": 0}, ...]
        每行最多 2 个按钮，row 指定行号
        """
        super().__init__(parent, text="快捷操作", bg="#f5f5f5",
                         font=("Microsoft YaHei", 9), padx=8, pady=4)
        self._buttons = {}
        self._rows = {}

        for act in (actions or []):
            self.add_action(act["label"], act["callback"], act.get("row", 0))

    def add_action(self, label: str, callback, row: int = 0):
        """动态添加操作按钮"""
        if row not in self._rows:
            self._rows[row] = tk.Frame(self, bg="#f5f5f5")
            self._rows[row].pack(fill="x", pady=2)

        btn = tk.Button(self._rows[row], text=label,
                        font=("Microsoft YaHei", 9),
                        relief="flat", bg="white", padx=14, pady=4,
                        command=callback)
        btn.pack(side="left", padx=2)
        self._buttons[label] = btn
        return btn

    def set_enabled(self, label: str, enabled: bool):
        if label in self._buttons:
            self._buttons[label].configure(state="normal" if enabled else "disabled")
