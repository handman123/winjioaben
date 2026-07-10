"""通用 JSON 配置工具 — 读写项目根目录下的 config/*.json"""

import os
import json


def _project_root():
    import sys
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    # shared/config_manager.py → project root (2 levels up)
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load_json(rel_path: str) -> dict | None:
    """从项目根目录读取 JSON 文件，不存在返回 None"""
    p = os.path.join(_project_root(), rel_path)
    if not os.path.exists(p):
        return None
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(rel_path: str, data: dict):
    """写入 JSON 文件到项目根目录"""
    p = os.path.join(_project_root(), rel_path)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
