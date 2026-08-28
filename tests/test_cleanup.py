import datetime
import os
from pathlib import Path
import tempfile
import unittest

import cleanup


MIB = 1024 * 1024


def set_file_age(path: Path, days: int) -> None:
    timestamp = (datetime.datetime.now() - datetime.timedelta(days=days)).timestamp()
    os.utime(path, (timestamp, timestamp))


class CleanupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.original_base_directory = cleanup.BASE_DIRECTORY
        self.addCleanup(
            setattr, cleanup, "BASE_DIRECTORY", self.original_base_directory
        )
        cleanup.BASE_DIRECTORY = self.temporary_directory.name

    def test_zero_max_age_preserves_old_file_below_size_limit(self) -> None:
        old_file = Path(self.temporary_directory.name) / "old.mp4"
        old_file.write_bytes(b"a" * 10)
        set_file_age(old_file, 365)

        cleanup.cleanup_old_videos(max_age_days=0, max_size_mb=1000)

        self.assertTrue(old_file.exists())

    def test_size_limit_deletes_oldest_file_only(self) -> None:
        oldest_file = Path(self.temporary_directory.name) / "oldest.mp4"
        newest_file = Path(self.temporary_directory.name) / "newest.mp4"
        oldest_file.write_bytes(b"a" * 10)
        newest_file.write_bytes(b"b" * 20)
        set_file_age(oldest_file, 2)
        set_file_age(newest_file, 1)

        cleanup.cleanup_old_videos(max_age_days=0, max_size_mb=25 / MIB)

        self.assertFalse(oldest_file.exists())
        self.assertTrue(newest_file.exists())

    def test_positive_max_age_still_deletes_expired_file(self) -> None:
        old_file = Path(self.temporary_directory.name) / "old.mp4"
        old_file.write_bytes(b"a" * 10)
        set_file_age(old_file, 365)

        cleanup.cleanup_old_videos(max_age_days=60, max_size_mb=1000)

        self.assertFalse(old_file.exists())


if __name__ == "__main__":
    unittest.main()
