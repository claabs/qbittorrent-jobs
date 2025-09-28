import os

from dotenv import load_dotenv
from qbittorrentapi import Client, LoginFailed

load_dotenv()


class QBitTagManager:
    def __init__(self):
        self.client = None
        self.tag_text = "tracker-error"

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
        tracker_torrents = self.client.torrents_info(
            private=True, include_trackers=True
        )
        valid_hashes = self._apply_tagging_rules(tracker_torrents)
        self._clean_stale_tags(valid_hashes)

    def _has_tracker_error(self, torrent):
        """Check if any tracker has an error status"""
        private_trackers = [t for t in torrent.trackers if t.msg != 'This torrent is private']
        # enum 4 = NOT_WORKING
        return all(tracker.status == 4 for tracker in private_trackers)

    def _apply_tagging_rules(self, torrents):
        """Apply progress/seeding rules and return valid hashes"""
        add_tag = []
        remove_tag = []
        valid_hashes = set()

        for torrent in torrents:
            # enum 4 = NOT_WORKING
            has_error = self._has_tracker_error(torrent)

            current_tags = set(torrent.tags.split(", ") if torrent.tags else [])

            if has_error:
                valid_hashes.add(torrent.hash)
                if self.tag_text not in current_tags:
                    print(f"Tagging '{torrent.name}' with '{self.tag_text}'")
                    add_tag.append(torrent.hash)
            else:
                if self.tag_text in current_tags:
                    print(f"Removing tag '{self.tag_text}' from '{torrent.name}'")
                    remove_tag.append(torrent.hash)

        # Batch process tag updates
        if add_tag:
            self.client.torrents_add_tags(torrent_hashes=add_tag, tags=self.tag_text)
            print(f"Added '{self.tag_text}' to {len(add_tag)} torrents")

        if remove_tag:
            self.client.torrents_remove_tags(
                torrent_hashes=remove_tag, tags=self.tag_text
            )
            print(f"Removed '{self.tag_text}' from {len(remove_tag)} torrents")

        return valid_hashes

    def _clean_stale_tags(self, valid_hashes):
        """Remove tag from torrents that no longer match criteria"""
        tagged_torrents = self.client.torrents_info(tag=self.tag_text)
        stale_hashes = [t.hash for t in tagged_torrents if t.hash not in valid_hashes]

        if stale_hashes:
            self.client.torrents_remove_tags(torrent_hashes=stale_hashes, tags=self.tag_text)
            print(f"Cleaned '{self.tag_text}' from {len(stale_hashes)} stale torrents")


if __name__ == "__main__":
    tagger = QBitTagManager()
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
