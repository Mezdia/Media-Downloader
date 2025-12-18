"""
YouTube & Instagram Downloader API - Production-Ready FastAPI Backend
Powered by yt-dlp for video/audio extraction and downloading from YouTube & Instagram.

LEGAL DISCLAIMER:
This tool is for personal, educational use only. Downloading copyrighted content
may violate YouTube/Instagram Terms of Service and copyright laws in your jurisdiction.
Use responsibly and only for content you have rights to download.
"""

import os
import re
import uuid
import asyncio
import time
import shutil
import zipfile
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Union
from pathlib import Path
from collections import defaultdict
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks, Request, APIRouter
from fastapi.responses import FileResponse, StreamingResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
import yt_dlp
import aiofiles


DOWNLOAD_DIR = Path("tmp/downloads")
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

INSTAGRAM_DOWNLOAD_DIR = Path("tmp/instagram")
INSTAGRAM_DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

CLEANUP_TIMEOUT_MINUTES = 30
MAX_REQUESTS_PER_MINUTE = 30

app = FastAPI(
    title="YouTube & Instagram Downloader API",
    description="A production-ready API for downloading YouTube videos and Instagram content (posts, reels, stories).",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

instagram_router = APIRouter(prefix="/instagram", tags=["Instagram"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

jobs: Dict[str, Dict[str, Any]] = {}
rate_limit_store: Dict[str, List[float]] = defaultdict(list)


class DownloadRequest(BaseModel):
    url: str
    quality: Optional[str] = Field(default="best", description="Quality: best, worst, audio_only, 720p, 1080p, 1440p, 4k")
    format_id: Optional[str] = Field(default=None, description="Specific format ID (overrides quality)")
    type: Optional[str] = Field(default="video", description="Type: video, audio, both")
    audio_format: Optional[str] = Field(default="best", description="Audio format: mp3, m4a, best")


class PlaylistSelectRequest(BaseModel):
    url: str
    video_indices: List[int]
    quality: Optional[str] = "best"
    type: Optional[str] = "video"
    audio_format: Optional[str] = "best"


class SubtitleRequest(BaseModel):
    url: str
    lang: Optional[str] = "en"
    auto: Optional[bool] = False


class BatchDownloadRequest(BaseModel):
    urls: List[str] = Field(..., description="List of YouTube URLs to download")
    quality: Optional[str] = Field(default="best", description="Quality: best, worst, audio_only, 720p, 1080p, 1440p, 4k")
    type: Optional[str] = Field(default="video", description="Type: video, audio, both")
    audio_format: Optional[str] = Field(default="best", description="Audio format: mp3, m4a, best")


class InstagramPostDownloadRequest(BaseModel):
    url: str = Field(..., description="Instagram post URL or shortcode")
    quality: Optional[str] = Field(default="best", description="Quality: best, medium, low")
    download_type: Optional[str] = Field(default="media", description="Type: media, video_only, image_only")
    include_metadata: Optional[bool] = Field(default=True, description="Include post metadata")


class InstagramReelDownloadRequest(BaseModel):
    url: str = Field(..., description="Instagram reel URL or shortcode")
    quality: Optional[str] = Field(default="best", description="Quality: best, 1080p, 720p, 480p")
    download_type: Optional[str] = Field(default="video", description="Type: video, audio_only, video_only")
    audio_format: Optional[str] = Field(default="best", description="Audio format: best, mp3, m4a")
    include_metadata: Optional[bool] = Field(default=True, description="Include reel metadata")


class InstagramStoryDownloadRequest(BaseModel):
    username: str = Field(..., description="Instagram username")
    quality: Optional[str] = Field(default="best", description="Quality: best, high, medium, low")
    format: Optional[str] = Field(default="individual", description="Format: individual, zip")


class InstagramCarouselDownloadRequest(BaseModel):
    url: str = Field(..., description="Instagram carousel post URL")
    quality: Optional[str] = Field(default="best", description="Quality: best, high, medium, low")
    include_metadata: Optional[bool] = Field(default=True, description="Include metadata.json in ZIP")


class InstagramBatchItem(BaseModel):
    url: str = Field(..., description="Instagram URL or shortcode")
    type: str = Field(..., description="Content type: post, reel, story")


class InstagramBatchDownloadRequest(BaseModel):
    items: List[InstagramBatchItem] = Field(..., description="List of items to download")
    quality: Optional[str] = Field(default="best", description="Quality preference")
    continue_on_error: Optional[bool] = Field(default=True, description="Continue if individual download fails")


def get_client_ip(request: Request) -> str:
    """Get client IP address from request."""
    if request.client:
        return request.client.host
    return "unknown"


def check_rate_limit(ip: str) -> bool:
    """Check if IP has exceeded rate limit."""
    now = time.time()
    minute_ago = now - 60
    rate_limit_store[ip] = [t for t in rate_limit_store[ip] if t > minute_ago]
    if len(rate_limit_store[ip]) >= MAX_REQUESTS_PER_MINUTE:
        return False
    rate_limit_store[ip].append(now)
    return True


def get_format_string(quality: Optional[str], download_type: Optional[str]) -> str:
    """Convert quality preference to yt-dlp format string."""
    quality = quality or "best"
    download_type = download_type or "video"
    
    if quality == "audio_only" or download_type == "audio":
        return "bestaudio/best"
    
    quality_map = {
        "best": "bestvideo+bestaudio/best",
        "worst": "worstvideo+worstaudio/worst",
        "720p": "bestvideo[height<=720]+bestaudio/best[height<=720]",
        "1080p": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
        "1440p": "bestvideo[height<=1440]+bestaudio/best[height<=1440]",
        "4k": "bestvideo[height<=2160]+bestaudio/best[height<=2160]",
    }
    return quality_map.get(quality, "bestvideo+bestaudio/best")


def get_yt_dlp_opts(output_path: str, format_str: str, audio_format: Optional[str] = None) -> dict:
    """Get yt-dlp options dictionary."""
    audio_format = audio_format or "best"
    
    opts = {
        "outtmpl": output_path,
        "format": format_str,
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": False,
    }
    
    if audio_format == "mp3":
        opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }]
        opts["format"] = "bestaudio/best"
    elif audio_format == "m4a":
        opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "m4a",
            "preferredquality": "192",
        }]
        opts["format"] = "bestaudio/best"
    
    return opts


async def cleanup_old_files():
    """Remove files older than CLEANUP_TIMEOUT_MINUTES."""
    try:
        now = datetime.now()
        for file_path in DOWNLOAD_DIR.iterdir():
            if file_path.is_file():
                file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                if now - file_time > timedelta(minutes=CLEANUP_TIMEOUT_MINUTES):
                    file_path.unlink()
    except Exception:
        pass


def extract_video_info(info: dict) -> dict:
    """Extract relevant video information."""
    return {
        "id": info.get("id"),
        "title": info.get("title"),
        "description": info.get("description", "")[:500] if info.get("description") else None,
        "duration": info.get("duration"),
        "duration_string": info.get("duration_string"),
        "view_count": info.get("view_count"),
        "upload_date": info.get("upload_date"),
        "channel": info.get("channel"),
        "channel_id": info.get("channel_id"),
        "channel_url": info.get("channel_url"),
        "channel_subscriber_count": info.get("channel_follower_count"),
        "thumbnail": info.get("thumbnail"),
        "thumbnails": info.get("thumbnails", [])[-3:] if info.get("thumbnails") else [],
        "webpage_url": info.get("webpage_url"),
        "is_live": info.get("is_live", False),
        "age_limit": info.get("age_limit", 0),
    }


def extract_format_info(fmt: dict) -> dict:
    """Extract relevant format information."""
    return {
        "format_id": fmt.get("format_id"),
        "ext": fmt.get("ext"),
        "resolution": fmt.get("resolution") or f"{fmt.get('width', 'N/A')}x{fmt.get('height', 'N/A')}",
        "fps": fmt.get("fps"),
        "vcodec": fmt.get("vcodec"),
        "acodec": fmt.get("acodec"),
        "filesize": fmt.get("filesize") or fmt.get("filesize_approx"),
        "filesize_approx": fmt.get("filesize_approx"),
        "quality": fmt.get("quality"),
        "format_note": fmt.get("format_note"),
        "tbr": fmt.get("tbr"),
        "abr": fmt.get("abr"),
        "vbr": fmt.get("vbr"),
    }


