"""原神配置 — 读写 config/genshin.json"""

from shared import config_manager

CONFIG = "config/genshin.json"


def load() -> dict:
    data = config_manager.load_json(CONFIG)
    return data or {}


def save(data: dict):
    config_manager.save_json(CONFIG, data)


def get_game_path() -> str:
    return load().get("game_path", "")


def set_game_path(path: str):
    data = load()
    data["game_path"] = path
    save(data)
