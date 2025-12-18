"""
Cleanup mechanism for tmp folder - deletes files older than 30 minutes
"""

import os
import time
import threading
from pathlib import Path
from datetime import datetime, timedelta

# Configuration
TMP_DIR = Path("tmp")
CLEANUP_INTERVAL_MINUTES = 5  # Check every 5 minutes
FILE_RETENTION_MINUTES = 30

def cleanup_old_files():
    """Remove files older than FILE_RETENTION_MINUTES from tmp directory."""
    try:
        now = datetime.now()
        cutoff_time = now - timedelta(minutes=FILE_RETENTION_MINUTES)

        if not TMP_DIR.exists():
            return

        # Walk through all files in tmp directory recursively
        for file_path in TMP_DIR.rglob('*'):
            if file_path.is_file():
                # Check if file is older than cutoff
                file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                if file_mtime < cutoff_time:
                    try:
                        file_path.unlink()
                        print(f"Deleted old file: {file_path}")
                    except Exception as e:
                        print(f"Error deleting {file_path}: {e}")

        # Clean up empty directories
        for dir_path in TMP_DIR.rglob('*'):
            if dir_path.is_dir() and not any(dir_path.iterdir()):
                try:
                    dir_path.rmdir()
                    print(f"Deleted empty directory: {dir_path}")
                except Exception as e:
                    print(f"Error deleting directory {dir_path}: {e}")

    except Exception as e:
        print(f"Error during cleanup: {e}")

def cleanup_loop():
    """Run cleanup in a loop every CLEANUP_INTERVAL_MINUTES."""
    while True:
        cleanup_old_files()
        time.sleep(CLEANUP_INTERVAL_MINUTES * 60)

def start_cleanup_thread():
    """Start the cleanup thread."""
    cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
    cleanup_thread.start()
    print("Cleanup thread started")

if __name__ == "__main__":
    # Run cleanup once and then start the loop
    cleanup_old_files()
    cleanup_loop()