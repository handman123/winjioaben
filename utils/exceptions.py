"""统一异常层次结构 — 所有自定义异常的根和业务子类"""


class GameDataKeeperError(Exception):
    """基础异常 — 所有自定义异常的根"""

    def __init__(self, message: str, *, detail: str = "", recoverable: bool = True):
        super().__init__(message)
        self.detail = detail            # 技术细节（写入日志）
        self.recoverable = recoverable  # False 时弹窗阻断，True 时静默 fallback


# ── 备份/恢复异常 ──

class BackupError(GameDataKeeperError):
    """备份/恢复操作异常"""
    pass


class SourceNotFoundError(BackupError):
    """源目录不存在"""
    def __init__(self, path: str):
        super().__init__(f"源目录不存在: {path}", detail=path, recoverable=True)


class SourceEmptyError(BackupError):
    """源目录为空"""
    def __init__(self, path: str):
        super().__init__(f"源目录为空: {path}", detail=path, recoverable=True)


# ── Steam 异常 ──

class SteamError(GameDataKeeperError):
    """Steam 操作异常"""
    pass


class SteamNotInstalledError(SteamError):
    """Steam 未安装"""
    def __init__(self):
        super().__init__("未检测到 Steam 安装", recoverable=False)


class SteamRunningError(SteamError):
    """Steam 正在运行（需要关闭才能继续）"""
    def __init__(self):
        super().__init__("Steam 正在运行，请先关闭", recoverable=True)


class RegistryAccessError(SteamError):
    """注册表访问失败"""
    def __init__(self, key: str):
        super().__init__(f"注册表访问失败: {key}", detail=key, recoverable=True)


# ── 进程发现异常 ──

class DiscoveryError(GameDataKeeperError):
    """进程发现异常"""
    pass


# ── 配置异常 ──

class ConfigError(GameDataKeeperError):
    """配置读写异常"""
    pass


# ── 原神异常 ──

class GenshinError(GameDataKeeperError):
    """原神操作异常"""
    pass


class AccountNotFoundError(GenshinError):
    """账号不存在"""
    def __init__(self, name: str):
        super().__init__(f"账号不存在: {name}", detail=name, recoverable=True)


class AccountExistsError(GenshinError):
    """账号已存在（保存时重名）"""
    def __init__(self, name: str):
        super().__init__(f"账号 [{name}] 已存在，是否覆盖？", detail=name, recoverable=True)


# ── 存储目录异常 ──

class StorageError(GameDataKeeperError):
    """存储目录异常"""
    pass
