import os
import datetime
from tools import logger

BASE_DIRECTORY = "/videos"


def get_all_video_files() -> list[tuple[str, float, datetime.datetime]]:
    """
    Walk the /videos directory and return a list of (filepath, size_bytes, modified_time)
    sorted oldest first.

    Directory structure: /videos/{device_name}/{year}/{month}/{day}/{filename}.mp4
    """
    files = []
    for root, dirs, filenames in os.walk(BASE_DIRECTORY):
        for filename in filenames:
            if not filename.endswith(".mp4"):
                continue
            filepath = os.path.join(root, filename)
            try:
                stat = os.stat(filepath)
                size = stat.st_size
                mtime = datetime.datetime.fromtimestamp(stat.st_mtime)
                files.append((filepath, size, mtime))
            except OSError as e:
                logger.warning(f"Could not stat file {filepath}: {e}")

    # Sort oldest first so we delete oldest when enforcing limits
    files.sort(key=lambda x: x[2])
    return files


def get_total_size(files: list[tuple[str, float, datetime.datetime]]) -> int:
    return sum(size for _, size, _ in files)


def cleanup_old_videos(max_age_days: int = 60, max_size_mb: float = 250000):
    """
    Delete videos that are either:
      - Older than max_age_days days, OR
      - Causing total storage to exceed max_size_mb MB (oldest deleted first)
    """
    max_size_bytes = max_size_mb * 1024 ** 2

    logger.info(f"Running cleanup (max age: {max_age_days} days, max size: {max_size_mb} MB)...")

    files = get_all_video_files()
    if not files:
        logger.info("Cleanup: no video files found, nothing to do.")
        return

    total_size = get_total_size(files)
    now = datetime.datetime.now()
    cutoff_date = now - datetime.timedelta(days=max_age_days)

    deleted_count = 0
    deleted_bytes = 0

    for filepath, size, mtime in files:
        deleted = False

        # Rule 1: delete if older than max_age_days
        if mtime < cutoff_date:
            reason = f"older than {max_age_days} days (modified {mtime.strftime('%Y-%m-%d')})"
            deleted = True

        # Rule 2: delete oldest files if still over size limit
        elif total_size > max_size_bytes:
            reason = (
                f"storage limit exceeded "
                f"({total_size / 1024**2:.2f} MB > {max_size_mb} MB)"
            )
            deleted = True

        if deleted:
            try:
                os.remove(filepath)
                total_size -= size
                deleted_count += 1
                deleted_bytes += size
                logger.info(f"Cleanup: deleted {filepath} — {reason}")
                _remove_empty_dirs(os.path.dirname(filepath))
            except OSError as e:
                logger.warning(f"Cleanup: could not delete {filepath}: {e}")

    if deleted_count == 0:
        logger.info(
            f"Cleanup: nothing to delete. "
            f"Total size: {total_size / 1024**2:.2f} MB, "
            f"oldest file: {files[0][2].strftime('%Y-%m-%d') if files else 'N/A'}"
        )
    else:
        logger.info(
            f"Cleanup complete: deleted {deleted_count} file(s), "
            f"freed {deleted_bytes / 1024**2:.2f} MB. "
            f"Remaining: {total_size / 1024**2:.2f} MB"
        )


def _remove_empty_dirs(directory: str):
    """Recursively remove empty directories up to (but not including) BASE_DIRECTORY."""
    while directory and directory != BASE_DIRECTORY:
        if os.path.isdir(directory) and not os.listdir(directory):
            try:
                os.rmdir(directory)
                logger.debug(f"Cleanup: removed empty directory {directory}")
            except OSError:
                break
        else:
            break
        directory = os.path.dirname(directory)