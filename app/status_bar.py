import tkinter as tk
from tkinter import ttk


class StatusBar(tk.Frame):
    """通用状态栏组件"""

    def __init__(self, parent):
        super().__init__(parent, bg="#e0e0e0", height=28)
        self.pack_propagate(False)

        self.status_var = tk.StringVar(value="就绪")
        tk.Label(self, textvariable=self.status_var, bg="#e0e0e0",
                 fg="gray", anchor="w", padx=8).pack(side="left")

        self.progress = ttk.Progressbar(self, mode="indeterminate", length=120)
        self.progress.pack(side="right", padx=8)
        self.progress.pack_forget()  # 默认隐藏

    def set_status(self, text: str):
        self.status_var.set(text)

    def show_progress(self):
        self.progress.pack(side="right", padx=8)
        self.progress.start(10)

    def hide_progress(self):
        self.progress.stop()
        self.progress.pack_forget()
