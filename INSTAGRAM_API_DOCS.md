# Instagram Downloader & Info API Documentation

Complete API reference for the Instagram content extraction and download module.

## Base URL

```
http://localhost:5000/instagram
```

## Authentication

No authentication required for public content access.

## Rate Limiting

- 30 requests per minute per IP address
- Returns HTTP 429 when limit exceeded

## Content Availability

All endpoints operate on publicly available Instagram content only. Private accounts and age-restricted content will return appropriate error responses.

---

## Profile & User Information

### 1. Get Profile Information

#### GET /instagram/profile/info

Retrieve detailed information about an Instagram profile/account.

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| username | string | Yes | Instagram username (without @) |

**Example Request:**
```bash
curl "http://localhost:5000/instagram/profile/info?username=instagram"
```

**Response (Success - 200):**
```json
{
  "type": "profile",
  "user_id": "25025320",
  "username": "instagram",
  "display_name": "Instagram",
  "bio": "Bringing you closer to the people and things you love.",
  "bio_links": [
    {
      "url": "https://example.com",
      "link_title": "Official Website"
    }
  ],
  "profile_picture_url": "https://instagram.fhyd9-1.fna.fbcdn.net/...",
  "profile_picture_urls": {
    "standard": "https://instagram.fhyd9-1.fna.fbcdn.net/.../s150x150/",
    "high_resolution": "https://instagram.fhyd9-1.fna.fbcdn.net/.../s320x320/",
    "full_size": "https://instagram.fhyd9-1.fna.fbcdn.net/.../"
  },
  "followers_count": 123456789,
  "following_count": 42,
  "total_posts": 5678,
  "total_reels": 234,
  "total_stories": 12,
  "is_verified": true,
  "is_private": false,
  "is_business_account": true,
  "is_professional": true,
  "category": "App",
  "contact_email": "contact@instagram.com",
  "phone_number": null,
  "website_url": "https://www.instagram.com",
  "profile_url": "https://www.instagram.com/instagram/",
  "edge_timeline_to_media": {
    "count": 5678
  }
}
```

**Error Responses:**

| Status | Error Code | Description |
|--------|-----------|-------------|
| 400 | INVALID_USERNAME | Username is invalid or empty |
| 403 | ACCOUNT_PRIVATE | This is a private account and content is not publicly accessible |
| 404 | PROFILE_NOT_FOUND | The requested profile does not exist |
| 429 | RATE_LIMIT | Rate limit exceeded. Please try again later |
| 500 | SERVER_ERROR | Internal server error |

---

### 2. List Profile Posts

#### GET /instagram/profile/posts

Get a list of recent posts from an Instagram profile with pagination support.

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| username | string | Yes | - | Instagram username |
| limit | integer | No | 12 | Number of posts to return (1-50) |
| cursor | string | No | null | Pagination cursor from previous response |

**Example Request:**
```bash
curl "http://localhost:5000/instagram/profile/posts?username=instagram&limit=12"
```

**Response (Success - 200):**
```json
{
  "type": "profile_posts",
  "username": "instagram",
  "total_posts_count": 5678,
  "posts": [
    {
      "post_id": "CnU4zIh9x_F",
      "shortcode": "CnU4zIh9x_F",
      "post_type": "image",
      "caption": "Post caption text...",
      "image_url": "https://instagram.fhyd9-1.fna.fbcdn.net/.../s1080x1080/",
      "image_urls": [
        "https://instagram.fhyd9-1.fna.fbcdn.net/.../s1080x1080/",
        "https://instagram.fhyd9-1.fna.fbcdn.net/.../s1080x1080/"
      ],
      "timestamp": 1640000000,
      "datetime": "2021-12-20T12:00:00Z",
      "like_count": 123456,
      "comment_count": 5678,
      "view_count": 234567,
      "engagement_rate": 0.042,
      "location": {
        "id": "123456789",
        "name": "New York, New York"
      },
      "hashtags": ["#instagram", "#follow", "#like"],
      "mentions": ["@someone", "@another"],
      "carousel_count": null,
      "is_carousel": false,
      "is_video": false,
      "video_duration": null,
      "has_audio": false
    },
    {
      "post_id": "CnT4zIh8y_E",
      "shortcode": "CnT4zIh8y_E",
      "post_type": "carousel",
      "caption": "Carousel post with multiple items...",
      "thumbnail_url": "https://instagram.fhyd9-1.fna.fbcdn.net/.../s1080x1080/",
      "carousel_count": 3,
      "items": [
        {
          "type": "image",
          "url": "https://instagram.fhyd9-1.fna.fbcdn.net/.../s1080x1080/"
        },
        {
          "type": "video",
          "url": "https://instagram.fhyd9-1.fna.fbcdn.net/.../video.mp4",
          "duration": 15.5
        },
        {
          "type": "image",
          "url": "https://instagram.fhyd9-1.fna.fbcdn.net/.../s1080x1080/"
        }
      ],
      "timestamp": 1639900000,
      "like_count": 98765,
      "comment_count": 4321,
      "view_count": 150000,
      "engagement_rate": 0.038
    }
  ],
  "page_info": {
    "has_next_page": true,
    "end_cursor": "QVFIUm9wYWJBSlhpVWJxN0NaNQ==",
    "start_cursor": "QVFIUm9wYWJBSlhiVWJxN0NaNQ=="
  }
}
```

**Error Responses:**

