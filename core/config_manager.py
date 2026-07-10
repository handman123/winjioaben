import os, json, sys

# PyInstaller 打包后 sys._MEIPASS 是只读临时目录，应写到 exe 所在目录
if getattr(sys, 'frozen', False):
    CONFIG_DIR = os.path.join(os.path.dirname(sys.executable), "config")
else:
    CONFIG_DIR = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config")

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
    """返回所有已配置的游戏列表"""
    return load().get("games", [])

def add_game(name, folder, save_paths):
    """追加游戏配置（不覆盖已有游戏）"""
    cfg = load()
    safe = folder.replace("\\","_").replace("/","_").replace(" ","_")
    # 去重：已存在的同名游戏先移除
    cfg["games"] = [g for g in cfg.get("games", []) if g["backup_dir"] != safe]
    cfg["games"].append({"id": safe.lower(), "name": name, "steam_appid": "",
        "max_backups": 5, "save_paths": save_paths, "backup_dir": safe})
    save(cfg)

def remove_game(backup_dir):
    """删除指定游戏配置"""
    cfg = load()
    cfg["games"] = [g for g in cfg.get("games", []) if g["backup_dir"] != backup_dir]
    save(cfg)
