"""Shared test fixtures and helpers for matchmaking tests."""

import json

import pytest

from storage import MatchmakingStorage


@pytest.fixture
def tmp_json(tmp_path):
    """Provide a unique temporary JSON file path (file does not exist yet)."""
    return tmp_path / "matchmaking_test.json"


@pytest.fixture
def storage(tmp_json):
    """Provide a MatchmakingStorage instance backed by a unique temp file."""
    return MatchmakingStorage(filepath=str(tmp_json))


@pytest.fixture
def corrupted_json(tmp_json):
    """Write corrupted JSON to the temp file and return its path."""
    with open(tmp_json, "w") as f:
        f.write("{ broken json [[[ }")
    return tmp_json


@pytest.fixture
def partial_json(tmp_json):
    """Write a JSON file with missing required keys."""
    with open(tmp_json, "w") as f:
        json.dump({"queue": []}, f)  # missing "matches"
    return tmp_json