| Status | Error Code | Description |
|--------|-----------|-------------|
| 400 | INVALID_LIMIT | Limit parameter out of range (1-50) |
| 403 | ACCOUNT_PRIVATE | This account is private |
| 404 | PROFILE_NOT_FOUND | Profile not found |
| 429 | RATE_LIMIT | Rate limit exceeded |
| 500 | SERVER_ERROR | Internal server error |

---

### 3. List Profile Reels

#### GET /instagram/profile/reels

Get reels from an Instagram profile with pagination.

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| username | string | Yes | - | Instagram username |
| limit | integer | No | 12 | Number of reels to return (1-50) |
| cursor | string | No | null | Pagination cursor |

**Example Request:**
```bash
curl "http://localhost:5000/instagram/profile/reels?username=instagram&limit=12"
```

**Response (Success - 200):**
```json
{
  "type": "profile_reels",
  "username": "instagram",
  "total_reels_count": 234,
  "reels": [
    {
      "reel_id": "CnU4zIh9x_F",
      "shortcode": "CnU4zIh9x_F",
      "caption": "Reel caption text...",
      "video_url": "https://instagram.fhyd9-1.fna.fbcdn.net/.../video.mp4",
      "thumbnail_url": "https://instagram.fhyd9-1.fna.fbcdn.net/.../s1080x1080/",
      "duration": 15.5,
      "timestamp": 1640000000,
      "datetime": "2021-12-20T12:00:00Z",
      "view_count": 1234567,
      "like_count": 123456,
      "comment_count": 5678,
      "share_count": 1234,
      "save_count": 567,
      "engagement_rate": 0.085,
      "audio": {
        "title": "Original Audio Title",
        "artist": "Artist Name",
        "audio_id": "17912345678901234",
        "audio_url": "https://instagram.fhyd9-1.fna.fbcdn.net/.../audio.mp3"
      },
      "music_used": true,
      "hashtags": ["#reels", "#trending"],
      "mentions": ["@collaborator"],
      "has_effects": true
    },
    {
      "reel_id": "CnT4zIh8y_E",
      "shortcode": "CnT4zIh8y_E",
      "caption": "Another reel...",
      "video_url": "https://instagram.fhyd9-1.fna.fbcdn.net/.../video.mp4",
      "thumbnail_url": "https://instagram.fhyd9-1.fna.fbcdn.net/.../s1080x1080/",
      "duration": 22.3,
      "timestamp": 1639900000,
      "view_count": 987654,
      "like_count": 98765,
      "comment_count": 4321
    }
  ],
  "page_info": {
    "has_next_page": true,
    "end_cursor": "QVFIUm9wYWJBSlhpVWJxN0NaNQ==",
    "start_cursor": "QVFIUm9wYWJBSlhiVWJxN0NaNQ=="
  }
}
```

**Error Responses:**

| Status | Error Code | Description |
|--------|-----------|-------------|
| 400 | INVALID_LIMIT | Limit parameter out of range |
| 403 | ACCOUNT_PRIVATE | This account is private |
| 404 | PROFILE_NOT_FOUND | Profile not found |
| 429 | RATE_LIMIT | Rate limit exceeded |
| 500 | SERVER_ERROR | Internal server error |

---

## Content Information

### 4. Get Post Information

#### GET /instagram/post/info

Get detailed information about a specific Instagram post.

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| url_or_code | string | Yes | Post URL (full or shortcode) or post code |

**Example Requests:**
```bash
# Using full URL
curl "http://localhost:5000/instagram/post/info?url_or_code=https://www.instagram.com/p/CnU4zIh9x_F/"

# Using shortcode
curl "http://localhost:5000/instagram/post/info?url_or_code=CnU4zIh9x_F"
```

**Response (Success - 200, Image Post):**
```json
{
  "type": "post",
  "post_id": "CnU4zIh9x_F",
  "shortcode": "CnU4zIh9x_F",
  "content_type": "image",
  "caption": "Beautiful sunset 🌅 #nature #photography",
  "caption_html": "Beautiful sunset <img alt=\"🌅\"> #nature #photography",
  "image_url": "https://instagram.fhyd9-1.fna.fbcdn.net/.../s1080x1080/",
  "image_urls": {
    "thumbnail": "https://instagram.fhyd9-1.fna.fbcdn.net/.../s150x150/",
    "medium": "https://instagram.fhyd9-1.fna.fbcdn.net/.../s640x640/",
    "high_resolution": "https://instagram.fhyd9-1.fna.fbcdn.net/.../s1080x1080/",
    "original": "https://instagram.fhyd9-1.fna.fbcdn.net/.../"
  },
  "video_url": null,
  "video_duration": null,
  "owner": {
    "user_id": "25025320",
    "username": "instagram",
    "display_name": "Instagram",
    "profile_picture_url": "https://instagram.fhyd9-1.fna.fbcdn.net/.../s150x150/",
    "is_verified": true,
    "is_private": false
  },
  "taken_at_timestamp": 1640000000,
  "datetime": "2021-12-20T12:00:00Z",
  "location": {
    "id": "123456789",
    "name": "Santa Monica Beach",
    "lat": 34.0195,
    "lng": -118.4912
  },
  "edge_media_to_caption": {
    "edges": [
      {
        "node": {
          "text": "Beautiful sunset 🌅 #nature #photography"
        }
      }
    ]
  },
  "edge_media_to_comment": {
    "count": 5678
  },
  "edge_liked_by": {
    "count": 123456
  },
  "edge_media_to_hoisted_comments": {
    "count": 0
  },
  "comments_disabled": false,
  "taken_at": 1640000000,
  "media_preview": "data:image/jpeg;base64,...",
  "display_url": "https://instagram.fhyd9-1.fna.fbcdn.net/.../s1080x1080/",
  "accessibility_caption": "Photo by instagram on 12/20/21 at 12:00 PM UTC",
  "is_video": false,
  "has_audio": false,
  "play_count": null,
  "hashtags": [
    {
      "name": "nature",
      "count": 123456789
    },
    {
      "name": "photography",
      "count": 456789012
    }
  ],
  "mentions": [
    {
      "username": "photographer",
      "user_id": "123456789"
    }
  ],
  "tagged_users": []
}
```

