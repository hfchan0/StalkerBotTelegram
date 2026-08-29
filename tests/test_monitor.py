from pathlib import Path

from archive_monitor.models import MediaItem
from archive_monitor.monitor import Monitor


class FakeSource:
    def fetch(self, username: str, known_media_ids: set[str]) -> list[MediaItem]:
        if "post-1" in known_media_ids:
            return []
        return [
            MediaItem(
                media_id="post-1",
                username=username,
                kind="post",
                source_url="https://instagram.com/p/post-1/",
                files=[("photo.jpg", b"image-bytes")],
                caption="A new post",
                published_at="2026-08-29T12:00:00Z",
            )
        ]


class RecordingPublisher:
    def __init__(self) -> None:
        self.published: list[MediaItem] = []

    def publish(self, item: MediaItem, paths: list[Path]) -> bool:
        self.published.append(item)
        return True


def test_run_once_archives_and_publishes_new_media_only(tmp_path: Path) -> None:
    publisher = RecordingPublisher()
    monitor = Monitor(
        source=FakeSource(),
        publisher=publisher,
        archive_dir=tmp_path / "archive",
        state_path=tmp_path / "state.sqlite3",
        usernames=["authorized_creator"],
    )

    assert monitor.run_once() == 1
    assert (tmp_path / "archive" / "authorized_creator" / "2026" / "08" / "29" / "post-1" / "photo.jpg").read_bytes() == b"image-bytes"
    assert [item.media_id for item in publisher.published] == ["post-1"]

    assert monitor.run_once() == 0
    assert [item.media_id for item in publisher.published] == ["post-1"]