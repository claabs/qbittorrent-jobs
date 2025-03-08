import argparse
import csv
import datetime
import json
import os

from dotenv import load_dotenv
from qbittorrentapi import Client, LoginFailed

load_dotenv()


class TrackerUptimeMonitor:
    def __init__(self, stats_file):
        self.client = None
        self.stats_file = stats_file
        self.stats = self._load_stats()

    def _load_stats(self):
        try:
            with open(self.stats_file, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_stats(self):
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
                    "last_seen",
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
                # Preserve stats but mark inactive
                self.stats[url]["last_seen"] = now
                continue

            status = "up" if current_statuses[url] == 2 else "down"

            self.stats[url]["total_checks"] += 1
            if status == "up":
                self.stats[url]["up_checks"] += 1
            self.stats[url]["percent"] = round(
                self.stats[url]["up_checks"] / self.stats[url]["total_checks"] * 100
            )
            self.stats[url]["last_status"] = status
            self.stats[url]["last_updated"] = now
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
                "last_seen": now,
            }

        self._save_stats()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-f",
        "--file",
        default="/config/tracker-stats.json",
        help="Path to uptime stats history (JSON format)",
    )
    args = parser.parse_args()

    monitor = TrackerUptimeMonitor(args.file)
    monitor.connect(
        host=os.getenv("QB_HOST", "http://localhost:8080"),
        username=os.getenv("QB_USER", "admin"),
        password=os.getenv("QB_PASS", "adminadmin"),
    )

    try:
        monitor.update_stats()
        print("Tracker statistics updated successfully")

    finally:
        monitor.client.auth_log_out()
