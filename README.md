# YouTube & Instagram Downloader API

Designed by Mezd and powered by Mezdia.

A production-ready FastAPI backend for downloading YouTube videos and Instagram content (posts, reels, stories) powered by yt-dlp.

## Legal Disclaimer

**⚠️ IMPORTANT:** This tool is for personal, educational use only. Downloading copyrighted content may violate YouTube/Instagram Terms of Service and copyright laws in your jurisdiction. Use responsibly and only for content you have rights to download.

## Features

### YouTube Features
- **Video Information**: Get detailed metadata for any YouTube video or playlist
- **Format Listing**: View all available formats (video, audio, combined)
- **Video Download**: Download videos in various qualities (best, 720p, 1080p, 1440p, 4k)
- **Audio Download**: Extract audio in MP3, M4A, or best quality
- **Playlist Support**: Download entire playlists or select specific videos
- **Subtitles**: Get available subtitles in any language (manual and auto-generated)
- **Thumbnails**: Get video thumbnails in various qualities
- **Background Processing**: Long downloads run in background with progress tracking
- **Rate Limiting**: Built-in protection against API abuse
- **Bilingual UI**: Interactive testing interface in English and Persian

### Instagram Features
- **Post Information**: Get detailed metadata for Instagram posts (images, videos, carousels)
- **Reel Information**: Extract reel metadata, engagement stats, and available formats
- **Story Information**: Check active stories from Instagram profiles
- **Profile Information**: Get profile details and recent posts
- **Content Download**: Download posts, reels, stories, and carousels
- **Batch Downloads**: Download multiple Instagram items simultaneously
- **ZIP Export**: Download carousels and story collections as ZIP files
- **Statistics**: Get engagement metrics for posts and reels

## Requirements

- Python 3.11+
- ffmpeg (for audio conversion and video merging)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd youtube-downloader-api
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Ensure ffmpeg is installed:
```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Windows
# Download from https://ffmpeg.org/download.html
```

4. Run the server:
```bash
uvicorn main:app --host 0.0.0.0 --port 5000 --reload
```

## Quick Start

1. Open the testing UI at: `http://localhost:5000`
2. Or access the API documentation at: `http://localhost:5000/docs`

## API Endpoints

### YouTube Endpoints

#### GET /info
Get video or playlist information.

**Parameters:**
- `url` (required): YouTube video or playlist URL

**Example:**
```bash
curl "http://localhost:5000/info?url=https://www.youtube.com/watch?v=VIDEO_ID"
```

#### GET /formats
Get available formats for a video.

**Parameters:**
- `url` (required): YouTube video URL

**Example:**
```bash
curl "http://localhost:5000/formats?url=https://www.youtube.com/watch?v=VIDEO_ID"
```

#### POST /download/single
Download a single video or audio file.

**Body Parameters:**
- `url` (required): YouTube video URL
- `quality`: "best", "worst", "720p", "1080p", "1440p", "4k", "audio_only"
- `type`: "video", "audio"
- `audio_format`: "best", "mp3", "m4a"
- `format_id`: Specific format ID (overrides quality)

**Example:**
```bash
curl -X POST "http://localhost:5000/download/single" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=VIDEO_ID", "quality": "720p"}'
```

#### GET /status/{job_id}
Check download progress.

**Example:**
```bash
curl "http://localhost:5000/status/YOUR_JOB_ID"
```

#### GET /download/file/{filename}
Download processed file.

#### GET /download/playlist/info
Get playlist information.

**Parameters:**
- `url` (required): YouTube playlist URL

#### POST /download/playlist/all
Download all videos from a playlist.

#### POST /download/playlist/select
Download selected videos from a playlist.

**Body Parameters:**
- `url` (required): YouTube playlist URL
- `video_indices`: List of video indices to download
- `quality`, `type`, `audio_format`: Same as single download

#### GET /subtitles
Get available subtitles.

**Parameters:**
- `url` (required): YouTube video URL
- `lang`: Language code ("en", "fa", "all", etc.)

#### POST /subtitles
Download subtitles file.

**Body Parameters:**
- `url` (required): YouTube video URL
- `lang`: Language code
- `auto`: Include auto-generated subtitles (boolean)

#### GET /thumbnail
Get video thumbnail.

**Parameters:**
- `url` (required): YouTube video URL
- `quality`: "maxres", "hq", "mq", "sd", "default"

### Instagram Endpoints

#### GET /instagram/post/info
Get Instagram post information.

**Parameters:**
- `url` (required): Instagram post URL or shortcode

**Example:**
```bash
curl "http://localhost:5000/instagram/post/info?url=https://www.instagram.com/p/POST_CODE/"
```

#### GET /instagram/reel/info
Get Instagram reel information.

