#!/bin/sh

set -e

RUN_ON_STARTUP=${RUN_ON_STARTUP:-"true"}
RUN_ONCE=${RUN_ONCE:-"false"}
HNR_CRON_SCHEDULE=${HNR_CRON_SCHEDULE:-"45 * * * *"}
UPTIME_CRON_SCHEDULE=${UPTIME_CRON_SCHEDULE:-"15 * * * *"}

# If RUN_ON_STARTUP is set, run it once before setting up the schedule
echo "Run on startup: ${RUN_ON_STARTUP}"
if [ "$RUN_ON_STARTUP" = "true" ]; then
    python /app/qbittorrent_jobs/hnr_tagger.py
    python /app/qbittorrent_jobs/tracker_uptime.py
fi

# If runOnce is not set, schedule the process
echo "Run once: ${RUN_ONCE}"
if [ "$RUN_ONCE" = "false" ]; then
    echo "Setting HNR cron schedule as ${HNR_CRON_SCHEDULE}"
    echo "Setting uptime cron schedule as ${UPTIME_CRON_SCHEDULE}"
    # Add the command to the crontab
    echo "${HNR_CRON_SCHEDULE} python /app/qbittorrent_jobs/hnr_tagger.py" >> $HOME/crontab
    echo "${UPTIME_CRON_SCHEDULE} python /app/qbittorrent_jobs/tracker_uptime.py" >> $HOME/crontab
    # Run the cron process. The container should halt here and wait for the schedule.
    supercronic -no-reap -passthrough-logs $HOME/crontab
fi
echo "Exiting..."