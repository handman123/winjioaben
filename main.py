import tkinter as tk
import os, sys

# Make sure we can import from the project root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.app import App

if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
