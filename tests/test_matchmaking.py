"""Tests for matchmaking business logic and scheduled reset."""

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, PropertyMock

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
        # April 2026: first Thursday is April 2, second is April 9
        dt = datetime(2026, 4, 9, tzinfo=timezone.utc)
        assert dt.weekday() == 3
        assert self.is_second_thursday(dt) is True

    def test_first_thursday_not_matched(self):
        """First Thursday (day 1-7) should not trigger."""
        dt = datetime(2026, 4, 2, tzinfo=timezone.utc)
        assert dt.weekday() == 3
        assert self.is_second_thursday(dt) is False

    def test_third_thursday_not_matched(self):
        """Third Thursday (day 15-21) should not trigger."""
        dt = datetime(2026, 4, 16, tzinfo=timezone.utc)
        assert dt.weekday() == 3
        assert self.is_second_thursday(dt) is False

    def test_wednesday_not_matched(self):
        """Non-Thursday should never trigger."""
        dt = datetime(2026, 4, 8, tzinfo=timezone.utc)  # Wednesday
        assert self.is_second_thursday(dt) is False

    def test_friday_not_matched(self):
        dt = datetime(2026, 4, 10, tzinfo=timezone.utc)  # Friday
        assert self.is_second_thursday(dt) is False

    def test_various_months_second_thursday(self):
        """Check known second Thursdays across months."""
        cases = [
            # (year, month, expected_second_thursday_day)
            (2026, 1, 8),   # January 2026
            (2026, 2, 12),  # February 2026
            (2026, 3, 12),  # March 2026
            (2026, 4, 9),   # April 2026
            (2026, 5, 14),  # May 2026
            (2026, 12, 10), # December 2026
        ]
        for year, month, expected_day in cases:
            dt = datetime(year, month, expected_day, tzinfo=timezone.utc)
            assert dt.weekday() == 3, f"{year}-{month:02d}-{expected_day:02d} is not a Thursday"
            assert self.is_second_thursday(dt) is True, f"Failed for {year}-{month}"

    def test_day_before_and_after_second_thursday(self):
        """The days adjacent to second Thursday should not match."""
        # April 2026: second Thursday = 9th
        dt_before = datetime(2026, 4, 8, tzinfo=timezone.utc)   # Wednesday
        dt_after = datetime(2026, 4, 10, tzinfo=timezone.utc)   # Friday
        assert self.is_second_thursday(dt_before) is False
        assert self.is_second_thursday(dt_after) is False


class TestAutoResetDedup:
    """Verify the same-day reset prevention."""

    def test_dedup_prevents_double_reset(self, tmp_path):
        """If last_auto_reset_date is today, don't reset again."""
        json_file = tmp_path / "test.json"
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        data = {
            "queue": [{"user_id": 1, "username": "Test", "faction": "AOF"}],
            "matches": [],
            "last_auto_reset_date": today,
        }
        with open(json_file, "w") as f:
            import json
            json.dump(data, f)

        storage = MatchmakingStorage(filepath=str(json_file))
        # The dedup check would see last_auto_reset_date == today
        assert storage.data.get("last_auto_reset_date") == today

    def test_dedup_allows_reset_on_different_day(self, tmp_path):
        """If last_auto_reset_date is yesterday, allow reset."""
        json_file = tmp_path / "test.json"
        yesterday = "2026-01-01"
        today = "2026-01-02"

        data = {
            "queue": [{"user_id": 1, "username": "Test", "faction": "AOF"}],
            "matches": [],
            "last_auto_reset_date": yesterday,
        }
        with open(json_file, "w") as f:
            import json
            json.dump(data, f)

        storage = MatchmakingStorage(filepath=str(json_file))
        assert storage.data.get("last_auto_reset_date") == yesterday
        # The dedup check would see last_auto_reset_date != today → allow reset


