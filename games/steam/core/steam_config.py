"""Steam 游戏配置 — 读写 config/steam.json"""

from utils import config_manager

CONFIG = "config/steam.json"


def _load() -> dict:
    data = config_manager.load_json(CONFIG)
    if not data:
        return {"version": "1.3", "games": []}
    return data


def _save(cfg: dict):
    config_manager.save_json(CONFIG, cfg)


def get_games() -> list[dict]:
    return _load().get("games", [])


def add_game(name: str, folder: str, save_paths: list[dict]):
    cfg = _load()
    safe = folder.replace("\\", "_").replace("/", "_").replace(" ", "_")
    cfg["games"] = [g for g in cfg.get("games", []) if g["backup_dir"] != safe]
    cfg["games"].append({
        "id": safe.lower(),
        "name": name,
        "steam_appid": "",
        "max_backups": 5,
        "save_paths": save_paths,
        "backup_dir": safe,
    })
    _save(cfg)


def remove_game(backup_dir: str):
    cfg = _load()
    cfg["games"] = [g for g in cfg.get("games", []) if g["backup_dir"] != backup_dir]
    _save(cfg)
