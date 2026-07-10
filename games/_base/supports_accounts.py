"""多账号管理接口 — 只有支持多账号切换的 Core 才实现此接口"""

from abc import ABC, abstractmethod


class SupportsMultiAccount(ABC):
    """
    多账号凭证管理接口。

    实现此接口的 Core 保证提供以下方法，
    AccountCard 依赖此接口而非具体 Core 类型。
    """

    @abstractmethod
    def list_accounts(self) -> list[dict]:
        """列出所有已保存的账号 [{name, created_at, updated_at}, ...]"""
        ...

    @abstractmethod
    def backup_credential(self, account_name: str):
        """保存当前登录凭证为指定账号名"""
        ...

    @abstractmethod
    def restore_credential(self, account_name: str):
        """从指定账号恢复凭证到注册表"""
        ...

    @abstractmethod
    def overwrite_credential(self, account_name: str):
        """覆盖更新已有账号的凭证"""
        ...

    @abstractmethod
    def delete_account(self, account_name: str):
        """删除指定账号"""
        ...

    @abstractmethod
    def rename_account(self, old_name: str, new_name: str):
        """重命名账号"""
        ...