@app.on_event("startup")
async def startup_event():
    """Clean up old files on startup."""
    await cleanup_old_files()


@app.get("/")
async def root():
    """Redirect to the testing UI."""
    return RedirectResponse(url="/ui/index.html")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/info")
async def get_video_info(request: Request, url: str = Query(..., description="YouTube video or playlist URL")):
    """
    Get detailed information about a YouTube video or playlist.
    Returns metadata including title, duration, views, channel info, and thumbnails.
    """
    if not check_rate_limit(get_client_ip(request)):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please try again later.")
    
    try:
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            "ignoreerrors": True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            if info is None:
                raise HTTPException(status_code=400, detail="Could not extract video information. The video may be private, age-restricted, or unavailable.")
            
            if info.get("_type") == "playlist":
                entries = info.get("entries", [])
                videos = []
                for entry in entries:
                    if entry:
                        videos.append(extract_video_info(entry))
                
                return {
                    "type": "playlist",
                    "playlist_id": info.get("id"),
                    "playlist_title": info.get("title"),
                    "playlist_count": len(videos),
                    "uploader": info.get("uploader"),
                    "videos": videos
                }
            else:
                return {
                    "type": "video",
                    **extract_video_info(info)
                }
                
    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e)
        if "Private video" in error_msg:
            raise HTTPException(status_code=403, detail="This video is private and cannot be accessed.")
        elif "age-restricted" in error_msg.lower():
            raise HTTPException(status_code=403, detail="This video is age-restricted. Login may be required.")
        elif "not available" in error_msg.lower():
            raise HTTPException(status_code=404, detail="This video is not available in your region or has been removed.")
        elif "live" in error_msg.lower():
            raise HTTPException(status_code=400, detail="Live streams cannot be downloaded while they are active.")
        else:
            raise HTTPException(status_code=400, detail=f"Error extracting video info: {error_msg}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/formats")
async def get_formats(request: Request, url: str = Query(..., description="YouTube video URL")):
    """
    Get all available formats for a YouTube video.
    Returns grouped formats: video-only, audio-only, and combined.
    """
    if not check_rate_limit(get_client_ip(request)):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please try again later.")
    
    try:
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            if info is None:
                raise HTTPException(status_code=400, detail="Could not extract format information.")
            
            formats = info.get("formats", [])
            
            video_only = []
            audio_only = []
            combined = []
            
            for fmt in formats:
                fmt_info = extract_format_info(fmt)
                vcodec = fmt.get("vcodec", "none")
                acodec = fmt.get("acodec", "none")
                
                if vcodec != "none" and acodec != "none":
                    combined.append(fmt_info)
                elif vcodec != "none":
                    video_only.append(fmt_info)
                elif acodec != "none":
                    audio_only.append(fmt_info)
            
            return {
                "video_id": info.get("id"),
                "title": info.get("title"),
                "formats": {
                    "video_only": video_only,
                    "audio_only": audio_only,
                    "combined": combined
                },
                "recommended": {
                    "best_video": "bestvideo+bestaudio/best",
                    "best_audio": "bestaudio/best",
                    "720p": "bestvideo[height<=720]+bestaudio",
                    "1080p": "bestvideo[height<=1080]+bestaudio",
                }
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting formats: {str(e)}")


@app.post("/download/single")
async def download_single(request: Request, download_req: DownloadRequest, background_tasks: BackgroundTasks):
    """
    Download a single YouTube video or audio.
    Returns a job ID for tracking the download progress.
    """
    if not check_rate_limit(get_client_ip(request)):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please try again later.")
    
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "status": "pending",
        "progress": 0,
        "url": download_req.url,
        "created_at": datetime.now().isoformat(),
        "files": [],
        "error": None
    }
    
    background_tasks.add_task(
        process_download,
        job_id,
        download_req.url,
        download_req.quality,
        download_req.format_id,
        download_req.type,
        download_req.audio_format
    )
    
    return {
        "job_id": job_id,
        "status": "pending",
        "message": "Download started. Use /status/{job_id} to check progress.",
        "status_url": f"/status/{job_id}"
    }


async def process_download(job_id: str, url: str, quality: Optional[str], format_id: Optional[str], 
                          download_type: Optional[str], audio_format: Optional[str]):
    """Background task to process video download."""
    try:
        jobs[job_id]["status"] = "processing"
        
        file_id = str(uuid.uuid4())[:8]
        output_template = str(DOWNLOAD_DIR / f"{file_id}_%(title)s.%(ext)s")
        
        if format_id:
            format_str = format_id
        else:
            format_str = get_format_string(quality, download_type)
        
        ydl_opts = get_yt_dlp_opts(output_template, format_str, audio_format)
        
        def progress_hook(d):
            if d["status"] == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
                downloaded = d.get("downloaded_bytes", 0)
                if total > 0:
                    jobs[job_id]["progress"] = int((downloaded / total) * 100)
            elif d["status"] == "finished":
                jobs[job_id]["progress"] = 100
        
        ydl_opts["progress_hooks"] = [progress_hook]
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            
            if info:
                downloaded_files = list(DOWNLOAD_DIR.glob(f"{file_id}_*"))
                jobs[job_id]["files"] = [
                    {
                        "filename": f.name,
                        "path": str(f),
                        "size": f.stat().st_size,
                        "download_url": f"/download/file/{f.name}"
                    }
                    for f in downloaded_files
                ]
                jobs[job_id]["status"] = "completed"
                jobs[job_id]["title"] = info.get("title")
            else:
                jobs[job_id]["status"] = "failed"
                jobs[job_id]["error"] = "Download failed - could not extract video info"
                
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)


@app.get("/status/{job_id}")
async def get_job_status(job_id: str):
    """
    Check the status of a download job.
    Returns progress percentage and download links when complete.
    """
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs[job_id]
    return {
        "job_id": job_id,
        "status": job["status"],
        "progress": job["progress"],
        "files": job.get("files", []),
        "error": job.get("error"),
        "title": job.get("title"),
        "created_at": job["created_at"]
    }


@app.get("/download/file/{filename}")
async def download_file(filename: str):
    """
    Download a processed file by filename.
    Files are automatically cleaned up after 30 minutes.
    """
    file_path = DOWNLOAD_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found or has been cleaned up")
    
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/octet-stream"
    )


@app.post("/download/batch")
async def download_batch(request: Request, batch_req: BatchDownloadRequest, background_tasks: BackgroundTasks):
    """
    Download multiple YouTube videos/audios simultaneously.
    Returns a job ID for tracking all downloads together.
    """
    if not check_rate_limit(get_client_ip(request)):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please try again later.")
    
    if not batch_req.urls:
        raise HTTPException(status_code=400, detail="At least one URL must be provided")
    
    if len(batch_req.urls) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 URLs per batch download")
    
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "status": "pending",
        "progress": 0,
        "urls": batch_req.urls,
        "created_at": datetime.now().isoformat(),
        "files": [],
        "error": None,
        "type": "batch",
        "total_urls": len(batch_req.urls),
        "completed_count": 0
    }
    
    background_tasks.add_task(
        process_batch_download,
        job_id,
        batch_req.urls,
        batch_req.quality,
        batch_req.type,
        batch_req.audio_format
    )
    
    return {
        "job_id": job_id,
        "status": "pending",
        "total_urls": len(batch_req.urls),
        "message": "Batch download started. Use /status/{job_id} to check progress.",
        "status_url": f"/status/{job_id}"
    }