**Parameters:**
- `url` (required): Instagram reel URL or shortcode

#### GET /instagram/story/info
Get Instagram story information.

**Parameters:**
- `username` (required): Instagram username

#### GET /instagram/profile/info
Get Instagram profile information.

**Parameters:**
- `username` (required): Instagram username

#### GET /instagram/profile/posts
Get Instagram profile posts.

**Parameters:**
- `username` (required): Instagram username
- `limit`: Number of posts to return (1-50, default: 12)

#### POST /instagram/download/post
Download Instagram post.

**Body Parameters:**
- `url` (required): Instagram post URL or shortcode
- `quality`: "best", "medium", "low"
- `download_type`: "media", "video_only", "image_only"

#### POST /instagram/download/reel
Download Instagram reel.

**Body Parameters:**
- `url` (required): Instagram reel URL or shortcode
- `quality`: "best", "1080p", "720p", "480p"
- `download_type`: "video", "audio_only"
- `audio_format`: "best", "mp3", "m4a"

#### POST /instagram/download/story
Download Instagram stories.

**Body Parameters:**
- `username` (required): Instagram username
- `quality`: "best", "high", "medium", "low"
- `format`: "individual", "zip"

#### POST /instagram/download/carousel
Download Instagram carousel as ZIP.

**Body Parameters:**
- `url` (required): Instagram carousel post URL
- `quality`: "best", "high", "medium", "low"
- `include_metadata`: Include metadata.json in ZIP

#### POST /instagram/download/batch
Batch download Instagram content.

**Body Parameters:**
- `items`: List of items to download
- `items[].url`: URL or shortcode
- `items[].type`: "post", "reel", "story"
- `quality`: Quality preference
- `continue_on_error`: Continue if individual download fails

#### GET /instagram/status/{job_id}
Check Instagram download status.

#### GET /instagram/download/file/{filename}
Download Instagram file.

#### GET /instagram/post/stats
Get Instagram post statistics.

**Parameters:**
- `url` (required): Instagram post URL or shortcode

#### GET /instagram/reel/stats
Get Instagram reel statistics.

**Parameters:**
- `url` (required): Instagram reel URL or shortcode

## Configuration

Environment variables:
- `CLEANUP_TIMEOUT_MINUTES`: Time before downloaded files are deleted (default: 30)
- `MAX_REQUESTS_PER_MINUTE`: Rate limit per IP (default: 30)

## Error Handling

The API returns appropriate HTTP status codes:
- `200`: Success
- `400`: Bad request (invalid URL, etc.)
- `403`: Forbidden (private content, age-restricted)
- `404`: Not found (content unavailable)
- `429`: Rate limit exceeded
- `500`: Internal server error

## Testing UI

Access the interactive testing UI at the root URL (`/`). Features:
- Test all API endpoints
- Switch between English and Persian
- View JSON responses
- Download files directly

## Admin Panel System

This system includes a comprehensive admin panel with both web-based and Telegram-based interfaces for complete bot management.

### Web Admin Panel

Access the web-based admin panel at `/static/admin/index.html`. Features:

#### Dashboard
- **Real-time Statistics**: Live system metrics and user activity
- **Active Downloads**: Current download jobs and progress
- **Storage Usage**: Disk usage and cleanup status
- **System Uptime**: Server uptime and health monitoring
- **Recent Activity**: Live activity feed with download history

#### User Management
- **User List**: Complete user database with search and filtering
- **User Actions**: Ban, unban, promote, and demote users
- **User Statistics**: Download counts, activity, and status
- **Advanced Filtering**: Filter by admin status, banned users, active users
- **User Search**: Real-time search by username, name, or user ID

#### Variable Management
- **Dynamic Variables**: Create, edit, and delete system variables
- **Variable Descriptions**: Add descriptions for better documentation
- **Real-time Updates**: Variables update in real-time across the system
- **Variable History**: Track variable changes and updates

#### Broadcast Messaging
- **Message Broadcasting**: Send messages to all users simultaneously
- **Preview Mode**: Preview messages before sending
- **Rich Formatting**: Support for Markdown formatting
- **Delivery Tracking**: Track delivery success and error rates
- **Message History**: View all sent broadcasts with statistics

#### Analytics & Reporting
- **Download Analytics**: Detailed download statistics and trends
- **User Growth**: New user registration and activity tracking
- **Platform Statistics**: YouTube vs Instagram usage breakdown
- **Time-based Reports**: Generate reports for different time periods
- **Export Capabilities**: Export analytics data for external analysis

#### System Settings
- **Rate Limiting**: Configure API rate limits per user
- **File Management**: Set file retention times and size limits
- **Feature Toggles**: Enable/disable analytics and logging
- **Maintenance Mode**: Put the system in maintenance mode
- **Database Management**: Cleanup, backup, and reset database operations