**Response (Success - 200, Carousel Post):**
```json
{
  "type": "post",
  "post_id": "CnT4zIh8y_E",
  "shortcode": "CnT4zIh8y_E",
  "content_type": "carousel",
  "caption": "Carousel adventure! 🎞️",
  "carousel_media": [
    {
      "id": "item_1",
      "type": "image",
      "image_url": "https://instagram.fhyd9-1.fna.fbcdn.net/.../s1080x1080/",
      "image_urls": {
        "thumbnail": "https://instagram.fhyd9-1.fna.fbcdn.net/.../s150x150/",
        "medium": "https://instagram.fhyd9-1.fna.fbcdn.net/.../s640x640/",
        "high_resolution": "https://instagram.fhyd9-1.fna.fbcdn.net/.../s1080x1080/"
      }
    },
    {
      "id": "item_2",
      "type": "video",
      "video_url": "https://instagram.fhyd9-1.fna.fbcdn.net/.../video.mp4",
      "thumbnail_url": "https://instagram.fhyd9-1.fna.fbcdn.net/.../s1080x1080/",
      "duration": 15.5,
      "has_audio": true,
      "audio_url": "https://instagram.fhyd9-1.fna.fbcdn.net/.../audio.m4a"
    },
    {
      "id": "item_3",
      "type": "image",
      "image_url": "https://instagram.fhyd9-1.fna.fbcdn.net/.../s1080x1080/"
    }
  ],
  "carousel_count": 3,
  "owner": {
    "user_id": "25025320",
    "username": "instagram",
    "display_name": "Instagram"
  },
  "taken_at_timestamp": 1639900000,
  "datetime": "2021-12-19T12:00:00Z",
  "edge_media_to_comment": {
    "count": 4321
  },
  "edge_liked_by": {
    "count": 98765
  }
}
```

**Error Responses:**

| Status | Error Code | Description |
|--------|-----------|-------------|
| 400 | INVALID_URL | URL format is invalid |
| 403 | POST_PRIVATE | Post is private or from a private account |
| 403 | POST_DELETED | Post has been deleted |
| 404 | POST_NOT_FOUND | The requested post does not exist |
| 429 | RATE_LIMIT | Rate limit exceeded |
| 500 | SERVER_ERROR | Internal server error |

---

### 5. Get Reel Information

#### GET /instagram/reel/info

Get detailed information about a specific Reel.

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| url_or_id | string | Yes | Reel URL, shortcode, or reel ID |

**Example Request:**
```bash
curl "http://localhost:5000/instagram/reel/info?url_or_id=https://www.instagram.com/reel/CnU4zIh9x_F/"
```

**Response (Success - 200):**
```json
{
  "type": "reel",
  "reel_id": "CnU4zIh9x_F",
  "shortcode": "CnU4zIh9x_F",
  "caption": "Check out this amazing reel! 🎬",
  "video_url": "https://instagram.fhyd9-1.fna.fbcdn.net/.../video.mp4",
  "video_urls": {
    "low_quality": "https://instagram.fhyd9-1.fna.fbcdn.net/.../v/low.mp4",
    "medium_quality": "https://instagram.fhyd9-1.fna.fbcdn.net/.../v/medium.mp4",
    "high_quality": "https://instagram.fhyd9-1.fna.fbcdn.net/.../video.mp4"
  },
  "thumbnail_url": "https://instagram.fhyd9-1.fna.fbcdn.net/.../s1080x1080/",
  "duration": 22.5,
  "width": 1080,
  "height": 1920,
  "aspect_ratio": 0.5625,
  "video_codec": "h264",
  "audio_codec": "aac",
  "bitrate": 2500000,
  "fps": 30,
  "has_audio": true,
  "audio_url": "https://instagram.fhyd9-1.fna.fbcdn.net/.../audio.m4a",
  "audio": {
    "title": "Trending Sound",
    "artist": "Sound Creator",
    "audio_id": "17912345678901234",
    "audio_url": "https://instagram.fhyd9-1.fna.fbcdn.net/.../audio.mp3",
    "is_original_audio": false
  },
  "owner": {
    "user_id": "25025320",
    "username": "instagram",
    "display_name": "Instagram",
    "profile_picture_url": "https://instagram.fhyd9-1.fna.fbcdn.net/.../s150x150/",
    "is_verified": true
  },
  "taken_at_timestamp": 1640000000,
  "datetime": "2021-12-20T12:00:00Z",
  "view_count": 1234567,
  "like_count": 234567,
  "comment_count": 45678,
  "share_count": 12345,
  "save_count": 23456,
  "engagement_rate": 0.182,
  "play_count": 1234567,
  "avg_watch_time_percent": 72.5,
  "location": {
    "id": "123456789",
    "name": "Los Angeles, California"
  },
  "hashtags": [
    {
      "name": "reels",
      "count": 123456789
    },
    {
      "name": "trending",
      "count": 98765432
    }
  ],
  "comments_disabled": false,
  "allow_comments_from": "everyone",
  "music_info": {
    "music_title": "Trending Sound",
    "music_artist": "Artist Name",
    "music_clip_duration": 15,
    "music_start_time": 7
  }
}
```

