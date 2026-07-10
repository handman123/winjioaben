from app.tab_registry import TabRegistry
from games.hsr.ui.page import HsrPage
from games.hsr.core.manager import HsrCore

TabRegistry.register("崩坏:星穹铁道", HsrPage, HsrCore)
