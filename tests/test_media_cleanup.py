from pathlib import Path

from ytdl_bot.media import remove_file_and_empty_parents, upload_size_looks_valid


def test_upload_size_verification_with_tolerance() -> None:
    local_size = 100 * 1024 * 1024
    assert upload_size_looks_valid(local_size, local_size - 1024 * 1024) is True
    assert upload_size_looks_valid(local_size, local_size + 20 * 1024 * 1024) is False


def test_remove_file_and_empty_parents(tmp_path: Path) -> None:
    stop_dir = tmp_path / "downloads"
    target_dir = stop_dir / "abc" / "720"
    target_dir.mkdir(parents=True, exist_ok=True)
    media_file = target_dir / "video.mp4"
    media_file.write_bytes(b"data")

    remove_file_and_empty_parents(media_file, stop_at=stop_dir)

    assert not media_file.exists()
    assert not target_dir.exists()
    assert not (stop_dir / "abc").exists()
    assert stop_dir.exists()