**Error Responses:**

| Status | Error Code | Description |
|--------|-----------|-------------|
| 400 | INVALID_URL | URL format is invalid |
| 403 | REEL_PRIVATE | Reel is from a private account |
| 404 | REEL_NOT_FOUND | Reel does not exist |
| 429 | RATE_LIMIT | Rate limit exceeded |
| 500 | SERVER_ERROR | Internal server error |

---

### 6. Get Story Information

#### GET /instagram/story/info

Get information about Instagram stories (active stories from a user).

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| username | string | Yes | Instagram username |

**Example Request:**
```bash
curl "http://localhost:5000/instagram/story/info?username=instagram"
```

**Response (Success - 200):**
```json
{
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
      "image_url": "https://instagram.fhyd9-1.fna.fbcdn.net/.../s1080x1920/",
      "video_url": null,
      "video_duration": null,
      "thumbnail_url": "https://instagram.fhyd9-1.fna.fbcdn.net/.../s150x150/",
      "taken_at_timestamp": 1640000000,
      "datetime": "2021-12-20T12:00:00Z",
      "expires_at_timestamp": 1640086400,
      "time_until_expiry_seconds": 86400,
      "view_count": 12345,
      "viewer_ids": [],
      "has_viewers": true,
      "has_interactive_elements": false,
      "accessibility_caption": null
    },
    {
      "story_id": "17912345678901235_25025320",
      "story_index": 2,
      "media_type": "video",
      "image_url": null,
      "video_url": "https://instagram.fhyd9-1.fna.fbcdn.net/.../story.mp4",
      "video_urls": {
        "low_quality": "https://instagram.fhyd9-1.fna.fbcdn.net/.../low.mp4",
        "high_quality": "https://instagram.fhyd9-1.fna.fbcdn.net/.../story.mp4"
      },
      "video_duration": 8.5,
      "thumbnail_url": "https://instagram.fhyd9-1.fna.fbcdn.net/.../s150x150/",
      "taken_at_timestamp": 1639999000,
      "datetime": "2021-12-20T11:50:00Z",
      "expires_at_timestamp": 1640085400,
      "time_until_expiry_seconds": 85400,
      "view_count": 5678,
      "has_interactive_elements": true,
      "interactive_elements": [
        {
          "type": "poll",
          "content": "Do you like this?"
        }
      ]
    },
    {
      "story_id": "17912345678901236_25025320",
      "story_index": 3,
      "media_type": "image",
      "image_url": "https://instagram.fhyd9-1.fna.fbcdn.net/.../s1080x1920/",
      "taken_at_timestamp": 1639998000,
      "view_count": 2345
    }
  ]
}
```

**Response (No Active Stories - 200):**
```json
{
  "type": "stories",
  "username": "instagram",
  "user_id": "25025320",
  "has_active_stories": false,
  "active_stories_count": 0,
  "stories": []
}
```

**Error Responses:**

| Status | Error Code | Description |
|--------|-----------|-------------|
| 403 | ACCOUNT_PRIVATE | This is a private account |
| 403 | STORIES_DISABLED | Stories are disabled or hidden |
| 404 | PROFILE_NOT_FOUND | Profile not found |
| 429 | RATE_LIMIT | Rate limit exceeded |
| 500 | SERVER_ERROR | Internal server error |

---

## Download Operations

### 7. Download Post

#### POST /instagram/download/post

Start a background job to download an Instagram post (image, video, or carousel).

**Request Body (JSON):**

```json
{
  "url": "https://www.instagram.com/p/CnU4zIh9x_F/",
  "quality": "best",
  "download_type": "media",
  "include_metadata": true
}
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| url | string | Yes | - | Instagram post URL or shortcode |
| quality | string | No | "best" | Quality preference: best, medium, low |
| download_type | string | No | "media" | Type: media, video_only, image_only |
| include_metadata | boolean | No | true | Include post metadata in response |

**Example Request:**
```bash
curl -X POST "http://localhost:5000/instagram/download/post" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.instagram.com/p/CnU4zIh9x_F/",
    "quality": "best",
    "download_type": "media"
  }'
