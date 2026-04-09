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
        if json_file.exists():
            json_file.unlink()
        storage = MatchmakingStorage(filepath=str(json_file))
        assert storage.queue == []
        assert storage.matches == []
        assert json_file.exists()

    def test_loads_valid_json(self, tmp_json):
        """Load properly structured JSON."""
        data = {
            "queue": [{"user_id": 1, "username": "Alice", "system": "AOF", "points": "1000"}],
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
        storage.add_to_queue(1, "Alice", "AOF", "1000")
        assert len(storage.queue) == 1
        assert storage.queue[0] == {"user_id": 1, "username": "Alice", "system": "AOF", "points": "1000"}

    def test_is_in_queue(self, storage):
        storage.add_to_queue(1, "Alice", "AOF", "1000")
        assert storage.is_in_queue(1) is True
        assert storage.is_in_queue(999) is False

    def test_remove_from_queue(self, storage):
        storage.add_to_queue(1, "Alice", "AOF", "1000")
        storage.add_to_queue(2, "Bob", "GDF", "2000")

        result = storage.remove_from_queue(1)
        assert result is True
        assert len(storage.queue) == 1
        assert storage.queue[0]["user_id"] == 2

    def test_remove_nonexistent_user(self, storage):
        result = storage.remove_from_queue(999)
        assert result is False

    def test_duplicate_user_not_added_twice_via_is_in_queue(self, storage):
        """is_in_queue should return True after first add."""
        storage.add_to_queue(1, "Alice", "AOF", "1000")
        assert storage.is_in_queue(1) is True

    def test_queue_persists_to_file(self, storage):
        """After adding, reading the file should reflect the change."""
        storage.add_to_queue(1, "Alice", "AOF", "1000")
        with open(storage.filepath, "r") as f:
            loaded = json.load(f)
        assert len(loaded["queue"]) == 1


class TestMatchOperations:
    """Test match recording and lookup."""

    def test_add_match(self, storage):
        p1 = {"user_id": 1, "username": "Alice", "system": "AOF", "points": "1000"}
        p2 = {"user_id": 2, "username": "Bob", "system": "GDF", "points": "2000"}
        storage.add_match(p1, p2)

        assert len(storage.matches) == 1
        assert storage.matches[0]["player1"] == p1
        assert storage.matches[0]["player2"] == p2

    def test_is_in_match(self, storage):
        p1 = {"user_id": 1, "username": "Alice", "system": "AOF", "points": "1000"}
        p2 = {"user_id": 2, "username": "Bob", "system": "GDF", "points": "2000"}
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
        assert storage.is_in_match(999) is False

    def test_match_persists_to_file(self, storage):
        p1 = {"user_id": 1, "username": "Alice", "system": "AOF", "points": "1000"}
        p2 = {"user_id": 2, "username": "Bob", "system": "GDF", "points": "2000"}
        storage.add_match(p1, p2)

        with open(storage.filepath, "r") as f:
            loaded = json.load(f)
        assert len(loaded["matches"]) == 1


class TestReset:
    """Test reset behavior."""

    def test_reset_clears_everything(self, storage):
        storage.add_to_queue(1, "Alice", "AOF", "1000")
        storage.add_to_queue(2, "Bob", "GDF", "2000")
        p1 = {"user_id": 3, "username": "Carol", "system": "AOF", "points": "1500"}
        p2 = {"user_id": 4, "username": "Dave", "system": "GDF", "points": "3000+"}
        storage.add_match(p1, p2)

        storage.reset_all()
        assert storage.queue == []
        assert storage.matches == []

    def test_reset_persists_to_file(self, storage, tmp_json):
        storage.add_to_queue(1, "Alice", "AOF", "1000")
        storage.reset_all()

        with open(tmp_json, "r") as f:
            loaded = json.load(f)
        assert loaded == {"queue": [], "matches": []}


class TestFindOpponent:
    """Test the compatible opponent search."""

    def test_finds_matching_opponent(self, storage):
        """Should find the first waiting player with same system + points."""
        storage.add_to_queue(1, "Alice", "AOF", "1000")
        storage.add_to_queue(2, "Bob", "GDF", "2000")
        storage.add_to_queue(3, "Carol", "AOF", "1000")

        # Carol wants AOF 1000 → should match Alice (first in queue)
        opponent = storage.find_compatible_opponent(3, "AOF", "1000")
        assert opponent is not None
        assert opponent["user_id"] == 1

    def test_no_match_different_system(self, storage):
        """Should return None if no one shares system."""
        storage.add_to_queue(1, "Alice", "AOF", "1000")
        storage.add_to_queue(2, "Bob", "GDF", "1000")

        opponent = storage.find_compatible_opponent(3, "AOF", "2000")
        assert opponent is None

    def test_no_match_different_points(self, storage):
        """Should return None if no one shares points."""
        storage.add_to_queue(1, "Alice", "AOF", "1000")

        opponent = storage.find_compatible_opponent(2, "AOF", "2000")
        assert opponent is None

    def test_empty_queue(self, storage):
        """Should return None on empty queue."""
        assert storage.find_compatible_opponent(1, "AOF", "1000") is None

    def test_match_and_remove(self, storage):
        """After matching, remove opponent from queue."""
        storage.add_to_queue(1, "Alice", "AOF", "1000")
        storage.add_to_queue(2, "Bob", "AOF", "2000")

        opponent = storage.find_compatible_opponent(3, "AOF", "1000")
        assert opponent is not None
        storage.remove_from_queue_by_entry(opponent)

        assert len(storage.queue) == 1
        assert storage.queue[0]["user_id"] == 2

    def test_fifo_among_compatible(self, storage):
        """First compatible player should be matched, not later ones."""
        storage.add_to_queue(1, "Alice", "AOF", "1000")
        storage.add_to_queue(2, "Eve", "AOF", "1000")

        # Carol arrives, should match Alice (first compatible)
        opponent = storage.find_compatible_opponent(3, "AOF", "1000")
        assert opponent["user_id"] == 1


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
        p1 = {"user_id": 1, "username": "Alice", "system": "AOF", "points": "1000"}
        p2 = {"user_id": 2, "username": "Bob", "system": "GDF", "points": "2000"}
        p3 = {"user_id": 3, "username": "Carol", "system": "AOF", "points": "1500"}
        storage.add_match(p1, p2)
        storage.add_match(p1, p3)

        assert storage.is_in_match(1) is True

    def test_empty_queue_and_matches_properties(self, storage):
        """Properties should return lists."""
        assert isinstance(storage.queue, list)
        assert isinstance(storage.matches, list)

    def test_old_data_without_points_field(self, tmp_json):
        """Queue entries from before the points change should still work."""
        data = {
            "queue": [{"user_id": 1, "username": "Alice", "system": "AOF"}],  # no points
            "matches": [],
        }
        with open(tmp_json, "w") as f:
            json.dump(data, f)

        storage = MatchmakingStorage(filepath=str(tmp_json))
        # find_compatible_opponent with points=None matches entries that also lack the key
        opponent = storage.find_compatible_opponent(2, "AOF", None)
        assert opponent is not None  # Alice has no points key, so None == None
        assert opponent["user_id"] == 1

        # But a search with specific points won't match old entries
        opponent_with_points = storage.find_compatible_opponent(3, "AOF", "1000")
        assert opponent_with_points is None

        # is_in_queue should still work
        assert storage.is_in_queue(1) is True
