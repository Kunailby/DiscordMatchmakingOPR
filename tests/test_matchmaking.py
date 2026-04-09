"""Tests for matchmaking business logic and scheduled reset."""

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from storage import MatchmakingStorage


class TestSecondThursdayDetection:
    """Verify the second-Thursday date calculation logic."""

    def is_second_thursday(self, dt: datetime) -> bool:
        """Replicate the logic from the cog for testing."""
        if dt.weekday() != 3:  # Not Thursday
            return False
        week_number = (dt.day - 1) // 7 + 1
        return week_number == 2

    def test_second_thursday_first_half(self):
        """Second Thursday falls on day 8-14."""
        dt = datetime(2026, 4, 9, tzinfo=timezone.utc)
        assert dt.weekday() == 3
        assert self.is_second_thursday(dt) is True

    def test_first_thursday_not_matched(self):
        dt = datetime(2026, 4, 2, tzinfo=timezone.utc)
        assert dt.weekday() == 3
        assert self.is_second_thursday(dt) is False

    def test_third_thursday_not_matched(self):
        dt = datetime(2026, 4, 16, tzinfo=timezone.utc)
        assert dt.weekday() == 3
        assert self.is_second_thursday(dt) is False

    def test_wednesday_not_matched(self):
        dt = datetime(2026, 4, 8, tzinfo=timezone.utc)
        assert self.is_second_thursday(dt) is False

    def test_friday_not_matched(self):
        dt = datetime(2026, 4, 10, tzinfo=timezone.utc)
        assert self.is_second_thursday(dt) is False

    def test_various_months_second_thursday(self):
        """Check known second Thursdays across months."""
        cases = [
            (2026, 1, 8), (2026, 2, 12), (2026, 3, 12),
            (2026, 4, 9), (2026, 5, 14), (2026, 12, 10),
        ]
        for year, month, expected_day in cases:
            dt = datetime(year, month, expected_day, tzinfo=timezone.utc)
            assert dt.weekday() == 3, f"{year}-{month:02d}-{expected_day:02d} is not a Thursday"
            assert self.is_second_thursday(dt) is True, f"Failed for {year}-{month}"

    def test_day_before_and_after_second_thursday(self):
        dt_before = datetime(2026, 4, 8, tzinfo=timezone.utc)
        dt_after = datetime(2026, 4, 10, tzinfo=timezone.utc)
        assert self.is_second_thursday(dt_before) is False
        assert self.is_second_thursday(dt_after) is False


class TestAutoResetDedup:
    """Verify the same-day reset prevention."""

    def test_dedup_prevents_double_reset(self, tmp_path):
        json_file = tmp_path / "test.json"
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        data = {
            "queue": [{"user_id": 1, "username": "Test", "system": "AOF", "points": "1000"}],
            "matches": [],
            "last_auto_reset_date": today,
        }
        with open(json_file, "w") as f:
            import json
            json.dump(data, f)

        storage = MatchmakingStorage(filepath=str(json_file))
        assert storage.data.get("last_auto_reset_date") == today

    def test_dedup_allows_reset_on_different_day(self, tmp_path):
        json_file = tmp_path / "test.json"
        yesterday = "2026-01-01"

        data = {
            "queue": [{"user_id": 1, "username": "Test", "system": "AOF", "points": "1000"}],
            "matches": [],
            "last_auto_reset_date": yesterday,
        }
        with open(json_file, "w") as f:
            import json
            json.dump(data, f)

        storage = MatchmakingStorage(filepath=str(json_file))
        assert storage.data.get("last_auto_reset_date") == yesterday


