# qbittorrent-jobs

## Hit and Run Tagger

A script that finds potential hit and run torrents in qBittorrent and tags them. Tags torrents that are:

- private
- have downloaded bytes (no cross-seeds)
- match the configured tracker
- under the configured maximum seed time
- above the configured minimum progress percentage

## Setup

### Image

`ghcr.io/claabs/qbittorrent-jobs`

### Environment Variables

| Variable       | Example              | Default          | Description                                                                  |
|----------------|----------------------|------------------|------------------------------------------------------------------------------|
| QB_USER        | `username`           | `admin`          | qBittorrent username                                                         |
| QB_PASS        | `password`           | `adminadmin`     | qBittorrent password                                                         |
| QB_HOST        | `192.168.1.100:8080` | `localhost:8080` | HTTP URL for the qBittorrent web UI, with port                               |
| CRON_SCHEDULE  | `* * * * *`          | `45 * * * *`     | Cron schedule of when to run the job                                         |
| RUN_ON_STARTUP | `false`              | `true`           | If true, runs the script immediately on startup, then schedules the cron job |
| RUN_ONCE       | `true`               | `false`          | If true, does not schedule the cron job                                      |
| TZ             | `America/Chicago`    | `UTC`            | Your timezone identifier                                                     |

### Volumes

- `/mnt/my/path/config:/config:ro`: stores the job config files (`hnr.jsonc`)

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
