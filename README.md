# Google Nest Camera Video - Sync To Storage

I wanted an easy way to store my Nest event history to my local NAS and store more than 60 days of footage. This module is for personal use only, especially as it uses unpublished APIs. Use it at your own risk!

## Requirements

- Python 3.10+ (or use the provided Docker image)
- Docker & Docker Compose (recommended)

## How It Works
1. Gets your **Google Home devices using HomeGraph**
2. Retrieves your recent **Google Nest events**
3. **Downloads full-quality Google Nest video clips**
4. Stores those clips to a local storage directory by `device_name` and into subdirectories with the format `YYYY/MM/DD/*.mp4`

## Setup

### 1. Obtain a Google Master Token

Run the following command to get your master token:
```bash
docker run --rm -it breph/ha-google-home_get-token
```

You can use an app password generated from [Google App Passwords](https://myaccount.google.com/apppasswords). Make sure you've generated it on the account that has your Nest cameras.

### 2. Create the Configuration File

Create a folder on your system for the config (e.g., `/path/to/config`), then create a `nest.ini` file inside it:

```ini
[nest]
# Your local timezone for video filenames
# See: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
timezone = America/Los_Angeles

# How often to fetch new video data (in minutes)
refresh_interval = 60

# How many minutes of video history to fetch each sync (optional, default: 240)
# Recommended: 240 for free Nest Aware (3 hr history + 1 hr buffer)
fetch_range = 240

# Your Google account email
google_username = youremail@gmail.com

# The master token from step 1
google_master_token = YOUR_MASTER_TOKEN_HERE
```

A sample config is provided in `config/sample_config_nest.ini`.

### 3. Run with Docker Compose

Update `docker-compose.yaml` to point to your config and video storage directories:

```yaml
volumes:
  - /path/to/config:/config
  - /path/to/videos:/videos
```

Then start the container:
```bash
docker-compose up -d
```

## Configuration Options

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `timezone` | Yes | - | Your local timezone for video filenames (e.g., `America/Los_Angeles`) |
| `refresh_interval` | Yes | - | How often to sync new videos, in minutes |
| `fetch_range` | No | `240` | Minutes of video history to fetch per sync. 240 = 4 hours (recommended for free Nest Aware) |
| `google_username` | Yes | - | Google account email with Nest cameras |
| `google_master_token` | Yes | - | Master token obtained from step 1 |

## Credits:

Most of the work is credited to the original author [TamirMa](https://github.com/TamirMa/google-nest-telegram-sync), I just modified it to sync to local NAS storage instead, and putting it into a Docker container to make it easier to deploy.

Now that the endpoints are available over web, it should be easier to develop for with dev tools (w/o needing to proxy mitm requests)

You can find his original research over here [here](https://medium.com/@tamirmayer/google-nest-camera-internal-api-fdf9dc3ce167)

He also mentioned the original credits to some other incredible developers:

Much credits for the authors of the [**glocaltokens**](https://github.com/leikoilja/glocaltokens) module

Thanks also for the authors of the docker [**ha-google-home_get-token**](https://hub.docker.com/r/breph/ha-google-home_get-token)
