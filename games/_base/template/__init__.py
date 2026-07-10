"""新游戏接入模板 — 复制此目录并修改以下内容：
1. 重命名 NewGameCore / NewGameTab 类名
2. 修改 GAME_NAME / GAME_ID 等属性
3. 实现 Core 层钩子方法
4. 在 games/__init__.py 中添加 import
"""

from app.tab_registry import TabRegistry
from .ui.tab import NewGameTab
from .core.manager import NewGameCore

TabRegistry.register("新游戏", NewGameTab, NewGameCore)
