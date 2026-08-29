from datetime import datetime, timedelta, timezone
from pathlib import Path
import tarfile

from archive_monitor.maintenance import create_monthly_backup, remove_expired_media


def test_removes_only_media_older_than_retention_period(tmp_path: Path) -> None:
    expired = tmp_path / "archive" / "creator" / "old.jpg"
    retained = tmp_path / "archive" / "creator" / "new.jpg"
    expired.parent.mkdir(parents=True)
    expired.write_bytes(b"old")
    retained.write_bytes(b"new")
    old_timestamp = (datetime.now(timezone.utc) - timedelta(days=366)).timestamp()
    expired.touch()
    import os

    os.utime(expired, (old_timestamp, old_timestamp))

    assert remove_expired_media(tmp_path / "archive", 365) == 1
    assert not expired.exists()
    assert retained.exists()


def test_creates_media_only_monthly_backup(tmp_path: Path) -> None:
    media = tmp_path / "archive" / "creator" / "photo.jpg"
    state = tmp_path / "state.sqlite3"
    media.parent.mkdir(parents=True)
    media.write_bytes(b"image")
    state.write_bytes(b"state")

    backup = create_monthly_backup(tmp_path / "archive", tmp_path / "backups", "2026-08")

    with tarfile.open(backup) as archive:
        assert archive.getnames() == ["creator/photo.jpg"]