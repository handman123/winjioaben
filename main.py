import tkinter as tk
import os
import sys

# Ensure we can import from the project root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.main_window import App

if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
