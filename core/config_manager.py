import os, json

# 配置文件路径由 set_data_drive() 动态设置
# 默认放在 exe 同目录下作为临时配置（数据盘未连接时使用）
if getattr(__import__('sys'), 'frozen', False):
    _default_dir = os.path.dirname(__import__('sys').executable)
else:
    _default_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CONFIG_DIR = os.path.join(_default_dir, "config")
GAMES_JSON = os.path.join(CONFIG_DIR, "games.json")

def set_data_drive(drive):
    """将配置文件路径切换到数据盘"""
    global CONFIG_DIR, GAMES_JSON
    if drive:
        CONFIG_DIR = os.path.join(drive, "GameDataKeeper")
        GAMES_JSON = os.path.join(CONFIG_DIR, "games.json")

def _default():
    return {"version": "1.3", "comment": "", "games": []}

def load():
    if not os.path.exists(GAMES_JSON):
        return _default()
    with open(GAMES_JSON, "r", encoding="utf-8") as f:
        return json.load(f)

def save(cfg):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(GAMES_JSON, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)

def get_games():
    return load().get("games", [])

def add_game(name, folder, save_paths):
    cfg = load()
    safe = folder.replace("\\","_").replace("/","_").replace(" ","_")
    cfg["games"] = [g for g in cfg.get("games", []) if g["backup_dir"] != safe]
    cfg["games"].append({"id": safe.lower(), "name": name, "steam_appid": "",
        "max_backups": 5, "save_paths": save_paths, "backup_dir": safe})
    config_dir = os.path.dirname(GAMES_JSON)
    save(cfg)

def remove_game(backup_dir):
    cfg = load()
    cfg["games"] = [g for g in cfg.get("games", []) if g["backup_dir"] != backup_dir]
    save(cfg)
