# Deploy On Google Cloud

This guide deploys the authorized Instagram archive monitor to Google Compute Engine from Windows 11. The service has no web interface and makes only outbound HTTPS requests to Instagram and Telegram, so it needs no public application ports.

Google Cloud credits are temporary. Before creating the VM, open **Billing > Budgets & alerts** in the Google Cloud Console and create alerts at 50%, 90%, and 100% of the credit amount. Stop or delete the VM when you no longer want it running; stopped VMs can still incur persistent-disk charges.

## 1. Install And Sign In To The Google Cloud CLI

1. Install the [Google Cloud CLI](https://cloud.google.com/sdk/docs/install-sdk) for Windows.
2. Open a new PowerShell window and authenticate:

```powershell
gcloud auth login
gcloud auth application-default login
gcloud projects list
```

3. In the Google Cloud Console, create or select a project, then enable billing for it. Set the project ID below:

```powershell
$PROJECT_ID = "replace-with-your-project-id"
gcloud config set project $PROJECT_ID
```

## 2. Create The VM

Choose a nearby available region, such as `asia-east1` (Taiwan) or `asia-southeast1` (Singapore). An `e2-small` VM provides 2 GB RAM and is a sensible minimum for Docker, but it consumes credits. Use a 50 GB persistent boot disk for the archive.

```powershell
$ZONE = "asia-east1-a"
$VM_NAME = "instagram-archive-monitor"

gcloud compute instances create $VM_NAME `
  --zone $ZONE `
  --machine-type e2-small `
  --image-family ubuntu-2404-lts-amd64 `
  --image-project ubuntu-os-cloud `
  --boot-disk-size 50GB `
  --boot-disk-type pd-balanced `
  --tags instagram-archive-monitor
```

Do not add a HTTP/HTTPS firewall rule and do not open port 80, 443, or any Docker application port. The default Google Cloud SSH workflow is sufficient. For a stricter setup, use browser-based SSH with Identity-Aware Proxy rather than opening TCP 22 to the internet.

Connect:

```powershell
gcloud compute ssh $VM_NAME --zone $ZONE
```

## 3. Install Docker On The VM

Run these commands in the SSH session:

```bash
sudo apt update
sudo apt install -y ca-certificates curl git ufw
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
sudo ufw allow OpenSSH
sudo ufw enable
exit
```

Reconnect so the Docker group permission applies:

```powershell
gcloud compute ssh $VM_NAME --zone $ZONE
```

## 4. Upload The Project

First publish the implementation commit to your repository from the project directory on Windows:

```powershell
git push origin main
```

Then clone it on the VM. Replace the repository URL if you use a fork or private repository:

```bash
git clone https://github.com/hfchan0/StalkerBotTelegram.git ~/instagram-archive-monitor
cd ~/instagram-archive-monitor
mkdir -p data secrets
chmod 700 data secrets
cp .env.example .env
nano .env
chmod 600 .env
```

Fill in `.env` without quotes around usernames:

```env
INSTAGRAM_USERNAMES=creator_one,creator_two
TELEGRAM_BOT_TOKEN=your-real-token
TELEGRAM_CHANNEL_CHAT_ID=-1001234567890
TELEGRAM_ALERT_CHAT_ID=123456789
```

Never commit `.env`, browser cookies, or the `secrets/` directory.

## 5. Upload Chrome Cookies

On your Windows computer, sign in to the dedicated Instagram service account in Chrome and export Instagram cookies in Netscape `cookies.txt` format, including `sessionid`. Place the file temporarily in the project root as `cookies.txt`.

From PowerShell:

```powershell
gcloud compute scp .\cookies.txt "${VM_NAME}:~/instagram-archive-monitor/secrets/instagram-cookies.txt" --zone $ZONE
Remove-Item .\cookies.txt
```

On the VM:

```bash
cd ~/instagram-archive-monitor
chmod 600 secrets/instagram-cookies.txt
```

## 6. Start And Verify

On the VM:

```bash
cd ~/instagram-archive-monitor
docker compose up -d --build
docker compose ps
docker compose logs -f monitor
```

The initial scan may archive currently available media. Confirm that the private Telegram channel and `data/archive/` contain expected items before leaving the service unattended.

## Operations

Run these from the VM project directory:

```bash
docker compose logs --tail=200 monitor
docker compose restart monitor
docker compose up -d --build
df -h data
```

To replace an expired Instagram session, upload a new `cookies.txt` with `gcloud compute scp`, run `chmod 600 secrets/instagram-cookies.txt`, then run `docker compose restart monitor`.

To retrieve a monthly archive from Windows:

```powershell
gcloud compute scp "${VM_NAME}:~/instagram-archive-monitor/data/backups/instagram-media-YYYY-MM.tar.gz" "$HOME\Downloads\" --zone $ZONE
```

To avoid charges when pausing the monitor, stop the VM:

```powershell
gcloud compute instances stop $VM_NAME --zone $ZONE
```

Starting it later preserves the archive disk:

```powershell
gcloud compute instances start $VM_NAME --zone $ZONE
```