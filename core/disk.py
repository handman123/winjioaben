import os, string

ID = "GameDataKeeper\\.datadisk_id"

def find():
    for l in string.ascii_uppercase:
        if os.path.exists(os.path.join(f"{l}:", ID)):
            return f"{l}:"
    return None

def list_drives():
    return [f"{l}:" for l in string.ascii_uppercase if os.path.exists(f"{l}:\\")]

def init(drive):
    root = os.path.join(drive, "GameDataKeeper")
    for d in [root, f"{root}\\Steam\\config", f"{root}\\Steam\\ssfn", f"{root}\\Saves"]:
        os.makedirs(d, exist_ok=True)
    with open(os.path.join(root, ".datadisk_id"), "w") as f:
        f.write("# GameDataKeeper\n")
    return True
