import argparse
import csv
import datetime
import json
import os
import urllib.parse

from dotenv import load_dotenv
from qbittorrentapi import Client, LoginFailed

load_dotenv()


class TrackerManager:
    def __init__(self, stats_file):
        self.client = None
        self.stats_file = stats_file
        self.stats = self._load_stats()
        self.active_stats = {}

    def _load_stats(self):
        try:
            with open(self.stats_file, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_stats(self):
        for data in self.stats.values():
            if "last_seen" in data:
                # remove deprecated field
                del data["last_seen"]

        # Save with alphabetical sorting
        with open(self.stats_file, "w") as f:
            json.dump(self.stats, f, indent=2, sort_keys=True)

        # Save as CSV
        csv_file = os.path.splitext(self.stats_file)[0] + ".csv"
        with open(csv_file, "w", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "url",
                    "up_checks",
                    "total_checks",
                    "percent",
                    "first_seen",
                    "last_updated",
                    "last_status",
                    "last_up",
                ],
            )
            writer.writeheader()
            for url, data in self.stats.items():
                row = {"url": url}
                row.update(data)
                writer.writerow(row)

    def connect(self, host, username, password):
        self.client = Client(
            host=host,
            username=username,
            password=password,
            VERIFY_WEBUI_CERTIFICATE=False,
        )
        try:
            self.client.auth_log_in()
        except LoginFailed as e:
            print(f"Login failed: {str(e)}")
            exit(1)

    def _get_tracker_statuses(self):
        """Get current status for all non-private trackers"""
        status_map = {}

        for torrent in self.client.torrents_info(include_trackers=True, private=False):
            for tracker in torrent.trackers:
                url = tracker["url"]
                if url.startswith("**"):
                    # Skip non-trackers
                    continue

                if tracker.status in [0, 1]:
                    # Skip trackers that have not been contacted or are disabled
                    continue
                # Track lowest status for this tracker
                # 1: Not contacted
                # 2: Working
                # 3: Updating
                # 4: Not Working
                current_status = status_map.get(url, 4)
                status_map[url] = min(current_status, tracker.status)

        return status_map

    def update_stats(self):
        """Update statistics with latest status check"""
        current_statuses = self._get_tracker_statuses()
        now = datetime.datetime.now(datetime.UTC).isoformat()

        # Update existing trackers
        for url in list(self.stats.keys()):
            if url not in current_statuses:
                continue

            status = "up" if current_statuses[url] == 2 else "down"

            active_tracker_stats = {
                "up_checks": self.stats[url].get("up_checks", 0) + 1
                if status == "up"
                else self.stats[url].get("up_checks", 0),
                "total_checks": self.stats[url].get("total_checks", 0) + 1,
                "percent": round(
                    (self.stats[url].get("up_checks", 0) + (1 if status == "up" else 0))
                    / (self.stats[url].get("total_checks", 0) + 1)
                    * 100
                ),
                "last_status": status,
                "last_updated": now,
                "last_up": now
                if status == "up"
                else self.stats[url].get("last_up", None),
            }

            self.stats[url] = active_tracker_stats
            self.active_stats[url] = active_tracker_stats
            del current_statuses[url]

        # Add new trackers
        for url, status_val in current_statuses.items():
            status = "up" if status_val == 2 else "down"

            self.stats[url] = {
                "up_checks": 1 if status == "up" else 0,
                "total_checks": 1,
                "percent": 100 if status == "up" else 0,
                "first_seen": now,
                "last_updated": now,
                "last_status": status,
                "last_up": now if status == "up" else None,
            }

        self._save_stats()

    def prune_trackers(self):
        """Remove trackers with less than 50% uptime and not recently up"""
        now = datetime.datetime.now(datetime.UTC)
        trackers_to_remove = []
        for url, tracker in self.active_stats.items():
            if tracker["percent"] < 50 and (
                "last_up" not in tracker
                or tracker["last_up"] is None
                or (
                    now - datetime.datetime.fromisoformat(tracker["last_up"])
                ).total_seconds()
                > 86400
            ):
                encoded_url = urllib.parse.quote(
                    url, safe=":/?&="
                )  # URL-encode the to handle zero-width spaces
                trackers_to_remove.append(encoded_url)
                print(
                    f"Removing tracker {encoded_url} with {tracker['percent']}% uptime"
                )
        self.client.torrents_remove_trackers("*", trackers_to_remove)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-f",
        "--file",
        default="/config/tracker-stats.json",
        help="Path to uptime stats history (JSON format)",
    )
    args = parser.parse_args()

    tracker_manager = TrackerManager(args.file)
    tracker_manager.connect(
        host=os.getenv("QB_HOST", "http://localhost:8080"),
        username=os.getenv("QB_USER", "admin"),
        password=os.getenv("QB_PASS", "adminadmin"),
    )

    try:
        tracker_manager.update_stats()
        print("Tracker statistics updated successfully")
        tracker_manager.prune_trackers()

    finally:
        tracker_manager.client.auth_log_out()
