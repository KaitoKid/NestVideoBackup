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

Start with the original token helper:

```bash
docker run --rm -it breph/ha-google-home_get-token
```

Enter the Google email that has access to your Nest cameras and your password
when prompted. If the account uses 2-step verification, prefer an app password
generated from [Google App Passwords](https://myaccount.google.com/apppasswords).
A successful run prints a master token; copy that master token into `nest.ini`
in step 2.

Do not put your password or app password directly in the command. Run the
legacy helper in a private terminal because some versions may echo interactive
input. Treat the resulting master token as a password too.

#### Backup method: browser-based token exchange

Google may reject the original direct password/app-password flow for some
accounts. If it returns `BadAuthentication`, `NeedsBrowser`, or a master token
of `None`, use this browser-based backup method. It obtains the same type of
master token required by this application; it only changes how that token is
created.

The backup method uses the alternative login flow supported by
[`gpsoauth`](https://pypi.org/project/gpsoauth/). First, build this repository's
image:

```bash
docker build -t nest-video-backup .
```

Then obtain and exchange a temporary browser token:

1. Open [Google EmbeddedSetup](https://accounts.google.com/EmbeddedSetup) in a
   normal browser.
2. Sign in with the Google account that has access to your Nest cameras,
   complete 2-step verification, and select **I agree** when prompted. A page
   ending in `#close` is normal.
3. Open the browser's developer tools and find the `oauth_token` cookie for
   `https://accounts.google.com`:
   - Chrome/Edge: **Application** -> **Storage** -> **Cookies**
   - Firefox: **Storage** -> **Cookies**
4. Copy the complete cookie value (it normally starts with `oauth2_4/` or
   `oauth2_1/`) and use it immediately in the command below.

Create the config directory, then run the included exchange helper:

```bash
mkdir -p /path/to/config

docker run --rm -it \
  --entrypoint python \
  --mount type=bind,src=/path/to/config,dst=/config \
  nest-video-backup \
  /app/configure_from_oauth_token.py
```

The backup helper prompts for your Google email and the `oauth_token` without
echoing the token. It exchanges the temporary cookie and creates or updates
`/path/to/config/nest.ini` with mode `0600`, preserving any existing settings.
It saves only the resulting master token and does not need your Google password
or an app password.

Treat both tokens as passwords: do not put them in shell arguments, screenshots,
issues, or chat messages. If the helper returns `AUTH_FAILED`, repeat the
EmbeddedSetup flow and copy a fresh `oauth_token` cookie.

### 2. Create the Configuration File

If the original token helper succeeded, create the configuration from the
provided sample:

```bash
mkdir -p /path/to/config
cp config/sample_config_nest.ini /path/to/config/nest.ini
```

If you used the browser-based backup helper, it already created or updated
`/path/to/config/nest.ini`; do not replace it with the sample. In either case,
review the file and update the timezone, sync interval, fetch range, and cleanup
settings as needed:

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

# Set manually after using the original helper, or filled by the backup helper
google_username = youremail@gmail.com

# Set manually after using the original helper, or filled by the backup helper
google_master_token = YOUR_MASTER_TOKEN_HERE
```

A sample config is provided in `config/sample_config_nest.ini`.

### 3. Run with Docker Compose

Copy the provided example, then update it to point to your config and video
storage directories:

```bash
cp docker-compose-example.yaml docker-compose.yaml
```

```yaml
volumes:
  - /path/to/config:/config
  - /path/to/videos:/videos
```

Then start the container:
```bash
docker compose up -d
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

Thanks also to the authors of the
[**ha-google-home_get-token**](https://hub.docker.com/r/breph/ha-google-home_get-token)
Docker image. The documented backup method uses `gpsoauth`'s browser-based
exchange for accounts where Google rejects the direct password flow.
