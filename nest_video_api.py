import pytz
import datetime
from models import CameraEvent

from tools import logger
import xml.etree.ElementTree as ET

class NestDoorbellDevice(object):

    NEST_API_DOMAIN = "https://nest-camera-frontend.googleapis.com"

    EVENTS_URI = NEST_API_DOMAIN + "/dashmanifest/namespace/nest-phoenix-prod/device/{device_id}"
    DOWNLOAD_VIDEO_URI = NEST_API_DOMAIN + "/mp4clip/namespace/nest-phoenix-prod/device/{device_id}"

    def __init__(self, google_auth_connection, device_id, device_name):
        self._connection = google_auth_connection
        self._device_id = device_id
        self._device_name = device_name

    def __parse_events(self, events_xml):
        root = ET.fromstring(events_xml)
        # logger.info(events_xml)
        periods = root.findall(".//{urn:mpeg:dash:schema:mpd:2011}Period")
        return [
            CameraEvent.from_attrib(period.attrib, self) for period in periods
        ]

    def __download_event_by_time(self, start_time, end_time):
        params = {
            "start_time" : int(start_time.timestamp()*1000), # 1707368737876
            "end_time" : int(end_time.timestamp()*1000), # 1707368757371
        }
        return self._connection.make_nest_get_request(
            self._device_id,
            NestDoorbellDevice.DOWNLOAD_VIDEO_URI, 
            params=params
        )
    
    @property
    def device_id(self):
        return self._device_id

    @property
    def device_name(self):
        return self._device_name

    def get_events(self, end_time: datetime.datetime, duration_minutes: int):
        start_time = end_time - datetime.timedelta(minutes=duration_minutes)
        params = {
            "start_time" : start_time.astimezone(pytz.timezone("UTC")).isoformat()[:-9]+"Z", # 2024-02-07T19:32:25.250Z
            "end_time" : end_time.astimezone(pytz.timezone("UTC")).isoformat()[:-9]+"Z", # 2024-02-08T19:32:25.250Z
            "types": 4, 
            "variant" : 2,
        }
        logger.info (params)
        return self.__parse_events(
            self._connection.make_nest_get_request(
                self._device_id,
                NestDoorbellDevice.EVENTS_URI, 
                params=params
            )
        )
        
    def download_camera_event(self, camera_event : CameraEvent):
        return self.__download_event_by_time(
            camera_event.start_time,
            camera_event.end_time
        ) 
