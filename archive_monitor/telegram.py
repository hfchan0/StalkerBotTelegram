import mimetypes
import time
from pathlib import Path
from typing import Callable, Protocol

import requests

from .models import MediaItem


class TelegramTransport(Protocol):
    def post(self, method: str, payload: dict) -> None: ...


class RequestsTelegramTransport:
    def __init__(self, bot_token: str) -> None:
        self.bot_token = bot_token

    def post(self, method: str, payload: dict) -> None:
        file_path = payload.pop("file", None)
        url = f"https://api.telegram.org/bot{self.bot_token}/{method}"
        if file_path is None:
            response = requests.post(url, json=payload, timeout=60)
        else:
            with Path(file_path).open("rb") as media:
                response = requests.post(
                    url,
                    data=payload,
                    files={"media": (Path(file_path).name, media)},
                    timeout=300,
                )
        response.raise_for_status()
        if not response.json().get("ok"):
            raise RuntimeError("Telegram API rejected the request")


class TelegramPublisher:
    def __init__(
        self,
        transport: TelegramTransport,
        channel_chat_id: str,
        alert_chat_id: str,
        max_upload_bytes: int = 50 * 1024 * 1024,
        retries: int = 3,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.transport = transport
        self.channel_chat_id = channel_chat_id
        self.alert_chat_id = alert_chat_id
        self.max_upload_bytes = max_upload_bytes
        self.retries = retries
        self.sleep = sleep

    def publish(self, item: MediaItem, paths: list[Path]) -> bool:
        caption = self._caption(item)
        delivered = True
        for index, path in enumerate(paths):
            if path.stat().st_size > self.max_upload_bytes:
                self.alert(
                    f"Telegram delivery skipped: {path.name} is too large. "
                    f"Local archive: {path}; source: {item.source_url}"
                )
                delivered = False
                continue
            method = "sendVideo" if self._is_video(path) else "sendPhoto"
            payload = {"chat_id": self.channel_chat_id, "file": str(path), "caption": caption}
            try:
                self._post_with_retry(method, payload)
            except Exception as error:
                self.alert(
                    f"Telegram delivery failed for {path.name}: {error}. "
                    f"Local archive retained: {path}; source: {item.source_url}"
                )
                delivered = False
        return delivered

    def alert(self, text: str) -> None:
        self._post_with_retry("sendMessage", {"chat_id": self.alert_chat_id, "text": text})

    def _post_with_retry(self, method: str, payload: dict) -> None:
        for attempt in range(self.retries):
            try:
                self.transport.post(method, payload.copy())
                return
            except Exception:
                if attempt == self.retries - 1:
                    raise
                self.sleep(2**attempt)

    @staticmethod
    def _is_video(path: Path) -> bool:
        return (mimetypes.guess_type(path.name)[0] or "").startswith("video/")

    @staticmethod
    def _caption(item: MediaItem) -> str:
        return f"@{item.username}\n{item.published_at}\n{item.caption}\n{item.source_url}"[:1024]