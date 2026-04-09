"""JSON-based persistent storage for matchmaking data."""

import copy
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_DATA = {
    "queue": [],
    "matches": [],
    "pending_challenges": []
}


def _default_data() -> dict[str, Any]:
    """Return a fresh copy of default data structure."""
    return copy.deepcopy(DEFAULT_DATA)


class MatchmakingStorage:
    """Handles reading/writing matchmaking data to a JSON file."""

    def __init__(self, filepath: str = "matchmaking_data.json"):
        self.filepath = Path(filepath)
        self.data: dict[str, Any] = {}
        self._load_data()

    def _load_data(self) -> None:
        """Load data from JSON file, handling missing or corrupted files."""
        if not self.filepath.exists():
            logger.info("Storage file not found. Initializing with default data.")
            self.data = _default_data()
            self._save_data()
            return

        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                loaded = json.load(f)

            # Validate structure
            if not isinstance(loaded, dict):
                raise ValueError("Data is not a dictionary")
            if "queue" not in loaded or "matches" not in loaded:
                raise ValueError("Missing required keys: 'queue' and/or 'matches'")
            if not isinstance(loaded["queue"], list) or not isinstance(loaded["matches"], list):
                raise ValueError("'queue' and 'matches' must be lists")

            self.data = loaded
            # Backfill missing keys from older saves
            if "pending_challenges" not in self.data:
                self.data["pending_challenges"] = []
            logger.info(f"Loaded storage from {self.filepath}")

        except (json.JSONDecodeError, ValueError, OSError) as e:
            logger.warning(f"Storage file corrupted or unreadable ({e}). Resetting to defaults.")
            self.data = _default_data()
            self._save_data()

    def _save_data(self) -> None:
        """Persist current data to JSON file."""
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except OSError as e:
            logger.error(f"Failed to save storage data: {e}")

    @property
    def queue(self) -> list[dict[str, Any]]:
        return self.data["queue"]

    @property
    def matches(self) -> list[dict[str, Any]]:
        return self.data["matches"]

    @property
    def pending_challenges(self) -> list[dict[str, Any]]:
        return self.data["pending_challenges"]

    def add_pending_challenge(
        self, challenger_id: int, challenger_name: str,
        target_id: int, target_name: str, system: str, points: str,
    ) -> None:
        """Record a pending rival challenge."""
        self.pending_challenges.append({
            "challenger_id": challenger_id,
            "challenger_name": challenger_name,
            "target_id": target_id,
            "target_name": target_name,
            "system": system,
            "points": points,
        })
        self._save_data()

    def remove_pending_challenge(self, target_id: int) -> bool:
        """Remove a pending challenge by target user_id. Returns True if removed."""
        before = len(self.pending_challenges)
        self.data["pending_challenges"] = [
            c for c in self.pending_challenges if c["target_id"] != target_id
        ]
        if len(self.pending_challenges) < before:
            self._save_data()
            return True
        return False

    def find_pending_challenge_by_challenger(self, challenger_id: int) -> dict[str, Any] | None:
        """Find a pending challenge where the given user is the challenger."""
        for c in self.pending_challenges:
            if c["challenger_id"] == challenger_id:
                return c
        return None

    def find_pending_challenge_by_target(self, target_id: int) -> dict[str, Any] | None:
        """Find a pending challenge where the given user is the target."""
        for c in self.pending_challenges:
            if c["target_id"] == target_id:
                return c
        return None

    def is_pending_challenge(self, user_id: int) -> bool:
        """Check if a user has a pending challenge (as challenger or target)."""
        return (self.find_pending_challenge_by_challenger(user_id) is not None
                or self.find_pending_challenge_by_target(user_id) is not None)

    def add_to_queue(self, user_id: int, username: str, system: str, points: str) -> None:
        """Add a user to the matchmaking queue."""
        self.queue.append({
            "user_id": user_id,
            "username": username,
            "system": system,
            "points": points,
        })
        self._save_data()

    def find_compatible_opponent(self, user_id: int, system: str, points: str) -> dict[str, Any] | None:
        """Find the first waiting player with matching system and points.
        Returns the opponent entry or None if no match found."""
        for entry in self.queue:
            if (entry["user_id"] != user_id
                    and entry.get("system") == system
                    and entry.get("points") == points):
                return entry
        return None

    def remove_from_queue_by_entry(self, entry: dict[str, Any]) -> None:
        """Remove a specific entry from the queue (used when matching a player out)."""
        self.data["queue"] = [p for p in self.queue if p["user_id"] != entry["user_id"]]
        self._save_data()

    def remove_from_queue(self, user_id: int) -> bool:
        """Remove a user from the queue by user_id. Returns True if removed."""
        original_length = len(self.queue)
        self.data["queue"] = [p for p in self.queue if p["user_id"] != user_id]
        if len(self.queue) < original_length:
            self._save_data()
            return True
        return False

    def add_match(self, player1: dict[str, Any], player2: dict[str, Any]) -> None:
        """Record a confirmed match between two players."""
        self.matches.append({
            "player1": player1,
            "player2": player2
        })
        self._save_data()

    def is_in_queue(self, user_id: int) -> bool:
        """Check if a user is currently in the queue."""
        return any(p.get("user_id") == user_id for p in self.queue)

    def is_in_match(self, user_id: int) -> bool:
        """Check if a user is already in a confirmed match."""
        return self.find_match_for_user(user_id) is not None

    def find_match_for_user(self, user_id: int) -> dict[str, Any] | None:
        """Find the match entry containing a given user. Returns the match dict or None."""
        for m in self.matches:
            p1 = m.get("player1", {})
            p2 = m.get("player2", {})
            if p1.get("user_id") == user_id or p2.get("user_id") == user_id:
                return m
        return None

    def remove_match(self, match_entry: dict[str, Any]) -> None:
        """Remove a specific match entry from the matches list."""
        # Identify the match by both players' user_ids
        p1_id = match_entry.get("player1", {}).get("user_id")
        p2_id = match_entry.get("player2", {}).get("user_id")

        def _matches(m: dict) -> bool:
            m1 = m.get("player1", {}).get("user_id")
            m2 = m.get("player2", {}).get("user_id")
            return m1 == p1_id and m2 == p2_id

        self.data["matches"] = [m for m in self.matches if not _matches(m)]
        self._save_data()

    def reset_all(self) -> None:
        """Clear all queues and matches."""
        self.data = _default_data()
        self._save_data()
