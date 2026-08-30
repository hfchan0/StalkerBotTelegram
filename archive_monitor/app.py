import logging
import os
import shutil
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from .instagram import InstaloaderSource
from .maintenance import create_monthly_backup, remove_expired_media, trim_archive_to_size
from .monitor import Monitor
from .telegram import RequestsTelegramTransport, TelegramPublisher
from .telegram_control import TelegramStoryController

LOGGER = logging.getLogger(__name__)


def required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} must be set")
    return value


def main() -> None:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(message)s")
    data_dir = Path(os.getenv("DATA_DIR", "/data"))
    interval_seconds = int(os.getenv("POLL_INTERVAL_MINUTES", "20")) * 60
    usernames = [name.strip().removeprefix("@") for name in required("INSTAGRAM_USERNAMES").split(",") if name.strip()]
    if len(usernames) > 9:
        raise RuntimeError("INSTAGRAM_USERNAMES must contain at most nine authorized accounts")
    transport = RequestsTelegramTransport(required("TELEGRAM_BOT_TOKEN"))
    publisher = TelegramPublisher(transport, required("TELEGRAM_CHANNEL_CHAT_ID"), required("TELEGRAM_ALERT_CHAT_ID"))
    auth_failure_limit = int(os.getenv("AUTH_FAILURE_LIMIT", "3"))
    rate_limit_pause_seconds = int(os.getenv("RATE_LIMIT_PAUSE_MINUTES", "60")) * 60
    scheduled_monitoring = os.getenv("SCHEDULED_MONITORING", "false").lower() == "true"
    if auth_failure_limit < 1:
        raise RuntimeError("AUTH_FAILURE_LIMIT must be at least 1")
    monitor = None
    monitor_lock = threading.Lock()
    monitoring_paused = threading.Event()
    control_started = False
    authentication_failures = 0
    while True:
        try:
            if monitor is None:
                source = InstaloaderSource(
                    Path(os.getenv("INSTAGRAM_COOKIES_PATH", "/run/secrets/instagram-cookies.txt")),
                    data_dir / "staging",
                    include_posts_and_reels=os.getenv("MONITOR_POSTS_AND_REELS", "false").lower() == "true",
                )
                monitor = Monitor(source, publisher, data_dir / "archive", data_dir / "state.sqlite3", usernames)
            if not control_started:
                controller = TelegramStoryController(
                    transport,
                    int(required("TELEGRAM_ALERT_CHAT_ID")),
                    usernames,
                    lambda username: _download_stories(monitor, monitor_lock, username),
                    lambda paused: _set_monitoring_paused(monitoring_paused, paused),
                    lambda url: _download_post(monitor, monitor_lock, url),
                )
                threading.Thread(target=controller.run_forever, daemon=True).start()
                control_started = True
            if not scheduled_monitoring:
                LOGGER.info("Scheduled monitoring is disabled; waiting for Telegram commands")
            elif monitoring_paused.is_set():
                LOGGER.info("Scheduled monitoring is paused")
            else:
                with monitor_lock:
                    count = monitor.run_once()
                LOGGER.info("Monitor cycle complete: %s new items", count)
            authentication_failures = 0
            remove_expired_media(data_dir / "archive", int(os.getenv("RETENTION_DAYS", "365")))
            removed = trim_archive_to_size(
                data_dir / "archive", int(os.getenv("MAX_ARCHIVE_BYTES", str(15 * 1024**3)))
            )
            if removed:
                publisher.alert(f"Archive quota removed {removed} oldest media files.")
            current_month = datetime.now(timezone.utc).strftime("%Y-%m")
            if _backup_month_marker(data_dir).read_text().strip() != current_month:
                _create_backup(data_dir, current_month, publisher)
                _backup_month_marker(data_dir).write_text(current_month)
        except Exception as error:
            LOGGER.exception("Monitor cycle failed")
            try:
                if _is_rate_limited_error(error):
                    publisher.alert(
                        f"Instagram rate limit received. Polling paused for {rate_limit_pause_seconds // 60} minutes."
                    )
                    time.sleep(rate_limit_pause_seconds)
                elif _is_authentication_error(error):
                    monitor = None
                    authentication_failures += 1
                    publisher.alert(
                        f"Instagram authentication failed ({authentication_failures}/{auth_failure_limit}): {error}"
                    )
                    if authentication_failures >= auth_failure_limit:
                        _pause_until_restart()
                else:
                    publisher.alert(f"Instagram archive monitor failed: {error}")
            except Exception:
                LOGGER.exception("Could not send Telegram failure alert")
        finally:
            try:
                _warn_low_disk(data_dir, publisher)
            except Exception:
                LOGGER.exception("Could not check archive disk usage")
        time.sleep(interval_seconds)


def _warn_low_disk(data_dir: Path, publisher: TelegramPublisher) -> None:
    usage = shutil.disk_usage(data_dir)
    percent_used = usage.used * 100 // usage.total
    if percent_used >= 80:
        publisher.alert(f"Instagram archive disk warning: {percent_used}% used at {data_dir}")


def _create_backup(data_dir: Path, month: str, publisher: TelegramPublisher) -> None:
    backup = create_monthly_backup(data_dir / "archive", data_dir / "backups", month)
    publisher.alert(f"Monthly Instagram media backup is ready: {backup.name}. Download it over SFTP/SSH.")


def _backup_month_marker(data_dir: Path) -> Path:
    data_dir.mkdir(parents=True, exist_ok=True)
    marker = data_dir / ".last_backup_month"
    if not marker.exists():
        marker.write_text("")
    return marker


def _is_authentication_error(error: Exception) -> bool:
    message = str(error).lower()
    return any(keyword in message for keyword in ("cookie", "session", "login", "authentication", "401", "403", "checkpoint"))


def _is_rate_limited_error(error: Exception) -> bool:
    return "429" in str(error) or "too many requests" in str(error).lower()


def _pause_until_restart() -> None:
    LOGGER.error("Authentication failure limit reached; polling paused until the container is restarted")
    while True:
        time.sleep(3600)


def _download_stories(monitor: Monitor, monitor_lock: threading.Lock, username: str) -> int:
    with monitor_lock:
        return monitor.run_stories_once(username)


def _download_post(monitor: Monitor, monitor_lock: threading.Lock, url: str) -> int:
    with monitor_lock:
        return monitor.run_post_once(url)


def _set_monitoring_paused(monitoring_paused: threading.Event, paused: bool) -> None:
    if paused:
        monitoring_paused.set()
    else:
        monitoring_paused.clear()


if __name__ == "__main__":
    main()