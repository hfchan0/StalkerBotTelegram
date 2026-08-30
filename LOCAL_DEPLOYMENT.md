# Local Deployment On Windows 11

Run the authorized Instagram archive monitor on your own Windows 11 PC. It requires no domain name, VPS, router configuration, or open inbound ports; the service makes outbound HTTPS requests only.

Your PC must remain powered on, connected to the internet, and not sleeping for 24/7 monitoring. This is the lowest-cost deployment option.

## 1. Install Docker Desktop

1. Install [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/).
2. During setup, select the WSL 2 backend when prompted, then restart Windows if Docker requests it.
3. Open Docker Desktop and wait until it reports that the engine is running.
4. In PowerShell, from this project folder, verify Docker is available:

```powershell
docker version
docker compose version
```

## 2. Configure Windows For Continuous Operation

Open **Settings > System > Power & battery > Screen and sleep**. Set **When plugged in, put my device to sleep after** to **Never**. The screen can turn off; the computer must not sleep or hibernate.

Use a Windows account password and keep your device physically secure. The archive, Telegram token, and Instagram session live on this computer.

## 3. Create The Local Secrets And Storage Folders

From the project directory in PowerShell:

```powershell
Copy-Item .env.example .env
New-Item -ItemType Directory -Force data, secrets
```

Open `.env` and set your real values. Do not use quotes around usernames:

```env
INSTAGRAM_USERNAMES=creator_one,creator_two
TELEGRAM_BOT_TOKEN=your-real-token
TELEGRAM_CHANNEL_CHAT_ID=-1001234567890
TELEGRAM_ALERT_CHAT_ID=123456789
POLL_INTERVAL_MINUTES=20
SCHEDULED_MONITORING=false
MONITOR_POSTS_AND_REELS=false
RATE_LIMIT_PAUSE_MINUTES=60
AUTH_FAILURE_LIMIT=3
RETENTION_DAYS=365
# 15 GiB hard cap; oldest media is deleted first when this is exceeded.
MAX_ARCHIVE_BYTES=16106127360
```

Never commit `.env`, `data/`, or `secrets/` to Git. They are ignored by this project.

## 4. Export The Instagram Session From Chrome

Use a dedicated Instagram account with recovery email/phone and app-based 2FA. Sign in normally in Chrome.

1. Open the Chrome Web Store and search for a cookie exporter that explicitly exports Netscape `cookies.txt` files. A commonly used option is **Get cookies.txt LOCALLY**. Confirm it exports locally rather than sending cookies to a service, review its permissions, and remove it after exporting.
2. While signed in at `https://www.instagram.com`, click the extension icon, choose to export cookies for the current site, and save the result as `cookies.txt`.
3. Open the exported file in a text editor and confirm it contains a row with `sessionid` and the domain `.instagram.com` or `instagram.com`. Do not paste that value anywhere.
4. Move the file to `secrets/instagram-cookies.txt` in this project.

The session cookie is equivalent to an authenticated session. Never share it, upload it to GitHub, or send it through Telegram. If Instagram invalidates it, repeat this step and restart the monitor.

## 5. Start And Verify

Run:

```powershell
docker compose up -d --build
docker compose ps
docker compose logs -f monitor
```

Expected behavior:

- Docker shows the `instagram-archive-monitor` container as running.
- New media appears in your private Telegram archive channel.
- Media files appear in `data/archive/`.
- Errors, low-disk warnings, and monthly backup reminders go to your personal Telegram chat.

The first scan can download older unseen media. Start with one authorized account and inspect the Telegram channel before adding the second.

By default, scheduled monitoring is disabled. The service contacts Instagram only after you use `/stories` or `/download` in Telegram. Set `SCHEDULED_MONITORING=true` only when you want periodic checks. With scheduled monitoring enabled, it checks only active Stories by default. Set `MONITOR_POSTS_AND_REELS=true` only when you also want post/Reel monitoring; that mode makes substantially more Instagram requests and can download historical media on its first run. When Instagram returns HTTP 429, the monitor sends one alert and waits 60 minutes before its next attempt. Change `RATE_LIMIT_PAUSE_MINUTES` only to make this longer, not shorter.

Press `Ctrl+C` to stop following logs; it does not stop the monitor.

## Download Active Stories On Demand

In the personal Telegram chat you used for `TELEGRAM_ALERT_CHAT_ID`, send the bot `/stories`. It shows buttons for only the accounts in `INSTAGRAM_USERNAMES`. Select one button to immediately download and forward its currently active Stories. You can also type an allowed username directly, for example `/stories creator_one`.

This cannot recover expired Stories and does not download profile posts or Reels. The account picker accepts commands only from your configured personal alert chat; do not change that chat ID to a public group.

To download a selected post or Reel, send `/download ` followed by its full Instagram URL, for example `/download https://www.instagram.com/p/POST_CODE/`. The bot downloads the photos/videos only when the linked post belongs to an account in `INSTAGRAM_USERNAMES`.

Send `/pause` in the same personal chat to stop scheduled Instagram checks without stopping the container. Send `/resume` to enable scheduled checks again. These commands take effect until the container restarts.

Send `/help` (or `/start`) in the same chat to see the available commands.

## Operations

Run these commands from the project folder:

```powershell
docker compose logs --tail=200 monitor
docker compose restart monitor
docker compose up -d --build
docker compose down
docker compose ps
```

`docker compose down` stops the monitor. Start it again with `docker compose up -d --build`.

To replace expired cookies:

1. Export a fresh Chrome `cookies.txt`.
2. Replace `secrets/instagram-cookies.txt`.
3. Run `docker compose restart monitor`. After three consecutive authentication alerts, the monitor pauses polling until this restart, preventing repeated Telegram alerts.

## Backups And Disk Space

The service retains archive media for 365 days, enforces a 15 GiB hard archive limit by removing the oldest media first, and creates a media-only compressed backup under `data/backups/` each month. Copy the backup to an external drive or another computer after receiving the Telegram reminder. Change `MAX_ARCHIVE_BYTES` in `.env` to adjust the cap; for example, `10737418240` is 10 GiB.

Check free disk space in PowerShell:

```powershell
Get-PSDrive -PSProvider FileSystem
```

The monitor alerts at 80% usage. Keep at least several gigabytes free for Docker and incoming videos.

## Start Docker After Reboot

In Docker Desktop, open **Settings > General** and enable **Start Docker Desktop when you sign in**. Docker restarts the service automatically because Compose uses `restart: unless-stopped`.

After a Windows update or reboot, sign in to your Windows account so Docker Desktop can start. Check the monitor with:

```powershell
docker compose ps
```