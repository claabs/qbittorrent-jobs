import argparse
import os
from pathlib import Path
from urllib.parse import urlparse

import json5
from dotenv import load_dotenv
from qbittorrentapi import Client, LoginFailed

load_dotenv()


class QBitTagManager:
    def __init__(self, config_file):
        self.client = None
        self.configs = self._load_configs(config_file)

    def _load_configs(self, config_file):
        """Load and validate JSONC configuration file"""
        try:
            with open(config_file, "r") as f:
                configs = json5.load(f)

            if not isinstance(configs, list):
                raise ValueError("Config file must be a top level array")

            required_fields = {"tracker", "min_progress", "max_seeding", "tag"}
            for idx, cfg in enumerate(configs):
                missing = required_fields - cfg.keys()
                if missing:
                    raise ValueError(
                        f"Config {idx} missing fields: {', '.join(missing)}"
                    )

                cfg["min_progress"] = float(cfg["min_progress"])
                cfg["max_seeding"] = int(cfg["max_seeding"])

            return configs

        except Exception as e:
            print(f"Config error: {str(e)}")
            exit(1)

    def connect(self, host, username, password):
        """Initialize qBittorrent connection"""
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

    def process_all(self):
        """Process all configured tracker rules"""
        for config in self.configs:
            self._process_config(config)

    def _process_config(self, config):
        """Handle a single tracker configuration"""
        print(f"Processing config: {config['tag']}")

        # Get torrents matching exact tracker
        tracker_torrents = self.client.torrents_info(
            private=True, include_trackers=True
        )
        valid_hashes = self._apply_tagging_rules(tracker_torrents, config)
        self._clean_stale_tags(valid_hashes, config["tag"])

    def _apply_tagging_rules(self, torrents, config):
        """Apply progress/seeding rules and return valid hashes"""
        add_tag = []
        remove_tag = []
        valid_hashes = set()

        for torrent in torrents:
            tracker_matches = any(
                urlparse(tracker["url"]).hostname == config["tracker"]
                for tracker in torrent.trackers
            )

            torrent_progress = torrent.downloaded / torrent.total_size

            meets_criteria = (
                torrent_progress >= config["min_progress"]
                and torrent.seeding_time < config["max_seeding"]
                and tracker_matches
                and torrent.downloaded > 0
            )

            current_tags = set(torrent.tags.split(", ") if torrent.tags else [])

            if meets_criteria:
                valid_hashes.add(torrent.hash)
                if config["tag"] not in current_tags:
                    print(f"Tagging '{torrent.name}' with '{config['tag']}'")
                    add_tag.append(torrent.hash)
            else:
                if config["tag"] in current_tags:
                    print(f"Removing tag '{config['tag']}' from '{torrent.name}'")
                    remove_tag.append(torrent.hash)

        # Batch process tag updates
        if add_tag:
            self.client.torrents_add_tags(torrent_hashes=add_tag, tags=config["tag"])
            print(f"Added '{config['tag']}' to {len(add_tag)} torrents")

        if remove_tag:
            self.client.torrents_remove_tags(
                torrent_hashes=remove_tag, tags=config["tag"]
            )
            print(f"Removed '{config['tag']}' from {len(remove_tag)} torrents")

        return valid_hashes

    def _clean_stale_tags(self, valid_hashes, tag):
        """Remove tag from torrents that no longer match criteria"""
        tagged_torrents = self.client.torrents_info(tag=tag)
        stale_hashes = [t.hash for t in tagged_torrents if t.hash not in valid_hashes]

        if stale_hashes:
            self.client.torrents_remove_tags(torrent_hashes=stale_hashes, tags=tag)
            print(f"Cleaned '{tag}' from {len(stale_hashes)} stale torrents")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-c",
        "--config",
        default="/config/hnr.jsonc",
        help="Path to config file (JSONC format)",
    )
    args = parser.parse_args()

    if not Path(args.config).exists():
        print(f"Config file not found: {args.config}")
        exit(1)

    tagger = QBitTagManager(args.config)
    tagger.connect(
        host=os.getenv("QB_HOST", "localhost:8080"),
        username=os.getenv("QB_USER", "admin"),
        password=os.getenv("QB_PASS", "adminadmin"),
    )

    try:
        tagger.process_all()
        print("All configurations processed successfully")
    finally:
        tagger.client.auth_log_out()
