"""新游戏 Page 模板 — 复制此目录：
1. 重命名 NewGameCore / NewGamePage 类名
2. 修改 GAME_NAME / GAME_ID 属性
3. 实现 Core 层钩子方法
4. 在 games/__init__.py 添加 import
"""

from app.tab_registry import TabRegistry
from .ui.page import NewGamePage
from .core.manager import NewGameCore

TabRegistry.register("新游戏", NewGamePage, NewGameCore)
