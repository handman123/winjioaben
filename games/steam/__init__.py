from app.tab_registry import TabRegistry
from games.steam.ui.page import SteamPage
from games.steam.core import SteamCore

TabRegistry.register("Steam", SteamPage, SteamCore)
