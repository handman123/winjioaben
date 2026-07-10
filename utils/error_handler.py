"""统一错误处理：日志记录 + 用户提示 + 安全降级"""

import os
import sys
import traceback
import functools
from datetime import datetime
from typing import Callable, Any


def _get_log_dir() -> str:
    """获取日志目录（GameDataKeeper/ 根目录），写入失败则返回空字符串"""
    try:
        import utils.disk as disk
        return disk.get_root()
    except Exception:
        return ""


def log_error(context: str, error: Exception):
    """写入错误日志到 GameDataKeeper/error.log"""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    msg = f"[{ts}] [{context}] {type(error).__name__}: {error}"

    from utils.exceptions import GameDataKeeperError
    if isinstance(error, GameDataKeeperError) and error.detail:
        msg += f"\n  详情: {error.detail}"

    log_dir = _get_log_dir()
    if log_dir:
        try:
            os.makedirs(log_dir, exist_ok=True)
            with open(os.path.join(log_dir, "error.log"), "a", encoding="utf-8") as f:
                f.write(msg + "\n")
            return
        except OSError:
            pass
    # 最终降级：stderr
    print(msg, file=sys.stderr)


def handle_errors(context: str = "操作", *, reraise: bool = False):
    """
    装饰器：自动捕获异常并统一处理。

    - GameDataKeeperError: 写日志；不可恢复时弹窗
    - 普通 Exception: 写日志 + 弹窗
    - 返回值: 异常时返回 None（safe fallback）
    """
    import tkinter.messagebox as messagebox
    from utils.exceptions import GameDataKeeperError

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except GameDataKeeperError as e:
                log_error(context, e)
                if not e.recoverable:
                    messagebox.showerror(f"{context}失败", str(e))
                if reraise:
                    raise
                return None
            except Exception as e:
                log_error(context, e)
                messagebox.showerror(f"{context}异常", f"未预期的错误:\n{str(e)}")
                if reraise:
                    raise GameDataKeeperError(str(e), detail=traceback.format_exc())
                return None
        return wrapper
    return decorator
