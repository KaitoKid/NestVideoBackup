# Google Nest Camera Video - Sync To Storage

I wanted an easy way to store my Nest event history to my local NAS and store more than 60 days of footage. By default it starts by only backing up the last 4 hours of data. You can build your own image if you want your initial fetch to include more than that. Just modify `FETCH_RANGE` in minutes.
This module is for personal use only, especially as it uses unpublished APIs. Use it is at your own risk!

## How It Works
1. Gets your **Google Home devices using HomeGraph**
2. Retrieves your recent **Google Nest events**
3. **Download full-quality Google Nest video clips**
4. Stores those clips to a local storage directory by `device_name` and into subdirectories with the format `YYYY/MM/DD/*.mp4`

## Usage:

1. Obtain a Google Master Token with `docker run --rm -it breph/ha-google-home_get-token`. You can use an app password generated from [Google App Passwords](https://myaccount.google.com/apppasswords), make sure you're generated it on the right account
2. Create a folder on your system for the appdata from this image, and put the `nest.ini` template file inside with the data filled out
3. If using docker-compose, point the folder that is holding the `nest.ini` to `/config`, and your local storage pool or mounted storageand to `/videos`
4. You can also build this yourself with `docker-compose up` if you don't want to use the published image

## Credits:

Most of the work is credited to the original author [TamirMa](https://github.com/TamirMa/google-nest-telegram-sync), I just modified it to sync to local NAS storage instead, and putting it into a Docker container to make it easier to deploy.

Now that the endpoints are available over web, it should be easier to develop for with dev tools (w/o needing to proxy mitm requests)

You can find his original research over here [here](https://medium.com/@tamirmayer/google-nest-camera-internal-api-fdf9dc3ce167)

He also mentioned the original credits to some other incredible developers:

Much credits for the authors of the [**glocaltokens**](https://github.com/leikoilja/glocaltokens) module

Thanks also for the authors of the docker [**ha-google-home_get-token**](https://hub.docker.com/r/breph/ha-google-home_get-token)
