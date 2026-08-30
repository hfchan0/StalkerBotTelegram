from archive_monitor.telegram_control import TelegramStoryController


class FakeTransport:
    def __init__(self, updates: list[dict]) -> None:
        self.updates = updates
        self.posts: list[tuple[str, dict]] = []

    def get_updates(self, offset: int | None) -> list[dict]:
        return self.updates

    def post(self, method: str, payload: dict) -> None:
        self.posts.append((method, payload))


def test_stories_command_shows_only_authorized_accounts_to_control_chat() -> None:
    transport = FakeTransport(
        [{"update_id": 10, "message": {"text": "/stories", "chat": {"id": 123}}}]
    )
    controller = TelegramStoryController(transport, 123, ["creator_one", "creator_two"], lambda _: 0)

    controller.poll_once()

    assert transport.posts == [
        (
            "sendMessage",
            {
                "chat_id": 123,
                "text": "Select an account to download its active Stories.",
                "reply_markup": {
                    "inline_keyboard": [
                        [{"text": "@creator_one", "callback_data": "stories:creator_one"}],
                        [{"text": "@creator_two", "callback_data": "stories:creator_two"}],
                    ]
                },
            },
        )
    ]


def test_pause_command_is_restricted_to_control_chat() -> None:
    paused: list[bool] = []
    transport = FakeTransport(
        [
            {"update_id": 10, "message": {"text": "/pause", "chat": {"id": 999}}},
            {"update_id": 11, "message": {"text": "/pause", "chat": {"id": 123}}},
        ]
    )
    controller = TelegramStoryController(
        transport, 123, ["creator_one"], lambda _: 0, paused.append
    )

    controller.poll_once()

    assert paused == [True]
    assert transport.posts == [("sendMessage", {"chat_id": 123, "text": "Monitoring paused."})]


def test_help_command_lists_available_controls_for_control_chat() -> None:
    transport = FakeTransport(
        [{"update_id": 10, "message": {"text": "/help", "chat": {"id": 123}}}]
    )
    controller = TelegramStoryController(transport, 123, ["creator_one"], lambda _: 0)

    controller.poll_once()

    assert transport.posts == [
        (
            "sendMessage",
            {
                "chat_id": 123,
                "text": (
                    "Available commands:\n"
                        "/stories [username] - Select or type an allowed account for active Stories.\n"
                        "  Example: /stories creator_one\n"
                    "/download <Instagram URL> - Download an allowed post or Reel.\n"
                        "  Example: /download https://www.instagram.com/p/POST_CODE/\n"
                    "/pause - Stop scheduled monitoring.\n"
                    "/resume - Resume scheduled monitoring.\n"
                    "/help - Show this command list."
                ),
            },
        )
    ]


def test_download_command_passes_post_or_reel_url_from_control_chat() -> None:
    downloaded: list[str] = []
    transport = FakeTransport(
        [
            {
                "update_id": 10,
                "message": {
                    "text": "/download https://www.instagram.com/reel/ABC123/",
                    "chat": {"id": 123},
                },
            }
        ]
    )
    controller = TelegramStoryController(
        transport, 123, ["creator_one"], lambda _: 0, download_post=downloaded.append
    )

    controller.poll_once()

    assert downloaded == ["https://www.instagram.com/reel/ABC123/"]
    assert transport.posts[0] == (
        "sendMessage",
        {"chat_id": 123, "text": "Downloading the linked post or Reel."},
    )


def test_invalid_command_shows_example_usage() -> None:
    transport = FakeTransport(
        [{"update_id": 10, "message": {"text": "/download not-a-link", "chat": {"id": 123}}}]
    )
    controller = TelegramStoryController(transport, 123, ["creator_one"], lambda _: 0)

    controller.poll_once()

    assert transport.posts == [
        (
            "sendMessage",
            {
                "chat_id": 123,
                "text": "Usage: /download https://www.instagram.com/p/POST_CODE/\n"
                "Example: /download https://www.instagram.com/reel/REEL_CODE/",
            },
        )
    ]


def test_story_callback_without_message_text_downloads_selected_account() -> None:
    downloaded: list[str] = []
    transport = FakeTransport(
        [
            {
                "update_id": 10,
                "callback_query": {
                    "id": "callback-1",
                    "data": "stories:creator_one",
                    "message": {"chat": {"id": 123}},
                },
            }
        ]
    )
    controller = TelegramStoryController(transport, 123, ["creator_one"], downloaded.append)

    controller.poll_once()

    assert downloaded == ["creator_one"]
    assert transport.posts[0] == ("answerCallbackQuery", {"callback_query_id": "callback-1"})


def test_stories_command_accepts_manually_typed_allowed_username() -> None:
    downloaded: list[str] = []
    transport = FakeTransport(
        [{"update_id": 10, "message": {"text": "/stories creator_one", "chat": {"id": 123}}}]
    )
    controller = TelegramStoryController(transport, 123, ["creator_one"], downloaded.append)

    controller.poll_once()

    assert downloaded == ["creator_one"]
    assert transport.posts[0] == (
        "sendMessage",
        {"chat_id": 123, "text": "Downloading active Stories for @creator_one."},
    )