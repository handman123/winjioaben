import os, sys

REQUIRED_DIRS = ["Steam/config", "Steam/ssfn", "Saves"]

def _exe_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_root():
    """返回存档根目录（exe 同级的 GameDataKeeper 目录）"""
    return os.path.join(_exe_dir(), "GameDataKeeper")

def validate():
    """检查目录结构是否符合规范，返回 (ok: bool, missing: [str])"""
    root = get_root()
    missing = []
    if not os.path.isdir(root):
        missing.append(root)
    for d in REQUIRED_DIRS:
        full = os.path.join(root, d)
        if not os.path.isdir(full):
            missing.append(full)
    return len(missing) == 0, missing

def ensure():
    """确保目录结构存在（创建缺失的目录）"""
    root = get_root()
    for d in [root] + [os.path.join(root, x) for x in REQUIRED_DIRS]:
        os.makedirs(d, exist_ok=True)
    return root
