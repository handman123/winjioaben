import os, json
from core.disk import get_root

def _config_path():
    return os.path.join(get_root(), "games.json")

def _default():
    return {"version": "1.3", "comment": "", "games": []}

def load():
    p = _config_path()
    if not os.path.exists(p):
        return _default()
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

def save(cfg):
    os.makedirs(get_root(), exist_ok=True)
    with open(_config_path(), "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)

def get_games():
    return load().get("games", [])

def add_game(name, folder, save_paths):
    cfg = load()
    safe = folder.replace("\\","_").replace("/","_").replace(" ","_")
    cfg["games"] = [g for g in cfg.get("games", []) if g["backup_dir"] != safe]
    cfg["games"].append({"id": safe.lower(), "name": name, "steam_appid": "",
        "max_backups": 5, "save_paths": save_paths, "backup_dir": safe})
    save(cfg)

def remove_game(backup_dir):
    cfg = load()
    cfg["games"] = [g for g in cfg.get("games", []) if g["backup_dir"] != backup_dir]
    save(cfg)
