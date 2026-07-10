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

def get_game():
    games = load().get("games", [])
    return games[0] if games else None

def set_game(name, folder, save_paths):
    cfg = load()
    safe = folder.replace("\\","_").replace("/","_").replace(" ","_")
    cfg["games"] = [{"id": safe.lower(), "name": name, "steam_appid": "",
        "max_backups": 5, "save_paths": save_paths, "backup_dir": safe}]
    save(cfg)
