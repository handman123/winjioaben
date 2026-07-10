"""Steam 游戏进程发现 — 三级降级检测"""

import os
import subprocess

_SAVE_PATTERNS = {"SaveFiles", "SaveGames", "Save", "Saves", "SaveData", "Saved",
                  "saves", "save", "storage"}


def detect_running():
    """三级降级检测正在运行的 Steam 游戏，返回 {folder, root, exe} 或 None"""
    # 方案1: psutil（快速精确）
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
            except Exception:
                continue
    except ImportError:
        pass

    # 方案2: WMIC 降级（Windows 自带）
    try:
        r = subprocess.run(
            ["wmic", "process", "get", "ExecutablePath", "/format:csv"],
            capture_output=True, text=True, timeout=15
        )
        for line in r.stdout.splitlines():
            if '\\steamapps\\common\\' in line:
                parts = line.split(',')
                exe = parts[-1].strip()
                segs = exe.split('\\steamapps\\common\\')
                if len(segs) >= 2:
                    folder = segs[1].split('\\')[0]
                    root = segs[0] + '\\steamapps\\common\\' + folder
                    return {"folder": folder, "root": root, "exe": exe}
    except Exception:
        pass

    # 方案3: PowerShell 降级（Win10+ 最终保底）
    try:
        cmd = (
            "Get-CimInstance Win32_Process | "
            "Where-Object {$_.ExecutablePath -like '*steamapps\\common*'} | "
            "Select-Object -First 1 -ExpandProperty ExecutablePath"
        )
        r = subprocess.run(["powershell", "-NoProfile", "-Command", cmd],
                           capture_output=True, text=True, timeout=20)
        exe = r.stdout.strip()
        if exe and '\\steamapps\\common\\' in exe:
            segs = exe.split('\\steamapps\\common\\')
            folder = segs[1].split('\\')[0]
            root = segs[0] + '\\steamapps\\common\\' + folder
            return {"folder": folder, "root": root, "exe": exe}
    except Exception:
        pass

    return None


def find_save_dirs(game_root, max_depth=4):
    """递归搜索存档目录（匹配常见存档文件夹名）"""
    found = []

    def scan(path, depth):
        if depth > max_depth:
            return
        try:
            for name in os.listdir(path):
                full = os.path.join(path, name)
                if os.path.isdir(full):
                    if name in _SAVE_PATTERNS:
                        fc = sum(1 for _ in _walk(full))
                        if fc > 0:
                            found.append({"name": name, "path": full, "files": fc})
                    scan(full, depth + 1)
        except (PermissionError, OSError):
            pass

    scan(game_root, 0)
    return found


def diag_processes():
    """诊断：列出当前可见进程及其路径（用于排查检测失败原因）"""
    lines = []
    try:
        import psutil
        for p in psutil.process_iter(['name', 'exe']):
            try:
                name = p.info['name'] or ''
                exe = p.info['exe'] or ''
                if exe:
                    lines.append(f"  {name}  →  {exe}")
                else:
                    lines.append(f"  {name}  (路径不可读取)")
            except Exception:
                pass
    except ImportError:
        try:
            r = subprocess.run(
                ["wmic", "process", "get", "Name,ExecutablePath", "/format:csv"],
                capture_output=True, text=True, timeout=10
            )
            for line in r.stdout.splitlines():
                if ',' in line:
                    parts = line.split(',')
                    if len(parts) >= 3 and parts[2].strip():
                        lines.append(f"  {parts[1].strip()}  →  {parts[2].strip()}")
        except Exception:
            pass
    return '\n'.join(lines[:15])


def _walk(path):
    for root, dirs, files in os.walk(path):
        for f in files:
            yield 1
