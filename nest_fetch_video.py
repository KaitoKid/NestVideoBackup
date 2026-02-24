from nest_video_api import NestDoorbellDevice
from tools import logger
from models import CameraEvent

import pytz
import datetime
import os

# Get the PUID and PGID environment variables for file ownership
PUID = int(os.environ.get('PUID', 1000))
PGID = int(os.environ.get('PGID', 1000))

BASE_DIRECTORY = "/videos"

# Minimum valid MP4 size (ftyp box header = 8 bytes minimum)
MIN_MP4_SIZE = 8


def get_timezone():
    """Get timezone at runtime to ensure config is loaded."""
    return os.environ.get("TIMEZONE", "America/Los_Angeles")


def get_fetch_range():
    """Get fetch range at runtime to ensure config is loaded."""
    return int(os.environ.get("FETCH_RANGE", 240))


def validate_mp4(data: bytes) -> bool:
    """Check that downloaded data looks like a valid MP4 file.

    Validates the presence of the 'ftyp' box which must appear
    at the start of any valid MP4/ISO base media file.
    """
    if not data or len(data) < MIN_MP4_SIZE:
        return False
    return data[4:8] == b'ftyp'


def set_file_ownership(path: str):
    """Set file ownership to configured PUID/PGID. Silently fails if not permitted."""
    try:
        os.chown(path, PUID, PGID)
    except (OSError, PermissionError):
        pass  # Non-root containers won't be able to chown; that's fine


class DataEventsSync(object):

    def __init__(self, nest_camera_devices) -> None:
        self._nest_camera_devices = nest_camera_devices
        self._recent_events = set()

    def sync_single_nest_camera(self, nest_device: NestDoorbellDevice):

        logger.info(f"Syncing: {nest_device.device_id}")
        if "DEVICE_" not in nest_device.device_id:
            logger.info(f"{nest_device.device_id} does not look like a gen 2 Nest Doorbell, skipping...")
            return

        all_recent_camera_events: list[CameraEvent] = nest_device.get_events(
            end_time=datetime.datetime.now(tz=datetime.timezone.utc),
            duration_minutes=get_fetch_range()
        )

        # Create the directory to store videos on a per-day and per-device basis
        tz = get_timezone()
        today = datetime.datetime.now(tz=datetime.timezone.utc).astimezone(pytz.timezone(tz))
        year = str(today.year)
        month = str(today.month).zfill(2)
        day = str(today.day).zfill(2)
        directory = os.path.join(BASE_DIRECTORY, nest_device.device_name, year, month, day)
        os.makedirs(directory, exist_ok=True)
        set_file_ownership(directory)

        logger.info(f"[{nest_device.device_id}] Received {len(all_recent_camera_events)} camera events")

        skipped = 0
        errors = 0
        for camera_event_obj in all_recent_camera_events:
            file_name = (
                nest_device.device_name + "_"
                + camera_event_obj.start_time.astimezone(pytz.timezone(tz)).strftime("%Y-%m-%d_%I-%M-%S%p")
                + ".mp4"
            )
            final_path = os.path.join(directory, file_name)

            # Check if file has been previously downloaded
            if os.path.exists(final_path):
                logger.debug(f"CameraEvent ({camera_event_obj}) already exists, skipping..")
                skipped += 1
                continue

            logger.debug(f"Downloading camera event: {camera_event_obj}")
            try:
                video_data = nest_device.download_camera_event(camera_event_obj)
            except Exception as e:
                logger.error(f"Failed to download event {camera_event_obj.event_id}: {e}")
                errors += 1
                continue

            # Validate the downloaded data is actually an MP4
            if not validate_mp4(video_data):
                logger.warning(
                    f"Invalid MP4 data for {camera_event_obj.event_id} "
                    f"(size={len(video_data) if video_data else 0}), skipping"
                )
                errors += 1
                continue

            # Atomic write: write to temp file, then rename
            # Prevents corrupt files from interrupted writes
            temp_path = final_path + '.downloading'
            try:
                with open(temp_path, "wb") as f:
                    f.write(video_data)
                os.rename(temp_path, final_path)
                set_file_ownership(final_path)
            except Exception as e:
                logger.error(f"Failed to write {file_name}: {e}")
                # Clean up partial temp file
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                errors += 1
                continue

            logger.info(f"Saved {file_name} successfully ({len(video_data)} bytes)")
            self._recent_events.add(camera_event_obj.event_id)

        downloaded = len(all_recent_camera_events) - skipped - errors
        logger.info(
            f"[{nest_device.device_id}] Downloaded: {downloaded}, "
            f"skipped: {skipped}, errors: {errors}"
        )

    def sync(self):
        logger.info("Syncing all camera devices")
        for nest_device in self._nest_camera_devices:
            self.sync_single_nest_camera(nest_device)
