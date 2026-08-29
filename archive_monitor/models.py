from dataclasses import dataclass


@dataclass(frozen=True)
class MediaItem:
    media_id: str
    username: str
    kind: str
    source_url: str
    files: list[tuple[str, bytes]]
    caption: str
    published_at: str