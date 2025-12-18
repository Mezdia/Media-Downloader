# YouTube & Instagram Downloader API Documentation

Designed by Mezd and powered by Mezdia.

Complete API reference for the YouTube & Instagram Downloader API.

## Web Interface

A modern, responsive web interface is available at the root URL (`/`) that provides access to all API endpoints through an intuitive UI. The interface supports:

- **Platform Switching**: Toggle between YouTube and Instagram features
- **Multi-language Support**: English and Persian (Farsi) languages
- **Visual & JSON Views**: Switch between user-friendly visual cards and raw JSON responses
- **Real-time Job Monitoring**: Track download progress and manage jobs
- **Batch Operations**: Download multiple videos simultaneously
- **Stream Support**: Direct video streaming capabilities

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
  "thumbnails": [
    {
      "url": "https://i.ytimg.com/vi/.../maxresdefault.jpg",
      "width": 1280,
      "height": 720
    }
  ],
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
      "id": "VIDEO_ID",
      "title": "Video 1",
      "description": "Description...",
      "duration": 180,
      "duration_string": "3:00",
      "view_count": 1000000,
      "upload_date": "20230101",
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
    }
  ],
  "has_more": true
}
```

---

### 15. Stream Video

#### GET /stream/video

Stream a YouTube video directly without saving to disk. Returns a redirect to the video stream URL that can be played in real-time.

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

## Instagram API

### Base URL

```
http://localhost:5000/instagram
```

### 16. Instagram API Info

#### GET /instagram/info

Get Instagram API information and capabilities.

**Response:**
```json
{
  "api": {
    "name": "Instagram Downloader & Info API",
    "version": "2.0.0",
    "base_url": "/instagram",
    "docs_url": "/docs"
  },
  "capabilities": {
    "supported_content_types": ["posts", "reels", "stories", "carousels"],
    "download_features": ["batch_downloads", "quality_selection", "audio_extraction", "zip_export"],
    "statistics": ["engagement_metrics", "view_counts"]
  },
  "limits": {
    "max_batch_size": 20,
    "file_retention_minutes": 30,
    "rate_limit_requests_per_minute": 30
  },
  "endpoints": [
    {"method": "GET", "path": "/instagram/post/info", "description": "Get post information"},
    {"method": "GET", "path": "/instagram/reel/info", "description": "Get reel information"},
    {"method": "GET", "path": "/instagram/story/info", "description": "Get stories information"},
    {"method": "GET", "path": "/instagram/profile/info", "description": "Get profile information"},
    {"method": "GET", "path": "/instagram/profile/posts", "description": "Get profile posts"},
    {"method": "POST", "path": "/instagram/download/post", "description": "Download a post"},
    {"method": "POST", "path": "/instagram/download/reel", "description": "Download a reel"},
    {"method": "POST", "path": "/instagram/download/story", "description": "Download stories"},
    {"method": "POST", "path": "/instagram/download/carousel", "description": "Download carousel as ZIP"},
    {"method": "POST", "path": "/instagram/download/batch", "description": "Batch download"},
    {"method": "GET", "path": "/instagram/status/{job_id}", "description": "Check download status"},
    {"method": "GET", "path": "/instagram/download/file/{filename}", "description": "Get downloaded file"},
    {"method": "GET", "path": "/instagram/post/stats", "description": "Get post statistics"},
    {"method": "GET", "path": "/instagram/reel/stats", "description": "Get reel statistics"}
  ]
}
```

### 17. Get Post Information

#### GET /instagram/post/info

Get detailed information about an Instagram post.

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| url | string | Yes | Instagram post URL or shortcode |

**Example Request:**
```bash
curl "http://localhost:5000/instagram/post/info?url=https://www.instagram.com/p/CnU4zIh9x_F/"
```

**Response:**
```json
{
  "success": true,
  "type": "image",
  "post_id": "CnU4zIh9x_F",
  "shortcode": "CnU4zIh9x_F",
  "caption": "Beautiful sunset 🌅",
  "owner": {
    "username": "instagram",
    "user_id": "25025320"
  },
  "timestamp": 1640000000,
  "upload_date": "20211220",
  "view_count": 123456,
  "like_count": 12345,
  "comment_count": 678,
  "duration": null,
  "thumbnail": "https://instagram.fhyd9-1.fna.fbcdn.net/...",
  "webpage_url": "https://www.instagram.com/p/CnU4zIh9x_F/",
  "is_carousel": false,
  "carousel_count": null,
  "media_items": null
}
```

### 18. Get Reel Information

#### GET /instagram/reel/info

Get detailed information about an Instagram reel.

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| url | string | Yes | Instagram reel URL or shortcode |

**Response:**
```json
{
  "success": true,
  "type": "reel",
  "reel_id": "CnU4zIh9x_F",
  "shortcode": "CnU4zIh9x_F",
  "caption": "Amazing reel!",
  "video_url": "https://instagram.fhyd9-1.fna.fbcdn.net/...",
  "thumbnail": "https://instagram.fhyd9-1.fna.fbcdn.net/...",
  "duration": 22.5,
  "width": 1080,
  "height": 1920,
  "fps": 30,
  "owner": {
    "username": "instagram",
    "user_id": "25025320"
  },
  "timestamp": 1640000000,
  "upload_date": "20211220",
  "view_count": 1234567,
  "like_count": 234567,
  "comment_count": 45678,
  "webpage_url": "https://www.instagram.com/reel/CnU4zIh9x_F/",
  "formats": [
    {
      "format_id": "123",
      "ext": "mp4",
      "resolution": "1080x1920",
      "filesize": 12345678
    }
  ]
}
```

### 19. Get Story Information

#### GET /instagram/story/info

Get information about active stories from an Instagram profile.

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| username | string | Yes | Instagram username |

**Response:**
```json
{
  "success": true,
  "type": "stories",
  "username": "instagram",
  "user_id": "25025320",
  "has_active_stories": true,
  "active_stories_count": 3,
  "stories": [
    {
      "story_id": "17912345678901234_25025320",
      "story_index": 1,
      "media_type": "image",
      "url": "https://instagram.fhyd9-1.fna.fbcdn.net/...",
      "thumbnail": "https://instagram.fhyd9-1.fna.fbcdn.net/...",
      "duration": null,
      "timestamp": 1640000000,
      "width": 1080,
      "height": 1920
    }
  ]
}
```

### 20. Get Profile Information

#### GET /instagram/profile/info

Get profile information for an Instagram account.

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| username | string | Yes | Instagram username |

**Response:**
```json
{
  "success": true,
  "type": "profile",
  "username": "instagram",
  "user_id": "25025320",
  "profile_url": "https://www.instagram.com/instagram/",
  "total_posts": 1234,
  "recent_posts": [
    {
      "id": "CnU4zIh9x_F",
      "title": "Post title",
      "url": "https://www.instagram.com/p/CnU4zIh9x_F/",
      "thumbnail": "https://instagram.fhyd9-1.fna.fbcdn.net/...",
      "duration": null
    }
  ],
  "recent_posts_count": 12
}
```

### 21. Get Profile Posts

#### GET /instagram/profile/posts

Get recent posts from an Instagram profile.

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| username | string | Yes | - | Instagram username |
| limit | integer | No | 12 | Number of posts to return (1-50) |

**Response:**
```json
{
  "success": true,
  "type": "profile_posts",
  "username": "instagram",
  "total_posts": 1234,
  "returned_count": 12,
  "limit": 12,
  "posts": [
    {
      "index": 0,
      "post_id": "CnU4zIh9x_F",
      "title": "Post title",
      "url": "https://www.instagram.com/p/CnU4zIh9x_F/",
      "thumbnail": "https://instagram.fhyd9-1.fna.fbcdn.net/...",
      "duration": null,
      "is_video": false
    }
  ]
}
```

### 22. Download Post

#### POST /instagram/download/post

Download an Instagram post.

**Request Body:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| url | string | Yes | - | Instagram post URL or shortcode |
| quality | string | No | "best" | Quality: best, medium, low |
| download_type | string | No | "media" | Type: media, video_only, image_only |
| include_metadata | boolean | No | true | Include metadata |

**Response:**
```json
{
  "job_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "status": "pending",
  "message": "Post download started. Use /instagram/status/{job_id} to check progress.",
  "status_url": "/instagram/status/a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d"
}
```

### 23. Download Reel

#### POST /instagram/download/reel

Download an Instagram reel.

**Request Body:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| url | string | Yes | - | Reel URL or shortcode |
| quality | string | No | "best" | Quality: best, 1080p, 720p, 480p |
| download_type | string | No | "video" | Type: video, audio_only |
| audio_format | string | No | "best" | Audio format: best, mp3, m4a |

**Response:**
```json
{
  "job_id": "b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d6e",
  "status": "pending",
  "message": "Reel download started. Use /instagram/status/{job_id} to check progress.",
  "status_url": "/instagram/status/b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d6e"
}
```

### 24. Download Stories

#### POST /instagram/download/story

Download Instagram stories.

**Request Body:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| username | string | Yes | - | Instagram username |
| quality | string | No | "best" | Quality: best, high, medium, low |
| format | string | No | "individual" | Format: individual, zip |

**Response:**
```json
{
  "job_id": "c3d4e5f6-a7b8-4c9d-0e1f-2a3b4c5d6e7f",
  "status": "pending",
  "message": "Story download started. Use /instagram/status/{job_id} to check progress.",
  "status_url": "/instagram/status/c3d4e5f6-a7b8-4c9d-0e1f-2a3b4c5d6e7f"
}
```

### 25. Download Carousel

#### POST /instagram/download/carousel

Download carousel as ZIP.

**Request Body:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| url | string | Yes | - | Carousel post URL |
| quality | string | No | "best" | Quality |
| include_metadata | boolean | No | true | Include metadata.json |

**Response:**
```json
{
  "job_id": "d4e5f6a7-b8c9-4d0e-1f2a-3b4c5d6e7f8a",
  "status": "pending",
  "message": "Carousel download started as ZIP. Use /instagram/status/{job_id} to check progress.",
  "status_url": "/instagram/status/d4e5f6a7-b8c9-4d0e-1f2a-3b4c5d6e7f8a"
}
```

### 26. Batch Download

#### POST /instagram/download/batch

Batch download Instagram content.

**Request Body:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| items | array | Yes | List of items |
| items[].url | string | Yes | URL or shortcode |
| items[].type | string | Yes | Type: post, reel, story |
| quality | string | No | Quality |
| continue_on_error | boolean | No | Continue if error |

**Response:**
```json
{
  "job_id": "e5f6a7b8-c9d0-4e1f-2a3b-4c5d6e7f8a9b",
  "status": "pending",
  "total_items": 2,
  "message": "Batch download started. Use /instagram/status/{job_id} to check progress.",
  "status_url": "/instagram/status/e5f6a7b8-c9d0-4e1f-2a3b-4c5d6e7f8a9b"
}
```

### 27. Check Download Status

#### GET /instagram/status/{job_id}

Check download status.

**Response (Completed):**
```json
{
  "job_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "status": "completed",
  "progress": 100,
  "type": "instagram_post",
  "files": [
    {
      "filename": "CnU4zIh9x_F_image.jpg",
      "size": 2621440,
      "size_mb": 2.5,
      "download_url": "/instagram/download/file/CnU4zIh9x_F_image.jpg",
      "media_type": "image"
    }
  ],
  "error": null,
  "created_at": "2025-01-15T12:00:00.000000"
}
```

### 28. Download File

#### GET /instagram/download/file/{filename}

Download a file.

### 29. Get Post Stats

#### GET /instagram/post/stats

Get post statistics.

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| url | string | Yes | Post URL or shortcode |

**Response:**
```json
{
  "success": true,
  "type": "post_statistics",
  "post_id": "CnU4zIh9x_F",
  "shortcode": "CnU4zIh9x_F",
  "owner_username": "instagram",
  "statistics": {
    "likes_count": 123456,
    "comments_count": 5678,
    "view_count": 234567,
    "total_engagement": 394502
  }
}
```

### 30. Get Reel Stats

#### GET /instagram/reel/stats

Get reel statistics.

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| url | string | Yes | Reel URL or shortcode |

**Response:**
```json
{
  "success": true,
  "type": "reel_statistics",
  "reel_id": "CnU4zIh9x_F",
  "shortcode": "CnU4zIh9x_F",
  "owner_username": "instagram",
  "duration_seconds": 22.5,
  "statistics": {
    "view_count": 1234567,
    "likes_count": 234567,
    "comments_count": 45678,
    "total_engagement": 315746
  }
}
```

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

---

## Legal Disclaimer

**⚠️ IMPORTANT:** This tool is for personal, educational use only. Downloading copyrighted content may violate YouTube/Instagram Terms of Service and copyright laws in your jurisdiction. Use responsibly and only for content you have rights to download.

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.0.0 | 2025-01-15 | Added Instagram support, improved error handling |

---

**Base API Endpoint:** `http://localhost:5000`

**API Documentation:** Visit `/docs` for interactive Swagger documentation