### Telegram Admin Panel

Access the Telegram-based admin panel using bot commands:

#### Admin Commands
- `/admin` - Open the interactive admin dashboard
- `/stats` - Quick system statistics
- `/users` - List recent users
- `/broadcast <message>` - Send broadcast message
- `/ban <user_id>` - Ban a user
- `/unban <user_id>` - Unban a user
- `/promote <user_id>` - Promote user to admin
- `/demote <user_id>` - Demote admin to user
- `/variable <key> <value>` - Set system variable
- `/getvar <key>` - Get system variable value

#### Interactive Features
- **Inline Keyboards**: Interactive buttons for all admin functions
- **Real-time Updates**: Live statistics and notifications
- **User Search**: Search and manage users directly in Telegram
- **Quick Actions**: One-click user management actions
- **System Monitoring**: Real-time system health and activity

### Bot Features

#### Advanced Animations
- **Context-aware Reactions**: Smart emoji reactions based on content type
- **Progress Animations**: Animated progress indicators during downloads
- **Status Updates**: Live status updates with emojis and animations
- **Interactive Feedback**: Visual feedback for all user actions

#### Enhanced User Experience
- **Smart URL Detection**: Automatic platform detection and processing
- **Quality Selection**: Glass-style quality selection interface
- **Live Progress**: Real-time download and upload progress
- **Error Handling**: Comprehensive error messages with user guidance

#### Message Management
- **Message Editing**: Edit bot messages with updated information
- **Message Deletion**: Delete messages after completion
- **Reaction Management**: Add and remove reactions to messages
- **User Reactions**: React to user messages for better engagement

### API Integration

All admin functions are accessible via REST API endpoints:

#### Admin Endpoints
- `GET /admin/stats` - System statistics
- `GET /admin/users` - User list
- `POST /admin/users/{id}/ban` - Ban user
- `POST /admin/users/{id}/unban` - Unban user
- `POST /admin/users/{id}/promote` - Promote to admin
- `POST /admin/users/{id}/demote` - Demote from admin
- `GET /admin/variables` - Get variables
- `POST /admin/variables` - Create/update variable
- `DELETE /admin/variables/{key}` - Delete variable
- `POST /admin/broadcast` - Send broadcast
- `GET /admin/broadcast/history` - Broadcast history
- `GET /admin/analytics` - Analytics data
- `GET /admin/settings` - System settings
- `POST /admin/settings` - Update settings
- `GET /admin/activity/recent` - Recent activity
- `POST /admin/database/cleanup` - Database cleanup
- `GET /admin/database/backup` - Database backup
- `POST /admin/database/reset` - Database reset (dangerous)

### Security Features

- **Admin-only Access**: All admin functions require admin privileges
- **Role-based Permissions**: Different permission levels for different operations
- **Input Validation**: Comprehensive input validation and sanitization
- **Rate Limiting**: Protection against API abuse
- **Audit Logging**: Track all admin actions for security

### Modern UI/UX

#### Glass-morphism Design
- **Modern Aesthetics**: Glass-effect cards and components
- **Gradient Backgrounds**: Beautiful gradient backgrounds
- **Smooth Animations**: CSS animations and transitions
- **Responsive Design**: Works on desktop, tablet, and mobile

#### Interactive Elements
- **Real-time Updates**: Live data updates without page refresh
- **Search Functionality**: Instant search across all data
- **Filtering Options**: Advanced filtering and sorting
- **Export Features**: Export data in various formats

#### Accessibility
- **Keyboard Navigation**: Full keyboard support
- **Screen Reader Support**: ARIA labels and descriptions
- **High Contrast**: High contrast mode support
- **Multi-language**: Support for multiple languages

### Getting Started

1. **Web Admin Panel**: Open `/static/admin/index.html` in your browser
2. **Telegram Admin**: Start a chat with your bot and use `/admin`
3. **API Access**: Use the admin API endpoints for integration
4. **User Management**: Use the user management features to control access
5. **System Monitoring**: Monitor system health and performance
6. **Broadcasting**: Send messages to all users
7. **Analytics**: Track usage and performance metrics

### Best Practices

- **Regular Backups**: Use the database backup feature regularly
- **Monitor Usage**: Keep an eye on system statistics and usage
- **User Management**: Regularly review and manage user permissions
- **System Maintenance**: Use cleanup features to maintain optimal performance
- **Security**: Regularly review admin access and permissions
- **Analytics**: Use analytics to understand usage patterns and optimize performance

## File Cleanup

Downloaded files are automatically deleted after 30 minutes to save storage space.

## Rate Limiting

The API limits requests to 30 per minute per IP address to prevent abuse.

## License

MIT License - See LICENSE file for details.