async def process_batch_download(job_id: str, urls: List[str], quality: Optional[str], download_type: Optional[str], audio_format: Optional[str]):
    """Background task to process batch downloads."""
    try:
        jobs[job_id]["status"] = "processing"
        total = len(urls)
        
        for idx, url in enumerate(urls):
            try:
                file_id = str(uuid.uuid4())[:8]
                output_template = str(DOWNLOAD_DIR / f"{file_id}_%(title)s.%(ext)s")
                format_str = get_format_string(quality, download_type)
                download_opts = get_yt_dlp_opts(output_template, format_str, audio_format)
                
                with yt_dlp.YoutubeDL(download_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    
                    if info:
                        downloaded_files = list(DOWNLOAD_DIR.glob(f"{file_id}_*"))
                        for f in downloaded_files:
                            jobs[job_id]["files"].append({
                                "filename": f.name,
                                "path": str(f),
                                "size": f.stat().st_size,
                                "download_url": f"/download/file/{f.name}",
                                "title": info.get("title")
                            })
                        jobs[job_id]["completed_count"] += 1
                    
            except Exception as e:
                jobs[job_id].setdefault("errors", []).append({
                    "url": url,
                    "error": str(e)
                })
            
            jobs[job_id]["progress"] = int(((idx + 1) / total) * 100)
        
        jobs[job_id]["status"] = "completed"
        
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)


@app.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str):
    """
    Cancel a running download job.
    Only pending and processing jobs can be cancelled.
    """
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs[job_id]
    
    if job["status"] not in ["pending", "processing"]:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot cancel job with status '{job['status']}'. Only pending or processing jobs can be cancelled."
        )
    
    job["status"] = "cancelled"
    job["error"] = "Job was cancelled by user"
    
    return {
        "job_id": job_id,
        "status": "cancelled",
        "message": "Download job has been cancelled",
        "cancelled_at": datetime.now().isoformat()
    }


@app.get("/jobs")
async def list_jobs(
    skip: int = Query(default=0, ge=0, description="Number of jobs to skip"),
    limit: int = Query(default=10, ge=1, le=100, description="Number of jobs to return"),
    status: Optional[str] = Query(default=None, description="Filter by status: pending, processing, completed, failed, cancelled"),
    type: Optional[str] = Query(default=None, description="Filter by type: video, playlist, batch")
):
    """
    List all download jobs with pagination and filtering.
    Returns job summaries with status and progress.
    """
    # Filter jobs based on criteria
    filtered_jobs = list(jobs.items())
    
    if status:
        filtered_jobs = [(jid, j) for jid, j in filtered_jobs if j.get("status") == status]
    
    if type:
        filtered_jobs = [(jid, j) for jid, j in filtered_jobs if j.get("type", "video") == type]
    
    # Sort by creation time (newest first)
    filtered_jobs.sort(key=lambda x: x[1].get("created_at", ""), reverse=True)
    
    # Apply pagination
    total = len(filtered_jobs)
    paginated_jobs = filtered_jobs[skip:skip + limit]
    
    job_summaries = []
    for job_id, job in paginated_jobs:
        job_summaries.append({
            "job_id": job_id,
            "status": job.get("status"),
            "type": job.get("type", "video"),
            "progress": job.get("progress"),
            "created_at": job.get("created_at"),
            "files_count": len(job.get("files", [])),
            "error_count": len(job.get("errors", [])),
            "title": job.get("title"),
            "total_urls": job.get("total_urls"),
            "completed_count": job.get("completed_count")
        })
    
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "jobs": job_summaries,
        "has_more": (skip + limit) < total
    }


@app.get("/stream/video")
async def stream_video(
    request: Request,
    url: str = Query(..., description="YouTube video URL"),
    quality: str = Query(default="best", description="Quality: best, worst, 720p, 1080p, 1440p, 4k")
):
    """
    Stream a YouTube video directly without saving to disk.
    Returns a streaming response that can be played in real-time.
    """
    if not check_rate_limit(get_client_ip(request)):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please try again later.")
    
    try:
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "format": get_format_string(quality, "video"),
            "socket_timeout": 30,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            if info is None:
                raise HTTPException(status_code=400, detail="Could not extract video information")
            
            # Get the best video format URL
            formats = info.get("formats", [])
            video_url = None
            
            for fmt in formats:
                if fmt.get("vcodec") != "none" and fmt.get("format_id"):
                    video_url = fmt.get("url")
                    if video_url:
                        break
            
            if not video_url:
                raise HTTPException(status_code=400, detail="No video URL found for streaming")
            
            # Return redirect to the video URL for streaming
            return RedirectResponse(
                url=video_url,
                status_code=307,
                headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error streaming video: {str(e)}")


@app.get("/download/playlist/info")
async def get_playlist_info(request: Request, url: str = Query(..., description="YouTube playlist URL")):
    """
    Get information about all videos in a playlist.
    Returns list of videos with index, title, duration, and thumbnail.
    """
    if not check_rate_limit(get_client_ip(request)):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please try again later.")
    
    try:
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": True,
            "ignoreerrors": True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            if info is None or info.get("_type") != "playlist":
                raise HTTPException(status_code=400, detail="URL is not a valid playlist")
            
            entries = info.get("entries", [])
            videos = []
            
            for idx, entry in enumerate(entries):
                if entry:
                    videos.append({
                        "index": idx,
                        "id": entry.get("id"),
                        "title": entry.get("title"),
                        "duration": entry.get("duration"),
                        "url": entry.get("url") or f"https://www.youtube.com/watch?v={entry.get('id')}",
                        "thumbnail": entry.get("thumbnail") or entry.get("thumbnails", [{}])[0].get("url") if entry.get("thumbnails") else None
                    })
            
            return {
                "playlist_id": info.get("id"),
                "playlist_title": info.get("title"),
                "playlist_count": len(videos),
                "uploader": info.get("uploader"),
                "videos": videos
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting playlist info: {str(e)}")


@app.post("/download/playlist/all")
async def download_playlist_all(request: Request, download_req: DownloadRequest, background_tasks: BackgroundTasks):
    """
    Download all videos from a playlist.
    Returns a job ID for tracking progress. Downloads are processed individually to avoid memory issues.
    """
    if not check_rate_limit(get_client_ip(request)):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please try again later.")
    
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "status": "pending",
        "progress": 0,
        "url": download_req.url,
        "created_at": datetime.now().isoformat(),
        "files": [],
        "error": None,
        "type": "playlist"
    }
    
    background_tasks.add_task(
        process_playlist_download,
        job_id,
        download_req.url,
        download_req.quality,
        download_req.format_id,
        download_req.type,
        download_req.audio_format,
        None
    )
    
    return {
        "job_id": job_id,
        "status": "pending",
        "message": "Playlist download started. Use /status/{job_id} to check progress.",
        "status_url": f"/status/{job_id}"
    }


@app.post("/download/playlist/select")
async def download_playlist_select(request: Request, select_req: PlaylistSelectRequest, background_tasks: BackgroundTasks):
    """
    Download selected videos from a playlist by their indices.
    Returns a job ID for tracking progress.
    """
    if not check_rate_limit(get_client_ip(request)):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please try again later.")
    
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "status": "pending",
        "progress": 0,
        "url": select_req.url,
        "created_at": datetime.now().isoformat(),
        "files": [],
        "error": None,
        "type": "playlist_select",
        "selected_indices": select_req.video_indices
    }
    
    background_tasks.add_task(
        process_playlist_download,
        job_id,
        select_req.url,
        select_req.quality,
        None,
        select_req.type,
        select_req.audio_format,
        select_req.video_indices
    )
    
    return {
        "job_id": job_id,
        "status": "pending",
        "message": "Selected videos download started. Use /status/{job_id} to check progress.",
        "status_url": f"/status/{job_id}"
    }


