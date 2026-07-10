import os

_PATTERNS = {"SaveFiles","SaveGames","Save","Saves","SaveData","Saved","saves","save","storage"}

def detect_running():
    try:
        import psutil
        for p in psutil.process_iter(['exe']):
            try:
                exe = p.info['exe']
                if exe and '\\steamapps\\common\\' in exe:
                    parts = exe.split('\\steamapps\\common\\')
                    folder = parts[1].split('\\')[0]
                    root = parts[0] + '\\steamapps\\common\\' + folder
                    return {"folder": folder, "root": root, "exe": exe}
            except: continue
    except ImportError: pass
    return None

def find_save_dirs(game_root, max_depth=4):
    found = []
    def scan(path, depth):
        if depth > max_depth: return
        try:
            for name in os.listdir(path):
                full = os.path.join(path, name)
                if os.path.isdir(full):
                    if name in _PATTERNS:
                        fc = sum(1 for _ in _walk(full))
                        if fc > 0:
                            found.append({"name": name, "path": full, "files": fc})
                    scan(full, depth + 1)
        except (PermissionError, OSError): pass
    scan(game_root, 0)
    return found

def _walk(path):
    for root, dirs, files in os.walk(path):
        for f in files: yield 1