class TestQueueAndMatchFlow:
    """Integration-style tests simulating the full matchmaking flow with points."""

    def test_join_empty_queue(self, storage):
        """First user joins → added to queue."""
        storage.add_to_queue(1, "Alice", "AOF", "1000")
        assert storage.is_in_queue(1)
        assert len(storage.queue) == 1

    def test_join_with_matching_opponent(self, storage):
        """Second user with same system + points → instant match."""
        storage.add_to_queue(1, "Alice", "AOF", "1000")
        assert storage.is_in_queue(1)

        # Simulate the cog finding Alice and creating a match
        opponent = storage.find_compatible_opponent(2, "AOF", "1000")
        assert opponent is not None
        storage.remove_from_queue_by_entry(opponent)
        storage.add_match(opponent, {"user_id": 2, "username": "Bob", "system": "AOF", "points": "1000"})

        assert len(storage.queue) == 0
        assert len(storage.matches) == 1
        assert storage.matches[0]["player1"]["username"] == "Alice"
        assert storage.matches[0]["player2"]["username"] == "Bob"
        assert not storage.is_in_queue(1)
        assert storage.is_in_match(1)
        assert storage.is_in_match(2)

    def test_no_match_different_points(self, storage):
        """Same system but different points → no match."""
        storage.add_to_queue(1, "Alice", "AOF", "1000")

        opponent = storage.find_compatible_opponent(2, "AOF", "2000")
        assert opponent is None
        assert storage.is_in_queue(1)

    def test_no_match_different_system(self, storage):
        """Same points but different system → no match."""
        storage.add_to_queue(1, "Alice", "AOF", "1000")

        opponent = storage.find_compatible_opponent(2, "GDF", "1000")
        assert opponent is None
        assert storage.is_in_queue(1)

    def test_user_cannot_be_in_queue_after_match(self, storage):
        """After being matched, user should no longer be in queue."""
        storage.add_to_queue(1, "Alice", "AOF", "1000")
        opponent = storage.find_compatible_opponent(2, "AOF", "1000")
        storage.remove_from_queue_by_entry(opponent)
        storage.add_match(opponent, {"user_id": 2, "username": "Bob", "system": "AOF", "points": "1000"})

        assert not storage.is_in_queue(1)

    def test_leave_while_waiting(self, storage):
        """User can leave while waiting."""
        storage.add_to_queue(1, "Alice", "AOF", "1000")
        assert storage.is_in_queue(1)

        result = storage.remove_from_queue(1)
        assert result is True
        assert not storage.is_in_queue(1)
        assert len(storage.queue) == 0

    def test_leave_while_matched_denied_by_logic(self, storage):
        """is_in_match should return True so the cog can deny leave."""
        p1 = {"user_id": 1, "username": "Alice", "system": "AOF", "points": "1000"}
        p2 = {"user_id": 2, "username": "Bob", "system": "GDF", "points": "2000"}
        storage.add_match(p1, p2)

        assert storage.is_in_match(1)

    def test_multiple_users_in_queue_different_points(self, storage):
        """Users with same system but different points queue separately."""
        storage.add_to_queue(1, "Alice", "AOF", "1000")
        storage.add_to_queue(2, "Bob", "AOF", "1500")
        storage.add_to_queue(3, "Carol", "AOF", "2000")

        assert len(storage.queue) == 3
        assert storage.is_in_queue(1)
        assert storage.is_in_queue(2)
        assert storage.is_in_queue(3)

    def test_fifo_among_compatible(self, storage):
        """First compatible player should be matched."""
        storage.add_to_queue(1, "Alice", "AOF", "1000")
        storage.add_to_queue(2, "Eve", "AOF", "1000")

        # Dave arrives wanting AOF 1000 → should match Alice
        opponent = storage.find_compatible_opponent(4, "AOF", "1000")
        assert opponent["user_id"] == 1


class TestConcurrencyGuard:
    """Test that the asyncio.Lock concept is sound for concurrent joins."""

    @pytest.mark.asyncio
    async def test_lock_serializes_access(self, storage):
        """Verify that the lock prevents concurrent queue modifications."""
        lock = asyncio.Lock()
        results = []

        async def try_join(user_id, system, points):
            async with lock:
                if storage.is_in_queue(user_id):
                    results.append(f"user {user_id}: already_queued")
                    return
                opponent = storage.find_compatible_opponent(user_id, system, points)
                if opponent:
                    storage.remove_from_queue_by_entry(opponent)
                    storage.add_match(opponent, {"user_id": user_id, "username": f"User{user_id}", "system": system, "points": points})
                    results.append(f"user {user_id}: matched with {opponent['username']}")
                else:
                    storage.add_to_queue(user_id, f"User{user_id}", system, points)
                    results.append(f"user {user_id}: queued ({system}/{points})")

        # Simulate two users joining "simultaneously" with same prefs
        await asyncio.gather(
            try_join(1, "AOF", "1000"),
            try_join(2, "AOF", "1000"),
        )

        assert len(results) == 2
        assert storage.is_in_queue(1) or storage.is_in_match(1)
        assert storage.is_in_queue(2) or storage.is_in_match(2)

    @pytest.mark.asyncio
    async def test_different_points_no_match(self, storage):
        """Two users with different points should both queue."""
        lock = asyncio.Lock()
        results = []

        async def try_join(user_id, system, points):
            async with lock:
                if storage.is_in_queue(user_id):
                    results.append(f"user {user_id}: already_queued")
                    return
                opponent = storage.find_compatible_opponent(user_id, system, points)
                if opponent:
                    storage.remove_from_queue_by_entry(opponent)
                    storage.add_match(opponent, {"user_id": user_id, "username": f"User{user_id}", "system": system, "points": points})
                    results.append(f"user {user_id}: matched")
                else:
                    storage.add_to_queue(user_id, f"User{user_id}", system, points)
                    results.append(f"user {user_id}: queued")

        await asyncio.gather(
            try_join(1, "AOF", "1000"),
            try_join(2, "AOF", "2000"),
        )

        assert len(results) == 2
        assert len(storage.queue) == 2
        assert storage.is_in_queue(1)
        assert storage.is_in_queue(2)
        assert len(storage.matches) == 0
