"""Tests for matchmaking business logic and rival challenges."""

import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

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
