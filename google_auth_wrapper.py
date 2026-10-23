import datetime
import re
from collections import Counter, defaultdict
from urllib.parse import urlparse

import requests
from nest_video_api import NestDoorbellDevice

from tools import logger
import glocaltokens.client

class GLocalAuthenticationTokensMultiService(glocaltokens.client.GLocalAuthenticationTokens):
    def __init__(self, *args, **kwargs) -> None:
        super(GLocalAuthenticationTokensMultiService, self).__init__(*args, **kwargs)

        self._last_access_token_service = None
    
    def get_access_token(self, service=glocaltokens.client.ACCESS_TOKEN_SERVICE) -> str | None:
        """Return existing or fetch access_token"""
        if (
            self.access_token is None
            or self.access_token_date is None
            or self._has_expired(self.access_token_date, glocaltokens.client.ACCESS_TOKEN_DURATION)
            or self._last_access_token_service != service
        ):
            logger.debug(
                "There is no access_token stored, "
                "or it has expired, getting a new one..."
            )
            master_token = self.get_master_token()
            if master_token is None:
                logger.debug("Unable to obtain master token.")
                return None
            if self.username is None:
                logger.error("Username is not set.")
                return None
            res = glocaltokens.client.perform_oauth(
                self._escape_username(self.username),
                master_token,
                self.get_android_id(),
                app=glocaltokens.client.ACCESS_TOKEN_APP_NAME,
                service=service,
                client_sig=glocaltokens.client.ACCESS_TOKEN_CLIENT_SIGNATURE,
            )
            if "Auth" not in res:
                logger.error("[!] Could not get access token.")
                logger.debug("Request response: %s", res)
                return None
            self.access_token = res["Auth"]
            self.access_token_date = datetime.datetime.now()
            self._last_access_token_service = service
        logger.debug(
            "Access token: %s, datetime %s",
            glocaltokens.client.censor(self.access_token),
            self.access_token_date,
        )
        return self.access_token

class GoogleConnection(object):

    NAME = "Google"

    NEST_SCOPE = "oauth2:https://www.googleapis.com/auth/nest-account"
    GET_TRAITS_URI = (
        "https://googlehomefoyer-pa.clients6.google.com/$rpc/"
        "google.internal.home.foyer.v1.HomeControlService/GetTraits"
    )

    def __init__(self, master_token, username, password="FAKE_PASSWORD"):
        self._google_auth = GLocalAuthenticationTokensMultiService(
            master_token=master_token, 
            username=username, 
            password=password,
        )

    def make_nest_get_request(self, device_id : str, url : str, params={}):
        url = url.format(device_id=device_id)
        logger.debug(f"Sending request to: '{url}' with params: '{params}'")

        access_token = self._google_auth.get_access_token(service=GoogleConnection.NEST_SCOPE)
        if not access_token:
            raise Exception("Couldn't get a Nest access token")
        
        res = requests.get(
            url=url, 
            params=params, 
            headers={
                "Authorization": f"Bearer {access_token}"
            }
        )
        res.raise_for_status()
        return res.content

    def _get_google_home_traits(self, homegraph_device_id):
        access_token = self._google_auth.get_access_token()
        if not access_token:
            raise RuntimeError("Couldn't get a Google Home access token")

        response = requests.post(
            GoogleConnection.GET_TRAITS_URI,
            json=[[[homegraph_device_id]]],
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json+protobuf",
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _find_camera_backend_id(value):
        """Find the migrated DEVICE_ id embedded in a Google Home trait response."""
        if isinstance(value, str):
            parsed = urlparse(value)
            if (
                parsed.scheme == "https"
                and parsed.hostname == "nest-camera-frontend.googleapis.com"
                and "/dashmanifest/" in parsed.path
            ):
                match = re.search(r"/device/(DEVICE_[^/?]+)", parsed.path)
                if match:
                    return match.group(1)
            return None

        if isinstance(value, dict):
            values = value.values()
        elif isinstance(value, (list, tuple)):
            values = value
        else:
            return None

        for child in values:
            device_id = GoogleConnection._find_camera_backend_id(child)
            if device_id:
                return device_id
        return None

    def _resolve_camera_backend_id(self, device):
        original_id = device.device_info.agent_info.unique_id
        if original_id.startswith("DEVICE_"):
            return original_id, False

        try:
            traits = self._get_google_home_traits(device.device_info.device_id)
            backend_id = self._find_camera_backend_id(traits)
        except (requests.RequestException, RuntimeError, TypeError, ValueError) as error:
            logger.warning(
                "Could not resolve migrated camera '%s': %s",
                device.device_name,
                error,
            )
            return original_id, False

        if backend_id:
            logger.info(
                "Resolved migrated legacy camera '%s' to its Google Home backend",
                device.device_name,
            )
            return backend_id, True

        logger.warning(
            "Camera '%s' does not expose a migrated Google Home backend yet",
            device.device_name,
        )
        return original_id, False

    @staticmethod
    def _assign_storage_names(cameras):
        """Keep unique names unchanged and separate cameras that share a name."""
        name_counts = Counter(camera["name"] for camera in cameras)
        cameras_by_name = defaultdict(list)
        for camera in cameras:
            cameras_by_name[camera["name"]].append(camera)

        primary_ids = {}
        for name, same_name_cameras in cameras_by_name.items():
            direct_ids = sorted(
                camera["backend_id"]
                for camera in same_name_cameras
                if not camera["migrated"]
                and camera["backend_id"].startswith("DEVICE_")
            )
            all_ids = sorted(camera["backend_id"] for camera in same_name_cameras)
            primary_ids[name] = (direct_ids or all_ids)[0]

        for camera in cameras:
            storage_name = camera["name"]
            if (
                name_counts[camera["name"]] > 1
                and camera["backend_id"] != primary_ids[camera["name"]]
            ):
                storage_name += "_" + camera["backend_id"][-8:]
            camera["storage_name"] = storage_name

    def get_nest_camera_devices(self):

        homegraph_response = self._google_auth.get_homegraph()

        if homegraph_response is None:
            logger.error("Failed to get homegraph response. Check your master token and username and whether you've imported your config file appropriately.")
            raise Exception("Could not authenticate with Google. Your master token may be expired or invalid, or you might've not imported your config file appropriately.")

        cameras = []
        for device in homegraph_response.home.devices:
            if (
                "action.devices.traits.CameraStream" not in device.traits
                or "Nest" not in device.hardware.model
            ):
                continue

            backend_id, migrated = self._resolve_camera_backend_id(device)
            cameras.append(
                {
                    "backend_id": backend_id,
                    "migrated": migrated,
                    "name": device.device_name,
                }
            )

        self._assign_storage_names(cameras)
        return [
            NestDoorbellDevice(
                self,
                camera["backend_id"],
                camera["name"],
                storage_name=camera["storage_name"],
            )
            for camera in cameras
        ]
