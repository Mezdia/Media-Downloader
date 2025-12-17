# مستندات API دانلودر یوتیوب

مرجع کامل API برای دانلودر یوتیوب.

## آدرس پایه

```
http://localhost:5000
```

## احراز هویت

برای استفاده محلی نیازی به احراز هویت نیست.

## محدودیت نرخ

- 30 درخواست در دقیقه برای هر آدرس IP
- در صورت تجاوز از محدودیت، کد HTTP 429 برگردانده می‌شود

---

## نقاط پایانی

### 1. بررسی سلامت

#### GET /health

بررسی اینکه آیا API در حال اجراست.

**پاسخ:**
```json
{
  "status": "healthy",
  "timestamp": "2025-01-15T12:00:00.000000"
}
```

---

### 2. اطلاعات ویدیو

#### GET /info

دریافت متادیتای کامل برای یک ویدیو یا لیست پخش یوتیوب.

**پارامترهای کوئری:**

| پارامتر | نوع | الزامی | توضیحات |
|---------|-----|--------|---------|
| url | string | بله | آدرس ویدیو یا لیست پخش یوتیوب |

**درخواست نمونه:**
```bash
curl "http://localhost:5000/info?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

**پاسخ (ویدیو):**
```json
{
  "type": "video",
  "id": "dQw4w9WgXcQ",
  "title": "عنوان ویدیو",
  "description": "توضیحات ویدیو...",
  "duration": 212,
  "duration_string": "3:32",
  "view_count": 1234567890,
  "upload_date": "20091025",
  "channel": "نام کانال",
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

**پاسخ (لیست پخش):**
```json
{
  "type": "playlist",
  "playlist_id": "PL...",
  "playlist_title": "عنوان لیست پخش",
  "playlist_count": 25,
  "uploader": "نام کانال",
  "videos": [
    {
      "id": "...",
      "title": "ویدیو 1",
      "duration": 180,
      ...
    }
  ]
}
```

**پاسخ‌های خطا:**
- `400`: آدرس نامعتبر یا استخراج ناموفق
- `403`: ویدیو خصوصی یا دارای محدودیت سنی
- `404`: ویدیو در دسترس نیست
- `429`: تجاوز از محدودیت نرخ

---

### 3. فرمت‌های موجود

#### GET /formats

دریافت تمام فرمت‌های دانلود موجود برای یک ویدیو.

**پارامترهای کوئری:**

| پارامتر | نوع | الزامی | توضیحات |
|---------|-----|--------|---------|
| url | string | بله | آدرس ویدیو یوتیوب |

**درخواست نمونه:**
```bash
curl "http://localhost:5000/formats?url=https://www.youtube.com/watch?v=VIDEO_ID"
```

**پاسخ:**
```json
{
  "video_id": "VIDEO_ID",
  "title": "عنوان ویدیو",
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
        "resolution": "فقط صدا",
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

### 4. دانلود ویدیو تکی

#### POST /download/single

شروع دانلود یک ویدیو یا فایل صوتی.

**بدنه درخواست:**

| پارامتر | نوع | الزامی | پیش‌فرض | توضیحات |
|---------|-----|--------|---------|---------|
| url | string | بله | - | آدرس ویدیو یوتیوب |
| quality | string | خیر | "best" | پیش‌تنظیم کیفیت: "best"، "worst"، "720p"، "1080p"، "1440p"، "4k"، "audio_only" |
| format_id | string | خیر | null | شناسه فرمت خاص (اولویت بر quality) |
| type | string | خیر | "video" | نوع دانلود: "video"، "audio" |
| audio_format | string | خیر | "best" | فرمت صدا: "best"، "mp3"، "m4a" |

**درخواست نمونه:**
```bash
curl -X POST "http://localhost:5000/download/single" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.youtube.com/watch?v=VIDEO_ID",
    "quality": "720p",
    "type": "video"
  }'
```

**پاسخ:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "message": "دانلود شروع شد. برای بررسی پیشرفت از /status/{job_id} استفاده کنید.",
  "status_url": "/status/550e8400-e29b-41d4-a716-446655440000"
}
```

---

### 5. وضعیت کار

#### GET /status/{job_id}

بررسی وضعیت یک کار دانلود.

**پارامترهای مسیر:**

| پارامتر | نوع | توضیحات |
|---------|-----|---------|
| job_id | string | شناسه یکتای کار دانلود |

**درخواست نمونه:**
```bash
curl "http://localhost:5000/status/550e8400-e29b-41d4-a716-446655440000"
```

**پاسخ (در حال پردازش):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "progress": 45,
  "files": [],
  "error": null,
  "title": "عنوان ویدیو",
  "created_at": "2025-01-15T12:00:00.000000"
}
```

**پاسخ (تکمیل شده):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "progress": 100,
  "files": [
    {
      "filename": "abc12345_عنوان ویدیو.mp4",
      "path": "tmp/downloads/abc12345_عنوان ویدیو.mp4",
      "size": 52428800,
      "download_url": "/download/file/abc12345_عنوان ویدیو.mp4"
    }
  ],
  "error": null,
  "title": "عنوان ویدیو",
  "created_at": "2025-01-15T12:00:00.000000"
}
```

**مقادیر وضعیت:**
- `pending`: کار ایجاد شده، در انتظار شروع
- `processing`: دانلود در حال انجام
- `completed`: دانلود با موفقیت تمام شد
- `failed`: دانلود ناموفق (فیلد `error` را بررسی کنید)

---

### 6. دانلود فایل

#### GET /download/file/{filename}

دانلود یک فایل پردازش شده.

**پارامترهای مسیر:**

| پارامتر | نوع | توضیحات |
|---------|-----|---------|
| filename | string | نام فایل برای دانلود |

