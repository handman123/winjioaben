"""崩坏:星穹铁道模块 — 自动注册到 Tab 栏"""
from app.tab_registry import TabRegistry
from games.hsr.ui.tab import HsrTab
from games.hsr.core.manager import HsrCore

TabRegistry.register("崩坏:星穹铁道", HsrTab, HsrCore)
