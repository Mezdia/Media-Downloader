# YouTube Downloader API

## Overview
A production-ready FastAPI backend for downloading YouTube videos, audio, subtitles, and thumbnails powered by yt-dlp. Features background job processing, rate limiting, and a bilingual (English/Persian) testing UI.

## Project Structure
```
├── main.py                 # FastAPI application with all endpoints
├── static/
│   └── index.html          # Bilingual testing UI (EN/FA)
├── tmp/
│   └── downloads/          # Temporary download storage (auto-cleaned)
├── README_EN.md            # English documentation
├── README_FA.md            # Persian documentation
├── API_DOCS_EN.md          # English API reference
├── API_DOCS_FA.md          # Persian API reference
├── pyproject.toml          # Python dependencies
└── .gitignore              # Git ignore rules
```

## API Endpoints
- `GET /info` - Get video/playlist metadata
- `GET /formats` - List available download formats
- `POST /download/single` - Download single video/audio
- `GET /status/{job_id}` - Check download progress
- `GET /download/file/{filename}` - Retrieve downloaded file
- `GET /download/playlist/info` - Get playlist info
- `POST /download/playlist/all` - Download entire playlist
- `POST /download/playlist/select` - Download selected videos
- `GET /subtitles` - List available subtitles
- `POST /subtitles` - Download subtitles
- `GET /thumbnail` - Get video thumbnail

## Running the Application
The application runs on port 5000 with:
```bash
python main.py
```

Or using uvicorn:
```bash
uvicorn main:app --host 0.0.0.0 --port 5000 --reload
```

## Key Features
- Background download processing with job tracking
- Rate limiting (30 requests/minute per IP)
- Automatic file cleanup (30 minutes)
- MP3 audio conversion via ffmpeg
- Support for playlists with individual video selection
- Comprehensive error handling

## Dependencies
- FastAPI - Web framework
- yt-dlp - YouTube download engine
- uvicorn - ASGI server
- ffmpeg - Audio/video processing (system)
- aiofiles - Async file operations
- pydantic - Data validation

## User Preferences
- Bilingual support (English and Persian)
- Simple, clean UI for testing
- Separate documentation files for each language

## Recent Changes
- Initial project setup with complete API implementation
- Created bilingual testing UI with language switcher
- Added English and Persian documentation
- Implemented background job processing system
- Added rate limiting and file cleanup

## Legal Notice
This tool is for personal, educational use only. Users are responsible for compliance with copyright laws and YouTube's Terms of Service.
