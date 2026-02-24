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

    config = configparser.ConfigParser()
    config['nest'] = {
        'timezone': '',
        'refresh_interval': '',
        'google_username': '',
        'google_master_token': ''
    }
    with open(config_path, 'w') as configfile:
        config.write(configfile)

config = configparser.ConfigParser()
config.read(config_path)


def strip_inline_comment(value):
    """Strip inline comments (# or ;) from config values.

    Only strips comments preceded by whitespace to avoid truncating
    values that legitimately contain # or ; (like master tokens).
    """
    for prefix in (' #', ' ;', '\t#', '\t;'):
        if prefix in value:
            value = value.split(prefix)[0]
    return value.strip()


# Keys that are optional and have defaults
OPTIONAL_KEYS = {'fetch_range'}
# Keys that contain sensitive values -- do NOT put these in os.environ
SENSITIVE_KEYS = {'google_master_token', 'google_username'}

# Store sensitive values separately, only push non-sensitive config to env
_sensitive_config = {}

if 'nest' in config:
    for key, value in config['nest'].items():
        value = strip_inline_comment(value)
        if not value and key.lower() not in OPTIONAL_KEYS:
            logger.error(f"The value for {key} in the [nest] section is empty")
            sys.exit(1)
        if value:
            if key.lower() in SENSITIVE_KEYS:
                _sensitive_config[key.upper()] = value
            else:
                os.environ[key.upper()] = value
else:
    logger.error("The [nest] section does not exist in the config file provided")
    sys.exit(1)

GOOGLE_MASTER_TOKEN = _sensitive_config.get("GOOGLE_MASTER_TOKEN")
GOOGLE_USERNAME = _sensitive_config.get("GOOGLE_USERNAME")
REFRESH_INTERVAL = int(os.environ.get("REFRESH_INTERVAL", 60))
TIMEZONE = os.environ.get("TIMEZONE", "America/Los_Angeles")
FETCH_RANGE = int(os.environ.get("FETCH_RANGE", 240))

if not GOOGLE_MASTER_TOKEN or not GOOGLE_USERNAME:
    logger.error("google_master_token and google_username must be set in the config file")
    sys.exit(1)

# Log loaded configuration (mask sensitive values)
logger.info("Configuration loaded:")
logger.info(f"  timezone: {TIMEZONE}")
logger.info(f"  refresh_interval: {REFRESH_INTERVAL} minutes")
logger.info(f"  fetch_range: {FETCH_RANGE} minutes")
username_parts = GOOGLE_USERNAME.split('@')
logger.info(f"  google_username: {username_parts[0][:3]}***@{username_parts[1]}")
logger.info(f"  google_master_token: [loaded, length={len(GOOGLE_MASTER_TOKEN)}]")


def main():

    logger.info("Welcome to the Google Nest Doorbell Local Storage Downloader")

    logger.info("Initializing the Google connection")
    google_connection = GoogleConnection(GOOGLE_MASTER_TOKEN, GOOGLE_USERNAME)

    logger.info("Getting Camera Devices")
    nest_camera_devices = google_connection.get_nest_camera_devices()
    logger.info(f"Found {len(nest_camera_devices)} Camera Device{'s' if len(nest_camera_devices) > 1 else ''}")
    des = DataEventsSync(
        nest_camera_devices=nest_camera_devices
    )

    logger.info("Initialized a Data Syncer")

    consecutive_failures = 0

    def sync_schedule():
        nonlocal consecutive_failures
        try:
            des.sync()
            consecutive_failures = 0
        except Exception as e:
            consecutive_failures += 1
            logger.error(f"Sync failed (attempt #{consecutive_failures}): {e}", exc_info=True)
            if consecutive_failures >= 3:
                logger.critical(
                    f"Sync has failed {consecutive_failures} consecutive times. "
                    "Check your master token and network connectivity."
                )

    # Create an event loop explicitly
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Schedule the job to run every x minutes
    scheduler = AsyncIOScheduler(event_loop=loop)
    scheduler.add_job(
        sync_schedule,
        'interval',
        minutes=REFRESH_INTERVAL,
        next_run_time=datetime.datetime.now() + datetime.timedelta(seconds=10)
    )
    scheduler.start()

    try:
        loop.run_forever()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down gracefully...")
    finally:
        scheduler.shutdown(wait=False)
        loop.close()


if __name__ == "__main__":
    main()
