import logging
from urllib.parse import urlparse
from typing import Callable, Protocol

LOGGER = logging.getLogger(__name__)


def _ignore_pause_change(paused: bool) -> None:
    pass


class ControlTransport(Protocol):
    def get_updates(self, offset: int | None) -> list[dict]: ...

    def post(self, method: str, payload: dict) -> None: ...


class TelegramStoryController:
    def __init__(
        self,
        transport: ControlTransport,
        control_chat_id: int,
        usernames: list[str],
        download_stories: Callable[[str], int],
        set_paused: Callable[[bool], None] = _ignore_pause_change,
        download_post: Callable[[str], int] | None = None,
    ) -> None:
        self.transport = transport
        self.control_chat_id = control_chat_id
        self.usernames = usernames
        self.download_stories = download_stories
        self.set_paused = set_paused
        self.download_post = download_post
        self.offset: int | None = None

    def run_forever(self) -> None:
        while True:
            try:
                self.poll_once()
            except Exception:
                LOGGER.exception("Telegram story control poll failed")

    def poll_once(self) -> None:
        for update in self.transport.get_updates(self.offset):
            self.offset = update["update_id"] + 1
            self._handle_update(update)

    def _handle_update(self, update: dict) -> None:
        message = update.get("message", {})
        text = message.get("text", "").strip()
        if text and message.get("chat", {}).get("id") == self.control_chat_id:
            command = text.split(maxsplit=1)[0].split("@", 1)[0]
            if command == "/stories":
                self._handle_stories_command(text)
            elif command == "/pause":
                self.set_paused(True)
                self._send_message("Monitoring paused.")
            elif command == "/resume":
                self.set_paused(False)
                self._send_message("Monitoring resumed.")
            elif command == "/download":
                self._download_linked_media(message.get("text", ""))
            elif command in {"/help", "/start"}:
                self._send_message(self._help_text())
            else:
                self._send_message(f"Unknown command.\n\n{self._help_text()}")
            return
        callback = update.get("callback_query", {})
        if callback.get("message", {}).get("chat", {}).get("id") != self.control_chat_id:
            return
        username = callback.get("data", "").removeprefix("stories:")
        if not callback or username not in self.usernames:
            return
        self.transport.post("answerCallbackQuery", {"callback_query_id": callback["id"]})
        self._download_stories_for_username(username)

    def _handle_stories_command(self, message: str) -> None:
        _, _, username = message.partition(" ")
        username = username.strip().removeprefix("@")
        if not username:
            self._show_account_picker()
        elif username in self.usernames:
            self._download_stories_for_username(username)
        else:
            self._send_message(
                "Usage: /stories or /stories ALLOWED_USERNAME\n"
                "Example: /stories creator_one"
            )

    def _download_stories_for_username(self, username: str) -> None:
        self._send_message(f"Downloading active Stories for @{username}.")
        try:
            count = self.download_stories(username)
            self._send_message(f"Finished @{username}: {count} new Story items delivered.")
        except Exception as error:
            LOGGER.exception("Manual Story download failed for %s", username)
            self._send_message(f"Could not download Stories for @{username}: {error}")

    def _show_account_picker(self) -> None:
        keyboard = [
            [{"text": f"@{username}", "callback_data": f"stories:{username}"}]
            for username in self.usernames
        ]
        self.transport.post(
            "sendMessage",
            {
                "chat_id": self.control_chat_id,
                "text": "Select an account to download its active Stories.",
                "reply_markup": {"inline_keyboard": keyboard},
            },
        )

    def _download_linked_media(self, message: str) -> None:
        _, _, url = message.partition(" ")
        if self.download_post is None or not self._is_instagram_post_or_reel_url(url):
            self._send_message(
                "Usage: /download https://www.instagram.com/p/POST_CODE/\n"
                "Example: /download https://www.instagram.com/reel/REEL_CODE/"
            )
            return
        self._send_message("Downloading the linked post or Reel.")
        try:
            count = self.download_post(url)
            self._send_message(f"Finished: {count} new media items delivered.")
        except Exception as error:
            LOGGER.exception("Manual linked-media download failed")
            self._send_message(f"Could not download the link: {error}")

    @staticmethod
    def _is_instagram_post_or_reel_url(url: str) -> bool:
        parsed = urlparse(url)
        return parsed.netloc.lower() in {"instagram.com", "www.instagram.com"} and (
            parsed.path.startswith("/p/") or parsed.path.startswith("/reel/")
        )

    def _send_message(self, text: str) -> None:
        self.transport.post("sendMessage", {"chat_id": self.control_chat_id, "text": text})

    @staticmethod
    def _help_text() -> str:
        return (
            "Available commands:\n"
            "/stories [username] - Select or type an allowed account for active Stories.\n"
            "  Example: /stories creator_one\n"
            "/download <Instagram URL> - Download an allowed post or Reel.\n"
            "  Example: /download https://www.instagram.com/p/POST_CODE/\n"
            "/pause - Stop scheduled monitoring.\n"
            "/resume - Resume scheduled monitoring.\n"
            "/help - Show this command list."
        )