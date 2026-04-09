"""Tests for the JSON persistence layer (storage.py)."""

import json
import sys
from pathlib import Path

import pytest

# Ensure the parent directory is on the path so storage can be imported
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from storage import MatchmakingStorage


class TestStorageInitialization:
    """Test storage startup behavior."""

    def test_creates_default_on_missing_file(self, tmp_path):
        """If the file doesn't exist, create it with default data."""
        json_file = tmp_path / "missing.json"
        # Ensure file does not exist
        if json_file.exists():
            json_file.unlink()
        storage = MatchmakingStorage(filepath=str(json_file))
        assert storage.queue == []
        assert storage.matches == []
        assert json_file.exists()

    def test_loads_valid_json(self, tmp_json):
        """Load properly structured JSON."""
        data = {
            "queue": [{"user_id": 1, "username": "Alice", "faction": "AOF"}],
            "matches": [],
        }
        with open(tmp_json, "w") as f:
            json.dump(data, f)

        storage = MatchmakingStorage(filepath=str(tmp_json))
        assert len(storage.queue) == 1
        assert storage.queue[0]["username"] == "Alice"

    def test_recovers_from_corrupted_file(self, corrupted_json):
        """Corrupted JSON should not crash — resets to defaults."""
        storage = MatchmakingStorage(filepath=str(corrupted_json))
        assert storage.queue == []
        assert storage.matches == []

    def test_recovers_from_partial_keys(self, partial_json):
        """JSON missing required keys should reset to defaults."""
        storage = MatchmakingStorage(filepath=str(partial_json))
        assert storage.queue == []
        assert storage.matches == []

    def test_recovers_from_non_dict_root(self, tmp_json):
        """JSON that is a list instead of a dict should reset."""
        with open(tmp_json, "w") as f:
            json.dump([1, 2, 3], f)
        storage = MatchmakingStorage(filepath=str(tmp_json))
        assert storage.data == {"queue": [], "matches": []}


class TestQueueOperations:
    """Test adding/removing users from the queue."""

    def test_add_to_queue(self, storage):
        storage.add_to_queue(1, "Alice", "AOF")
        assert len(storage.queue) == 1
        assert storage.queue[0] == {"user_id": 1, "username": "Alice", "faction": "AOF"}

    def test_is_in_queue(self, storage):
        storage.add_to_queue(1, "Alice", "AOF")
        assert storage.is_in_queue(1) is True
        assert storage.is_in_queue(999) is False

    def test_remove_from_queue(self, storage):
        storage.add_to_queue(1, "Alice", "AOF")
        storage.add_to_queue(2, "Bob", "GDF")

        result = storage.remove_from_queue(1)
        assert result is True
        assert len(storage.queue) == 1
        assert storage.queue[0]["user_id"] == 2

    def test_remove_nonexistent_user(self, storage):
        result = storage.remove_from_queue(999)
        assert result is False

    def test_duplicate_user_not_added_twice_via_is_in_queue(self, storage):
        """is_in_queue should return True after first add."""
        storage.add_to_queue(1, "Alice", "AOF")
        assert storage.is_in_queue(1) is True

    def test_queue_persists_to_file(self, storage):
        """After adding, reading the file should reflect the change."""
        storage.add_to_queue(1, "Alice", "AOF")
        with open(storage.filepath, "r") as f:
            loaded = json.load(f)
        assert len(loaded["queue"]) == 1


class TestMatchOperations:
    """Test match recording and lookup."""

    def test_add_match(self, storage):
        p1 = {"user_id": 1, "username": "Alice", "faction": "AOF"}
        p2 = {"user_id": 2, "username": "Bob", "faction": "GDF"}
        storage.add_match(p1, p2)

        assert len(storage.matches) == 1
        assert storage.matches[0]["player1"] == p1
        assert storage.matches[0]["player2"] == p2

    def test_is_in_match(self, storage):
        p1 = {"user_id": 1, "username": "Alice", "faction": "AOF"}
        p2 = {"user_id": 2, "username": "Bob", "faction": "GDF"}
        storage.add_match(p1, p2)

        assert storage.is_in_match(1) is True
        assert storage.is_in_match(2) is True
        assert storage.is_in_match(999) is False

    def test_is_in_match_with_malformed_data(self, tmp_json):
        """Should not crash on matches with missing keys."""
        data = {
            "queue": [],
            "matches": [
                {"player1": {"user_id": 1}},  # missing player2
                {"player1": {}},               # missing user_id
                {"weird": "entry"},            # completely malformed
            ],
        }
        with open(tmp_json, "w") as f:
            json.dump(data, f)

        storage = MatchmakingStorage(filepath=str(tmp_json))
        assert storage.is_in_match(1) is True
        assert storage.is_in_match(999) is False  # should not crash

    def test_match_persists_to_file(self, storage):
        p1 = {"user_id": 1, "username": "Alice", "faction": "AOF"}
        p2 = {"user_id": 2, "username": "Bob", "faction": "GDF"}
        storage.add_match(p1, p2)

        with open(storage.filepath, "r") as f:
            loaded = json.load(f)
        assert len(loaded["matches"]) == 1


class TestReset:
    """Test reset behavior."""

    def test_reset_clears_everything(self, storage):
        storage.add_to_queue(1, "Alice", "AOF")
        storage.add_to_queue(2, "Bob", "GDF")
        p1 = {"user_id": 3, "username": "Carol", "faction": "AOF"}
        p2 = {"user_id": 4, "username": "Dave", "faction": "GDF"}
        storage.add_match(p1, p2)

        storage.reset_all()
        assert storage.queue == []
        assert storage.matches == []

    def test_reset_persists_to_file(self, storage, tmp_json):
        storage.add_to_queue(1, "Alice", "AOF")
        storage.reset_all()

        with open(tmp_json, "r") as f:
            loaded = json.load(f)
        assert loaded == {"queue": [], "matches": []}


class TestEdgeCases:
    """Edge-case and robustness tests."""

    def test_is_in_queue_with_missing_user_id(self, tmp_json):
        """Should not crash if a queue entry is missing user_id."""
        data = {
            "queue": [{"username": "Ghost"}],  # no user_id
            "matches": [],
        }
        with open(tmp_json, "w") as f:
            json.dump(data, f)

        storage = MatchmakingStorage(filepath=str(tmp_json))
        assert storage.is_in_queue(1) is False

    def test_multiple_matches_same_user(self, storage):
        """A user can technically appear in multiple matches (data-level)."""
        p1 = {"user_id": 1, "username": "Alice", "faction": "AOF"}
        p2 = {"user_id": 2, "username": "Bob", "faction": "GDF"}
        p3 = {"user_id": 3, "username": "Carol", "faction": "AOF"}
        storage.add_match(p1, p2)
        storage.add_match(p1, p3)

        assert storage.is_in_match(1) is True

    def test_empty_queue_and_matches_properties(self, storage):
        """Properties should return lists."""
        assert isinstance(storage.queue, list)
        assert isinstance(storage.matches, list)