```

**Response (Success - 202):**
```json
{
  "job_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "status": "pending",
  "message": "Download started. Use /status/{job_id} to check progress.",
  "status_url": "/instagram/status/a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "post_info": {
    "post_id": "CnU4zIh9x_F",
    "content_type": "image",
    "caption": "Beautiful sunset 🌅"
  }
}
```

**Error Responses:**

| Status | Error Code | Description |
|--------|-----------|-------------|
| 400 | INVALID_URL | Post URL is invalid |
| 400 | INVALID_QUALITY | Quality parameter is invalid |
| 403 | POST_PRIVATE | Post is private and cannot be downloaded |
| 404 | POST_NOT_FOUND | Post not found |
| 429 | RATE_LIMIT | Rate limit exceeded |
| 500 | SERVER_ERROR | Internal server error |

---

### 8. Download Reel

#### POST /instagram/download/reel

Start a background job to download an Instagram Reel with audio/video options.

**Request Body (JSON):**

```json
{
  "url": "https://www.instagram.com/reel/CnU4zIh9x_F/",
  "quality": "best",
  "download_type": "video",
  "audio_format": "best"
}
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| url | string | Yes | - | Reel URL, shortcode, or ID |
| quality | string | No | "best" | Quality: best, 1080p, 720p, 480p, 360p |
| download_type | string | No | "video" | Type: video, audio_only, video_only |
| audio_format | string | No | "best" | Audio format: best, mp3, m4a, aac |
| include_metadata | boolean | No | true | Include reel metadata |

**Example Request:**
```bash
curl -X POST "http://localhost:5000/instagram/download/reel" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.instagram.com/reel/CnU4zIh9x_F/",
    "quality": "best",
    "download_type": "video"
  }'
```

**Response (Success - 202):**
```json
{
  "job_id": "b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d6e",
  "status": "pending",
  "message": "Reel download started.",
  "status_url": "/instagram/status/b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d6e",
  "reel_info": {
    "reel_id": "CnU4zIh9x_F",
    "duration": 22.5,
    "owner": "instagram"
  }
}
```

**Error Responses:**

| Status | Error Code | Description |
|--------|-----------|-------------|
| 400 | INVALID_URL | Reel URL is invalid |
| 400 | INVALID_QUALITY | Quality parameter invalid |
| 403 | REEL_PRIVATE | Reel is from a private account |
| 404 | REEL_NOT_FOUND | Reel not found |
| 429 | RATE_LIMIT | Rate limit exceeded |
| 500 | SERVER_ERROR | Internal server error |

---

### 9. Download Story

#### POST /instagram/download/story

Start a background job to download Instagram stories.

**Request Body (JSON):**

```json
{
  "username": "instagram",
  "quality": "best",
  "format": "individual"
}
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| username | string | Yes | - | Instagram username |
| quality | string | No | "best" | Quality: best, high, medium, low |
| format | string | No | "individual" | Format: individual, zip |
| include_expired | boolean | No | false | Include expired stories |

**Example Request:**
```bash
curl -X POST "http://localhost:5000/instagram/download/story" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "instagram",
    "quality": "best",
    "format": "individual"
  }'
```

**Response (Success - 202):**
```json
{
  "job_id": "c3d4e5f6-a7b8-4c9d-0e1f-2a3b4c5d6e7f",
  "status": "pending",
  "message": "Story download started.",
  "status_url": "/instagram/status/c3d4e5f6-a7b8-4c9d-0e1f-2a3b4c5d6e7f",
  "story_info": {
    "username": "instagram",
    "active_stories_count": 3,
    "format": "individual"
  }
}
```

**Error Responses:**

| Status | Error Code | Description |
|--------|-----------|-------------|
| 403 | ACCOUNT_PRIVATE | This account is private |
| 403 | STORIES_UNAVAILABLE | Stories are not available |
| 404 | PROFILE_NOT_FOUND | Profile not found |
| 429 | RATE_LIMIT | Rate limit exceeded |
| 500 | SERVER_ERROR | Internal server error |

---

### 10. Download Carousel as ZIP

#### POST /instagram/download/carousel

Download a carousel post with all media items as a ZIP file.

**Request Body (JSON):**

```json
{
  "url": "https://www.instagram.com/p/CnU4zIh8y_E/",
  "quality": "best",
  "include_metadata": true
}
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| url | string | Yes | - | Carousel post URL |
| quality | string | No | "best" | Quality: best, high, medium, low |
| include_metadata | boolean | No | true | Include metadata.json |

**Example Request:**
```bash
curl -X POST "http://localhost:5000/instagram/download/carousel" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.instagram.com/p/CnU4zIh8y_E/",
    "quality": "best"
  }'
```

**Response (Success - 202):**
```json
{
  "job_id": "d4e5f6a7-b8c9-4d0e-1f2a-3b4c5d6e7f8a",
  "status": "pending",
  "message": "Carousel download started as ZIP.",
  "status_url": "/instagram/status/d4e5f6a7-b8c9-4d0e-1f2a-3b4c5d6e7f8a",
  "carousel_info": {
    "post_id": "CnU4zIh8y_E",
    "item_count": 3,
    "output_format": "zip"
  }
}
```

**Error Responses:**

| Status | Error Code | Description |
|--------|-----------|-------------|
| 400 | INVALID_URL | URL is not a carousel post |
| 403 | POST_PRIVATE | Post is private |
| 404 | POST_NOT_FOUND | Post not found |
| 429 | RATE_LIMIT | Rate limit exceeded |
| 500 | SERVER_ERROR | Internal server error |

---

### 11. Batch Download

#### POST /instagram/download/batch

Start batch downloads for multiple posts/reels.

**Request Body (JSON):**

