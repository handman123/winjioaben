import os, shutil, subprocess, time, winreg

def find_path():
    for k in [r"SOFTWARE\WOW6432Node\Valve\Steam", r"SOFTWARE\Valve\Steam"]:
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, k)
            p, _ = winreg.QueryValueEx(key, "InstallPath")
            winreg.CloseKey(key)
            if os.path.exists(p): return p
        except OSError: continue
    for dp in [r"C:\Program Files (x86)\Steam", r"D:\Program Files (x86)\Steam", r"C:\Steam"]:
        if os.path.exists(dp): return dp
    return None

def is_running():
    try:
        r = subprocess.run(["tasklist","/FI","IMAGENAME eq steam.exe"], capture_output=True, text=True)
        return "steam.exe" in r.stdout.lower()
    except: return False

def kill():
    if is_running():
        subprocess.run(["taskkill","/F","/IM","steam.exe"], capture_output=True)
        time.sleep(3)

def launch(steam_path):
    exe = os.path.join(steam_path, "steam.exe")
    if os.path.exists(exe):
        subprocess.Popen([exe], shell=True)

def backup(steam_path, data_drive):
    root = os.path.join(data_drive, "Steam")
    cfg = os.path.join(root, "config"); ssfn = os.path.join(root, "ssfn")
    os.makedirs(cfg, exist_ok=True); os.makedirs(ssfn, exist_ok=True)
    r = []
    for f in os.listdir(steam_path):
        if f.startswith("ssfn") and os.path.isfile(os.path.join(steam_path, f)):
            shutil.copy2(os.path.join(steam_path, f), ssfn); r.append(f"ssfn/{f}")
    for f in ["loginusers.vdf","config.vdf"]:
        src = os.path.join(steam_path, "config", f)
        if os.path.exists(src): shutil.copy2(src, cfg); r.append(f"config/{f}")
    try:
        subprocess.run(["reg","export",r"HKCU\Software\Valve\Steam",
            os.path.join(root,"registry.reg"),"/y"], capture_output=True, check=True)
        r.append("registry")
    except: pass
    return r

def restore(steam_path, data_drive):
    root = os.path.join(data_drive, "Steam")
    r = []
    ssfn = os.path.join(root, "ssfn")
    if os.path.exists(ssfn):
        for f in os.listdir(ssfn):
            shutil.copy2(os.path.join(ssfn, f), steam_path); r.append(f"ssfn/{f}")
    steam_cfg = os.path.join(steam_path, "config")
    os.makedirs(steam_cfg, exist_ok=True)
    for f in ["loginusers.vdf","config.vdf"]:
        src = os.path.join(root, "config", f)
        if os.path.exists(src): shutil.copy2(src, steam_cfg); r.append(f"config/{f}")
    regf = os.path.join(root, "registry.reg")
    if os.path.exists(regf):
        try: subprocess.run(["reg","import",regf], capture_output=True, check=True); r.append("registry")
        except: pass
    return r
