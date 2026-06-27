# WavePalace — VPS Provisioning Guide

> **VPS is DEFERRED** — provision when Slice 4 (live events) becomes a priority.
> Estimated provisioning time: 2–3 hours.
> This is infrastructure setup, not application code. All toggle/schema work
> (pre-Slice 4 add-on) can be built without this server running.

---

## Server spec

| Field | Value |
|---|---|
| Provider | Hetzner Cloud — hetzner.com/cloud |
| Server type | CPX32 — 4 vCPU, 8 GB RAM (newer generation) |
| OS | Ubuntu 22.04 LTS |
| Region | FSN1 — Falkenstein, Germany |
| Monthly cost | ~$42/mo base · ~$51/mo with backups enabled |
| Hetzner project name | `wavepalace` |

**Why Hetzner CPX32 FSN1:**
- CPX32 at ~$42/mo vs ~$48/mo on DigitalOcean/Linode for identical specs
- FSN1 chosen at decision time: no active incidents · lower cost
- Avoid ASH (Ashburn): active Load Balancer incident + higher pricing at decision time
- Avoid HEL1 / NBG1: active Object Storage incidents at decision time
- Re-evaluate region availability at provisioning time — pick the lowest-incident datacenter

---

## Provisioning steps

### 1. Hetzner account + project

1. Sign up at **hetzner.com/cloud** (or log in)
2. Create a new project named `wavepalace`
3. Go to **SSH Keys** → add your public key (required before server creation)

### 2. Create the server

1. Click **Add Server**
2. Location: **FSN1 — Falkenstein** (re-check incident status at provisioning time)
3. Image: **Ubuntu 22.04 LTS**
4. Type: **CPX32** (4 vCPU / 8 GB)
5. SSH key: select the key added above
6. Name: `wavepalace-streaming`
7. Click **Create & Buy Now**

Note the public IP — you'll need it for DNS and SSH.

### 3. Cloudflare DNS

In Cloudflare for `wavepalace.live`:

1. Add an **A record**: `stream` → VPS public IP
2. Set proxy status to **DNS only (grey cloud)** — do NOT enable the orange cloud proxy
   - HTTP-TS (`.ts` streams) does not work through Cloudflare proxy on the free plan
   - HTTPS termination happens on the VPS directly

Verify: `dig stream.wavepalace.live A` should return the VPS IP directly.

### 4. Initial server setup

```bash
ssh root@<VPS_IP>
apt update && apt upgrade -y
apt install -y curl git ufw
```

Configure firewall:
```bash
ufw allow 22    # SSH
ufw allow 80    # HTTP (AzuraCast + certbot)
ufw allow 443   # HTTPS (AzuraCast + stream)
ufw allow 1935  # RTMP (SRS ingest)
ufw allow 8080  # HTTP-TS (SRS output)
ufw enable
```

### 5. Install Docker

```bash
curl -fsSL https://get.docker.com | sh
apt install -y docker-compose-plugin
systemctl enable docker
```

Verify: `docker --version && docker compose version`

### 6. Install AzuraCast

```bash
mkdir -p /var/azuracast && cd /var/azuracast
curl -fsSL https://raw.githubusercontent.com/AzuraCast/AzuraCast/stable/docker.sh > docker.sh
chmod +x docker.sh
./docker.sh install
```

During setup:
- Domain: `azuracast.wavepalace.live`
- HTTPS: Let's Encrypt (enter admin email)
- Admin password: save to a secure vault

AzuraCast will be accessible at `https://azuracast.wavepalace.live`.
**Admin never opens AzuraCast directly — WavePalace FastAPI proxies all calls.**

### 7. Install SRS (Simple Realtime Server)

```bash
docker run -d \
  --name srs \
  --restart always \
  -p 1935:1935 \
  -p 1985:1985 \
  -p 8080:8080 \
  -v /etc/srs:/etc/srs \
  ossrs/srs:5
```

Default SRS config accepts RTMP on port 1935 and outputs HTTP-TS on port 8080.
HTTP-TS URL pattern: `http://<VPS_IP>:8080/live/{slug}.ts`
After SSL setup: `https://stream.wavepalace.live/live/{slug}.ts`

Verify SRS API: `curl http://localhost:1985/api/v1/versions`

### 8. Install FFmpeg

```bash
apt install -y ffmpeg
ffmpeg -version  # confirm installed
```

### 9. FFmpeg systemd service (one per channel)

Create a template at `/etc/systemd/system/ffmpeg-channel@.service`:

```ini
[Unit]
Description=FFmpeg combiner for WavePalace channel %i
After=network.target

[Service]
Type=simple
Restart=always
RestartSec=5
ExecStart=/usr/bin/ffmpeg \
  -re -stream_loop -1 -i https://stream.wavepalace.live/icecast/%i \
  -re -stream_loop -1 -i https://stream.wavepalace.live/loops/%i/loop.mp4 \
  -c:v libx264 -preset ultrafast -tune zerolatency -r 1 \
  -c:a aac -b:a 256k \
  -f flv rtmp://localhost/live/%i

[Install]
WantedBy=multi-user.target
```

Enable for each channel slug:
```bash
systemctl enable ffmpeg-channel@late-night-house
systemctl start ffmpeg-channel@late-night-house
systemctl status ffmpeg-channel@late-night-house
```

---

## CORS config for audio visualizer (Slice 1C)

The web audio visualizer (Slice 1C) uses the Web Audio API to tap the live stream for
real-time frequency data. The browser requires CORS headers on the `.ts` stream responses
or it silently blocks `createMediaElementSource()`.

Add the following to the nginx config that fronts SRS (or directly in the SRS HTTP server
config if nginx is not used):

```nginx
location /live/ {
    add_header Access-Control-Allow-Origin "https://wavepalace.live";
    add_header Access-Control-Allow-Methods "GET, HEAD, OPTIONS";
    add_header Access-Control-Allow-Headers "*";
    proxy_pass http://127.0.0.1:8080;
}
```

Or if running SRS directly on port 8080 without nginx, add to `/etc/srs/srs.conf`:

```
http_server {
    enabled on;
    listen 8080;
    dir ./objs/nginx/html;
    cross_domains *;
}
```

The `<audio>` element in the web player already has `crossOrigin="anonymous"` (added in
Slice 1C). Without the server-side CORS header, the visualizer canvas goes dark but audio
still plays — graceful degradation is built in.

**Smoke test for visualizer CORS:**
```bash
curl -I -H "Origin: https://wavepalace.live" \
  https://stream.wavepalace.live/live/<slug>.ts | grep -i access-control
```
Should return `Access-Control-Allow-Origin: https://wavepalace.live`.

---

## Smoke test checklist

Run all checks after provisioning. Slice 4 code can begin once these pass.

- [ ] AzuraCast accessible at `https://azuracast.wavepalace.live` — admin login works
- [ ] SRS HTTP API responds: `curl http://localhost:1985/api/v1/versions` → JSON response
- [ ] FFmpeg service running: `systemctl status ffmpeg-channel@<slug>` → active (running)
- [ ] HTTP-TS stream reachable from VPS: `curl -I https://stream.wavepalace.live/live/<slug>.ts` → 200
- [ ] Stream plays in VLC: `vlc https://stream.wavepalace.live/live/<slug>.ts`
- [ ] Stream plays in VRChat test world — video visible, audio audible, no disconnect
- [ ] CORS headers present on `.ts` responses (visualizer requirement — see section above)

---

## Build order note

```
Slice 3 add-on:      External Stream Passthrough (liveStreamUrl field + admin UI)
                     No VPS required

Pre-Slice 4 add-on:  Add streamingActive + vrchatFallbackUrl to Channel schema
                     Player routing logic (three-tier chain)
                     Admin per-channel toggle, bulk toggle, mux refresh controls
                     Run POST /api/mux/all to populate vrchatFallbackUrl
                     No VPS required — all toggle work ships without VPS

Pre-Slice 4:         Provision Hetzner CPX32 FSN1 VPS (this guide)
                     Install AzuraCast + SRS + FFmpeg
                     Pass all smoke tests above

Slice 4:             Wire WavePalace FastAPI to running VPS
                     Live event streaming — ingest keys + link-in
                     Activation = flip streamingActive via existing admin toggle
```

---

## Troubleshooting

| Issue | Fix |
|---|---|
| SRS port 8080 not reachable | Check `ufw status` — port 8080 must be open |
| FFmpeg service crashes immediately | Check Icecast stream URL — AzuraCast station must be running and broadcasting |
| VRChat doesn't play the stream | VRChat requires HTTP-TS, not HLS or RTMP. Verify URL ends in `.ts` and SRS outputs HTTP-TS |
| Cloudflare grey cloud returns wrong IP | Cloudflare proxy must be OFF (grey cloud) for `stream.wavepalace.live` — verify in DNS settings |
| AzuraCast Let's Encrypt fails | Ensure port 80 is open in `ufw` and `stream.wavepalace.live` A record propagated before running certbot |