```json
{
  "items": [
    {
      "url": "https://www.instagram.com/p/CnU4zIh9x_F/",
      "type": "post"
    },
    {
      "url": "https://www.instagram.com/reel/CnU4zIh8y_E/",
      "type": "reel"
    }
  ],
  "quality": "best",
  "continue_on_error": true
}
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| items | array | Yes | List of items to download |
| items[].url | string | Yes | URL or shortcode |
| items[].type | string | Yes | Type: post, reel, story |
| quality | string | No | Quality preference |
| continue_on_error | boolean | No | Continue if individual download fails |

**Example Request:**
```bash
curl -X POST "http://localhost:5000/instagram/download/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "items": [
      {
        "url": "https://www.instagram.com/p/CnU4zIh9x_F/",
        "type": "post"
      },
      {
        "url": "https://www.instagram.com/reel/CnU4zIh8y_E/",
        "type": "reel"
      }
    ],
    "quality": "best"
  }'
```

**Response (Success - 202):**
```json
{
  "batch_job_id": "e5f6a7b8-c9d0-4e1f-2a3b-4c5d6e7f8a9b",
  "status": "pending",
  "message": "Batch download started.",
  "batch_size": 2,
  "items": [
    {
      "job_id": "job_1",
      "url": "https://www.instagram.com/p/CnU4zIh9x_F/",
      "type": "post",
      "status": "pending"
    },
    {
      "job_id": "job_2",
      "url": "https://www.instagram.com/reel/CnU4zIh8y_E/",
      "type": "reel",
      "status": "pending"
    }
  ],
  "status_url": "/instagram/status/e5f6a7b8-c9d0-4e1f-2a3b-4c5d6e7f8a9b"
}
```

**Error Responses:**

| Status | Error Code | Description |
|--------|-----------|-------------|
| 400 | INVALID_REQUEST | Invalid batch request format |
| 400 | EMPTY_BATCH | No items in batch |
| 429 | RATE_LIMIT | Rate limit exceeded |
| 500 | SERVER_ERROR | Internal server error |

---

## Job Management

### 12. Check Download Status

#### GET /instagram/status/{job_id}

Check the progress and status of a download job.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| job_id | string | Job ID returned from download endpoint |

**Example Request:**
```bash
curl "http://localhost:5000/instagram/status/a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d"
```

**Response (Success - Processing - 200):**
```json
{
  "job_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "status": "processing",
  "progress": 65,
  "progress_details": {
    "current": 65,
    "total": 100,
    "stage": "downloading"
  },
  "created_at": "2021-12-20T12:00:00Z",
  "started_at": "2021-12-20T12:00:05Z",
  "estimated_completion_seconds": 35,
  "speed_mbps": 2.5,
  "file_size_mb": null,
  "message": "Downloading media files..."
}
```

**Response (Success - Completed - 200):**
```json
{
  "job_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "status": "completed",
  "progress": 100,
  "created_at": "2021-12-20T12:00:00Z",
  "started_at": "2021-12-20T12:00:05Z",
  "completed_at": "2021-12-20T12:01:15Z",
  "duration_seconds": 70,
  "files": [
    {
      "filename": "CnU4zIh9x_F_image.jpg",
      "size_mb": 2.5,
      "download_url": "/instagram/download/file/CnU4zIh9x_F_image.jpg",
      "media_type": "image/jpeg",
      "dimensions": "1080x1350"
    }
  ],
  "file_count": 1,
  "total_size_mb": 2.5,
  "message": "Download completed successfully.",
  "expires_in_seconds": 1799
}
```

**Response (Error - 200):**
```json
{
  "job_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "status": "failed",
  "progress": 0,
  "error": {
    "code": "POST_PRIVATE",
    "message": "Post is private and cannot be downloaded",
    "details": "The post belongs to a private account"
  },
  "created_at": "2021-12-20T12:00:00Z",
  "started_at": "2021-12-20T12:00:05Z",
  "failed_at": "2021-12-20T12:00:10Z"
}
```

**Error Responses:**

| Status | Error Code | Description |
|--------|-----------|-------------|
| 404 | JOB_NOT_FOUND | Job ID not found or expired |
| 429 | RATE_LIMIT | Rate limit exceeded |
| 500 | SERVER_ERROR | Internal server error |

---

## File Download

### 13. Get Downloaded File

#### GET /instagram/download/file/{filename}

Download a completed media file from a finished download job.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| filename | string | Filename returned from status endpoint |

**Example Request:**
```bash
curl "http://localhost:5000/instagram/download/file/CnU4zIh9x_F_image.jpg" \
  -o downloaded_image.jpg
