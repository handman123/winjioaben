"""原神凭证管理 — Windows 注册表导出/导入 + 单 JSON 文件多账号存储"""

import os
import json
import subprocess
import tempfile
from datetime import datetime

from shared.exceptions import AccountNotFoundError, AccountExistsError, GenshinError

# 全量覆盖国服 + 国际服 + SDK
REGISTRY_KEYS = [
    r"HKEY_CURRENT_USER\Software\miHoYo\原神",
    r"HKEY_CURRENT_USER\Software\miHoYo\Genshin Impact",
    r"HKEY_CURRENT_USER\Software\miHoYo\miHoYo SDK",
    r"HKEY_CURRENT_USER\Software\Cognosphere",
]

ACCOUNTS_FILE = "Genshin/accounts.json"


# ── JSON 文件读写 ──────────────────────────────────────

def _accounts_path(storage_root: str) -> str:
    return os.path.join(storage_root, ACCOUNTS_FILE)


def _load(storage_root: str) -> dict:
    """读取 accounts.json，不存在则返回默认空结构"""
    p = _accounts_path(storage_root)
    if not os.path.exists(p):
        return {"version": "1.0", "accounts": {}}
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(storage_root: str, data: dict):
    """写入 accounts.json"""
    os.makedirs(os.path.dirname(_accounts_path(storage_root)), exist_ok=True)
    with open(_accounts_path(storage_root), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ── 账号管理 API ───────────────────────────────────────

def list_accounts(storage_root: str) -> list[dict]:
    """返回所有已保存账号的摘要列表"""
    data = _load(storage_root)
    result = []
    for name, info in data.get("accounts", {}).items():
        result.append({
            "name": name,
            "created_at": info.get("created_at", ""),
            "updated_at": info.get("updated_at", ""),
            "reg_count": len(info.get("reg_data", {})),
        })
    return sorted(result, key=lambda a: a["name"].lower())


def save_account(storage_root: str, account_name: str) -> int:
    """保存当前登录凭证为指定账号名。成功返回成功导出的注册表键数量。"""
    data = _load(storage_root)

    # 检查重名
    if account_name in data.get("accounts", {}):
        raise AccountExistsError(account_name)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    reg_data = {}
    exported = 0

    for key in REGISTRY_KEYS:
        content = _export_registry(key)
        if content is not None:
            # 用 key 的最后一段作为简洁标识
            short_name = key.rstrip("\\").rsplit("\\", 1)[-1]
            reg_data[short_name] = content
            exported += 1

    if exported == 0:
        raise GenshinError("未检测到原神注册表数据，请确认原神已安装并登录过。", recoverable=True)

    data.setdefault("accounts", {})[account_name] = {
        "created_at": now,
        "updated_at": now,
        "reg_data": reg_data,
    }
    _save(storage_root, data)
    return exported


def overwrite_account(storage_root: str, account_name: str) -> int:
    """覆盖更新已有账号的凭证（不提示重名）。成功返回导出的注册表键数量。"""
    data = _load(storage_root)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    reg_data = {}
    exported = 0

    for key in REGISTRY_KEYS:
        content = _export_registry(key)
        if content is not None:
            short_name = key.rstrip("\\").rsplit("\\", 1)[-1]
            reg_data[short_name] = content
            exported += 1

    if exported == 0:
        raise GenshinError("未检测到原神注册表数据，请确认原神已安装并登录过。", recoverable=True)

    existing = data.get("accounts", {}).get(account_name, {})
    existing["reg_data"] = reg_data
    existing["updated_at"] = now
    if "created_at" not in existing:
        existing["created_at"] = now
    data.setdefault("accounts", {})[account_name] = existing
    _save(storage_root, data)
    return exported


def restore_account(storage_root: str, account_name: str) -> int:
    """从已保存的账号恢复凭证到注册表。成功返回导入的注册表键数量。"""
    data = _load(storage_root)
    account = data.get("accounts", {}).get(account_name)
    if not account:
        raise AccountNotFoundError(account_name)

    reg_data = account.get("reg_data", {})
    if not reg_data:
        raise GenshinError(f"账号 [{account_name}] 的凭证数据为空", recoverable=False)

    imported = 0
    for short_name, content in reg_data.items():
        if _import_registry(content):
            imported += 1

    if imported == 0:
        raise GenshinError("注册表导入失败", recoverable=False)

    return imported


def delete_account(storage_root: str, account_name: str):
    """删除指定账号"""
    data = _load(storage_root)
    if account_name not in data.get("accounts", {}):
        raise AccountNotFoundError(account_name)
    del data["accounts"][account_name]
    _save(storage_root, data)


def rename_account(storage_root: str, old_name: str, new_name: str):
    """重命名账号"""
    data = _load(storage_root)
    if old_name not in data.get("accounts", {}):
        raise AccountNotFoundError(old_name)
    if new_name in data.get("accounts", {}):
        raise AccountExistsError(new_name)
    data["accounts"][new_name] = data["accounts"].pop(old_name)
    _save(storage_root, data)


# ── 底层注册表操作 ─────────────────────────────────────

def _export_registry(key: str) -> str | None:
    """导出指定注册表键为 .reg 文本内容。键不存在则返回 None。"""
    try:
        fd, tmp = tempfile.mkstemp(suffix=".reg")
        os.close(fd)
        # /y 覆盖已有文件
        result = subprocess.run(
            ["reg", "export", key, tmp, "/y"],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode != 0:
            # 键不存在或者其他错误
            if os.path.exists(tmp):
                os.remove(tmp)
            return None

        with open(tmp, "r", encoding="utf-16") as f:
            content = f.read()

        os.remove(tmp)

        # 如果内容只有 BOM 或空，说明键存在但无数据
        if not content.strip():
            return None

        return content
    except Exception:
        return None


def _import_registry(reg_content: str) -> bool:
    """将 .reg 文本内容导入注册表。成功返回 True。"""
    try:
        fd, tmp = tempfile.mkstemp(suffix=".reg")
        with os.fdopen(fd, "w", encoding="utf-16") as f:
            f.write(reg_content)

        result = subprocess.run(
            ["reg", "import", tmp],
            capture_output=True, text=True, timeout=15,
        )
        os.remove(tmp)
        return result.returncode == 0
    except Exception:
        return False
