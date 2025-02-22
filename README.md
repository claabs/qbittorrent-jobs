# qbittorrent-jobs

## Hit and Run Tagger

A script that finds potential hit and run torrents in qBittorrent and tags them. Tags torrents that are:

- private
- have downloaded bytes (no cross-seeds)
- match the configured tracker
- under the configured maximum seed time
- above the configured minimum progress percentage

## Tracker Uptime

A script that logs the status of all trackers in all torrents, considering "Working" to be "up" and the remaining statuses "down". Helps with determining what trackers to delete from your client over a certaim duration.

## Setup

### Image

`ghcr.io/claabs/qbittorrent-jobs`

### Environment Variables

| Variable             | Example              | Default          | Description                                                                  |
|----------------------|----------------------|------------------|------------------------------------------------------------------------------|
| QB_USER              | `username`           | `admin`          | qBittorrent username                                                         |
| QB_PASS              | `password`           | `adminadmin`     | qBittorrent password                                                         |
| QB_HOST              | `192.168.1.100:8080` | `localhost:8080` | HTTP URL for the qBittorrent web UI, with port                               |
| HNR_CRON_SCHEDULE    | `* * * * *`          | `45 * * * *`     | Cron schedule of when to run the HNR tagger job                              |
| UPTIME_CRON_SCHEDULE | `* * * * *`          | `15 * * * *`     | Cron schedule of when to run the tracker uptime job                          |
| RUN_ON_STARTUP       | `false`              | `true`           | If true, runs the script immediately on startup, then schedules the cron job |
| RUN_ONCE             | `true`               | `false`          | If true, does not schedule the cron job                                      |
| TZ                   | `America/Chicago`    | `UTC`            | Your timezone identifier                                                     |

### Volumes

- `/mnt/my/path/config:/config:rw`: stores the job config files (`hnr.jsonc`) and tracker data (`tracker-stats.json`)

### Hit and Run Config

File: `/config/hnr.jsonc`

```jsonc
[
    {
        "tracker": "tracker.example.com", // The hostname of the private tracker
        "min_progress": 1, // The torrent must have 100% progress to be tagged
        "max_seeding": 518400, // The torrent must be seeding for under 6 days (in seconds)
        "tag": "example-hnr"
    },
    {
        "tracker": "torrent.local", // The hostname of the private tracker
        "min_progress": 0.2, // The torrent must have at least 20% progress to be tagged
        "max_seeding": 432000, // The torrent must be seeding for under 5 days (in seconds)
        "tag": "local-hnr"
    }
]
```

## Development

### Build Image

`docker build . -t qbittorrent-jobs`

### Run Container

`docker run --rm -it -e QB_HOST=192.168.1.100:8080 -v ./config:/config qbittorrent-jobs`
