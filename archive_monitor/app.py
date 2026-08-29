import logging
import os
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

from .instagram import InstaloaderSource
from .maintenance import create_monthly_backup, remove_expired_media, trim_archive_to_size
from .monitor import Monitor
from .telegram import RequestsTelegramTransport, TelegramPublisher

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
    try:
        source = InstaloaderSource(Path(os.getenv("INSTAGRAM_COOKIES_PATH", "/run/secrets/instagram-cookies.txt")), data_dir / "staging")
    except Exception as error:
        LOGGER.exception("Instagram authentication initialization failed")
        publisher.alert(f"Instagram archive monitor authentication failed: {error}")
        raise
    monitor = Monitor(source, publisher, data_dir / "archive", data_dir / "state.sqlite3", usernames)
    while True:
        try:
            count = monitor.run_once()
            LOGGER.info("Monitor cycle complete: %s new items", count)
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


if __name__ == "__main__":
    main()