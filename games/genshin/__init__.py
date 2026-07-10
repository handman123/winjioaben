"""原神模块 — 自动注册到 Tab 栏"""
from app.tab_registry import TabRegistry
from games.genshin.ui.tab import GenshinTab
from games.genshin.core.manager import GenshinCore

TabRegistry.register("原神", GenshinTab, GenshinCore)
