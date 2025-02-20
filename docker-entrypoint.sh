#!/bin/sh

set -e

RUN_ON_STARTUP=${RUN_ON_STARTUP:-"true"}
RUN_ONCE=${RUN_ONCE:-"false"}
CRON_SCHEDULE=${CRON_SCHEDULE:-"45 * * * *"}

# If RUN_ON_STARTUP is set, run it once before setting up the schedule
echo "Run on startup: ${RUN_ON_STARTUP}"
if [ "$RUN_ON_STARTUP" = "true" ]; then
    python /app/qbittorrent_jobs/hnr_tagger.py
fi

# If runOnce is not set, schedule the process
echo "Run once: ${RUN_ONCE}"
if [ "$RUN_ONCE" = "false" ]; then
    echo "Setting cron schedule as ${CRON_SCHEDULE}"
    # Add the command to the crontab
    echo "${CRON_SCHEDULE} python /app/qbittorrent_jobs/hnr_tagger.py" > $HOME/crontab
    # Run the cron process. The container should halt here and wait for the schedule.
    supercronic -no-reap -passthrough-logs $HOME/crontab
fi
echo "Exiting..."