async def process_playlist_download(job_id: str, url: str, quality: Optional[str], format_id: Optional[str],
                                    download_type: Optional[str], audio_format: Optional[str], indices: Optional[List[int]]):
    """Background task to process playlist download."""
    try:
        jobs[job_id]["status"] = "processing"
        
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": True,
            "ignoreerrors": True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            if info is None:
                jobs[job_id]["status"] = "failed"
                jobs[job_id]["error"] = "Could not extract playlist info"
                return
            
            entries = info.get("entries", [])
            
            if indices:
                entries_to_download = [(i, entries[i]) for i in indices if i < len(entries) and entries[i]]
            else:
                entries_to_download = [(i, e) for i, e in enumerate(entries) if e]
            
            total = len(entries_to_download)
            jobs[job_id]["total_videos"] = total
            
            for idx, (video_idx, entry) in enumerate(entries_to_download):
                video_url = entry.get("url") or f"https://www.youtube.com/watch?v={entry.get('id')}"
                
                file_id = str(uuid.uuid4())[:8]
                output_template = str(DOWNLOAD_DIR / f"{file_id}_%(title)s.%(ext)s")
                
                format_str = format_id if format_id else get_format_string(quality, download_type)
                download_opts = get_yt_dlp_opts(output_template, format_str, audio_format)
                
                try:
                    with yt_dlp.YoutubeDL(download_opts) as dl:
                        dl.download([video_url])
                    
                    downloaded_files = list(DOWNLOAD_DIR.glob(f"{file_id}_*"))
                    for f in downloaded_files:
                        jobs[job_id]["files"].append({
                            "filename": f.name,
                            "path": str(f),
                            "size": f.stat().st_size,
                            "download_url": f"/download/file/{f.name}",
                            "video_index": video_idx,
                            "title": entry.get("title")
                        })
                except Exception as e:
                    jobs[job_id].setdefault("errors", []).append({
                        "video_index": video_idx,
                        "title": entry.get("title"),
                        "error": str(e)
                    })
                
                jobs[job_id]["progress"] = int(((idx + 1) / total) * 100)
            
            jobs[job_id]["status"] = "completed"
            
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)


@app.get("/subtitles")
async def get_subtitles_info(request: Request, url: str = Query(...), lang: str = Query(default="all")):
    """
    Get available subtitles for a video.
    Use lang="all" to list all available languages.
    """
    if not check_rate_limit(get_client_ip(request)):
        raise HTTPException(status_code=429, detail="Rate limit exceeded.")
    
    try:
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "writesubtitles": True,
            "writeautomaticsub": True,
            "skip_download": True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            if info is None:
                raise HTTPException(status_code=400, detail="Could not extract video info")
            
            subtitles = info.get("subtitles", {})
            auto_subs = info.get("automatic_captions", {})
            
            if lang == "all":
                return {
                    "video_id": info.get("id"),
                    "title": info.get("title"),
                    "manual_subtitles": list(subtitles.keys()),
                    "auto_generated_subtitles": list(auto_subs.keys()),
                    "subtitle_details": {
                        lang: [{"ext": s.get("ext"), "url": s.get("url")} for s in subs]
                        for lang, subs in subtitles.items()
                    },
                    "auto_subtitle_details": {
                        lang: [{"ext": s.get("ext"), "url": s.get("url")} for s in subs]
                        for lang, subs in auto_subs.items()
                    }
                }
            else:
                sub_info = subtitles.get(lang) or auto_subs.get(lang)
                if not sub_info:
                    raise HTTPException(status_code=404, detail=f"Subtitles for language '{lang}' not found")
                
                return {
                    "video_id": info.get("id"),
                    "title": info.get("title"),
                    "language": lang,
                    "is_auto_generated": lang in auto_subs and lang not in subtitles,
                    "formats": [{"ext": s.get("ext"), "url": s.get("url")} for s in sub_info]
                }
                
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting subtitles: {str(e)}")


@app.post("/subtitles")
async def download_subtitles(request: Request, sub_req: SubtitleRequest, background_tasks: BackgroundTasks):
    """
    Download subtitles for a video.
    Returns the subtitle content or a download link.
    """
    if not check_rate_limit(get_client_ip(request)):
        raise HTTPException(status_code=429, detail="Rate limit exceeded.")
    
    try:
        file_id = str(uuid.uuid4())[:8]
        output_template = str(DOWNLOAD_DIR / f"{file_id}_%(title)s")
        
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "writesubtitles": True,
            "writeautomaticsub": sub_req.auto,
            "subtitleslangs": [sub_req.lang],
            "skip_download": True,
            "outtmpl": output_template,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(sub_req.url, download=True)
            
            if info is None:
                raise HTTPException(status_code=400, detail="Could not extract video info")
            
            sub_files = list(DOWNLOAD_DIR.glob(f"{file_id}_*.vtt")) + list(DOWNLOAD_DIR.glob(f"{file_id}_*.srt"))
            
            if not sub_files:
                raise HTTPException(status_code=404, detail=f"No subtitles found for language '{sub_req.lang}'")
            
            sub_file = sub_files[0]
            
            return {
                "video_id": info.get("id"),
                "title": info.get("title"),
                "language": sub_req.lang,
                "filename": sub_file.name,
                "download_url": f"/download/file/{sub_file.name}"
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error downloading subtitles: {str(e)}")


@app.get("/thumbnail")
async def get_thumbnail(
    request: Request,
    url: str = Query(..., description="YouTube video URL"),
    quality: str = Query(default="maxres", description="Quality: maxres, hq, mq, sd, default")
):
    """
    Get the thumbnail URL for a video.
    Returns a redirect to the thumbnail or the URL.
    """
    if not check_rate_limit(get_client_ip(request)):
        raise HTTPException(status_code=429, detail="Rate limit exceeded.")
    
    try:
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            if info is None:
                raise HTTPException(status_code=400, detail="Could not extract video info")
            
            video_id = info.get("id")
            thumbnails = info.get("thumbnails", [])
            
            quality_map = {
                "maxres": f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
                "hq": f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
                "mq": f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg",
                "sd": f"https://img.youtube.com/vi/{video_id}/sddefault.jpg",
                "default": f"https://img.youtube.com/vi/{video_id}/default.jpg",
            }
            
            thumbnail_url = quality_map.get(quality, thumbnails[-1].get("url") if thumbnails else None)
            
            if not thumbnail_url:
                raise HTTPException(status_code=404, detail="Thumbnail not found")
            
            return {
                "video_id": video_id,
                "title": info.get("title"),
                "quality": quality,
                "thumbnail_url": thumbnail_url,
                "all_thumbnails": [{"quality": t.get("id"), "url": t.get("url")} for t in thumbnails[-5:]]
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting thumbnail: {str(e)}")


def normalize_instagram_url(url_or_code: str) -> str:
    """Convert Instagram shortcode or URL to full URL."""
    url_or_code = url_or_code.strip()
    
    if url_or_code.startswith(('http://', 'https://')):
        return url_or_code
    
    if '/p/' in url_or_code or '/reel/' in url_or_code or '/reels/' in url_or_code:
        return f"https://www.instagram.com{url_or_code}"
    
    return f"https://www.instagram.com/p/{url_or_code}/"


def normalize_instagram_reel_url(url_or_code: str) -> str:
    """Convert Instagram reel shortcode or URL to full URL."""
    url_or_code = url_or_code.strip()
    
    if url_or_code.startswith(('http://', 'https://')):
        return url_or_code
    
    if '/reel/' in url_or_code or '/reels/' in url_or_code:
        return f"https://www.instagram.com{url_or_code}"
    
    return f"https://www.instagram.com/reel/{url_or_code}/"


def normalize_instagram_profile_url(username: str) -> str:
    """Convert Instagram username to profile URL."""
    username = username.strip().lstrip('@')
    return f"https://www.instagram.com/{username}/"


def normalize_instagram_stories_url(username: str) -> str:
    """Convert Instagram username to stories URL."""
    username = username.strip().lstrip('@')
    return f"https://www.instagram.com/stories/{username}/"


def extract_instagram_shortcode(url: str) -> Optional[str]:
    """Extract shortcode from Instagram URL."""
    patterns = [
        r'instagram\.com/p/([A-Za-z0-9_-]+)',
        r'instagram\.com/reel/([A-Za-z0-9_-]+)',
        r'instagram\.com/reels/([A-Za-z0-9_-]+)',
        r'instagram\.com/tv/([A-Za-z0-9_-]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def get_instagram_ydl_opts(output_path: str, quality: str = "best") -> dict:
    """Get yt-dlp options for Instagram downloads."""
    opts = {
        "outtmpl": output_path,
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": False,
        "extract_flat": False,
    }
    
    if quality == "best":
        opts["format"] = "best"
    elif quality in ["1080p", "high"]:
        opts["format"] = "best[height<=1080]/best"
    elif quality in ["720p", "medium"]:
        opts["format"] = "best[height<=720]/best"
    elif quality in ["480p", "low"]:
        opts["format"] = "best[height<=480]/best"
    else:
        opts["format"] = "best"
    
    return opts


def get_instagram_audio_opts(output_path: str, audio_format: str = "mp3") -> dict:
    """Get yt-dlp options for Instagram audio extraction."""
    opts = {
        "outtmpl": output_path,
        "quiet": True,
        "no_warnings": True,
        "format": "bestaudio/best",
    }
    
    if audio_format == "mp3":
        opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }]
    elif audio_format == "m4a":
        opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "m4a",
            "preferredquality": "192",
        }]
    
    return opts


