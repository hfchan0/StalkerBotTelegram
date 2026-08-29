import sqlite3
from pathlib import Path
from typing import Protocol

from .models import MediaItem


class MediaSource(Protocol):
    def fetch(self, username: str, known_media_ids: set[str]) -> list[MediaItem]: ...


class Publisher(Protocol):
    def publish(self, item: MediaItem, paths: list[Path]) -> bool: ...


class Monitor:
    def __init__(
        self,
        source: MediaSource,
        publisher: Publisher,
        archive_dir: Path,
        state_path: Path,
        usernames: list[str],
    ) -> None:
        self.source = source
        self.publisher = publisher
        self.archive_dir = archive_dir
        self.state_path = state_path
        self.usernames = usernames
        self._initialize_state()

    def run_once(self) -> int:
        discovered = 0
        for username in self.usernames:
            for item in self.source.fetch(username, self._known_media_ids()):
                if self._is_seen(item.media_id):
                    continue
                paths = self._archive(item)
                if not self.publisher.publish(item, paths):
                    continue
                self._mark_seen(item.media_id)
                discovered += 1
        return discovered

    def _initialize_state(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.state_path) as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS delivered_media (media_id TEXT PRIMARY KEY)"
            )

    def _is_seen(self, media_id: str) -> bool:
        with sqlite3.connect(self.state_path) as connection:
            return connection.execute(
                "SELECT 1 FROM delivered_media WHERE media_id = ?", (media_id,)
            ).fetchone() is not None

    def _known_media_ids(self) -> set[str]:
        with sqlite3.connect(self.state_path) as connection:
            return {
                row[0]
                for row in connection.execute("SELECT media_id FROM delivered_media")
            }

    def _mark_seen(self, media_id: str) -> None:
        with sqlite3.connect(self.state_path) as connection:
            connection.execute(
                "INSERT INTO delivered_media (media_id) VALUES (?)", (media_id,)
            )

    def _archive(self, item: MediaItem) -> list[Path]:
        date_path = item.published_at[:10].replace("-", "/")
        item_dir = self.archive_dir / item.username / date_path / item.media_id
        item_dir.mkdir(parents=True, exist_ok=True)
        paths = []
        for filename, content in item.files:
            path = item_dir / filename
            path.write_bytes(content)
            paths.append(path)
        return paths