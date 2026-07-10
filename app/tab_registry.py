"""Tab 注册中心 — 新增游戏只需在此注册一行"""


class TabEntry:
    def __init__(self, name: str, tab_class, core_class=None, icon: str = ""):
        self.name = name
        self.tab_class = tab_class
        self.core_class = core_class
        self.icon = icon


class TabRegistry:
    """Tab 注册中心 — 新增游戏只需注册一行"""
    _tabs: list[TabEntry] = []

    @classmethod
    def register(cls, name: str, tab_class, core_class=None, icon: str = ""):
        cls._tabs.append(TabEntry(name, tab_class, core_class, icon))

    @classmethod
    def get_all(cls) -> list[TabEntry]:
        return list(cls._tabs)

    @classmethod
    def clear(cls):
        cls._tabs.clear()