def extract_instagram_post_info(info: dict) -> dict:
    """Extract relevant Instagram post information."""
    entries = info.get("entries", [info])
    if not entries:
        entries = [info]
    
    first_entry = entries[0] if entries else info
    
    is_carousel = len(entries) > 1 if info.get("_type") == "playlist" else False
    
    media_items = []
    for idx, entry in enumerate(entries):
        if entry:
            item = {
                "index": idx,
                "type": "video" if entry.get("ext") in ["mp4", "webm", "m4v"] else "image",
                "url": entry.get("url") or entry.get("webpage_url"),
                "thumbnail": entry.get("thumbnail"),
                "duration": entry.get("duration"),
                "width": entry.get("width"),
                "height": entry.get("height"),
            }
            media_items.append(item)
    
    return {
        "type": "carousel" if is_carousel else ("video" if first_entry.get("ext") in ["mp4", "webm", "m4v"] else "image"),
        "post_id": info.get("id") or extract_instagram_shortcode(info.get("webpage_url", "")),
        "shortcode": extract_instagram_shortcode(info.get("webpage_url", "")) or info.get("id"),
        "caption": info.get("description") or info.get("title"),
        "owner": {
            "username": info.get("uploader") or info.get("channel"),
            "user_id": info.get("uploader_id") or info.get("channel_id"),
        },
        "timestamp": info.get("timestamp"),
        "upload_date": info.get("upload_date"),
        "view_count": info.get("view_count"),
        "like_count": info.get("like_count"),
        "comment_count": info.get("comment_count"),
        "duration": info.get("duration"),
        "thumbnail": info.get("thumbnail"),
        "webpage_url": info.get("webpage_url"),
        "is_carousel": is_carousel,
        "carousel_count": len(entries) if is_carousel else None,
        "media_items": media_items if is_carousel else None,
    }


def extract_instagram_reel_info(info: dict) -> dict:
    """Extract relevant Instagram reel information."""
    return {
        "type": "reel",
        "reel_id": info.get("id"),
        "shortcode": extract_instagram_shortcode(info.get("webpage_url", "")) or info.get("id"),
        "caption": info.get("description") or info.get("title"),
        "video_url": info.get("url"),
        "thumbnail": info.get("thumbnail"),
        "duration": info.get("duration"),
        "width": info.get("width"),
        "height": info.get("height"),
        "fps": info.get("fps"),
        "owner": {
            "username": info.get("uploader") or info.get("channel"),
            "user_id": info.get("uploader_id") or info.get("channel_id"),
        },
        "timestamp": info.get("timestamp"),
        "upload_date": info.get("upload_date"),
        "view_count": info.get("view_count"),
        "like_count": info.get("like_count"),
        "comment_count": info.get("comment_count"),
        "webpage_url": info.get("webpage_url"),
        "formats": [
            {
                "format_id": f.get("format_id"),
                "ext": f.get("ext"),
                "resolution": f.get("resolution") or f"{f.get('width', 'N/A')}x{f.get('height', 'N/A')}",
                "filesize": f.get("filesize"),
            }
            for f in info.get("formats", [])[:5]
        ],
    }


def extract_instagram_story_info(info: dict) -> dict:
    """Extract relevant Instagram story information."""
    entries = info.get("entries", [info])
    if not entries:
        entries = [info]
    
    stories = []
    for idx, entry in enumerate(entries):
        if entry:
            stories.append({
                "story_id": entry.get("id"),
                "story_index": idx + 1,
                "media_type": "video" if entry.get("ext") in ["mp4", "webm", "m4v"] else "image",
                "url": entry.get("url") or entry.get("webpage_url"),
                "thumbnail": entry.get("thumbnail"),
                "duration": entry.get("duration"),
                "timestamp": entry.get("timestamp"),
                "width": entry.get("width"),
                "height": entry.get("height"),
            })
    
    return {
        "type": "stories",
        "username": info.get("uploader") or info.get("channel"),
        "user_id": info.get("uploader_id") or info.get("channel_id"),
        "has_active_stories": len(stories) > 0,
        "active_stories_count": len(stories),
        "stories": stories,
    }


@instagram_router.get("/info")
async def instagram_api_info():
    """
    Get Instagram API information and capabilities.
    Returns available endpoints and supported features.
    """
    return {
        "api": {
            "name": "Instagram Downloader & Info API",
            "version": "1.0.0",
            "base_url": "/instagram",
        },
        "capabilities": {
            "supported_content_types": ["posts", "reels", "stories", "carousels"],
            "download_features": ["batch_downloads", "quality_selection", "audio_extraction", "zip_export"],
        },
        "limits": {
            "max_batch_size": 20,
            "file_retention_minutes": 30,
            "rate_limit_requests_per_minute": 30,
        },
        "endpoints": [
            {"method": "GET", "path": "/instagram/post/info", "description": "Get post information"},
            {"method": "GET", "path": "/instagram/reel/info", "description": "Get reel information"},
            {"method": "GET", "path": "/instagram/story/info", "description": "Get stories information"},
            {"method": "GET", "path": "/instagram/profile/info", "description": "Get profile information"},
            {"method": "POST", "path": "/instagram/download/post", "description": "Download a post"},
            {"method": "POST", "path": "/instagram/download/reel", "description": "Download a reel"},
            {"method": "POST", "path": "/instagram/download/story", "description": "Download stories"},
            {"method": "POST", "path": "/instagram/download/carousel", "description": "Download carousel as ZIP"},
            {"method": "POST", "path": "/instagram/download/batch", "description": "Batch download"},
            {"method": "GET", "path": "/instagram/status/{job_id}", "description": "Check download status"},
            {"method": "GET", "path": "/instagram/download/file/{filename}", "description": "Get downloaded file"},
        ]
    }


@instagram_router.get("/formats")
async def instagram_get_formats():
    """
    Get available download formats and quality options for Instagram content.
    Returns supported qualities for posts, reels, and stories.
    """
    return {
        "type": "available_formats",
        "post_formats": {
            "image": {
                "qualities": [
                    {"name": "best", "description": "Original resolution"},
                    {"name": "high", "description": "High quality"},
                    {"name": "medium", "description": "Medium quality"},
                    {"name": "low", "description": "Low quality"},
                ]
            },
            "video": {
                "qualities": [
                    {"name": "best", "description": "Best available quality"},
                    {"name": "1080p", "description": "Full HD"},
                    {"name": "720p", "description": "HD"},
                    {"name": "480p", "description": "Mobile friendly"},
                ]
            }
        },
        "reel_formats": {
            "video_qualities": [
                {"name": "best", "description": "Best quality"},
                {"name": "1080p", "description": "Full HD"},
                {"name": "720p", "description": "HD"},
                {"name": "480p", "description": "Standard"},
            ],
            "audio_formats": [
                {"format": "best", "description": "Best available"},
                {"format": "mp3", "bitrate": "192k"},
                {"format": "m4a", "bitrate": "128k"},
            ]
        },
        "story_formats": {
            "qualities": [
                {"name": "best", "description": "Original resolution"},
                {"name": "high", "description": "High quality"},
                {"name": "medium", "description": "Medium quality"},
            ]
        }
    }


