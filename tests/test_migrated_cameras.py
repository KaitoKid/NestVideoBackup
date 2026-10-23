import datetime
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest import mock

import pytz

import google_auth_wrapper
import nest_fetch_video
from google_auth_wrapper import GoogleConnection
from nest_fetch_video import DataEventsSync


def make_homegraph_device(name, unique_id, homegraph_id):
    return SimpleNamespace(
        device_name=name,
        traits=["action.devices.traits.CameraStream"],
        hardware=SimpleNamespace(model="Nest Doorbell"),
        device_info=SimpleNamespace(
            device_id=homegraph_id,
            agent_info=SimpleNamespace(unique_id=unique_id),
        ),
    )


class MigratedCameraTests(unittest.TestCase):
    def setUp(self):
        self.connection = GoogleConnection.__new__(GoogleConnection)
        self.connection._google_auth = mock.Mock()

    def test_migrated_camera_uses_backend_id_and_separate_storage_name(self):
        direct_id = "DEVICE_1111111111111111"
        migrated_id = "DEVICE_22222222DEADBEEF"
        direct = make_homegraph_device("Front Door", direct_id, "direct-uuid")
        legacy = make_homegraph_device(
            "Front Door", "legacy-nest-device-id", "legacy-uuid"
        )
        self.connection._google_auth.get_homegraph.return_value = SimpleNamespace(
            home=SimpleNamespace(devices=[direct, legacy])
        )
        self.connection._google_auth.get_access_token.return_value = "access-token"
        response = mock.Mock()
        response.json.return_value = [
            [
                "cameraStream",
                {
                    "mpegdash": (
                        "https://nest-camera-frontend.googleapis.com/"
                        "dashmanifest/namespace/nest-phoenix-prod/device/"
                        f"{migrated_id}?auth=temporary"
                    )
                },
            ]
        ]
        response.raise_for_status.return_value = None

        with mock.patch.object(
            google_auth_wrapper.requests, "post", return_value=response
        ) as post:
            cameras = self.connection.get_nest_camera_devices()

        self.assertEqual([camera.device_id for camera in cameras], [direct_id, migrated_id])
        self.assertEqual(
            [camera.storage_name for camera in cameras],
            ["Front Door", "Front Door_DEADBEEF"],
        )
        post.assert_called_once_with(
            GoogleConnection.GET_TRAITS_URI,
            json=[[['legacy-uuid']]],
            headers={
                "Authorization": "Bearer access-token",
                "Content-Type": "application/json+protobuf",
            },
            timeout=30,
        )

    def test_unique_camera_name_keeps_existing_storage_layout(self):
        camera_id = "DEVICE_1111111111111111"
        device = make_homegraph_device("Back Door", camera_id, "camera-uuid")
        self.connection._google_auth.get_homegraph.return_value = SimpleNamespace(
            home=SimpleNamespace(devices=[device])
        )

        cameras = self.connection.get_nest_camera_devices()

        self.assertEqual(cameras[0].storage_name, "Back Door")

    def test_untrusted_urls_are_not_treated_as_camera_backend_ids(self):
        values = [
            "http://nest-camera-frontend.googleapis.com/dashmanifest/device/DEVICE_BAD",
            "https://example.com/dashmanifest/device/DEVICE_BAD",
            "https://nest-camera-frontend.googleapis.com/mp4clip/device/DEVICE_BAD",
        ]

        self.assertIsNone(GoogleConnection._find_camera_backend_id(values))


class CameraStorageTests(unittest.TestCase):
    def test_sync_uses_storage_name_for_directory_and_filename(self):
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        camera = mock.Mock()
        camera.device_id = "DEVICE_22222222DEADBEEF"
        camera.device_name = "Front Door"
        camera.storage_name = "Front Door_DEADBEEF"
        event = SimpleNamespace(
            event_id="event-1",
            start_time=datetime.datetime(2026, 8, 28, 7, 30, tzinfo=pytz.utc),
        )
        camera.get_events.return_value = [event]
        camera.download_camera_event.return_value = b"video-data"

        with (
            mock.patch.object(
                nest_fetch_video, "BASE_DIRECTORY", temporary_directory.name
            ),
            mock.patch.object(nest_fetch_video, "get_timezone", return_value="UTC"),
        ):
            DataEventsSync([camera]).sync_single_nest_camera(camera)

        files = list(Path(temporary_directory.name).rglob("*.mp4"))
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].parent.parent.parent.parent.name, "Front Door_DEADBEEF")
        self.assertTrue(files[0].name.startswith("Front Door_DEADBEEF_"))
        self.assertEqual(files[0].read_bytes(), b"video-data")


if __name__ == "__main__":
    unittest.main()
