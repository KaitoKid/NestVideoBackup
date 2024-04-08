from tools import logger
from google_auth_wrapper import GoogleConnection
from nest_fetch_video import DataEventsSync

import os
import sys
import datetime
import asyncio
import configparser
from apscheduler.schedulers.asyncio import AsyncIOScheduler

config_path = "/config/nest.ini"
if not os.path.exists(config_path):
    logger.info("No .ini file detected, creating one with empty values")

    # Create the config file with empty values
    config = configparser.ConfigParser()
    config['nest'] = {
        'TIMEZONE': '',
        'REFRESH_INTERVAL': '',
        'GOOGLE_USERNAME': '',
        'GOOGLE_MASTER_TOKEN': ''
    }
    with open(config_path, 'w') as configfile:
        config.write(configfile)

config = configparser.ConfigParser()
config.read(config_path)

if 'nest' in config:
    for key, value in config['nest'].items():
        if not value:
            logger.error(f"The value for {key} in the [nest] section is empty")
            sys.exit(1)
        os.environ[key.upper()] = value
else:
    logger.error("The [nest] section does not exist in the config file provided")
    sys.exit(1)

GOOGLE_MASTER_TOKEN = os.environ.get("GOOGLE_MASTER_TOKEN")
GOOGLE_USERNAME = os.environ.get("GOOGLE_USERNAME")
REFRESH_INTERVAL=int(os.environ.get("REFRESH_INTERVAL", 60))
LOCAL_TIMEZONE = os.environ.get("TIMEZONE", "America/Los_Angeles")

assert GOOGLE_MASTER_TOKEN and GOOGLE_USERNAME 

def main():

    logger.info("Welcome to the Google Nest Doorbell Local Storage Downloader")

    logger.info("Initializing the Google connection using the master_token")
    google_connection = GoogleConnection(GOOGLE_MASTER_TOKEN, GOOGLE_USERNAME)

    logger.info("Getting Camera Devices")
    nest_camera_devices = google_connection.get_nest_camera_devices()
    logger.info(f"Found {len(nest_camera_devices)} Camera Device{'s' if len(nest_camera_devices) > 1 else ''}")
    des = DataEventsSync(
            nest_camera_devices=nest_camera_devices
        )

    logger.info("Initialized a Data Syncer")

    def sync_schedule():
        try:
            des.sync()
        except Exception as e:
            logger.info(f"An error occurred: {e}")

    # Schedule the job to run every x minutes
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        sync_schedule, 
        'interval', 
        minutes=REFRESH_INTERVAL, 
        next_run_time=datetime.datetime.now() + datetime.timedelta(seconds=10)
    )
    scheduler.start()

    try:
        asyncio.get_event_loop().run_forever()
    except (KeyboardInterrupt, SystemExit):
        pass

if __name__ == "__main__":
    main()
