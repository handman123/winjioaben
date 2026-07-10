"""Steam 模块 — 自动注册到 Tab 栏"""
from app.tab_registry import TabRegistry
from games.steam.ui.tab import SteamTab
from games.steam.core import SteamCore

TabRegistry.register("Steam", SteamTab, SteamCore)