@instagram_router.get("/post/info")
async def instagram_get_post_info(
    request: Request,
    url: str = Query(..., description="Instagram post URL or shortcode")
):
    """
    Get detailed information about an Instagram post.
    Supports single images, videos, and carousels.
    """
    if not check_rate_limit(get_client_ip(request)):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please try again later.")
    
    try:
        normalized_url = normalize_instagram_url(url)
        
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            "ignoreerrors": True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(normalized_url, download=False)
            
            if info is None:
                raise HTTPException(
                    status_code=404, 
                    detail="Post not found. It may be private, deleted, or the URL is invalid."
                )
            
            return {
                "success": True,
                **extract_instagram_post_info(info)
            }
            
    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e).lower()
        if "private" in error_msg:
            raise HTTPException(status_code=403, detail="This post is from a private account.")
        elif "not found" in error_msg or "404" in error_msg:
            raise HTTPException(status_code=404, detail="Post not found or has been deleted.")
        elif "login" in error_msg or "authentication" in error_msg:
            raise HTTPException(status_code=403, detail="This content requires authentication.")
        else:
            raise HTTPException(status_code=400, detail=f"Error extracting post info: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@instagram_router.get("/reel/info")
async def instagram_get_reel_info(
    request: Request,
    url: str = Query(..., description="Instagram reel URL or shortcode")
):
    """
    Get detailed information about an Instagram reel.
    Returns video metadata, engagement stats, and available formats.
    """
    if not check_rate_limit(get_client_ip(request)):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please try again later.")
    
    try:
        normalized_url = normalize_instagram_reel_url(url)
        
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(normalized_url, download=False)
            
            if info is None:
                raise HTTPException(
                    status_code=404, 
                    detail="Reel not found. It may be private, deleted, or the URL is invalid."
                )
            
            return {
                "success": True,
                **extract_instagram_reel_info(info)
            }
            
    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e).lower()
        if "private" in error_msg:
            raise HTTPException(status_code=403, detail="This reel is from a private account.")
        elif "not found" in error_msg or "404" in error_msg:
            raise HTTPException(status_code=404, detail="Reel not found or has been deleted.")
        else:
            raise HTTPException(status_code=400, detail=f"Error extracting reel info: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@instagram_router.get("/story/info")
async def instagram_get_story_info(
    request: Request,
    username: str = Query(..., description="Instagram username")
):
    """
    Get information about active stories from an Instagram profile.
    Returns list of currently available stories.
    """
    if not check_rate_limit(get_client_ip(request)):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please try again later.")
    
    try:
        stories_url = normalize_instagram_stories_url(username)
        
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            "ignoreerrors": True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(stories_url, download=False)
            
            if info is None:
                return {
                    "success": True,
                    "type": "stories",
                    "username": username.strip().lstrip('@'),
                    "has_active_stories": False,
                    "active_stories_count": 0,
                    "stories": [],
                    "message": "No active stories found or account may be private."
                }
            
            return {
                "success": True,
                **extract_instagram_story_info(info)
            }
            
    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e).lower()
        if "private" in error_msg:
            raise HTTPException(status_code=403, detail="This account is private.")
        elif "not found" in error_msg:
            raise HTTPException(status_code=404, detail="Profile not found.")
        else:
            return {
                "success": True,
                "type": "stories",
                "username": username.strip().lstrip('@'),
                "has_active_stories": False,
                "active_stories_count": 0,
                "stories": [],
                "message": "No active stories found or stories have expired."
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@instagram_router.get("/profile/info")
async def instagram_get_profile_info(
    request: Request,
    username: str = Query(..., description="Instagram username")
):
    """
    Get profile information for an Instagram account.
    Returns username, bio, followers count, and recent content info.
    """
    if not check_rate_limit(get_client_ip(request)):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please try again later.")
    
    try:
        profile_url = normalize_instagram_profile_url(username)
        
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": True,
            "ignoreerrors": True,
            "playlistend": 12,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(profile_url, download=False)
            
            if info is None:
                raise HTTPException(status_code=404, detail="Profile not found.")
            
            entries = info.get("entries", [])
            recent_posts = []
            for entry in entries[:12]:
                if entry:
                    recent_posts.append({
                        "id": entry.get("id"),
                        "title": entry.get("title"),
                        "url": entry.get("url") or entry.get("webpage_url"),
                        "thumbnail": entry.get("thumbnail"),
                        "duration": entry.get("duration"),
                    })
            
            return {
                "success": True,
                "type": "profile",
                "username": info.get("uploader") or info.get("channel") or username.strip().lstrip('@'),
                "user_id": info.get("uploader_id") or info.get("channel_id"),
                "profile_url": profile_url,
                "total_posts": info.get("playlist_count") or len(entries),
                "recent_posts": recent_posts,
                "recent_posts_count": len(recent_posts),
            }
            
    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e).lower()
        if "private" in error_msg:
            raise HTTPException(status_code=403, detail="This account is private.")
        elif "not found" in error_msg or "404" in error_msg:
            raise HTTPException(status_code=404, detail="Profile not found.")
        else:
            raise HTTPException(status_code=400, detail=f"Error: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@instagram_router.get("/profile/posts")
async def instagram_get_profile_posts(
    request: Request,
    username: str = Query(..., description="Instagram username"),
    limit: int = Query(default=12, ge=1, le=50, description="Number of posts to return")
):
    """
    Get recent posts from an Instagram profile.
    Supports pagination with limit parameter.
    """
    if not check_rate_limit(get_client_ip(request)):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please try again later.")
    
    try:
        profile_url = normalize_instagram_profile_url(username)
        
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": True,
            "ignoreerrors": True,
            "playlistend": limit,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(profile_url, download=False)
            
            if info is None:
                raise HTTPException(status_code=404, detail="Profile not found.")
            
            entries = info.get("entries", [])
            posts = []
            for idx, entry in enumerate(entries[:limit]):
                if entry:
                    posts.append({
                        "index": idx,
                        "post_id": entry.get("id"),
                        "title": entry.get("title"),
                        "url": entry.get("url") or entry.get("webpage_url"),
                        "thumbnail": entry.get("thumbnail"),
                        "duration": entry.get("duration"),
                        "is_video": entry.get("duration") is not None,
                    })
            
            return {
                "success": True,
                "type": "profile_posts",
                "username": info.get("uploader") or username.strip().lstrip('@'),
                "total_posts": info.get("playlist_count") or len(entries),
                "returned_count": len(posts),
                "limit": limit,
                "posts": posts,
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@instagram_router.post("/download/post")
async def instagram_download_post(
    request: Request,
    download_req: InstagramPostDownloadRequest,
    background_tasks: BackgroundTasks
):
    """
    Download an Instagram post (image, video, or carousel).
    Returns a job ID for tracking download progress.
    """
    if not check_rate_limit(get_client_ip(request)):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please try again later.")
    
    job_id = str(uuid.uuid4())
    normalized_url = normalize_instagram_url(download_req.url)
    
    jobs[job_id] = {
        "status": "pending",
        "progress": 0,
        "url": normalized_url,
        "created_at": datetime.now().isoformat(),
        "files": [],
        "error": None,
        "type": "instagram_post",
        "platform": "instagram"
    }
    
    background_tasks.add_task(
        process_instagram_download,
        job_id,
        normalized_url,
        download_req.quality or "best",
        download_req.download_type or "media",
        None
    )
    
    return {
        "job_id": job_id,
        "status": "pending",
        "message": "Post download started. Use /instagram/status/{job_id} to check progress.",
        "status_url": f"/instagram/status/{job_id}"
    }


@instagram_router.post("/download/reel")
async def instagram_download_reel(
    request: Request,
    download_req: InstagramReelDownloadRequest,
    background_tasks: BackgroundTasks
):
    """
    Download an Instagram reel with optional audio extraction.
    Returns a job ID for tracking download progress.
    """
    if not check_rate_limit(get_client_ip(request)):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please try again later.")
    
    job_id = str(uuid.uuid4())
    normalized_url = normalize_instagram_reel_url(download_req.url)
    
    jobs[job_id] = {
        "status": "pending",
        "progress": 0,
        "url": normalized_url,
        "created_at": datetime.now().isoformat(),
        "files": [],
        "error": None,
        "type": "instagram_reel",
        "platform": "instagram"
    }
    
    background_tasks.add_task(
        process_instagram_download,
        job_id,
        normalized_url,
        download_req.quality or "best",
        download_req.download_type or "video",
        download_req.audio_format if download_req.download_type == "audio_only" else None
    )
    
    return {
        "job_id": job_id,
        "status": "pending",
        "message": "Reel download started. Use /instagram/status/{job_id} to check progress.",
        "status_url": f"/instagram/status/{job_id}"
    }


@instagram_router.post("/download/story")
async def instagram_download_story(
    request: Request,
    download_req: InstagramStoryDownloadRequest,
    background_tasks: BackgroundTasks
):
    """
    Download Instagram stories from a user.
    Returns a job ID for tracking download progress.
    """
    if not check_rate_limit(get_client_ip(request)):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please try again later.")
    
    job_id = str(uuid.uuid4())
    stories_url = normalize_instagram_stories_url(download_req.username)
    
    jobs[job_id] = {
        "status": "pending",
        "progress": 0,
        "url": stories_url,
        "username": download_req.username.strip().lstrip('@'),
        "created_at": datetime.now().isoformat(),
        "files": [],
        "error": None,
        "type": "instagram_story",
        "platform": "instagram",
        "format": download_req.format
    }
    
    background_tasks.add_task(
        process_instagram_story_download,
        job_id,
        stories_url,
        download_req.quality or "best",
        download_req.format or "individual"
    )
    
    return {
        "job_id": job_id,
        "status": "pending",
        "message": "Story download started. Use /instagram/status/{job_id} to check progress.",
        "status_url": f"/instagram/status/{job_id}"
    }


@instagram_router.post("/download/carousel")
async def instagram_download_carousel(
    request: Request,
    download_req: InstagramCarouselDownloadRequest,
    background_tasks: BackgroundTasks
):
    """
    Download an Instagram carousel (multi-image/video post) as a ZIP file.
    All media items are bundled together with optional metadata.
    """
    if not check_rate_limit(get_client_ip(request)):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please try again later.")
    
    job_id = str(uuid.uuid4())
    normalized_url = normalize_instagram_url(download_req.url)
    
    jobs[job_id] = {
        "status": "pending",
        "progress": 0,
        "url": normalized_url,
        "created_at": datetime.now().isoformat(),
        "files": [],
        "error": None,
        "type": "instagram_carousel",
        "platform": "instagram",
        "include_metadata": download_req.include_metadata
    }
    
    background_tasks.add_task(
        process_instagram_carousel_download,
        job_id,
        normalized_url,
        download_req.quality or "best",
        download_req.include_metadata if download_req.include_metadata is not None else True
    )
    
    return {
        "job_id": job_id,
        "status": "pending",
        "message": "Carousel download started as ZIP. Use /instagram/status/{job_id} to check progress.",
        "status_url": f"/instagram/status/{job_id}"
    }


@instagram_router.post("/download/batch")
async def instagram_download_batch(
    request: Request,
    batch_req: InstagramBatchDownloadRequest,
    background_tasks: BackgroundTasks
):
    """
    Download multiple Instagram posts/reels in batch.
    Returns a job ID for tracking all downloads.
    """
    if not check_rate_limit(get_client_ip(request)):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please try again later.")
    
    if not batch_req.items:
        raise HTTPException(status_code=400, detail="At least one item must be provided")
    
    if len(batch_req.items) > 20:
        raise HTTPException(status_code=400, detail="Maximum 20 items per batch download")
    
    job_id = str(uuid.uuid4())
    
    jobs[job_id] = {
        "status": "pending",
        "progress": 0,
        "items": [{"url": item.url, "type": item.type} for item in batch_req.items],
        "created_at": datetime.now().isoformat(),
        "files": [],
        "error": None,
        "type": "instagram_batch",
        "platform": "instagram",
        "total_items": len(batch_req.items),
        "completed_count": 0,
        "errors": []
    }
    
    background_tasks.add_task(
        process_instagram_batch_download,
        job_id,
        batch_req.items,
        batch_req.quality or "best",
        batch_req.continue_on_error if batch_req.continue_on_error is not None else True
    )
    
    return {
        "job_id": job_id,
        "status": "pending",
        "total_items": len(batch_req.items),
        "message": "Batch download started. Use /instagram/status/{job_id} to check progress.",
        "status_url": f"/instagram/status/{job_id}"
    }


@instagram_router.get("/status/{job_id}")
async def instagram_get_status(job_id: str):
    """
    Check the status of an Instagram download job.
    Returns progress percentage and download links when complete.
    """
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found or has expired")
    
    job = jobs[job_id]
    
    if job.get("platform") != "instagram":
        raise HTTPException(status_code=400, detail="This is not an Instagram job. Use /status/{job_id} for YouTube jobs.")
    
    response = {
        "job_id": job_id,
        "status": job["status"],
        "progress": job["progress"],
        "type": job.get("type"),
        "files": job.get("files", []),
        "error": job.get("error"),
        "created_at": job["created_at"],
    }
    
    if job.get("type") == "instagram_batch":
        response["total_items"] = job.get("total_items")
        response["completed_count"] = job.get("completed_count")
        response["errors"] = job.get("errors", [])
    
    if job["status"] == "completed" and job.get("files"):
        response["message"] = "Download completed successfully."
        response["file_count"] = len(job.get("files", []))
    elif job["status"] == "failed":
        response["message"] = f"Download failed: {job.get('error', 'Unknown error')}"
    elif job["status"] == "processing":
        response["message"] = "Download in progress..."
    else:
        response["message"] = "Download queued..."
    
    return response


@instagram_router.get("/download/file/{filename}")
async def instagram_download_file(filename: str):
    """
    Download a completed Instagram media file.
    Files are automatically cleaned up after 30 minutes.
    """
    file_path = INSTAGRAM_DOWNLOAD_DIR / filename
    
    if not file_path.exists():
        file_path = DOWNLOAD_DIR / filename
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found or has been cleaned up")
    
    media_types = {
        ".mp4": "video/mp4",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".mp3": "audio/mpeg",
        ".m4a": "audio/mp4",
        ".zip": "application/zip",
    }
    
    ext = file_path.suffix.lower()
    media_type = media_types.get(ext, "application/octet-stream")
    
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type=media_type,
        headers={"Cache-Control": "no-cache"}
    )


@instagram_router.get("/post/stats")
async def instagram_get_post_stats(
    request: Request,
    url: str = Query(..., description="Instagram post URL or shortcode")
):
    """
    Get engagement statistics for an Instagram post.
    Returns likes, comments, and view counts.
    """
    if not check_rate_limit(get_client_ip(request)):
        raise HTTPException(status_code=429, detail="Rate limit exceeded.")
    
    try:
        normalized_url = normalize_instagram_url(url)
        
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(normalized_url, download=False)
            
            if info is None:
                raise HTTPException(status_code=404, detail="Post not found.")
            
            likes = info.get("like_count", 0)
            comments = info.get("comment_count", 0)
            views = info.get("view_count", 0)
            
            total_engagement = likes + comments
            
            return {
                "success": True,
                "type": "post_statistics",
                "post_id": info.get("id"),
                "shortcode": extract_instagram_shortcode(info.get("webpage_url", "")),
                "owner_username": info.get("uploader") or info.get("channel"),
                "statistics": {
                    "likes_count": likes,
                    "comments_count": comments,
                    "view_count": views,
                    "total_engagement": total_engagement,
                },
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@instagram_router.get("/reel/stats")
async def instagram_get_reel_stats(
    request: Request,
    url: str = Query(..., description="Instagram reel URL or shortcode")
):
    """
    Get engagement statistics for an Instagram reel.
    Returns views, likes, comments, and engagement metrics.
    """
    if not check_rate_limit(get_client_ip(request)):
        raise HTTPException(status_code=429, detail="Rate limit exceeded.")
    
    try:
        normalized_url = normalize_instagram_reel_url(url)
        
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(normalized_url, download=False)
            
            if info is None:
                raise HTTPException(status_code=404, detail="Reel not found.")
            
            views = info.get("view_count", 0)
            likes = info.get("like_count", 0)
            comments = info.get("comment_count", 0)
            duration = info.get("duration", 0)
            
            total_engagement = likes + comments
            
            return {
                "success": True,
                "type": "reel_statistics",
                "reel_id": info.get("id"),
                "shortcode": extract_instagram_shortcode(info.get("webpage_url", "")),
                "owner_username": info.get("uploader") or info.get("channel"),
                "duration_seconds": duration,
                "statistics": {
                    "view_count": views,
                    "likes_count": likes,
                    "comments_count": comments,
                    "total_engagement": total_engagement,
                },
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


async def process_instagram_download(
    job_id: str, 
    url: str, 
    quality: str, 
    download_type: str,
    audio_format: Optional[str]
):
    """Background task to process Instagram post/reel download."""
    try:
        jobs[job_id]["status"] = "processing"
        
        file_id = str(uuid.uuid4())[:8]
        output_template = str(INSTAGRAM_DOWNLOAD_DIR / f"{file_id}_%(title)s.%(ext)s")
        
        if download_type == "audio_only" and audio_format:
            ydl_opts = get_instagram_audio_opts(output_template, audio_format)
        else:
            ydl_opts = get_instagram_ydl_opts(output_template, quality)
        
        def progress_hook(d):
            if d["status"] == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
                downloaded = d.get("downloaded_bytes", 0)
                if total > 0:
                    jobs[job_id]["progress"] = int((downloaded / total) * 100)
            elif d["status"] == "finished":
                jobs[job_id]["progress"] = 100
        
        ydl_opts["progress_hooks"] = [progress_hook]
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            
            if info:
                downloaded_files = list(INSTAGRAM_DOWNLOAD_DIR.glob(f"{file_id}_*"))
                jobs[job_id]["files"] = [
                    {
                        "filename": f.name,
                        "size": f.stat().st_size,
                        "size_mb": round(f.stat().st_size / (1024 * 1024), 2),
                        "download_url": f"/instagram/download/file/{f.name}",
                        "media_type": "video" if f.suffix in [".mp4", ".webm"] else ("audio" if f.suffix in [".mp3", ".m4a"] else "image")
                    }
                    for f in downloaded_files
                ]
                jobs[job_id]["status"] = "completed"
                jobs[job_id]["title"] = info.get("title") or info.get("description", "")[:50]
            else:
                jobs[job_id]["status"] = "failed"
                jobs[job_id]["error"] = "Download failed - could not extract content"
                
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)


async def process_instagram_story_download(
    job_id: str,
    url: str,
    quality: str,
    output_format: str
):
    """Background task to process Instagram story download."""
    try:
        jobs[job_id]["status"] = "processing"
        
        file_id = str(uuid.uuid4())[:8]
        output_template = str(INSTAGRAM_DOWNLOAD_DIR / f"{file_id}_story_%(autonumber)s.%(ext)s")
        
        ydl_opts = get_instagram_ydl_opts(output_template, quality)
        
        def progress_hook(d):
            if d["status"] == "finished":
                jobs[job_id]["progress"] = min(jobs[job_id]["progress"] + 20, 90)
        
        ydl_opts["progress_hooks"] = [progress_hook]
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            
            if info:
                downloaded_files = list(INSTAGRAM_DOWNLOAD_DIR.glob(f"{file_id}_*"))
                
                if output_format == "zip" and len(downloaded_files) > 1:
                    zip_filename = f"{file_id}_stories.zip"
                    zip_path = INSTAGRAM_DOWNLOAD_DIR / zip_filename
                    
                    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                        for f in downloaded_files:
                            zipf.write(f, f.name)
                    
                    for f in downloaded_files:
                        f.unlink()
                    
                    jobs[job_id]["files"] = [{
                        "filename": zip_filename,
                        "size": zip_path.stat().st_size,
                        "size_mb": round(zip_path.stat().st_size / (1024 * 1024), 2),
                        "download_url": f"/instagram/download/file/{zip_filename}",
                        "media_type": "zip",
                        "stories_count": len(downloaded_files)
                    }]
                else:
                    jobs[job_id]["files"] = [
                        {
                            "filename": f.name,
                            "size": f.stat().st_size,
                            "size_mb": round(f.stat().st_size / (1024 * 1024), 2),
                            "download_url": f"/instagram/download/file/{f.name}",
                            "media_type": "video" if f.suffix in [".mp4", ".webm"] else "image"
                        }
                        for f in downloaded_files
                    ]
                
                jobs[job_id]["status"] = "completed"
                jobs[job_id]["progress"] = 100
            else:
                jobs[job_id]["status"] = "completed"
                jobs[job_id]["files"] = []
                jobs[job_id]["progress"] = 100
                jobs[job_id]["message"] = "No active stories found"
                
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)


async def process_instagram_carousel_download(
    job_id: str,
    url: str,
    quality: str,
    include_metadata: bool
):
    """Background task to process Instagram carousel download as ZIP."""
    try:
        jobs[job_id]["status"] = "processing"
        
        file_id = str(uuid.uuid4())[:8]
        output_template = str(INSTAGRAM_DOWNLOAD_DIR / f"{file_id}_%(autonumber)s.%(ext)s")
        
        ydl_opts = get_instagram_ydl_opts(output_template, quality)
        
        metadata = None
        
        with yt_dlp.YoutubeDL({"quiet": True}) as ydl:
            info = ydl.extract_info(url, download=False)
            if info:
                metadata = extract_instagram_post_info(info)
        
        jobs[job_id]["progress"] = 10
        
        def progress_hook(d):
            if d["status"] == "finished":
                jobs[job_id]["progress"] = min(jobs[job_id]["progress"] + 15, 85)
        
        ydl_opts["progress_hooks"] = [progress_hook]
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        downloaded_files = list(INSTAGRAM_DOWNLOAD_DIR.glob(f"{file_id}_*"))
        
        if downloaded_files:
            shortcode = extract_instagram_shortcode(url) or file_id
            zip_filename = f"{shortcode}_carousel.zip"
            zip_path = INSTAGRAM_DOWNLOAD_DIR / zip_filename
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for idx, f in enumerate(sorted(downloaded_files)):
                    new_name = f"item_{idx+1:02d}{f.suffix}"
                    zipf.write(f, new_name)
                
                if include_metadata and metadata:
                    import json
                    metadata_json = json.dumps(metadata, indent=2, ensure_ascii=False)
                    zipf.writestr("metadata.json", metadata_json)
            
            for f in downloaded_files:
                f.unlink()
            
            jobs[job_id]["files"] = [{
                "filename": zip_filename,
                "size": zip_path.stat().st_size,
                "size_mb": round(zip_path.stat().st_size / (1024 * 1024), 2),
                "download_url": f"/instagram/download/file/{zip_filename}",
                "media_type": "zip",
                "items_count": len(downloaded_files)
            }]
            jobs[job_id]["status"] = "completed"
            jobs[job_id]["progress"] = 100
        else:
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["error"] = "No files downloaded"
                
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)


