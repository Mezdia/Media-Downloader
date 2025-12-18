# YouTube Downloader API Documentation

Complete API reference for the YouTube Downloader API.

## Base URL

```
http://localhost:5000
```

## Authentication

No authentication required for local use.

## Rate Limiting

- 30 requests per minute per IP address
- Returns HTTP 429 when limit exceeded

---

## Endpoints

### 1. Health Check

#### GET /health

Check if the API is running.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-01-15T12:00:00.000000"
}
```

---

### 2. Video Information

#### GET /info

Get detailed metadata for a YouTube video or playlist.

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| url | string | Yes | YouTube video or playlist URL |

**Example Request:**
```bash
curl "http://localhost:5000/info?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

**Response (Video):**
```json
{
  "type": "video",
  "id": "dQw4w9WgXcQ",
  "title": "Video Title",
  "description": "Video description...",
  "duration": 212,
  "duration_string": "3:32",
  "view_count": 1234567890,
  "upload_date": "20091025",
  "channel": "Channel Name",
  "channel_id": "UC...",
  "channel_url": "https://www.youtube.com/channel/...",
  "channel_subscriber_count": 12345678,
  "thumbnail": "https://i.ytimg.com/vi/.../maxresdefault.jpg",
  "thumbnails": [...],
  "webpage_url": "https://www.youtube.com/watch?v=...",
  "is_live": false,
  "age_limit": 0
}
```

**Response (Playlist):**
```json
{
  "type": "playlist",
  "playlist_id": "PL...",
  "playlist_title": "Playlist Title",
  "playlist_count": 25,
  "uploader": "Channel Name",
  "videos": [
    {
      "id": "...",
      "title": "Video 1",
      "duration": 180,
      ...
    }
  ]
}
```

**Error Responses:**
- `400`: Invalid URL or extraction failed
- `403`: Private or age-restricted video
- `404`: Video not available
- `429`: Rate limit exceeded

---

### 3. Available Formats

#### GET /formats

Get all available download formats for a video.

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| url | string | Yes | YouTube video URL |

**Example Request:**
```bash
curl "http://localhost:5000/formats?url=https://www.youtube.com/watch?v=VIDEO_ID"
```

**Response:**
```json
{
  "video_id": "VIDEO_ID",
  "title": "Video Title",
  "formats": {
    "video_only": [
      {
        "format_id": "137",
        "ext": "mp4",
        "resolution": "1920x1080",
        "fps": 30,
        "vcodec": "avc1.640028",
        "acodec": "none",
        "filesize": 123456789,
        "format_note": "1080p"
      }
    ],
    "audio_only": [
      {
        "format_id": "140",
        "ext": "m4a",
        "resolution": "audio only",
        "acodec": "mp4a.40.2",
        "abr": 128
      }
    ],
    "combined": [
      {
        "format_id": "18",
        "ext": "mp4",
        "resolution": "640x360",
        "vcodec": "avc1.42001E",
        "acodec": "mp4a.40.2"
      }
    ]
  },
  "recommended": {
    "best_video": "bestvideo+bestaudio/best",
    "best_audio": "bestaudio/best",
    "720p": "bestvideo[height<=720]+bestaudio",
    "1080p": "bestvideo[height<=1080]+bestaudio"
  }
}
```

---

### 4. Single Video Download

#### POST /download/single

Start downloading a single video or audio file.

**Request Body:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| url | string | Yes | - | YouTube video URL |
| quality | string | No | "best" | Quality preset: "best", "worst", "720p", "1080p", "1440p", "4k", "audio_only" |
| format_id | string | No | null | Specific format ID (overrides quality) |
| type | string | No | "video" | Download type: "video", "audio" |
| audio_format | string | No | "best" | Audio format: "best", "mp3", "m4a" |

**Example Request:**
```bash
curl -X POST "http://localhost:5000/download/single" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.youtube.com/watch?v=VIDEO_ID",
    "quality": "720p",
    "type": "video"
  }'
```

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "message": "Download started. Use /status/{job_id} to check progress.",
  "status_url": "/status/550e8400-e29b-41d4-a716-446655440000"
}
```

---

### 5. Job Status

#### GET /status/{job_id}

Check the status of a download job.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| job_id | string | UUID of the download job |

**Example Request:**
```bash
curl "http://localhost:5000/status/550e8400-e29b-41d4-a716-446655440000"
```

**Response (In Progress):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "progress": 45,
  "files": [],
  "error": null,
  "title": "Video Title",
  "created_at": "2025-01-15T12:00:00.000000"
}
```

