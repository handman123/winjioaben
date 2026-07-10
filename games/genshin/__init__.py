from app.tab_registry import TabRegistry
from games.genshin.ui.page import GenshinPage
from games.genshin.core.manager import GenshinCore

TabRegistry.register("原神", GenshinPage, GenshinCore)
