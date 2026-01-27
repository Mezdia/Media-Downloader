# YTDL Telegram Bot

Production-ready multilingual Telegram bot for YouTube downloads with:

- quality picker (`240p, 360p, 480p, 720p, 1080p, 2160p` when available)
- server-side download via `yt-dlp` + `ffmpeg` merge support
- hidden-group cache with stealth delivery (`copyMessage`/`file_id`, no forward header)
- 24h rolling per-user quota (default 500 MB), unlimited admins
- admin panel + admin commands + live admin logs
- six-language UI (`en, fa, ar, zh, ru, es`)
- reaction + temporary UX messages (`👀/🤖`, `👾`, `Processing...`)
- About section with GitHub buttons and required Mezdia texts
- local file integrity check before upload and immediate cleanup after upload verification

## Tech stack

- Python 3.11+
- `aiogram` 3.x
- `aiosqlite`
- `yt-dlp`
- `ffmpeg` available in PATH (or set `FFMPEG_PATH`)

## Required environment variables

Copy `.env.example` to `.env` and set values:

- `BOT_TOKEN` Telegram bot token
- `BOT_TELEGRAM_ID` bot username without `@`
- `ADMINS` admin user IDs as JSON array or comma list (example: `[123456789]`)
- `GROUP_CHAT_ID` hidden cache group ID (example: `-1001234567890`)
- `FORWARDER_NAME` bookkeeping display name
- `FORWARDER_ID` bookkeeping ID
- `GITHUB_DEVELOPER_URL` developer profile URL
- `GITHUB_PROJECT_URL` project repo URL

Also configurable:

- `DATABASE_URI` (`sqlite:///./bot.db`)
- `STORAGE_PATH` temp download path
- `MAX_DAILY_TRAFFIC_BYTES` default `524288000` (500MB)
- `MAX_CONCURRENT_DOWNLOADS`
- `DOWNLOAD_TIMEOUT_SECONDS`
- `FFMPEG_PATH`
- `LOG_LEVEL`

## Install

```bash
python -m pip install -e .[dev]
```

## Run database migration

Migration creates/updates schema and seeds initial admins/settings.

```bash
ytdl-bot-migrate
```

Or:

```bash
python -m ytdl_bot.migrate
```

## Run bot

```bash
ytdl-bot
```

Or:

```bash
python -m ytdl_bot.main
```

## Railway deploy

This repo includes `Dockerfile` and `railway.json`.

1. Push this repository to GitHub.
2. In Railway, create a new project from the repo.
3. Set all required environment variables from `.env.example`.
4. Deploy.

The container start command runs migration then starts the bot:

```bash
ytdl-bot-migrate && ytdl-bot
```

Notes:

- `ffmpeg` is installed in the container image.
- Bot uses long polling (no webhook URL required).
- Service type should be kept as a worker/background service.

## Localization

Localization files are in `locales/`:

- `en.json`
- `fa.json`
- `ar.json`
- `zh.json`
- `ru.json`
- `es.json`

All visible strings/buttons/status/admin-help texts are localized.

## User flow summary

1. User sends YouTube link.
2. Bot reacts (`👀` or `🤖`), sends temporary `👾` and `Processing...`.
3. Bot probes formats and sends thumbnail + quality keyboard with approximate size.
4. Temporary messages are deleted.
5. On quality click:
   - check quota (skip for admin)
   - check cache key `{youtube_id}:{quality}`
   - if cached: copy from hidden group to user (no forward tag)
   - if not cached: download, upload to user, upload cached canonical copy to group, save cache metadata
   - after upload verification, local file is deleted immediately from its full path and empty temp folders are pruned
6. Animated status message is shown during processing, then deleted after completion.
7. Final caption always ends with `@${BOT_TELEGRAM_ID}`.

## Admin panel and commands

Admin panel button is only shown to IDs in `ADMINS`.

Supported admin commands:

- `/admin_usage <user_id>`
- `/admin_reset_usage <user_id>`
- `/admin_set_group <group_chat_id>`
- `/admin_clear_group`
- `/admin_cache_add <youtube_id> <quality> <group_message_id> <file_id> <size_bytes> [group_chat_id]`
- `/admin_cache_remove <youtube_id> <quality>`
- `/admin_force_copy <youtube_id> <quality> <target_chat_id>`
- `/admin_add <user_id>`
- `/admin_remove <user_id>`

## Quota model

- Rolling window: **24 hours**
- Metric: **final sent file size** (bytes uploaded to user)
- Non-admin default: 500 MB / 24h
- Admins: unlimited

## Tests

Run:

```bash
python -m pytest -q
```

Included tests:

- cache-hit serving behavior
- quota enforcement
- admin log message format
- reaction + temporary message lifecycle

## Operations guide

See [docs/operations.md](docs/operations.md) for cache inspection/cleanup and group-cache troubleshooting.
