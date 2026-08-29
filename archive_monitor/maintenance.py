import tarfile
from datetime import datetime, timedelta, timezone
from pathlib import Path


def remove_expired_media(archive_dir: Path, retention_days: int) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    deleted = 0
    for path in archive_dir.rglob("*"):
        if path.is_file() and datetime.fromtimestamp(path.stat().st_mtime, timezone.utc) < cutoff:
            path.unlink()
            deleted += 1
    for path in sorted(archive_dir.rglob("*"), reverse=True):
        if path.is_dir() and not any(path.iterdir()):
            path.rmdir()
    return deleted


def create_monthly_backup(archive_dir: Path, backup_dir: Path, month: str) -> Path:
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / f"instagram-media-{month}.tar.gz"
    with tarfile.open(backup_path, "w:gz") as archive:
        for path in sorted(archive_dir.rglob("*")):
            if path.is_file():
                archive.add(path, arcname=path.relative_to(archive_dir))
    return backup_path