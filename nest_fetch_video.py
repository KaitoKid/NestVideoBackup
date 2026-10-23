from nest_video_api import NestDoorbellDevice
from tools import logger
from models import CameraEvent

from io import BytesIO
import pytz
import datetime
import os

# Get the PUID and PGID environment variables
PUID = int(os.environ.get('PUID', 1000))
PGID = int(os.environ.get('PGID', 1000))

BASE_DIRECTORY = "/videos"

def get_timezone():
    """Get timezone at runtime to ensure config is loaded."""
    return os.environ.get("TIMEZONE", "America/Los_Angeles")

def get_fetch_range():
    """Get fetch range at runtime to ensure config is loaded."""
    return int(os.environ.get("FETCH_RANGE", 240))

class DataEventsSync(object):

    def __init__(self, nest_camera_devices) -> None:
        self._nest_camera_devices = nest_camera_devices
        self._recent_events = set()

    def sync_single_nest_camera(self, nest_device : NestDoorbellDevice):

        logger.info(f"Syncing: {nest_device.device_id}")
        if "DEVICE_" not in nest_device.device_id:
            # I only have a Gen 2 Nest Doorbell - have not tested other doorbells yet
            logger.info(f"{nest_device.device_id} does not look like a gen 2 Nest Doorbell, skipping...")
            return
        all_recent_camera_events : list[CameraEvent] = nest_device.get_events(
            end_time = datetime.datetime.now(),
            duration_minutes=get_fetch_range()
        )

        tz = get_timezone()

        logger.info(f"[{nest_device.device_id}] Received {len(all_recent_camera_events)} camera events")

        skipped = 0
        for camera_event_obj in all_recent_camera_events:
            local_start = camera_event_obj.start_time.astimezone(pytz.timezone(tz))
            # Filing by today's date made the check below miss clips from before
            # midnight that were still inside the fetch range, so they downloaded again.
            directory = os.path.join(BASE_DIRECTORY, nest_device.device_name, local_start.strftime("%Y/%m/%d"))
            os.makedirs(directory, exist_ok=True)
            file_name = nest_device.device_name + "_" + local_start.strftime("%Y-%m-%d_%I-%M-%S%p") + ".mp4"

            # Check if file has been previously downloaded
            if os.path.exists(os.path.join(directory, file_name)):
                logger.debug(f"CameraEvent ({camera_event_obj}) already sent, skipping..")
                skipped += 1
                continue

            logger.debug(f"Downloading camera event: {camera_event_obj}")
            video_data = nest_device.download_camera_event(camera_event_obj)
            video_io = BytesIO(video_data)

            with open(os.path.join(directory, file_name), "wb") as file:
                file.write(video_io.getvalue())

            logger.info("Saved " + file_name + " successfully")

            self._recent_events.add(camera_event_obj.event_id)

        downloaded = len(all_recent_camera_events) - skipped
        logger.info(f"[{nest_device.device_id}] Downloaded: {downloaded}, skipped (already downloaded): {skipped}")

    def sync(self):
        logger.info("Syncing all camera devices")
        for nest_device in self._nest_camera_devices:
            self.sync_single_nest_camera(nest_device)
