import http.cookiejar
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path

import instaloader

from .models import MediaItem

LOGGER = logging.getLogger(__name__)


class InstaloaderSource:
    """Fetches media only from the explicit, authorized username allowlist."""

    def __init__(
        self,
        cookie_path: Path,
        staging_dir: Path,
        include_stories: bool = True,
        include_posts_and_reels: bool = False,
    ) -> None:
        self.staging_dir = staging_dir
        self.include_stories = include_stories
        self.include_posts_and_reels = include_posts_and_reels
        self.loader = instaloader.Instaloader(
            dirname_pattern=str(staging_dir / "{target}"),
            download_comments=False,
            save_metadata=False,
            compress_json=False,
            post_metadata_txt_pattern="",
            storyitem_metadata_txt_pattern="",
            max_connection_attempts=1,
            quiet=True,
        )
        self._load_cookies(cookie_path)

    def fetch(self, username: str, known_media_ids: set[str]) -> list[MediaItem]:
        profile = instaloader.Profile.from_username(self.loader.context, username)
        result = []
        if self.include_posts_and_reels:
            posts_and_reels = list(profile.get_posts()) + list(profile.get_reels())
            result.extend(
                self._download_post(post, username)
                for post in posts_and_reels
                if f"post-{post.mediaid}" not in known_media_ids
            )
        if self.include_stories:
            result.extend(self.fetch_stories(username, known_media_ids, profile))
        return result

    def fetch_stories(
        self, username: str, known_media_ids: set[str], profile: instaloader.Profile | None = None
    ) -> list[MediaItem]:
        profile = profile or instaloader.Profile.from_username(self.loader.context, username)
        return [
            self._download_story(item, username)
            for story in self.loader.get_stories(userids=[profile.userid])
            for item in story.get_items()
            if f"story-{item.mediaid}" not in known_media_ids
        ]

    def fetch_post(self, url: str) -> MediaItem:
        post = instaloader.Post.from_shortcode(self.loader.context, self._shortcode_from_url(url))
        return self._download_post(post, post.owner_username)

    @staticmethod
    def _shortcode_from_url(url: str) -> str:
        path_parts = [part for part in url.split("?")[0].split("/") if part]
        if len(path_parts) < 2 or path_parts[-2] not in {"p", "reel"}:
            raise ValueError("URL must be an Instagram post or Reel link")
        return path_parts[-1]

    def _download_post(self, post: instaloader.Post, username: str) -> MediaItem:
        return self._download(
            media_id=f"post-{post.mediaid}",
            username=username,
            kind="post",
            source_url=f"https://www.instagram.com/p/{post.shortcode}/",
            caption=post.caption or "",
            published_at=post.date_utc.replace(tzinfo=timezone.utc).isoformat(),
            download=lambda target: self.loader.download_post(post, target=target),
        )

    def _download_story(self, story: instaloader.StoryItem, username: str) -> MediaItem:
        return self._download(
            media_id=f"story-{story.mediaid}",
            username=username,
            kind="story",
            source_url=f"https://www.instagram.com/stories/{username}/",
            caption="Instagram Story",
            published_at=story.date_utc.replace(tzinfo=timezone.utc).isoformat(),
            download=lambda target: self.loader.download_storyitem(story, target=target),
        )

    def _download(
        self,
        media_id: str,
        username: str,
        kind: str,
        source_url: str,
        caption: str,
        published_at: str,
        download: object,
    ) -> MediaItem:
        target = f"{username}--{media_id}"
        download(target)  # type: ignore[operator]
        item_dir = self.staging_dir / target
        files = [
            (path.name, path.read_bytes())
            for path in item_dir.iterdir()
            if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg", ".png", ".mp4", ".webp"}
        ]
        shutil.rmtree(item_dir, ignore_errors=True)
        if not files:
            raise RuntimeError(f"Instagram returned no media for {media_id}")
        return MediaItem(media_id, username, kind, source_url, files, caption, published_at)

    def _load_cookies(self, cookie_path: Path) -> None:
        if not cookie_path.is_file():
            raise FileNotFoundError(f"Instagram cookie file is missing: {cookie_path}")
        cookies = http.cookiejar.MozillaCookieJar(str(cookie_path))
        cookies.load(ignore_discard=True, ignore_expires=True)
        for cookie in cookies:
            if "instagram.com" in cookie.domain:
                self.loader.context._session.cookies.set_cookie(cookie)
        if not any(cookie.name == "sessionid" for cookie in self.loader.context._session.cookies):
            raise RuntimeError("cookies.txt does not contain an Instagram sessionid cookie")
        LOGGER.info("Loaded authenticated Instagram browser cookies")