```

**Response (Success - 200):**
```
[Binary file content]
```

**Response Headers:**
```
Content-Type: image/jpeg (or appropriate media type)
Content-Length: 2621440
Content-Disposition: attachment; filename="CnU4zIh9x_F_image.jpg"
Cache-Control: no-cache
```

**Error Responses:**

| Status | Error Code | Description |
|--------|-----------|-------------|
| 404 | FILE_NOT_FOUND | File not found or expired |
| 410 | FILE_EXPIRED | File has been deleted (expired after 30 minutes) |
| 429 | RATE_LIMIT | Rate limit exceeded |
| 500 | SERVER_ERROR | Internal server error |

---

## Statistics & Metrics

### 14. Get Post Statistics

#### GET /instagram/post/stats

Get engagement statistics for a post.

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| url_or_code | string | Yes | Post URL or shortcode |

**Example Request:**
```bash
curl "http://localhost:5000/instagram/post/stats?url_or_code=CnU4zIh9x_F"
```

**Response (Success - 200):**
```json
{
  "type": "post_statistics",
  "post_id": "CnU4zIh9x_F",
  "shortcode": "CnU4zIh9x_F",
  "owner_username": "instagram",
  "timestamp": 1640000000,
  "statistics": {
    "likes_count": 123456,
    "comments_count": 5678,
    "saves_count": 23456,
    "shares_count": 12345,
    "view_count": 234567,
    "total_engagement": 394502,
    "engagement_rate": 0.042,
    "engagement_rate_percent": 4.2
  },
  "engagement_breakdown": {
    "likes_percent": 31.3,
    "comments_percent": 1.4,
    "saves_percent": 5.9,
    "shares_percent": 3.1,
    "views_percent": 59.5
  },
  "trending": {
    "is_trending": true,
    "trend_score": 8.5,
    "engagement_velocity": 1234,
    "engagement_velocity_24h": 5678
  }
}
```

**Error Responses:**

| Status | Error Code | Description |
|--------|-----------|-------------|
| 400 | INVALID_URL | URL format invalid |
| 403 | POST_PRIVATE | Post is private |
| 404 | POST_NOT_FOUND | Post not found |
| 429 | RATE_LIMIT | Rate limit exceeded |
| 500 | SERVER_ERROR | Internal server error |

---

### 15. Get Reel Statistics

#### GET /instagram/reel/stats

Get engagement statistics for a Reel.

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| url_or_id | string | Yes | Reel URL, shortcode, or ID |

**Example Request:**
```bash
curl "http://localhost:5000/instagram/reel/stats?url_or_id=CnU4zIh9x_F"
```

**Response (Success - 200):**
```json
{
  "type": "reel_statistics",
  "reel_id": "CnU4zIh9x_F",
  "shortcode": "CnU4zIh9x_F",
  "owner_username": "instagram",
  "duration": 22.5,
  "timestamp": 1640000000,
  "statistics": {
    "views": 1234567,
    "likes": 234567,
    "comments": 45678,
    "shares": 12345,
    "saves": 23456,
    "total_engagement": 315746,
    "engagement_rate": 0.182,
    "engagement_rate_percent": 18.2,
    "average_watch_time_seconds": 16.2,
    "average_watch_percent": 72.0,
    "completion_rate": 72.0
  },
  "engagement_breakdown": {
    "views_percent": 79.1,
    "likes_percent": 7.5,
    "comments_percent": 1.5,
    "shares_percent": 0.4,
    "saves_percent": 0.7
  },
  "viral_metrics": {
    "is_viral": true,
    "viral_score": 9.2,
    "view_velocity_per_hour": 45678,
    "engagement_velocity_per_hour": 8234
  }
}
```

**Error Responses:**

| Status | Error Code | Description |
|--------|-----------|-------------|
| 400 | INVALID_URL | URL format invalid |
| 403 | REEL_PRIVATE | Reel from private account |
| 404 | REEL_NOT_FOUND | Reel not found |
| 429 | RATE_LIMIT | Rate limit exceeded |
| 500 | SERVER_ERROR | Internal server error |

---

## Utility Endpoints

### 16. Get Available Download Formats

#### GET /instagram/formats

Get available quality and format options for downloads.

**Example Request:**
```bash
curl "http://localhost:5000/instagram/formats"
```

**Response (Success - 200):**
```json
{
  "type": "available_formats",
  "post_formats": {
    "image": {
      "qualities": [
        {
          "name": "best",
          "resolution": "1080x1350",
          "description": "Original resolution"
        },
        {
          "name": "high",
          "resolution": "640x800",
          "description": "High quality"
        },
        {
          "name": "medium",
          "resolution": "480x600",
          "description": "Medium quality"
        },
        {
          "name": "low",
          "resolution": "320x400",
          "description": "Low quality (preview)"
        }
      ]
    },
    "video": {
      "qualities": [
        {
          "name": "best",
          "height": "1080p",
          "bitrate": "8000k",
          "fps": 30,
          "description": "Best quality (Full HD)"
        },
        {
          "name": "720p",
          "height": "720p",
          "bitrate": "3500k",
          "fps": 30,
          "description": "HD quality"
        },
        {
          "name": "480p",
          "height": "480p",
          "bitrate": "1500k",
          "fps": 30,
          "description": "Mobile friendly"
        },
        {
          "name": "360p",
          "height": "360p",
          "bitrate": "800k",
          "fps": 24,
          "description": "Low bandwidth"
        }
      ]
    }
  },
  "reel_formats": {
    "video": {
      "qualities": [
        {
          "name": "best",
          "height": "1080p",
          "fps": 30,
          "bitrate": "6000k",
          "description": "Best quality"
        },
        {
          "name": "1080p",
          "height": "1080p",
          "fps": 30,
          "bitrate": "6000k"
        },
        {
          "name": "720p",
          "height": "720p",
          "fps": 30,
          "bitrate": "3500k"
        },
        {
          "name": "480p",
          "height": "480p",
          "fps": 24,
          "bitrate": "1500k"
        }
      ]
    },
    "audio_formats": [
      {
        "format": "best",
        "codec": "aac",
        "bitrate": "128k",
        "description": "Best available"
      },
      {
        "format": "mp3",
        "codec": "mp3",
        "bitrate": "192k",
        "description": "MP3 format"
      },
      {
        "format": "m4a",
        "codec": "aac",
        "bitrate": "128k",
        "description": "M4A format"
      },
      {
        "format": "aac",
        "codec": "aac",
        "bitrate": "128k",
        "description": "AAC format"
      }
    ]
  },
  "story_formats": {
    "qualities": [
      {
        "name": "best",
        "resolution": "1080x1920",
        "description": "Original resolution"
      },
      {
        "name": "high",
        "resolution": "720x1280",
        "description": "High quality"
      },
      {
        "name": "medium",
        "resolution": "540x960",
        "description": "Medium quality"
      }
    ]
  },
  "supported_output_formats": {
    "image": ["jpg", "png", "webp"],
    "video": ["mp4", "mkv", "mov"],
    "audio": ["mp3", "m4a", "aac", "wav"]
  }
}
```

---

### 17. API Info

#### GET /instagram/info

Get general API information and capabilities.

**Example Request:**
```bash
curl "http://localhost:5000/instagram/info"
```

**Response (Success - 200):**
```json
{
  "api": {
    "name": "Instagram Downloader & Info API",
    "version": "1.0.0",
    "base_url": "/instagram",
    "documentation_url": "/docs"
  },
  "capabilities": {
    "supported_content_types": [
      "posts",
      "reels",
      "stories",
      "carousel",
      "profile_info"
    ],
    "download_features": [
      "batch_downloads",
      "quality_selection",
      "format_conversion",
      "audio_extraction",
      "metadata_inclusion",
      "zip_export"
    ],
    "statistics": [
      "engagement_metrics",
      "view_counts",
      "viral_detection"
    ]
  },
  "limits": {
    "max_batch_size": 50,
    "max_concurrent_downloads": 10,
    "file_retention_minutes": 30,
    "rate_limit_requests_per_minute": 30,
    "max_file_size_mb": 500,
    "max_carousel_items": 10
  },
  "requirements": {
    "content_must_be_public": true,
    "account_authentication": false,
    "requires_api_key": false
  }
}
```

---

## Error Handling

All error responses follow a consistent format:

**Standard Error Response:**
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": "Additional context or suggestions",
    "timestamp": "2021-12-20T12:00:00Z",
    "request_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d"
  }
}
```

