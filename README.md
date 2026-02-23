# Media Downloader Telegram Bot

Production-ready Telegram bot for YouTube downloads with multilingual UX, quality selection, hidden-group caching, per-user traffic limits, and admin operations.

## Highlights

- YouTube quality picker from allowed targets: `240p, 360p, 480p, 720p, 1080p, 2160p`.
- Reliable download pipeline with `yt-dlp` and `ffmpeg` merge support.
- Stealth cache serving using `copyMessage` or `file_id` (no forwarded header shown to users).
- Rolling traffic quota (24h) for regular users, unlimited for admins.
- Admin panel and admin commands for usage, cache, group config, forced copy, and job cancellation.
- Live status updates for users and live stage logs for admins.
- Full localization for `en`, `fa`, `ar`, `zh`, `ru`, `es`.
- Temporary UX flow (`👀/🤖`, `👾`, localized `Processing...`) with cleanup.
- Local file integrity checks before upload and immediate file cleanup after verified upload.
- About section with Mezdia credits and GitHub buttons.

## Architecture

The bot is structured in clear layers for maintainability and production safety.

### 1) Entry / bootstrap

- `src/ytdl_bot/main.py`: app startup, logging init, dependency wiring.
- `src/ytdl_bot/migrate.py`: schema migration and initial settings seed.

### 2) Configuration

- `src/ytdl_bot/config.py`: environment parsing and validation.
- Supports strict required variables plus runtime tuning (quota, concurrency, storage, timeout, ffmpeg path).

### 3) Transport and handlers

- `src/ytdl_bot/bot.py`: aiogram router and full user/admin flows.
- Handles callbacks, command routing, authorization checks, cache-vs-download routing, status lifecycle, and error recovery.

### 4) Domain services

- `src/ytdl_bot/youtube.py`: metadata probe + downloadable format resolution + download/merge.
- `src/ytdl_bot/progress.py`: animated user status + admin stage logging.
- `src/ytdl_bot/media.py`: file integrity verification and post-upload cleanup helpers.
- `src/ytdl_bot/logic.py`: isolated logic for quota checks and cached delivery helper.

### 5) Persistence

- `src/ytdl_bot/database.py`: SQLite schema + async CRUD operations.
- Core tables:
  - `users` (language + required usage columns)
  - `usage_events` (24h rolling accounting)
  - `cache` (youtube_id + quality -> group message/file metadata)
  - `jobs` (active/in-flight status)
  - `pending_requests` (quality selection context)
  - `settings` and `admins`

### 6) UI and i18n

- `src/ytdl_bot/keyboards.py`: inline keyboard builders.
- `src/ytdl_bot/i18n.py` + `locales/*.json`: localization runtime and dictionaries.
- `src/ytdl_bot/ux.py`: reactions and transient message utilities.

## Project structure

```text
.
├─ src/ytdl_bot/
│  ├─ bot.py
│  ├─ config.py
│  ├─ database.py
│  ├─ i18n.py
│  ├─ keyboards.py
│  ├─ logic.py
│  ├─ main.py
│  ├─ media.py
│  ├─ migrate.py
│  ├─ progress.py
│  ├─ ux.py
│  └─ youtube.py
├─ locales/
├─ tests/
├─ docs/operations.md
├─ Dockerfile
└─ railway.json
```

## Environment variables

Copy `.env.example` to `.env` and set values.

### Required

- `BOT_TOKEN`
- `BOT_TELEGRAM_ID`
- `ADMINS`
- `GROUP_CHAT_ID`
- `GITHUB_DEVELOPER_URL`
- `GITHUB_PROJECT_URL`

### Optional / tuning

- `DATABASE_URI` (default `sqlite:///./bot.db`)
- `STORAGE_PATH` (default `./data/downloads`)
- `MAX_DAILY_TRAFFIC_BYTES` (default `524288000`)
- `MAX_CONCURRENT_DOWNLOADS` (default `2`)
- `DOWNLOAD_TIMEOUT_SECONDS` (default `1800`)
- `FFMPEG_PATH` (default `ffmpeg`)
- `LOG_LEVEL` (default `INFO`)

## Setup and run

### 1) Local setup

1. Clone the repository.
2. Create and activate virtualenv.
3. Install dependencies.
4. Configure `.env`.
5. Run migration.
6. Start bot.

```bash
python -m venv .venv
. .venv/bin/activate  # Linux/macOS
# .venv\\Scripts\\activate  # Windows PowerShell

python -m pip install -e .[dev]
ytdl-bot-migrate
ytdl-bot
```

Alternative run commands:

```bash
python -m ytdl_bot.migrate
python -m ytdl_bot.main
```

### 2) Railway deployment

This project already includes Railway-ready config:

- `Dockerfile`
- `railway.json`

#### Steps

1. Push repository to GitHub.
2. Create a Railway project from this repository.
3. Add all required environment variables.
4. Deploy.

Container startup command:

```bash
ytdl-bot-migrate && ytdl-bot
```

#### Railway notes

- `ffmpeg` is installed in the image.
- Bot runs with long polling (no webhook needed).
- Use Worker/background style service.
- Use persistent volume only if you need durable local data; cache metadata is in DB and media files are transient.

## Core runtime flow

1. User sends YouTube URL.
2. Bot reacts (`👀`/`🤖`), sends transient `👾` and localized processing message.
3. Bot probes metadata/formats and shows thumbnail + quality keyboard.
4. Bot removes transient messages.
5. On quality click:
   - validates callback owner/admin
   - checks rolling quota (except admins)
   - checks hidden cache (`youtube_id:quality`)
   - serves from cache if present, otherwise downloads and uploads
6. After upload:
   - validates upload size
   - stores/updates cache entry
   - removes local downloaded file from full path and prunes empty folders
7. Status message is deleted from user chat after completion.
8. Final caption always ends with `@${BOT_TELEGRAM_ID}`.

## Admin controls

Admin panel button is visible only for IDs in `ADMINS`.

Available commands:

- `/admin_usage <user_id>`
- `/admin_reset_usage <user_id>`
- `/admin_set_group <group_chat_id>`
- `/admin_clear_group`
- `/admin_cache_add <youtube_id> <quality> <group_message_id> <file_id> <size_bytes> [group_chat_id]`
- `/admin_cache_remove <youtube_id> <quality>`
- `/admin_force_copy <youtube_id> <quality> <target_chat_id>`
- `/admin_add <user_id>`
- `/admin_remove <user_id>`

## Testing

```bash
python -m pytest -q
```

Coverage includes:

- cache hit serving
- quota enforcement
- admin log structure
- reaction and transient message lifecycle
- media cleanup helpers

## Operations

For cache inspection, cleanup, and group-cache troubleshooting see:

- [docs/operations.md](docs/operations.md)
