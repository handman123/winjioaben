import tkinter as tk

class PlaceholderTab(tk.Frame):
    def __init__(self, parent, app, title, features):
        super().__init__(parent, bg="#f5f5f5")
        msg = f"{title} - 功能开发中\n\n后续将支持:\n  {features}"
        tk.Label(self, text=msg, font=("Microsoft YaHei", 11),
                 fg="gray", bg="#f5f5f5", justify="left").place(x=60, y=80)