async def process_instagram_batch_download(
    job_id: str,
    items: List[InstagramBatchItem],
    quality: str,
    continue_on_error: bool
):
    """Background task to process batch Instagram downloads."""
    try:
        jobs[job_id]["status"] = "processing"
        total = len(items)
        
        for idx, item in enumerate(items):
            try:
                if item.type == "reel":
                    normalized_url = normalize_instagram_reel_url(item.url)
                elif item.type == "story":
                    normalized_url = normalize_instagram_stories_url(item.url)
                else:
                    normalized_url = normalize_instagram_url(item.url)
                
                file_id = str(uuid.uuid4())[:8]
                output_template = str(INSTAGRAM_DOWNLOAD_DIR / f"{file_id}_%(title)s.%(ext)s")
                
                ydl_opts = get_instagram_ydl_opts(output_template, quality)
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(normalized_url, download=True)
                    
                    if info:
                        downloaded_files = list(INSTAGRAM_DOWNLOAD_DIR.glob(f"{file_id}_*"))
                        for f in downloaded_files:
                            jobs[job_id]["files"].append({
                                "filename": f.name,
                                "size": f.stat().st_size,
                                "size_mb": round(f.stat().st_size / (1024 * 1024), 2),
                                "download_url": f"/instagram/download/file/{f.name}",
                                "source_url": item.url,
                                "source_type": item.type,
                                "media_type": "video" if f.suffix in [".mp4", ".webm"] else "image"
                            })
                        jobs[job_id]["completed_count"] += 1
                        
            except Exception as e:
                jobs[job_id]["errors"].append({
                    "url": item.url,
                    "type": item.type,
                    "error": str(e)
                })
                if not continue_on_error:
                    raise
            
            jobs[job_id]["progress"] = int(((idx + 1) / total) * 100)
        
        jobs[job_id]["status"] = "completed"
        
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)


app.include_router(instagram_router)


app.mount("/ui", StaticFiles(directory="static", html=True), name="static")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown."""
    pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