### Common Error Codes

| Code | HTTP Status | Description | Solution |
|------|-------------|-------------|----------|
| INVALID_URL | 400 | URL format is invalid | Check URL format and try again |
| INVALID_PARAMETER | 400 | Query or body parameter is invalid | Review parameter documentation |
| RATE_LIMIT | 429 | Rate limit exceeded (30 req/min) | Wait before making more requests |
| ACCOUNT_PRIVATE | 403 | Account is private | Only public accounts are supported |
| POST_PRIVATE | 403 | Post is from a private account | Post must be from public account |
| POST_DELETED | 403 | Post has been deleted | Content is no longer available |
| POST_NOT_FOUND | 404 | Post does not exist | Verify URL or shortcode |
| PROFILE_NOT_FOUND | 404 | Profile does not exist | Verify username |
| REEL_NOT_FOUND | 404 | Reel does not exist | Verify URL or reel ID |
| JOB_NOT_FOUND | 404 | Download job expired or invalid | Job expires after 30 minutes |
| FILE_EXPIRED | 410 | File has been deleted | Files are retained for 30 minutes |
| SERVER_ERROR | 500 | Internal server error | Retry after a moment |

---

## Usage Examples

### Complete Download Workflow Example

```bash
# 1. Get post information
curl "http://localhost:5000/instagram/post/info?url_or_code=CnU4zIh9x_F"

# 2. Start download
RESPONSE=$(curl -X POST "http://localhost:5000/instagram/download/post" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.instagram.com/p/CnU4zIh9x_F/",
    "quality": "best"
  }')

# Extract job_id
JOB_ID=$(echo $RESPONSE | grep -o '"job_id":"[^"]*' | cut -d'"' -f4)

# 3. Check status (poll until complete)
curl "http://localhost:5000/instagram/status/$JOB_ID"

# 4. Download file when ready
curl "http://localhost:5000/instagram/download/file/CnU4zIh9x_F_image.jpg" \
  -o saved_image.jpg
```

### Batch Download Workflow Example

```bash
# 1. Start batch download
BATCH_RESPONSE=$(curl -X POST "http://localhost:5000/instagram/download/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "items": [
      {"url": "https://www.instagram.com/p/CnU4zIh9x_F/", "type": "post"},
      {"url": "https://www.instagram.com/reel/CnU4zIh8y_E/", "type": "reel"}
    ],
    "quality": "best"
  }')

# 2. Monitor batch progress
BATCH_JOB_ID=$(echo $BATCH_RESPONSE | grep -o '"batch_job_id":"[^"]*' | cut -d'"' -f4)
curl "http://localhost:5000/instagram/status/$BATCH_JOB_ID"

# 3. Retrieve individual files as they complete
```

---

## Legal Notice

This API is designed for downloading and analyzing **publicly available** Instagram content only. Users are responsible for:

- Respecting Instagram's Terms of Service
- Complying with applicable copyright laws
- Respecting intellectual property rights
- Using downloaded content ethically and legally
- Not using this tool for unauthorized access or circumvention

Downloading private content or content without proper authorization is prohibited.

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2021-12-20 | Initial release with full Instagram support |

---

## Support & Contact

For issues or questions regarding the API, refer to the main project documentation or contact the development team.

**Base API Endpoint:** `http://localhost:5000/instagram`

**API Documentation:** Visit `/docs` for interactive Swagger documentation
