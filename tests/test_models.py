import datetime
import unittest

from models import CameraEvent


class CameraEventTests(unittest.TestCase):
    def test_event_longer_than_a_minute_keeps_its_full_length(self) -> None:
        event = CameraEvent.from_attrib(
            {"programDateTime": "2026-10-01T11:04:02.240Z", "duration": "PT1M35.5S"}, nest_device=None
        )

        self.assertEqual(event.duration, datetime.timedelta(seconds=95.5))
        self.assertEqual(event.end_time - event.start_time, datetime.timedelta(seconds=95.5))


if __name__ == "__main__":
    unittest.main()
