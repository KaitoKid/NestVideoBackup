import datetime
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import nest_fetch_video
from models import CameraEvent


class FakeDevice:
    device_id = "DEVICE_TEST"
    device_name = "Doorbell"

    def __init__(self, start_time):
        self.event = CameraEvent(device=self, start_time=start_time, duration=datetime.timedelta(seconds=15))
        self.downloads = 0

    def get_events(self, end_time, duration_minutes):
        return [self.event]

    def download_camera_event(self, event):
        self.downloads += 1
        return b"video"


class SyncTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        for patcher in (
            mock.patch.object(nest_fetch_video, "BASE_DIRECTORY", self.temporary_directory.name),
            mock.patch.dict(os.environ, {"TIMEZONE": "Europe/Dublin"}),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_clip_from_before_midnight_is_not_downloaded_again_after_midnight(self) -> None:
        late_evening = datetime.datetime(2026, 9, 22, 21, 33, 48, tzinfo=datetime.timezone.utc)
        device = FakeDevice(late_evening)
        sync = nest_fetch_video.DataEventsSync(nest_camera_devices=[device])

        with mock.patch.object(nest_fetch_video.datetime, "datetime", wraps=datetime.datetime) as clock:
            clock.now.return_value = datetime.datetime(2026, 9, 22, 21, 38)  # 22:38 in Dublin
            sync.sync_single_nest_camera(device)
            clock.now.return_value = datetime.datetime(2026, 9, 22, 23, 38)  # 00:38 the next day
            sync.sync_single_nest_camera(device)

        self.assertEqual(device.downloads, 1)
        saved = [str(p.relative_to(self.temporary_directory.name)) for p in Path(self.temporary_directory.name).rglob("*.mp4")]
        self.assertEqual(saved, ["Doorbell/2026/09/22/Doorbell_2026-09-22_10-33-48PM.mp4"])


if __name__ == "__main__":
    unittest.main()