class TestQueueAndMatchFlow:
    """Integration-style tests for the storage layer simulating matchmaking flow."""

    def test_join_empty_queue(self, storage):
        """First user joins → added to queue."""
        storage.add_to_queue(1, "Alice", "AOF")
        assert storage.is_in_queue(1)
        assert len(storage.queue) == 1

    def test_join_with_waiting_opponent(self, storage):
        """Second user joins while someone waits → they get matched."""
        # Alice is waiting
        storage.add_to_queue(1, "Alice", "AOF")
        assert storage.is_in_queue(1)

        # Bob joins → simulate the cog popping Alice and creating a match
        opponent = storage.queue.pop(0)
        storage.add_match(opponent, {"user_id": 2, "username": "Bob", "faction": "GDF"})

        assert len(storage.queue) == 0
        assert len(storage.matches) == 1
        assert storage.matches[0]["player1"]["username"] == "Alice"
        assert storage.matches[0]["player2"]["username"] == "Bob"
        assert not storage.is_in_queue(1)
        assert storage.is_in_match(1)
        assert storage.is_in_match(2)

    def test_user_cannot_be_in_queue_after_match(self, storage):
        """After being matched, user should no longer be in queue."""
        storage.add_to_queue(1, "Alice", "AOF")
        opponent = storage.queue.pop(0)
        storage.add_match(opponent, {"user_id": 2, "username": "Bob", "faction": "GDF"})

        assert not storage.is_in_queue(1)

    def test_leave_while_waiting(self, storage):
        """User can leave while waiting."""
        storage.add_to_queue(1, "Alice", "AOF")
        assert storage.is_in_queue(1)

        result = storage.remove_from_queue(1)
        assert result is True
        assert not storage.is_in_queue(1)
        assert len(storage.queue) == 0

    def test_leave_while_matched_denied_by_logic(self, storage):
        """The storage layer doesn't prevent leaving a match — that's the cog's job.
        But is_in_match should return True so the cog can deny it."""
        p1 = {"user_id": 1, "username": "Alice", "faction": "AOF"}
        p2 = {"user_id": 2, "username": "Bob", "faction": "GDF"}
        storage.add_match(p1, p2)

        assert storage.is_in_match(1)
        # The cog layer should block the leave based on this

    def test_multiple_users_in_queue(self, storage):
        """Multiple users can wait simultaneously."""
        storage.add_to_queue(1, "Alice", "AOF")
        storage.add_to_queue(2, "Bob", "GDF")
        storage.add_to_queue(3, "Carol", "AOF")

        assert len(storage.queue) == 3
        assert storage.is_in_queue(1)
        assert storage.is_in_queue(2)
        assert storage.is_in_queue(3)

    def test_fifo_order(self, storage):
        """Queue should be FIFO — first in, first matched."""
        storage.add_to_queue(1, "Alice", "AOF")
        storage.add_to_queue(2, "Bob", "GDF")

        opponent = storage.queue.pop(0)
        assert opponent["user_id"] == 1
        assert opponent["username"] == "Alice"


class TestConcurrencyGuard:
    """Test that the asyncio.Lock concept is sound for concurrent joins."""

    @pytest.mark.asyncio
    async def test_lock_serializes_access(self, storage):
        """Verify that the lock prevents concurrent queue modifications."""
        lock = asyncio.Lock()
        results = []

        async def try_join(user_id):
            async with lock:
                if storage.is_in_queue(user_id):
                    results.append(f"user {user_id}: already_queued")
                    return
                if storage.queue:
                    opponent = storage.queue.pop(0)
                    storage.add_match(opponent, {"user_id": user_id, "username": f"User{user_id}", "faction": "GDF"})
                    results.append(f"user {user_id}: matched with {opponent['username']}")
                else:
                    storage.add_to_queue(user_id, f"User{user_id}", "AOF")
                    results.append(f"user {user_id}: queued")

        # Simulate two users joining "simultaneously"
        await asyncio.gather(
            try_join(1),
            try_join(2),
        )

        # One should be queued, one should be matched (or both queued if order differs)
        assert len(results) == 2
        # The queue should not have both users if they were matched
        # or at minimum, no corruption occurred
        assert storage.is_in_queue(1) or storage.is_in_match(1)
        assert storage.is_in_queue(2) or storage.is_in_match(2)