**درخواست نمونه:**
```bash
curl -O "http://localhost:5000/download/file/abc12345_عنوان%20ویدیو.mp4"
```

**توجه:** فایل‌ها پس از 30 دقیقه به طور خودکار حذف می‌شوند.

---

### 7. اطلاعات لیست پخش

#### GET /download/playlist/info

دریافت اطلاعات تمام ویدیوهای یک لیست پخش.

**پارامترهای کوئری:**

| پارامتر | نوع | الزامی | توضیحات |
|---------|-----|--------|---------|
| url | string | بله | آدرس لیست پخش یوتیوب |

**درخواست نمونه:**
```bash
curl "http://localhost:5000/download/playlist/info?url=https://www.youtube.com/playlist?list=PL..."
```

**پاسخ:**
```json
{
  "playlist_id": "PL...",
  "playlist_title": "عنوان لیست پخش",
  "playlist_count": 25,
  "uploader": "نام کانال",
  "videos": [
    {
      "index": 0,
      "id": "VIDEO_ID",
      "title": "ویدیو 1",
      "duration": 180,
      "url": "https://www.youtube.com/watch?v=VIDEO_ID",
      "thumbnail": "https://i.ytimg.com/vi/.../default.jpg"
    }
  ]
}
```

---

### 8. دانلود کل لیست پخش

#### POST /download/playlist/all

دانلود تمام ویدیوهای یک لیست پخش.

**بدنه درخواست:** مشابه `/download/single`

**پاسخ:** فرمت مشابه `/download/single` (شامل job_id)

---

### 9. دانلود ویدیوهای انتخابی

#### POST /download/playlist/select

دانلود ویدیوهای خاص از یک لیست پخش بر اساس اندیس.

**بدنه درخواست:**

| پارامتر | نوع | الزامی | توضیحات |
|---------|-----|--------|---------|
| url | string | بله | آدرس لیست پخش یوتیوب |
| video_indices | array[int] | بله | لیست اندیس ویدیوها برای دانلود |
| quality | string | خیر | پیش‌تنظیم کیفیت |
| type | string | خیر | نوع دانلود |
| audio_format | string | خیر | فرمت صدا |

**درخواست نمونه:**
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

### 10. زیرنویس

#### GET /subtitles

دریافت زیرنویس‌های موجود برای یک ویدیو.

**پارامترهای کوئری:**

| پارامتر | نوع | الزامی | پیش‌فرض | توضیحات |
|---------|-----|--------|---------|---------|
| url | string | بله | - | آدرس ویدیو یوتیوب |
| lang | string | خیر | "all" | کد زبان یا "all" |

**درخواست نمونه:**
```bash
curl "http://localhost:5000/subtitles?url=https://www.youtube.com/watch?v=VIDEO_ID&lang=all"
```

**پاسخ (lang="all"):**
```json
{
  "video_id": "VIDEO_ID",
  "title": "عنوان ویدیو",
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

دانلود زیرنویس برای یک ویدیو.

**بدنه درخواست:**

| پارامتر | نوع | الزامی | پیش‌فرض | توضیحات |
|---------|-----|--------|---------|---------|
| url | string | بله | - | آدرس ویدیو یوتیوب |
| lang | string | خیر | "en" | کد زبان |
| auto | boolean | خیر | false | شامل زیرنویس‌های خودکار |

**پاسخ:**
```json
{
  "video_id": "VIDEO_ID",
  "title": "عنوان ویدیو",
  "language": "en",
  "filename": "abc12345_عنوان ویدیو.en.vtt",
  "download_url": "/download/file/abc12345_عنوان ویدیو.en.vtt"
}
```

---

### 11. تصویر بندانگشتی

#### GET /thumbnail

دریافت آدرس تصویر بندانگشتی ویدیو.

**پارامترهای کوئری:**

| پارامتر | نوع | الزامی | پیش‌فرض | توضیحات |
|---------|-----|--------|---------|---------|
| url | string | بله | - | آدرس ویدیو یوتیوب |
| quality | string | خیر | "maxres" | کیفیت: "maxres"، "hq"، "mq"، "sd"، "default" |

**درخواست نمونه:**
```bash
curl "http://localhost:5000/thumbnail?url=https://www.youtube.com/watch?v=VIDEO_ID&quality=hq"
```

**پاسخ:**
```json
{
  "video_id": "VIDEO_ID",
  "title": "عنوان ویدیو",
  "quality": "hq",
  "thumbnail_url": "https://img.youtube.com/vi/VIDEO_ID/hqdefault.jpg",
  "all_thumbnails": [
    {"quality": "0", "url": "..."},
    {"quality": "1", "url": "..."}
  ]
}
```

---

## فرمت پاسخ خطا

تمام خطاها از این فرمت پیروی می‌کنند:

```json
{
  "detail": "توضیح پیام خطا"
}
```

## پیش‌تنظیمات کیفیت

| پیش‌تنظیم | توضیحات |
|-----------|---------|
| best | بالاترین کیفیت موجود |
| worst | پایین‌ترین کیفیت موجود |
| 720p | حداکثر رزولوشن 720p |
| 1080p | حداکثر رزولوشن 1080p |
| 1440p | حداکثر رزولوشن 1440p (2K) |
| 4k | حداکثر رزولوشن 2160p (4K) |
| audio_only | فقط صدا، بدون ویدیو |

## فرمت‌های صدا

| فرمت | توضیحات |
|------|---------|
| best | بهترین فرمت صدای موجود |
| mp3 | تبدیل به MP3 (نیاز به ffmpeg) |
| m4a | تبدیل به M4A (نیاز به ffmpeg) |