**Response (Completed):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "progress": 100,
  "files": [
    {
      "filename": "abc12345_Video Title.mp4",
      "path": "tmp/downloads/abc12345_Video Title.mp4",
      "size": 52428800,
      "download_url": "/download/file/abc12345_Video Title.mp4"
    }
  ],
  "error": null,
  "title": "Video Title",
  "created_at": "2025-01-15T12:00:00.000000"
}
```

**Status Values:**
- `pending`: Job created, waiting to start
- `processing`: Download in progress
- `completed`: Download finished successfully
- `failed`: Download failed (check `error` field)

---

### 6. File Download

#### GET /download/file/{filename}

Download a processed file.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| filename | string | Name of the file to download |

**Example Request:**
```bash
curl -O "http://localhost:5000/download/file/abc12345_Video%20Title.mp4"
```

**Note:** Files are automatically deleted after 30 minutes.

---

### 7. Playlist Information

#### GET /download/playlist/info

Get information about all videos in a playlist.

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| url | string | Yes | YouTube playlist URL |

**Example Request:**
```bash
curl "http://localhost:5000/download/playlist/info?url=https://www.youtube.com/playlist?list=PL..."
```

**Response:**
```json
{
  "playlist_id": "PL...",
  "playlist_title": "Playlist Title",
  "playlist_count": 25,
  "uploader": "Channel Name",
  "videos": [
    {
      "index": 0,
      "id": "VIDEO_ID",
      "title": "Video 1",
      "duration": 180,
      "url": "https://www.youtube.com/watch?v=VIDEO_ID",
      "thumbnail": "https://i.ytimg.com/vi/.../default.jpg"
    }
  ]
}
```

---

### 8. Download Entire Playlist

#### POST /download/playlist/all

Download all videos from a playlist.

**Request Body:** Same as `/download/single`

**Response:** Same format as `/download/single` (returns job_id)

---

### 9. Download Selected Videos

#### POST /download/playlist/select

Download specific videos from a playlist by index.

**Request Body:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| url | string | Yes | YouTube playlist URL |
| video_indices | array[int] | Yes | List of video indices to download |
| quality | string | No | Quality preset |
| type | string | No | Download type |
| audio_format | string | No | Audio format |

**Example Request:**
```bash
curl -X POST "http://localhost:5000/download/playlist/select" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.youtube.com/playlist?list=PL...",
    "video_indices": [0, 2, 5],
    "quality": "720p"
  }'
```

---

### 10. Subtitles

#### GET /subtitles

Get available subtitles for a video.

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| url | string | Yes | - | YouTube video URL |
| lang | string | No | "all" | Language code or "all" |

**Example Request:**
```bash
curl "http://localhost:5000/subtitles?url=https://www.youtube.com/watch?v=VIDEO_ID&lang=all"
```

**Response (lang="all"):**
```json
{
  "video_id": "VIDEO_ID",
  "title": "Video Title",
  "manual_subtitles": ["en", "es", "fr"],
  "auto_generated_subtitles": ["en", "fa", "de", "ja"],
  "subtitle_details": {
    "en": [{"ext": "vtt", "url": "..."}]
  },
  "auto_subtitle_details": {
    "en": [{"ext": "vtt", "url": "..."}]
  }
}
```

#### POST /subtitles

Download subtitles for a video.

**Request Body:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| url | string | Yes | - | YouTube video URL |
| lang | string | No | "en" | Language code |
| auto | boolean | No | false | Include auto-generated |

**Response:**
```json
{
  "video_id": "VIDEO_ID",
  "title": "Video Title",
  "language": "en",
  "filename": "abc12345_Video Title.en.vtt",
  "download_url": "/download/file/abc12345_Video Title.en.vtt"
}
```

---

### 11. Thumbnail

#### GET /thumbnail

Get video thumbnail URL.

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| url | string | Yes | - | YouTube video URL |
| quality | string | No | "maxres" | Quality: "maxres", "hq", "mq", "sd", "default" |

**Example Request:**
```bash
curl "http://localhost:5000/thumbnail?url=https://www.youtube.com/watch?v=VIDEO_ID&quality=hq"
```

**Response:**
```json
{
  "video_id": "VIDEO_ID",
  "title": "Video Title",
  "quality": "hq",
  "thumbnail_url": "https://img.youtube.com/vi/VIDEO_ID/hqdefault.jpg",
  "all_thumbnails": [
    {"quality": "0", "url": "..."},
    {"quality": "1", "url": "..."}
  ]
}
```

---

### 12. Batch Download

#### POST /download/batch

Download multiple YouTube videos/audios simultaneously. Returns a single job ID for tracking all downloads.

**Request Body:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| urls | array | Yes | - | List of YouTube URLs (max 10) |
| quality | string | No | "best" | Quality: best, worst, audio_only, 720p, 1080p, 1440p, 4k |
| type | string | No | "video" | Type: video, audio, both |
| audio_format | string | No | "best" | Audio format: mp3, m4a, best |

**Example Request:**
```bash
curl -X POST "http://localhost:5000/download/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "urls": [
      "https://www.youtube.com/watch?v=VIDEO_ID_1",
      "https://www.youtube.com/watch?v=VIDEO_ID_2"
    ],
    "quality": "1080p",
    "type": "video"
  }'
