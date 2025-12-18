"""
YouTube Downloader API - Production-Ready FastAPI Backend
Powered by yt-dlp for video/audio extraction and downloading.

LEGAL DISCLAIMER:
This tool is for personal, educational use only. Downloading copyrighted content
may violate YouTube's Terms of Service and copyright laws in your jurisdiction.
Use responsibly and only for content you have rights to download.
"""

import os
import uuid
import asyncio
import time
import shutil
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path
from collections import defaultdict

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks, Request
from fastapi.responses import FileResponse, StreamingResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import yt_dlp
import aiofiles


DOWNLOAD_DIR = Path("tmp/downloads")
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

CLEANUP_TIMEOUT_MINUTES = 30
MAX_REQUESTS_PER_MINUTE = 30

app = FastAPI(
    title="YouTube Downloader API",
    description="A production-ready API for downloading YouTube videos, audio, subtitles, and thumbnails.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

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


app.mount("/ui", StaticFiles(directory="static", html=True), name="static")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown."""
    pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
