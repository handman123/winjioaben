import os
import zipfile
from datetime import datetime

from shared.exceptions import SourceNotFoundError, SourceEmptyError, BackupError


def _count(source_path):
    total_bytes = 0
    for root, dirs, files in os.walk(source_path):
        for f in files:
            try:
                total_bytes += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return total_bytes


def backup(source_path, backup_base_dir, max_backups=5, on_progress=None):
    """备份源目录为 zip。成功返回 info dict，失败抛出 BackupError 子类。"""
    if not os.path.exists(source_path):
        raise SourceNotFoundError(source_path)
    if not os.listdir(source_path):
        raise SourceEmptyError(source_path)

    total = _count(source_path)
    if total == 0:
        raise SourceEmptyError(source_path)

    os.makedirs(backup_base_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    zp = os.path.join(backup_base_dir, f"{ts}.zip")
    done = 0

    try:
        with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(source_path):
                for f in files:
                    fp = os.path.join(root, f)
                    try:
                        zf.write(fp, os.path.relpath(fp, source_path))
                        done += os.path.getsize(fp)
                        if on_progress and total > 0:
                            on_progress(done, total)
                    except OSError:
                        pass
    except Exception as e:
        if os.path.exists(zp):
            os.remove(zp)
        raise BackupError(f"压缩失败: {e}", detail=str(e))

    # Rotation: keep at most max_backups
    zips = sorted([x for x in os.listdir(backup_base_dir) if x.endswith(".zip")], reverse=True)
    deleted = []
    while len(zips) > max_backups:
        old = zips.pop()
        os.remove(os.path.join(backup_base_dir, old))
        deleted.append(old)

    return {
        "zip": f"{ts}.zip",
        "zip_size": os.path.getsize(zp),
        "original": total,
        "count": len(zips),
        "deleted": deleted,
    }


def restore(save_path, backup_base_dir, specific=None, on_progress=None):
    """从 zip 恢复存档。成功返回 info dict，失败抛出 BackupError 子类。"""
    if not os.path.exists(backup_base_dir):
        raise BackupError(f"备份目录不存在: {backup_base_dir}", recoverable=True)

    zips = sorted([x for x in os.listdir(backup_base_dir) if x.endswith(".zip")], reverse=True)
    if not zips:
        raise BackupError("无可用备份", recoverable=True)

    zip_name = specific if specific else zips[0]
    zp = os.path.join(backup_base_dir, zip_name)
    if not os.path.exists(zp):
        raise BackupError(f"备份文件不存在: {zip_name}", recoverable=True)

    # 清空目标目录
    os.makedirs(save_path, exist_ok=True)
    for item in os.listdir(save_path):
        ip = os.path.join(save_path, item)
        try:
            if os.path.isfile(ip) or os.path.islink(ip):
                os.unlink(ip)
            elif os.path.isdir(ip):
                import shutil
                shutil.rmtree(ip)
        except OSError:
            pass

    try:
        with zipfile.ZipFile(zp, "r") as zf:
            entries = zf.infolist()
            total = sum(e.file_size for e in entries)
            done = 0
            for e in entries:
                zf.extract(e, save_path)
                done += e.file_size
                if on_progress and total > 0:
                    on_progress(done, total)
    except Exception as e:
        raise BackupError(f"解压失败: {e}", detail=str(e))

    return {"zip": zip_name, "total": total}


def list_all(backup_base_dir):
    """列出所有备份，按时间倒序"""
    if not os.path.exists(backup_base_dir):
        return []
    result = []
    for z in sorted([x for x in os.listdir(backup_base_dir) if x.endswith(".zip")], reverse=True):
        zp = os.path.join(backup_base_dir, z)
        result.append({
            "name": z,
            "size": os.path.getsize(zp),
            "time": datetime.fromtimestamp(os.path.getmtime(zp)).strftime("%Y-%m-%d %H:%M:%S"),
        })
    return result