```

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "total_urls": 2,
  "message": "Batch download started. Use /status/{job_id} to check progress.",
  "status_url": "/status/550e8400-e29b-41d4-a716-446655440000"
}
```

**Error Responses:**
- `400`: Empty URL list or more than 10 URLs
- `429`: Rate limit exceeded
- `500`: Internal server error

---

### 13. Cancel Download Job

#### POST /jobs/{job_id}/cancel

Cancel a running or pending download job. Only jobs with status "pending" or "processing" can be cancelled.

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| job_id | string | Yes | The job ID to cancel |

**Example Request:**
```bash
curl -X POST "http://localhost:5000/jobs/550e8400-e29b-41d4-a716-446655440000/cancel"
```

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "cancelled",
  "message": "Download job has been cancelled",
  "cancelled_at": "2025-01-15T12:30:45.123456"
}
```

**Error Responses:**
- `404`: Job not found
- `400`: Job cannot be cancelled (already completed, failed, or cancelled)

---

### 14. List All Jobs

#### GET /jobs

List all download jobs with pagination and filtering. Returns summaries of jobs with their current status and progress.

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| skip | integer | No | 0 | Number of jobs to skip (pagination) |
| limit | integer | No | 10 | Number of jobs to return (1-100) |
| status | string | No | - | Filter by status: pending, processing, completed, failed, cancelled |
| type | string | No | - | Filter by type: video, playlist, batch |

**Example Request:**
```bash
curl "http://localhost:5000/jobs?skip=0&limit=10&status=completed"
```

**Response:**
```json
{
  "total": 25,
  "skip": 0,
  "limit": 10,
  "jobs": [
    {
      "job_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "completed",
      "type": "batch",
      "progress": 100,
      "created_at": "2025-01-15T12:00:00",
      "files_count": 2,
      "error_count": 0,
      "title": null,
      "total_urls": 2,
      "completed_count": 2
    },
    {
      "job_id": "660e8400-e29b-41d4-a716-446655440001",
      "status": "completed",
      "type": "video",
      "progress": 100,
      "created_at": "2025-01-15T11:55:00",
      "files_count": 1,
      "error_count": 0,
      "title": "Video Title",
      "total_urls": null,
      "completed_count": null
    }
  ],
  "has_more": true
}
```

---

### 15. Stream Video

#### GET /stream/video

Stream a YouTube video directly without saving to disk. Returns a redirect to the video stream URL that can be played in real-time by media players.

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| url | string | Yes | - | YouTube video URL |
| quality | string | No | "best" | Quality: best, worst, 720p, 1080p, 1440p, 4k |

**Example Request:**
```bash
curl "http://localhost:5000/stream/video?url=https://www.youtube.com/watch?v=VIDEO_ID&quality=720p"
```

**Response:**
- HTTP 307 Redirect with video stream URL
- Headers: `Cache-Control: no-cache, no-store, must-revalidate`
- Can be used directly in HTML5 video player or media player applications

**Example Usage:**
```html
<video width="640" height="480" controls>
  <source src="http://localhost:5000/stream/video?url=https://www.youtube.com/watch?v=VIDEO_ID" type="video/mp4">
  Your browser does not support the video tag.
</video>
```

**Error Responses:**
- `400`: Could not extract video information or no valid stream found
- `429`: Rate limit exceeded
- `500`: Internal server error

---

## Error Response Format

All errors follow this format:

```json
{
  "detail": "Error message description"
}
```

## Quality Presets

| Preset | Description |
|--------|-------------|
| best | Highest available quality |
| worst | Lowest available quality |
| 720p | Up to 720p resolution |
| 1080p | Up to 1080p resolution |
| 1440p | Up to 1440p (2K) resolution |
| 4k | Up to 2160p (4K) resolution |
| audio_only | Audio only, no video |

## Audio Formats

| Format | Description |
|--------|-------------|
| best | Best available audio format |
| mp3 | Convert to MP3 (requires ffmpeg) |
| m4a | Convert to M4A (requires ffmpeg) |
