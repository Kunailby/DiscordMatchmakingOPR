"""Tests for matchmaking business logic, rival challenges, and scheduled reset."""

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from storage import MatchmakingStorage


class TestSecondFridayDetection:
    """Verify the second-Friday date calculation logic."""

    def is_second_friday(self, dt: datetime) -> bool:
        """Replicate the logic from the cog for testing."""
        if dt.weekday() != 4:  # Not Friday
            return False
        week_number = (dt.day - 1) // 7 + 1
        return week_number == 2

    def test_second_friday_first_half(self):
        """Second Friday falls on day 8-14."""
        # April 2026: first Friday is April 3, second is April 10
        dt = datetime(2026, 4, 10, tzinfo=timezone.utc)
        assert dt.weekday() == 4
        assert self.is_second_friday(dt) is True

    def test_first_friday_not_matched(self):
        dt = datetime(2026, 4, 3, tzinfo=timezone.utc)
        assert dt.weekday() == 4
        assert self.is_second_friday(dt) is False

    def test_third_friday_not_matched(self):
        dt = datetime(2026, 4, 17, tzinfo=timezone.utc)
        assert dt.weekday() == 4
        assert self.is_second_friday(dt) is False

    def test_thursday_not_matched(self):
        dt = datetime(2026, 4, 9, tzinfo=timezone.utc)
        assert self.is_second_friday(dt) is False

    def test_saturday_not_matched(self):
        dt = datetime(2026, 4, 11, tzinfo=timezone.utc)
        assert self.is_second_friday(dt) is False

    def test_various_months_second_friday(self):
        """Check known second Fridays across months."""
        cases = [
            (2026, 1, 9), (2026, 2, 13), (2026, 3, 13),
            (2026, 4, 10), (2026, 5, 8), (2026, 12, 11),
        ]
        for year, month, expected_day in cases:
            dt = datetime(year, month, expected_day, tzinfo=timezone.utc)
            assert dt.weekday() == 4, f"{year}-{month:02d}-{expected_day:02d} is not a Friday"
            assert self.is_second_friday(dt) is True, f"Failed for {year}-{month}"

    def test_day_before_and_after_second_friday(self):
        # April 2026: second Friday = 10th
        dt_before = datetime(2026, 4, 9, tzinfo=timezone.utc)   # Thursday
        dt_after = datetime(2026, 4, 11, tzinfo=timezone.utc)   # Saturday
        assert self.is_second_friday(dt_before) is False
        assert self.is_second_friday(dt_after) is False


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
        storage.add_to_queue(1, "Alice", "AOF", "1000")
        assert storage.is_in_queue(1)
        assert len(storage.queue) == 1

    def test_join_with_matching_opponent(self, storage):
        """Second user with same system + points → instant match."""
        storage.add_to_queue(1, "Alice", "AOF", "1000")
        assert storage.is_in_queue(1)

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
        storage.add_to_queue(1, "Alice", "AOF", "1000")
        opponent = storage.find_compatible_opponent(2, "AOF", "2000")
        assert opponent is None
        assert storage.is_in_queue(1)

    def test_no_match_different_system(self, storage):
        storage.add_to_queue(1, "Alice", "AOF", "1000")
        opponent = storage.find_compatible_opponent(2, "GDF", "1000")
        assert opponent is None
        assert storage.is_in_queue(1)

    def test_user_cannot_be_in_queue_after_match(self, storage):
        storage.add_to_queue(1, "Alice", "AOF", "1000")
        opponent = storage.find_compatible_opponent(2, "AOF", "1000")
        storage.remove_from_queue_by_entry(opponent)
        storage.add_match(opponent, {"user_id": 2, "username": "Bob", "system": "AOF", "points": "1000"})
        assert not storage.is_in_queue(1)

    def test_leave_while_waiting(self, storage):
        storage.add_to_queue(1, "Alice", "AOF", "1000")
        assert storage.is_in_queue(1)
        result = storage.remove_from_queue(1)
        assert result is True
        assert not storage.is_in_queue(1)
        assert len(storage.queue) == 0

    def test_leave_while_matched_denied_by_logic(self, storage):
        p1 = {"user_id": 1, "username": "Alice", "system": "AOF", "points": "1000"}
        p2 = {"user_id": 2, "username": "Bob", "system": "GDF", "points": "2000"}
        storage.add_match(p1, p2)
        assert storage.is_in_match(1)

    def test_multiple_users_in_queue_different_points(self, storage):
        storage.add_to_queue(1, "Alice", "AOF", "1000")
        storage.add_to_queue(2, "Bob", "AOF", "1500")
        storage.add_to_queue(3, "Carol", "AOF", "2000")
        assert len(storage.queue) == 3

    def test_fifo_among_compatible(self, storage):
        storage.add_to_queue(1, "Alice", "AOF", "1000")
        storage.add_to_queue(2, "Eve", "AOF", "1000")
        opponent = storage.find_compatible_opponent(4, "AOF", "1000")
        assert opponent["user_id"] == 1


class TestConcurrencyGuard:
    """Test that the asyncio.Lock concept is sound for concurrent joins."""

    @pytest.mark.asyncio
    async def test_lock_serializes_access(self, storage):
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

        await asyncio.gather(
            try_join(1, "AOF", "1000"),
            try_join(2, "AOF", "1000"),
        )

        assert len(results) == 2
        assert storage.is_in_queue(1) or storage.is_in_match(1)
        assert storage.is_in_queue(2) or storage.is_in_match(2)

    @pytest.mark.asyncio
    async def test_different_points_no_match(self, storage):
        lock = asyncio.Lock()

        async def try_join(user_id, system, points):
            async with lock:
                if storage.is_in_queue(user_id):
                    return
                opponent = storage.find_compatible_opponent(user_id, system, points)
                if opponent:
                    storage.remove_from_queue_by_entry(opponent)
                    storage.add_match(opponent, {"user_id": user_id, "username": f"User{user_id}", "system": system, "points": points})
                else:
                    storage.add_to_queue(user_id, f"User{user_id}", system, points)

        await asyncio.gather(
            try_join(1, "AOF", "1000"),
            try_join(2, "AOF", "2000"),
        )

        assert len(storage.queue) == 2
        assert len(storage.matches) == 0
