# Authorized Instagram Archive Monitor

This project checks a small, explicit allowlist of public Instagram accounts, archives new posts/Reels and Stories locally, and forwards the media to a private Telegram channel. Use it only for accounts that have given you permission.

## What it does

- Polls the configured account list every 20 minutes by default.
- Stores media at `data/archive/<username>/<YYYY>/<MM>/<DD>/<media-id>/`.
- Uses SQLite to avoid duplicate Telegram delivery after restarts.
- Retries transient Telegram delivery failures and retains local files when forwarding fails or exceeds 50 MiB.
- Removes archived media older than 365 days and creates a media-only `.tar.gz` backup once per calendar month.
- Sends private Telegram alerts for monitor failures, disk usage of at least 80%, skipped large media, and a monthly backup reminder.

Instagram provides no supported webhook for arbitrary public accounts, so this is polling-based. Expired Stories cannot be recovered if the service or its session is unavailable.

## 1. Create the Telegram destinations

1. Open `@BotFather` in Telegram, send `/newbot`, follow the prompts, and copy the API token into `TELEGRAM_BOT_TOKEN`.
2. Create a **private channel** for the archive. Add the bot as an administrator with permission to post.
3. Send `/start` to the bot from your personal account; this enables personal alert messages.
4. Visit `https://api.telegram.org/bot<TOKEN>/getUpdates` after sending the bot a message. Find your personal `message.chat.id` for `TELEGRAM_ALERT_CHAT_ID`.
5. Post a test message in the archive channel, call `getUpdates` again, and find the channel `chat.id` (normally beginning `-100`) for `TELEGRAM_CHANNEL_CHAT_ID`.

Do not paste the token into a shell history or commit it.

## 2. Create the Oracle Always Free VPS

1. Create an Oracle Cloud account with your real billing information. From Hong Kong, try the nearest available home region; Always Free capacity varies.
2. In **Compute > Instances**, create an Always Free Ubuntu 24.04 instance with at least 1 OCPU, 1 GB RAM, and a 50 GB boot volume. An ARM instance with 2 GB RAM is preferable when capacity is available.
3. Generate an SSH key in PowerShell:

```powershell
ssh-keygen -t ed25519 -f $HOME\.ssh\instagram-archive-oracle
```

4. Paste the contents of `$HOME\.ssh\instagram-archive-oracle.pub` into Oracle's SSH key field when creating the instance.
5. Oracle security lists should allow only TCP 22 from your current public IP. Do not expose any application ports.
6. Connect, replacing the IP address:

```powershell
ssh -i $HOME\.ssh\instagram-archive-oracle ubuntu@<VPS_IP>
```

7. On the VPS, install Docker and lock down its firewall:

```bash
sudo apt update
sudo apt install -y ca-certificates curl git ufw
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
sudo ufw allow OpenSSH
sudo ufw enable
exit
```

Reconnect after the group change.

## 3. Upload and configure

From Windows PowerShell:

```powershell
scp -i $HOME\.ssh\instagram-archive-oracle -r . ubuntu@<VPS_IP>:~/instagram-archive-monitor
ssh -i $HOME\.ssh\instagram-archive-oracle ubuntu@<VPS_IP>
```

On the VPS:

```bash
cd ~/instagram-archive-monitor
cp .env.example .env
mkdir -p data secrets
chmod 700 data secrets
nano .env
```

Set the two authorized usernames, bot token, channel ID, and personal alert chat ID. Keep `.env` and `secrets/` private:

```bash
chmod 600 .env
```

## 4. Export the Instagram session cookies from Chrome

Use a dedicated Instagram account with recovery email/phone and app-based 2FA. Sign in normally in Chrome; do not automate the account-creation or login flow.

1. Install a reputable Chrome cookie exporter that writes **Netscape `cookies.txt`** format. Review the extension's permissions and remove it afterward.
2. While signed in at `https://www.instagram.com`, export **only** Instagram cookies, including `sessionid`, as `cookies.txt`.
3. Transfer it securely from your Windows computer:

```powershell
scp -i $HOME\.ssh\instagram-archive-oracle .\cookies.txt ubuntu@<VPS_IP>:~/instagram-archive-monitor/secrets/instagram-cookies.txt
```

4. On the VPS, restrict the file:

```bash
chmod 600 secrets/instagram-cookies.txt
```

The service reads the file read-only. Sessions can expire or be challenged; when alerts show authentication trouble, export a fresh cookie file and restart the service. Never upload this cookie file to GitHub or send it in Telegram.

## 5. Start and operate

```bash
docker compose up -d --build
docker compose logs -f monitor
docker compose ps
```

The first run imports currently available items. To avoid an initial backlog, start with one authorized account and review the archive channel before adding the second. The monitor only performs outbound HTTPS requests; Compose exposes no ports.

Useful operations:

```bash
docker compose restart monitor
docker compose logs --tail=200 monitor
docker compose pull
docker compose up -d --build
```

## 6. Download the monthly backup

When the bot alerts that the monthly backup is ready, run from Windows:

```powershell
scp -i $HOME\.ssh\instagram-archive-oracle ubuntu@<VPS_IP>:~/instagram-archive-monitor/data/backups/instagram-media-YYYY-MM.tar.gz $HOME\Downloads\
```

Verify the download before removing anything on the VPS. The backup contains only archived media, never cookies, `.env`, tokens, or the SQLite state.