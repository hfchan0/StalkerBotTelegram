from pathlib import Path

from archive_monitor.models import MediaItem
from archive_monitor.telegram import TelegramPublisher


class FakeTransport:
    def __init__(self, failures: int = 0) -> None:
        self.failures = failures
        self.calls: list[tuple[str, dict]] = []

    def post(self, method: str, payload: dict) -> None:
        self.calls.append((method, payload))
        if len(self.calls) <= self.failures:
            raise OSError("temporary Telegram failure")


def item() -> MediaItem:
    return MediaItem(
        media_id="post-1",
        username="authorized_creator",
        kind="post",
        source_url="https://instagram.com/p/post-1/",
        files=[],
        caption="A new post",
        published_at="2026-08-29T12:00:00Z",
    )


def test_publish_retries_transient_telegram_errors(tmp_path: Path) -> None:
    photo_path = tmp_path / "photo.jpg"
    video_path = tmp_path / "video.mp4"
    photo_path.write_bytes(b"image-bytes")
    video_path.write_bytes(b"video-bytes")
    transport = FakeTransport(failures=1)
    publisher = TelegramPublisher(transport, "-100123", "456", retries=2, sleep=lambda _: None)

    assert publisher.publish(item(), [photo_path, video_path]) is True

    assert [method for method, _ in transport.calls] == ["sendPhoto", "sendPhoto", "sendVideo"]
    assert all("authorized_creator" in payload["caption"] for _, payload in transport.calls[1:])


def test_publish_alerts_and_retains_media_larger_than_limit(tmp_path: Path) -> None:
    media_path = tmp_path / "large.mp4"
    media_path.write_bytes(b"0123456789")
    transport = FakeTransport()
    publisher = TelegramPublisher(transport, "-100123", "456", max_upload_bytes=5)

    assert publisher.publish(item(), [media_path]) is False

    assert [method for method, _ in transport.calls] == ["sendMessage"]
    assert "too large" in transport.calls[0][1]["text"]
    assert media_path.exists()