from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Callable

from yt_dlp import DownloadError as YtDlpDownloadError
from yt_dlp import YoutubeDL

from .models import ALLOWED_QUALITIES, DownloadResult, ProbeResult, QualityOption
from .utils import extract_youtube_id


class YoutubeServiceError(RuntimeError):
    """Raised when probing or downloading a YouTube video fails."""


ProgressCallback = Callable[[float, str | None], None]


class YoutubeService:
    def __init__(self, storage_path: Path, ffmpeg_path: str) -> None:
        self.storage_path = storage_path
        self.ffmpeg_path = ffmpeg_path

    async def probe(self, url: str) -> ProbeResult:
        return await asyncio.to_thread(self._probe_sync, url)

    def _probe_sync(self, url: str) -> ProbeResult:
        opts = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "skip_download": True,
        }
        try:
            with YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
        except YtDlpDownloadError as exc:
            raise YoutubeServiceError(str(exc)) from exc

        if info is None:
            raise YoutubeServiceError("No metadata returned from source")

        if "entries" in info and info["entries"]:
            info = info["entries"][0]

        youtube_id = str(info.get("id") or extract_youtube_id(url) or "")
        if not youtube_id:
            raise YoutubeServiceError("Could not determine video id")

        title = str(info.get("title") or youtube_id)
        description = str(info.get("description") or "")
        thumbnail_url = info.get("thumbnail")
        duration = info.get("duration")
        if duration is not None:
            duration = int(duration)

        formats = info.get("formats") or []
        quality_map = self._build_quality_map(formats)

        return ProbeResult(
            youtube_id=youtube_id,
            url=url,
            title=title,
            description=description,
            thumbnail_url=thumbnail_url,
            duration_seconds=duration,
            qualities=quality_map,
        )

    def _build_quality_map(self, formats: list[dict]) -> dict[int, QualityOption]:
        quality_map: dict[int, QualityOption] = {}

        audio_candidates = [
            f
            for f in formats
            if f.get("vcodec") == "none" and f.get("acodec") not in (None, "none")
        ]
        best_audio = self._pick_best_audio(audio_candidates)

        for quality in ALLOWED_QUALITIES:
            progressive = [
                f
                for f in formats
                if int(f.get("height") or 0) == quality
                and f.get("vcodec") not in (None, "none")
                and f.get("acodec") not in (None, "none")
                and f.get("ext") in {"mp4", "mkv", "webm"}
            ]
            if progressive:
                chosen = self._pick_best(progressive)
                quality_map[quality] = QualityOption(
                    quality=quality,
                    format_id=str(chosen.get("format_id")),
                    requires_merge=False,
                    ext=str(chosen.get("ext") or "mp4"),
                    filesize_bytes=self._size_of(chosen),
                )
                continue

            adaptive_video = [
                f
                for f in formats
                if int(f.get("height") or 0) == quality
                and f.get("vcodec") not in (None, "none")
                and f.get("acodec") in (None, "none")
            ]
            if adaptive_video and best_audio:
                chosen_video = self._pick_best(adaptive_video)
                video_size = self._size_of(chosen_video)
                audio_size = self._size_of(best_audio)
                estimated = None
                if video_size is not None and audio_size is not None:
                    estimated = video_size + audio_size
                quality_map[quality] = QualityOption(
                    quality=quality,
                    format_id=str(chosen_video.get("format_id")),
                    requires_merge=True,
                    ext="mp4",
                    filesize_bytes=estimated,
                )

        return quality_map

    @staticmethod
    def _pick_best(candidates: list[dict]) -> dict:
        def score(fmt: dict) -> tuple[float, int]:
            vbr = float(fmt.get("tbr") or 0.0)
            size = int(fmt.get("filesize") or fmt.get("filesize_approx") or 0)
            return vbr, size

        return sorted(candidates, key=score, reverse=True)[0]

    @staticmethod
    def _pick_best_audio(candidates: list[dict]) -> dict | None:
        if not candidates:
            return None

        def score(fmt: dict) -> tuple[float, int]:
            abr = float(fmt.get("abr") or fmt.get("tbr") or 0.0)
            size = int(fmt.get("filesize") or fmt.get("filesize_approx") or 0)
            return abr, size

        return sorted(candidates, key=score, reverse=True)[0]

    @staticmethod
    def _size_of(fmt: dict) -> int | None:
        size = fmt.get("filesize") or fmt.get("filesize_approx")
        if size is None:
            return None
        return int(size)

    async def download(
        self,
        probe: ProbeResult,
        quality_option: QualityOption,
        progress_callback: ProgressCallback | None = None,
    ) -> DownloadResult:
        return await asyncio.to_thread(self._download_sync, probe, quality_option, progress_callback)

    def _download_sync(
        self,
        probe: ProbeResult,
        quality_option: QualityOption,
        progress_callback: ProgressCallback | None,
    ) -> DownloadResult:
        output_dir = self.storage_path / probe.youtube_id / str(quality_option.quality)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_template = (output_dir / f"{probe.youtube_id}_{quality_option.quality}.%(ext)s").as_posix()

        def hook(progress: dict) -> None:
            if progress_callback is None:
                return
            status = progress.get("status")
            if status != "downloading":
                return

            downloaded = float(progress.get("downloaded_bytes") or 0)
            total = float(progress.get("total_bytes") or progress.get("total_bytes_estimate") or 0)
            eta = progress.get("eta")
            percent = 0.0 if total <= 0 else (downloaded / total) * 100
            eta_text = None
            if eta is not None:
                eta_text = _format_eta(int(eta))
            progress_callback(percent, eta_text)

        if quality_option.requires_merge:
            format_selector = f"{quality_option.format_id}+bestaudio[acodec!=none]/bestaudio/best"
        else:
            format_selector = str(quality_option.format_id)

        opts = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "retries": 3,
            "fragment_retries": 3,
            "format": format_selector,
            "outtmpl": output_template,
            "overwrites": True,
            "merge_output_format": quality_option.ext,
            "ffmpeg_location": self.ffmpeg_path,
            "progress_hooks": [hook],
        }

        try:
            with YoutubeDL(opts) as ydl:
                ydl.extract_info(probe.url, download=True)
        except YtDlpDownloadError as exc:
            raise YoutubeServiceError(str(exc)) from exc

        downloaded_file = self._locate_downloaded_file(output_dir)
        if downloaded_file is None:
            raise YoutubeServiceError("Download finished but no output file found")

        file_size = downloaded_file.stat().st_size
        return DownloadResult(
            youtube_id=probe.youtube_id,
            quality=quality_option.quality,
            file_path=downloaded_file,
            file_size_bytes=file_size,
            title=probe.title,
            description=probe.description,
        )

    @staticmethod
    def _locate_downloaded_file(output_dir: Path) -> Path | None:
        candidates: list[Path] = []
        for pattern in ("*.mp4", "*.mkv", "*.webm"):
            candidates.extend(output_dir.glob(pattern))
        if not candidates:
            return None
        candidates.sort(key=lambda item: item.stat().st_mtime, reverse=True)
        return candidates[0]


def _format_eta(seconds: int) -> str:
    if seconds < 0:
        seconds = 0
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"